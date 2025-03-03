import discord
from discord.ext import commands
import os
from utils.database import get_server_details
from utils.rconutility import RconUtility
import utils.settings as s
import logging

sftp_channel_id = os.getenv("CHATLOG_CHANNEL")
server_name = os.getenv("CHATLOG_SERVER")

class ChatRelayCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sftp_channel_id = sftp_channel_id
        self.server_name = server_name
        self.rcon_util = RconUtility()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        if message.channel.id != self.sftp_channel_id:
            return

        if not message.content:
            return

        server_details = await get_server_details(self.server_name)
        if not server_details:
            return

        broadcast_message = f"[{message.author.name}]: {message.content}"
        server_info = {
            "name": self.server_name,
            "host": server_details[0],
            "port": server_details[1],
            "password": server_details[2],
        }

        await self.rcon_util.rcon_command(server_info, f"Broadcast {broadcast_message}")

async def setup(bot):
    if not os.getenv("CHATLOG_CHANNEL"):
        logging.error("Chat log channel env variable not set. Chat feed will not be loaded.")
        return
    await bot.add_cog(ChatRelayCog(bot))
