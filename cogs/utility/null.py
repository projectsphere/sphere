import discord
from discord.ext import commands, tasks
from utils.database import fetch_all_servers, fetch_logchannel
from palworld_api import PalworldAPI
import logging

class NullPlayerCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_players.start()

    def cog_unload(self):
        self.check_players.cancel()

    # Temporary fix for null players joining without a valid ID.
    @tasks.loop(seconds=10)
    async def check_players(self):
        servers = await fetch_all_servers()
        for server in servers:
            guild_id, server_name, host, password, api_port, rcon_port = server
            log_channel_id = await fetch_logchannel(guild_id, server_name)
            log_channel = self.bot.get_channel(log_channel_id) if log_channel_id else None

            try:
                api = PalworldAPI(f"http://{host}:{api_port}", password)
                player_list = await api.get_player_list()
                for player in player_list['players']:
                    playerid = player['userId']
                    if "null_" in playerid:
                        await api.kick_player(playerid, "Invalid ID detected.")
                        logging.info(f"Kicked player {playerid} from server '{server_name}' due to invalid ID.")

                        if log_channel:
                            embed = discord.Embed(
                                title="Invalid ID Detected",
                                description=f"Player `{playerid}` was kicked from server {server_name} due to an invalid ID.",
                                color=discord.Color.red(),
                                timestamp=discord.utils.utcnow()
                            )
                            await log_channel.send(embed=embed)

                # logging.info(f"Checked null players for server '{server_name}'.")
            except Exception as e:
                logging.error(f"Error checking null players for server '{server_name}': {str(e)}")

    @check_players.before_loop
    async def before_check_players(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(NullPlayerCheck(bot))
