# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, unicode_literals

import asyncio
import weakref

"""db is the entities of all the application, there is no business logic (like actions on the entities), but just
the entities that the datamodel has. It should not import anything from the rest of the file, only config allowed
to be able to connect to the database"""

import enum

import aiopg.sa as asa
import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psa
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import functions

from mosbot import config


class utcnow(functions.FunctionElement):  # noqa
    key = 'utcnow'
    type = sa.DateTime(timezone=True)


@compiles(utcnow, 'postgresql')
def _pg_utcnow(element, compiler, **kwargs):  # pragma: no cover
    return "(statement_timestamp() AT TIME ZONE 'utc')::TIMESTAMP WITH TIME ZONE"


ENGINE = weakref.WeakKeyDictionary()


async def get_engine(debug=False):  # noqa D103  TODO
    global ENGINE
    loop = asyncio.get_event_loop()
    if loop in ENGINE:
        return ENGINE[loop]
    eng = ENGINE[loop] = await asa.create_engine(config.DATABASE_URL, echo=debug)
    return eng


metadata = sa.MetaData()
"""This is a SQLAlchemy object in which register the tables we are planning to access"""

User = sa.Table('user', metadata,
                sa.Column('id', sa.Integer, primary_key=True, nullable=False),
                sa.Column('dtid', sa.Text, unique=True, nullable=False),
                sa.Column('username', sa.Text, nullable=False),
                sa.Column('country', sa.Text, nullable=True),
                )
"""User table that stores the users that are in MoS

  :param int id: User id, unique in the DB, not externally retrieved
  :param str dtid: User id, from dubtrack, used to know users that changed their usernames
  :param str username: User name from dubtrack, it may be changed, so dtid is used to identify users
  :param str country: Country of the user, TBD (ideally will enable blocked videos autoskip)
"""


class Origin(enum.Enum):
    """Dubtrack currently supports two backend, youtube and soundcloud."""

    youtube = 1
    soundcloud = 2


Track = sa.Table('track', metadata,
                 sa.Column('id', sa.Integer, primary_key=True, nullable=False),
                 sa.Column('length', sa.Integer, nullable=False),
                 sa.Column('origin', psa.ENUM(Origin), nullable=False),
                 sa.Column('extid', sa.Text, nullable=False),
                 sa.Column('name', sa.Text, nullable=False),
                 sa.UniqueConstraint('origin', 'extid')
                 )
"""Track table contains references to videos(youtube)/songs(soundcloud)

    They are unique by ID, however, there may be duplicates in that we play the same song from different uploaders or
    versions. Tracks are only saved once, in that there is a unique check of origin/extid.

    :param int id: Track id, unique in the DB, not externally generated
    :param int length: Track duration in seconds
    :param Origin origin: Source of the track (usually YouTube)
    :param str extid: The id of the track had in the source (usually the track id in YouTube)
    :param str name: The name of the track in the source (usually the track name in YouTube). It's not always useful,
    but it's convenient when speaking to humans
"""

Playback = sa.Table('playback', metadata,
                    sa.Column('id', sa.Integer, primary_key=True, nullable=False),
                    sa.Column('track_id', sa.ForeignKey('track.id'), nullable=False),
                    sa.Column('user_id', sa.ForeignKey('user.id'), nullable=True),
                    sa.Column('start', sa.DateTime, unique=True, nullable=False),
                    )
"""Playback table contains the time/user that has played a given :ref:`Track:

    Playback is one go of a given :ref:`track_id` played at :ref:`start` time, by :ref:`user_id`.

    :param int id: Playback id, unique in the DB, not externally generated
    :param int track_id: The :ref:`Track.id` of the track played
    :param int user_id: The :ref:`User.id` of the user that played the track
    :param int start: When this specific playback started
"""


class Action(enum.Enum):
    """Action is the kind of actions the user can do.

    It will be probably be changed to a table in the future.
    """

    skip = 1
    upvote = 2
    downvote = 3


UserAction = sa.Table('user_action', metadata,
                      sa.Column('id', sa.Integer, primary_key=True, nullable=False),
                      sa.Column('ts', sa.DateTime, nullable=False),
                      sa.Column('playback_id', sa.ForeignKey('playback.id'), nullable=False),
                      sa.Column('user_id', sa.ForeignKey('user.id'), nullable=True),
                      sa.Column('action', psa.ENUM(Action), nullable=False),
                      )
"""UserAction table contains the actions made by a user.

    It has an optional :ref:`user_id` because when retrieving actions from the history channel (once we have missed
    it live), we don't have data telling us who did what, but only if skipped or not and if downvoted or not.

    :param int id: Id of a UserAction, not externally generated
    :param datetime.Datetime ts: This is a datetime entry on when the action happened. Upvotes/Downvotes are usually
    during, and I think they can also be afterwards, and skips are generated when the message of a user skipping
    arrives. Also, skips gathered from history have the date when the next song started, so even if we don't know
    who skipped a song, we can know when she did it.
    :param int playback_id: What playback this refers to. This could have maybe been stored without a reference, and
    in fact, skips don't have a reference to the song they are skipping, but it is valuable data, because that way we
    don't need to correlate timestamps with playbacks.
    :param int user_id: What user did the action. We usually don't have this data on the past history, but this is the
    key to know if the bot was on already or not, because the only way to know who did what is by being in the channel.
"""

BotData = sa.Table('bot_data', metadata,
                   sa.Column('id', sa.Integer, primary_key=True, nullable=False),
                   sa.Column('key', sa.Text, unique=True, nullable=False),
                   sa.Column('value', sa.JSON, nullable=False),
                   )
"""BotData contains configuration parameters of the bot. It's something I did to store random data, like what was the
last time we fetched history data.
"""


class BotConfig:
    """This are the keys used in :ref:`BotData`."""

    last_saved_history = 'last_saved_history'  #: Last timestamp history was gathered


BotConfig.configs = tuple(v for v in vars(BotConfig) if not v.startswith('__'))
