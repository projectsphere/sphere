import discord
from discord.ext import commands
import os
import logging
from palworld_api import PalworldAPI
from utils.database import fetch_server_details
import utils.settings as s

sftp_channel_id = s.chatlog_channel
server_name = s.chatlog_server

class ChatRelayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sftp_channel_id = sftp_channel_id
        self.server_name = server_name

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if str(message.channel.id) != str(self.sftp_channel_id):
            return
        if not message.content:
            return
        details = await fetch_server_details(message.guild.id, self.server_name)
        if not details:
            return
        host = details[2]
        password = details[3]
        api_port = details[4]
        server_url = f"http://{host}:{api_port}"
        broadcast_message = f"[{message.author.name}]: {message.content}"
        api = PalworldAPI(server_url, "admin", password)
        await api.make_announcement(broadcast_message)

async def setup(bot):
    if not sftp_channel_id:
        logging.error("CHATLOG_CHANNEL not set.")
        return
    if not server_name:
        logging.error("CHATLOG_SERVER not set.")
        return
    await bot.add_cog(ChatRelayCog(bot))
