#!/usr/bin/env python3
"""
Configuration Module
====================

Gère la configuration de l'application via fichier YAML.

Fonctionnalités:
- Chargement/sauvegarde de configuration YAML
- Valeurs par défaut
- Récupération de valeurs imbriquées
- Surcharge par variables d'environnement

La configuration permet de personnaliser:
- Paramètres GitHub (token, username)
- Options de cache
- Limite de rate limit
- Sections du README à générer
"""

import os
import re
from pathlib import Path
from typing import Any

import yaml


class Config:
    """
    Gestionnaire de configuration pour GitHub Stats

    Charge la configuration depuis un fichier YAML et permet
    d'accéder aux valeurs de manière simple et sécurisée.

    Les variables d'environnement surchargent les valeurs du fichier.

    Attributes:
        config_file (Path): Chemin vers le fichier de configuration
        data (Dict): Données de configuration chargées
    """

    ENV_PATTERN = re.compile(r"\$\{([^}:]+)(?::-(.*?))?\}")

    def __init__(self, config_file: str = "configs/config.yaml"):
        """
        Initialise la configuration

        Args:
            config_file: Chemin vers le fichier de configuration YAML
        """
        self.config_file = Path(config_file)
        self.data = {}
        self.load()

    def load(self):
        """
        Charge la configuration depuis le fichier YAML

        Si le fichier n'existe pas, crée une configuration par défaut.
        Applique ensuite les surcharges des variables d'environnement.
        """
        if self.config_file.exists():
            try:
                with open(self.config_file, encoding="utf-8") as f:
                    self.data = yaml.safe_load(f) or {}
                self.data = self._resolve_env_placeholders(self.data)
                print(f"✅ Configuration chargée depuis {self.config_file}")
            except yaml.YAMLError as e:
                # Échec explicite : un repli silencieux sur les valeurs par défaut
                # masquait une config invalide (le contenu du profil était ignoré).
                raise ValueError(f"Configuration invalide dans {self.config_file}: {e}") from e
        else:
            print("📝 Création de la configuration par défaut...")
            self.data = self.get_default_config()
            self.save()

        # Appliquer les surcharges d'environnement
        self._apply_env_overrides()

    def _resolve_env_placeholders(self, value: Any) -> Any:
        """
        Remplace les placeholders ${ENV_VAR:-default} par les valeurs d'environnement.
        """
        if isinstance(value, dict):
            return {k: self._resolve_env_placeholders(v) for k, v in value.items()}
        if isinstance(value, list):
            return [self._resolve_env_placeholders(item) for item in value]
        if isinstance(value, str):
            return self._replace_env_in_string(value)
        return value

    def _replace_env_in_string(self, text: str) -> str:
        def replacer(match: re.Match) -> str:
            var_name = match.group(1)
            default = match.group(2) if match.group(2) is not None else ""
            return os.getenv(var_name, default)

        return self.ENV_PATTERN.sub(replacer, text)

    def save(self):
        """
        Sauvegarde la configuration dans le fichier YAML

        Crée le répertoire parent si nécessaire.
        """
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)

            with open(self.config_file, "w", encoding="utf-8") as f:
                yaml.dump(self.data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

            print(f"✅ Configuration sauvegardée dans {self.config_file}")

        except Exception as e:
            print(f"❌ Erreur lors de la sauvegarde de la config: {e}")

    def get_default_config(self) -> dict[str, Any]:
        """
        Retourne la configuration par défaut

        Returns:
            Dictionnaire avec toutes les options par défaut
        """
        return {
            "github": {
                "token": os.getenv("GITHUB_TOKEN", ""),
                "username": os.getenv("GITHUB_USERNAME", ""),
                "api_url": "https://api.github.com",
            },
            "stats": {
                # Inclure les dépôts privés dans les statistiques
                "include_private": True,
                # Période d'analyse (jours)
                "days_back": 365,
                # Nombre de repos par page (max 100)
                "max_repos_per_page": 100,
                # Nombre maximum de pages de commits à analyser par repo
                "max_commits_pages": 10,
                # Inclure les statistiques de code (additions/suppressions)
                "include_code_changes": True,
                # Inclure les statistiques de langages
                "include_languages": True,
                # Inclure la heatmap d'activité
                "include_heatmap": True,
                # Inclure les contributions externes
                "include_external_contributions": False,
            },
            "cache": {
                # Activer le système de cache
                "enabled": True,
                # Durée de validité du cache (heures)
                "max_age_hours": 24,
                # Répertoire de cache
                "directory": ".cache",
                # Nettoyer automatiquement le vieux cache
                "auto_clean": True,
            },
            "rate_limit": {
                # Nombre minimum de requêtes avant d'attendre
                "min_remaining": 100,
                # Attendre automatiquement si limite atteinte
                "wait_on_limit": True,
                # Vérifier le rate limit toutes les N secondes
                "check_interval": 5,
            },
            "readme": {
                # Sections à inclure dans le README (voir src/readme_renderer.py)
                "sections": ["about", "stack", "stats", "languages", "activity", "contact"],
            },
            "logging": {
                # Niveau de log (DEBUG, INFO, WARNING, ERROR)
                "level": "INFO",
                # Répertoire des logs
                "directory": "logs",
                # Taille maximale d'un fichier log (Mo)
                "max_size_mb": 10,
                # Nombre de fichiers de backup
                "backup_count": 5,
            },
            "output": {
                # Fichier de sortie du README
                "readme_file": "README.md",
                # Sauvegarder aussi en JSON
                "save_json": True,
                # Fichier JSON de sortie
                "json_file": "stats/github_stats.json",
                # Afficher les stats dans la console
                "print_to_console": True,
            },
        }

    def _apply_env_overrides(self):
        """
        Applique les surcharges depuis les variables d'environnement

        Variables supportées:
        - GITHUB_TOKEN: Token d'authentification
        - GITHUB_USERNAME: Nom d'utilisateur GitHub
        - CACHE_ENABLED: Activer/désactiver le cache
        - LOG_LEVEL: Niveau de logging
        """
        # GitHub
        if os.getenv("GITHUB_TOKEN"):
            self.data["github"]["token"] = os.getenv("GITHUB_TOKEN")

        if os.getenv("GITHUB_USERNAME"):
            self.data["github"]["username"] = os.getenv("GITHUB_USERNAME")

        # Cache
        if os.getenv("CACHE_ENABLED"):
            self.data["cache"]["enabled"] = os.getenv("CACHE_ENABLED").lower() == "true"

        # Logging
        if os.getenv("LOG_LEVEL"):
            self.data["logging"]["level"] = os.getenv("LOG_LEVEL").upper()

    def get(self, key: str, default: Any = None) -> Any:
        """
        Récupère une valeur de configuration

        Supporte la notation par points pour les valeurs imbriquées.

        Args:
            key: Clé de configuration (ex: 'github.token' ou 'cache.enabled')
            default: Valeur par défaut si la clé n'existe pas

        Returns:
            La valeur de configuration ou la valeur par défaut

        Example:
            >>> config = Config()
            >>> token = config.get('github.token')
            >>> cache_enabled = config.get('cache.enabled', True)
        """
        keys = key.split(".")
        value = self.data

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Définit une valeur de configuration

        Args:
            key: Clé de configuration (notation par points supportée)
            value: Valeur à définir

        Example:
            >>> config = Config()
            >>> config.set('github.token', 'ghp_xxx')
            >>> config.save()
        """
        keys = key.split(".")
        data = self.data

        # Naviguer jusqu'à l'avant-dernière clé
        for k in keys[:-1]:
            if k not in data:
                data[k] = {}
            data = data[k]

        # Définir la valeur
        data[keys[-1]] = value

    def validate(self) -> tuple[bool, list[str]]:
        """
        Valide la configuration

        Vérifie que les paramètres obligatoires sont présents.

        Returns:
            Tuple (is_valid, errors)
            - is_valid: True si la config est valide
            - errors: Liste des erreurs trouvées

        Example:
            >>> config = Config()
            >>> is_valid, errors = config.validate()
            >>> if not is_valid:
            ...     for error in errors:
            ...         print(f"Erreur: {error}")
        """
        errors = []

        # Vérifier le token GitHub
        token = self.get("github.token")
        if not token:
            errors.append("Token GitHub manquant (GITHUB_TOKEN)")

        # Vérifier le username
        username = self.get("github.username")
        if not username:
            errors.append("Username GitHub manquant (GITHUB_USERNAME)")

        # Vérifier les valeurs numériques
        days_back = self.get("stats.days_back")
        if not isinstance(days_back, int) or days_back < 1:
            errors.append("stats.days_back doit être un entier positif")

        min_remaining = self.get("rate_limit.min_remaining")
        if not isinstance(min_remaining, int) or min_remaining < 0:
            errors.append("rate_limit.min_remaining doit être un entier positif")

        return len(errors) == 0, errors

    def display(self):
        """
        Affiche la configuration actuelle (masque le token)
        """
        print("\n" + "=" * 60)
        print("📋 CONFIGURATION ACTUELLE")
        print("=" * 60)

        # Copier et masquer le token
        display_data = dict(self.data)
        if "github" in display_data and "token" in display_data["github"]:
            token = display_data["github"]["token"]
            if token:
                display_data["github"]["token"] = token[:8] + "..." + token[-4:] if len(token) > 12 else "***"

        # Afficher en YAML
        print(yaml.dump(display_data, default_flow_style=False, allow_unicode=True))
        print("=" * 60 + "\n")

    def to_dict(self) -> dict[str, Any]:
        """
        Retourne la configuration complète en dictionnaire

        Returns:
            Copie du dictionnaire de configuration
        """
        return dict(self.data)
