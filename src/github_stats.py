"""
GitHub Stats Module
===================

Collecte les statistiques du compte via l'API REST GitHub (dépôts publics et
privés accessibles au jeton) :

- dépôts (publics / privés), étoiles, dépôts actifs
- commits de l'utilisateur sur la période (compte + heatmap jour/heure UTC)
- pull requests créées par l'utilisateur (ouvertes, mergées, fermées sans merge)
- langages (hors forks)

Le jeton n'a besoin que de droits en LECTURE : la publication du README est
faite par le workflow (commit avec GITHUB_TOKEN), pas par ce module.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import requests

from .cache_manager import CacheManager
from .config import Config
from .rate_limiter import RateLimitHandler
from .readme_renderer import ProfileStats, PullRequestStats

PER_PAGE = 100
REQUEST_TIMEOUT = 30
MAX_RATE_LIMIT_WAIT = 900

JsonObject = dict[str, Any]
QueryParams = Mapping[str, str | int]


class GitHubAuthError(RuntimeError):
    """Jeton refusé par GitHub (expiré, révoqué ou droits insuffisants)."""


def parse_github_date(value: str) -> datetime:
    """Convertit une date ISO 8601 de l'API (ex. 2026-04-20T02:52:00Z) en datetime UTC."""
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(UTC)


def build_heatmap(dates: list[datetime]) -> dict[int, dict[int, int]]:
    """Compte les commits par jour de semaine (0 = lundi) et par heure UTC."""
    heatmap = {day: dict.fromkeys(range(24), 0) for day in range(7)}
    for moment in dates:
        utc = moment.astimezone(UTC)
        heatmap[utc.weekday()][utc.hour] += 1
    return heatmap


class GitHubStatsPrivate:
    """Collecteur de statistiques pour un compte GitHub."""

    def __init__(self, token: str, username: str, config: Config | None = None) -> None:
        self.username = username
        self.headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        self.base_url = "https://api.github.com"
        self.config = config or Config()
        self.cache = CacheManager(self.config.get("cache.directory", ".cache"))
        self.min_remaining = int(self.config.get("rate_limit.min_remaining", 100))
        self.rate_limiter = RateLimitHandler(self.headers, self.min_remaining)
        self.days_back = int(self.config.get("stats.days_back", 365))
        self.max_commit_pages = int(self.config.get("stats.max_commits_pages", 10))
        self.logger = self._setup_logger()

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("GitHubStats")
        if logger.handlers:
            return logger
        logger.setLevel(getattr(logging, str(self.config.get("logging.level", "INFO")), logging.INFO))
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(formatter)
        logger.addHandler(console)
        log_dir = Path(self.config.get("logging.directory", "logs"))
        log_dir.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "github_stats.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        return logger

    # ------------------------------------------------------------------
    # Accès HTTP
    # ------------------------------------------------------------------

    def _respect_rate_limit(self, response: requests.Response) -> None:
        remaining = response.headers.get("X-RateLimit-Remaining")
        reset = response.headers.get("X-RateLimit-Reset")
        if remaining is None or reset is None or int(remaining) >= self.min_remaining:
            return
        wait = min(MAX_RATE_LIMIT_WAIT, max(0, int(reset) - int(time.time())) + 1)
        self.logger.warning("⏳ Rate limit bas (%s restantes), pause de %s s", remaining, wait)
        time.sleep(wait)

    def _get(self, path: str, params: QueryParams | None = None) -> requests.Response:
        response = requests.get(f"{self.base_url}{path}", headers=self.headers, params=params, timeout=REQUEST_TIMEOUT)
        self._respect_rate_limit(response)
        return response

    def _paginate(
        self, path: str, params: QueryParams | None = None, *, max_pages: int = 50, required: bool = False
    ) -> list[JsonObject]:
        """Récupère toutes les pages d'une liste.

        401 (jeton invalide) est toujours fatal, 403 l'est si la ressource est indispensable ;
        toute autre erreur (404 dépôt inaccessible, 409 dépôt vide…) ignore la ressource.
        """
        items: list[JsonObject] = []
        for page in range(1, max_pages + 1):
            response = self._get(path, {**(params or {}), "per_page": PER_PAGE, "page": page})
            if response.status_code == 401 or (response.status_code == 403 and required):
                raise GitHubAuthError(
                    f"GitHub a refusé le jeton (HTTP {response.status_code}) : "
                    "STATS_TOKEN expiré, révoqué ou sans accès en lecture aux dépôts"
                )
            if response.status_code != 200:
                self.logger.warning("⚠️  %s ignoré (HTTP %s)", path, response.status_code)
                break
            data = response.json()
            if not isinstance(data, list):
                break
            items.extend(data)
            if len(data) < PER_PAGE:
                break
        return items

    # ------------------------------------------------------------------
    # Statistiques
    # ------------------------------------------------------------------

    def get_all_repos(self) -> list[JsonObject]:
        """Tous les dépôts dont l'utilisateur est propriétaire (publics + privés)."""
        cache_key = f"repos_{self.username}"
        use_cache = bool(self.config.get("cache.enabled", True))
        if use_cache:
            cached = self.cache.get(cache_key, max_age_hours=self.config.get("cache.max_age_hours", 24))
            if isinstance(cached, list):
                self.logger.info("📦 Cache utilisé pour les dépôts (%s)", len(cached))
                return cached
        repos = self._paginate("/user/repos", {"type": "owner", "sort": "updated"}, required=True)
        self.logger.info("✅ %s dépôt(s) récupéré(s)", len(repos))
        if use_cache:
            self.cache.set(cache_key, repos)
        return repos

    def _since(self) -> datetime:
        return datetime.now(UTC) - timedelta(days=self.days_back)

    def get_commit_dates(self, repos: list[JsonObject]) -> list[datetime]:
        """Dates des commits de l'utilisateur sur la période, tous dépôts confondus."""
        since = self._since().strftime("%Y-%m-%dT%H:%M:%SZ")
        dates: list[datetime] = []
        for repo in repos:
            commits = self._paginate(
                f"/repos/{repo['full_name']}/commits",
                {"author": self.username, "since": since},
                max_pages=self.max_commit_pages,
            )
            dates += [parse_github_date(c["commit"]["author"]["date"]) for c in commits]
        self.logger.info("✅ %s commit(s) sur %s jours", len(dates), self.days_back)
        return dates

    def count_pull_requests(self, repos: list[JsonObject]) -> PullRequestStats:
        """PR créées par l'utilisateur (l'API /pulls ne filtre pas par auteur : filtre local)."""
        stats: PullRequestStats = {"total": 0, "open": 0, "merged": 0, "closed_unmerged": 0}
        for repo in repos:
            for pr in self._paginate(f"/repos/{repo['full_name']}/pulls", {"state": "all"}):
                if (pr.get("user") or {}).get("login") != self.username:
                    continue
                stats["total"] += 1
                if pr["state"] == "open":
                    stats["open"] += 1
                elif pr.get("merged_at"):
                    stats["merged"] += 1
                else:
                    stats["closed_unmerged"] += 1
        self.logger.info("✅ %s PR (%s mergées)", stats["total"], stats["merged"])
        return stats

    def count_active_repos(self, repos: list[JsonObject]) -> int:
        """Dépôts ayant reçu un push sur la période."""
        since = self._since()
        return sum(1 for r in repos if r.get("pushed_at") and parse_github_date(r["pushed_at"]) >= since)

    def get_language_stats(self, repos: list[JsonObject]) -> dict[str, float]:
        """Part de chaque langage (en octets), forks exclus, triée par ordre décroissant."""
        totals: dict[str, int] = {}
        for repo in repos:
            if repo.get("fork"):
                continue
            response = self._get(f"/repos/{repo['full_name']}/languages")
            if response.status_code != 200:
                self.logger.warning("⚠️  Langages de %s ignorés (HTTP %s)", repo["full_name"], response.status_code)
                continue
            for language, size in response.json().items():
                totals[language] = totals.get(language, 0) + int(size)
        grand_total = sum(totals.values())
        if grand_total == 0:
            return {}
        ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
        return {language: round(size / grand_total * 100, 2) for language, size in ranked}

    def calculate_all_stats(self) -> ProfileStats:
        """Calcule l'ensemble des statistiques utilisées par le README."""
        print(self.rate_limiter.get_status_message())
        repos = self.get_all_repos()
        commit_dates = self.get_commit_dates(repos)
        return {
            "total_repos": len(repos),
            "public_repos": sum(1 for r in repos if not r["private"]),
            "private_repos": sum(1 for r in repos if r["private"]),
            "stars": sum(int(r["stargazers_count"]) for r in repos),
            "commits_last_year": len(commit_dates),
            "active_repos": self.count_active_repos(repos),
            "prs": self.count_pull_requests(repos),
            "languages": self.get_language_stats(repos),
            "activity_heatmap": build_heatmap(commit_dates),
            "period_days": self.days_back,
        }
