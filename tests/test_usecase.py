import pytest


@pytest.fixture
def mock_dubtrackws(mocker):
    return mocker.patch('mosbot.usecase.DubtrackWS')


@pytest.fixture
def mock_load_bot_data(mocker):
    return mocker.patch('mosbot.usecase.load_bot_data')


@pytest.mark.asyncio
async def test_save_history_songs_config_check(db_conn, mock_dubtrackws, mock_load_bot_data):
    pass
