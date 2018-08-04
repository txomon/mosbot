# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

from abot.dubtrack import DubtrackBotBackend
from json import JSONDecodeError

from mosbot.db import BotConfig

"""This file contains"""

import asyncio
import json
import pprint
import typing

import click

import abot.cli as cli
from abot.bot import Bot, current_event, MessageEvent
from mosbot import config as mos_config
from mosbot.handler import availability_handler, history_handler
from mosbot.query import load_bot_data, save_bot_data
from mosbot.usecase import save_history_songs
from mosbot.util import setup_logging, check_alembic_in_latest_version


class BotConfigValueType(click.ParamType):
    """This is a custom type created to receive BotConfig parameters and validate them."""

    name = 'json'

    def convert(self, value, param, ctx):  # noqa D103  TODO
        success, converted = self.try_json(value)
        if success:
            return converted
        return value

    def try_json(self, value):  # noqa D103  TODO
        try:
            return True, json.loads(value)
        except JSONDecodeError:
            return False, None


@cli.group(invoke_without_command=True)
async def botcmd():
    """Group in which the commands available only through the bot are."""
    pass  # pragma: no cover


@botcmd.command()
async def atest():  # noqa D103
    """Test (ping/pong) like to check if it works"""
    event: MessageEvent = current_event.get()
    await event.reply('atest')


@botcmd.command()
@click.option('--debug/--no-debug', '-d/ ', default=False)
async def history_sync(debug):
    """Triggers a history sync task. It should be really controlled so that users cannot trigger it alone."""
    event: MessageEvent = current_event.get()
    if not event:
        check_alembic_in_latest_version()
        setup_logging(debug)
    await save_history_songs()


@botcmd.command()
@click.option('--value', '-v', type=BotConfigValueType())
@click.argument('key', type=click.Choice(BotConfig.configs))
async def config(key, value):
    """Set new value for key in the database.

    This function is used to override internals, needs to be controlled, as someone could really break something here.
    """
    event: MessageEvent = current_event.get()
    if value:
        await save_bot_data(key, value)
        await event.reply(f'Saved key {key}')
    else:
        value = await load_bot_data(key)
        await event.reply(f'Value for key {key} is `{json.dumps(value)}`')


@click.group(invoke_without_command=True)
def botcli():
    """Group of commands that can only be executed from the command line."""
    pass  # pragma: no cover


@botcli.command()
def test():
    """Test command to see if it works."""
    click.echo('TEST')
    pprint.pprint(typing.get_type_hints(history_handler))


@botcli.command()
@click.option('--debug/--no-debug', '-d/ ', default=False)
@click.option('--room', '-r', nargs=1, default='master-of-soundtrack')
def run(debug, room):
    """Run the bot, this is the main command that is usually run in the server."""
    check_alembic_in_latest_version()
    setup_logging(debug)
    # Setup
    bot = Bot()
    dubtrack_backend = DubtrackBotBackend(room=room)
    dubtrack_backend.configure(username=mos_config.DUBTRACK_USERNAME, password=mos_config.DUBTRACK_PASSWORD)
    bot.attach_backend(backend=dubtrack_backend)
    bot.attach_command_group(botcmd)  #: Disabled until permissions are implemented

    bot.add_event_handler(func=history_handler)
    bot.add_event_handler(func=availability_handler)

    # Run
    loop = asyncio.get_event_loop()
    loop.run_until_complete(bot.run_forever())
