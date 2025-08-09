import discord
import re
import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from db.db_connector import DBConnector
from views.ratings import RatingsStartView
from views.recommendations import RecommendationsStartView
from helpers.messages import *
from discord.ext import commands
import time
import json

# Set up logging
logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                    level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)

# Load environment variables - don't forget to configure .env for production
if os.path.exists('.env'):
    load_dotenv()
    environment = os.getenv('ENVIRONMENT', 'development')
else:
    environment = os.environ.get('ENVIRONMENT', 'development')

if environment == 'production':
    db_path = 'db/rutta-dj-prod.sqlite3'
    logging.info('Running in production mode')
    vars = json.load(open('config/prod.json'))
else:
    db_path = 'db/rutta-dj-dev.sqlite3'
    vars = json.load(open('config/dev.json'))
    logging.info('Running in development mode')

# Set up configuration variables
# These can be overridden by environment variables for flexibility
TRACK_LIST_CHANNEL = vars.get('track_list_channel', 'test-track-list')
MUSIC_REVIEW_CHANNEL = vars.get('music_review_channel', 'test-music-review')
CONTROLLING_USER = vars.get('controlling_user', 'longliveHIM').lower()

# Set up Discord client with intents
# Enable message content intent to read message content
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True

client = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

# Set up DB connection
try:
    db = DBConnector(db_path)
    db.create_tables()
    logging.info('Database connection established and tables created.')
except Exception as e:
    logging.error(f'Error setting up database: {e}')
    raise


def create_rating_embed(title, author, link, rating, explanation):
    try:
        embed = discord.Embed(title=f'Rating for {title}',
                              description=explanation)
        embed.set_thumbnail(url=client.user.avatar.url)
        embed.add_field(name='Author', value=author, inline=True)
        embed.add_field(name='Link', value=link, inline=True)
        embed.add_field(name='Rating', value=rating, inline=True)
        embed.set_footer(text='Rutta DJ Bot')
    except Exception as e:
        logging.error(f'Error creating rating embed: {e}')
        embed = discord.Embed(title='Error',
                              description='Failed to create rating embed.')
        embed.set_thumbnail(url=client.user.avatar.url)
        embed.set_footer(text='Rutta DJ Bot')
    return embed


def create_recommendation_embed(title, author, link, genre, tag):
    try:
        embed = discord.Embed(title=f'Recommendation: {title}',
                              description=f'Genre: {genre}\nTag: {tag}')
        embed.set_thumbnail(url=client.user.avatar.url)
        embed.add_field(name='Author', value=author, inline=True)
        embed.add_field(name='Link', value=link, inline=True)
        embed.set_footer(text='Rutta DJ Bot')
    except Exception as e:
        logging.error(f'Error creating recommendation embed: {e}')
        embed = discord.Embed(
            title='Error',
            description='Failed to create recommendation embed.')
        embed.set_thumbnail(url=client.user.avatar.url)
        embed.set_footer(text='Rutta DJ Bot')
    return embed

async def process_message(message):
    if str(message.author.global_name).lower() != CONTROLLING_USER:
        return False
    
    if message.channel.name == TRACK_LIST_CHANNEL:
        return await process_track_list_message(message)
    elif message.channel.name == MUSIC_REVIEW_CHANNEL:
        return await process_music_review_message(message)
    
async def process_track_list_message(message): 
    # Expecting format:
    # Genre - Tag\nhttps://www.youtube.com/watch?v=4hz68I4BRMA
    # OR:
    # @Genre[s] - Tag\nhttps://www.youtube.com/watch?v=4hz68I4BRMA
    logging.info(f'Received message from {message.author.global_name} in {TRACK_LIST_CHANNEL}: {message.content}')
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
        if not genres:
            genres = genre_tag_line[0].strip().split(' ')
        if len(genres) < 2:
            genres.append('')  # Ensure we have at least two genres
        tag = genre_tag_line[-1].strip()
        
        if message.embeds:
            embed = message.embeds[0]
            title, author, link = parse_embed(embed)
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
            logging.error(f'Missing author in replied message: {message.content}')
            return False
        
        db.insert_recommendation(message.id, author, title, link, genres, tag)
        logging.info(f'Recommendation inserted: {title} by {author} ({link}) with genres {genres} and tag {tag}')
        curr_time = datetime.now(timezone.utc)
        diff = curr_time - message.created_at
        if diff.total_seconds() < 360:
            embed = create_recommendation_embed(title, author, link, ' '.join(genres), tag)
            await message.channel.send(embed=embed)

    except Exception as e:
        logging.error(f'Error processing track list message: {e}')
        return False

async def process_music_review_message(message):
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
        title, author, link = parse_embed(embed)
        if not title:
            logging.error(f'Missing title in replied message: {replied_message.content}')
            return False
        if not link:
            logging.error(f'Missing link in replied message: {replied_message.content}')
            return False
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
            unique_id = f"{message.id}-{idx}" if len(tracks_to_process) > 1 else message.id
            db.insert_rating(unique_id, replied_message.author.global_name, track_name, link, rating, explanation)
            embed = create_rating_embed(track_name, author, link, rating, explanation)
            logging.info(f'Rating inserted: {track_name} by {author} ({link}) with rating {rating} and explanation "{explanation}"')
            curr_time = datetime.now(timezone.utc)
            diff = curr_time - message.created_at
            if diff.total_seconds() < 360:
                await message.channel.send(embed=embed)
            return True
    except Exception as e:
        logging.error(f'Error processing music review message: {e}')
        return False

# async def process_message(message):
#     if message.author == client.user:
#         return False  # Ignore messages from the bot itself

#     # Only process messages in the relevant channels
#     if message.channel.name == TRACK_LIST_CHANNEL:
#         logging.info(
#             f'Received message from {message.author.global_name} in {TRACK_LIST_CHANNEL}: {message.content}'
#         )
#         # Only process messages from Rutta
#         if str(message.author.global_name).lower() == CONTROLLING_USER:
#             # Expecting format:
#             # Genre - Tag\nhttps://www.youtube.com/watch?v=4hz68I4BRMA
#             if message.embeds:
#                 embed = None
#                 genre, tag = parse_recommendation(message.content)
#                 title, author, link = parse_embed(message.embeds[0])
#                 if genre and tag and title:
#                     if not author: author = 'Unknown'
#                     try:
#                         db.insert_recommendation(message.id, author, title,
#                                                  link, genre, tag)
#                         logging.info(
#                             f'Recommendation inserted: {title} by {author} ({link}) with genre {genre} and tag {tag}'
#                         )
#                     except Exception as e:
#                         embed = discord.Embed(
#                             title='Error',
#                             description='Failed to insert recommendation.')
#                         logging.error(f'Error inserting recommendation: {e}')
#                     try:
#                         if not embed:
#                             embed = create_recommendation_embed(
#                                 title, author, link, genre, tag)
#                     except Exception as e:
#                         embed = discord.Embed(
#                             title='Error',
#                             description='Failed to create recommendation embed.'
#                         )
#                         logging.error(
#                             f'Error creating recommendation embed: {e}')
#                     curr_time = datetime.now(timezone.utc)
#                     diff = curr_time - message.created_at
#                     if diff.total_seconds() < 360:
#                         await message.channel.send(embed=embed)
#                     if (embed.title == 'Error'): return False
#                     else: return True
#                 else:
#                     logging.error(f'Failed to parse recommendation: {message.content}')
#                     return False
#             else:
#                 logging.info(
#                     f'No embeds found in message: {message.content}. Waiting for edit.'
#                 )
#                 return False  # Wait for edit to process the recommendation
#         else:
#             return False  # Skip messages not from Rutta

#     elif message.channel.name == MUSIC_REVIEW_CHANNEL:
#         # If Rutta is rating a track, he should be replying to a message with the song link
#         # This assumes that the embed is in the replied message and has already been generated. Might break if embed isn't generated or there's a lot of lag
#         if str(message.author.global_name).lower() == CONTROLLING_USER and message.reference:
#             try:
#                 replied_message = await message.channel.fetch_message(message.reference.message_id)
#             except Exception as e:
#                 replied_message = None
#                 logging.warning(
#                     f'Could not fetch replied message: {message.reference.message_id}. Error: {e}'
#                 )
#                 return False
#             if replied_message:
#                 recommended_by = replied_message.author.global_name if replied_message.author else 'Unknown'
#                 title, author, link = None, None, None
#                 if replied_message.embeds:
#                     title, author, link = parse_embed(replied_message.embeds[0])
#                 rating, explanation = parse_rating(message.content)
#                 if title and link and rating is not None:
#                     if not author: author = 'Unknown'
#                     try:
#                         db.insert_rating(message.id, recommended_by, title,
#                                          link, rating, explanation)
#                         embed = create_rating_embed(title, author, link,
#                                                     rating, explanation)
#                         logging.info(
#                             f'Rating inserted: {title} by {author} ({link}) with rating {rating} and explanation "{explanation}"'
#                         )
#                     except Exception as e:
#                         embed = discord.Embed(
#                             title='Error',
#                             description='Failed to insert rating.')
#                         logging.error(f'Error inserting rating: {e}. Title: {title}, Author: {author}, Link: {link}, Rating: {rating}, Explanation: {explanation}')
#                         return False
#                     curr_time = datetime.now(timezone.utc)
#                     diff = curr_time - message.created_at
#                     if diff.total_seconds() < 360:
#                         await message.channel.send(embed=embed)
#                     return True
#                 else:
#                     logging.error(f'Failed to parse rating: {message.content}. Title: {title}, Author: {author}, Link: {link}, Rating: {rating}')
#                     return False
#         elif str(message.author.global_name).lower() == CONTROLLING_USER:
#             logging.error(
#                 f'No embeds found in replied message: {message.content}'
#             )
#             return False


@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')


@client.command()
#@commands.has_permissions(administrator=True)
async def process(ctx):
    logging.info(f'Received request to process history')

    try:
        channels = [ch for ch in client.get_all_channels() if ch.name in [TRACK_LIST_CHANNEL, MUSIC_REVIEW_CHANNEL] and isinstance(ch, discord.TextChannel)]
        
        if not channels:
            await ctx.send(f"Target channel {channel} not found!")
            return

        processed_count = 0
        skipped_count = 0

        # Process messages in batches to avoid memory issues
        for channel in channels:
            logging.info(f'Starting historical processing in {channel}')
            async for message in channel.history(limit=1000, oldest_first=True):
                if await process_message(message):
                    processed_count += 1
                else:
                    skipped_count += 1
            logging.info(
                f'Processed {processed_count} messages, skipped {skipped_count} messages.'
            )

        await ctx.send(
            f"Historical processing complete!\n"
            f"Processed: {processed_count} new messages\n"
            f"Skipped: {skipped_count} messages (already processed or not target user)"
        )
        logging.info(
            f'Historical processing complete: {processed_count} processed, {skipped_count} skipped.'
        )

    except Exception as e:
        logging.error(f'Error processing history: {e}')
        await ctx.send(f"Error processing history: {e}")


@client.command()
async def ratings(ctx):
    logging.info(f'Received request to show ratings')
    view = RatingsStartView(db=db)
    try:
        await ctx.send("View Reviews By:", view=view)
    except Exception as e:
        logging.error(f'Error sending ratings view: {e}')

@client.command()
async def recommendations(ctx):
    logging.info(f'Received request to show recommendations')
    view = RecommendationsStartView(db=db)
    try:
        await ctx.send("View Recommendations By:", view=view)
    except Exception as e:
        logging.error(f'Error sending recommendations view: {e}')

@client.event
async def on_message(message):
    await client.process_commands(message)
    await process_message(message)


# @client.event
# async def on_message_edit(before, after):
#     if after.author == client.user:
#         return

#     # Only process messages in the relevant channels
#     logging.info(f'Received edited message in {after.channel.name}: {after.content}')

#     if after.channel.name == TRACK_LIST_CHANNEL and len(before.embeds) == 0 and len(after.embeds) > 0 and str(after.author.global_name).lower() == CONTROLLING_USER:
#         genre, tag = parse_recommendation(after.content)
#         title, author, link = parse_embed(after.embeds[0])
#         if genre and tag and title and author and link:
#             try:
#                 db.insert_recommendation(after.id, author, title, link, genre,
#                                          tag)
#                 embed = create_recommendation_embed(title, author, link, genre,
#                                                     tag)
#                 await after.channel.send(embed=embed)
#                 logging.info(
#                     f'Recommendation inserted on edit: {title} by {author} ({link}) with genre {genre} and tag {tag}'
#                 )
#             except Exception as e:
#                 logging.error(f'Error inserting recommendation on edit: {e}')


try:
    logging.info('Bot Is Running.')
    client.run(
        os.getenv('DISCORD_TOKEN', 'PUT YOUR TOKEN IN THE ENV FILE YOU DUMB IDIOT DUMMY'))
except discord.LoginFailure as e:
    logging.error(f'Bot Login Failure: {e}')
