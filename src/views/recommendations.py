import discord
from discord.ui import View, Button

def _build_embed_table(recommendations):
    embed = discord.Embed(title="Results", color=discord.Color.blue())
    for rec in recommendations:
        embed.add_field(
            name=rec['title'],
            value=f"Author: {rec['author']}\nLink: {rec['link']}\nGenre: {rec['genre']}\nTag: {rec['tag']}",
            inline=False
        )
    embed.set_footer(text="Click 'Close' to dismiss this message.")
    return embed

class RecommendationsStartView(View):
    def __init__(self, db):
        super().__init__()
        self.db = db
    

    @discord.ui.button(label="Genre", style=discord.ButtonStyle.primary, custom_id="genre")
    async def genre_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="Select a genre:", view=GenreView(db=self.db)
        )
    
    @discord.ui.button(label="Tag", style=discord.ButtonStyle.primary, custom_id="tag")
    async def tag_callback(self, interaction: discord.Interaction, button: Button): 
        await interaction.response.edit_message(
            content="Select a tag:", view=TagView(db=self.db)
        )

class GenreView(View):
    def __init__(self, db):
        super().__init__()
        self.db = db
        genres = db.get_all_genres()
        for i, genre in enumerate(genres):
            self.add_item(GenreButton(genre, db))
        self.add_item(GenreBackButton(db, 1))

class GenreButton(Button):
    def __init__(self, genre, db):
        super().__init__(label=genre, style=discord.ButtonStyle.primary, custom_id=f"genre_{genre}")
        self.db = db
        self.genre = genre

    async def callback(self, interaction: discord.Interaction):
        recommendations = self.db.get_recommendations_by_genre(self.genre)
        embed = _build_embed_table(recommendations)
        await interaction.response.edit_message(
            content=f"Recommendations for {self.genre}:", embed = embed, view=RecommendationsView()
        )

class GenreBackButton(Button):
    def __init__(self, db, row):
        super().__init__(label="Back", style=discord.ButtonStyle.danger, custom_id="back_genre", row=row)
        self.db = db

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="View Recommendations By:", view=RecommendationsStartView(self.db))

class TagView(View):
    def __init__(self, db):
        super().__init__()
        self.db = db
        tags = db.get_all_tags()
        for i, tag in enumerate(tags):
            self.add_item(TagButton(tag, db, 0))
        self.add_item(TagBackButton(db, 1))

class TagButton(Button):
    def __init__(self, tag, db, row):
        super().__init__(label=tag, style=discord.ButtonStyle.primary, custom_id=f"tag_{tag}", row=row)
        self.db = db
        self.tag = tag

    async def callback(self, interaction: discord.Interaction):
        recommendations = self.db.get_recommendations_by_tag(self.tag)
        embed = _build_embed_table(recommendations)
        await interaction.response.edit_message(
            content=f"Recommendations for {self.tag}:", embed=embed, view=RecommendationsView()
        )

class TagBackButton(Button):
    def __init__(self, db, row):
        super().__init__(label="Back", style=discord.ButtonStyle.danger, custom_id="back_tag", row=row)
        self.db = db

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content="Select a tag:", view=RecommendationsStartView(self.db))

class RecommendationsView(View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="close")
    async def close_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(delete_after=1)