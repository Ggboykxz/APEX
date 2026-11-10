"""APEX Codegen SDK — génère un client depuis un schéma API.

Phase 4 (parité OpenCode : codegen SDK OpenAPI → client TypeScript/Python).
Implémentation compacte et sans dépendance :

- lit un schéma simple (OpenAPI 3.0 subset) au format JSON,
- émet un client Python (``apex/generated_client.py``) avec une fonction par
  opération (GET/POST), typée avec ``dataclass`` pour les modèles.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

__all__ = ["API_SCHEMA_PATH", "generate_client", "load_schema"]

API_SCHEMA_PATH = Path(__file__).parent / "api_schema.json"


def load_schema(path: Path | None = None) -> dict[str, Any]:
    p = path or API_SCHEMA_PATH
    return json.loads(p.read_text(encoding="utf-8"))


def _py_name(s: str) -> str:
    # camelCase -> snake_case
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", s)
    s = re.sub(r"[^a-zA-Z0-9_]", "_", s)
    return s.strip("_").lower() or "x"


def generate_client(schema: dict[str, Any], out: Path) -> Path:
    """Émet le client Python depuis le schéma."""
    paths = schema.get("paths", {})
    components = schema.get("components", {}).get("schemas", {})

    lines: list[str] = [
        '"""Généré par apex.codegen_sdk — ne pas éditer à la main."""',
        "from __future__ import annotations",
        "from dataclasses import dataclass, field",
        "from typing import Any, Optional",
        "",
        "import json",
        "from urllib import request, error",
        "",
        "",
        "class APIClient:",
        '    """Client typé minimal pour l\'API APEX."""',
        "",
        "    def __init__(self, base_url: str, api_key: Optional[str] = None):",
        "        self.base_url = base_url.rstrip('/')",
        "        self.api_key = api_key",
        "",
        "    def _call(self, method: str, path: str, body: Optional[dict] = None):",
        "        url = self.base_url + path",
        "        headers = {'Content-Type': 'application/json'}",
        "        if self.api_key:",
        "            headers['Authorization'] = f'Bearer {self.api_key}'",
        "        data = json.dumps(body).encode() if body is not None else None",
        "        req = request.Request(url, data=data, headers=headers, method=method)",
        "        try:",
        "            with request.urlopen(req, timeout=30) as resp:",
        "                raw = resp.read().decode('utf-8', errors='replace')",
        "                return json.loads(raw) if raw else None",
        "        except error.HTTPError as e:",
        "            return {'error': e.code, 'message': e.read().decode(errors='replace')}",
        "",
    ]

    # Modèles (schémas simples avec propriétés)
    for name, sch in components.items():
        props = sch.get("properties", {})
        if not props:
            continue
        lines.append("@dataclass")
        lines.append(f"class {_py_name(name)}:")
        for pname, pspec in props.items():
            ptype = pspec.get("type", "Any")
            pytype = {
                "string": "str",
                "integer": "int",
                "boolean": "bool",
                "array": "list",
                "object": "dict",
            }.get(ptype, "Any")
            default = ""
            if ptype == "string":
                default = ' = ""'
            elif ptype == "integer":
                default = " = 0"
            elif ptype == "boolean":
                default = " = False"
            elif ptype == "array":
                default = " = field(default_factory=list)"
            lines.append(f"    {_py_name(pname)}: {pytype}{default}")
        lines.append("")

    # Opérations
    for path, methods in paths.items():
        for method, op in methods.items():
            if method not in ("get", "post", "put", "delete", "patch"):
                continue
            op_id = op.get("operationId", f"{method}_{_py_name(path)}")
            fn = _py_name(op_id)
            lines.append(f"    def {fn}(self):")
            lines.append(f'        """{op.get("summary", op_id)}"""')
            lines.append(f"        return self._call('{method.upper()}', {path!r})")
            lines.append("")

    out.write_text("\n".join(lines), encoding="utf-8")
    return out
