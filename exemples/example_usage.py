#!/usr/bin/env python3
"""
Exemples d'Utilisation de GitHub Stats Automation
=================================================

Ce fichier contient des exemples pratiques d'utilisation de la bibliothèque.
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from datetime import UTC, datetime

from src.cache_manager import CacheManager
from src.config import Config
from src.github_stats import GitHubStatsPrivate, build_heatmap
from src.rate_limiter import RateLimitHandler
from src.readme_renderer import load_profile, render_readme

# ============================================================================
# EXEMPLE 1 : Utilisation Basique
# ============================================================================


def example_basic():
    """Exemple basique de récupération de statistiques"""
    print("\n" + "=" * 70)
    print("EXEMPLE 1 : Utilisation Basique")
    print("=" * 70)

    # Initialiser avec token et username
    stats_manager = GitHubStatsPrivate(token="ghp_your_token_here", username="your_username")

    # Calculer toutes les stats
    stats = stats_manager.calculate_all_stats()

    # Afficher quelques résultats
    print("\n📊 Résultats:")
    print(f"   Repos total: {stats['total_repos']}")
    print(f"   Stars: {stats['stars']}")
    print(f"   Commits: {stats['commits_last_year']}")
    print(f"   PRs: {stats['prs']['total']}")


# ============================================================================
# EXEMPLE 2 : Utilisation avec Configuration Personnalisée
# ============================================================================


def example_custom_config():
    """Exemple avec configuration personnalisée"""
    print("\n" + "=" * 70)
    print("EXEMPLE 2 : Configuration Personnalisée")
    print("=" * 70)

    # Créer une configuration
    config = Config("configs/config.yaml")

    # Modifier des valeurs
    config.set("stats.days_back", 180)  # 6 mois au lieu d'un an
    config.set("cache.enabled", False)  # Désactiver le cache

    # Initialiser avec la config
    stats_manager = GitHubStatsPrivate(token="ghp_your_token_here", username="your_username", config=config)

    stats = stats_manager.calculate_all_stats()

    print(f"\n📊 Stats sur {config.get('stats.days_back')} jours:")
    print(f"   Commits: {stats['commits_last_year']}")


# ============================================================================
# EXEMPLE 3 : Récupération de Statistiques Spécifiques
# ============================================================================


def example_specific_stats():
    """Exemple de récupération de statistiques spécifiques"""
    print("\n" + "=" * 70)
    print("EXEMPLE 3 : Statistiques Spécifiques")
    print("=" * 70)

    stats_manager = GitHubStatsPrivate(token="ghp_your_token_here", username="your_username")

    # Récupérer seulement les repos
    repos = stats_manager.get_all_repos()
    print(f"\n📦 Nombre de repos: {len(repos)}")

    # Compter les étoiles
    stars = sum(r["stargazers_count"] for r in repos)
    print(f"⭐ Total étoiles: {stars}")

    # Analyser les langages
    languages = stats_manager.get_language_stats(repos)
    print("\n💻 Top 3 langages:")
    for lang, percentage in list(languages.items())[:3]:
        print(f"   {lang}: {percentage}%")


# ============================================================================
# EXEMPLE 4 : Gestion du Cache
# ============================================================================


def example_cache_usage():
    """Exemple d'utilisation du cache"""
    print("\n" + "=" * 70)
    print("EXEMPLE 4 : Gestion du Cache")
    print("=" * 70)

    cache = CacheManager(".cache")

    # Sauvegarder des données
    data = {"repos": 42, "stars": 156}
    cache.set("my_stats", data)
    print("\n✅ Données sauvegardées en cache")

    # Récupérer depuis le cache
    cached_data = cache.get("my_stats", max_age_hours=24)
    if cached_data:
        print(f"📦 Données en cache: {cached_data}")

    # Informations sur le cache
    info = cache.get_cache_info()
    print("\n📊 Informations du cache:")
    print(f"   Fichiers: {info['total_files']}")
    print(f"   Taille: {info['total_size_mb']} MB")

    # Nettoyer le cache
    count = cache.clear()
    print(f"\n🧹 {count} fichier(s) supprimé(s)")


# ============================================================================
# EXEMPLE 5 : Vérification du Rate Limit
# ============================================================================


def example_rate_limit():
    """Exemple de gestion du rate limit"""
    print("\n" + "=" * 70)
    print("EXEMPLE 5 : Rate Limit")
    print("=" * 70)

    headers = {"Authorization": "token ghp_your_token_here", "Accept": "application/vnd.github.v3+json"}

    limiter = RateLimitHandler(headers)

    # Vérifier le rate limit
    rate_info = limiter.check_rate_limit()
    print("\n📊 État du Rate Limit:")
    print(f"   Restantes: {rate_info['remaining']}/{rate_info['limit']}")
    print(f"   Reset à: {rate_info['reset_datetime'].strftime('%H:%M:%S')}")

    # Attendre si nécessaire
    waited = limiter.wait_if_needed()
    if waited:
        print("⏳ On a attendu le reset du rate limit")
    else:
        print("✅ Pas besoin d'attendre")


# ============================================================================
# EXEMPLE 6 : Génération de README Personnalisé
# ============================================================================


def example_custom_readme():
    """Exemple de génération de README personnalisé"""
    print("\n" + "=" * 70)
    print("EXEMPLE 6 : README Personnalisé")
    print("=" * 70)

    # Configurer les sections à inclure
    config = Config()
    sections = ["stats", "languages"]

    stats_manager = GitHubStatsPrivate(token="ghp_your_token_here", username="your_username", config=config)

    stats = stats_manager.calculate_all_stats()
    readme = render_readme(
        load_profile(config.get("profile")),
        stats,
        username="your_username",
        updated_on=datetime.now(UTC).date(),
        sections=sections,
    )

    # Sauvegarder localement
    with open("README_custom.md", "w", encoding="utf-8") as f:
        f.write(readme)

    print("\n✅ README personnalisé généré dans README_custom.md")


# ============================================================================
# EXEMPLE 7 : Export des Statistiques en JSON
# ============================================================================


def example_export_json():
    """Exemple d'export des statistiques en JSON"""
    print("\n" + "=" * 70)
    print("EXEMPLE 7 : Export JSON")
    print("=" * 70)

    stats_manager = GitHubStatsPrivate(token="ghp_your_token_here", username="your_username")

    stats = stats_manager.calculate_all_stats()

    # Sauvegarder en JSON
    output_file = "stats/github_stats.json"
    Path("stats").mkdir(exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Statistiques exportées dans {output_file}")
    print(f"📊 Taille du fichier: {Path(output_file).stat().st_size} bytes")


# ============================================================================
# EXEMPLE 8 : Analyse des Langages
# ============================================================================


def example_language_analysis():
    """Exemple d'analyse détaillée des langages"""
    print("\n" + "=" * 70)
    print("EXEMPLE 8 : Analyse des Langages")
    print("=" * 70)

    stats_manager = GitHubStatsPrivate(token="ghp_your_token_here", username="your_username")

    repos = stats_manager.get_all_repos()
    languages = stats_manager.get_language_stats(repos)

    print("\n💻 Répartition des langages:")
    print("=" * 50)

    for lang, percentage in languages.items():
        # Créer une barre visuelle
        bar_length = int(percentage / 2)
        bar = "█" * bar_length
        print(f"{lang:<20} {bar} {percentage:.1f}%")


# ============================================================================
# EXEMPLE 9 : Heatmap d'Activité
# ============================================================================


def example_activity_heatmap():
    """Exemple de génération de heatmap d'activité"""
    print("\n" + "=" * 70)
    print("EXEMPLE 9 : Heatmap d'Activité")
    print("=" * 70)

    config = Config()
    config.set("stats.include_heatmap", True)

    stats_manager = GitHubStatsPrivate(token="ghp_your_token_here", username="your_username", config=config)

    repos = stats_manager.get_all_repos()
    heatmap = build_heatmap(stats_manager.get_commit_dates(repos))

    # Trouver l'heure la plus active
    max_commits = 0
    max_day = 0
    max_hour = 0

    for day in range(7):
        for hour in range(24):
            commits = heatmap.get(day, {}).get(hour, 0)
            if commits > max_commits:
                max_commits = commits
                max_day = day
                max_hour = hour

    days = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
    print("\n🔥 Période la plus active:")
    print(f"   {days[max_day]} à {max_hour}h avec {max_commits} commits")


# ============================================================================
# EXEMPLE 10 : Mode Dry-Run (Sans Publication)
# ============================================================================


def example_dry_run():
    """Exemple de mode dry-run pour tester sans publier"""
    print("\n" + "=" * 70)
    print("EXEMPLE 10 : Mode Dry-Run")
    print("=" * 70)

    stats_manager = GitHubStatsPrivate(token="ghp_your_token_here", username="your_username")

    # Calculer les stats
    stats = stats_manager.calculate_all_stats()

    # Générer le README
    readme = render_readme(
        load_profile(stats_manager.config.get("profile")),
        stats,
        username="your_username",
        updated_on=datetime.now(UTC).date(),
    )

    # Afficher un aperçu au lieu de publier
    print("\n📝 Aperçu du README (50 premières lignes):")
    print("=" * 70)

    lines = readme.split("\n")
    for line in lines[:50]:
        print(line)

    if len(lines) > 50:
        print(f"\n... ({len(lines) - 50} lignes supplémentaires)")

    print("\n✅ Mode dry-run : Aucune publication sur GitHub")


# ============================================================================
# Point d'Entrée
# ============================================================================


def main():
    """Exécute tous les exemples (commentez ceux que vous ne voulez pas)"""
    print("\n" + "=" * 70)
    print("EXEMPLES D'UTILISATION - GITHUB STATS AUTOMATION".center(70))
    print("=" * 70)

    print("\n⚠️  Note: Ces exemples nécessitent un token GitHub valide")
    print("   Modifiez les valeurs 'ghp_your_token_here' et 'your_username'")
    print("   avant d'exécuter ce script.")

    # Décommentez les exemples que vous voulez exécuter

    # example_basic()
    # example_custom_config()
    # example_specific_stats()
    # example_cache_usage()
    # example_rate_limit()
    # example_custom_readme()
    # example_export_json()
    # example_language_analysis()
    # example_activity_heatmap()
    # example_dry_run()

    print("\n" + "=" * 70)
    print("✅ Exemples terminés!")
    print("=" * 70)


if __name__ == "__main__":
    main()
