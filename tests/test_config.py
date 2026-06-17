from __future__ import annotations

import re
import unittest

from create_dlthub_workspace import config
from create_dlthub_workspace.config import RECOMMENDED
from create_dlthub_workspace.scaffold import PER_AGENT_DIR, SCAFFOLDS_DIR, TOOLKITS_MANIFEST

_TOOLKIT_KEY = re.compile(r"^([A-Za-z0-9_-]+):$", re.MULTILINE)


def _installed_toolkits(agent: str) -> set[str]:
    manifest = SCAFFOLDS_DIR / RECOMMENDED.scaffold / PER_AGENT_DIR / agent / TOOLKITS_MANIFEST
    return set(_TOOLKIT_KEY.findall(manifest.read_text(encoding="utf-8")))


class ConfigTests(unittest.TestCase):
    def test_toolkits_is_a_tuple(self) -> None:
        # A bare string iterates per-character in `for toolkit in TOOLKITS`.
        self.assertIsInstance(config.TOOLKITS, tuple)
        self.assertTrue(config.TOOLKITS)

    def test_toolkits_are_installed_in_scaffolds(self) -> None:
        for agent in config.AGENTS:
            installed = _installed_toolkits(agent)
            for toolkit in config.TOOLKITS:
                self.assertIn(toolkit, installed, f"{toolkit!r} not installed for agent {agent!r}")


if __name__ == "__main__":
    unittest.main()
