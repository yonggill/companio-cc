"""Tests for companio.helpers, including filter_secrets()."""

import pytest

from companio.helpers import filter_secrets


class TestFilterSecrets:
    # ------------------------------------------------------------------
    # Basic / edge cases
    # ------------------------------------------------------------------

    def test_empty_string_returns_empty(self):
        assert filter_secrets("") == ""

    def test_plain_text_unchanged(self):
        msg = "Hello, world! No secrets here."
        assert filter_secrets(msg) == msg

    def test_custom_mask(self):
        key = "sk-" + "a" * 20
        result = filter_secrets(key, mask="[REDACTED]")
        assert result == "[REDACTED]"

    # ------------------------------------------------------------------
    # OpenAI / Anthropic API keys
    # ------------------------------------------------------------------

    def test_openai_key_masked(self):
        key = "sk-" + "x" * 20
        assert filter_secrets(key) == "***"

    def test_anthropic_key_masked(self):
        key = "sk-ant-" + "y" * 20
        assert filter_secrets(key) == "***"

    def test_openai_key_too_short_not_masked(self):
        # Only 19 chars after "sk-" — below the 20-char minimum
        key = "sk-" + "x" * 19
        assert filter_secrets(key) == key

    # ------------------------------------------------------------------
    # GitHub tokens
    # ------------------------------------------------------------------

    def test_github_pat_ghp_masked(self):
        token = "ghp_" + "A" * 36
        assert filter_secrets(token) == "***"

    def test_github_token_gho_masked(self):
        token = "gho_" + "B" * 36
        assert filter_secrets(token) == "***"

    def test_github_token_ghs_masked(self):
        token = "ghs_" + "C" * 36
        assert filter_secrets(token) == "***"

    def test_github_token_ghu_masked(self):
        token = "ghu_" + "D" * 36
        assert filter_secrets(token) == "***"

    def test_github_token_too_short_not_masked(self):
        # 35 chars — below the 36-char minimum
        token = "ghp_" + "A" * 35
        assert filter_secrets(token) == token

    # ------------------------------------------------------------------
    # Slack tokens
    # ------------------------------------------------------------------

    def test_slack_bot_token_masked(self):
        token = "xoxb-123456789-987654321-abcdefghij"
        assert filter_secrets(token) == "***"

    def test_slack_user_token_masked(self):
        token = "xoxp-111111111-222222222-zzzzzzzzzz"
        assert filter_secrets(token) == "***"

    def test_slack_session_token_masked(self):
        token = "xoxs-333333333-444444444-qqqqqqqqqq"
        assert filter_secrets(token) == "***"

    # ------------------------------------------------------------------
    # AWS access key IDs
    # ------------------------------------------------------------------

    def test_aws_access_key_masked(self):
        key = "AKIAIOSFODNN7EXAMPLE"  # exactly AKIA + 16 uppercase alphanum
        assert filter_secrets(key) == "***"

    def test_aws_key_wrong_length_not_masked(self):
        # Only 15 chars after AKIA — one short
        key = "AKIA" + "A" * 15
        assert filter_secrets(key) == key

    # ------------------------------------------------------------------
    # JWT tokens
    # ------------------------------------------------------------------

    def test_jwt_masked(self):
        header = "eyJ" + "a" * 20
        payload = "eyJ" + "b" * 20
        jwt = f"{header}.{payload}.someSignature"
        assert filter_secrets(jwt) == "***"

    def test_jwt_too_short_not_masked(self):
        # Both header and payload below 20-char minimum
        jwt = "eyJabc.eyJxyz"
        assert filter_secrets(jwt) == jwt

    # ------------------------------------------------------------------
    # Webhook secrets
    # ------------------------------------------------------------------

    def test_webhook_secret_masked(self):
        secret = "whsec_supersecretvalue123"
        assert filter_secrets(secret) == "***"

    # ------------------------------------------------------------------
    # Private keys
    # ------------------------------------------------------------------

    def test_rsa_private_key_masked(self):
        pem = (
            "-----BEGIN RSA PRIVATE KEY-----\n"
            "MIIEowIBAAKCAQEA0Z3VS5JJcds3xHn/ygWep4\n"
            "-----END RSA PRIVATE KEY-----"
        )
        assert filter_secrets(pem) == "***"

    def test_ec_private_key_masked(self):
        pem = (
            "-----BEGIN EC PRIVATE KEY-----\n"
            "MHQCAQEEIOaWJNRmGrSuB0e1234abcd\n"
            "-----END EC PRIVATE KEY-----"
        )
        assert filter_secrets(pem) == "***"

    def test_openssh_private_key_masked(self):
        pem = (
            "-----BEGIN OPENSSH PRIVATE KEY-----\n"
            "b3BlbnNzaC1rZXktdjEAAAA\n"
            "-----END OPENSSH PRIVATE KEY-----"
        )
        assert filter_secrets(pem) == "***"

    def test_generic_private_key_masked(self):
        pem = (
            "-----BEGIN PRIVATE KEY-----\n"
            "MIIEvQIBADANBgkqhkiG9w0BAQEFAASC\n"
            "-----END PRIVATE KEY-----"
        )
        assert filter_secrets(pem) == "***"

    # ------------------------------------------------------------------
    # Multiple secrets in one string
    # ------------------------------------------------------------------

    def test_multiple_secrets_all_masked(self):
        openai_key = "sk-" + "o" * 20
        aws_key = "AKIAIOSFODNN7EXAMPLE"
        text = f"OpenAI: {openai_key} and AWS: {aws_key}"
        result = filter_secrets(text)
        assert openai_key not in result
        assert aws_key not in result
        assert "OpenAI:" in result
        assert "and AWS:" in result

    def test_secret_embedded_in_text(self):
        key = "sk-" + "z" * 25
        text = f"My API key is {key}, keep it safe."
        result = filter_secrets(text)
        assert key not in result
        assert "My API key is" in result
        assert "keep it safe." in result

    def test_multiple_occurrences_of_same_secret(self):
        key = "sk-" + "r" * 20
        text = f"{key} and again {key}"
        result = filter_secrets(text)
        assert result == "*** and again ***"
