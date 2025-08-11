import discord
from discord.ui import Button

class PrevButton(Button):
    def __init__(self, db, page, prev_view, prev_content):
        super().__init__(label="Prev", style=discord.ButtonStyle.secondary)
        self.db = db
        self.page = page
        self.prev_view = prev_view
        self.prev_content = prev_content

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.edit_message(
            content=self.prev_content, view=self.prev_view(self.db, self.page - 1)
        )