# ADR-0007 — Extension VS Code comme client léger

- **Statut** : Accepté
- **Date** : 2026-10-25
- **Contexte** : La roadmap v2.5 demande une extension VS Code. APEX possède
  déjà un backend HTTP/SSE (`apex serve`), un TUI Ink et un client web. Une
  extension qui embarquerait sa propre boucle d'agent, ses outils ou ses clés
  de fournisseur dupliquerait les permissions, les snapshots et les
  garde-fous shell, avec un risque de divergence.

- **Décision** : Créer `integrations/vscode`, une extension TypeScript
  **client léger** du backend existant :

  1. **Connexion** : `apex.serverUrl` (défaut `http://127.0.0.1:8765`).
     `apex.server.autoStart` lance `apex serve --cwd <workspaceFolder>` si
     aucun serveur ne répond. Un serveur par dossier de workspace en
     multi-racine ; les autres dossiers sont attachés explicitement.
  2. **Protocole** : chat via `POST /chat/stream` (SSE), état et sessions via
     `/api/v1/*`, diff via `/api/v1/session/{id}/diff`, événements via
     `/ws/events`. Aucun appel direct aux fournisseurs LLM.
  3. **UI** : webview de chat (CSP stricte, pas de script distant), status bar
     (modèle, coût, contexte), commandes `apex.chat`, `apex.explainSelection`,
     `apex.fixSelection`, `apex.reviewDiff`, `apex.newSession`, entrées de
     menu contextuel sur la sélection.
  4. **Sécurité** : la clé API du backend est stockée dans
     `SecretStorage` et envoyée en en-tête `Authorization` ; jamais dans les
     réglages, les logs ou la webview. Les demandes de permission `ASK`
     remontées par l'EventBus sont affichées dans la webview ; refuser est le
     défaut si la webview est fermée.
  5. **Distribution** : packaging VSIX en CI et artefact de build uniquement.
     Pas de publication Marketplace tant que la parité et l'expérience ne sont
     pas stabilisées ; décision produit explicite requise, comme pour
     ADR-0004.
  6. **Tests** : tests unitaires (client HTTP, parsing SSE, réducteur d'état)
     avec un serveur mocké ; un test d'intégration démarre `apex serve` sur un
     port éphémère et vérifie un aller-retour de chat sans réseau externe.

- **Conséquences** :
  - Une seule implémentation de l'agent, des outils et des permissions.
  - L'extension reste utilisable avec un backend distant ou conteneurisé en
    changeant `apex.serverUrl`.
  - Le multi-racine impose une gestion explicite des serveurs ; le mode
    « un serveur global » n'est pas supporté implicitement.
  - La webview doit rester un composant de présentation : aucun outil n'y est
    exécuté.

- **Alternatives considérées** :
  - **Extension autonome appelant les fournisseurs** — rejeté : duplication
    des clés, des permissions, des snapshots et des garde-fous.
  - **Language Server Protocol** — rejeté : LSP ne modélise pas le chat, les
    sessions ni les approbations d'outils.
  - **Application desktop Electron** — rejeté : coût de distribution et
    d'intégration IDE supérieur pour un besoin couvert par VS Code.
