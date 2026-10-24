# ECC Agent-Sort — APEX

> Produit par la skill ECC `agent-sort` (evidence-based), le 2026-10-24.
> Objectif : classifier les composants ECC pour APEX en DAILY vs LIBRARY,
> avec preuves issues du dépôt, et plan d'installation résultant.

## STACK

| Surface | Preuve | Conclusion |
|---|---|---|
| Backend Python 3.11+ CLI agent | `apex/*` (178 .py), `pyproject.toml` (pytest, ruff, mypy, setuptools) | Stack active |
| Site web TypeScript / Next.js 16 | `src/app/*` (67 .tsx, 31 .ts), `package.json` (next 16, tailwind v4, radix, prisma, next-auth), `package-lock.json` | Stack active |
| TUI Ink 5 + React 18 | `tui-frontend/` (package.json, tsx) | Stack active |
| Port Rust | `rust/apex-rs/` (19 .rs, Cargo.toml, axum/tokio) | Nouveau — actif |
| Docs | `docs/` + `mkdocs.yml` (mkdocs-material) | Actif |
| CI/CD | 18 workflows `.github/workflows/` (ci, coverage, security, deploy-website, docker-ci, release…) | Actif |
| Surfaces harness existantes | `.apex/` (agents + commands), `skills/` (48 dossiers), `AGENTS.md`, `.env` committé | Ne pas introduire de 2ᵉ système d'install |

## DAILY — toujours chargé (preuves)

| Composant ECC | Type | Preuve dépôt |
|---|---|---|
| `ck` (Context Keeper) | skill | Projet long-terme avec sessions/mémoire (`session.py`, `memory.py`) ; continuité inter-sessions |
| `tdd-workflow` | skill | `tests/` complet (2094 tests revendiqués), workflow `coverage.yml` |
| `verification-loop` | skill | CI exécute build/lint/test/coverage ; passerelle de vérification locale locale |
| `git-workflow` | skill | Repo git très actif : commit, PR, release-drafter, dependabot |
| `error-handling` | skill | Code Python+TS+Rust (3 langages), gestion d'erreurs multiplateforme |
| `rust-build` / `rust-review` / `rust-test` | commandes | `rust/apex-rs/` (Cargo.toml) — déjà présentes dans l'install OpenCode home |

## LIBRARY — accessible, non chargé par défaut (preuves)

| Composant | Type | Justification |
|---|---|---|
| `production-audit` | skill | Utile en pre-launch/post-merge ; CI deploy-website/docker existe mais pas quotidien |
| `intent-driven-development` | skill | Réservé aux changements à fort impact (sécurité, deploys) |
| `architecture-decision-records` | skill | Docs riches — utile à l'usage, pas chaque session |
| `code-tour`, `codebase-onboarding` | skills | Onboarding contributeurs (CONTRIBUTING.md existe) |
| `unified-memory` | skill | Vault cross-harness ; APEX a déjà `memory.py` — garder accessible |
| `browser-qa`, `e2e-testing` | skills | Site Next.js déployé ; pas de suite Playwright dans le repo actuellement |
| `windows-desktop-e2e` | skill | Hors stack (pas de WPF/WinForms/Qt) |
| Meta ECC (`ecc-guide`, `ecc-recipes`, `configure-ecc`, `agent-sort`, `rules-distill`, `skill-scout`, `skill-stocktake`, `skill-comply`, `eval-harness`, `delivery-gate`, `hookify-rules`, `plankton-code-quality`, `continuous-learning-v2`, `council`, `santa-method`, `loop-design-check`, `strategic-compact`, `context-budget`, `growth-log`, `inherit-legacy-style`, `living-docs-governance`, `product-lens`, `ai-regression-testing`, `agent-self-evaluation`, `agent-introspection-debugging`, `click-path-audit`, `codehealth-mcp`, `config-gc`, `iterative-retrieval`, `plan-canvas`, `dev-team`, `repo-scan`) | skills | Génériques ou orientées ECC — restent joignables via recherche / routeur `skill-library` |

## INSTALL PLAN

1. ✅ Copier les skills DAILY dans `skills/` du dépôt : `ck`, `tdd-workflow`, `verification-loop`, `git-workflow`, `error-handling` (réutilise les surfaces natives APEX — pas de 2ᵉ système).
2. ✅ Créer le routeur `skills/skill-library/SKILL.md` (DAILY vs LIBRARY + mots-clés de déclenchement).
3. ✅ Rédiger ce rapport (`docs/ecc-agent-sort.md`).
4. ❌ Ne PAS installer le hook runtime ECC : APEX a déjà `permission.py` + `shell_security.py`, et le repo ne charge pas les hooks OpenCode/Claude.
5. ❌ Ne PAS installer de règles de langage obsolètes (pas de Java/Flutter/Go/Swift dans le repo — les commandes `cpp-*`, `flutter-*`, `java-*`, `go-*`, `kotlin-*` restent en LIBRARY dans l'install home).

## VERIFICATION

- [x] Les 5 dossiers DAILY existent dans `skills/` du dépôt (locaux)
- [x] Aucun écrasement : aucun des 5 noms n'existait déjà dans `skills/`
- [x] Aucun hook exécutable installé dans le repo
- [x] Les surfaces en conflit (`.env` committé, `opencode.json` user) traitées
- [x] `skills/` est ignoré par le `.gitignore` du dépôt (`/skills/`) — les skills
      DAILY restent une surface locale, non versionnée (choix du projet respecté)
- [~] Suivi : `verification-loop` après un changement majeur ; `production-audit`
      avant release ; `cargo test` pour valider les ports Rust

### Résultats d'audit complémentaires (2026-10-24)

- 6 tests `test_shell_security.py` codant d'anciens faux positifs (classif
  DANGEROUS erronée pour `git push`, `ssh`, `npm publish`, `docker run bash`,
  `openssl rand`) corrigés vers le comportement sain ; `git push` simple passe
  désormais par la branche de confirmation.
- `apex/commands_manager.py` : les `!bash` inline sont maintenant analysés par
  `shell_analyzer` (blocage DANGEROUS / requires_confirmation).
- `.env` (DATABASE_URL) untracked ; 51 `*.py,cover` + 6 `.pyc` untracked.
- Workflows GitHub : toutes les actions sont épinglées par tag sauf
  `trufflesecurity/trufflehog@main` (recommandation : épingler un SHA/tag).

## Résumé

- DAILY : 6 (5 skills + rust-* déjà présents)
- LIBRARY : 40+ (listés)
- Surfaces obsolètes retirées : aucune (rien n'était installé) — 0 suppression
- Questions ouvertes : purge de l'historique git du `.env` (si `DATABASE_URL`
  est un credential réel) ; `trufflehog@main` à épingler ; vérifier la suite
  pytest complète (la revendication « 2094 passing » n'était pas fiable : 6
  tests étaient cassés).
