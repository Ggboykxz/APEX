# ADR-0006 — Mode serveur MCP (stdio)

- **Statut** : Accepté
- **Date** : 2026-10-25
- **Contexte** : APEX consomme déjà des serveurs MCP (`apex/mcp.py`), mais
  n'expose pas ses propres outils. Les clients MCP (OpenCode, IDE, agents
  tiers) ne peuvent donc pas réutiliser `read_file`, `repo_map`, `grep` ou les
  outils Git d'APEX. Le protocole MCP est JSON-RPC 2.0 ; le transport stdio
  est le plus simple à sécuriser localement et ne nécessite ni port ni
  certificat.

- **Décision** : Ajouter `apex mcp serve`, un serveur MCP **stdio uniquement** :

  1. **Transport** : JSON-RPC 2.0 sur stdin/stdout, une requête à la fois.
     `stdout` est réservé aux messages protocolaires ; tout log va sur
     `stderr`. Aucun listener réseau dans cette version.
  2. **Négociation** : répondre à `initialize` avec la version de protocole
     supportée, `capabilities.tools`, puis traiter `tools/list` et
     `tools/call`. Les notifications `initialized` sont acceptées sans effet.
  3. **Outils** : exposer les schémas JSON des outils natifs via le registre
     existant, sans duplication de logique. Les noms sont exposés tels quels ;
     le client les namespace par serveur.
  4. **Sécurité** : toute exécution passe par le `ToolRegistry` et le
     `permission_manager` existants. Le profil par défaut est **lecture
     seule** (`read_file`, `grep`, `glob`, `repo_map`, outils Git en lecture) ;
     les outils destructeurs (`write_file`, `edit_file`, `apply_patch`,
     `run_command`) ne sont exposés que si
     `mcp.server.allow_tools` les autorise explicitement.
  5. **Limites** : timeout par appel (120 s par défaut), réponse plafonnée à
     1 MiB, taille de requête plafonnée à 1 MiB, une erreur JSON-RPC propre
     par requête invalide. Le serveur s'arrête sur EOF stdin.
  6. **Ressources** : non exposées dans cette itération. La carte de dépôt
     reste accessible via l'outil `repo_map`. Une extension `resources` est
     possible sans casser le contrat.

- **Conséquences** :
  - Les clients MCP peuvent utiliser APEX sans réimplémenter les outils, les
    permissions ou les garde-fous shell.
  - Le serveur hérite du répertoire de travail du processus parent ; aucun
    chemin arbitraire n'est accepté au-delà des validations d'outils.
  - Pas d'authentification : la confiance est celle du processus parent
    (stdio). Un transport HTTP/SSE nécessiterait auth, rate limiting et une
    revue de sécurité séparée.
  - Les schémas doivent rester alignés sur `apex/tools.py` ; un test de
    parité (`tools/list` == registre) est obligatoire.

- **Alternatives considérées** :
  - **Transport HTTP/SSE** — rejeté pour cette itération : surface réseau,
    authentification et limites à concevoir ; stdio couvre les clients
    locaux visés.
  - **Serveur MCP dans le port Rust** — rejeté : parité Rust encore
    partielle (ADR-0004) et duplication de la logique de permissions.
  - **Exposer tous les outils par défaut** — rejeté : un client MCP ne doit
    pas obtenir `run_command` sans opt-in explicite.
