import datetime
import logging
from abot.dubtrack import DubtrackEntity, DubtrackPlaying, DubtrackSkip, DubtrackDub

from mosbot.db import Origin, Action
from mosbot.query import get_last_playback, \
    save_user_action, get_dub_action, get_or_save_user, get_or_save_track, get_or_save_playback

logger = logging.getLogger(__name__)


async def ensure_dubtrack_entity(*, user: DubtrackEntity, conn=None):
    """Make sure that a dubtrack entity is registered in the database"""
    user_dict = {
        'dtid': user.id,
        'username': user.username,
    }
    return await get_or_save_user(user_dict=user_dict, conn=conn)


async def ensure_dubtrack_playing(*, event: DubtrackPlaying, conn=None):
    """Make sure that we have the track and the playback in the database"""
    user = await ensure_dubtrack_entity(user=event.sender, conn=conn)
    user_id = user['id']
    track_dict = {
        'length': event.length.total_seconds(),
        'origin': getattr(Origin, event.song_type),
        'extid': event.song_external_id,
        'name': event.song_name,
    }
    track = await get_or_save_track(track_dict=track_dict, conn=conn)
    track_id = track['id']

    playback_dict = {
        'user_id': user_id,
        'track_id': track_id,
        'start': event.played,
    }
    await get_or_save_playback(playback_dict=playback_dict, conn=conn)


async def ensure_dubtrack_skip(*, event: DubtrackSkip, conn=None):
    """Make sure to record an skip in the last playback we have.

    Warning: This can put at risk db integrity because we don't know what is the song it skipped. We are entirely
    relying on that dubtrack backend will send first a chat skip event and then a playing event. Also, this may have
    a race condition because of the asyncronicity of the library/bot. We may end up processing this event untimed and
    wrong... Hope there is not such race condition for now.
    """
    playback = await get_last_playback(conn=conn)
    user = await ensure_dubtrack_entity(user=event.sender, conn=conn)
    playback_id = playback['id']
    user_id = user['id']
    await save_user_action(user_action_dict={
        'playback_id': playback_id,
        'user_id': user_id,
        'action': Action.skip,
        'ts': datetime.datetime.utcnow(),
    }, conn=conn)


async def ensure_dubtrack_dub(*, event: DubtrackDub, conn=None):
    """Ensure that a user action (user upvote/downvote) is being stored. Because we don't have all the track info,
    we cannot be 100% sure of the track, but we check start time, that is unique, if this checks, better to lose the
    data than to put a wrong dub from a person"""
    playback = await get_last_playback(conn=conn)
    if not event.played == playback['start']:
        logger.error(f'Last saved playback is {playback["start"]} but this vote is for {event.played}')
        return
    playback_id = playback['id']

    user = await ensure_dubtrack_entity(user=event.sender, conn=conn)
    user_id = user['id']
    action_type = get_dub_action(event.dubtype)

    user_action_dict = {
        'ts': datetime.datetime.utcnow(),
        'playback_id': playback_id,
        'user_id': user_id,
        'action': action_type,
    }
    await save_user_action(user_action_dict=user_action_dict, conn=conn)
