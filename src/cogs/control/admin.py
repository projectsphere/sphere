import discord
from discord.ext import commands
from discord import app_commands
from utils.database import fetch_server_details, server_autocomplete
from utils.bans import (
    fetch_bans,
    log_ban,
    clear_bans
)
from palworld_api import PalworldAPI
import logging
import io

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_api_instance(self, guild_id, server_name):
        server_config = await fetch_server_details(guild_id, server_name)
        if not server_config:
            return None, f"Server '{server_name}' configuration not found."
        
        host = server_config[2]
        password = server_config[3]
        api_port = server_config[4]
        
        api = PalworldAPI(f"http://{host}:{api_port}", password)
        return api, None

    async def server_autocomplete(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id
        server_names = await server_autocomplete(guild_id, current)
        choices = [app_commands.Choice(name=name, value=name) for name in server_names]
        return choices

    @app_commands.command(name="kick", description="Kick a player from the server.")
    @app_commands.describe(server="The name of the server", player_id="The player ID to kick", reason="The reason for the kick")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def kick_player(self, interaction: discord.Interaction, server: str, player_id: str, reason: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            api, error = await self.get_api_instance(interaction.guild.id, server)
            if error:
                await interaction.followup.send(error, ephemeral=True)
                return
            
            await api.kick_player(player_id, reason)
            await interaction.followup.send(f"Player {player_id} has been kicked for: {reason}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {str(e)}", ephemeral=True)
            logging.error(f"An unexpected error occurred: {str(e)}")

    @app_commands.command(name="ban", description="Ban a player from the server.")
    @app_commands.describe(server="The name of the server", player_id="The player ID to ban", reason="The reason for the ban")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def ban_player(self, interaction: discord.Interaction, server: str, player_id: str, reason: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            api, error = await self.get_api_instance(interaction.guild.id, server)
            if error:
                await interaction.followup.send(error, ephemeral=True)
                return
            
            await api.ban_player(player_id, reason)
            await log_ban(player_id, reason)
            await interaction.followup.send(f"Player {player_id} has been banned for: {reason}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {str(e)}", ephemeral=True)
            logging.error(f"An unexpected error occurred: {str(e)}")

    @app_commands.command(name="unban", description="Unban a player from the server.")
    @app_commands.describe(server="The name of the server", player_id="The player ID to unban")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def unban_player(self, interaction: discord.Interaction, server: str, player_id: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            api, error = await self.get_api_instance(interaction.guild.id, server)
            if error:
                await interaction.followup.send(error, ephemeral=True)
                return
            
            await api.unban_player(player_id)
            await interaction.followup.send(f"Player {player_id} has been unbanned.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {str(e)}", ephemeral=True)
            logging.error(f"An unexpected error occurred: {str(e)}")

    # Uploads ban logs as a text file
    @app_commands.command(name="bans", description="List all banned players.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def list_bans(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        bans = await fetch_bans()
        if bans:
            ban_list = "\n".join([f"{ban[0]}: {ban[1]}" for ban in bans])
            ban_file = io.StringIO(ban_list)
            discord_file = discord.File(ban_file, filename="bannedplayers.txt")
            await interaction.followup.send("Banned players:", file=discord_file, ephemeral=True)
            ban_file.close()
        else:
            await interaction.followup.send("No players are banned.", ephemeral=True)
            logging.info("No players are banned.")

    @app_commands.command(name="clearbans", description="Clear ban history from the database.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def clear_bans_command(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=True)
        await clear_bans()
        await interaction.followup.send("All bans have been cleared.", ephemeral=True)
        logging.info("All bans have been cleared.")

async def setup(bot):
    await bot.add_cog(AdminCog(bot))
