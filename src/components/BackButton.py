import discord
from discord.ui import Button


class BackButton(Button):

    def __init__(self, db, row, prev_view, prev_content):
        super().__init__(label="Back",
                         style=discord.ButtonStyle.danger,
                         custom_id="back_ratings",
                         row=row)
        self.db = db
        self.prev_view = prev_view
        self.prev_content = prev_content

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(content=self.prev_content,
                                                view=self.prev_view)
