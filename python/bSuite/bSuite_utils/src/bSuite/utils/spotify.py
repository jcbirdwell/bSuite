def u2p(playlist_id: str) -> str:
    return f'spotify:playlist:{playlist_id}'


def t2u(track_id: str):
    return f'spotify:track:{track_id}'


def u2t(track_uri: str) -> str:
    return track_uri.split(':')[-1]


def l2u(spotify_link: str) -> str:
    # EX = https://open.spotify.com/track/1Xgg0bhjK57PJ6WLYOi3oY?si=0c8a18e405274770
    if 'https://open.spotify.com/' not in spotify_link:
        raise TypeError('Invalid link')

    spotify_link = spotify_link.removeprefix('https://open.spotify.com/').split('/')
    # EX => ['track', '1Xgg0bhjK57PJ6WLYOi3oY?si=0c8a18e405274770']

    if '?' in spotify_link[1]:
        spotify_link[1] = spotify_link[1].split('?')[0]
    # EX => ['track', '1Xgg0bhjK57PJ6WLYOi3oY']

    return f"spotify:{spotify_link[0]}:{spotify_link[1]}"       # EX => 'spotify:track:1Xgg0bhjK57PJ6WLYOi3oY'
