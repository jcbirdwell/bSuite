import browser_cookie3  # only required if sp_dc token isn't manually provided
import requests


def get_cookies():
    browser = browser_cookie3.Firefox(domain_name='.spotify.com')
    return browser.load()


def get_web_access_token(sp_dc: str | None = None) -> str:
    """Obtains a web player access token either using the specified sp_dc token or by extracting the sp_dc cookie token
    from the browsers local storage. If not manually providing the sp_dc token, user MUST be logged into the spotify
    web player prior to running and cookie storage access must be granted to python (if prompted on function run)"""

    # url used by web player to obtain access token
    url = 'https://open.spotify.com/get_access_token?reason=transport&productType=web_player'

    # checks if sp_dc is provided, if not attempts to load cached cookies (hopefully including the sp_dc token)
    sp_dc = sp_dc if sp_dc else get_cookies()
    cookies = {'sp_dc': sp_dc}

    # submits the access token request and parses the json response to dict
    response = requests.get(url, cookies=cookies).json()

    # grabs token from response dict
    access_token = response.get('accessToken')
    return access_token


def get_username(web_access_token: str):
    """Additional request that finds username associated with web access token in the case one isn't provided"""

    # requests profile from standard spotify api and parses as a dict
    response = requests.get(
        url='https://api.spotify.com/v1/me',
        headers={'Authorization': f'Bearer {web_access_token}'}
    ).json()
    return response.get('id')


def get_friend_activity(web_access_token: str):
    """Uses the access token to request the activity feed. Returns as a list of dicts, each representing a friend"""

    # url for the special web player endpoint that provides friend activity
    url = 'https://guc-spclient.spotify.com/presence-view/v1/buddylist'

    # web access token packaged as an authorization header
    header = {'Authorization': f'Bearer {web_access_token}'}

    # endpoint response as a dict
    response = requests.get(url, headers=header).json()

    # returns desired value from response dict
    return response.get('friends')


def get_following(web_access_token: str, username: str | None = None) -> list[dict]:
    """Uses a web access token to get a list of user dicts that follow the provided username. If no username is
    provided, the function will request and use the username associated with the token"""

    # Obtains username associated with the access token in the case none is provided.
    if not username:
        username = get_username(web_access_token)

    # url for web player endpoint that returns a list of users followed by the given user.
    url = f'https://spclient.wg.spotify.com/user-profile-view/v3/profile/{username}/following?market=from_token'

    # formatting web access token as an authorization header
    header = {'Authorization': f'Bearer {web_access_token}'}

    # sends request and parses json response
    response = requests.get(url, headers=header).json()

    # returns desired values from response dict
    return response.get('profiles')


def get_followers(web_access_token: str, username: str | None = None) -> list[dict]:
    """Uses a web access token to get a list of user dicts that the provided username follows. If no username is
    provided, the function will request and use the username associated with the token"""

    # Obtains username associated with the access token in the case none is provided.
    if not username:
        username = get_username(web_access_token)

    # url for web player endpoint that returns a list of users that follow the given user.
    url = f'https://spclient.wg.spotify.com/user-profile-view/v3/profile/{username}/followers?market=from_token'

    # formatting web access token as an authorization header
    header = {'Authorization': f'Bearer {web_access_token}'}

    # sends request and parses json response
    response = requests.get(url, headers=header).json()

    # returns desired values from response dict
    return response.get('profiles')
