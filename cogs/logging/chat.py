import discord
from discord.ext import commands, tasks
from discord import app_commands
import aiohttp
import re
import logging
import os
import asyncio
from utils.database import (
    get_chat,
    set_chat,
    delete_chat,
    fetch_server_details,
    server_autocomplete
)
from palworld_api import PalworldAPI
from utils.servermodal import ChatSetupModal

class ChatCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.current_log_file = {}
        self.last_processed_line = {}
        self.first_check_done = {}
        self.blocked_phrases = ["/adminpassword", "/creativemenu", "/"]
        self.check_logs.start()

    def cog_unload(self):
        self.check_logs.cancel()

    @tasks.loop(seconds=8)
    async def check_logs(self):
        for guild in self.bot.guilds:
            config = await get_chat(guild.id)
            if not config:
                continue

            server_name, chat_channel_id, log_path, webhook_url = config

            try:
                files = sorted(
                    [f for f in os.listdir(log_path) if f.endswith(".txt") or f.endswith(".log")],
                    key=lambda x: os.stat(os.path.join(log_path, x)).st_mtime,
                    reverse=True
                )
                if not files:
                    continue

                newest_file = os.path.join(log_path, files[0])
                if self.current_log_file.get(guild.id) != newest_file:
                    self.current_log_file[guild.id] = newest_file
                    self.last_processed_line[guild.id] = None
                    self.first_check_done[guild.id] = False

                with open(newest_file, "r", encoding="utf-8", errors="ignore") as file:
                    content = file.read()
                    lines = content.splitlines()

                if not self.first_check_done.get(guild.id, False):
                    if lines:
                        self.last_processed_line[guild.id] = lines[-1]
                    self.first_check_done[guild.id] = True
                    continue

                new_lines_start = False
                for line in lines:
                    if line == self.last_processed_line.get(guild.id):
                        new_lines_start = True
                        continue
                    if new_lines_start or self.last_processed_line.get(guild.id) is None:
                        if "[Chat::" in line:
                            await self.process_and_send(line, webhook_url, server_name)

                if lines:
                    self.last_processed_line[guild.id] = lines[-1]
            except Exception as e:
                logging.error(f"Log check failed for guild {guild.id}: {e}")

    async def process_and_send(self, line, webhook_url, server_name):
        try:
            match = re.search(r"\[Chat::(?:Global|Local|Guild)\]\['([^']+)'.*\]: (.*)", line)
            if match:
                username, message = match.groups()
                if any(bp in message for bp in self.blocked_phrases):
                    return
                async with aiohttp.ClientSession() as session:
                    await session.post(webhook_url, json={"username": f"{username} ({server_name})", "content": message})
                    await asyncio.sleep(1)
        except:
            pass

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild or not message.content:
            return

        config = await get_chat(message.guild.id)
        if not config:
            return

        server_name, chat_channel_id, log_path, webhook_url = config
        if str(message.channel.id) != str(chat_channel_id):
            return

        details = await fetch_server_details(message.guild.id, server_name)
        if not details:
            return

        host = details[2]
        password = details[3]
        api_port = details[4]
        api = PalworldAPI(f"http://{host}:{api_port}", "admin", password)
        await api.make_announcement(f"[{message.author.name}]: {message.content}")

    async def server_names(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id
        server_names = await server_autocomplete(guild_id, current)
        return [app_commands.Choice(name=name, value=name) for name in server_names]

    @app_commands.command(name="setupchat", description="Configure chat feed and relay")
    @app_commands.describe(server="Select the server name")
    @app_commands.autocomplete(server=server_names)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def setupchat(self, interaction: discord.Interaction, server: str):
        modal = ChatSetupModal(title="Setup Chat Feed/Relay")

        async def on_submit_override(modal_interaction: discord.Interaction):
            await modal_interaction.response.defer(ephemeral=True)

            chat_channel_id = int(modal.children[0].value)
            log_path = modal.children[1].value
            webhook_url = modal.children[2].value

            try:
                await set_chat(
                    interaction.guild_id,
                    server,
                    chat_channel_id,
                    log_path,
                    webhook_url
                )
                await modal_interaction.followup.send("Chat feed and relay configured successfully.", ephemeral=True)
            except Exception as e:
                await modal_interaction.followup.send(f"Failed to save chat config: {e}", ephemeral=True)
                logging.error(f"Failed to save chat config: {e}")

        modal.on_submit = on_submit_override
        await interaction.response.send_modal(modal)

    @app_commands.command(name="removechat", description="Remove chat config for a server")
    @app_commands.describe(server="Select the server name to remove")
    @app_commands.autocomplete(server=server_names)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def removechat(self, interaction: discord.Interaction, server: str):
        try:
            await delete_chat(interaction.guild.id, server)
            await interaction.response.send_message("Chat config removed.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"Failed to remove chat config: {e}", ephemeral=True)
            logging.error(f"Failed to remove chat config: {e}")

    @check_logs.before_loop
    async def before_check_logs(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(ChatCog(bot))
