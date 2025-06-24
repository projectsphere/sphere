import discord
from discord.ext import commands, tasks
from utils.database import fetch_all_servers
from palworld_api import PalworldAPI
import aiohttp
import logging
from aiocache import Cache
import os
import asyncio

# This is for logging VAC Banned and account name mismatches
# Not really needed anymore due to crossplay.
class VACCheckCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = Cache(Cache.MEMORY)
        self.vac_check_task.start()

    def cog_unload(self):
        self.vac_check_task.cancel()

    @tasks.loop(minutes=5)
    async def vac_check_task(self):
        servers = await fetch_all_servers()
        for server in servers:
            guild_id, server_name, host, password, api_port, rcon_port = server
            try:
                api = PalworldAPI(f"http://{host}:{api_port}", password)
                player_list = await api.get_player_list()

                for player in player_list.get("players", []):
                    user_id = player.get("userId")
                    account_name = player.get("accountName")
                    ip_address = player.get("ip")

                    if user_id and user_id.startswith("steam_"):
                        cached = await self.cache.get(user_id)
                        if cached:
                            #logging.info(f"Skipping recently checked user: {user_id}")
                            continue

                        steam_id = user_id.replace("steam_", "")
                        await self.check_vac_status(steam_id, account_name, ip_address)
                        await self.validate_account_name(steam_id, account_name)

                        await self.cache.set(user_id, True, ttl=600)
                        await asyncio.sleep(2)

            except Exception as e:
                logging.error(f"Error processing server '{server_name}': {str(e)}")

    async def check_vac_status(self, steam_id, account_name, ip_address):
        steam_api_key = os.getenv("STEAM_API_KEY")
        if not steam_api_key:
            logging.error("STEAM_API_KEY environment variable is not set.")
            return

        url = "https://api.steampowered.com/ISteamUser/GetPlayerBans/v1/"
        params = {"key": steam_api_key, "steamids": steam_id}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data["players"]:
                            player_data = data["players"][0]
                            if player_data["VACBanned"]:
                                logging.info(
                                    f"VAC Ban detected for Steam ID {steam_id} | Account Name: {account_name} | IP: {ip_address} | Details: {player_data}"
                                )
                            else:
                                logging.info(
                                    f"No VAC Ban for Steam ID {steam_id} | Account Name: {account_name} | IP: {ip_address}."
                                )
                        else:
                            logging.warning(
                                f"No data returned for Steam ID {steam_id} | Account Name: {account_name} | IP: {ip_address}."
                            )
                    else:
                        logging.error(
                            f"Failed to check VAC status for Steam ID {steam_id} | Account Name: {account_name} | IP: {ip_address}. Response: {response.status}"
                        )
        except Exception as e:
            logging.error(
                f"Error checking VAC status for Steam ID {steam_id} | Account Name: {account_name} | IP: {ip_address}: {str(e)}"
            )

    async def validate_account_name(self, steam_id, account_name):
        steam_api_key = os.getenv("STEAM_API_KEY")
        if not steam_api_key:
            logging.error("STEAM_API_KEY environment variable is not set.")
            return

        url = "https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
        params = {"key": steam_api_key, "steamids": steam_id}

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        players = data.get("response", {}).get("players", [])
                        if players:
                            steam_personaname = players[0].get("personaname")
                            if account_name == steam_personaname:
                                logging.info(
                                    f"Account name match: Palworld Account Name '{account_name}' matches Steam Name '{steam_personaname}' for Steam ID {steam_id}."
                                )
                            else:
                                logging.warning(
                                    f"Account name mismatch: Palworld Account Name '{account_name}' does not match Steam Name '{steam_personaname}' for Steam ID {steam_id}."
                                )
                        else:
                            logging.warning(
                                f"No player summary found for Steam ID {steam_id}."
                            )
                    else:
                        logging.error(
                            f"Failed to fetch player summary for Steam ID {steam_id}. Response: {response.status}"
                        )
        except Exception as e:
            logging.error(
                f"Error validating account name for Steam ID {steam_id}: {str(e)}"
            )

    @vac_check_task.before_loop
    async def before_vac_check_task(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    if not os.getenv("STEAM_API_KEY"):
        logging.error("Steam API Key is not set. VAC Check cog will not be loaded.")
        return
    await bot.add_cog(VACCheckCog(bot))
