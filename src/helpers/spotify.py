import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
from dotenv import load_dotenv
import os
import logging

# Load environment variables from .env file
if os.path.exists('.env'):
    load_dotenv()
    CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID', 'your_client_id_here')
    CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET', 'your_client_secret_here')
else:
    CLIENT_ID = os.environ.get('SPOTIFY_CLIENT_ID', 'your_client_id_here')
    CLIENT_SECRET = os.environ.get('SPOTIFY_CLIENT_SECRET', 'your_client_secret_here')


# Authenticate with Spotify API
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=CLIENT_ID,
                                                           client_secret=CLIENT_SECRET))

def get_artist_from_spotify_link(spotify_link):
    """
    Extracts the artist(s) from a given Spotify track or album link.
    """
    # Extract the Spotify ID and type from the link
    match = re.search(r'spotify\.com/(track|album)/([a-zA-Z0-9]+)', spotify_link)
    if not match:
        logging.error(f'Invalid Spotify link: {spotify_link}')
        return None
    
    item_type = match.group(1)
    item_id = match.group(2)

    try:
        if item_type == 'track':
            track_info = sp.track(item_id)
            artists = [artist['name'] for artist in track_info['artists']]
            return ", ".join(artists)
        elif item_type == 'album':
            album_info = sp.album(item_id)
            artists = [artist['name'] for artist in album_info['artists']]
            return ", ".join(artists)
        else: 
            logging.error(f'Unsupported Spotify item type: {item_type}')
            return None
    except spotipy.exceptions.SpotifyException as e:
        logging.error(f'Spotify API error: {e}')
        return None