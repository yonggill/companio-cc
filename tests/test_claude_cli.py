"""Tests for ClaudeCLI subprocess wrapper."""

import asyncio
import json

import pytest

from companio.core.claude_cli import ClaudeCLI, ClaudeResponse, _filtered_env


# ── ClaudeResponse.from_json ──────────────────────────────────────────


class TestClaudeResponseFromJson:
    def test_success(self):
        raw = json.dumps(
            {
                "result": "Hello, world!",
                "session_id": "sess-123",
                "cost_usd": 0.05,
                "duration_ms": 1234,
                "num_turns": 3,
                "is_error": False,
                "subtype": "success",
            }
        )
        resp = ClaudeResponse.from_json(raw)
        assert resp.result == "Hello, world!"
        assert resp.session_id == "sess-123"
        assert resp.total_cost_usd == 0.05
        assert resp.duration_ms == 1234
        assert resp.num_turns == 3
        assert resp.is_error is False
        assert resp.subtype == "success"

    def test_error_response(self):
        raw = json.dumps(
            {
                "result": "Max turns exceeded",
                "session_id": "sess-456",
                "cost_usd": 0.10,
                "duration_ms": 5000,
                "num_turns": 50,
                "is_error": True,
                "subtype": "error_max_turns",
            }
        )
        resp = ClaudeResponse.from_json(raw)
        assert resp.is_error is True
        assert resp.subtype == "error_max_turns"
        assert resp.result == "Max turns exceeded"

    def test_invalid_json(self):
        resp = ClaudeResponse.from_json("not valid json {{{")
        assert resp.is_error is True
        assert "parse" in resp.result.lower() or "json" in resp.result.lower()

    def test_missing_fields_uses_defaults(self):
        raw = json.dumps({"result": "ok"})
        resp = ClaudeResponse.from_json(raw)
        assert resp.result == "ok"
        assert resp.session_id is None
        assert resp.total_cost_usd == 0.0
        assert resp.duration_ms == 0
        assert resp.num_turns == 0
        assert resp.is_error is False

    def test_empty_string(self):
        resp = ClaudeResponse.from_json("")
        assert resp.is_error is True


# ── _filtered_env ─────────────────────────────────────────────────────


class TestFilteredEnv:
    def test_removes_claude_vars(self, monkeypatch):
        monkeypatch.setenv("CLAUDE_CODE_ENTRYPOINT", "test")
        monkeypatch.setenv("CLAUDECODE_FOO", "bar")
        monkeypatch.setenv("CLAUDE_WHATEVER", "baz")
        monkeypatch.setenv("HOME", "/home/user")
        env = _filtered_env()
        assert "CLAUDE_CODE_ENTRYPOINT" not in env
        assert "CLAUDECODE_FOO" not in env
        assert "CLAUDE_WHATEVER" not in env
        assert env.get("HOME") == "/home/user"

    def test_removes_secret_patterns(self, monkeypatch):
        monkeypatch.setenv("MY_API_KEY", "secret123")
        monkeypatch.setenv("DB_PASSWORD", "pass")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "x")
        monkeypatch.setenv("OPENAI_API_KEY", "sk-xxx")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-xxx")
        monkeypatch.setenv("TELEGRAM_TOKEN", "tok")
        monkeypatch.setenv("DATABASE_URL", "postgres://...")
        monkeypatch.setenv("PGPASSWORD", "pg")
        monkeypatch.setenv("JWT_SECRET", "jwt")
        monkeypatch.setenv("SENTRY_DSN", "https://...")
        monkeypatch.setenv("SAFE_VAR", "keep")
        env = _filtered_env()
        for key in [
            "MY_API_KEY", "DB_PASSWORD", "AWS_SECRET_ACCESS_KEY",
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "TELEGRAM_TOKEN",
            "DATABASE_URL", "PGPASSWORD", "JWT_SECRET", "SENTRY_DSN",
        ]:
            assert key not in env, f"{key} should be filtered"
        assert env.get("SAFE_VAR") == "keep"


# ── ClaudeCLI._build_cmd ─────────────────────────────────────────────


class TestBuildCmd:
    def test_basic(self):
        cli = ClaudeCLI()
        cmd = cli._build_cmd(system_prompt=None)
        assert cmd[:4] == ["claude", "-p", "--output-format", "json"]
        assert "--max-turns" in cmd
        idx = cmd.index("--max-turns")
        assert cmd[idx + 1] == "50"

    def test_with_model(self):
        cli = ClaudeCLI(model="opus-4")
        cmd = cli._build_cmd(system_prompt=None)
        assert "--model" in cmd
        idx = cmd.index("--model")
        assert cmd[idx + 1] == "opus-4"

    def test_with_system_prompt(self):
        cli = ClaudeCLI()
        cmd = cli._build_cmd(system_prompt="Be helpful")
        assert "--append-system-prompt" in cmd
        idx = cmd.index("--append-system-prompt")
        assert cmd[idx + 1] == "Be helpful"

    def test_bypass_permissions(self):
        cli = ClaudeCLI(permission_mode="bypassPermissions")
        cmd = cli._build_cmd(system_prompt=None)
        assert "--dangerously-skip-permissions" in cmd

    def test_default_permissions_no_flag(self):
        cli = ClaudeCLI(permission_mode="default")
        cmd = cli._build_cmd(system_prompt=None)
        assert "--dangerously-skip-permissions" not in cmd

    def test_allowed_tools(self):
        cli = ClaudeCLI(allowed_tools=["Read", "Edit", "Bash"])
        cmd = cli._build_cmd(system_prompt=None)
        assert "--allowedTools" in cmd
        idx = cmd.index("--allowedTools")
        assert cmd[idx + 1] == "Read,Edit,Bash"

    def test_no_allowed_tools_no_flag(self):
        cli = ClaudeCLI()
        cmd = cli._build_cmd(system_prompt=None)
        assert "--allowedTools" not in cmd


# ── ClaudeCLI.run ─────────────────────────────────────────────────────


class TestClaudeCLIRun:
    @pytest.mark.asyncio
    async def test_success(self, monkeypatch):
        response_json = json.dumps(
            {
                "result": "Done!",
                "session_id": "sess-1",
                "cost_usd": 0.01,
                "duration_ms": 500,
                "num_turns": 1,
                "is_error": False,
                "subtype": "success",
            }
        )

        async def fake_spawn(cmd, message):
            return (0, response_json, "")

        cli = ClaudeCLI()
        monkeypatch.setattr(cli, "_spawn", fake_spawn)
        resp = await cli.run("Hello")
        assert resp.result == "Done!"
        assert resp.is_error is False

    @pytest.mark.asyncio
    async def test_process_error_nonzero_exit(self, monkeypatch):
        async def fake_spawn(cmd, message):
            return (1, "", "something went wrong")

        cli = ClaudeCLI()
        monkeypatch.setattr(cli, "_spawn", fake_spawn)
        resp = await cli.run("Hello")
        assert resp.is_error is True
        assert "something went wrong" in resp.result

    @pytest.mark.asyncio
    async def test_timeout(self, monkeypatch):
        async def fake_spawn(cmd, message):
            raise asyncio.TimeoutError()

        cli = ClaudeCLI()
        monkeypatch.setattr(cli, "_spawn", fake_spawn)
        resp = await cli.run("Hello")
        assert resp.is_error is True
        assert "timeout" in resp.result.lower()

    @pytest.mark.asyncio
    async def test_cancelled_error(self, monkeypatch):
        async def fake_spawn(cmd, message):
            raise asyncio.CancelledError()

        cli = ClaudeCLI()
        monkeypatch.setattr(cli, "_spawn", fake_spawn)
        resp = await cli.run("Hello")
        assert resp.is_error is True
        assert "cancel" in resp.result.lower()

    @pytest.mark.asyncio
    async def test_empty_stdout_exit_zero(self, monkeypatch):
        async def fake_spawn(cmd, message):
            return (0, "", "")

        cli = ClaudeCLI()
        monkeypatch.setattr(cli, "_spawn", fake_spawn)
        resp = await cli.run("Hello")
        assert resp.is_error is True
        assert "empty" in resp.result.lower()

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self, monkeypatch):
        call_count = 0
        max_concurrent = 0

        async def fake_spawn(cmd, message):
            nonlocal call_count, max_concurrent
            call_count += 1
            max_concurrent = max(max_concurrent, call_count)
            await asyncio.sleep(0.05)
            call_count -= 1
            return (
                0,
                json.dumps({"result": "ok", "is_error": False}),
                "",
            )

        cli = ClaudeCLI(max_concurrent=2)
        monkeypatch.setattr(cli, "_spawn", fake_spawn)
        tasks = [cli.run("msg") for _ in range(5)]
        await asyncio.gather(*tasks)
        assert max_concurrent <= 2
