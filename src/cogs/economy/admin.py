import discord
from discord.ext import commands
from discord import app_commands
import yaml
import os
from src.utils.economy import get_gold, add_gold, set_gold, remove_gold

CONFIG_FILE = os.path.join("config", "sftp.yml")

def load_economy_config():
    if not os.path.exists(CONFIG_FILE):
        return {"currency_name": "gold"}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        return config.get("economy", {"currency_name": "gold"})

class EconomyAdminCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = load_economy_config()

    @app_commands.command(name="addgold", description="Add gold to a user's balance.")
    @app_commands.describe(user="The user to give gold to", amount="Amount of gold to add")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def addgold(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        await interaction.response.defer(ephemeral=True)
        
        if amount <= 0:
            await interaction.followup.send("Amount must be greater than 0.", ephemeral=True)
            return
        
        guild_id = interaction.guild.id
        new_balance = await add_gold(user.id, guild_id, amount)
        currency = self.config.get("currency_name", "gold")
        
        embed = discord.Embed(
            title="Gold Added",
            description=f"Added **{amount} {currency}** to {user.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="New Balance", value=f"{new_balance} {currency}", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="removegold", description="Remove gold from a user's balance.")
    @app_commands.describe(user="The user to remove gold from", amount="Amount of gold to remove")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def removegold(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        await interaction.response.defer(ephemeral=True)
        
        if amount <= 0:
            await interaction.followup.send("Amount must be greater than 0.", ephemeral=True)
            return
        
        guild_id = interaction.guild.id
        success, new_balance = await remove_gold(user.id, guild_id, amount)
        currency = self.config.get("currency_name", "gold")
        
        if not success:
            await interaction.followup.send(
                f"{user.mention} only has **{new_balance} {currency}**. Cannot remove {amount} {currency}.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="Gold Removed",
            description=f"Removed **{amount} {currency}** from {user.mention}",
            color=discord.Color.red()
        )
        embed.add_field(name="New Balance", value=f"{new_balance} {currency}", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="setgold", description="Set a user's gold balance to a specific amount.")
    @app_commands.describe(user="The user to set gold for", amount="Amount of gold to set")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setgold(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        await interaction.response.defer(ephemeral=True)
        
        if amount < 0:
            await interaction.followup.send("Amount cannot be negative.", ephemeral=True)
            return
        
        guild_id = interaction.guild.id
        await set_gold(user.id, guild_id, amount)
        currency = self.config.get("currency_name", "gold")
        
        embed = discord.Embed(
            title="Gold Set",
            description=f"Set {user.mention}'s balance to **{amount} {currency}**",
            color=discord.Color.blue()
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="checkgold", description="Check another user's gold balance.")
    @app_commands.describe(user="The user to check")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def checkgold(self, interaction: discord.Interaction, user: discord.Member):
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        gold = await get_gold(user.id, guild_id)
        currency = self.config.get("currency_name", "gold")
        
        embed = discord.Embed(
            title=f"{user.name}'s Balance",
            description=f"{user.mention} has **{gold} {currency}**",
            color=discord.Color.gold()
        )
        embed.set_thumbnail(url=user.display_avatar.url)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(EconomyAdminCog(bot))
