#!/usr/bin/env python3
"""
Script Principal - Mise à Jour des Statistiques GitHub
========================================================

Ce script est le point d'entrée principal pour mettre à jour
les statistiques GitHub du profil.

Fonctionnalités:
- Chargement de la configuration
- Validation des credentials
- Récupération des statistiques
- Génération du README (contenu : section ``profile`` de configs/config.yaml)
- Sauvegarde des données en JSON (optionnel)

Le README est écrit localement ; sa publication est faite par le workflow
GitHub Actions (commit avec GITHUB_TOKEN). Le jeton de stats ne sert qu'en lecture.

Usage:
    python scripts/update_stats.py [options]

Options:
    --dry-run : Afficher un aperçu du README généré
    --no-cache : Désactiver le cache
    --config PATH : Chemin vers le fichier de configuration
    --output PATH : Fichier de sortie pour le README
    --verbose : Mode verbeux (plus de logs)

Exemples:
    python scripts/update_stats.py
    python scripts/update_stats.py --dry-run
    python scripts/update_stats.py --no-cache --verbose
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.cache_manager import CacheManager  # noqa: E402 (après sys.path)
from src.config import Config  # noqa: E402
from src.env_loader import find_dotenv, load_dotenv  # noqa: E402
from src.github_stats import GitHubAuthError, GitHubStatsPrivate  # noqa: E402
from src.readme_renderer import ProfileConfigError, load_profile, load_sections, render_readme  # noqa: E402
from src.utils import format_number, token_fingerprint, validate_github_token, validate_github_username  # noqa: E402

# Charger le .env automatiquement (usage local ; en CI les variables viennent des secrets)
env_file = find_dotenv()
if env_file:
    load_dotenv(str(env_file))
    print(f"🔐 Fichier .env chargé depuis: {env_file}")
else:
    print("⚠️  Aucun fichier .env trouvé (utilisation des variables d'environnement système)")


def parse_arguments():
    """
    Parse les arguments de la ligne de commande

    Returns:
        Arguments parsés
    """
    parser = argparse.ArgumentParser(
        description="Met à jour les statistiques GitHub du profil",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples d'utilisation:
  %(prog)s                          # Mode normal
  %(prog)s --dry-run                # Tester sans publier
  %(prog)s --no-cache --verbose     # Sans cache, mode verbeux
  %(prog)s --config custom.yaml     # Utiliser une config personnalisée
        """,
    )

    parser.add_argument("--dry-run", action="store_true", help="Afficher un aperçu du README généré")

    parser.add_argument(
        "--no-cache", action="store_true", help="Désactiver le cache (force la récupération depuis l'API)"
    )

    parser.add_argument(
        "--config",
        type=str,
        default="configs/config.yaml",
        help="Chemin vers le fichier de configuration (défaut: configs/config.yaml)",
    )

    parser.add_argument("--output", type=str, help="Fichier de sortie pour le README (défaut: README.md)")

    parser.add_argument("--verbose", "-v", action="store_true", help="Mode verbeux (affiche plus d'informations)")

    parser.add_argument("--clear-cache", action="store_true", help="Nettoyer le cache avant de commencer")

    parser.add_argument("--json", type=str, help="Sauvegarder les stats en JSON dans ce fichier")

    parser.add_argument("--show-config", action="store_true", help="Afficher la configuration et quitter")

    return parser.parse_args()


def validate_credentials(token: str, username: str) -> tuple[bool, list[str]]:
    """
    Valide les credentials GitHub

    Args:
        token: Token d'authentification
        username: Nom d'utilisateur

    Returns:
        Tuple (is_valid, errors)
    """
    errors = []

    if not token:
        errors.append("❌ Token GitHub manquant (GITHUB_TOKEN)")
    elif not validate_github_token(token):
        errors.append("⚠️  Format du token GitHub invalide")

    if not username:
        errors.append("❌ Username GitHub manquant (GITHUB_USERNAME)")
    elif not validate_github_username(username):
        errors.append("⚠️  Format du username GitHub invalide")

    return len(errors) == 0, errors


def print_banner():
    """Affiche la bannière du script"""
    banner = """
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          🚀 GITHUB STATS AUTOMATION 2025                     ║
║                                                              ║
║          Mise à jour automatique des statistiques           ║
║          incluant les dépôts privés                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_summary(stats: dict):
    """
    Affiche un résumé des statistiques

    Args:
        stats: Dictionnaire des statistiques
    """
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DES STATISTIQUES".center(70))
    print("=" * 70)

    print(f"\n{'📦 DÉPÔTS':<40}")
    print(f"   Total                : {format_number(stats['total_repos']):>15}")
    print(f"   └─ Publics           : {format_number(stats['public_repos']):>15}")
    print(f"   └─ Privés            : {format_number(stats['private_repos']):>15}")

    print(f"\n{'⭐ ÉTOILES':<40}")
    print(f"   Total                : {format_number(stats['stars']):>15}")

    print(f"\n{'📝 COMMITS':<40}")
    print(f"   Derniers {stats['period_days']} jours   : {format_number(stats['commits_last_year']):>15}")

    print(f"\n{'🔀 PULL REQUESTS':<40}")
    print(f"   Total                : {format_number(stats['prs']['total']):>15}")
    print(f"   ├─ Ouvertes          : {format_number(stats['prs']['open']):>15}")
    print(f"   ├─ Mergées           : {format_number(stats['prs']['merged']):>15}")
    print(f"   └─ Fermées sans merge: {format_number(stats['prs']['closed_unmerged']):>15}")

    if stats["languages"]:
        print(f"\n{'💻 TOP 5 LANGAGES':<40}")
        for i, (lang, percent) in enumerate(list(stats["languages"].items())[:5], 1):
            print(f"   {i}. {lang:<25} : {percent:>10.1f}%")

    print(f"\n{'🤝 ACTIVITÉ':<40}")
    print(f"   Dépôts actifs        : {format_number(stats['active_repos']):>15}")

    print("\n" + "=" * 70)


def save_stats_to_json(stats: dict, filepath: str):
    """
    Sauvegarde les statistiques en JSON

    Args:
        stats: Statistiques à sauvegarder
        filepath: Chemin du fichier JSON
    """
    try:
        output_path = Path(filepath)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Convertir les données non-sérialisables
        stats_copy = dict(stats)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(stats_copy, f, indent=2, ensure_ascii=False)

        print(f"✅ Statistiques sauvegardées dans: {filepath}")

    except Exception as e:
        print(f"⚠️  Erreur lors de la sauvegarde JSON: {e}")


def save_readme_to_file(content: str, filepath: str):
    """
    Sauvegarde le README dans un fichier local

    Args:
        content: Contenu du README
        filepath: Chemin du fichier
    """
    # Pas de capture d'exception : un échec d'écriture doit faire échouer le workflow
    output_path = Path(filepath)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8", newline="\n")
    print(f"✅ README sauvegardé dans: {filepath}")


def main():
    """Point d'entrée principal du script"""

    # Parser les arguments
    args = parse_arguments()

    # Afficher la bannière
    print_banner()

    # Charger la configuration
    try:
        config = Config(args.config)
        print(f"✅ Configuration chargée depuis: {args.config}")
    except Exception as e:
        print(f"❌ Erreur lors du chargement de la configuration: {e}")
        return 1

    # Afficher la config si demandé
    if args.show_config:
        config.display()
        return 0

    # Appliquer les options de ligne de commande
    if args.no_cache:
        config.set("cache.enabled", False)
        print("🔧 Cache désactivé")

    if args.verbose:
        config.set("logging.level", "DEBUG")
        print("🔧 Mode verbeux activé")

    # Récupérer les credentials
    token = config.get("github.token")
    username = config.get("github.username")

    # Valider les credentials
    is_valid, errors = validate_credentials(token, username)
    if not is_valid:
        print("\n❌ ERREUR: Credentials invalides\n")
        for error in errors:
            print(f"   {error}")

        print("\n💡 Configuration requise:")
        print("   export GITHUB_TOKEN='votre_token'")
        print("   export GITHUB_USERNAME='votre_username'")
        print("\n🔑 Créez un token sur: https://github.com/settings/personal-access-tokens")
        print("   Fine-grained, lecture seule : Metadata, Contents, Pull requests")
        return 1

    # Valider la configuration complète
    is_valid, errors = config.validate()
    if not is_valid:
        print("\n⚠️  Avertissements de configuration:\n")
        for error in errors:
            print(f"   {error}")
        print()

    print(f"\n🎯 Utilisateur cible: {username}")
    print(f"🔑 Token fourni (empreinte {token_fingerprint(token)})")

    # Valider le contenu du profil avant tout appel API
    try:
        profile = load_profile(config.get("profile"))
        sections = load_sections(config.get("readme.sections"))
    except ProfileConfigError as e:
        print(f"❌ Contenu du profil invalide dans {args.config}: {e}")
        return 1

    # Nettoyer le cache si demandé
    if args.clear_cache:
        cache = CacheManager(config.get("cache.directory", ".cache"))
        count = cache.clear()
        print(f"🧹 Cache nettoyé: {count} fichier(s) supprimé(s)")

    # Initialiser le gestionnaire de stats
    try:
        stats_manager = GitHubStatsPrivate(token, username, config)
    except Exception as e:
        print(f"❌ Erreur lors de l'initialisation: {e}")
        return 1

    # Calculer les statistiques
    print("\n" + "=" * 70)
    print("🔍 RÉCUPÉRATION DES STATISTIQUES...")
    print("=" * 70 + "\n")

    try:
        stats = stats_manager.calculate_all_stats()
    except GitHubAuthError as e:
        print(f"\n❌ {e}")
        return 1
    except Exception as e:
        print(f"\n❌ Erreur lors du calcul des statistiques: {e}")
        return 1

    # Afficher le résumé
    print_summary(stats)

    # Sauvegarder les stats en JSON si demandé
    if args.json:
        save_stats_to_json(stats, args.json)
    elif config.get("output.save_json", False):
        json_file = config.get("output.json_file", "stats/github_stats.json")
        save_stats_to_json(stats, json_file)

    # Générer le README
    print("\n📝 Génération du README...")
    try:
        readme_content = render_readme(
            profile, stats, username=username, updated_on=datetime.now(UTC).date(), sections=sections
        )
    except ProfileConfigError as e:
        print(f"❌ Erreur lors de la génération du README: {e}")
        return 1

    # Sauvegarder le README localement
    output_file = args.output or config.get("output.readme_file", "README.md")
    save_readme_to_file(readme_content, output_file)

    if args.dry_run:
        print("\n" + "=" * 70)
        print("🔍 Aperçu du README (30 premières lignes)".center(70))
        print("=" * 70)
        lines = readme_content.split("\n")
        print("\n".join(lines[:30]))
        if len(lines) > 30:
            print(f"\n... ({len(lines) - 30} lignes supplémentaires)")

    print(f"\n✅ README généré : {output_file} (publication : commit du workflow)")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interruption par l'utilisateur (Ctrl+C)")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
