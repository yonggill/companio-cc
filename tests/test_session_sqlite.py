import pytest

from companiocc.session import SessionManager


@pytest.fixture
async def session_mgr(tmp_path):
    mgr = SessionManager(tmp_path / "sessions")
    await mgr.initialize()
    yield mgr
    await mgr.close()


class TestSQLiteSession:
    @pytest.mark.asyncio
    async def test_create_session(self, session_mgr):
        session = await session_mgr.get_or_create("telegram:123")
        assert session.session_id == "telegram:123"
        assert session.messages == []

    @pytest.mark.asyncio
    async def test_save_and_load(self, session_mgr):
        session = await session_mgr.get_or_create("telegram:123")
        session.messages.append({"role": "user", "content": "hello"})
        session.messages.append({"role": "assistant", "content": "hi"})
        await session_mgr.save(session)
        # Clear cache to force reload
        session_mgr._cache.clear()
        loaded = await session_mgr.get_or_create("telegram:123")
        assert len(loaded.messages) == 2
        assert loaded.messages[0]["content"] == "hello"

    @pytest.mark.asyncio
    async def test_clear_session(self, session_mgr):
        session = await session_mgr.get_or_create("telegram:123")
        session.messages.append({"role": "user", "content": "hello"})
        await session_mgr.save(session)
        await session_mgr.clear("telegram:123")
        loaded = await session_mgr.get_or_create("telegram:123")
        assert loaded.messages == []

    @pytest.mark.asyncio
    async def test_incremental_save(self, session_mgr):
        session = await session_mgr.get_or_create("telegram:123")
        session.messages.append({"role": "user", "content": "first"})
        await session_mgr.save(session)
        session.messages.append({"role": "user", "content": "second"})
        await session_mgr.save(session)
        session_mgr._cache.clear()
        loaded = await session_mgr.get_or_create("telegram:123")
        assert len(loaded.messages) == 2

    @pytest.mark.asyncio
    async def test_last_consolidated(self, session_mgr):
        session = await session_mgr.get_or_create("telegram:123")
        session.last_consolidated = 5
        await session_mgr.save(session)
        session_mgr._cache.clear()
        loaded = await session_mgr.get_or_create("telegram:123")
        assert loaded.last_consolidated == 5

    @pytest.mark.asyncio
    async def test_multiple_sessions(self, session_mgr):
        s1 = await session_mgr.get_or_create("telegram:user1")
        s2 = await session_mgr.get_or_create("telegram:user2")
        s1.messages.append({"role": "user", "content": "from user1"})
        s2.messages.append({"role": "user", "content": "from user2"})
        await session_mgr.save(s1)
        await session_mgr.save(s2)
        session_mgr._cache.clear()
        r1 = await session_mgr.get_or_create("telegram:user1")
        r2 = await session_mgr.get_or_create("telegram:user2")
        assert r1.messages[0]["content"] == "from user1"
        assert r2.messages[0]["content"] == "from user2"
