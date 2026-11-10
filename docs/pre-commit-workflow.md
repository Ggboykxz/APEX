# Pre-Commit Verification Workflow — APEX

**Règle absolue : AUCUN commit/push sans avoir passé TOUTE cette boucle.**

Ce workflow utilise tous les MCP et skills installés. Chaque étape doit réussir avant la suivante.

## 1. Code Health (CodeScene MCP)

```bash
# Score du fichier modifié (minimum 9.0, idéal 9.5+)
tools.codescene.code_health_score(file_path=...)

# Revue détaillée + sauvegarde avant commit
tools.codescene.pre_commit_code_health_safeguard()

# Revue d'ensemble avant PR
tools.codescene.analyze_change_set()
```

## 2. Tests automatisés (obligatoires, sans exception)

```bash
# Python backend (pytest via venv)
/tmp/opencode/venv/bin/python -m pytest tests/ -q

# Tests TUI
cd tui-frontend && PATH="$PATH:/home/user/.global_modules/bin" bun test

# Phase 1 & 2 (schema/core/plugins/hooks/skills/commandes/flags/MCP)
PYTHONPATH=/home/user/myapp/APEX python3 -B tests/test_phase1_core.py
PYTHONPATH=/home/user/myapp/APEX python3 -B tests/test_phase2_ext.py
```

## 3. Qualité statique

```bash
# TypeScript root + TUI
npx tsc --noEmit
cd tui-frontend && npx tsc --noEmit

# ESLint root
npx eslint .

# Build production
npm run build
```

## 4. Sécurité (AgentShield + GitHub Push Protection)

```bash
# Scan AgentShield (grade ≥ B requis, 0 finding High)
npx ecc-agentshield scan --path . --format text --min-severity medium

# Vérifier absence de secrets dans le diff (grep 'ghp_' / 'pat_' / 'sk-')
git diff --cached | grep -E '(ghp_|pat_|sk-|AKIA|BEGIN.*PRIVATE)' && echo "SECRET TROUVÉ — BLOCAGE" || echo "OK: pas de secret"
```

## 5. Revue par MCP/skills

```bash
# Review git (gitpeak) : health, worktrees, diff
tools.gitpeak.gitpeak_health()
tools.gitpeak.gitpeak_staged_diff()

# Review GitHub (MCP github) : vérifier l'état distant
tools.github.list_commits(owner="Ggboykxz", repo="APEX")

# Memory (MCP) : enregistrer le contexte des changements
tools.memory.add_observations(...)
```

## 6. Documentation (Context7) — vérifier les API utilisées

```bash
# Si un code utilise une lib, vérifier la doc à jour
tools.context7.query_docs(libraryId=..., query=...)
```

## 7. Check list finale

- [ ] Tests Python : **3917+ passés** (0 échec bloquant)
- [ ] Tests TUI : **59 passés**
- [ ] Tests Phase 1+2 : **17 passés**
- [ ] TSC root + TUI : **0 erreur**
- [ ] ESLint : **propre**
- [ ] Build : **réussi**
- [ ] CodeScene : **score ≥ 9.0**
- [ ] AgentShield : **grade ≥ B, 0 High**
- [ ] Aucun secret dans le diff
- [ ] GitHub distant : **0 divergence non résolue**

---

*Ce workflow est exécuté AVANT chaque commit et chaque push. Il ne peut pas être ignoré.*
