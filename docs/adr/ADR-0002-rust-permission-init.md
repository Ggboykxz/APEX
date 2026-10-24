# ADR-0002 — Port Rust de `permission` : initialisation au constructeur

- **Statut** : Accepté
- **Date** : 2026-10-24
- **Contexte** : `apex/permission.py` initialise les règles par défaut
  paresseusement (`initialize()` appelée depuis `can_execute_tool`). En Rust,
  les références partagées avec mutation interne compliquent ce lazy-init
  (`RefCell`/`Mutex` dans `&self`).

- **Décision** : `PermissionManager::new()` construit directement les règles
  par défaut ; pas d'`ensure_initialized` différé. Le singleton
  `PERMISSION_MANAGER` (LazyLock<Mutex<…>>) est donc toujours initialisé.

- **Conséquences** :
  - Sémantique identique pour tous les usages observables (l'état par défaut
    est le même).
  - Suppression d'une source de bugs (oubli d'`initialize()`).
  - `can_execute_tool` devient `&self` (pas de mutation interne).

- **Alternatives considérées** : `OnceCell` + `RefCell` — rejeté : complexité
    inutile, aucun bénéfice observable.
