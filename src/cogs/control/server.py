from discord.ext import commands
from discord import app_commands
import discord
from utils.database import (
    add_server,
    remove_server,
    server_autocomplete,
    remove_whitelist_status,
    delete_chat,
    del_backup,
    delete_query,
    remove_logchannel
)
from utils.servermodal import AddServerModal
from palworld_api import PalworldAPI
import logging

class ServerManagementCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addserver", description="Add a server configuration")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def add_server_command(self, interaction: discord.Interaction):
        modal = AddServerModal(title="Add Server")

        async def on_submit_override(modal_interaction: discord.Interaction):
            await modal_interaction.response.defer(ephemeral=True)

            server_name = modal.children[0].value
            host = modal.children[1].value
            password = modal.children[2].value
            api_port = int(modal.children[3].value) if modal.children[3].value else None
            rcon_port = int(modal.children[4].value) if modal.children[4].value else None

            try:
                api = PalworldAPI(f"http://{host}:{api_port}", password)
                server_info = await api.get_server_info()
                
                if not server_info or 'version' not in server_info:
                    await modal_interaction.followup.send("Failed to connect to server: Invalid response from API.", ephemeral=True)
                    return
                
                await add_server(
                    interaction.guild_id,
                    server_name,
                    host,
                    password,
                    api_port,
                    rcon_port
                )
                await modal_interaction.followup.send(f"Server added successfully. Version: {server_info.get('version', 'Unknown')}", ephemeral=True)
            except Exception as e:
                await modal_interaction.followup.send(f"Failed to add server: {e}", ephemeral=True)
                logging.error(f"Failed to add server: {e}")

        modal.on_submit = on_submit_override
        await interaction.response.send_modal(modal)
        
    async def server_names(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id
        server_names = await server_autocomplete(guild_id, current)
        return [app_commands.Choice(name=name, value=name) for name in server_names]

    @app_commands.command(name="removeserver", description="Remove a server configuration")
    @app_commands.autocomplete(server=server_names)
    @app_commands.describe(server="Server to remove")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def remove_server_command(self, interaction: discord.Interaction, server: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await remove_server(interaction.guild_id, server)
            await remove_whitelist_status(interaction.guild_id, server)
            await delete_chat(interaction.guild_id, server)
            await del_backup(interaction.guild_id, server)
            await delete_query(interaction.guild_id, server)
            await remove_logchannel(interaction.guild_id, server)
            await interaction.followup.send("Server removed successfully.")
        except Exception as e:
            await interaction.followup.send(f"Failed to remove server: {e}", ephemeral=True)
            logging.error(f"Failed to remove server: {e}")

async def setup(bot):
    await bot.add_cog(ServerManagementCog(bot))
