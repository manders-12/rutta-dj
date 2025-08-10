import discord
from discord.ui import View, Button
from components.BackButton import BackButton


def _build_embed_table(results, j = 0, embed=None):
    for j, result in enumerate(results):
        embed.add_field(
            name=result['track_name'],
            value=
            f"Rating: {result['rating']}\nReview: {result['review']}\nRecommended By: {result['recommended_by']}",
            inline=False)
    embed.set_footer(text="Click 'Close' to dismiss this message.")
    return embed

# Discord's embed field limit is 25, so we need to split results into multiple embeds if they exceed this limit, we'll call _build_embed_table as many times as needed
def _build_embed_tables(results):
    embeds = []
    embed = discord.Embed(title="Results", description="Page 1", color=discord.Color.blue())
    for i, result in enumerate(results):
        if i % 25 == 0 and i > 0:
            embeds.append(embed)
            embed = discord.Embed(title="Results", description=f"Page {(i//25)+1}", color=discord.Color.blue())
        embed.add_field(
            name=result['track_name'],
            value=
            f"Rating: {result['rating']}\nReview: {result['review']}\nRecommended By: {result['recommended_by']}",
            inline=False)
    if embed.fields:
        embeds.append(embed)
    return embeds

class RatingsStartView(View):

    def __init__(self, db):
        super().__init__()
        self.db = db

        #self.add_item(discord.Button(label="Ratings", style=discord.ButtonStyle.primary, custom_id="ratings"))
        #self.add_item(Button(label="Recommended By", style=discord.ButtonStyle.primary, custom_id="recommended"))

    @discord.ui.button(label="Rating",
                       style=discord.ButtonStyle.primary,
                       custom_id="ratings")
    async def ratings_callback(self, interaction: discord.Interaction,
                               button: Button):
        await interaction.response.edit_message(content="Select a rating:",
                                                view=RatingsView(db=self.db))

    @discord.ui.button(label="Recommended By",
                       style=discord.ButtonStyle.primary,
                       custom_id="recommended")
    async def recommended_callback(self, interaction: discord.Interaction,
                                   button: Button):
        await interaction.response.edit_message(
            content="View Songs Recommended By:", view=RecView(db=self.db))


class RatingsView(View):
    def __init__(self, db):
        super().__init__()
        self.db = db
        for i in range(1, 11):
            row = (i - 1) // 5  # Calculate row number based on index
            self.add_item(RatingButton(i, db, row))
        self.add_item(
            BackButton(db, ((i + 1) // 5) + 1, RatingsStartView(db),
                       "View Reviews By:"))


# class RatingsBackButton(Button):
#     def __init__(self, db, row):
#         super().__init__(label="Back", style=discord.ButtonStyle.danger, custom_id="back_ratings", row = row)
#         self.db = db

#     async def callback(self, interaction: discord.Interaction):
#         await interaction.response.edit_message(content = "View Reviews By:", view=RatingsStartView(self.db))


class RecView(View):

    def __init__(self, db):
        super().__init__()
        self.db = db
        recommended_by = db.get_all_recommended_by()
        for i, name in enumerate(recommended_by):
            self.add_item(RecButton(name, db))
        self.add_item(
            BackButton(db, 1, RatingsStartView(db), "View Reviews By:"))


# class RecBackButton(Button):
#     def __init__(self, db, row):
#         super().__init__(label="Back", style=discord.ButtonStyle.danger, custom_id="back_rec", row = row)
#         self.db = db

#     async def callback(self, interaction: discord.Interaction):
#         await interaction.response.edit_message(content = "View Reviews By:", view=RatingsStartView(self.db))

#old shitty malformed table builder
#def _build_embed_table(results):
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


class RecButton(Button):

    def __init__(self, name: str, db):
        super().__init__(label=name,
                         style=discord.ButtonStyle.secondary)
        self.db = db
        self.name = name

    async def callback(self, interaction: discord.Interaction):
        results = self.db.get_tracks_by_recommended_by(self.name)
        if results:
            embeds = _build_embed_tables(results)
            await interaction.response.edit_message(
                content=None,
                embed=embeds[0],
                view=ResultsTable(embeds, 0)
            )
        else:
            await interaction.response.send_message(
                f"No tracks found recommended by {self.name}.", ephemeral=True)


class RatingButton(Button):

    def __init__(self, value: int, db, row):
        super().__init__(label=str(value),
                         style=discord.ButtonStyle.secondary,
                         row=row)
        self.db = db
        self.value = value

    async def callback(self, interaction: discord.Interaction):
        results = self.db.get_tracks_by_rating(self.value)
        if results:
            embeds = _build_embed_tables(results)
            await interaction.response.edit_message(
                content=None,
                embed=embeds[0],
                view=ResultsTable(embeds, 0)
            )
        else:
            await interaction.response.send_message(
                f"No tracks found with rating {self.value}.", ephemeral=True)


class ResultsTable(View):

    def __init__(self, embeds, page):
        super().__init__()
        self.embeds = embeds
        self.page = page
        self.add_item(PreviousButton())
        self.add_item(NextButton())
        self.add_item(CloseButton())

    async def update_embed(self, interaction):
        await interaction.response.edit_message(
            embed=self.embeds[self.page],
            view=self
        )

class PreviousButton(Button):
    def __init__(self):
        super().__init__(label="Previous", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if view.page > 0:
            view.page -= 1
            await view.update_embed(interaction)
        else:
            await interaction.response.send_message("Already at the first page.", ephemeral=True)

class NextButton(Button):
    def __init__(self):
        super().__init__(label="Next", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: discord.Interaction):
        view = self.view
        if view.page < len(view.embeds) - 1:
            view.page += 1
            await view.update_embed(interaction)
        else:
            await interaction.response.send_message("Already at the last page.", ephemeral=True)

class CloseButton(Button):
    def __init__(self):
        super().__init__(label="Close", style=discord.ButtonStyle.danger)

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(view=None)
