import sys

import pytest
from alembic.command import upgrade, downgrade
from alembic.config import Config

from mosbot.util import setup_logging, check_alembic_in_latest_version


@pytest.fixture
def logging_mock(mocker):
    return mocker.patch('mosbot.util.logging')


@pytest.fixture
def os_mock(mocker):
    return mocker.patch('mosbot.util.os')


@pytest.fixture
def sys_mock(mocker):
    return mocker.patch('mosbot.util.sys')


@pytest.mark.parametrize('debug', (True, False))
def test_setup_logging(logging_mock, os_mock, sys_mock, debug):
    except_hook = sys_mock.excepthook
    setup_logging(debug=debug)
    logging_mock.config.fileConfig.assert_called_once_with(
        os_mock.path.join.return_value,
        disable_existing_loggers=False,
    )
    if not debug:
        return

    assert sys_mock.excepthook != except_hook

    def ras():
        raise Exception('aaaa')

    try:
        ras()
    except Exception as e:
        ty, v, tb = sys.exc_info()
        sys_mock.excepthook(ty, v, tb)


def test_check_alembic_in_latest_version():
    config = Config('alembic.ini')
    downgrade(config, 'base')
    with pytest.raises(RuntimeError):
        check_alembic_in_latest_version()
    upgrade(config, 'head')
    check_alembic_in_latest_version()
