import asynctest as am
import pytest
from abot.dubtrack import DubtrackPlaying, DubtrackSkip, DubtrackDub, DubtrackUserUpdate

from mosbot.handler import history_handler, availability_handler


@pytest.yield_fixture
def ensure_dubtrack_playing_mock():
    with am.patch('mosbot.handler.ensure_dubtrack_playing') as m:
        yield m


@pytest.yield_fixture
def ensure_dubtrack_dub_mock():
    with am.patch('mosbot.handler.ensure_dubtrack_dub') as m:
        yield m


@pytest.yield_fixture
def ensure_dubtrack_skip_mock():
    with am.patch('mosbot.handler.ensure_dubtrack_skip') as m:
        yield m


@pytest.mark.parametrize('event, func', (
        (DubtrackPlaying, 'edp'),
        (DubtrackSkip, 'eds'),
        (DubtrackDub, 'edd'),
        (DubtrackUserUpdate, None),  # Unrelated event
))
@pytest.mark.asyncio
async def test_history_handler(
        db_conn,
        ensure_dubtrack_playing_mock,
        ensure_dubtrack_dub_mock,
        ensure_dubtrack_skip_mock,
        event,
        func
):
    event = event(data=am.MagicMock(), dubtrack_backend=am.MagicMock())
    await history_handler(event=event)

    if func is None:
        return

    called_func = {
        'edp': ensure_dubtrack_playing_mock,
        'edd': ensure_dubtrack_dub_mock,
        'eds': ensure_dubtrack_skip_mock,
    }[func]
    called_func.assert_awaited_once_with(event=event, conn=db_conn)


@pytest.mark.asyncio
async def test_availability_handler():
    await availability_handler(event=None)
