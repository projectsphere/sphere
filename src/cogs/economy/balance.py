import discord
from discord.ext import commands
from discord import app_commands
import yaml
import os
from src.utils.economy import get_gold

CONFIG_FILE = os.path.join("config", "sftp.yml")

def load_economy_config():
    if not os.path.exists(CONFIG_FILE):
        return {"currency_name": "gold"}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        return config.get("economy", {"currency_name": "gold"})

class BalanceCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = load_economy_config()

    @app_commands.command(name="balance", description="Check your gold balance.")
    @app_commands.guild_only()
    async def balance(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        discord_id = interaction.user.id
        
        gold = await get_gold(discord_id, guild_id)
        currency = self.config.get("currency_name", "gold")
        
        embed = discord.Embed(
            title=f"{interaction.user.name}'s Balance",
            description=f"You have **{gold} {currency}**",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(BalanceCog(bot))
