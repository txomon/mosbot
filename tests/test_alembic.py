import pytest
from alembic.command import downgrade, upgrade
from alembic.config import Config

from mosbot.db import get_engine

config = Config('alembic.ini')


@pytest.fixture
def database():
    pass  # Override


@pytest.mark.asyncio
async def test_upgrade():
    engine = await get_engine()
    conn = await engine.acquire()
    await conn.execute('drop schema public cascade; create schema public;')
    upgrade(config, 'head')
    engine.terminate()
    await engine.wait_closed()


def test_downgrade():
    downgrade(config, 'base')
