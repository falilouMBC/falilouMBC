"""Rendu du README de profil GitHub.

Le contenu éditorial (présentation, stack, contacts) vient de la section
``profile`` de ``configs/config.yaml`` ; les chiffres viennent de
``GitHubStatsPrivate.calculate_all_stats``. Ce module ne fait aucun appel
réseau : il valide le contenu puis produit le Markdown.
"""

from __future__ import annotations

import html
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import TypedDict
from urllib.parse import quote

BADGE_STYLE = "for-the-badge"
ALLOWED_SECTIONS = ("about", "stack", "stats", "languages", "activity", "contact")
MAX_LANGUAGES = 6
LANGUAGE_BAR_LENGTH = 30

_HEX_COLOR = re.compile(r"^[0-9A-Fa-f]{6}$")
_NAMED_COLOR = re.compile(r"^[a-z]+$")
_ICON_SLUG = re.compile(r"^[a-z0-9]+$")
_EMAIL = re.compile(r"^[^@\s<>()\[\]]+@[^@\s<>()\[\]]+\.[A-Za-z]{2,}$")
_LINKEDIN = re.compile(r"^https://(www\.)?linkedin\.com/in/[A-Za-z0-9_-]+/?$")
_USERNAME = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$")
_DAYS = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")
_HEAT_LEVELS = ("⬜", "🟩", "🟨", "🟧", "🟥")


class ProfileConfigError(ValueError):
    """Contenu invalide dans la section ``profile`` ou ``readme`` de la config."""


class PullRequestStats(TypedDict):
    total: int
    open: int
    merged: int
    closed_unmerged: int


class ProfileStats(TypedDict):
    total_repos: int
    public_repos: int
    private_repos: int
    stars: int
    commits_last_year: int
    active_repos: int
    prs: PullRequestStats
    languages: dict[str, float]
    activity_heatmap: dict[int, dict[int, int]]
    period_days: int


@dataclass(frozen=True)
class Badge:
    label: str
    color: str
    logo: str
    logo_color: str


@dataclass(frozen=True)
class Profile:
    name: str
    headline: str
    location: str
    summary: str
    about: tuple[str, ...]
    stack: tuple[Badge, ...]
    learning: tuple[Badge, ...]
    linkedin: str
    email: str


# --------------------------------------------------------------------------
# Validation du contenu (schéma de la section ``profile``)
# --------------------------------------------------------------------------


def _mapping(raw: object, where: str) -> Mapping[str, object]:
    if not isinstance(raw, Mapping):
        raise ProfileConfigError(f"{where} doit être un dictionnaire")
    return raw


def _text(raw: Mapping[str, object], key: str, where: str, *, required: bool) -> str:
    value = raw.get(key, "")
    if not isinstance(value, str):
        raise ProfileConfigError(f"{where}.{key} doit être une chaîne")
    value = value.strip()
    if required and not value:
        raise ProfileConfigError(f"{where}.{key} est obligatoire")
    return value


def _text_list(raw: object, where: str) -> tuple[str, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list) or not all(isinstance(i, str) and i.strip() for i in raw):
        raise ProfileConfigError(f"{where} doit être une liste de chaînes non vides")
    return tuple(i.strip() for i in raw)


def _badge(raw: object, where: str) -> Badge:
    item = _mapping(raw, where)
    color = _text(item, "color", where, required=True)
    if not _HEX_COLOR.match(color):
        raise ProfileConfigError(f"{where}.color doit être une couleur hexadécimale (ex. 3178C6)")
    logo = _text(item, "logo", where, required=False)
    if logo and not _ICON_SLUG.match(logo):
        raise ProfileConfigError(f"{where}.logo doit être un identifiant simple-icons (ex. docker)")
    logo_color = _text(item, "logo_color", where, required=False) or "white"
    if not (_HEX_COLOR.match(logo_color) or _NAMED_COLOR.match(logo_color)):
        raise ProfileConfigError(f"{where}.logo_color invalide")
    return Badge(_text(item, "label", where, required=True), color, logo, logo_color)


def _badges(raw: object, where: str) -> tuple[Badge, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ProfileConfigError(f"{where} doit être une liste")
    return tuple(_badge(item, f"{where}[{i}]") for i, item in enumerate(raw))


def _contact(raw: object) -> tuple[str, str]:
    contact = _mapping(raw if raw is not None else {}, "profile.contact")
    linkedin = _text(contact, "linkedin", "profile.contact", required=False)
    if linkedin and not _LINKEDIN.match(linkedin):
        raise ProfileConfigError("profile.contact.linkedin doit être https://www.linkedin.com/in/…")
    email = _text(contact, "email", "profile.contact", required=False)
    if email and not _EMAIL.match(email):
        raise ProfileConfigError("profile.contact.email invalide")
    return linkedin, email


def load_profile(raw: object) -> Profile:
    """Valide la section ``profile`` de la config et la convertit en ``Profile``."""
    data = _mapping(raw, "profile")
    linkedin, email = _contact(data.get("contact"))
    return Profile(
        name=_text(data, "name", "profile", required=True),
        headline=_text(data, "headline", "profile", required=True),
        location=_text(data, "location", "profile", required=False),
        summary=_text(data, "summary", "profile", required=False),
        about=_text_list(data.get("about"), "profile.about"),
        stack=_badges(data.get("stack"), "profile.stack"),
        learning=_badges(data.get("learning"), "profile.learning"),
        linkedin=linkedin,
        email=email,
    )


def load_sections(raw: object) -> tuple[str, ...]:
    """Valide ``readme.sections`` ; toutes les sections si la clé est absente."""
    if raw is None:
        return ALLOWED_SECTIONS
    if not isinstance(raw, list) or not all(isinstance(s, str) for s in raw):
        raise ProfileConfigError("readme.sections doit être une liste de chaînes")
    unknown = sorted(set(raw) - set(ALLOWED_SECTIONS))
    if unknown:
        allowed = ", ".join(ALLOWED_SECTIONS)
        raise ProfileConfigError(f"readme.sections inconnues : {', '.join(unknown)} (autorisées : {allowed})")
    return tuple(raw)


# --------------------------------------------------------------------------
# Rendu Markdown
# --------------------------------------------------------------------------


def _escape(text: str) -> str:
    return html.escape(text, quote=False)


def badge_markdown(badge: Badge) -> str:
    """Badge statique shields.io (le libellé est encodé selon les règles shields)."""
    label = quote(badge.label.replace("-", "--").replace("_", "__"), safe="")
    url = f"https://img.shields.io/badge/{label}-{badge.color}?style={BADGE_STYLE}"
    if badge.logo:
        url += f"&logo={badge.logo}&logoColor={badge.logo_color}"
    alt = badge.label.replace("[", "\\[").replace("]", "\\]")
    return f"![{alt}]({url})"


def _header(profile: Profile) -> str:
    tagline = f"**{_escape(profile.headline)}**"
    if profile.location:
        tagline += f" · 📍 {_escape(profile.location)}"
    lines = [f"# Hi, I'm {_escape(profile.name)} 👋", "", tagline]
    if profile.summary:
        lines += ["", _escape(profile.summary)]
    return "\n".join(lines)


def _about(profile: Profile) -> str:
    if not profile.about:
        return ""
    items = "\n".join(f"- {_escape(item)}" for item in profile.about)
    return f"## 🧑‍💻 About me\n\n{items}"


def _stack(profile: Profile) -> str:
    if not profile.stack:
        return ""
    block = "## 🛠️ Tech stack\n\n" + "\n".join(badge_markdown(b) for b in profile.stack)
    if profile.learning:
        learning = " ".join(badge_markdown(b) for b in profile.learning)
        block += f"\n\n**Currently learning:** {learning}"
    return block


def _period(days: int) -> str:
    return "last 12 months" if days == 365 else f"last {days} days"


def _stats(stats: ProfileStats) -> str:
    period = _period(stats["period_days"])
    prs = stats["prs"]
    pr_detail = f"{prs['merged']:,} merged · {prs['open']:,} open"
    if prs["closed_unmerged"]:
        pr_detail += f" · {prs['closed_unmerged']:,} closed"
    rows = [
        f"| 📝 Commits ({period}) | **{stats['commits_last_year']:,}** |",
        f"| 📦 Active repositories ({period}) | **{stats['active_repos']:,}** |",
        f"| 🔀 Pull requests | **{prs['total']:,}** ({pr_detail}) |",
        f"| 🗂️ Repositories | **{stats['total_repos']:,}** "
        f"({stats['public_repos']:,} public · {stats['private_repos']:,} private) |",
        f"| ⭐ Stars earned | **{stats['stars']:,}** |",
    ]
    table = "\n".join(["| Metric | Value |", "| :-- | --: |", *rows])
    return f"## 📊 GitHub activity\n\n<sub>Public and private repositories.</sub>\n\n{table}"


def _languages(stats: ProfileStats) -> str:
    top = list(stats["languages"].items())[:MAX_LANGUAGES]
    if not top:
        return ""
    width = max(len(name) for name, _ in top)
    lines = []
    for name, percent in top:
        filled = min(LANGUAGE_BAR_LENGTH, round(percent / 100 * LANGUAGE_BAR_LENGTH))
        bar = "█" * filled + "░" * (LANGUAGE_BAR_LENGTH - filled)
        lines.append(f"{name:<{width}}  {bar}  {percent:5.1f} %")
    return "### 💻 Most used languages\n\n```text\n" + "\n".join(lines) + "\n```"


def heat_level(count: int, maximum: int) -> int:
    """Niveau 0 à 4 : 0 = aucun commit, 4 = quart supérieur de l'activité."""
    if count <= 0 or maximum <= 0:
        return 0
    return min(4, -(-4 * count // maximum))


def _activity(stats: ProfileStats) -> str:
    heatmap = stats["activity_heatmap"]
    buckets = [
        [sum(heatmap.get(day, {}).get(hour, 0) for hour in range(start, start + 3)) for start in range(0, 24, 3)]
        for day in range(7)
    ]
    maximum = max(max(row) for row in buckets)
    if maximum == 0:
        return ""
    header = "     " + "".join(f"{start:02d}  " for start in range(0, 24, 3)).rstrip()
    rows = [
        f"{_DAYS[day]}  " + "  ".join(_HEAT_LEVELS[heat_level(c, maximum)] for c in row)
        for day, row in enumerate(buckets)
    ]
    legend = "⬜ none  🟩 low  🟨 medium  🟧 high  🟥 very high"
    body = "\n".join([header, *rows, "", legend])
    return f"### 🔥 When I commit (UTC, 3-hour slots)\n\n```text\n{body}\n```"


def _contact_section(profile: Profile) -> str:
    links = []
    if profile.linkedin:
        links.append(f"[{badge_markdown(Badge('LinkedIn', '0A66C2', '', 'white'))}]({profile.linkedin})")
    if profile.email:
        links.append(f"[{badge_markdown(Badge('Email', 'D14836', '', 'white'))}](mailto:{profile.email})")
    if not links:
        return ""
    return "## 📫 Contact\n\n" + "\n".join(links)


def _footer(username: str, updated_on: date) -> str:
    if not _USERNAME.match(username):
        raise ProfileConfigError("Nom d'utilisateur GitHub invalide")
    views = (
        f'<img src="https://komarev.com/ghpvc/?username={quote(username)}'
        '&style=flat-square&color=blue" alt="Profile views" />'
    )
    note = f"<sub>Stats updated automatically on {updated_on.isoformat()} (UTC).</sub>"
    return f'<div align="center">\n\n{views}\n\n{note}\n\n</div>'


def render_readme(
    profile: Profile,
    stats: ProfileStats,
    *,
    username: str,
    updated_on: date,
    sections: Sequence[str] = ALLOWED_SECTIONS,
) -> str:
    """Assemble le README complet ; les sections vides sont omises."""
    renderers = {
        "about": lambda: _about(profile),
        "stack": lambda: _stack(profile),
        "stats": lambda: _stats(stats),
        "languages": lambda: _languages(stats),
        "activity": lambda: _activity(stats),
        "contact": lambda: _contact_section(profile),
    }
    blocks = [_header(profile)]
    blocks += [block for name in sections if (block := renderers[name]())]
    return "\n\n".join(blocks) + "\n\n---\n\n" + _footer(username, updated_on) + "\n"
