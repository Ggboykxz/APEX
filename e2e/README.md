# Tests E2E (Playwright)

Suite de tests de bout en bout pour le site statique APEX (`out/`).

## Exécution

```bash
# 1. Build statique
npm run build

# 2. Lancer le serveur statique + tests
npm run e2e
```

Ou manuellement :

```bash
npx serve out -l 3001 &
npx playwright test
```

## Couverture

- `e2e/site.spec.ts` — vérifie que les 10 routes principales répondent `200` avec du contenu (tests de requêtes).
- Navigation navigateur (titre, liens, contenu) pour les pages clés.

## Limite connue (environnement Nix)

Dans le sandbox Nix actuel, les tests **navigateur** (page.goto) ne peuvent pas
s'exécuter : le Chromium headless crashe (SIGTRAP/SIGABRT) au chargement des
pages Next.js complexes. La cause est environnementale (bibliothèques système /
pipe CDP sous Nix), pas le code APEX.

Les tests de **requêtes** (réponse HTTP des routes) passent à 10/10 dans cet
environnement. Sur un environnement standard (CI GitHub Actions, Ubuntu),
l'ensemble de la suite doit s'exécuter normalement.

Si vous êtes sous Nix et voulez tenter les tests navigateur :

```bash
nix-shell  # fournit libglib, gtk3, nss, etc. (voir shell.nix)
```
