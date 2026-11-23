"""Tests de la collecte des statistiques (API GitHub simulée, aucun appel réseau)."""

from __future__ import annotations

from collections.abc import Callable, Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from src import github_stats
from src.config import Config
from src.github_stats import GitHubAuthError, GitHubStatsPrivate, build_heatmap, parse_github_date
from src.readme_renderer import load_profile, render_readme
from src.utils import token_fingerprint, validate_github_token

NOW = datetime.now(UTC)
RECENT = (NOW - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
OLD = (NOW - timedelta(days=400)).strftime("%Y-%m-%dT%H:%M:%SZ")


class FakeResponse:
    def __init__(self, status_code: int = 200, payload: Any = None, headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload if payload is not None else []
        self.headers = headers or {}

    def json(self) -> Any:
        return self._payload


Route = dict[tuple[str, int], FakeResponse]


@pytest.fixture
def make_collector(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Callable[..., GitHubStatsPrivate]:
    for var in ("GITHUB_TOKEN", "GITHUB_USERNAME", "CACHE_ENABLED", "LOG_LEVEL"):
        monkeypatch.delenv(var, raising=False)

    def factory(*, cache: bool = False) -> GitHubStatsPrivate:
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "github: {token: '', username: falilouMBC}\n"
            f"cache: {{enabled: {str(cache).lower()}, directory: '{tmp_path / 'cache'}'}}\n"
            f"logging: {{level: INFO, directory: '{tmp_path / 'logs'}'}}\n"
            "stats: {days_back: 365, max_commits_pages: 2}\n"
            "rate_limit: {min_remaining: 100}\n",
            encoding="utf-8",
        )
        return GitHubStatsPrivate("github_pat_test", "falilouMBC", Config(str(config_file)))

    return factory


@pytest.fixture
def api(monkeypatch: pytest.MonkeyPatch) -> Iterator[Route]:
    """Routes simulées : (chemin, page) → réponse ; page 0 = requête sans pagination."""
    routes: Route = {}

    def fake_get(url: str, *, headers: dict[str, str], params: dict[str, Any] | None, timeout: int) -> FakeResponse:
        assert headers["Authorization"] == "Bearer github_pat_test"
        assert timeout == github_stats.REQUEST_TIMEOUT
        path = url.removeprefix("https://api.github.com")
        page = int((params or {}).get("page", 0))
        return routes.get((path, page), FakeResponse(404, {"message": "Not Found"}))

    monkeypatch.setattr("src.github_stats.requests.get", fake_get)
    yield routes


def repo(name: str, **extra: Any) -> dict[str, Any]:
    return {"full_name": f"falilouMBC/{name}", "private": False, "stargazers_count": 0, "fork": False, **extra}


def pr(login: str | None, state: str, merged: bool = False) -> dict[str, Any]:
    return {"user": {"login": login} if login else None, "state": state, "merged_at": RECENT if merged else None}


def commit(when: str) -> dict[str, Any]:
    return {"commit": {"author": {"date": when}}}


# ------------------------------------------------------------- utilitaires


def test_parse_github_date_and_heatmap() -> None:
    monday_9h = parse_github_date("2026-11-23T09:15:00Z")
    assert monday_9h == datetime(2026, 11, 23, 9, 15, tzinfo=UTC)
    heatmap = build_heatmap([monday_9h, monday_9h, parse_github_date("2026-11-27T15:00:00+02:00")])
    assert heatmap[0][9] == 2
    assert heatmap[4][13] == 1  # converti en UTC


def test_token_validation_and_fingerprint() -> None:
    assert validate_github_token("github_pat_" + "A1b2_" * 17)
    assert validate_github_token("ghp_" + "a" * 36)
    assert not validate_github_token("ghp_court")
    assert not validate_github_token("")
    fingerprint = token_fingerprint("ghp_" + "a" * 36)
    assert fingerprint.startswith("sha256:") and len(fingerprint) == 15
    assert "aaaa" not in fingerprint


# ----------------------------------------------------------- dépôts / auth


def test_repos_are_paginated(make_collector: Callable[..., GitHubStatsPrivate], api: Route) -> None:
    api[("/user/repos", 1)] = FakeResponse(payload=[repo(f"r{i}") for i in range(100)])
    api[("/user/repos", 2)] = FakeResponse(payload=[repo("last")])
    assert len(make_collector().get_all_repos()) == 101


def test_repos_use_cache(make_collector: Callable[..., GitHubStatsPrivate], api: Route) -> None:
    api[("/user/repos", 1)] = FakeResponse(payload=[repo("a")])
    collector = make_collector(cache=True)
    assert len(collector.get_all_repos()) == 1
    api.clear()  # le second appel ne doit plus toucher l'API
    assert collector.get_all_repos()[0]["full_name"] == "falilouMBC/a"


@pytest.mark.parametrize("status", [401, 403])
def test_refused_token_on_repos_is_fatal(
    make_collector: Callable[..., GitHubStatsPrivate], api: Route, status: int
) -> None:
    api[("/user/repos", 1)] = FakeResponse(status, {"message": "Bad credentials"})
    with pytest.raises(GitHubAuthError, match=f"HTTP {status}.*STATS_TOKEN"):
        make_collector().get_all_repos()


def test_invalid_token_anywhere_is_fatal(make_collector: Callable[..., GitHubStatsPrivate], api: Route) -> None:
    api[("/repos/falilouMBC/a/pulls", 1)] = FakeResponse(401)
    with pytest.raises(GitHubAuthError):
        make_collector().count_pull_requests([repo("a")])


# ----------------------------------------------------------------- PR


def test_pull_requests_counted_for_author_only(make_collector: Callable[..., GitHubStatsPrivate], api: Route) -> None:
    api[("/repos/falilouMBC/a/pulls", 1)] = FakeResponse(
        payload=[
            pr("falilouMBC", "open"),
            pr("falilouMBC", "closed", merged=True),
            pr("falilouMBC", "closed", merged=True),
            pr("falilouMBC", "closed"),
            pr("dependabot[bot]", "closed", merged=True),
            pr(None, "open"),
        ]
    )
    api[("/repos/falilouMBC/b/pulls", 1)] = FakeResponse(403)  # dépôt inaccessible : ignoré
    stats = make_collector().count_pull_requests([repo("a"), repo("b"), repo("c")])  # c → 404 ignoré
    assert stats == {"total": 4, "open": 1, "merged": 2, "closed_unmerged": 1}


# ------------------------------------------------------------- commits


def test_commits_respect_page_cap_and_skip_empty_repo(
    make_collector: Callable[..., GitHubStatsPrivate], api: Route
) -> None:
    for page in (1, 2, 3):
        api[("/repos/falilouMBC/a/commits", page)] = FakeResponse(payload=[commit(RECENT)] * 100)
    api[("/repos/falilouMBC/empty/commits", 1)] = FakeResponse(409, {"message": "Git Repository is empty."})
    dates = make_collector().get_commit_dates([repo("a"), repo("empty")])
    assert len(dates) == 200  # max_commits_pages = 2


def test_active_repos(make_collector: Callable[..., GitHubStatsPrivate]) -> None:
    repos = [repo("new", pushed_at=RECENT), repo("old", pushed_at=OLD), repo("never", pushed_at=None)]
    assert make_collector().count_active_repos(repos) == 1


# ------------------------------------------------------------ langages


def test_languages_exclude_forks_and_failures(make_collector: Callable[..., GitHubStatsPrivate], api: Route) -> None:
    api[("/repos/falilouMBC/a/languages", 0)] = FakeResponse(payload={"Python": 300, "TypeScript": 600})
    api[("/repos/falilouMBC/b/languages", 0)] = FakeResponse(payload={"TypeScript": 100})
    api[("/repos/falilouMBC/fork/languages", 0)] = FakeResponse(payload={"C": 10_000})
    repos = [repo("a"), repo("b"), repo("fork", fork=True), repo("gone")]
    languages = make_collector().get_language_stats(repos)
    assert languages == {"TypeScript": 70.0, "Python": 30.0}
    assert list(languages) == ["TypeScript", "Python"]


def test_languages_empty(make_collector: Callable[..., GitHubStatsPrivate], api: Route) -> None:
    api[("/repos/falilouMBC/a/languages", 0)] = FakeResponse(payload={})
    assert make_collector().get_language_stats([repo("a")]) == {}


# ---------------------------------------------------------- rate limit


def test_low_rate_limit_waits_until_reset(
    make_collector: Callable[..., GitHubStatsPrivate], api: Route, monkeypatch: pytest.MonkeyPatch
) -> None:
    slept: list[float] = []
    monkeypatch.setattr("src.github_stats.time.time", lambda: 1_000.0)
    monkeypatch.setattr("src.github_stats.time.sleep", slept.append)
    low = {"X-RateLimit-Remaining": "5", "X-RateLimit-Reset": "1060"}
    api[("/repos/falilouMBC/a/languages", 0)] = FakeResponse(payload={"Go": 1}, headers=low)
    api[("/repos/falilouMBC/b/languages", 0)] = FakeResponse(
        payload={"Go": 1}, headers={"X-RateLimit-Remaining": "5", "X-RateLimit-Reset": "999999"}
    )
    api[("/repos/falilouMBC/c/languages", 0)] = FakeResponse(
        payload={"Go": 1}, headers={"X-RateLimit-Remaining": "4000", "X-RateLimit-Reset": "1060"}
    )
    make_collector().get_language_stats([repo("a"), repo("b"), repo("c")])
    assert slept == [61, github_stats.MAX_RATE_LIMIT_WAIT]


# ------------------------------------------------------------ bout en bout


def test_calculate_all_stats_renders(
    make_collector: Callable[..., GitHubStatsPrivate], api: Route, monkeypatch: pytest.MonkeyPatch
) -> None:
    collector = make_collector()
    monkeypatch.setattr(collector.rate_limiter, "get_status_message", lambda: "rate limit ok")
    api[("/user/repos", 1)] = FakeResponse(
        payload=[
            repo("pub", stargazers_count=5, pushed_at=RECENT),
            repo("priv", private=True, stargazers_count=2, pushed_at=OLD),
        ]
    )
    api[("/repos/falilouMBC/pub/commits", 1)] = FakeResponse(payload=[commit("2026-11-23T09:00:00Z")] * 3)
    api[("/repos/falilouMBC/pub/pulls", 1)] = FakeResponse(payload=[pr("falilouMBC", "closed", merged=True)])
    api[("/repos/falilouMBC/pub/languages", 0)] = FakeResponse(payload={"TypeScript": 10})

    stats = collector.calculate_all_stats()

    assert stats["total_repos"] == 2 and stats["public_repos"] == 1 and stats["private_repos"] == 1
    assert stats["stars"] == 7 and stats["commits_last_year"] == 3 and stats["active_repos"] == 1
    assert stats["activity_heatmap"][0][9] == 3
    readme = render_readme(
        load_profile({"name": "Falilou", "headline": "Dev"}),
        stats,
        username="falilouMBC",
        updated_on=NOW.date(),
    )
    assert "**2** (1 public · 1 private)" in readme
