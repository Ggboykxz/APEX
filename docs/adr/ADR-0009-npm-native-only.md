# ADR-0009 — Distribution npm + natif uniquement

- **Statut** : Accepté (remplace les clauses PyPI, pip/pipx/uv et Homebrew de
  l'[ADR-0008](ADR-0008-installation-refonte.md))
- **Date** : 2026-11-08
- **Contexte** : L'ADR-0008 avait unifié l'installation autour du paquet
  Python `apex-ai` (pip, pipx, uv), du wrapper npm et d'une formule Homebrew,
  le backend Rust restant un canal opt-in. Cette matrice multipliait les
  chemins de provisionnement, les dépendances d'exécution (Python, pip, Node,
  Homebrew) et les surfaces de panne : le wrapper npm devait installer Python
  avant de pouvoir déléguer, Homebrew dépendait du SHA du sdist PyPI, et
  chaque canal avait ses propres commandes de mise à jour et de
  désinstallation. La publication PyPI est par ailleurs arrêtée : le paquet
  `apex-ai` existant reste résolvable mais ne doit plus être un canal
  d'installation supporté.

- **Décision** :

  1. **Deux canaux de distribution seulement.**
     - **npm** : le paquet `apex-ai` (zéro dépendance runtime) fournit la
       commande `apex` et télécharge le binaire natif vérifié au premier
       lancement.
     - **natif** : le backend Rust `apex-rs`, publié comme asset GitHub
       Release pour cinq cibles, avec un sidecar `.sha256` par archive.

     PyPI, pip, pipx, uv et Homebrew ne sont plus des canaux d'installation.
     Ils disparaissent des scripts, des workflows et de la documentation.
  2. **Le paquet PyPI existant reste tel quel.** Les versions déjà publiées
     ne sont ni supprimées ni yankées et `pip install apex-ai` continue de
     résoudre l'ancienne version. Aucune nouvelle version n'est publiée ; ce
     n'est pas un chemin supporté.
  3. **Le CLI/TUI Python devient une surface de développement source-only.**
     Il reste exécutable depuis un checkout (`pip install -e ".[dev]"`) et
     reste la référence de parité, mais il n'est distribué par aucun canal.
     `apex/install_manager.py` le décrit comme canal `source`, jamais comme
     canal de distribution.
  4. **Ordre de résolution du wrapper npm** : `APEX_BINARY` → `apex` déjà
     présent sur le `PATH` (checkout ou installation personnalisée) →
     backend natif (`apex-rs` sur le `PATH`, `~/.apex/bin/apex-rs`, puis
     téléchargement vérifié). Le provisionnement Python est supprimé.
  5. **`APEX_INSTALL_METHOD` n'accepte que `auto` ou `native`.** Toute valeur
     `pip`, `pipx` ou `uv` échoue immédiatement avec un message de migration
     (retirer la variable ou passer à `native`), au lieu d'ignorer
     silencieusement le réglage.
  6. **Installateurs unifiés.** `scripts/install.sh` et `scripts/install.ps1`
     partagent `--method auto|npm|native|docker` (`auto` = natif),
     `--version`, `--prefix`, `--no-path`, `--yes`, `--dry-run`,
     `--uninstall [--purge]`. Les fichiers `install.sh` / `install.ps1` à la
     racine ne sont que des répartiteurs vers ces scripts canoniques (checkout
     d'abord, sinon téléchargement de `main`, surchargeable par `APEX_REF`).
     Aucun bootstrap `curl | sh` silencieux.
  7. **Cycle de vie aligné sur les canaux restants.** `apex upgrade` utilise
     `npm install -g` pour le canal npm et le téléchargement vérifié pour le
     canal natif ; un checkout source reçoit l'instruction de faire
     `git pull` ; les canaux pip sont rejetés. `uninstall_plan` n'émet
     `npm uninstall -g apex-ai` que lorsque le canal npm est détecté, et
     aucune commande de gestionnaire de paquets sinon. Les garanties
     « données versus secrets » de l'ADR-0008 sont conservées : une
     désinstallation par défaut ne supprime jamais `api_keys.json` ni
     `gateway.json`.
  8. **Workflow de release simplifié.** La publication ne construit plus de
     wheel/sdist, ne publie plus sur PyPI et ne rend plus de formule
     Homebrew. Le job `github-release` n'attend que `build-native` et ne joint
     que `dist-native/*` ; l'image Docker et le paquet npm restent publiés.

- **Conséquences** :
  - Un seul chemin d'installation complet (npm) et un chemin headless sans
    Node (asset natif) ; moins de dépendances et de jobs de release.
  - Les utilisateurs de pip/pipx/uv doivent migrer vers npm ou vers le
    binaire natif ; le message d'erreur de `APEX_INSTALL_METHOD` explique
    comment.
  - Le TUI Python n'est plus installable par un utilisateur final : il faut
    un checkout. Le backend natif reste headless.
  - `pyproject.toml` et `apex/install_manager.py` continuent d'exister pour
    le développement et les tests, mais ne définissent plus de canal public.
  - Les installateurs et le wrapper doivent rester synchronisés avec les noms
    d'assets de `release.yml` ; `tests/test_install_manager.py`,
    `integrations/npm/test/*.test.js` et les exécutions `--dry-run` de
    `.github/workflows/install.yml` verrouillent ce contrat.

- **Alternatives considérées** :
  - **Conserver pip/pipx/uv en parallèle de npm** — rejeté : c'est la
    multiplication des canaux qui a motivé cet ADR, et PyPI n'est plus publié.
  - **Supprimer les versions PyPI existantes** — rejeté : PyPI interdit de
    réutiliser un nom de fichier, et la suppression casserait des
    installations existantes sans bénéfice.
  - **Publier le CLI/TUI Python sur npm** — rejeté : le paquet npm est un
    wrapper mince, pas un runtime Python embarqué.
  - **Garder Homebrew via un tap** — rejeté : la formule dépendait du sdist
    PyPI, donc d'un canal que l'on arrête.
