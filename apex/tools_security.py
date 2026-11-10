"""The file names the file-reading tools refuse to open.

Centralised here so that the read and the discovery tools apply the very
same policy.
"""

from __future__ import annotations

from pathlib import Path

__all__ = [
    "BLOCKED_SECRET_NAMES",
    "SECRET_CONFIG_DIRS",
    "SECRET_CONFIG_NAMES",
    "is_blocked_secret",
]

BLOCKED_SECRET_NAMES = frozenset(
    {
        ".env",
        ".env.local",
        ".env.production",
        ".env.development",
        "id_rsa",
        "id_dsa",
        "id_ecdsa",
        "id_ed25519",
        "credentials.json",
        "credentials.yaml",
        "credentials.yml",
        "service-account.json",
        "service-account.key",
        ".netrc",
        ".pgp",
        ".gpg",
        ".asc",
        ".key",
        ".p12",
        ".pfx",
        ".dockerconfigjson",
        "dockercfg",
        "kubeconfig",
        "kubeconfig.yaml",
        ".npmrc",
        ".yarnrc",
        ".gemrc",
        "authorized_keys",
        "known_hosts",
        ".htpasswd",
        ".pgpass",
    }
)
SECRET_CONFIG_DIRS = frozenset({".ssh", ".aws", ".kube", ".gnupg", ".config"})
SECRET_CONFIG_NAMES = frozenset({"config.json", "config.yaml", "config.yml"})


def is_blocked_secret(path: Path) -> bool:
    """Whether reading this file is blocked because it usually holds secrets."""
    name = path.name.lower()
    if name in BLOCKED_SECRET_NAMES:
        return True
    # Only block config files in known secret locations (home dir, .ssh, .aws, etc.)
    if name in SECRET_CONFIG_NAMES and any(part in SECRET_CONFIG_DIRS for part in path.parts):
        return True
    return name.startswith(".env.") and not name.endswith(".example")
