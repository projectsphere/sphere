import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.database import (
    fetch_all_servers,
    add_logchannel,
    remove_logchannel,
    fetch_logchannel,
    server_autocomplete,
    update_player_playtime,
    add_active_session,
    remove_active_session,
    load_active_sessions,
    load_total_playtimes_for_server
)
from palworld_api import PalworldAPI
import logging
from datetime import timedelta, datetime

def discord_timestamp(dt: datetime, style: str = "f") -> str:
    """Return a Discord-formatted timestamp. Example: <t:1632105600:f>"""
    return f"<t:{int(dt.timestamp())}:{style}>"

def format_duration(duration: timedelta) -> str:
    """Converts a timedelta to a string showing hours, minutes, and seconds."""
    total_seconds = int(duration.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours}h {minutes}m {seconds}s"

class EventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.player_cache = {}
        self.active_sessions = {}
        self.total_playtimes = {}
        self.log_players.start()

    def cog_unload(self):
        self.log_players.cancel()

    @tasks.loop(seconds=20)
    async def log_players(self):
        servers = await fetch_all_servers()
        for server in servers:
            guild_id, server_name, host, password, api_port, rcon_port = server
            log_channel_id = await fetch_logchannel(guild_id, server_name)
            if not log_channel_id:
                continue

            channel = self.bot.get_channel(log_channel_id)
            if not channel:
                continue

            try:
                api = PalworldAPI(f"http://{host}:{api_port}", "admin", password)
                player_list = await api.get_player_list()
                current_players = {(player['userId'], player['accountName']) for player in player_list['players']}

                if server_name not in self.player_cache:
                    self.player_cache[server_name] = current_players
                    self.active_sessions[server_name] = await load_active_sessions(server_name)
                    self.total_playtimes[server_name] = await load_total_playtimes_for_server(server_name)

                old_players = self.player_cache[server_name]
                joined_players = current_players - old_players
                left_players = old_players - current_players

                for userId, accountName in joined_players:
                    now = discord.utils.utcnow()
                    if server_name not in self.active_sessions:
                        self.active_sessions[server_name] = {}
                    self.active_sessions[server_name][userId] = now
                    await add_active_session(server_name, userId, int(now.timestamp()))
                    join_time_str = discord_timestamp(now, "f")
                    join_text = f"Player `{accountName} ({userId})` has joined **{server_name}** at {join_time_str}."
                    join_embed = discord.Embed(
                        title="Player Joined",
                        description=join_text,
                        color=discord.Color.green(),
                        timestamp=now
                    )
                    await channel.send(embed=join_embed)

                for userId, accountName in left_players:
                    now = discord.utils.utcnow()
                    leave_str = discord_timestamp(now, "f")
                    join_time = self.active_sessions.get(server_name, {}).pop(userId, None)
                    if join_time:
                        session_duration = now - join_time
                        session_str = format_duration(session_duration)
                        session_seconds = int(session_duration.total_seconds())
                        await update_player_playtime(server_name, userId, session_seconds)
                        previous_total = self.total_playtimes[server_name].get(userId, 0)
                        new_total = previous_total + session_seconds
                        self.total_playtimes[server_name][userId] = new_total
                        total_str = format_duration(timedelta(seconds=new_total))
                        join_time_str = discord_timestamp(join_time, "f")
                        left_text = (
                            f"Player `{accountName} ({userId})` has left **{server_name}** at {leave_str}.\n"
                            f"**Session Duration:** {session_str} (Joined at {join_time_str})\n"
                            f"**Total Playtime:** {total_str}"
                        )
                        # Remove persistent active session.
                        await remove_active_session(server_name, userId)
                    else:
                        left_text = f"Player `{accountName} ({userId})` has left **{server_name}** at {leave_str} (join time not recorded)."
                    
                    left_embed = discord.Embed(
                        title="Player Left",
                        description=left_text,
                        color=discord.Color.red(),
                        timestamp=now
                    )
                    await channel.send(embed=left_embed)

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
