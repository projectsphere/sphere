import discord
from discord.ext import commands, tasks
import aiohttp
import re
from paramiko import SSHClient, AutoAddPolicy
import logging
import os
import asyncio
from utils.database import fetch_server_details
from palworld_api import PalworldAPI

# Cog for SFTP based chat feed.
sftp_host = os.getenv("SFTP_HOST", "")
sftp_username = os.getenv("SFTP_USERNAME", "")
sftp_password = os.getenv("SFTP_PASSWORD", "")
sftp_port = int(os.getenv("SFTP_PORT", 2022))
sftp_path = os.getenv("SFTP_PATH", "Pal/Binaries/Win64/PalDefender/Logs")
sftp_webhook = os.getenv("SFTP_WEBHOOK", "")
sftp_channel = os.getenv("SFTP_CHANNEL", "")
sftp_servername = os.getenv("SFTP_SERVERNAME", "")

class ChatLogCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sftp_host = sftp_host
        self.sftp_username = sftp_username
        self.sftp_password = sftp_password
        self.sftp_port = sftp_port
        self.log_directory = sftp_path
        self.webhook_url = sftp_webhook
        self.first_check_done = False
        self.last_processed_line = None
        self.session = aiohttp.ClientSession()
        self.check_logs.start()
        self.blocked_phrases = ["/adminpassword", "/creativemenu", "/"]

    def cog_unload(self):
        self.check_logs.cancel()
        self.bot.loop.create_task(self.session.close())

    def connect_sftp(self):
        try:
            ssh = SSHClient()
            ssh.set_missing_host_key_policy(AutoAddPolicy())
            ssh.connect(
                hostname=self.sftp_host,
                username=self.sftp_username,
                password=self.sftp_password,
                port=self.sftp_port
            )
            sftp = ssh.open_sftp()
            return sftp, ssh
        except Exception as e:
            logging.error(f"Failed to connect to SFTP: {e}")
            return None, None

    @tasks.loop(seconds=15)
    async def check_logs(self):
        sftp, ssh = self.connect_sftp()
        if sftp is None or ssh is None:
            logging.info("SFTP connection could not be established.")
            return

        try:
            sftp.chdir(self.log_directory)
            files = sorted(sftp.listdir(), key=lambda x: sftp.stat(x).st_mtime, reverse=True)
            log_file_path = next((f for f in files if f.endswith('.log')), None)

            if log_file_path is None:
                logging.error("No log files found in the directory.")
                return

            with sftp.file(log_file_path, 'r') as file:
                content = file.read().decode('utf-8')
                lines = content.splitlines()

            if not self.first_check_done:
                self.last_processed_line = lines[-1] if lines else None
                self.first_check_done = True
                logging.info(f"Initial setup completed. Monitoring new lines from {log_file_path}.")
                return

            new_lines_start = False
            for line in lines:
                if line == self.last_processed_line:
                    new_lines_start = True
                    continue
                if new_lines_start or self.last_processed_line is None:
                    if "[Chat::" in line:
                        await self.process_and_send(line)
                        await asyncio.sleep(1)

            if lines:
                self.last_processed_line = lines[-1]
        except Exception as e:
            logging.error(f"Error during log check: {e}")
        finally:
            sftp.close()
            ssh.close()

    async def process_and_send(self, line):
        try:
            match = re.search(r"\[Chat::(?:Global|Local|Guild)\]\['([^']+)'.*\]: (.*)", line)
            if match:
                username, message = match.groups()
                if any(blocked_phrase in message for blocked_phrase in self.blocked_phrases):
                    logging.info(f"Blocked message from {username} containing a blocked phrase.")
                    return
                payload = {"username": username, "content": message}
                async with self.session.post(self.webhook_url, json=payload) as response:
                    if response.status != 200:
                        logging.info(f"Error sending message to webhook: {response.status} - {await response.text()}")
        except Exception as e:
            logging.error(f"Error processing and sending log line: {e}")

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.content:
            return
        if sftp_channel and message.channel.id == int(sftp_channel) and sftp_servername:
            details = await fetch_server_details(message.guild.id, sftp_servername)
            if details:
                host = details[2]
                password = details[3]
                api_port = details[4]
                api = PalworldAPI(f"http://{host}:{api_port}", password)
                await api.make_announcement(f"[{message.author.name}]: {message.content}")

    @check_logs.before_loop
    async def before_check_logs(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(ChatLogCog(bot))
