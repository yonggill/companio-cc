"""Tests for configuration schema, defaults, and loading."""

import json
from pathlib import Path

import pytest

from companiocc.config.schema import Config, TelegramConfig


class TestConfigDefaults:
    """Verify Config can be instantiated with sane defaults."""

    def test_default_instantiation(self):
        config = Config()
        assert config.agents.defaults.memory_window == 200
        assert config.claude.max_turns == 50
        assert config.claude.timeout == 300
        assert config.claude.max_concurrent == 5
        assert config.claude.model is None
        assert config.claude.allowed_tools == []

    def test_telegram_config_defaults(self):
        tc = TelegramConfig()
        assert tc.enabled is False
        assert tc.token == ""
        assert tc.allow_from == []
        assert tc.proxy is None
        assert tc.reply_to_message is False

    def test_env_prefix(self):
        config = Config()
        assert config.model_config.get("env_prefix") == "COMPANIOCC_"

    def test_workspace_path_uses_companio(self):
        config = Config()
        assert ".companiocc" in config.agents.defaults.workspace
        assert ".nanobot" not in config.agents.defaults.workspace

    def test_gateway_defaults(self):
        config = Config()
        assert config.gateway.host == "0.0.0.0"
        assert config.gateway.port == 18790
        assert config.gateway.heartbeat.enabled is True
        assert config.gateway.heartbeat.interval_s == 600

    def test_channels_defaults(self):
        config = Config()
        assert config.channels.send_progress is True
        assert config.channels.send_tool_hints is False


class TestConfigExampleConsistency:
    """Verify config.example.json matches schema defaults."""

    @pytest.fixture()
    def example_config(self) -> dict:
        path = Path(__file__).resolve().parent.parent / "companiocc" / "templates" / "config.example.json"
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def test_example_validates_against_schema(self, example_config):
        """config.example.json must be loadable by the schema without errors."""
        config = Config.model_validate(example_config)
        assert config.agents.defaults.memory_window == 200

    def test_example_matches_defaults(self, example_config):
        """Key values in config.example.json should equal schema defaults."""
        default = Config()
        loaded = Config.model_validate(example_config)
        assert loaded.agents.defaults.memory_window == default.agents.defaults.memory_window
        assert loaded.claude.max_turns == default.claude.max_turns
        assert loaded.claude.timeout == default.claude.timeout
        assert loaded.gateway.heartbeat.interval_s == default.gateway.heartbeat.interval_s


class TestConfigLoader:
    """Verify loader helpers."""

    def test_load_dotenv_does_not_crash_on_missing(self, tmp_path):
        from companiocc.config.loader import load_dotenv_if_exists

        # Should silently do nothing when .env is absent
        load_dotenv_if_exists(tmp_path)

    def test_load_config_from_nonexistent_path(self, tmp_path):
        from companiocc.config.loader import load_config

        config = load_config(tmp_path / "does_not_exist.json")
        assert config.agents.defaults.memory_window == 200
