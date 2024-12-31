import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.database import (
    add_player,
    fetch_all_servers,
    fetch_player,
    player_autocomplete
)
from palworld_api import PalworldAPI
import logging

class PlayerLoggingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log_players.start()

    def cog_unload(self):
        self.log_players.cancel()

    @tasks.loop(seconds=30)
    async def log_players(self):
        servers = await fetch_all_servers()
        for server in servers:
            guild_id, server_name, host, password, api_port = server
            try:
                api = PalworldAPI(f"http://{host}:{api_port}", "admin", password)
                player_list = await api.get_player_list()
                for player in player_list['players']:
                    await add_player(player)
                logging.info(f"Players from server '{server_name}' logged successfully.")
            except Exception as e:
                logging.error(f"Issues logging players on '{server_name}': {str(e)}")

    async def player_autocomplete(self, interaction: discord.Interaction, current: str):
        players = await player_autocomplete(current)
        choices = [
            app_commands.Choice(name=f"{player[1]} (ID: {player[0]})", value=player[0]) 
            for player in players[:25]
        ]
        return choices

    @app_commands.command(name="lookup", description="Fetch and display player information")
    @app_commands.autocomplete(user=player_autocomplete)
    @app_commands.default_permissions(administrator=True)
    async def player_lookup(self, interaction: discord.Interaction, user: str):
        player = await fetch_player(user)
        if player:
            embed = self.player_embed(player)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("Player not found.", ephemeral=True)

    def player_embed(self, player):
        embed = discord.Embed(title=f"Player: {player[1]} ({player[2]})", color=discord.Color.blurple())
        embed.add_field(name="Level", value=player[8])
        embed.add_field(name="Ping", value=player[5])
        embed.add_field(name="Location", value=f"({player[6]}, {player[7]})")
        embed.add_field(name="PlayerID", value=f"```{player[0]}```", inline=False)
        embed.add_field(name="PlayerUID", value=f"```{player[3]}```", inline=False)
        embed.add_field(name="PlayerIP", value=f"```{player[4]}```", inline=False)
        return embed

    @log_players.before_loop
    async def before_log_players(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(PlayerLoggingCog(bot))
