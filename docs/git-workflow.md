# Git Workflow — APEX

> Workflow basé sur la skill ECC `git-workflow` (2026-10-24).

## Branches

| Branche | Rôle | Protection |
|---|---|---|
| `main` | Production — toujours déployable | ✅ Protégée (PR requises, checks: CI, Commit Lint, TUI, Security, historique linéaire, pas de force push) |
| `dev` | Intégration — zone de rassemblement des fonctionnalités avant `main` | Ouverte (push direct autorisé) |
| `feature/*` | Travail isolé (ex. `feature/rust-port`) | — |

## Flux recommandé

```
main ◄── PR (dev → main) ◄── dev ◄── push direct (feature/*)
```

1. Toute modification part d'une branche (`dev` pour les petits correctifs, `feature/*` pour les gros chantiers).
2. `dev` reçoit les intégrations ; les workflows CI y tournent (push branches incluent `dev`).
3. Promotion vers `main` **uniquement via pull request** (la protection de `main` l'impose) avec checks verts et revue.
4. `main` ne reçoit jamais de push direct ni de force push.

## Règles de commit

- Conventional Commits : `fix(scope): ...`, `feat(scope): ...`, `chore(scope): ...`, `docs(scope): ...`, `test(scope): ...` (vérifié par le workflow Commit Lint).
- Un commit = un changement logique ; messages clairs.

## Checks requis sur `main`

CI · Commit Lint · TUI · Security (configurés dans la branch protection).

## Bots

Dependabot (deps), Stale, PR Labeler, Welcome/Greetings, Dependency Review (PR deps), Release Drafter.
