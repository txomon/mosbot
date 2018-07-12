# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from json import JSONDecodeError

from mosbot.db import BotConfig

"""This file contains"""

import asyncio
import json
import pprint
import typing

import click

import abot.cli as cli
import abot.dubtrack as dt
from abot.bot import Bot
from mosbot import config as mos_config
from mosbot.handler import availability_handler, history_handler
from mosbot.query import load_bot_data, save_bot_data
from mosbot.usecase import save_history_songs
from mosbot.util import setup_logging, check_alembic_in_latest_version


class BotConfigValueType(click.ParamType):
    """This is a custom type created to receive BotConfig parameters and validate them"""
    name = 'json'

    def convert(self, value, param, ctx):
        success, converted = self.try_json(value)
        if success:
            return converted
        return value

    def try_json(self, value):
        try:
            return True, json.loads(value)
        except JSONDecodeError:
            return False, None


@cli.group(invoke_without_command=True)
async def botcmd():
    """Group in which the commands available only through the bot are"""
    pass  # pragma: no cover


@botcmd.command()
async def atest():
    """Test (ping/pong) like to check if it works"""
    print('aTest')


@botcmd.command()
@click.option('--debug/--no-debug', '-d/ ', default=False)
async def history_sync(debug):
    """Triggers a history sync task. It should be really controlled so that users cannot trigger it alone."""
    check_alembic_in_latest_version()
    setup_logging(debug)
    await save_history_songs()


@botcmd.command()
@click.option('--value', '-v', type=BotConfigValueType())
@click.argument('key', type=click.Choice(BotConfig.configs))
async def config(key, value):
    """Set new value for key in the database (used to override internals, needs to be controlled, as someone could
    really break something here"""
    if value:
        await save_bot_data(key, value)
        cli.echo(f'Saved key {key}')
    else:
        value = await load_bot_data(key)
        cli.echo(f'Value for key {key} is `{json.dumps(value)}`')


@click.group(invoke_without_command=True)
def botcli():
    """Group of commands that can only be executed from the command line"""
    pass  # pragma: no cover


@botcli.command()
def test():
    """Test command to see if it works"""
    click.echo('TEST')
    pprint.pprint(typing.get_type_hints(history_handler))


@botcli.command()
@click.option('--debug/--no-debug', '-d/ ', default=False)
def run(debug):
    """Run the bot, this is the main command that is usually run in the server"""
    check_alembic_in_latest_version()
    setup_logging(debug)
    # Setup
    bot = Bot()
    dubtrack_backend = dt.DubtrackBotBackend()
    dubtrack_backend.configure(username=mos_config.DUBTRACK_USERNAME, password=mos_config.DUBTRACK_PASSWORD)
    bot.attach_backend(backend=dubtrack_backend)
    # bot.attach_command_group(botcmd) #: Disabled until permissions are implemented

    bot.add_event_handler(func=history_handler)
    bot.add_event_handler(func=availability_handler)

    # Run
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.run_forever())
