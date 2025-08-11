import logging
import discord

class EmbedsHelper:
    def __init__(self, config):
        self.config = config
        self.client = config.get_client()
        self.logger = logging.getLogger(__name__)

    def create_rating_embed(self, title, author, link, rating, explanation):
        try:
            embed = discord.Embed(title=f'Rating for {title}',
                                  description=explanation)
            embed.set_thumbnail(url=self.client.user.avatar.url)
            embed.add_field(name='Author', value=author, inline=True)
            embed.add_field(name='Link', value=link, inline=True)
            embed.add_field(name='Rating', value=rating, inline=True)
            embed.set_footer(text='Rutta DJ Bot')
        except Exception as e:
            logging.error(f'Error creating rating embed: {e}')
            embed = discord.Embed(title='Error',
                                  description='Failed to create rating embed.')
            embed.set_thumbnail(url=self.client.user.avatar.url)
            embed.set_footer(text='Rutta DJ Bot')
        return embed

    def create_recommendation_embed(self, title, author, link, genres, tag):
        try:
            if genres[1]:
                genre_description = f'Genres: {genres[0]}, {genres[1]}'
            else:
                genre_description = f'Genre: {genres[0]}'
            embed = discord.Embed(title=f'Recommendation: {title}',
                                  description=f'{genre_description}\nTag: {tag}')
            embed.set_thumbnail(url=self.client.user.avatar.url)
            embed.add_field(name='Author', value=author, inline=True)
            embed.add_field(name='Link', value=link, inline=True)
            embed.set_footer(text='Rutta DJ Bot')
        except Exception as e:
            logging.error(f'Error creating recommendation embed: {e}')
            embed = discord.Embed(
                title='Error',
                description='Failed to create recommendation embed.')
            embed.set_thumbnail(url=self.client.user.avatar.url)
            embed.set_footer(text='Rutta DJ Bot')
        return embed
    
    def parse_embed(embed):
        try:
            title = embed.title if embed.title else ''
            author = embed.author.name if embed.author else embed.footer.text if embed.footer else embed.description if embed.description else embed.fields[0].value if embed.fields else ''
            if author.endswith(' - Topic'):
                author = author.rstrip(' - Topic')
            link = embed.url if hasattr(embed, 'url') else None
        except Exception as e:
            logging.error(f'Error parsing embed: {e}')
            title, author, link = None, None, None
        return title, author, link
    

# import logging
# import discord
# from config import config

# client = config.client

# def create_rating_embed(title, author, link, rating, explanation):
#     try:
#         embed = discord.Embed(title=f'Rating for {title}',
#                               description=explanation)
#         embed.set_thumbnail(url=client.user.avatar.url)
#         embed.add_field(name='Author', value=author, inline=True)
#         embed.add_field(name='Link', value=link, inline=True)
#         embed.add_field(name='Rating', value=rating, inline=True)
#         embed.set_footer(text='Rutta DJ Bot')
#     except Exception as e:
#         logging.error(f'Error creating rating embed: {e}')
#         embed = discord.Embed(title='Error',
#                               description='Failed to create rating embed.')
#         embed.set_thumbnail(url=client.user.avatar.url)
#         embed.set_footer(text='Rutta DJ Bot')
#     return embed


# def create_recommendation_embed(title, author, link, genres, tag):
#     try:
#         if genres[1]:
#             genre_description = f'Genres: {genres[0]}, {genres[1]}'
#         else:
#             genre_description = f'Genre: {genres[0]}'
#         embed = discord.Embed(title=f'Recommendation: {title}',
#                               description=f'{genre_description}\nTag: {tag}')
#         embed.set_thumbnail(url=client.user.avatar.url)
#         embed.add_field(name='Author', value=author, inline=True)
#         embed.add_field(name='Link', value=link, inline=True)
#         embed.set_footer(text='Rutta DJ Bot')
#     except Exception as e:
#         logging.error(f'Error creating recommendation embed: {e}')
#         embed = discord.Embed(
#             title='Error',
#             description='Failed to create recommendation embed.')
#         embed.set_thumbnail(url=client.user.avatar.url)
#         embed.set_footer(text='Rutta DJ Bot')
#     return embed