import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import re
import os
import logging

# Authenticate with Spotify API
class SpotifyHelper:
    def __init__(self):
        self._sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=os.environ.get('SPOTIFY_CLIENT_ID'), 
                                                           client_secret=os.environ.get('SPOTIFY_CLIENT_SECRET')))

    def get_artist_from_spotify_link(self, spotify_link):
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
                track_info = self._sp.track(item_id)
                artists = [artist['name'] for artist in track_info['artists']]
                return ", ".join(artists)
            elif item_type == 'album':
                album_info = self._sp.album(item_id)
                artists = [artist['name'] for artist in album_info['artists']]
                return ", ".join(artists)
            else: 
                logging.error(f'Unsupported Spotify item type: {item_type}')
                return None
        except spotipy.exceptions.SpotifyException as e:
            logging.error(f'Spotify API error: {e}')
            return None