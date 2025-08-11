import discord
import logging
import os
from views.ratings import RatingsStartView
from views.recommendations import RecommendationsStartView
from config.config import Config
from helpers.embeds import EmbedsHelper
from helpers.messages import MessagesHelper
from helpers.spotify import SpotifyHelper

try:
    conf = Config()
    conf.initialize()
    logger = logging.getLogger(__name__)
    client = conf.get_client()
    db = conf.get_db()
    vars = conf.get_vars()

    embedsHelper = EmbedsHelper(conf)
    spotifyHelper = SpotifyHelper()
    messagesHelper = MessagesHelper(conf, embedsHelper, spotifyHelper)

except Exception as e:
    logging.error(f'Error initializing configuration: {e}')
    raise


@client.event
async def on_ready():
    logging.info(f'Logged in as {client.user}')


@client.command()
#@commands.has_permissions(administrator=True)
async def process(ctx):
    logging.info(f'Received request to process history')

    try:
        channels = [ch for ch in client.get_all_channels() if ch.name in [vars['TRACK_LIST_CHANNEL'], vars['MUSIC_REVIEW_CHANNEL']] and isinstance(ch, discord.TextChannel)]
        
        if not channels:
            await ctx.send(f"Target channel {channel} not found!")
            return

        processed_count = 0
        skipped_count = 0

        # Process messages in batches to avoid memory issues
        for channel in channels:
            logging.info(f'Starting historical processing in {channel}')
            async for message in channel.history(limit=100000, oldest_first=True):
                if await messagesHelper.process_message(message):
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
    await messagesHelper.process_message(message)

try:
    logging.info('Bot Is Running.')
    client.run(os.getenv('DISCORD_TOKEN'))
except discord.LoginFailure as e:
    logging.error(f'Bot Login Failure: {e}')
