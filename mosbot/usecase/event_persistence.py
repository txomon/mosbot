import datetime
import logging
from abot.dubtrack import DubtrackEntity, DubtrackPlaying, DubtrackSkip, DubtrackDub

from mosbot.db import Origin, Action
from mosbot.query import get_user, save_user, get_track, save_track, get_playback, save_playback, get_last_playback, \
    save_user_action, get_dub_action

logger = logging.getLogger(__name__)


async def ensure_dubtrack_entity(user: DubtrackEntity, *, conn=None):
    """Make sure that a dubtrack entity is registered in the database"""
    dtid = user.id
    username = user.username
    user = await get_user(user_dict={'dtid': dtid}, conn=conn)
    if not user:
        user = await save_user(user_dict={'dtid': dtid, 'username': username}, conn=conn)
        if not user:
            raise ValueError('Impossible to create/save the user')
    return user


async def ensure_dubtrack_playing(event: DubtrackPlaying, *, conn=None):
    """Make sure that we have the track and the playback in the database"""
    user = await ensure_dubtrack_entity(event.sender)
    user_id = user['id']
    track_entry = {
        'length': event.length.total_seconds(),
        'origin': getattr(Origin, event.song_type),
        'extid': event.song_external_id,
        'name': event.song_name,
    }
    track = await get_track(track_dict=track_entry, conn=conn)
    if not track:
        track = await save_track(track_dict=track_entry, conn=conn)
        if not track:
            raise ValueError(f"Couldn't save track {track_entry}")
    track_id = track['id']

    playback_entry = {
        'user_id': user_id,
        'track_id': track_id,
        'start': event.played,
    }

    playback = await get_playback(playback_dict=playback_entry, conn=conn)
    if not playback:
        await save_playback(playback_dict=playback_entry, conn=conn)


async def ensure_dubtrack_skip(event: DubtrackSkip, *, conn=None):
    """Make sure to record an skip in the last playback we have.

    Warning: This can put at risk db integrity because we don't know what is the song it skipped. We are entirely
    relying on that dubtrack backend will send first a chat skip event and then a playing event. Also, this may have
    a race condition because of the asyncronicity of the library/bot. We may end up processing this event untimed and
    wrong... Hope there is not such race condition for now.
    """
    playback = await get_last_playback(conn=conn)
    user = await ensure_dubtrack_entity(event.sender)
    playback_id = playback['id']
    user_id = user['id']
    await save_user_action(user_action_dict={
        'playback_id': playback_id,
        'user_id': user_id,
        'action': Action.skip,
        'ts': datetime.datetime.utcnow(),
    })


async def ensure_dubtrack_dub(event: DubtrackDub, *, conn=None):
    """Ensure that a user action (user upvote/downvote) is being stored. Because we don't have all the track info,
    we cannot be 100% sure of the track, but we check start time, that is unique, if this checks, better to lose the
    data than to put a wrong dub from a person"""
    playback = await get_last_playback(conn=conn)
    if not event.played == playback['start']:
        logger.error(f'Last saved playback is {playback["start"]} but this vote is for {event.played}')
        return
    playback_id = playback['id']

    user = await ensure_dubtrack_entity(event.sender, conn=conn)
    user_id = user['id']
    action_type = get_dub_action(event.dubtype)

    user_action_dict = {
        'ts': datetime.datetime.utcnow(),
        'playback_id': playback_id,
        'user_id': user_id,
        'action': action_type,
    }
    await save_user_action(user_action_dict=user_action_dict, conn=conn)
