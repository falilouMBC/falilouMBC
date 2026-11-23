"""Tests du rendu du README et de la validation du contenu du profil."""

from __future__ import annotations

import copy
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml

from src.readme_renderer import (
    ALLOWED_SECTIONS,
    Badge,
    ProfileConfigError,
    ProfileStats,
    badge_markdown,
    heat_level,
    load_profile,
    load_sections,
    render_readme,
)

CONFIG_PATH = Path(__file__).resolve().parent.parent / "configs" / "config.yaml"
TODAY = date(2026, 11, 23)


@pytest.fixture
def raw_profile() -> dict[str, Any]:
    return {
        "name": "Falilou",
        "headline": "Fullstack Developer · Solution Architect",
        "location": "Dakar, Senegal",
        "summary": "I build secure banking applications.",
        "about": ["🏦 Banking apps", "🔐 Security by default"],
        "stack": [
            {"label": "TypeScript", "color": "3178C6", "logo": "typescript"},
            {"label": "Oracle Database", "color": "C74634"},
        ],
        "learning": [{"label": "Kubernetes", "color": "326CE5", "logo": "kubernetes"}],
        "contact": {"linkedin": "https://www.linkedin.com/in/falilouMBC", "email": "falilou.dev@example.org"},
    }


@pytest.fixture
def stats() -> ProfileStats:
    heatmap = {day: dict.fromkeys(range(24), 0) for day in range(7)}
    heatmap[0][9] = 2
    heatmap[0][10] = 2  # même créneau 09-11 que 9 h : doit être additionné
    heatmap[4][15] = 1
    return {
        "total_repos": 36,
        "public_repos": 20,
        "private_repos": 16,
        "stars": 7,
        "commits_last_year": 1363,
        "active_repos": 19,
        "prs": {"total": 76, "open": 9, "merged": 67, "closed_unmerged": 0},
        "languages": {
            "TypeScript": 53.6,
            "Java": 17.3,
            "Python": 11.0,
            "PHP": 5.7,
            "Blade": 4.4,
            "JS": 2.8,
            "HTML": 2.1,
        },
        "activity_heatmap": heatmap,
        "period_days": 365,
    }


def render(raw: dict[str, Any], stats: ProfileStats, **kwargs: Any) -> str:
    return render_readme(load_profile(raw), stats, username="falilouMBC", updated_on=TODAY, **kwargs)


# ---------------------------------------------------------------- validation


def test_shipped_config_is_valid() -> None:
    data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    profile = load_profile(data["profile"])
    assert profile.name == "Falilou"
    assert profile.stack
    assert load_sections(data["readme"]["sections"]) == ALLOWED_SECTIONS


def test_load_profile_valid(raw_profile: dict[str, Any]) -> None:
    profile = load_profile(raw_profile)
    assert profile.stack[1] == Badge("Oracle Database", "C74634", "", "white")
    assert profile.about == ("🏦 Banking apps", "🔐 Security by default")


def test_optional_fields_default_to_empty() -> None:
    profile = load_profile({"name": "Falilou", "headline": "Dev"})
    assert (profile.about, profile.stack, profile.linkedin, profile.email) == ((), (), "", "")


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (("name",), "  ", "profile.name est obligatoire"),
        (("headline",), 42, "profile.headline doit être une chaîne"),
        (("about",), "pas une liste", "profile.about"),
        (("about",), ["ok", ""], "profile.about"),
        (("stack",), {"label": "x"}, "profile.stack doit être une liste"),
        (("stack", 0), "TypeScript", r"profile.stack\[0\] doit être un dictionnaire"),
        (("stack", 0, "color"), "#3178C6", "couleur hexadécimale"),
        (("stack", 0, "logo"), "Type Script", "identifiant simple-icons"),
        (("stack", 0, "logo_color"), "#fff", "logo_color invalide"),
        (("contact",), ["x"], "profile.contact doit être un dictionnaire"),
        (("contact", "linkedin"), "http://evil.example/in/x", "linkedin"),
        (("contact", "email"), "pas-un-email", "email invalide"),
    ],
)
def test_load_profile_rejects_invalid(
    raw_profile: dict[str, Any], path: tuple[str | int, ...], value: object, message: str
) -> None:
    raw = copy.deepcopy(raw_profile)
    target: Any = raw
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ProfileConfigError, match=message):
        load_profile(raw)


def test_load_profile_rejects_non_mapping() -> None:
    with pytest.raises(ProfileConfigError, match="profile doit être un dictionnaire"):
        load_profile(None)


def test_load_sections() -> None:
    assert load_sections(None) == ALLOWED_SECTIONS
    assert load_sections(["stats"]) == ("stats",)
    with pytest.raises(ProfileConfigError, match="inconnues : issues"):
        load_sections(["stats", "issues"])
    with pytest.raises(ProfileConfigError, match="liste de chaînes"):
        load_sections("stats")


# --------------------------------------------------------------------- rendu


def test_badge_encoding() -> None:
    assert badge_markdown(Badge("C#", "239120", "", "white")) == (
        "![C#](https://img.shields.io/badge/C%23-239120?style=for-the-badge)"
    )
    url = badge_markdown(Badge("Spring-Boot_3 [x]", "6DB33F", "springboot", "white"))
    assert "Spring--Boot__3%20%5Bx%5D-6DB33F" in url
    assert url.startswith(r"![Spring-Boot_3 \[x\]]")
    assert url.endswith("&logo=springboot&logoColor=white)")


@pytest.mark.parametrize(
    ("count", "maximum", "level"), [(0, 4, 0), (1, 0, 0), (1, 4, 1), (2, 4, 2), (3, 4, 3), (4, 4, 4)]
)
def test_heat_level(count: int, maximum: int, level: int) -> None:
    assert heat_level(count, maximum) == level


def test_render_full_readme(raw_profile: dict[str, Any], stats: ProfileStats) -> None:
    readme = render(raw_profile, stats)
    assert readme.startswith("# Hi, I'm Falilou 👋\n\n**Fullstack Developer · Solution Architect** · 📍 Dakar, Senegal")
    assert "- 🔐 Security by default" in readme
    assert "![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript" in readme
    assert "**Currently learning:** ![Kubernetes]" in readme
    assert "| 📝 Commits (last 12 months) | **1,363** |" in readme
    assert "| 🔀 Pull requests | **76** (67 merged · 9 open) |" in readme
    assert "**36** (20 public · 16 private)" in readme
    assert "closed" not in readme.split("## 📊")[1].split("###")[0]
    assert "HTML" not in readme  # top 6 langages seulement
    assert "TypeScript  ████████████████  " in readme.replace("░", "")  # 53,6 % de 30 → 16 blocs
    assert "(mailto:falilou.dev@example.org)" in readme
    assert "(https://www.linkedin.com/in/falilouMBC)" in readme
    assert "Stats updated automatically on 2026-11-23 (UTC)." in readme
    assert readme.endswith("</div>\n") and not readme.endswith("\n\n")


def test_activity_sums_three_hour_slots(raw_profile: dict[str, Any], stats: ProfileStats) -> None:
    rows = render(raw_profile, stats, sections=("activity",)).split("```text\n")[1].splitlines()
    assert rows[0].startswith("     00  03  06  09")
    assert rows[1] == "Mon  ⬜  ⬜  ⬜  🟥  ⬜  ⬜  ⬜  ⬜"  # 9 h + 10 h = 4 → maximum
    assert rows[5] == "Fri  ⬜  ⬜  ⬜  ⬜  ⬜  🟩  ⬜  ⬜"


def test_closed_prs_and_custom_period(raw_profile: dict[str, Any], stats: ProfileStats) -> None:
    stats["prs"]["closed_unmerged"] = 2
    stats["period_days"] = 90
    readme = render(raw_profile, stats, sections=("stats",))
    assert "· 2 closed)" in readme
    assert "Commits (last 90 days)" in readme
    assert "Tech stack" not in readme and "Contact" not in readme


def test_empty_sections_are_omitted(stats: ProfileStats) -> None:
    stats["languages"] = {}
    stats["activity_heatmap"] = {day: dict.fromkeys(range(24), 0) for day in range(7)}
    readme = render({"name": "Falilou", "headline": "Dev"}, stats)
    for title in ("About me", "Tech stack", "Most used languages", "When I commit", "Contact"):
        assert title not in readme
    assert "GitHub activity" in readme


def test_text_is_html_escaped(raw_profile: dict[str, Any], stats: ProfileStats) -> None:
    raw_profile["summary"] = "<script>alert(1)</script> & co"
    readme = render(raw_profile, stats)
    assert "&lt;script&gt;alert(1)&lt;/script&gt; &amp; co" in readme
    assert "<script>" not in readme


def test_invalid_username_is_rejected(raw_profile: dict[str, Any], stats: ProfileStats) -> None:
    with pytest.raises(ProfileConfigError, match="utilisateur GitHub invalide"):
        render_readme(load_profile(raw_profile), stats, username="x&y=1", updated_on=TODAY)
