def u2p(playlist_id: str) -> str:
    return f'spotify:playlist:{playlist_id}'


def t2u(track_id):
    return f'spotify:track:{track_id}'


def u2t(track_uri: str) -> str:
    return track_uri.split(':')[-1]
