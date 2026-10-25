# ADR-0005 — Carte de dépôt symbolique pour le contexte

- **Statut** : Accepté
- **Date** : 2026-10-25
- **Contexte** : Les modèles doivent comprendre la structure d'un dépôt sans
  consommer des milliers de tokens en fichiers complets. Les approches
  existantes (injection de fichiers entiers, recherche plein texte,
  embeddings) sont soit trop coûteuses, soit non déterministes, soit
  dépendantes d'un service externe. APEX a besoin d'une vue compacte,
  reproductible et hors ligne, utilisable comme outil par l'agent et comme
  contexte initial.

- **Décision** : Introduire `apex/repomap.py`, une carte de dépôt au niveau
  des symboles :

  1. **Extraction** : `ast` pour Python (classes, fonctions, méthodes,
     décorateurs, signatures, résumé de docstring de module) ; heuristiques
     regex ancrées sur les lignes pour JavaScript/TypeScript, Rust et Go.
  2. **Classement** : comptage textuel des références inter-fichiers aux
     déclarations de premier niveau, puis profondeur de répertoire, puis
     chemin. Les définitions conservent l'ordre source dans un fichier.
  3. **Budget** : rendu d'une ligne d'en-tête par fichier et d'une ligne de
     signature par déclaration ; estimation `ceil(caractères / 4)` ; les
     entrées les moins bien classées sont retirées jusqu'à tenir dans le
     budget. Une entrée seule trop grande est omise, jamais tronquée.
  4. **Cache** : cache JSON par racine dans `~/.apex/cache/repomap/`,
     validé par `mtime_ns` + taille de chaque fichier, écriture atomique,
     cache corrompu ignoré, `use_cache=False` pour le contourner. Le cache
     ne sort jamais de `~/.apex` et n'écrit rien dans le dépôt cible.
  5. **Surface** : `get_symbol_map()` dans `apex/context.py` et l'outil
     `repo_map` (lecture seule) dans `apex/tools.py`.

- **Conséquences** :
  - Le contexte initial peut inclure une vue structurelle du dépôt pour un
    coût borné et prévisible.
  - L'extraction non-Python est volontairement heuristique : les
    déclarations multi-lignes, génériques complexes et méthodes de classes
    JS/TS peuvent manquer. Ces limites sont documentées dans
    `docs/reference/repomap.md` et couvertes par des tests de non-régression.
  - Seul le `.gitignore` de la racine est lu ; les liens symboliques de
    répertoires sont ignorés pour éviter les boucles.
  - La fraîcheur du cache repose sur `mtime` + taille : une édition de même
    taille avec un horodatage préservé peut rester obsolète.
  - Aucune dépendance runtime nouvelle, aucun appel réseau.

- **Alternatives considérées** :
  - **Embeddings / RAG** — rejeté : dépendance à un service ou à un modèle
    d'embedding, résultats non déterministes, coût d'indexation continu.
  - **tree-sitter** — rejeté pour cette itération : dépendance native et
    matrice de build multiplateforme, alors que les heuristiques couvrent
    le besoin actuel. Réévaluable si la précision devient bloquante.
  - **ctags** — rejeté : binaire externe, sortie dépendante de la version,
    moins de contrôle sur le classement et le budget.
  - **Injection de fichiers entiers** — rejeté : coût en tokens imprévisible
    et saturation rapide de la fenêtre de contexte.
