# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import sys

import logging.config
import os
import pprint
import traceback
from alembic.config import Config
from alembic.runtime.environment import EnvironmentContext
from alembic.script import ScriptDirectory
from functools import wraps

logger = logging.getLogger(__name__)


def setup_logging(debug=False):
    """Setup logging app wide, pass parameter to enable more verbosity

    :param bool debug: If we want it verbose or not, defaults to False
    :return:
    """
    filename = 'logging.conf' if not debug else 'logging-debug.conf'
    logging.config.fileConfig(os.path.join(os.path.dirname(__file__), filename), disable_existing_loggers=False)
    if debug:
        logger.debug('Level is debug now')

        # logging.getLogger('abot.dubtrack.layer3').setLevel(logging.DEBUG)
        def excepthook(type, value, tb):
            traceback.print_exception(type, value, tb)

            while tb.tb_next:
                tb = tb.tb_next

            logger.error(f'Locals: {pprint.pformat(tb.tb_frame.f_locals)}')

        sys.excepthook = excepthook
    else:
        logger.info('Level is info now')


def check_alembic_in_latest_version():
    """Makes sure we are using the latest alembic"""
    config = Config('alembic.ini')
    script = ScriptDirectory.from_config(config)
    heads = script.get_revisions(script.get_heads())
    head = heads[0].revision
    current_head = None

    def _f(rev, context):
        nonlocal current_head
        current_head = rev[0] if rev else 'base'
        return []

    with EnvironmentContext(config, script, fn=_f):
        script.run_env()

    if head != current_head:
        raise RuntimeError(f'Database is not upgraded to latest head {head} from {current_head}')


def retries(*, tries=10, final_message):
    def retry(func):
        @wraps(func)
        async def wrapper(*a, **kw):
            for try_num in range(1, tries + 1):
                try:
                    return await func(*a, **kw)
                except Exception:
                    message = f'Call {try_num} to function {func} failed'
                    if try_num == 1:
                        logger.exception(message)
                    elif try_num == tries:
                        pass  # This finishes the loop
                    else:
                        logger.info(message)
            else:
                logger.exception(str.format(final_message, *a, **kw))
        return wrapper
    return retry
