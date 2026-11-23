# 🚀 GitHub Stats Automation

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![GitHub Actions](https://img.shields.io/badge/GitHub_Actions-Ready-orange?style=for-the-badge&logo=github-actions)

**Système automatisé de statistiques GitHub incluant les dépôts privés**

[Installation](#-installation) • [Configuration](#-configuration) • [Utilisation](#-utilisation) • [Documentation](#-documentation)

</div>

---

## 📋 Table des Matières

- [À Propos](#-à-propos)
- [Fonctionnalités](#-fonctionnalités)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Utilisation](#-utilisation)
  - [Locale](#utilisation-locale)
  - [GitHub Actions](#github-actions-automatisation)
- [Structure du Projet](#-structure-du-projet)
- [Modules](#-modules)
- [Personnalisation](#-personnalisation)
- [Dépannage](#-dépannage)
- [Contribution](#-contribution)
- [Licence](#-licence)

---

## 🎯 À Propos

**GitHub Stats Automation** est un outil complet pour générer automatiquement des statistiques GitHub détaillées et les afficher sur votre profil. Contrairement aux solutions existantes, cet outil peut accéder à vos **dépôts privés** pour des statistiques complètes.

### Pourquoi cet outil ?

- ✅ **Accès aux dépôts privés** : Vos stats incluent vraiment tout votre travail
- ✅ **Personnalisable** : Configuration YAML complète
- ✅ **Automatisation** : GitHub Actions intégrée
- ✅ **Cache intelligent** : Optimise les requêtes API
- ✅ **Rate limit aware** : Gère automatiquement les limites de l'API
- ✅ **Open source** : Code transparent et modifiable

---

## ✨ Fonctionnalités

### 📊 Statistiques Collectées

- **Dépôts** : Publics, privés, total
- **Commits** : Nombre de commits sur une période
- **Pull Requests** : Total, ouvertes, mergées, fermées
- **Issues** : Total, ouvertes, fermées
- **Étoiles** : Total d'étoiles reçues
- **Langages** : Répartition des langages utilisés
- **Modifications de code** : Lignes ajoutées/supprimées
- **Heatmap d'activité** : Commits par jour et heure

### 🔧 Fonctionnalités Techniques

- **Cache intelligent** : Stockage local des données pour réduire les requêtes API
- **Gestion du rate limit** : Attend automatiquement si nécessaire
- **Retry automatique** : Réessaie en cas d'erreur temporaire
- **Logging complet** : Suivi détaillé de l'exécution
- **Mode dry-run** : Tester sans publier
- **Configuration flexible** : Fichier YAML + variables d'environnement
- **Templates personnalisables** : Créez votre propre style de README

---

## 📋 Prérequis

- **Python 3.10+**
- **Git**
- **Compte GitHub** avec possibilité de créer des tokens
- **Repository GitHub** pour votre profil (username/username)

> 💡 **Note** : Pour afficher les stats sur votre profil, créez un repository public avec le même nom que votre username.

---

## 🚀 Installation

### 1. Cloner le Repository

```bash
git clone https://github.com/VOTRE_USERNAME/github_pr_automation.git
cd github_pr_automation
```

### 2. Créer un Environnement Virtuel (Recommandé)

```bash
# Créer l'environnement
python -m venv venv

# Activer l'environnement
# Sur Windows
venv\Scripts\activate

# Sur macOS/Linux
source venv/bin/activate
```

### 3. Installer les Dépendances

```bash
pip install requests pyyaml
```

### 4. Configurer les Variables d'Environnement

```bash
# Copier le fichier d'exemple
cp configs/env.example .env

# Éditer .env et ajouter vos credentials
# GITHUB_TOKEN=ghp_votre_token
# GITHUB_USERNAME=votre_username
```

---

## ⚙️ Configuration

### 1. Créer le jeton de lecture (STATS_TOKEN)

Le script ne fait que **lire** l'API : la publication du README est un commit
du workflow avec le `GITHUB_TOKEN` du dépôt. Le jeton n'a donc besoin d'aucun
droit d'écriture.

1. [Settings > Developer settings > Fine-grained tokens](https://github.com/settings/personal-access-tokens) → **Generate new token**
2. Nom : `profile-stats-readonly` ; expiration : 1 an (mets un rappel la veille)
3. **Repository access** : *All repositories*
4. **Permissions** (toutes en *Read-only*) : `Contents`, `Metadata`, `Pull requests`
5. Dans le dépôt `falilouMBC/falilouMBC` : **Settings > Secrets and variables > Actions** →
   secret `STATS_TOKEN` (le coller directement dans le champ, jamais dans un fichier ni un chat)

Quand le jeton expire, le job échoue avec « GitHub a refusé le jeton (HTTP 401) ».
Il suffit d'en générer un nouveau et de remplacer le secret.

### 2. Modifier le contenu du profil

Tout le texte affiché sur le profil est dans la section `profile` de
`configs/config.yaml` (présentation, liste « About me », badges de la stack,
contacts). Aucune modification de code n'est nécessaire :

```yaml
profile:
  name: "Falilou"
  headline: "Fullstack Developer · Solution Architect"
  stack:
    - { label: "Docker", color: "2496ED", logo: "docker" }  # logo : identifiant simpleicons.org
  contact:
    linkedin: "https://www.linkedin.com/in/falilouMBC"
    email: ""  # vide = badge masqué

readme:
  sections: [about, stack, stats, languages, activity, contact]  # ordre d'affichage
```

Le contenu est validé avant tout appel API : une couleur, un logo, une URL
LinkedIn ou un e-mail invalide arrête le script avec un message explicite.
Une config YAML invalide arrête aussi le script (plus de repli silencieux).

Aperçu local sans publier :

```bash
python scripts/update_stats.py --dry-run --output /tmp/README.preview.md
```

### 3. Statistiques affichées

| Ligne | Calcul |
| :-- | :-- |
| Commits | commits dont tu es l'auteur sur la branche par défaut, 365 derniers jours |
| Active repositories | dépôts ayant reçu un push sur la période |
| Pull requests | PR que tu as créées dans tes dépôts (bots exclus) : mergées, ouvertes, fermées sans merge |
| Languages | octets par langage, forks exclus |
| When I commit | commits par jour et par créneau de 3 h, en UTC |

### 4. Tests et hooks

```bash
pip install -r requirements-dev.txt
pre-commit install
python -m pytest          # couverture minimale 85 % sur le rendu et la collecte
mypy                      # typage strict (rendu, collecte, tests)
git add -A && pre-commit run   # fichiers indexés, comme au commit
```

> Les modules non modifiés (`cache_manager.py`, `rate_limiter.py`, `env_loader.py`,
> `check_env.py`) ne passent pas encore ruff : `--all-files` échouera tant qu'ils
> n'auront pas été nettoyés dans une MR dédiée.

---

## 🎮 Utilisation

### Utilisation Locale

#### Mode Basique

```bash
python scripts/update_stats.py
```

#### Options Disponibles

```bash
# Mode dry-run (ne publie pas)
python scripts/update_stats.py --dry-run

# Désactiver le cache
python scripts/update_stats.py --no-cache

# Mode verbeux
python scripts/update_stats.py --verbose

# Nettoyer le cache avant
python scripts/update_stats.py --clear-cache

# Sauvegarder les stats en JSON
python scripts/update_stats.py --json stats/output.json

# Afficher la configuration
python scripts/update_stats.py --show-config

# Combiner plusieurs options
python scripts/update_stats.py --dry-run --verbose --no-cache
```

#### Exemple de Sortie

```
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║          🚀 GITHUB STATS AUTOMATION                         ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝

✅ Configuration chargée depuis: configs/config.yaml
🎯 Utilisateur cible: votre_username
🔑 Token: ghp_1234...wxyz

══════════════════════════════════════════════════════════════
🔍 RÉCUPÉRATION DES STATISTIQUES...
══════════════════════════════════════════════════════════════

📦 42 dépôt(s) trouvé(s)
⭐ Total d'étoiles: 156
📝 Total commits: 1,234
🔀 Total PRs: 89 (merged: 76)
❗ Total Issues: 34

✅ Statistiques calculées avec succès
📝 README généré
💾 README mis à jour sur GitHub
```

### GitHub Actions (Automatisation)

#### Configuration

1. **Créer le repository de profil**
   ```bash
   # Sur GitHub, créez un repository public nommé exactement comme votre username
   # Exemple: si vous êtes "johndoe", créez "johndoe/johndoe"
   ```

2. **Configurer les secrets**
   - Allez dans **Settings > Secrets and variables > Actions**
   - Créez un secret nommé `STATS_TOKEN`
   - Collez le jeton fine-grained en lecture seule (voir « Créer le jeton de lecture »)

3. **Activer le workflow**
   - Copiez `.github/workflows/update-stats.yml` dans votre repo de profil
   - Commitez et pushez

4. **Configuration du workflow**
   ```yaml
   # Le workflow s'exécute automatiquement :
   on:
     schedule:
       - cron: '23 1 * * *'  # Tous les jours à 01:23 UTC
     workflow_dispatch:     # Déclenchement manuel
   ```

#### Déclenchement Manuel

1. Allez dans l'onglet **Actions** de votre repository
2. Sélectionnez **"Update GitHub Stats"**
3. Cliquez sur **"Run workflow"**
4. Options disponibles :
   - **Dry run** : aperçu dans les logs, sans commit

> Dans un dépôt public, GitHub désactive le cron après 60 jours sans activité.
> Si le README ne bouge plus, vérifie l'onglet **Actions** et réactive le workflow.

---

## 📁 Structure du Projet

```
github_pr_automation/
│
├── .github/
│   └── workflows/
│       └── update-stats.yml          # Workflow GitHub Actions
│
├── configs/
│   ├── config.yaml                   # Configuration principale
│   └── env.example                   # Exemple de variables d'env
│
├── logs/                             # Fichiers de log (généré)
│
├── scripts/
│   └── update_stats.py               # Script principal
│
├── src/
│   ├── __init__.py                   # Package Python
│   ├── cache_manager.py              # Gestion du cache
│   ├── config.py                     # Gestion de la configuration
│   ├── github_stats.py               # Classe principale
│   ├── rate_limiter.py               # Gestion du rate limiting
│   └── utils.py                      # Utilitaires divers
│
├── stats/                            # Stats JSON (optionnel, généré)
│
├── templates/
│   └── profile_template.md           # Template de README
│
├── .gitignore                        # Fichiers ignorés
└── README_PROJECT.md                 # Ce fichier
```

---

## 🧩 Modules

### 1. **cache_manager.py**
- Gère le cache des données API
- Stockage en JSON avec validation temporelle
- Réduction des requêtes API

### 2. **rate_limiter.py**
- Vérifie le rate limit GitHub
- Attend automatiquement si nécessaire
- Affiche des barres de progression

### 3. **config.py**
- Charge la configuration YAML
- Gère les surcharges d'environnement
- Validation des paramètres

### 4. **github_stats.py**
- Classe principale de collecte
- Intègre tous les modules
- Génère le README

### 5. **utils.py**
- Fonctions utilitaires
- Formatage de nombres/dates
- Génération de graphiques ASCII

### 6. **update_stats.py**
- Point d'entrée du script
- Parsing des arguments
- Orchestration générale

---

## 🎨 Personnalisation

### Modifier le contenu et les sections

Voir « Modifier le contenu du profil » : tout se règle dans la section
`profile` et `readme.sections` de `configs/config.yaml`.

### Ajuster la Période d'Analyse

```yaml
stats:
  days_back: 180  # 6 mois au lieu d'un an
```

---

## 🔧 Dépannage

### Erreur : "Token GitHub manquant"

**Cause** : La variable d'environnement n'est pas définie

**Solution** :
```bash
export GITHUB_TOKEN='ghp_votre_token'
export GITHUB_USERNAME='votre_username'
```

### Erreur : "Rate limit exceeded"

**Cause** : Trop de requêtes API

**Solutions** :
1. Activez le cache : `cache.enabled: true`
2. Augmentez `cache.max_age_hours`
3. Réduisez `stats.max_commits_pages`
4. Attendez la réinitialisation du rate limit

### Le README n'est pas mis à jour sur GitHub

**Causes possibles** :
1. Token sans permissions suffisantes
2. Repository de profil inexistant
3. Erreur de réseau

**Solutions** :
1. Vérifiez les permissions du token (repo + user)
2. Créez le repository `username/username`
3. Regardez les logs : `logs/github_stats.log`

### GitHub Actions ne fonctionne pas

**Vérifications** :
1. Le secret `STATS_TOKEN` est configuré
2. Le workflow a les permissions d'écriture
3. Le repository de profil existe et est public

---

## 📊 Exemples de Statistiques

### Console

```
═══════════════════════════════════════════════════════
📊 RÉSUMÉ DES STATISTIQUES
═══════════════════════════════════════════════════════

📦 DÉPÔTS
   Total                :              42
   └─ Publics           :              35
   └─ Privés            :               7

⭐ ÉTOILES
   Total                :             156

📝 COMMITS
   Derniers 365 jours   :           1,234

🔀 PULL REQUESTS
   Total                :              89
   ├─ Ouvertes          :               3
   ├─ Mergées           :              76
   └─ Fermées           :              10

💻 TOP 5 LANGAGES
   1. Python                  :      45.2%
   2. JavaScript              :      28.7%
   3. TypeScript              :      12.3%
   4. HTML                    :       8.1%
   5. CSS                     :       5.7%
```

### README Généré

Voir votre profil GitHub après exécution !

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Voici comment contribuer :

1. **Forkez** le projet
2. **Créez** une branche : `git checkout -b feature/ma-feature`
3. **Committez** : `git commit -m 'Ajout de ma feature'`
4. **Pushez** : `git push origin feature/ma-feature`
5. **Ouvrez** une Pull Request

### Guidelines

- Code Python propre et commenté
- Ajoutez des docstrings
- Testez vos changements
- Mettez à jour la documentation

---

## 📝 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

---

## 🙏 Remerciements

- [GitHub API](https://docs.github.com/en/rest) pour l'accès aux données
- [Shields.io](https://shields.io/) pour les badges
- Communauté open source pour l'inspiration

---

## 📞 Support

Besoin d'aide ?

- 📖 **Documentation** : Ce fichier README
- 🐛 **Bug Report** : [Ouvrir une issue](https://github.com/VOTRE_USERNAME/github_pr_automation/issues)
- 💡 **Feature Request** : [Ouvrir une issue](https://github.com/VOTRE_USERNAME/github_pr_automation/issues)
- 💬 **Discussions** : [GitHub Discussions](https://github.com/VOTRE_USERNAME/github_pr_automation/discussions)

---

<div align="center">

**Fait avec ❤️ par la communauté**

⭐ **Si ce projet vous plaît, donnez-lui une étoile !** ⭐

</div>
