import discord
from discord.ext import commands
import os
import datetime
import logging
import asyncio
import yaml
from paramiko import SSHClient, AutoAddPolicy
from utils.database import fetch_server_details
from palworld_api import PalworldAPI

CONFIG_FILE = os.path.join("config", "sftp.yml")

def load_yaml_config():
    if not os.path.exists(CONFIG_FILE):
        return {"servers": []}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"servers": []}

class SFTPSaveCheckCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = [cfg for cfg in load_yaml_config().get("servers", []) if cfg.get("save_path")]
        self.first_check_time = {}
        self.last_mod_time = {}
        self.failure_count = {}
        self.failure_threshold = 3
        self.poll_seconds = 60
        self.tasks = {}
        self._start_tasks = asyncio.create_task(self._spawn())

    def cog_unload(self):
        for t in self.tasks.values():
            t.cancel()

    def _sftp_stat_mtime(self, cfg, remote_path):
        ssh = None
        sftp = None
        try:
            ssh = SSHClient()
            ssh.set_missing_host_key_policy(AutoAddPolicy())
            ssh.connect(
                hostname=cfg["host"],
                username=cfg["username"],
                password=cfg["password"],
                port=int(cfg.get("port", 2022)),
                timeout=10,
            )
            sftp = ssh.open_sftp()
            return sftp.stat(remote_path).st_mtime
        finally:
            try:
                if sftp:
                    sftp.close()
            except:
                pass
            try:
                if ssh:
                    ssh.close()
            except:
                pass

    async def _worker(self, cfg):
        name = cfg["name"]
        remote_root = cfg["save_path"].rstrip("/\\")
        level_path = f"{remote_root}/Level.sav"
        self.first_check_time.setdefault(name, None)
        self.last_mod_time.setdefault(name, None)
        self.failure_count.setdefault(name, 0)
        while True:
            try:
                now = datetime.datetime.utcnow().timestamp()
                try:
                    mod_time = await asyncio.to_thread(self._sftp_stat_mtime, cfg, level_path)
                except Exception as e:
                    logging.warning(f"[{name}] save mtime check failed: {e}")
                    self.failure_count[name] += 1
                    if self.failure_count[name] >= self.failure_threshold:
                        details = await fetch_server_details(cfg.get("guild_id", 0), name) if "guild_id" in cfg else await fetch_server_details(0, name)
                        if details:
                            host = details[2]; password = details[3]; api_port = details[4]
                            api = PalworldAPI(f"http://{host}:{api_port}", password)
                            try:
                                await api.shutdown_server(30, "Save check failed repeatedly. Restarting in 30 seconds.")
                            except Exception as ex:
                                logging.error(f"[{name}] API restart failed: {ex}")
                        self.failure_count[name] = 0
                        self.first_check_time[name] = now
                    await asyncio.sleep(self.poll_seconds)
                    continue

                if self.first_check_time[name] is None:
                    self.first_check_time[name] = now
                    self.last_mod_time[name] = mod_time
                    await asyncio.sleep(self.poll_seconds)
                    continue

                if now - self.first_check_time[name] < 300:
                    self.last_mod_time[name] = mod_time
                    await asyncio.sleep(self.poll_seconds)
                    continue

                if (now - mod_time) > 300 and self.last_mod_time[name] == mod_time:
                    self.failure_count[name] += 1
                    logging.warning(f"[{name}] save stall attempt {self.failure_count[name]}/{self.failure_threshold}")
                else:
                    self.failure_count[name] = 0

                self.last_mod_time[name] = mod_time

                if self.failure_count[name] >= self.failure_threshold:
                    details = await fetch_server_details(cfg.get("guild_id", 0), name) if "guild_id" in cfg else await fetch_server_details(0, name)
                    if details:
                        host = details[2]; password = details[3]; api_port = details[4]
                        api = PalworldAPI(f"http://{host}:{api_port}", password)
                        try:
                            await api.shutdown_server(30, "Save stalled! Restarting in 30 seconds!")
                            logging.info(f"[{name}] save stalled — initiating restart.")
                        except Exception as e:
                            logging.error(f"[{name}] restart failed: {e}")
                    self.failure_count[name] = 0
                    self.first_check_time[name] = now
            except Exception as e:
                logging.exception(f"[{name}] exception in save monitor: {e}")
            await asyncio.sleep(self.poll_seconds)

    async def _spawn(self):
        for cfg in self.config:
            name = cfg["name"]
            if name not in self.tasks:
                self.tasks[name] = asyncio.create_task(self._worker(cfg), name=f"save-worker:{name}")

async def setup(bot):
    if not os.path.exists(CONFIG_FILE):
        logging.warning("sftp.yml not found, SFTP Save Check cog not loaded.")
        return
    await bot.add_cog(SFTPSaveCheckCog(bot))
