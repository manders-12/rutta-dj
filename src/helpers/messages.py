import re
import logging
import time
from datetime import datetime, timezone, timedelta
from config.config import Config
from helpers.embeds import EmbedsHelper
from helpers.spotify import SpotifyHelper
import inflect

class MessagesHelper:
    def __init__(self, config : Config, embedsHelper : EmbedsHelper, spotifyHelper : SpotifyHelper):
        self.config = config
        self.embedsHelper = embedsHelper
        self.spotifyHelper = spotifyHelper
        self.db = config.get_db()
        self.vars = config.get_vars()
    
    async def process_message(self, message):
        if str(message.author.global_name).lower() != self.vars['CONTROLLING_USER']:
            return False
        
        if message.channel.name == self.vars['TRACK_LIST_CHANNEL']:
            return await self._process_track_list_message(message)
        elif message.channel.name == self.vars['MUSIC_REVIEW_CHANNEL']:
            return await self._process_music_review_message(message)
        
    async def _process_track_list_message(self, message): 
        # Expecting format:
        # Genre - Tag\nhttps://www.youtube.com/watch?v=4hz68I4BRMA
        # OR:
        # @Genre[s] - Tag\nhttps://www.youtube.com/watch?v=4hz68I4BRMA
        logging.info(f'Received message from {message.author.global_name} in {self.vars['TRACK_LIST_CHANNEL']}: {message.content}')
        if (message.created_at + timedelta(seconds = 60) > datetime.now(timezone.utc)): time.sleep(5) #Pray the embed is generated :)
        try:
            text = message.content.strip()
            lines = text.split('\n')
            if len(lines) < 2:
                logging.error(f'Invalid format in message: {text}')
                return False
            
            genre_tag_line = lines[0].strip().split('-')
            if len(genre_tag_line) < 2:
                logging.error(f'Invalid genre-tag format in message: {text}')
                return False
            genres = re.findall(r'<@&\d+>', genre_tag_line[0])
            for i, genre in enumerate(genres):
                role_id = re.findall(r"<@&(\d+)>", genre)
                role = message.guild.get_role(int(role_id[0]))
                if role:
                    genres[i] = role.name
                else:
                    logging.error(f'Role {role_id[0]} not found: {message.content}')
                    return False

            if not genres:
                genres = genre_tag_line[0].strip().split('/') if '/' in genre_tag_line[0] else genre_tag_line[0].strip().split('\\') if '\\' in genre_tag_line[0] else genre_tag_line[0].strip().split(' ')
            if len(genres) < 2:
                genres.append(None)  # Ensure we have at least two genres
            tag = genre_tag_line[-1].strip()
            
            if message.embeds:
                embed = message.embeds[0]
                title, author, link = self.embedsHelper.parse_embed(embed)
            else:
                logging.error(f'Message {message.content} does not contain an embed.')
                return False
            if not title:
                logging.error(f'Missing title in replied message: {message.content}')
                return False
            if not link:
                logging.error(f'Missing link in replied message: {message.content}')
                return False
            if not author:
                author = self.spotifyHelper.get_artist_from_spotify_link(link)
            if not author:
                logging.error(f'Missing author in replied message: {message.content}') 
                return False
            
            p = inflect.engine()
            
            tag = p.singular_noun(tag)
            self.db.insert_recommendation(message.id, author, title, link, genres, tag)
            logging.info(f'Recommendation inserted: {title} by {author} ({link}) with genres {genres} and tag {tag}')
            curr_time = datetime.now(timezone.utc)
            diff = curr_time - message.created_at
            if diff.total_seconds() < 360:
                embed = self.embedsHelper.create_recommendation_embed(title, author, link, genres, tag)
                await message.channel.send(embed=embed)

        except Exception as e:
            logging.error(f'Error processing track list message: {e}')
            return False

    async def _process_music_review_message(self, message):
        # If Rutta is rating a track, he should be replying to a message with the song link
        # This assumes that the embed is in the replied message and has already been generated. Might break if embed isn't generated or there's a lot of lag
        if not message.reference:
            logging.error(f'Message {message.id} is not a reply to a recommendation.')
            return False
        
        try:
            #look for the replied message and embed and parse it if present
            replied_message = await message.channel.fetch_message(message.reference.message_id)
            if not replied_message.embeds:
                logging.error(f'Replied message {replied_message.id} does not contain an embed.')
                return False
            embed = replied_message.embeds[0]
            title, author, link = self.embedsHelper.parse_embed(embed)
            if not title:
                logging.error(f'Missing title in replied message: {replied_message.content}')
                return False
            if not link:
                logging.error(f'Missing link in replied message: {replied_message.content}')
                return False
            if not author:
                author = self.spotifyHelper.get_artist_from_spotify_link(link)
            if not author:
                logging.error(f'Missing author in replied message: {replied_message.content}')
                return False
            
            # Check if we're looking at an album or a track
            # Review format expected:

            # Title - Rating\nExplanation
            # Example: "Track Name - 5\nThis track is amazing!"

            # OR
            
            # Rating\nExplanation
            # Example: "5\nThis track is amazing!"
            # use re to find all ratings and explanations, if findall returns more than one and the title contains album or discography, assume it's an album review
            # This regex matches: optional title, rating, and explanation
            # Example: "Track Title - 5\nExplanation" or "5\nExplanation"

            #WARNING CURSED REGEX HIDE YOUR EYES I'M SO SORRY
            tracks_to_process = re.findall(r"(?:^|\n)(?:(.+?)\s*-\s*)?(\d+(?:\.\d+)?)\n(.+?)(?=\n(?:.+?\s*-\s*)?\d+(?:\.\d+)?\n|$)", message.content)
            if 'album' in title.lower() or 'discography' in title.lower() or len(tracks_to_process) > 1:
                logging.info(f'Processing album recommendation: {title}')
            for idx, track in enumerate(tracks_to_process):
                track_name, rating, explanation = track
                if not track_name:
                    track_name = title
                if not rating or not explanation:
                    logging.error(f'Missing rating or explanation in message: {message.content}')
                    return False
                #If it's an album the title might start with Track 1 - track_name or Track 1: track_name. We want to strip the Track [Integer] -  or Track [Integer]: part
                track_name = re.sub(r'^Track \d+ - |^Track \d+: ', '', track_name.strip())
                unique_id = f"{message.id}-{idx}" if len(tracks_to_process) > 1 else message.id
                self.db.insert_rating(unique_id, replied_message.author.global_name, track_name, link, rating, explanation)
                embed = self.embedsHelper.create_rating_embed(track_name, author, link, rating, explanation)
                logging.info(f'Rating inserted: {track_name} by {author} ({link}) with rating {rating} and explanation "{explanation}"')
                curr_time = datetime.now(timezone.utc)
                diff = curr_time - message.created_at
                if diff.total_seconds() < 360:
                    await message.channel.send(embed=embed)
            return True
        except Exception as e:
            logging.error(f'Error processing music review message: {e}')
            return False
        

# import re
# import logging
# import time
# from datetime import datetime, timezone, timedelta
# from helpers.spotify import get_artist_from_spotify_link

# # def extract_link(text):
# #     match = re.search(r'(https?://\S+)', text)
# #     return match.group(1) if match else None

# # def parse_rating(text):
# #     rating, explanation = None, None
# #     try:
# #         lines = text.split('\n')
# #         reviewI = None
# #         for i, line in enumerate(lines):
# #             parts = line.split('-')
# #             if len(parts) > 1 and parts[-1].strip().isdigit():
# #                 rating = parts[-1].strip()
# #                 reviewI = i + 1
# #                 break
# #         if reviewI is not None and reviewI < len(lines):
# #             explanation = '\n'.join(lines[reviewI:]).strip()
# #     except Exception as e:
# #         logging.error(f'Error parsing rating: {e}')
# #         rating, explanation = None, None
# #     return rating, explanation


# # def parse_recommendation(text):
# #     try:
# #         lines = text.split('\n')
# #         parts = lines[0].split('-')
# #         tag = parts[-1].strip()
# #         genre = "-".join(parts[0:-1]).strip()
# #     except Exception as e:
# #         logging.error(f'Error parsing recommendation: {e}')
# #         genre, tag = None, None
# #     return genre, tag


# def parse_embed(embed):
#     try:
#         title = embed.title if embed.title else ''
#         author = embed.author.name if embed.author else embed.footer.text if embed.footer else embed.description if embed.description else embed.fields[0].value if embed.fields else ''
#         if author.endswith(' - Topic'):
#             author = author.rstrip(' - Topic')
#         link = embed.url if hasattr(embed, 'url') else None
#     except Exception as e:
#         logging.error(f'Error parsing embed: {e}')
#         title, author, link = None, None, None
#     return title, author, link

# async def process_message(message):
#     if str(message.author.global_name).lower() != config.CONTROLLING_USER:
#         return False
    
#     if message.channel.name == config.TRACK_LIST_CHANNEL:
#         return await process_track_list_message(message)
#     elif message.channel.name == config.MUSIC_REVIEW_CHANNEL:
#         return await process_music_review_message(message)
    
# async def process_track_list_message(message): 
#     # Expecting format:
#     # Genre - Tag\nhttps://www.youtube.com/watch?v=4hz68I4BRMA
#     # OR:
#     # @Genre[s] - Tag\nhttps://www.youtube.com/watch?v=4hz68I4BRMA
#     logging.info(f'Received message from {message.author.global_name} in {config.TRACK_LIST_CHANNEL}: {message.content}')
#     if (message.created_at + timedelta(seconds = 60) > datetime.now(timezone.utc)): time.sleep(5) #Pray the embed is generated :)
#     try:
#         text = message.content.strip()
#         lines = text.split('\n')
#         if len(lines) < 2:
#             logging.error(f'Invalid format in message: {text}')
#             return False
        
#         genre_tag_line = lines[0].strip().split('-')
#         if len(genre_tag_line) < 2:
#             logging.error(f'Invalid genre-tag format in message: {text}')
#             return False
#         genres = re.findall(r'<@&\d+>', genre_tag_line[0])
#         for i, genre in enumerate(genres):
#             role_id = re.findall(r"<@&(\d+)>", genre)
#             role = message.guild.get_role(int(role_id[0]))
#             if role:
#                 genres[i] = role.name
#             else:
#                 logging.error(f'Role {role_id[0]} not found: {message.content}')
#                 return False

#         if not genres:
#             genres = genre_tag_line[0].strip().split('/') if '/' in genre_tag_line[0] else genre_tag_line[0].strip().split('\\') if '\\' in genre_tag_line[0] else genre_tag_line[0].strip().split(' ')
#         if len(genres) < 2:
#             genres.append(None)  # Ensure we have at least two genres
#         tag = genre_tag_line[-1].strip()
        
#         if message.embeds:
#             embed = message.embeds[0]
#             title, author, link = parse_embed(embed)
#         else:
#             logging.error(f'Message {message.content} does not contain an embed.')
#             return False
#         if not title:
#             logging.error(f'Missing title in replied message: {message.content}')
#             return False
#         if not link:
#             logging.error(f'Missing link in replied message: {message.content}')
#             return False
#         if not author:
#             author = get_artist_from_spotify_link(link)
#         if not author:
#             logging.error(f'Missing author in replied message: {message.content}') 
#             return False
        
#         db.insert_recommendation(message.id, author, title, link, genres, tag)
#         logging.info(f'Recommendation inserted: {title} by {author} ({link}) with genres {genres} and tag {tag}')
#         curr_time = datetime.now(timezone.utc)
#         diff = curr_time - message.created_at
#         if diff.total_seconds() < 360:
#             embed = create_recommendation_embed(title, author, link, genres, tag)
#             await message.channel.send(embed=embed)

#     except Exception as e:
#         logging.error(f'Error processing track list message: {e}')
#         return False

# async def process_music_review_message(message):
#     # If Rutta is rating a track, he should be replying to a message with the song link
#     # This assumes that the embed is in the replied message and has already been generated. Might break if embed isn't generated or there's a lot of lag
#     if not message.reference:
#         logging.error(f'Message {message.id} is not a reply to a recommendation.')
#         return False
    
#     try:
#         #look for the replied message and embed and parse it if present
#         replied_message = await message.channel.fetch_message(message.reference.message_id)
#         if not replied_message.embeds:
#             logging.error(f'Replied message {replied_message.id} does not contain an embed.')
#             return False
#         embed = replied_message.embeds[0]
#         title, author, link = parse_embed(embed)
#         if not title:
#             logging.error(f'Missing title in replied message: {replied_message.content}')
#             return False
#         if not link:
#             logging.error(f'Missing link in replied message: {replied_message.content}')
#             return False
#         if not author:
#             author = get_artist_from_spotify_link(link)
#         if not author:
#             logging.error(f'Missing author in replied message: {replied_message.content}')
#             return False
        
#         # Check if we're looking at an album or a track
#         # Review format expected:

#         # Title - Rating\nExplanation
#         # Example: "Track Name - 5\nThis track is amazing!"

#         # OR
        
#         # Rating\nExplanation
#         # Example: "5\nThis track is amazing!"
#         # use re to find all ratings and explanations, if findall returns more than one and the title contains album or discography, assume it's an album review
#         # This regex matches: optional title, rating, and explanation
#         # Example: "Track Title - 5\nExplanation" or "5\nExplanation"

#         #WARNING CURSED REGEX HIDE YOUR EYES I'M SO SORRY
#         tracks_to_process = re.findall(r"(?:^|\n)(?:(.+?)\s*-\s*)?(\d+(?:\.\d+)?)\n(.+?)(?=\n(?:.+?\s*-\s*)?\d+(?:\.\d+)?\n|$)", message.content)
#         if 'album' in title.lower() or 'discography' in title.lower() or len(tracks_to_process) > 1:
#             logging.info(f'Processing album recommendation: {title}')
#         for idx, track in enumerate(tracks_to_process):
#             track_name, rating, explanation = track
#             if not track_name:
#                 track_name = title
#             if not rating or not explanation:
#                 logging.error(f'Missing rating or explanation in message: {message.content}')
#                 return False
#             #If it's an album the title might start with Track 1 - track_name or Track 1: track_name. We want to strip the Track [Integer] -  or Track [Integer]: part
#             track_name = re.sub(r'^Track \d+ - |^Track \d+: ', '', track_name.strip())
#             unique_id = f"{message.id}-{idx}" if len(tracks_to_process) > 1 else message.id
#             db.insert_rating(unique_id, replied_message.author.global_name, track_name, link, rating, explanation)
#             embed = create_rating_embed(track_name, author, link, rating, explanation)
#             logging.info(f'Rating inserted: {track_name} by {author} ({link}) with rating {rating} and explanation "{explanation}"')
#             curr_time = datetime.now(timezone.utc)
#             diff = curr_time - message.created_at
#             if diff.total_seconds() < 360:
#                 await message.channel.send(embed=embed)
#         return True
#     except Exception as e:
#         logging.error(f'Error processing music review message: {e}')
#         return False
    
