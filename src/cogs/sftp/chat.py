import discord
from discord.ext import commands
import aiohttp
import re
from paramiko import SSHClient, AutoAddPolicy
import logging
import os
import asyncio
import yaml
from utils.database import fetch_server_details, verify_link_code, link_player, fetch_player
from palworld_api import PalworldAPI

CONFIG_FILE = os.path.join("config", "sftp.yml")

def load_yaml_config():
    if not os.path.exists(CONFIG_FILE):
        return {"servers": []}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"servers": []}

class SFTPChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_yaml_config().get("servers", [])
        self.sessions = {}
        self.last_processed_line = {}
        self.first_check_done = {}
        self.tasks = {}
        self.interval = 15
        self.blocked_phrases = ["/adminpassword", "/creativemenu", "/", "!"]
        self._chat_regex = re.compile(r"\[Chat::(?:Global|Local)\]\['([^']+)'.*\]: (.*)")
        self._link_regex = re.compile(r"\[Chat::(?:Global|Local)\]\['([^']+)'\s*\(UserId=([^,]+),.*\]:\s*[!/]link\s+([A-Z0-9]+)", re.IGNORECASE)

    async def cog_load(self):
        for cfg in self.config:
            name = cfg["name"]
            self.sessions[name] = aiohttp.ClientSession()
            self.last_processed_line[name] = None
            self.first_check_done[name] = False
            self.tasks[name] = asyncio.create_task(self._server_worker(cfg))

    async def cog_unload(self):
        for t in self.tasks.values():
            t.cancel()
        await asyncio.gather(*self.tasks.values(), return_exceptions=True)
        await asyncio.gather(*(s.close() for s in self.sessions.values()), return_exceptions=True)

    def _connect_and_read(self, cfg, last_line, first_done):
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
            log_dir = cfg.get("path", "Pal/Binaries/Win64/PalDefender/Logs")
            sftp.chdir(log_dir)
            files = sorted(sftp.listdir(), key=lambda x: sftp.stat(x).st_mtime, reverse=True)
            log_file_path = next((f for f in files if f.endswith(".log") or f.endswith(".txt")), None)
            if not log_file_path:
                return [], last_line, first_done
            with sftp.file(log_file_path, "r") as file:
                content = file.read().decode("utf-8", errors="ignore")
                lines = content.splitlines()
            if not first_done:
                return [], lines[-1] if lines else None, True
            new_lines = []
            new_lines_start = False
            for line in lines:
                if line == last_line:
                    new_lines_start = True
                    continue
                if new_lines_start or last_line is None:
                    if "[Chat::" in line:
                        new_lines.append(line)
            return new_lines, lines[-1] if lines else last_line, True
        except Exception as e:
            logging.error(f"[{cfg['name']}] SFTP error: {e}")
            return [], last_line, first_done
        finally:
            if sftp:
                try:
                    sftp.close()
                except:
                    pass
            if ssh:
                try:
                    ssh.close()
                except:
                    pass

    async def _server_worker(self, cfg):
        name = cfg["name"]
        while True:
            try:
                lines, new_last, first_done = await asyncio.to_thread(
                    self._connect_and_read,
                    cfg,
                    self.last_processed_line[name],
                    self.first_check_done[name],
                )
                if not self.first_check_done[name] and first_done:
                    self.last_processed_line[name] = new_last
                    self.first_check_done[name] = True
                else:
                    for line in lines:
                        await self.process_and_send(cfg, line)
                        if "link_channel" in cfg:
                            await self.process_link_command(cfg, line)
                        await asyncio.sleep(1)
                    self.last_processed_line[name] = new_last
                    self.first_check_done[name] = first_done
            except Exception as e:
                logging.error(f"[{name}] Worker error: {e}")
            await asyncio.sleep(self.interval)

    async def process_and_send(self, cfg, line):
        try:
            match = self._chat_regex.search(line)
            if match:
                username, message = match.groups()
                if any(bp in message for bp in self.blocked_phrases):
                    return
                payload = {"username": f"{username} ({cfg['name']})", "content": message}
                async with self.sessions[cfg["name"]].post(cfg["webhook"], json=payload) as response:
                    if response.status != 200:
                        logging.info(f"[{cfg['name']}] Webhook error: {response.status} - {await response.text()}")
        except Exception as e:
            logging.error(f"[{cfg['name']}] Error processing line: {e}")

    async def process_link_command(self, cfg, line):
        try:
            match = self._link_regex.search(line)
            if match:
                player_name, user_id, code = match.groups()
                code = code.upper()
                
                discord_id = await verify_link_code(code)
                if discord_id:
                    player_data = await fetch_player(user_id)
                    
                    if player_data:
                        player_userid = player_data[0]
                        await link_player(discord_id, player_userid, player_name)
                        
                        try:
                            user = await self.bot.fetch_user(discord_id)
                            embed = discord.Embed(
                                title="Account Linked Successfully!",
                                description="Your Discord account has been linked to your in-game player.",
                                color=discord.Color.green()
                            )
                            embed.add_field(name="Player Name", value=player_name, inline=True)
                            embed.add_field(name="User ID", value=f"`{player_userid}`", inline=True)
                            await user.send(embed=embed)
                        except discord.Forbidden:
                            logging.warning(f"Could not DM user {discord_id} - DMs may be disabled")
                        except Exception as e:
                            logging.error(f"Error sending DM to {discord_id}: {e}")
                        
                        if "link_channel" in cfg:
                            try:
                                channel = self.bot.get_channel(int(cfg["link_channel"]))
                                if channel:
                                    embed = discord.Embed(
                                        title="Player Linked",
                                        description=f"**{player_name}** has linked their account",
                                        color=discord.Color.green()
                                    )
                                    embed.add_field(name="User ID", value=f"`{player_userid}`", inline=True)
                                    embed.add_field(name="Discord", value=f"<@{discord_id}>", inline=True)
                                    embed.add_field(name="Server", value=cfg["name"], inline=False)
                                    await channel.send(embed=embed)
                            except Exception as e:
                                logging.error(f"Error sending link notification to channel: {e}")
                    else:
                        logging.warning(f"Player {player_name} not found in database for linking")
                else:
                    logging.info(f"Invalid link code attempted: {code} by {player_name}")
        except Exception as e:
            logging.error(f"[{cfg['name']}] Error processing link command: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        try:
            if message.author.bot or not message.guild or not message.content:
                return
            for cfg in self.config:
                if "channel" in cfg and str(message.channel.id) == str(cfg["channel"]) and "name" in cfg:
                    details = await fetch_server_details(message.guild.id, cfg["name"])
                    if details:
                        host = details[2]
                        password = details[3]
                        api_port = details[4]
                        api = PalworldAPI(f"http://{host}:{api_port}", password)
                        await api.make_announcement(f"[{message.author.name}]: {message.content}")
        except Exception as e:
            logging.error(f"Error in on_message: {e}", exc_info=True)

async def setup(bot):
    if not os.path.exists(CONFIG_FILE):
        logging.warning("sftp.yml not found, SFTP Chat cog not loaded.")
        return
    await bot.add_cog(SFTPChatCog(bot))