# ADR-0003 — Port Rust de `rate_limiter` : storage mémoire d'abord

- **Statut** : Accepté
- **Date** : 2026-10-24
- **Contexte** : `apex/rate_limiter.py` propose `MemoryStorage` (défaut) et
  `SQLiteStorage` (option `use_sqlite=True`). Le port Rust
  `rust/apex-rs/src/rate_limiter.rs` ne doit pas ajouter de dépendance sans
  besoin.

- **Décision** : Porter uniquement `MemoryStorage` (le défaut) dans la
  première passe. Le trait `StorageBackend` est public pour permettre une
  implémentation SQLite ultérieure.

- **Conséquences** :
  - Équivalence fonctionnelle avec l'usage par défaut de Python.
  - SQLite différé (nécessiterait `rusqlite` + gestion pool) : décision
    reportée, documentée dans l'en-tête du module.
  - Les tests couvrent fenêtres, indépendance des clés, statut et cleanup.

- **Alternatives considérées** : ajouter `rusqlite` maintenant — rejeté :
    dépendance non utilisée par le backend actuel, coût de build sur Windows.
