# APEX — Agent for Programming EXecution

*Built in Gabon 🇬🇦 for the world.*

> **APEX** est un agent de coding IA inspiré d'OpenCode, terminal-first, open-source. Il orchestre 100+ modèles LLM via litellm, exécute des outils avec un système de permissions granulaire, et protège chaque modification par des snapshots réversibles.

---

## Table des matières

1. [Vue d'ensemble](#1-vue-densemble)
2. [Architecture](#2-architecture)
3. [Agents (Build & Plan)](#3-agents-build--plan)
4. [Boucle de chat](#4-boucle-de-chat)
5. [Event Bus](#5-event-bus)
6. [Mémoire structurée (Parts)](#6-mémoire-structurée-parts)
7. [Registre d'outils](#7-registre-doutils-tools)
8. [Système de permissions](#8-système-de-permissions)
9. [Snapshots & Undo/Redo](#9-snapshots--undoredo)
10. [Providers IA](#10-providers-ia)
11. [Intégration LSP](#11-intégration-lsp)
12. [Support MCP](#12-support-mcp)
13. [Sessions](#13-sessions)
14. [Mode CI/CD](#14-mode-cicd)
15. [Commandes personnalisées](#15-commandes-personnalisées)
16. [Sécurité](#16-sécurité)

---

## 1. Vue d'ensemble

APEX est un **agent autonome** capable de :

- Analyser l'intégralité d'une codebase
- Lire, créer et modifier des fichiers avec précision
- Exécuter des commandes shell et interpréter les résultats
- Lancer des tests, lire les erreurs, itérer automatiquement
- Demander confirmation avant toute action destructive
- Gérer plusieurs sessions en parallèle sur le même projet

```
┌──────────────────────────────────────────────────────┐
│                      APEX                            │
│                                                      │
│   Frontend (TUI / REPL / API)                       │
│          ↕  HTTP / WebSocket / stdin                 │
│   Backend (Python)                                   │
│   ├── Agent Loop (chat, tools, permissions)          │
│   ├── Session Manager (SQLite/Memory)                │
│   ├── Event Bus (typed events)                       │
│   ├── Provider Abstraction (100+ LLM providers)      │
│   ├── Tool Registry (read, write, edit, bash...)     │
│   ├── LSP Client (language intelligence)             │
│   ├── MCP Client (protocoles externes)               │
│   └── Snapshot System (undo/redo Git-powered)        │
└──────────────────────────────────────────────────────┘
```

---

## 2. Architecture

### Composants principaux

| Composant | Description |
|-----------|-------------|
| `main.py` | CLI entry point, argument parsing |
| `agent.py` | Agent core, chat loop, LLM interaction |
| `tools.py` | 75+ built-in tools |
| `session.py` | Session management, persistence |
| `permission.py` | Permission system |
| `shell_security.py` | Shell command analysis |
| `rate_limiter.py` | Rate limiting |
| `api_key.py` | API key management |
| `billing.py` | Cost tracking |
| `http_api.py` | HTTP API server |

### TUI Architecture (OpenCode-like)

```
apex/tui/
├── app.py              # Main APEXTUI class
├── routes/             # Route-based navigation
│   ├── home.py         # HomeRoute
│   ├── session.py      # SessionRoute
│   └── plugin.py       # PluginRoute
├── components/         # UI components
│   ├── dialog.py       # Modal dialogs
│   ├── toast.py        # Notifications
│   ├── status_bar.py   # Status bar
│   └── command_palette.py
├── contexts/           # Context providers
│   ├── theme_context.py # Theme management (6 themes)
│   ├── route_context.py # Navigation
│   └── event_context.py # Event bus (on/once/off/emit)
├── keymap/            # KeymapManager with layers
├── themes/             # 6 built-in themes (JSON)
└── plugins/            # Plugin system with hooks
```

### Keymap Layers

| Layer | Description |
|-------|-------------|
| `global` | General commands (q, ?, :, t, n, p) |
| `input` | Input field bindings |
| `command` | Command palette |
| `navigation` | hjkl navigation |

---

## 3. Agents (Build & Plan)

APEX supporte deux modes d'agent basculeables :

### Agent `build` (défaut)
- **Accès complet à tous les outils** : lire, écrire, éditer, shell
- Agent principal pour le développement
- Modifie réellement les fichiers

### Agent `plan` (lecture seule)
- **Analyse et propose** sans toucher aucun fichier
- Parfait pour explorer une codebase
- Aucun side effect — safe à utiliser

### Switch entre modes

```bash
# Via commande
/agent build   # Mode build (défaut)
/agent plan    # Mode plan (lecture seule)

# Dans le TUI
Tab  → Bascule entre Build et Plan
```

---

## 4. Boucle de chat

La fonction centrale `chat()` orchestre toute l'autonomie d'APEX :

```
1. PROCESS INPUT
   └── Convertit le message + fichiers joints en parts structurées

2. CONTEXT MANAGEMENT
   └── Vérifie si on approche la limite de tokens
       → Si oui : résumé automatique via un modèle léger

3. AI CALL
   └── Envoie le contexte + tools disponibles au modèle IA
       → Stream la réponse token par token

4. TOOL EXECUTION
   └── Si l'IA appelle un outil :
       a. Vérifie les permissions
       b. Crée un snapshot (sauvegarde avant modification)
       c. Exécute l'outil
       d. Retourne le résultat à l'IA
       e. L'IA continue (boucle jusqu'à terminaison)

5. STATE UPDATE
   └── Persiste tout en base
       → Publie des events sur le bus pour les frontends
```

---

## 5. Event Bus

APEX est bâti sur un **bus d'événements fortement typé** :

```python
from apex.tui.contexts.event_context import EventBus

bus = EventBus()

# S'abonner
bus.on("session_updated", handler_function)
bus.on("file_changed", on_file_change)
bus.on("permission_requested", on_permission_request)

# Émettre
bus.emit("session_updated", session_data)
bus.emit("file_changed", file_path="src/main.py")

# Une seule fois
bus.once("tool_executed", handler)

# Désinscrire
bus.off("file_changed", handler)
```

### Événements typés

| Event | Description |
|-------|-------------|
| `session_updated` | Session modifiée |
| `session_created` | Nouvelle session |
| `session_deleted` | Session supprimée |
| `file_changed` | Fichier modifié |
| `message_added` | Nouveau message |
| `tool_executed` | Outil exécuté |
| `tool_error` | Erreur d'outil |
| `permission_requested` | Permission demandée |
| `permission_granted` | Permission accordée |
| `permission_denied` | Permission refusée |
| `theme_changed` | Thème changé |
| `route_changed` | Route changée |
| `tui_ready` | TUI démarrée |
| `tui_exit` | TUI fermée |

---

## 6. Mémoire structurée (Parts)

Messages avec parts typées :

```python
@dataclass
class MessagePart:
    part_type: str  # text, file, tool_call, tool_result, image
    content: Any

@dataclass
class Message:
    id: str
    role: str  # user, assistant, tool
    parts: List[MessagePart]
    token_usage: Optional[TokenUsage]
    cost_usd: Optional[float]
```

### Types de parts

| Part | Description |
|------|-------------|
| `text` | Texte du message |
| `file` | Fichier référencé (chemin + contenu) |
| `tool_call` | Appel d'outil (nom + paramètres) |
| `tool_result` | Résultat de l'outil |
| `image` | Image uploadée |
| `snapshot` | Référence au snapshot avant modification |

---

## 7. Registre d'outils (Tools)

### Outils natifs (75+)

| Outil | Description | Sécurité |
|-------|-------------|----------|
| `read_file` | Lit un fichier | Détection binaire, limite taille |
| `write_file` | Crée/écrase un fichier | Permission + snapshot |
| `edit_file` | Modification chirurgicale | Permission + snapshot |
| `bash` | Exécute commande shell | Parsing sécurité, sandbox |
| `grep` | Recherche dans codebase | Lecture seule |
| `glob` | Liste fichiers par pattern | Lecture seule |
| `read_directory` | Liste répertoire | Lecture seule |
| `search` | Recherche web | Lecture seule |
| `mcp_*` | Outils MCP | Via MCP client |

### Appels d'outils

```
IA → "Je vais modifier src/auth.ts"
  ↓
Tool Registry → vérifie permission
  ↓ (si autorisé)
Snapshot → crée snapshot Git
  ↓
Tool Execute → modifie le fichier
  ↓
LSP Client → diagnostics
  ↓
Bus.publish(FileChanged)
  ↓
Résultat → IA (avec diagnostics)
  ↓
IA continue ou termine
```

---

## 8. Système de permissions

### Actions

| Action | Description |
|--------|-------------|
| `ALLOW` | Autorisé sans confirmation |
| `DENY` | Refusé |
| `ASK` | Confirmation demandée |

### Configuration

```python
from apex.permission import permission_manager, PermissionAction

# Règle par pattern
permission_manager.add_rule(
    "read_file",
    PermissionAction.ASK,
    pattern="/src/**"
)

# Vérifier
can_execute, reason = permission_manager.can_execute_tool(
    "write_file",
    path="/src/components/Button.tsx"
)
```

### Mémoire des permissions

```python
# Autoriser toujours pour ce pattern
permission_manager.set_default(
    "write_file",
    PermissionAction.ALLOW,
    pattern="/src/components/**"
)

# Résultats mémorisés
# write sur /src/components/* → auto-approved
```

---

## 9. Snapshots & Undo/Redo

Avant chaque action destructive :

```python
from apex.snapshot import SnapshotManager

snapshot_mgr = SnapshotManager(cwd="/project")

# Créer snapshot
snapshot_id = await snapshot_mgr.track()

# Modifier les fichiers...
# IA exécute edit_file, write_file, etc.

# Obtenir le diff
patches = await snapshot_mgr.patch(snapshot_id)

# Restaurer si besoin
await snapshot_mgr.restore(snapshot_id)
```

### Commandes

```bash
/undo   # Annule la dernière action IA
/redo   # Réapplique une action annulée
```

---

## 10. Providers IA

### Supportés (100+)

| Provider | Modèles |
|----------|---------|
| Anthropic | claude-sonnet, claude-opus, claude-haiku |
| OpenAI | gpt-4o, o1, o3, o4-mini |
| Google | gemini-2, gemini-flash |
| Groq | llama-groq, mixtral-groq |
| DeepSeek | deepseek-chat, deepseek-coder |
| Ollama | llama3, codellama, mistral (local) |
| Et 100+ autres via litellm |

### Configuration

```python
# Environment variables
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
GROQ_API_KEY=gsk_...

# CLI
apex --model claude-sonnet
apex --model gpt-4o
apex --model ollama-llama3  # Local, sans API key
```

---

## 11. Intégration LSP

LSP = Language Server Protocol pour l'intelligence syntaxique :

```python
from apex.lsp import LSPClient

lsp = LSPClient(cwd="/project")

# Diagnostics après modification
diagnostics = await lsp.get_diagnostics("src/main.ts")
# [{error: "Type 'string' not assignable to 'number'", line: 42}]

# Références
refs = await lsp.find_references("src/utils.ts", symbol="helper")
```

**Impact** : après modification, APEX récupère les erreurs TypeScript/Lint et peut les corriger dans la même itération.

---

## 12. Support MCP

MCP = Model Context Protocol pour outils externes :

```python
# Configuration MCP
mcp_config = {
    "servers": [
        {
            "name": "github",
            "command": "npx @modelcontextprotocol/server-github",
            "env": {"GITHUB_TOKEN": "ghp_xxx"}
        }
    ]
}
```

Outils MCP disponibles comme outils natifs.

---

## 13. Sessions

### Persistance

```python
from apex.session import SessionManager

manager = SessionManager()

# Créer session
session = manager.create_session(
    project_path="/path/to/project",
    model="claude-sonnet"
)

# Sauvegarder
manager.save_session(session)

# Charger
loaded = manager.load_session(session_id)

# Lister
sessions = manager.list_sessions()
```

### Multi-session

```python
# Plusieurs sessions actives
s1 = manager.create_session(project="/proj", name="feature-auth")
s2 = manager.create_session(project="/proj", name="refactor-payment")
s3 = manager.create_session(project="/proj", name="tests-e2e")

# Switch
manager.switch_session(s2.id)
```

### Partage

```bash
/share   # Génère un lien de partage
```

---

## 14. Mode CI/CD

```bash
# Prompt unique, sortie JSON
apex -p "Check this diff for security issues" -f json

# Mode non-interactif
apex -p "Analyze this PR" --no-tui

# Avec modèle spécifique
apex -p "Generate changelog" --model gpt-4o -f json
```

### Flags

| Flag | Description |
|------|-------------|
| `-p "prompt"` | Prompt direct sans TUI |
| `-f json` | Sortie JSON structurée |
| `-q` | Quiet mode |
| `--model` | Modèle à utiliser |
| `--no-tui` | Pas d'interface TUI |

---

## 15. Commandes personnalisées

### Structure

```
~/.apex/commands/           # Commandes globales (user:)
<project>/.apex/commands/    # Commandes projet (project:)
```

### Exemple

```markdown
<!-- ~/.apex/commands/review.md -->
# Code Review Standard

Analyse le code et vérifie :
1. Respect des conventions (voir AGENTS.md)
2. Gestion des erreurs complète
3. Pas de console.log oubliés
4. Types explicites (pas de any)
5. Tests présents si logique complexe

Rapport : ✅ OK / ⚠️ Warning / ❌ Critique
```

### Utilisation

```bash
/user:review
/project:deploy-check
```

---

## 16. Sécurité

| Fonction | Description |
|----------|-------------|
| Shell Security | Détecte commandes dangereuses (rm -rf, curl|sh) |
| Permission System | ALLOW/DENY/ASK par pattern |
| Rate Limiting | Limites par clé API |
| API Key Management | Clés avec expiration |
| Billing | Suivi des coûts |

### Configuration

```python
from apex.shell_security import shell_analyzer

analysis = shell_analyzer.analyze("rm -rf /tmp/test")
# safe: False, category: DANGEROUS

from apex.rate_limiter import create_rate_limiter
limiter = create_rate_limiter(use_sqlite=True)
result = limiter.check_rate_limit("user_123")
```

---

## Projet Status

- **Version**: 1.3.1
- **Tests**: 1148 passing
- **License**: MIT

## Installation

```bash
pip install apex-ai
pipx install apex-ai
git clone https://github.com/Ggboykxz/APEX && cd APEX && pip install -e .
```

## Lancement

```bash
apex                        # REPL interactif
apex "prompt"              # One-shot
apex --ui                  # TUI Textual
apex --new-tui             # Nouveau TUI OpenCode-like
apex --model gpt-4o        # Modèle spécifique
apex -p "prompt" -f json   # Mode CI/CD
```

---

*Made with ❤️ in Gabon 🇬🇦*
*APEX v1.3.1 — Inspired by OpenCode*