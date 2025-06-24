import discord
from discord.ext import commands, tasks
import os
import datetime
import logging
from palworld_api import PalworldAPI
from utils.database import fetch_all_servers

class SaveMonitor(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_mod_time = None
        self.first_check_time = None
        self.monitor_loop.start()

    def cog_unload(self):
        self.monitor_loop.cancel()

    @tasks.loop(seconds=60)
    async def monitor_loop(self):
        save_path = os.getenv("SAVE_PATH")
        server_name = os.getenv("SERVER_NAME")

        if not save_path or not server_name:
            return

        servers = await fetch_all_servers()
        target = next((s for s in servers if s[1] == server_name), None)

        if not target:
            return

        _, _, host, password, api_port, _ = target
        level_sav = os.path.join(save_path, "Level.sav")

        if not os.path.exists(level_sav):
            return

        try:
            mod_time = os.path.getmtime(level_sav)
            now = datetime.datetime.utcnow().timestamp()

            if self.first_check_time is None:
                self.first_check_time = now
                self.last_mod_time = mod_time
                return

            if now - self.first_check_time < 300:
                return

            if now - mod_time > 300 and self.last_mod_time == mod_time:
                api = PalworldAPI(f"http://{host}:{api_port}", password)
                await api.shutdown_server(30, "Save stalled! Restarting in 30 seconds!")
                logging.info(f"Server '{server_name}' save file is stalled. Restarting server.")
                self.last_mod_time = now
            else:
                self.last_mod_time = mod_time

        except Exception as e:
            logging.error(f"Save monitor loop error: {e}")
            self.monitor_loop.cancel()

    @monitor_loop.before_loop
    async def before_monitor_loop(self):
        await self.bot.wait_until_ready()

        save_path = os.getenv("SAVE_PATH")
        server_name = os.getenv("SERVER_NAME")

        if not save_path or not server_name:
            self.monitor_loop.cancel()
            return

        servers = await fetch_all_servers()
        target = next((s for s in servers if s[1] == server_name), None)

        if not target:
            self.monitor_loop.cancel()
            return

        _, _, host, password, api_port, _ = target
        api = PalworldAPI(f"http://{host}:{api_port}", password)

        try:
            await api.get_server_info()
        except Exception as e:
            logging.error(f"Failed to contact API. Canceling monitor: {e}")
            self.monitor_loop.cancel()

async def setup(bot):
    await bot.add_cog(SaveMonitor(bot))
