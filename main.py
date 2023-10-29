# import necessary modules
import time
import spotipy
from dotenv import load_dotenv
import os
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, request, url_for, session, redirect

#get client key and from .env file
load_dotenv()

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")

# initialize Flask app
app = Flask(__name__)

# set the name of the session cookie
app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'

# set a random secret key to sign the cookie
app.secret_key = 'u2rjklqewrx34*kncz'

# set the key for the token info in the session dictionary
TOKEN_INFO = 'token_info'

@app.route('/')
def login():
    # create a SpotifyOAuth instance and get the authorization URL
    auth_url = create_spotify_oauth().get_authorize_url()
    # redirect the user to the authorization URL
    return redirect(auth_url)

# route to handle the redirect URI after authorization
@app.route('/callback')
def redirect_page():
    # clear the session
    session.clear()
    # get the authorization code from the request parameters
    code = request.args.get('code')
    # exchange the authorization code for an access token and refresh token
    token_info = create_spotify_oauth().get_access_token(code)
    # save the token info in the session
    session[TOKEN_INFO] = token_info
    # redirect the user to the recommend music route
    return redirect(url_for('recommend_music',_external=True))

# route to create a new playlist of recommended songs
@app.route('/soundiscover')
def recommend_music():
    
    try: 
        # get the token info from the session
        token_info = get_token()
    except:
        # if the token info is not found, redirect the user to the login route
        print('User not logged in')
        return redirect("/")

    # create a Spotipy instance with the access token
    sp = spotipy.Spotify(auth=token_info['access_token'])
    
    # get user top tracks and artists
    top_tracks = sp.current_user_top_tracks(time_range='short_term',limit=25)['items']
    top_artists = sp.current_user_top_artists()['items']
    
    # finds top tracks that are not among the user's favorite artists 
    seed_tracks = list()
    for track in top_tracks:
        no_seed = False
        for artist in top_artists:
            if track['artists'][0]['id'] == artist['id']:
                no_seed = True
                break
            
        if no_seed == False:
            seed_tracks.append(track)
            
        # ends program if no seed tracks are found 
        if len(seed_tracks) < 1:
            return "No seed track"

    # get track ids from seed tracks
    seed_tracks_ids = [track['id'] for track in seed_tracks]

    # get recommended tracks with 5 seed tracks at a time
    recommended_tracks = list()
    x = 5
    while x < len(seed_tracks_ids):
        recommended_tracks += sp.recommendations(seed_tracks=seed_tracks_ids[x - 5: x], limit=10)['tracks']
        x += 5
    
    # create playlist to add recommended songs
    user_id = sp.current_user()['id']
    playlist_name = 'SD Recommendation-'+ str(int(time.time()))
    sp.user_playlist_create(user=user_id, name=playlist_name, public=False, description='Created by Soundiscover')

    # get the playlist id of the new playlist
    current_playlists = sp.current_user_playlists()['items']
    for playlist in current_playlists:
        if playlist['name'] == playlist_name:
            playlist_id = playlist['id']
            break
        
    #add recommended tracks to new playlist
    sp.user_playlist_add_tracks(user=user_id, playlist_id=playlist_id, tracks=[t['id'] for t in recommended_tracks] )

    return "Succesful"


def get_token():
    token_info = session.get(TOKEN_INFO, None)
    if not token_info:
        # if the token info is not found, redirect the user to the login route
        redirect(url_for('login', _external=False))
    
    # check if the token is expired and refresh it if necessary
    now = int(time.time())

    is_expired = token_info['expires_at'] - now < 60
    if(is_expired):
        spotify_oauth = create_spotify_oauth()
        token_info = spotify_oauth.refresh_access_token(token_info['refresh_token'])
        session[TOKEN_INFO] = token_info

    return token_info

def create_spotify_oauth():
    return SpotifyOAuth(
        client_id = CLIENT_ID,
        client_secret = CLIENT_SECRET,
        redirect_uri = url_for('redirect_page', _external=True),
        scope='user-top-read playlist-modify-public playlist-modify-private playlist-read-private playlist-read-collaborative'
    )

app.run()