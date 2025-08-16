import os
import logging
import discord
import json
from discord.ext import commands
from db.db_connector import DBConnector
from dotenv import load_dotenv



class Config:
    def __init__(self):
        # Load environment variables - don't forget to configure .env for production
        load_dotenv()
        self.environment = os.environ.get('ENVIRONMENT', 'development')

    def _setup_logging(self):
        # Set up logging
        logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
                            level=logging.INFO,
                            datefmt='%Y-%m-%d %H:%M:%S')
        self.logger = logging.getLogger(f'Rutta-DJ-{self.environment}')
        self.logger.setLevel(logging.INFO)

    def _load_config(self):
        if self.environment.lower() == 'production':
            here = os.path.dirname(os.path.abspath(__file__))  # directory of config.py
            json_path = os.path.join(here, "prod.json")
            self.logger.info('Running in production mode')
            vars = json.load(open(json_path))
        else:
            here = os.path.dirname(os.path.abspath(__file__))  # directory of config.py
            json_path = os.path.join(here, "dev.json")
            self.logger.info('Running in development mode')
            vars = json.load(open(json_path))

        # Set up configuration variables
        self.TRACK_LIST_CHANNEL = vars.get('track_list_channel')
        self.MUSIC_REVIEW_CHANNEL = vars.get('music_review_channel')
        self.CONTROLLING_USER = vars.get('controlling_user').lower()
        self.DB_PATH = vars.get('db_path')

    def _setup_discord_client(self):
        # Set up Discord client with intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.members = True

        self.client = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

    def _setup_database(self):
        # Set up DB connection
        try:
            self.db = DBConnector(self.DB_PATH)
            self.db.create_tables()
            self.logger.info('Database connection established and tables created.')
        except Exception as e:
            self.logger.error(f'Error setting up database: {e}')
            raise

    def initialize(self):
        self._setup_logging()
        self._load_config()
        self._setup_discord_client()
        self._setup_database()

    def get_vars(self):
        return {
            'TRACK_LIST_CHANNEL': self.TRACK_LIST_CHANNEL,
            'MUSIC_REVIEW_CHANNEL': self.MUSIC_REVIEW_CHANNEL,
            'CONTROLLING_USER': self.CONTROLLING_USER,
        }
    
    def get_db(self):
        return self.db
    
    def get_client(self):
        return self.client




# import os
# import logging
# import discord
# import json
# from discord.ext import commands
# from db.db_connector import DBConnector
# # Load environment variables - don't forget to configure .env for production
# environment = os.environ.get('ENVIRONMENT', 'development')

# # Set up logging
# logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s',
#                     level=logging.INFO,
#                     datefmt='%Y-%m-%d %H:%M:%S')
# logger = logging.getLogger(f'Rutta-DJ-{environment}')
# logger.setLevel(logging.INFO)

# if environment.lower() == 'production':
#     logging.info('Running in production mode')
#     vars = json.load(open('src/config/prod.json'))
# else:
#     logging.info('Running in development mode')
#     vars = json.load(open('src/config/dev.json'))

# # Set up configuration variables
# TRACK_LIST_CHANNEL = vars.get('track_list_channel')
# MUSIC_REVIEW_CHANNEL = vars.get('music_review_channel')
# CONTROLLING_USER = vars.get('controlling_user').lower()
# DB_PATH = vars.get('db_path')

# # Set up Discord client with intents
# # Enable message content intent to read message content
# intents = discord.Intents.default()
# intents.message_content = True
# intents.messages = True
# intents.members = True

# client = commands.Bot(command_prefix=commands.when_mentioned, intents=config.intents)

# try:
#     db = DBConnector(DB_PATH)
#     db.create_tables()
#     logging.info('Database connection established and tables created.')
# except Exception as e:
#     logging.error(f'Error setting up database: {e}')
#     raise