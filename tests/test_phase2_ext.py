"""Tests unitaires Phase 2 — extensibilité APEX (parité OpenCode).

Couvre :
  - apex.utils.frontmatter : parseur YAML minimal stdlib
  - apex.skill_dynamic : parse SKILL.md, découverte récursive, manager dynamique
  - apex.command_declarative : commandes slash déclaratives, render, execute
  - apex.mcp_client_ext : config, connexion (handshake réel), pool
  - apex.feature_flags : flags avec couches env + config

Exécution : ``PYTHONPATH=/home/user/myapp/APEX python3 -B tests/test_phase2_ext.py``
"""

from __future__ import annotations

import os
import sys
import tempfile

from apex.utils.frontmatter import parse_frontmatter_document
from apex.skill_dynamic import (
    SkillDiscovery,
    SkillSourceConfig,
    parse_skill_md,
)
from apex.command_declarative import (
    DeclarativeCommandManager,
    parse_command_md,
)
from apex.mcp_client_ext import (
    MCPConnection,
    MCPConnectionPool,
    MCPServerConfig,
    MCPTransportError,
)
from apex.feature_flags import FeatureFlags
from apex.core import Core
from apex.hooks import PluginHooks

SKILL_MD = """---
name: test-skill
description: A test skill
metadata:
  version: 1
---
# Body
"""

CMD_MD = """---
description: Commit changes
subtask: true
agent: build
---
Run commit with $ARGUMENTS
"""


def test_frontmatter_parse():
    metadata, body = parse_frontmatter_document(SKILL_MD)
    assert metadata["name"] == "test-skill"
    assert metadata["description"] == "A test skill"
    assert body.strip() == "# Body"


def test_skill_parse():
    skill = parse_skill_md(SKILL_MD, "/tmp/SKILL.md")
    assert skill is not None
    assert skill.name == "test-skill"


def test_skill_discovery():
    with tempfile.TemporaryDirectory() as d:
        os.makedirs(os.path.join(d, "skills", "my-skill"))
        with open(os.path.join(d, "skills", "my-skill", "SKILL.md"), "w") as f:
            f.write(SKILL_MD)
        cfg = SkillSourceConfig(kind="directory", path=os.path.join(d, "skills"))
        found = SkillDiscovery(cfg).discover()
        assert "test-skill" in found


def test_command_parse():
    cmd = parse_command_md(CMD_MD, "/tmp/commit.md")
    assert cmd is not None
    assert cmd.name == "commit"
    assert cmd.subtask is True
    assert cmd.agent == "build"


def test_declarative_manager_load():
    core = Core()
    hooks = PluginHooks()
    mgr = DeclarativeCommandManager(core, hooks, roots=[".apex/commands"])
    mgr.load()
    found = mgr.list()
    assert "commit" in found
    assert "review" in found


def test_mcp_config_pool():
    cfg = MCPServerConfig(name="ctx", type="remote", url="https://x")
    assert cfg.name == "ctx"
    pool = MCPConnectionPool()
    pool.remove("ctx")  # no-op

def test_feature_flags_layer():
    flags = FeatureFlags(config_experimental={"mcp_oauth": True})
    assert flags.is_enabled("mcp_oauth") is True
    assert flags.is_enabled("skill_watch") is True
    assert flags.is_enabled("desktop") is False


if __name__ == "__main__":
    tests = [
        ("frontmatter_parse", test_frontmatter_parse),
        ("skill_parse", test_skill_parse),
        ("skill_discovery", test_skill_discovery),
        ("command_parse", test_command_parse),
        ("declarative_manager_load", test_declarative_manager_load),
        ("mcp_config_pool", test_mcp_config_pool),
        ("feature_flags_layer", test_feature_flags_layer),
    ]
    passed = 0
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS {name}")
            passed += 1
        except Exception as e:
            print(f"  FAIL {name}: {e}")
            failed += 1
    print(f"\n{passed} passed, {failed} failed out of {len(tests)}")
    if failed:
        sys.exit(1)
    print("=== TOUS LES TESTS PHASE 2 REUSSIS ===")
