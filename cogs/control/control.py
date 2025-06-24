import discord
from discord.ext import commands
from discord import app_commands
from utils.database import fetch_server_details, server_autocomplete
from palworld_api import PalworldAPI
import logging

class ControlCog(commands.Cog):
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

    @app_commands.command(name="announce", description="Make an announcement to the server.")
    @app_commands.describe(server="The name of the server", message="The message to announce")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def announce(self, interaction: discord.Interaction, server: str, message: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            api, error = await self.get_api_instance(interaction.guild.id, server)
            if error:
                await interaction.followup.send(error, ephemeral=True)
                return
            
            await api.make_announcement(message)
            await interaction.followup.send(f"Announcement sent: {message}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {str(e)}", ephemeral=True)
            logging.error(f"An unexpected error occurred: {str(e)}")

    @app_commands.command(name="shutdown", description="Shutdown the server.")
    @app_commands.describe(server="The name of the server", message="The message to display before shutdown", seconds="The number of seconds before shutdown")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def shutdown(self, interaction: discord.Interaction, server: str, message: str, seconds: int):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            api, error = await self.get_api_instance(interaction.guild.id, server)
            if error:
                await interaction.followup.send(error, ephemeral=True)
                return
            
            await api.shutdown_server(seconds, message)
            await interaction.followup.send(f"Server will shutdown in {seconds} seconds: {message}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {str(e)}", ephemeral=True)
            logging.error(f"An unexpected error occurred: {str(e)}")

    @app_commands.command(name="stop", description="Stop the server.")
    @app_commands.describe(server="The name of the server")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def stop(self, interaction: discord.Interaction, server: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            api, error = await self.get_api_instance(interaction.guild.id, server)
            if error:
                await interaction.followup.send(error, ephemeral=True)
                return
            
            response = await api.stop_server()
            await interaction.followup.send(f"Server stopped: {response}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {str(e)}", ephemeral=True)
            logging.error(f"An unexpected error occurred: {str(e)}")

    @app_commands.command(name="save", description="Save the server state.")
    @app_commands.describe(server="The name of the server")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def save(self, interaction: discord.Interaction, server: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            api, error = await self.get_api_instance(interaction.guild.id, server)
            if error:
                await interaction.followup.send(error, ephemeral=True)
                return
            
            response = await api.save_server_state()
            await interaction.followup.send(f"Server state saved: {response}", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {str(e)}", ephemeral=True)
            logging.error(f"An unexpected error occurred: {str(e)}")
    
async def setup(bot):
    await bot.add_cog(ControlCog(bot))
