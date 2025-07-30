import discord
import re
import logging
import os
from dotenv import load_dotenv
from datetime import datetime, timezone
from db_connector import DBConnector
from ratings import RatingsStartView
from recommendations import RecommendationsStartView
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

# Channel names to watch
#TRACK_LIST_CHANNEL = os.getenv('TRACK_LIST_CHANNEL', 'test-track-list')
#MUSIC_REVIEW_CHANNEL = os.getenv('MUSIC_REVIEW_CHANNEL', 'test-music-review')
# The username to match for recommendations and ratings
#CONTROLLING_USER = os.getenv('CONTROLLING_USER', 'longliveHIM').lower()

# Set up Discord client with intents
# Enable message content intent to read message content
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True

client = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)
#client = discord.Client(intents=intents)

# Set up DB connection
try:
    db = DBConnector(db_path)
    db.create_tables()
    logging.info('Database connection established and tables created.')
except Exception as e:
    logging.error(f'Error setting up database: {e}')
    raise


def extract_link(text):
    match = re.search(r'(https?://\S+)', text)
    return match.group(1) if match else None


def parse_rating(text):
    try:
        lines = text.split('\n')
        reviewI = None
        for i, line in enumerate(lines):
            parts = line.split('-')
            if len(parts) > 1 and parts[-1].strip().isdigit():
                rating = parts[-1].strip()
                reviewI = i + 1
                break
        if reviewI is not None and reviewI < len(lines):
            explanation = '\n'.join(lines[reviewI:]).strip()
    except Exception as e:
        logging.error(f'Error parsing rating: {e}')
        rating, explanation = None, None
    return rating, explanation


def parse_recommendation(text):
    try:
        lines = text.split('\n')
        parts = lines[0].split('-')
        tag = parts[-1].strip()
        genre = "-".join(parts[0:-1]).strip()
    except Exception as e:
        logging.error(f'Error parsing recommendation: {e}')
        genre, tag = None, None
    return genre, tag


def parse_embed(embed):
    try:
        title = embed.title if embed.title else ''
        author = embed.author.name if embed.author else ''
        author = author.rstrip(' - Topic')
        link = embed.url if hasattr(embed, 'url') else None
    except Exception as e:
        logging.error(f'Error parsing embed: {e}')
        title, author, link = None, None, None
    return title, author, link


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
    if message.author == client.user:
        return False  # Ignore messages from the bot itself

    # Only process messages in the relevant channels
    if message.channel.name == TRACK_LIST_CHANNEL:
        logging.info(
            f'Received message from {message.author.global_name} in {TRACK_LIST_CHANNEL}: {message.content}'
        )
        # Only process messages from Rutta
        if str(message.author.global_name).lower() == CONTROLLING_USER:
            # Expecting format:
            # Genre - Tag\nhttps://www.youtube.com/watch?v=4hz68I4BRMA
            if message.embeds:
                embed = None
                genre, tag = parse_recommendation(message.content)
                title, author, link = parse_embed(message.embeds[0])
                if genre and tag and title and author:
                    try:
                        db.insert_recommendation(message.id, author, title,
                                                 link, genre, tag)
                        logging.info(
                            f'Recommendation inserted: {title} by {author} ({link}) with genre {genre} and tag {tag}'
                        )
                    except Exception as e:
                        embed = discord.Embed(
                            title='Error',
                            description='Failed to insert recommendation.')
                        logging.error(f'Error inserting recommendation: {e}')
                    try:
                        if not embed:
                            embed = create_recommendation_embed(
                                title, author, link, genre, tag)
                    except Exception as e:
                        embed = discord.Embed(
                            title='Error',
                            description='Failed to create recommendation embed.'
                        )
                        logging.error(
                            f'Error creating recommendation embed: {e}')
                    curr_time = datetime.now(timezone.utc)
                    diff = curr_time - message.created_at
                    if diff.total_seconds() < 360:
                        await message.channel.send(embed=embed)
                    if (embed.title == 'Error'): return False
                    else: return True
            else:
                logging.info(
                    f'No embeds found in message: {message.content}. Waiting for edit.'
                )
                return False  # Wait for edit to process the recommendation
        else:
            return False  # Skip messages not from Rutta

    elif message.channel.name == MUSIC_REVIEW_CHANNEL:
        # If Rutta is rating a track, he should be replying to a message with the song link
        # This assumes that the embed is in the replied message and has already been generated. Might break if embed isn't generated or there's a lot of lag
        if str(message.author.global_name).lower(
        ) == CONTROLLING_USER and message.reference:
            try:
                replied_message = await message.channel.fetch_message(
                    message.reference.message_id)
            except Exception as e:
                replied_message = None
                logging.warning(
                    f'Could not fetch replied message: {message.reference.message_id}. Error: {e}'
                )
            if replied_message:
                recommended_by = replied_message.author.global_name if replied_message.author else 'Unknown'
                title, author, link = parse_embed(replied_message.embeds[0])
                rating, explanation = parse_rating(message.content)
                if title and author and link and rating is not None:
                    try:
                        db.insert_rating(message.id, recommended_by, title,
                                         link, rating, explanation)
                        embed = create_rating_embed(title, author, link,
                                                    rating, explanation)
                        logging.info(
                            f'Rating inserted: {title} by {author} ({link}) with rating {rating} and explanation "{explanation}"'
                        )
                    except Exception as e:
                        embed = discord.Embed(
                            title='Error',
                            description='Failed to insert rating.')
                        logging.error(f'Error inserting rating: {e}')
                    curr_time = datetime.now(timezone.utc)
                    diff = curr_time - message.created_at
                    if diff.total_seconds() < 360:
                        await message.channel.send(embed=embed)


@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')


@client.command()
@commands.has_permissions(administrator=True)
async def process(ctx):
    logging.info(f'Received request to process history')

    try:
        channels = []
        for channel in client.get_all_channels():
            if channel.name in [TRACK_LIST_CHANNEL, MUSIC_REVIEW_CHANNEL
                                ] and isinstance(channel, discord.TextChannel):
                channels.append(channel)
        if not channels:
            await ctx.send(f"Target channel {channel} not found!")
            return

        processed_count = 0
        skipped_count = 0

        # Process messages in batches to avoid memory issues
        for channel in channels:
            logging.info(f'Starting historical processing in {channel}')
            async for message in channel.history(oldest_first=True):
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


@client.event
async def on_message_edit(before, after):
    if after.author == client.user:
        return

    # Only process messages in the relevant channels
    logging.info(
        f'Received edited message in {after.channel.name}: {after.content}')
    if after.channel.name == TRACK_LIST_CHANNEL and len(
            before.embeds) == 0 and len(after.embeds) > 0 and str(
                after.author.global_name).lower() == CONTROLLING_USER:
        genre, tag = parse_recommendation(after.content)
        title, author, link = parse_embed(after.embeds[0])
        if genre and tag and title and author and link:
            try:
                db.insert_recommendation(after.id, author, title, link, genre,
                                         tag)
                embed = create_recommendation_embed(title, author, link, genre,
                                                    tag)
                await after.channel.send(embed=embed)
                logging.info(
                    f'Recommendation inserted on edit: {title} by {author} ({link}) with genre {genre} and tag {tag}'
                )
            except Exception as e:
                logging.error(f'Error inserting recommendation on edit: {e}')


try:
    client.run(
        os.getenv('DISCORD_TOKEN',
                  'PUT YOUR TOKEN IN THE ENV FILE YOU DUMB IDIOT DUMMY'))
    logging.info('Bot Is Running.')
except discord.LoginFailure as e:
    logging.error(f'Bot Login Failure: {e}')
