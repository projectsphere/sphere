import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
from utils.database import (
    add_player,
    fetch_all_servers,
    fetch_player,
    player_autocomplete,
    start_session,
    update_active_session,
    end_session,
    get_active_sessions,
    get_player_session
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
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()

        if not hasattr(self, 'server_online_cache'):
            self.server_online_cache = {}

        for server in servers:
            guild_id, server_name, host, password, api_port, rcon_port = server
            try:
                api = PalworldAPI(f"http://{host}:{api_port}", "admin", password)
                player_list = await api.get_player_list()
                current_online = set(player['userId'] for player in player_list['players'])
                previous_online = self.server_online_cache.get(server_name, set())
                self.server_online_cache[server_name] = current_online

                for player in player_list['players']:
                    await add_player(player)

                active_sessions = await get_active_sessions()
                for uid in current_online:
                    if uid not in active_sessions:
                        await start_session(uid, now)
                    else:
                        await update_active_session(uid, now)

                for uid in previous_online - current_online:
                    await end_session(uid, now)

            except Exception as e:
                if server_name in self.server_online_cache:
                    for uid in self.server_online_cache[server_name]:
                        await end_session(uid, now)
                    del self.server_online_cache[server_name]
                logging.error(f"API unreachable for '{server_name}', sessions ended for tracked users: {str(e)}")

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
    @app_commands.guild_only()
    async def player_lookup(self, interaction: discord.Interaction, user: str):
        player = await fetch_player(user)
        if player:
            session = await get_player_session(user)
            now = datetime.datetime.now(datetime.timezone.utc)
            total = session[1]
            if session[2]:
                dt_start = datetime.datetime.fromisoformat(session[2])
                total += int((now - dt_start).total_seconds())
            h = total // 3600
            m = (total % 3600) // 60
            s = total % 60
            if h == 0:
                time_str = f"`{m}m {s}s`"
            else:
                time_str = f"`{h}h {m}m {s}s`"
            embed = self.player_embed(player, time_str)
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message("Player not found.", ephemeral=True)

    def player_embed(self, player, time_str):
        embed = discord.Embed(title=f"Player: {player[1]} ({player[2]})", color=discord.Color.blurple())
        embed.add_field(name="Level", value=player[8])
        embed.add_field(name="Ping", value=player[5])
        embed.add_field(name="Location", value=f"({player[6]}, {player[7]})")
        embed.add_field(name="PlayerID", value=f"```{player[0]}```", inline=False)
        embed.add_field(name="PlayerUID", value=f"```{player[3]}```", inline=False)
        embed.add_field(name="PlayerIP", value=f"```{player[4]}```", inline=False)
        embed.add_field(name="Playtime", value=time_str)
        return embed

    @log_players.before_loop
    async def before_log_players(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(PlayerLoggingCog(bot))