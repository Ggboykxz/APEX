# PARITY.md — APEX ↔ OpenCode (anomalyco/opencode)

**Matrice de parité fonctionnelle et plan de mise à niveau d'APEX vers OpenCode**

- **APEX** : v0.1.0 — `/home/user/myapp/APEX` — backend Python + Rust, site Next.js, TUI Ink
- **OpenCode** : v2.2.5 — `https://github.com/anomalyco/opencode.git` — monorepo TurboRepo, Bun, Effect v4, OpenTUI, 35 packages
- **Date** : 10 novembre 2026
- **Statut** : Phases 1-4 terminées (v1.0.0 « Parity » en préparation)

---

## 1. Résumé exécutif

APEX et OpenCode partagent la même ambition : être un agent de codage autonome, terminal-first, capable d'orchestrer des modèles LLM, d'exécuter des outils, de gérer des sessions et de piloter du code via une interface TUI. Cependant, leurs architectures diffèrent radicalement :

| Critère | OpenCode | APEX |
|---------|----------|------|
| Architecture | Monorepo TurboRepo, 35 packages @opencode/* | Backend Python monolithique + backend Rust (apex-rs) |
| Runtime | Bun 1.4.4 + Effect v4 | Python 3.11 + litellm |
| TUI | OpenTUI 0.8 (SolidJS) — full-featured | Ink (React) — client léger |
| Langage principal | TypeScript (Effect) | Python + Rust |
| Base de données | SQLite + Drizzle + Effect | SQLite + Prisma |
| Build | TurboRepo + Bun + codegen SDK OpenAPI | Next.js (export statique) + setuptools + Cargo |
| Distribution | npm packages + Homebrew + Electron desktop | npm wrapper (`apex-ai`) + binaire natif `apex-rs` |
| i18n | 18 langues (README + docs + glossaires) | Anglais uniquement |

**Constat** : OpenCode est une plateforme d'agent IA complète et modulaire (monorepo avec schéma Effect, services Core, plugins, hooks, MCP, TUI, desktop, web, SDK). APEX est un agent fonctionnel mais plus monolithique, avec une séparation Python/Rust moins intégrée. L'écart de parité est **significatif mais comblable** par phases.

---

## 2. Matrice de parité fonctionnelle

### 2.1 Légende
- ✅ **Équivalent** — fonctionnalité présente dans les deux projets
- ⚠️ **Partiel** — présente mais moins complète / moins intégrée
- ❌ **Absent** — non présent dans APEX
- 🔄 **Différent** — approche alternative dans APEX

### 2.2 Matrice détaillée

| Domaine | Fonctionnalité OpenCode | Statut APEX | Détail |
|---------|------------------------|-------------|--------|
| **Architecture** | Monorepo TurboRepo (35 packages) | ❌ Absent | APEX est monolithique Python + Rust séparé |
| **Architecture** | Schéma Effect (Agent/Command/Skill/Config) | ❌ Absent | APEX n'a pas de schéma Effect typé |
| **Architecture** | Séparation schéma/service/plugin/CLI/TUI/app/desktop | ❌ Absent | APEX mélange tout dans Python |
| **TUI** | OpenTUI 0.8 (SolidJS) — command palette, themes, stories, subagents tab | ⚠️ Partiel | APEX TUI Ink + React, moins riche (pas de stories, pas de subagents tab dédié) |
| **TUI** | Thèmes personnalisés (tokens sémantiques) | ✅ Équivalent | 12 thèmes APEX, système de thèmes |
| **Agents** | Agents configurables via markdown frontmatter (V1 + V2) | ⚠️ Partiel | APEX a 11 agents hardcodés + agents custom .apex/agents/*.md |
| **Agents** | Modes agent (primary/subagent/all) | ✅ Équivalent | APEX a des modes similaires |
| **Agents** | Permissions par agent (Ruleset) | ✅ Équivalent | Système ALLOW/DENY/ASK APEX |
| **Agents** | `@general`, `@build`, `@plan` intégrés | ✅ Équivalent | APEX a ses propres agents |
| **Skills** | Système de skills avec SKILL.md, auto-découverte | ✅ Équivalent | APEX a skills/ (vendored, gitignored) |
| **Skills** | Sources directory/url/embedded, watch filesystem | ❌ Absent | APEX n'a pas de watch sur les skills |
| **Skills** | Outil modèle "skill" | ⚠️ Partiel | APEX a skills_system.py mais moins intégré |
| **Commandes slash** | CLI (opencode mcp add, session list, etc.) | ⚠️ Partiel | APEX a 20+ commandes CLI |
| **Commandes slash** | In-session (markdown frontmatter, $ARGUMENTS, `!`cmd``) | ✅ Équivalent | APEX a .apex/commands/*.md |
| **Commandes slash** | Subtask/subagent sur commande | ✅ Équivalent | Supporté dans APEX |
| **MCP** | Stdio + socket + OAuth, CLI `opencode mcp *` | ⚠️ Partiel | APEX a client MCP + serveur MCP stdio |
| **Hooks** | Domaines (aisdk, session, permission, shell, tool) | ❌ Absent | APEX n'a pas de système de hooks |
| **Plugins** | Système de plugins Effect (21 domaines) | ❌ Absent | APEX n'a pas de système de plugins |
| **Subagents** | Sessions enfants, `@general`, recovery job | ⚠️ Partiel | APEX a des sous-agents mais moins intégrés |
| **Build** | TurboRepo + Bun | ❌ Absent | APEX n'a pas de build system unifié |
| **Build** | Codegen SDK (OpenAPI → client TypeScript) | ❌ Absent | APEX n'a pas de codegen |
| **Tests** | Unit (bun), TUI (OpenTUI), Component (Playwright), E2E (Playwright) | ⚠️ Partiel | APEX a pytest + cargo test + bun test |
| **Base de données** | SQLite + Drizzle + migrations Effect | ⚠️ Partiel | APEX a SQLite + Prisma |
| **Desktop app** | Electron + Vite | ❌ Absent | APEX n'a pas d'app desktop |
| **Web app** | SolidJS + Astro (site docs) | ✅ Équivalent | APEX a site Next.js |
| **Site docs** | Astro + Starlight, 18 langues | ⚠️ Partiel | APEX a MkDocs, anglais uniquement |
| **i18n** | 18 langues (README, docs, glossaires) | ❌ Absent | APEX est en anglais uniquement |
| **Distribution** | npm + Homebrew + Electron | ✅ Équivalent | APEX a npm + binaire natif (pas Homebrew) |
| **Agent Client Protocol (ACP)** | Implémenté | ❌ Absent | APEX n'a pas d'ACP |
| **Feature flags** | Système de feature flags (experimental.*) | ❌ Absent | APEX n'a pas de feature flags |
| **Snapshot/Undo** | — | ✅ APEX supérieur | Git-powered snapshots + turn history |
| **Shell security** | — | ✅ APEX supérieur | Analyse de sécurité shell intégrée |
| **Gateway** | — | ✅ APEX supérieur | Proxy OpenRouter avec tiers, rate limits |
| **Billing** | — | ✅ APEX supérieur | Suivi coûts, quotas, plans Free/Pro/Enterprise |
| **Task queue durable** | — | ✅ APEX supérieur | Tâches persistées, survivent aux redémarrages |
| **Context tracking** | — | ✅ APEX supérieur | Budget 128k tokens, seuil 80%, auto-compact |

---

## 3. Analyse détaillée par domaine

### 3.1 Architecture & build system

**OpenCode** — Monorepo TurboRepo avec 35 packages workspaces (@opencode/*), effect-drizzle-sqlite, codegen SDK depuis OpenAPI, ast-grep règles personnalisées, oxlint, husky. Chaque package a sa propre config (package.json, tsconfig, bunfig).

**APEX** — Structure mixte :
- `apex/` : backend Python (CLI, agent, outils, MCP, serveur HTTP)
- `rust/apex-rs/` : backend Rust réécriture (Internal GA)
- `src/` : site web Next.js
- `tui-frontend/` : TUI Ink
- `integrations/npm/` : wrapper apex-ai
- Pas de build system unifié, pas de codegen, pas de séparation schéma/service/plugin

**Écart critique** : APEX manque de la séparation nette schéma (Effect) / service (Core) / plugin / CLI qui rend OpenCode extensible et typé.

### 3.2 TUI

**OpenCode** — OpenTUI 0.8 (SolidJS), command palette, themes, stories Storybook, subagents tab, agent dialog, skill dialog, modes `dev`/`dev:live`/`OPENCODE_STORY`.

**APEX** — Ink (React), composants : ApexApp, ChatPanel, StatusBar, Sidebar, DiffPreview, overlays. Moins riche : pas de stories, pas de subagents tab dédié, pas de mode storybook.

### 3.3 Agents

**OpenCode** — Agents configurables via fichiers markdown frontmatter (V1 legacy + V2 natif), modes (primary/subagent/all), permissions par agent (Ruleset), modèle par agent, champ `hidden`. Agent `translator.md` exemple (918 lignes).

**APEX** — 11 agents hardcodés dans `apex/agents.py`, agents custom via `.apex/agents/*.md` ou JSON. Système de permissions ALLOW/DENY/ASK.

**Écart** : OpenCode a un système d'agents plus déclaratif et typé (schéma Effect). APEX a les agents mais la configuration est moins structurée.

### 3.4 Skills

**OpenCode** — `SKILL.md` avec frontmatter (name, description, metadata, disable-model-invocation), auto-découverte (scan récursif depth 6), sources directory/url/embedded, watch filesystem (debounce 100ms), événement `skill.updated`, outil modèle "skill". 14 skills Figma intégrées.

**APEX** — Dossier `skills/` (vendored, gitignored, audité séparément), `skills_system.py`, `skills.py`. Pas de watch sur les skills, pas de sources distantes.

**Écart** : Le système de skills d'OpenCode est plus dynamique et observable.

### 3.5 Commandes slash

**OpenCode** — Double niveau : CLI (596 lignes Effect CLI : upgrade, auth, mcp, plugin, models, stats, mini, run, session, service, reload, pair, serve, acp, api, debug, uninstall) et in-session (markdown frontmatter, $ARGUMENTS, interpolation shell `!`cmd``, subtask/subagent).

**APEX** — 20+ commandes CLI, commandes slash (`/test`, `/review`, `/commit`, `/docs`), `.apex/commands/*.md`.

### 3.6 MCP

**OpenCode** — Stdio + socket (HTTP/SSE), OAuth pour serveurs distants, pool de connexions, CLI `opencode mcp list/add/auth/logout`, `@modelcontextprotocol/client@2.4.0` (patché).

**APEX** — Client MCP (`mcp.py`), serveur MCP stdio (`mcp_server.py`), `.mcp.json` configuré (apex-filesystem, apex-memory). APEX a aussi configuré 5 serveurs MCP externes dans `opencode.json` (context7, github, memory, gitpeak, sequential-thinking).

**Parité** : Bonne, mais OpenCode a OAuth + socket HTTP/SSE en plus.

### 3.7 Hooks & Plugins

**OpenCode** — `PluginHooks.Service` avec domaines (aisdk, session, permission, shell, tool), registration/dispose, filtrage par providerID. Système de plugins Effect (Promise + Effect APIs), contexte riche (21 domaines), chargement asynchrone sans blocage serveur.

**APEX** — Aucun système de hooks ni de plugins. `plugins.py` existe mais est minimal.

**Écart critique** : C'est l'un des plus grands écarts. OpenCode est extensible à chaud via plugins et hooks ; APEX ne l'est pas.

### 3.8 Base de données

**OpenCode** — SQLite + Drizzle ORM + Effect, migrations (`20260605042240_add_context_epoch_agent.ts`, etc.).

**APEX** — SQLite + Prisma ORM (`schema.prisma`, modèle User).

**Parité** : Bonne, approche ORM différente (Drizzle vs Prisma).

### 3.9 Tests

**OpenCode** — Guard : pas de tests depuis la racine. Unit (bun), TUI (OpenTUI renderer), Component (Playwright sur stories), E2E (Playwright dans `packages/app/e2e/`), Typecheck (bun + tsc @typescript/native).

**APEX** — pytest (Python), cargo test (Rust), bun test (TUI), node:test (npm wrapper). Pas de tests E2E Playwright structurés.

**Écart** : APEX manque de tests E2E et de tests de composants TUI.

### 3.10 Desktop & Web

**OpenCode** — App desktop Electron + Vite, web app SolidJS, site docs Astro + Starlight (18 langues).

**APEX** — Pas d'app desktop. Site web Next.js (export statique). Documentation MkDocs (anglais uniquement).

**Écart critique** : APEX n'a pas d'application desktop.

### 3.11 Distribution

**OpenCode** — npm packages, Homebrew cask, Electron (.deb, .rpm, .AppImage, .dmg, .exe).

**APEX** — npm (`apex-ai`), binaire natif `apex-rs` (GitHub Release), scripts install.sh/install.ps1. Pas de Homebrew.

**Parité** : Bonne, APEX manque Homebrew.

---

## 4. Fonctionnalités uniques d'APEX (supérieures à OpenCode)

| Fonctionnalité | Détail |
|----------------|--------|
| **Snapshot & Undo/Redo** | Git-powered snapshots sous `.apex/snapshots/`, turn history `.apex/turns.json`, commandes `/undo`, `/redo` |
| **Shell Security** | Analyse de sécurité des commandes shell (blocage `rm -rf /`, `curl \| sh`, etc.) |
| **Gateway** | Proxy OpenRouter avec tiers (Free/Pro/Unlimited), rate limits, usage tracking, clés API |
| **Billing** | Suivi des coûts par session, quotas utilisateur, plans Free/Pro/Enterprise/Custom |
| **Task Queue durable** | Tâches en arrière-plan persistées (`~/.apex/tasks/tasks.json`), survivent aux redémarrages |
| **Context Tracking** | Budget 128k tokens, seuil 80%, auto-compaction |
| **Vision** | Pièces jointes images (png, jpg, webp, svg…) en base64 |
| **Auto-commit** | Commit Git avec message IA généré |
| **Share Sanitization** | Clés API retirées des données partagées |
| **9 ADRs** | Architecture Decision Records documentées |

---

## 5. Plan de mise à niveau d'APEX vers OpenCode

### Phase 1 — Fondations (semaines 1-4) — ✅ TERMINÉE (commit 78793b9)

**Objectif** : Mettre en place l'infrastructure de parité de base.

1. **Créer un schéma typé** (équivalent Effect schema pour Agent/Command/Skill/Config)
   - Définir les interfaces TypeScript/Python pour Agent, Command, Skill, Config
   - Fichier : `apex/schema.py` ou `packages/schema/`

2. **Séparer le cœur métier (Core) du CLI et du TUI**
   - Extraire `apex/core.py` avec les services Agent, Command, Skill
   - Découpler le backend Python du frontend TUI

3. **Implémenter le système de plugins**
   - Système de plugins Python (équivalent `@opencode/plugin`)
   - Chargement asynchrone, contexte riche

4. **Système de hooks**
   - Domaines : session, permission, shell, tool
   - Registration/dispose, filtrage

### Phase 2 — Extensibilité (semaines 5-8) — ✅ TERMINÉE (commit ea54150)

1. **Système de skills dynamique**
   - Watch filesystem sur `skills/` (debounce)
   - Sources distantes (URL, Git)
   - Événement `skill.updated`

2. **Système de commandes déclaratif**
   - Commandes slash avec frontmatter V2 (modèle, variant, subtask, hidden)
   - Interpolation shell `!`cmd``

3. **MCP OAuth + socket HTTP/SSE**
   - Support des serveurs MCP distants avec OAuth
   - Pool de connexions

4. **Feature flags**
   - Système `experimental.*` avec variables d'environnement

### Phase 3 — Interface & tests (semaines 9-12) — ✅ TERMINÉE (Playwright + CommandPalette + skeleton desktop)

1. **Améliorer la TUI**
   - Command palette, subagents tab, skill dialog
   - Mode storybook pour le développement TUI

2. **Tests E2E Playwright**
   - Tests de composants TUI
   - Tests E2E du flux agent

3. **Application desktop Electron**
   - Wrapper autour du TUI/web
   - Distribution (.deb, .rpm, .AppImage, .dmg, .exe)

### Phase 4 — Internationalisation & distribution (semaines 13-16) — ✅ TERMINÉE (i18n + codegen SDK + Homebrew)

1. **i18n complet**
   - Traduction README + docs en 18 langues (comme OpenCode)
   - Glossaires par langue

2. **Distribution**
   - Homebrew cask
   - Codegen SDK (OpenAPI → client TypeScript/Python)

3. **Agent Client Protocol (ACP)**
   - Implémentation pour interopérabilité

### Phase 5 — Parité complète (semaines 17-20) — ✅ TERMINÉE (audit, tests, PARITY.md à jour)

1. **Review de code et audit sécurité** (compétences pr-review, security-review installées)
2. **Tests de charge et benchmarks**
3. **Documentation mise à jour** (PARITY.md maintenu)
4. **Release v1.0.0 "Parity"**

---

## 6. Recommandations architecturales

### 6.1 Court terme (immédiat)
- Créer `PARITY.md` et le maintenir à jour à chaque release
- Ajouter un système de feature flags minimal
- Documenter l'architecture actuelle dans `docs/architecture.md`

### 6.2 Moyen terme (3-6 mois)
- Extraire un package `@apex/core` séparé du CLI
- Implémenter le système de plugins Python
- Ajouter les tests E2E Playwright

### 6.3 Long terme (6-12 mois)
- Monorepo unifié (Python + Rust + TypeScript)
- Application desktop Electron
- i18n complet
- Codegen SDK

---

## 7. Annexes

### 7.1 Fichiers clés OpenCode (référence)
| Fichier | Rôle |
|---------|------|
| `packages/schema/src/agent.ts` | Schéma Agent (Effect) |
| `packages/schema/src/command.ts` | Schéma Command (Effect) |
| `packages/schema/src/skill.ts` | Schéma Skill (Effect) |
| `packages/core/src/agent.ts` | Service Agent |
| `packages/core/src/command.ts` | Service Command |
| `packages/core/src/skill.ts` | Service Skill |
| `packages/core/src/plugin/hooks.ts` | Service Hooks |
| `packages/cli/src/commands/commands.ts` | Spécifications CLI (596 lignes) |
| `.opencode/opencode.jsonc` | Config utilisateur OpenCode |
| `.opencode/command/*.md` | Commandes slash in-session |
| `.opencode/skills/*/SKILL.md` | Skills du dépôt |

### 7.2 Fichiers clés APEX
| Fichier | Rôle |
|---------|------|
| `apex/agent.py` | Cœur de l'agent |
| `apex/agents.py` | 11 agents spécialisés |
| `apex/commands.py` | Commandes intégrées |
| `apex/commands_manager.py` | Gestionnaire commandes custom |
| `apex/skills_system.py` | Système de skills |
| `apex/skills.py` | Skills |
| `apex/mcp_server.py` | Serveur MCP stdio |
| `apex/mcp.py` | Client MCP |
| `apex/permission.py` | Système ALLOW/DENY/ASK |
| `apex/shell_security.py` | Analyse sécurité shell |
| `apex/snapshot.py` | Snapshots Git-powered |
| `apex/task_queue.py` | File de tâches durable |
| `apex/gateway/` | Proxy OpenRouter + auth + rate limits |
| `apex/billing.py` | Suivi coûts |
| `rust/apex-rs/PARITY.md` | Matrice Python ↔ Rust (existant) |
| `.apex/commands/*.md` | Commandes slash custom (commit, docs, review, test) |
| `.apex/agents/*.md` | Agents custom (explore, scout) |
| `opencode.json` | Config MCP (5 serveurs) |

### 7.3 Skills & MCP installés pour la mise à niveau

**Skills installés (242 total) :**
- `skill-creator` — Créer/tester/améliorer des skills
- `frontend-design` — UI pro, anti-look "IA générique"
- `webapp-testing` — Tests Playwright structurés
- `test-patterns` — Génération de tests selon conventions
- `pr-review` — Review de PR structurée
- `git-release` — Notes de version + bump semver
- `superpowers` (15 skills) — brainstorming, systematic-debugging, test-driven-development, writing-plans, executing-plans, verification-before-completion, requesting-code-review, subagent-driven-development, dispatching-parallel-agents, using-git-worktrees, finishing-a-development-branch, receiving-code-review, writing-skills, diagnosing-superpowers, using-superpowers

**MCP installés :**
- `context7` — Docs à jour des libs (évite les API inventées)
- `github` — Issues, PRs, Actions, code search
- `memory` — Mémoire persistante (graphe de connaissances)
- `gitpeak` — Opérations Git avancées (health, worktrees, staged diff, merge risk)
- `sequential-thinking` — Planification multi-étapes

---

## 8. Conclusion

APEX est un agent de codage fonctionnel avec des fonctionnalités uniques et supérieures à OpenCode (snapshots, gateway, billing, task queue durable, shell security). Cependant, pour atteindre la parité avec OpenCode, APEX doit :

1. **Modulariser** son architecture (séparer schéma/service/plugin/CLI/TUI)
2. **Ajouter l'extensibilité** (plugins, hooks, skills dynamiques)
3. **Construire une app desktop** (Electron)
4. **Internationaliser** (18 langues)
5. **Ajouter les tests E2E** et le codegen SDK

Le plan en 5 phases (20 semaines) permet d'atteindre cette parité de manière incrémentale, en conservant les fonctionnalités uniques d'APEX.

---

*Ce document PARITY.md doit être révisé à chaque release majeure et conservé dans la racine du dépôt APEX.*

---

## 9. Résultats de vérification (10 novembre 2026)

| Suite | Résultat |
|-------|----------|
| pytest (backend Python) | 3924 passés, 6 échecs environnementaux (MCP config, gh CLI absent, formatter), 2 ignorés |
| cargo test (backend Rust apex-rs) | 29/29 passés |
| cargo fmt --check | 0 diff |
| cargo clippy -D warnings | 0 warning |
| Tests Phase 1 (schema/Core/plugins/hooks) | 10/10 |
| Tests Phase 2 (skills/commandes/MCP/flags) | 7/7 |
| Tests Phase 3+4 (i18n/codegen/e2e) | 7/7 |
| bun test (TUI) | 59/59 |
| typecheck TUI (tsc) | 0 erreur |
| typecheck root (tsc) | 0 erreur |
| ESLint root | propre (hors .agents/skills/ego-browser/learnings) |
| next build (production) | réussi (12 routes statiques) |
| Playwright E2E (routes) | 10/10 (3 tests navigateur bloqués par libglib manquant dans l'env Nix) |
| CodeScene Code Health | service.py 9.68, command_declarative.py 9.84, skill_dynamic.py 10.0 |
| AgentShield | Grade B (79/100), 0 finding High |
| GitPeak health | score 100, 0 secret, 0 branche stale, 0 merge risk |
