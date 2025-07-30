import discord
from discord.ui import View, Button

class StartView(View):
    def __init__(self, db):
        super().__init__()
        self.db = db  

        #self.add_item(discord.Button(label="Ratings", style=discord.ButtonStyle.primary, custom_id="ratings"))
        #self.add_item(Button(label="Recommended By", style=discord.ButtonStyle.primary, custom_id="recommended"))

    @discord.ui.button(label="Rating", style=discord.ButtonStyle.primary, custom_id="ratings")
    async def ratings_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="Select a rating:", view=RatingsView(db=self.db)
        )
    
    @discord.ui.button(label="Recommended By", style=discord.ButtonStyle.primary, custom_id="recommended")
    async def recommended_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(
            content="Select a recommendation:", view=RecView(db=self.db)
        )
    
class RatingsView(View):
    def __init__(self, db):
        super().__init__()
        self.db = db
        for i in range(1, 11):
            self.add_item(RatingButton(i, db))
        self.add_item(RatingsBackButton(db))

class RatingsBackButton(Button):
    def __init__(self, db):
        super().__init__(label="Back", style=discord.ButtonStyle.danger, custom_id="back_ratings")
        self.db = db

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=StartView(self.db))
    

class RecView(View):
    def __init__(self, db):
        super().__init__()
        self.db = db
        # Add buttons or other UI elements for recommendations here
        recommended_by = db.get_all_recommended_by()
        for i, name in enumerate(recommended_by):
            self.add_item(RecButton(name, db))
        self.add_item(RecBackButton(db))

class RecBackButton(Button):
    def __init__(self, db):
        super().__init__(label="Back", style=discord.ButtonStyle.danger, custom_id="back_rec")
        self.db = db

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=StartView(self.db))

#old shitty malformed table builder
#def build_embed_table(results):
#    embed = discord.Embed(title="Results", description="Here are the results:", color=discord.Color.blue())
#    ratings = [result['rating'] for result in results]
#    names = [result['track_name'] for result in results]
#    reviews = [result['review'] for result in results]
#    recomended_by = [result['recommended_by'] for result in results]
#    embed.add_field(name="Track Name", value=names, inline=True)
#    embed.add_field(name="Rating", value=ratings, inline=True)
#    embed.add_field(name="Review", value=reviews, inline=True)
#    embed.add_field(name="Recommended By", value=recomended_by, inline=True)
#    embed.set_footer(text="Click 'Close' to dismiss this message.")
#    return embed

def build_embed_table(results):
    embed = discord.Embed(title="Results", color=discord.Color.blue())
    for result in results:
        embed.add_field(name=result['track_name'], value=f"Rating: {result['rating']}\nReview: {result['review']}\nRecommended By: {result['recommended_by']}", inline=False)
    embed.set_footer(text="Click 'Close' to dismiss this message.")
    return embed
    
class RecButton(Button):
    def __init__(self, name: str, db):
        super().__init__(label=name, style=discord.ButtonStyle.secondary)
        self.db = db
        self.name = name

    async def callback(self, interaction: discord.Interaction):
        results = self.db.get_tracks_by_recommended_by(self.name)
        if results:
            embed = build_embed_table(results)
            await interaction.response.edit_message(content = None, embed = embed, view=ResultsTable())
        else:
            await interaction.response.send_message(f"No tracks found recommended by {self.name}.", ephemeral=True)

class RatingButton(Button):
    def __init__(self, value: int, db):
        super().__init__(label=str(value), style=discord.ButtonStyle.secondary)
        self.db = db
        self.value = value

    async def callback(self, interaction: discord.Interaction):
        results = self.db.get_tracks_by_rating(self.value)
        if results:
            embed = build_embed_table(results)
            await interaction.response.edit_message(content = None, embed = embed, view=ResultsTable())
        else:
            await interaction.response.send_message(f"No tracks found with rating {self.value}.", ephemeral=True)

class ResultsTable(View):
    def __init__(self):
        super().__init__()

    @discord.ui.button(label="Close", style=discord.ButtonStyle.danger, custom_id="close")
    async def close_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.edit_message(delete_after=1)