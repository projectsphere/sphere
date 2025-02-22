import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.database import (
    fetch_all_servers,
    add_logchannel,
    remove_logchannel,
    fetch_logchannel,
    server_autocomplete
)
from palworld_api import PalworldAPI
import logging

class EventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.player_cache = {}
        self.log_players.start()

    def cog_unload(self):
        self.log_players.cancel()

    @tasks.loop(seconds=20)
    async def log_players(self):
        servers = await fetch_all_servers()
        for server in servers:
            guild_id, server_name, host, password, api_port = server
            log_channel_id = await fetch_logchannel(guild_id, server_name)
            if log_channel_id:
                channel = self.bot.get_channel(log_channel_id)
                if channel:
                    try:
                        api = PalworldAPI(f"http://{host}:{api_port}", "admin", password)
                        player_list = await api.get_player_list()
                        current_players = {(player['userId'], player['accountName']) for player in player_list['players']}

                        if server_name not in self.player_cache:
                            self.player_cache[server_name] = current_players
                            continue

                        old_players = self.player_cache[server_name]
                        joined_players = current_players - old_players
                        left_players = old_players - current_players

                        for userId, accountName in joined_players:
                            join_text = f"Player `{accountName} ({userId})` has joined {server_name}."
                            join = discord.Embed(title="Player Joined", description=join_text , color=discord.Color.green())
                            await channel.send(embed=join)
                        for userId, accountName in left_players:
                            left_text = f"Player `{accountName} ({userId})` has left {server_name}."
                            left = discord.Embed(title="Player Left", description=left_text, color=discord.Color.red())
                            await channel.send(embed=left)

                        self.player_cache[server_name] = current_players
                    except Exception as e:
                        logging.error(f"Issues logging player on '{server_name}': {str(e)}")

    @log_players.before_loop
    async def before_log_players(self):
        await self.bot.wait_until_ready()
        
    async def server_names(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id
        server_names = await server_autocomplete(guild_id, current)
        return [app_commands.Choice(name=name, value=name) for name in server_names]
    
    log_group = app_commands.Group(name="logs", description="Log player join/leave events", default_permissions=discord.Permissions(administrator=True), guild_only=True)

    @log_group.command(name="set", description="Set the logging channel for player join/leave events")
    @app_commands.describe(server="The name of the server", channel="The channel to log events in")
    @app_commands.autocomplete(server=server_names)
    async def set_logchannel(self, interaction: discord.Interaction, server: str, channel: discord.TextChannel):
        await add_logchannel(interaction.guild.id, channel.id, server)
        await interaction.response.send_message(f"Log channel for server '{server}' set to {channel.mention}.", ephemeral=True)

    @log_group.command(name="remove", description="Remove the logging channel for player join/leave events")
    @app_commands.describe(server="The name of the server")
    @app_commands.autocomplete(server=server_names)
    async def delete_logchannel(self, interaction: discord.Interaction, server: str):
        await remove_logchannel(interaction.guild.id, server)
        await interaction.response.send_message(f"Log channel for server '{server}' removed.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EventsCog(bot))
