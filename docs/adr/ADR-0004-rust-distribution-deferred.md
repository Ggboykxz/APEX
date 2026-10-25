# ADR-0004 — Diffusion du port Rust différée (phase interne)

- **Statut** : Accepté
- **Date** : 2026-10-25
- **Contexte** : Le port Rust `rust/apex-rs` expose 23 modules, une CLI
  fonctionnelle (run, chat, serve, tools, plugins, call-tool, cost, memory,
  session) et 110 tests verts sur Linux. La parité fonctionnelle avec le
  backend Python n'est toutefois pas complète : certains modules sont portés
  mais non câblés, et `main.rs` conserve un `#![allow(dead_code)]` de
  transition. Une publication prématurée (binaires GitHub Releases, crate
  `apex-rs` sur crates.io) figerait une API et des artefacts avant que la
  parité et la matrice de conformance soient stabilisées.

- **Décision** : La diffusion externe du port Rust est reportée. La phase
  actuelle reste interne : build et tests du binaire dans la CI, numéro de
  version `0.1.0`, aucune publication sur crates.io et aucun binaire joint aux
  GitHub Releases. La documentation d'installation ne doit pas mentionner
  `cargo install apex-rs` tant que cet ADR n'est pas révisé.

- **Conséquences** :
  - Les utilisateurs passent exclusivement par le backend Python
    (`pip install apex-ai`) ; le binaire Rust reste un artefact de
    développement.
  - Les critères de sortie sont explicites et vérifiables en CI : zéro
    `#![allow(dead_code)]` au niveau crate, matrice de parité complète,
    E2E binaire vert sur Linux et Windows.
  - Pas de coût de maintenance d'un canal de distribution (signatures,
    attestations de provenance, versionnement sémantique public) avant que le
    produit soit prêt.

- **Critères de réouverture** :
  1. Parité documentée à 100 % dans `rust/apex-rs/PARITY.md` (ou équivalent).
  2. E2E binaire vert sur Linux et Windows pendant deux semaines consécutives.
  3. Décision produit explicite de distribuer le binaire.

- **Alternatives considérées** :
  - Publier immédiatement des binaires et la crate — rejeté : dette de
    compatibilité et charge de release prématurées.
  - Ne jamais distribuer le Rust — rejeté : le port reste un objectif
    stratégique de performance et de robustesse.
