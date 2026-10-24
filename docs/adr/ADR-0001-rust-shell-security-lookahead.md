# ADR-0001 — Port Rust de `shell_security` : déviation lookahead git

- **Statut** : Accepté
- **Date** : 2026-10-24
- **Contexte** : Le port `rust/apex-rs/src/shell_security.rs` doit reproduire
  `apex/shell_security.py`. Le pattern Python `git\s+(?!init|status|diff|log|show|branch|checkout|add|commit|push|pull|clone|fetch|merge|rebase|config|remote|stash)\w+`
  utilise un **negative lookahead**, non supporté par le crate `regex`.

- **Décision** : Implémenter la classification git par **tokens** :
  `git_category()` vérifie `tokens[0] == "git"` puis l'appartenance du
  sous-commande à `GIT_SAFE_SUBCOMMANDS`. Les patterns durs (`git push -f`,
  `filter-branch`, `push --all`) restent en regex.

- **Conséquences** :
  - Comportement équivalent pour les cas documentés (`git status` → WORKING_DIR,
    `git push -f` → GIT + confirmation, `git <inconnu>` → GIT).
  - Différence marginale : un sous-commande à espaces exotiques peut être
    classé GIT alors que Python le laissait passer ; acceptable.
  - Documenté dans l'en-tête du module.

- **Alternatives considérées** : crate `fancy-regex` (lookahead) — rejeté :
    dépendance supplémentaire pour un seul pattern, risque de divergences de
    moteur.
