# ADR-0008 — Refonte de l'installation et distribution du backend natif

- **Statut** : Accepté (remplace la clause « aucun binaire joint aux GitHub
  Releases » de l'[ADR-0004](ADR-0004-rust-distribution-deferred.md))
- **Date** : 2026-11-07
- **Contexte** : La surface d'installation avait divergé. Le dépôt déclarait
  quatre versions différentes (`VERSION` absent, `apex/__init__.py` et
  `pyproject.toml` en 2.0.0, `Cargo.toml` en 0.1.0, npm en 2.5.0), les deux
  installateurs (`scripts/install.sh`, `scripts/install.ps1`) ne savaient
  installer que le paquet Python de façon interactive, la formule Homebrew
  pointait encore sur la v1.2.0 sous licence MIT, et le backend Rust
  (`apex-rs`), pourtant en GA interne, n'était installable par aucun canal.
  `apex upgrade` ne connaissait ni `uv` ni `native` et lançait toujours
  `pip uninstall` ; `apex uninstall` ne supprimait ni les tâches durables ni
  le binaire natif.

- **Décision** :

  1. **Version canonique unique.** `VERSION` à la racine est la seule source
     de vérité. `scripts/version.py check` est le gate CI (tag de release,
     `apex/__init__.py`, `pyproject.toml`, `Cargo.toml`, `Cargo.lock`,
     `integrations/npm/package.json`) et `sync` réécrit tous les manifestes.
  2. **Le CLI/TUI Python reste l'installation par défaut.** Le backend Rust
     est **headless** (serve, run, tools, gateway) et **opt-in**.
  3. **Distribution native par assets GitHub Release.** Cinq cibles sont
     construites et publiées à chaque tag : `x86_64`/`aarch64` Linux,
     `x86_64`/`aarch64` macOS, `x86_64` Windows. Chaque
     `apex-rs-<triple>.tar.gz|.zip` est accompagné d'un `.sha256` qui sert
     d'unique ancre de confiance aux installateurs. Aucune publication sur
     crates.io : la crate reste interne.
  4. **Le binaire natif ne s'appelle jamais `apex`.** Il est installé comme
     `apex-rs`/`apex-rs.exe` dans `~/.apex/bin` (`APEX_INSTALL_DIR`), afin de
     ne jamais masquer le CLI Python ni créer deux implémentations
     concurrentes de `apex`.
  5. **Ordre de résolution du wrapper npm** : `APEX_BINARY` → `apex` sur le
     `PATH` → natif si `APEX_INSTALL_METHOD=native` ou
     `APEX_PREFER_NATIVE=1` → provisionnement Python (`pipx` > `uv` > `pip`)
     → repli natif quand aucun Python n'existe et que `APEX_NATIVE != 0`.
  6. **Installateurs unifiés.** `install.sh` et `install.ps1` partagent les
     mêmes options : `--method auto|python|uv|pipx|pip|native|docker`,
     `--version`, `--prefix`, `--no-path`, `--yes`, `--dry-run`,
     `--uninstall [--purge]`. Aucun bootstrap `curl | sh` silencieux : le
     script est téléchargé puis exécuté avec des options explicites.
  7. **Cycle de vie dans le paquet.** `apex/install_manager.py` détecte le
     canal, construit les commandes de mise à jour et le plan de
     désinstallation. `apex upgrade [--check] [--method …]` et
     `apex uninstall [--purge] [--dry-run]` s'appuient dessus.
  8. **Homebrew rendu à la release.** `Formula/apex-ai.rb.tmpl` est la source ;
     `scripts/render_homebrew.py` injecte le SHA256 du sdist PyPI (connu
     seulement après le build) et le fichier rendu `apex-ai.rb` est joint à la
     release. Le fichier rendu n'est jamais committé.
  9. **Données versus secrets.** Une désinstallation par défaut retire
     `~/.config/apex`, `~/.apex/{sessions,memory,tasks}` et le binaire natif,
     mais **jamais** `api_keys.json` ni `gateway.json`. `--purge` est le seul
     chemin qui supprime l'arbre `~/.apex` complet.

- **Conséquences** :
  - Une seule version à faire évoluer ; un tag `vX.Y.Z` ne peut plus
    publier un paquet dont les manifestes divergent.
  - Les utilisateurs sans Python peuvent installer le binaire headless, mais
    l'expérience complète (TUI, agents, partage) reste Python.
  - Les installateurs doivent rester synchronisés avec les noms d'assets du
    workflow `release.yml` ; le test `tests/test_install_manager.py` et
    `integrations/npm/test/native.test.js` verrouillent le mapping.
  - Homebrew dépend désormais du SHA du sdist : le job de release télécharge
    l'artefact construit (pas PyPI) pour le calculer, donc une panne PyPI ne
    bloque pas la publication de la formule.

- **Alternatives considérées** :
  - Publier `apex-rs` sur crates.io — rejeté : API interne encore mouvante
    et pas de versionnement sémantique public.
  - Installer le binaire natif sous le nom `apex` — rejeté : masque le CLI
    Python et crée deux comportements incompatibles sous un même nom.
  - Conserver quatre manifestes de version — rejeté : c'est précisément la
    dérive qui a motivé cet ADR.
  - Committer la formule Homebrew rendue — rejeté : le SHA devient obsolète
    au tag suivant et `brew` échoue silencieusement.
