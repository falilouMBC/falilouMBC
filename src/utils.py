#!/usr/bin/env python3
"""
Utilities Module
================

Fonctions utilitaires diverses pour le projet GitHub Stats.

Inclut:
- Formatage de nombres
- Génération de graphiques ASCII
- Formatage de dates
- Validation d'entrées
- Helpers pour les statistiques
"""

import hashlib
import re
from datetime import datetime, timedelta
from typing import Any


def format_number(num: int) -> str:
    """
    Formate un nombre avec des séparateurs de milliers

    Args:
        num: Nombre à formater

    Returns:
        Nombre formaté avec espaces (ex: 1 234 567)

    Example:
        >>> format_number(1234567)
        '1 234 567'
    """
    return f"{num:,}".replace(",", " ")


def format_percentage(value: float, total: float) -> str:
    """
    Calcule et formate un pourcentage

    Args:
        value: Valeur
        total: Total

    Returns:
        Pourcentage formaté (ex: "42.5%")
    """
    if total == 0:
        return "0.0%"

    percentage = (value / total) * 100
    return f"{percentage:.1f}%"


def format_duration(seconds: int) -> str:
    """
    Formate une durée en secondes en format lisible

    Args:
        seconds: Durée en secondes

    Returns:
        Durée formatée (ex: "2h 30m 15s")
    """
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60

    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")

    return " ".join(parts)


def format_date(date: datetime, format: str = "%d/%m/%Y") -> str:
    """
    Formate une date

    Args:
        date: Date à formater
        format: Format de sortie

    Returns:
        Date formatée
    """
    return date.strftime(format)


def format_relative_time(date: datetime) -> str:
    """
    Formate une date en temps relatif (ex: "il y a 2 jours")

    Args:
        date: Date à formater

    Returns:
        Temps relatif en français
    """
    now = datetime.now()
    diff = now - date

    if diff.days > 365:
        years = diff.days // 365
        return f"il y a {years} an{'s' if years > 1 else ''}"
    elif diff.days > 30:
        months = diff.days // 30
        return f"il y a {months} mois"
    elif diff.days > 0:
        return f"il y a {diff.days} jour{'s' if diff.days > 1 else ''}"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"il y a {hours} heure{'s' if hours > 1 else ''}"
    elif diff.seconds > 60:
        minutes = diff.seconds // 60
        return f"il y a {minutes} minute{'s' if minutes > 1 else ''}"
    else:
        return "à l'instant"


def generate_ascii_bar(value: int, max_value: int, length: int = 50, char: str = "█") -> str:
    """
    Génère une barre ASCII pour visualiser une valeur

    Args:
        value: Valeur à représenter
        max_value: Valeur maximale (100%)
        length: Longueur de la barre en caractères
        char: Caractère à utiliser pour la barre

    Returns:
        Barre ASCII

    Example:
        >>> generate_ascii_bar(75, 100, 20)
        '███████████████░░░░░'
    """
    if max_value == 0:
        filled = 0
    else:
        filled = int((value / max_value) * length)

    filled = min(filled, length)  # Limiter à la longueur max
    empty = length - filled

    return char * filled + "░" * empty


def generate_language_bar(percentage: float, length: int = 40) -> str:
    """
    Génère une barre de pourcentage pour les langages

    Args:
        percentage: Pourcentage (0-100)
        length: Longueur de la barre

    Returns:
        Barre avec pourcentage
    """
    filled = int((percentage / 100) * length)
    bar = "█" * filled + "░" * (length - filled)
    return f"{bar} {percentage:.1f}%"


def create_stats_table(stats: dict[str, Any], title: str = "Statistiques") -> str:
    """
    Crée un tableau markdown des statistiques

    Args:
        stats: Dictionnaire de statistiques
        title: Titre du tableau

    Returns:
        Tableau markdown formaté
    """
    table = f"### {title}\n\n"
    table += "| Métrique | Valeur |\n"
    table += "|----------|--------|\n"

    for key, value in stats.items():
        # Formater la clé (convertir snake_case en Title Case)
        display_key = key.replace("_", " ").title()

        # Formater la valeur
        if isinstance(value, int):
            display_value = format_number(value)
        elif isinstance(value, float):
            display_value = f"{value:.2f}"
        else:
            display_value = str(value)

        table += f"| {display_key} | **{display_value}** |\n"

    return table


def generate_heatmap_ascii(heatmap: dict[int, dict[int, int]]) -> str:
    """
    Génère une heatmap ASCII de l'activité

    Args:
        heatmap: Dict {jour: {heure: nombre}}

    Returns:
        Heatmap en ASCII art
    """
    days = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]

    # Trouver la valeur max pour la normalisation
    max_value = 0
    for day_data in heatmap.values():
        max_value = max(max_value, max(day_data.values(), default=0))

    # Générer la heatmap
    result = "```\n"
    result += "       " + "".join(f"{h:>3}" for h in range(0, 24, 3)) + "\n"

    for day_num, day_name in enumerate(days):
        result += f"{day_name}   "

        for hour in range(0, 24, 3):
            count = heatmap.get(day_num, {}).get(hour, 0)

            # Choisir l'emoji selon l'intensité
            if count == 0:
                emoji = "⬜"
            elif count < max_value * 0.25:
                emoji = "🟩"
            elif count < max_value * 0.5:
                emoji = "🟨"
            elif count < max_value * 0.75:
                emoji = "🟧"
            else:
                emoji = "🟥"

            result += f" {emoji} "

        result += "\n"

    result += "\n⬜ Aucune  🟩 Faible  🟨 Moyenne  🟧 Élevée  🟥 Très élevée\n"
    result += "```\n"

    return result


def create_badge_url(label: str, message: str, color: str, style: str = "for-the-badge") -> str:
    """
    Crée une URL de badge shields.io

    Args:
        label: Label du badge
        message: Message/valeur du badge
        color: Couleur du badge
        style: Style du badge

    Returns:
        URL markdown du badge

    Example:
        >>> create_badge_url("Python", "3.10", "blue")
        '![Python](https://img.shields.io/badge/Python-3.10-blue?style=for-the-badge)'
    """
    # Encoder les espaces et caractères spéciaux
    label = label.replace(" ", "%20")
    message = str(message).replace(" ", "%20")

    url = f"https://img.shields.io/badge/{label}-{message}-{color}?style={style}"
    return f"![{label}]({url})"


def validate_github_token(token: str) -> bool:
    """
    Valide le format d'un token GitHub

    Args:
        token: Token à valider

    Returns:
        True si le format est valide
    """
    if not token:
        return False

    # Préfixes GitHub : github_pat_ (fine-grained, recommandé en lecture seule),
    # ghp_ (classique), gho_, ghu_, ghs_ (GITHUB_TOKEN d'Actions), ghr_
    patterns = [
        r"^github_pat_[a-zA-Z0-9_]{70,255}$",  # Fine-grained Personal Access Token
        r"^gh[pousr]_[a-zA-Z0-9]{36,251}$",  # Classic PAT, OAuth, user, server, refresh
    ]

    return any(re.match(pattern, token) for pattern in patterns)


def token_fingerprint(token: str) -> str:
    """Empreinte non réversible du jeton : seule information affichable dans les logs."""
    return "sha256:" + hashlib.sha256(token.encode()).hexdigest()[:8]


def validate_github_username(username: str) -> bool:
    """
    Valide le format d'un username GitHub

    Args:
        username: Username à valider

    Returns:
        True si le format est valide
    """
    if not username:
        return False

    # Username GitHub: alphanumerique + tirets, max 39 caractères
    pattern = r"^[a-zA-Z0-9](?:[a-zA-Z0-9]|-(?=[a-zA-Z0-9])){0,38}$"
    return bool(re.match(pattern, username))


def truncate_text(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """
    Tronque un texte s'il est trop long

    Args:
        text: Texte à tronquer
        max_length: Longueur maximale
        suffix: Suffixe à ajouter si tronqué

    Returns:
        Texte tronqué
    """
    if len(text) <= max_length:
        return text

    return text[: max_length - len(suffix)] + suffix


def calculate_growth(current: int, previous: int) -> tuple[int, float]:
    """
    Calcule la croissance entre deux valeurs

    Args:
        current: Valeur actuelle
        previous: Valeur précédente

    Returns:
        Tuple (différence, pourcentage)
    """
    diff = current - previous

    if previous == 0:
        percentage = 100.0 if current > 0 else 0.0
    else:
        percentage = (diff / previous) * 100

    return diff, percentage


def get_emoji_for_metric(metric: str) -> str:
    """
    Retourne un emoji approprié pour une métrique

    Args:
        metric: Nom de la métrique

    Returns:
        Emoji correspondant
    """
    emoji_map = {
        "stars": "⭐",
        "commits": "📝",
        "prs": "🔀",
        "pull_requests": "🔀",
        "issues": "❗",
        "repos": "📦",
        "repositories": "📦",
        "forks": "🍴",
        "followers": "👥",
        "contributions": "🤝",
        "languages": "💻",
        "code": "💻",
        "additions": "➕",
        "deletions": "➖",
        "changes": "🔄",
    }

    metric_lower = metric.lower()

    for key, emoji in emoji_map.items():
        if key in metric_lower:
            return emoji

    return "📊"


def safe_divide(numerator: float, denominator: float, default: float = 0.0) -> float:
    """
    Division sécurisée (évite la division par zéro)

    Args:
        numerator: Numérateur
        denominator: Dénominateur
        default: Valeur par défaut si division impossible

    Returns:
        Résultat de la division ou valeur par défaut
    """
    if denominator == 0:
        return default

    return numerator / denominator


def get_date_range(days: int) -> tuple[datetime, datetime]:
    """
    Obtient une plage de dates

    Args:
        days: Nombre de jours dans le passé

    Returns:
        Tuple (date_début, date_fin)
    """
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)

    return start_date, end_date


def chunk_list(lst: list, chunk_size: int) -> list[list]:
    """
    Divise une liste en chunks

    Args:
        lst: Liste à diviser
        chunk_size: Taille de chaque chunk

    Returns:
        Liste de chunks
    """
    return [lst[i : i + chunk_size] for i in range(0, len(lst), chunk_size)]
