"""Add bot configuration table

Revision ID: 343c78c7a0b8
Revises: layout
Create Date: 2018-02-23 10:06:09.766820+00:00

"""
# revision identifiers, used by Alembic.
import logging

import sqlalchemy as sa
import sqlalchemy.dialects.postgresql as psa
from alembic import op
from sqlalchemy.engine import Connection

from mosbot.db import BotConfig, BotData, Playback

revision = '343c78c7a0b8'
down_revision = 'layout'
branch_labels = None
depends_on = None
logger = logging.getLogger(__name__)


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('bot_data',
                    sa.Column('id', sa.Integer(), nullable=False),
                    sa.Column('key', sa.Text(), nullable=False),
                    sa.Column('value', sa.JSON(), nullable=False),
                    sa.PrimaryKeyConstraint('id'),
                    sa.UniqueConstraint('key')
                    )
    op.alter_column('playback', 'start',
                    existing_type=psa.TIMESTAMP(),
                    nullable=False)
    op.alter_column('playback', 'track_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    op.alter_column('track', 'extid',
                    existing_type=sa.TEXT(),
                    nullable=False)
    op.alter_column('track', 'length',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    op.alter_column('track', 'name',
                    existing_type=sa.TEXT(),
                    nullable=False)
    op.alter_column('track', 'origin',
                    existing_type=psa.ENUM('youtube', 'soundcloud', name='origin'),
                    nullable=False)
    op.alter_column('user', 'dtid',
                    existing_type=sa.TEXT(),
                    nullable=False)
    op.alter_column('user', 'username',
                    existing_type=sa.TEXT(),
                    nullable=False)
    op.alter_column('user_action', 'action',
                    existing_type=psa.ENUM('skip', 'upvote', 'downvote', name='action'),
                    nullable=False)
    op.alter_column('user_action', 'playback_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    op.alter_column('user_action', 'ts',
                    existing_type=psa.TIMESTAMP(),
                    nullable=False)
    # ### end Alembic commands ###
    bind: Connection = op.get_bind()
    query = sa.select([sa.extract('epoch', Playback.c.start)]).order_by(sa.desc(Playback.c.start)).limit(1)
    try:
        last_timestamp, = bind.execute(query).first()
        query = sa.insert(BotData).values({'key': BotConfig.last_saved_history, 'value': last_timestamp})
        op.execute(query)
    except TypeError:
        query = sa.insert(BotData).values({'key': BotConfig.last_saved_history, 'value': 0})
        op.execute(query)
        logger.info(f'There is no previous history, setting {BotConfig.last_saved_history} to 0')


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column('user_action', 'ts',
                    existing_type=psa.TIMESTAMP(),
                    nullable=True)
    op.alter_column('user_action', 'playback_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)
    op.alter_column('user_action', 'action',
                    existing_type=psa.ENUM('skip', 'upvote', 'downvote', name='action'),
                    nullable=True)
    op.alter_column('user', 'username',
                    existing_type=sa.TEXT(),
                    nullable=True)
    op.alter_column('user', 'dtid',
                    existing_type=sa.TEXT(),
                    nullable=True)
    op.alter_column('track', 'origin',
                    existing_type=psa.ENUM('youtube', 'soundcloud', name='origin'),
                    nullable=True)
    op.alter_column('track', 'name',
                    existing_type=sa.TEXT(),
                    nullable=True)
    op.alter_column('track', 'length',
                    existing_type=sa.INTEGER(),
                    nullable=True)
    op.alter_column('track', 'extid',
                    existing_type=sa.TEXT(),
                    nullable=True)
    op.alter_column('playback', 'track_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)
    op.alter_column('playback', 'start',
                    existing_type=psa.TIMESTAMP(),
                    nullable=True)
    op.drop_table('bot_data')
    # ### end Alembic commands ###
