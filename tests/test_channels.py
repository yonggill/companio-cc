
import pytest

from companiocc.bus import MessageBus
from companiocc.channels.base import BaseChannel


class MockChannel(BaseChannel):
    name = "mock"

    async def start(self):
        self._running = True

    async def stop(self):
        self._running = False

    async def send(self, msg):
        pass


class MockConfig:
    allow_from = ["user1", "user2"]


class TestBaseChannel:
    def test_is_allowed_listed_user(self):
        bus = MessageBus()
        channel = MockChannel(config=MockConfig(), bus=bus)
        assert channel.is_allowed("user1") is True

    def test_is_allowed_unlisted_user(self):
        bus = MessageBus()
        channel = MockChannel(config=MockConfig(), bus=bus)
        assert channel.is_allowed("stranger") is False

    def test_is_allowed_wildcard(self):
        class WildcardConfig:
            allow_from = ["*"]
        bus = MessageBus()
        channel = MockChannel(config=WildcardConfig(), bus=bus)
        assert channel.is_allowed("anyone") is True

    def test_is_allowed_empty_list_denies_all(self):
        class EmptyConfig:
            allow_from = []
        bus = MessageBus()
        channel = MockChannel(config=EmptyConfig(), bus=bus)
        assert channel.is_allowed("anyone") is False

    @pytest.mark.asyncio
    async def test_handle_message_allowed(self):
        bus = MessageBus()
        channel = MockChannel(config=MockConfig(), bus=bus)
        await channel._handle_message(
            sender_id="user1", chat_id="chat1", content="hello"
        )
        assert bus.inbound_size == 1

    @pytest.mark.asyncio
    async def test_handle_message_denied(self):
        bus = MessageBus()
        channel = MockChannel(config=MockConfig(), bus=bus)
        await channel._handle_message(
            sender_id="stranger", chat_id="chat1", content="hello"
        )
        assert bus.inbound_size == 0

    def test_is_running_default(self):
        bus = MessageBus()
        channel = MockChannel(config=MockConfig(), bus=bus)
        assert channel.is_running is False


class TestCLI:
    def test_cli_app_exists(self):
        from companiocc.cli import app
        assert app is not None

    def test_cli_app_name(self):
        from companiocc.cli import app
        assert app.info.name == "companiocc"
