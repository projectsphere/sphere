import discord
from discord.ext import commands
from discord import app_commands
from utils.rconutility import RconUtility
from utils.database import fetch_server_details, server_autocomplete

class RconCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rcon = RconUtility()
        self.servers = []
        bot.loop.create_task(self.load_servers())

    async def load_servers(self):
        self.servers = []

    async def get_server_info(self, guild_id: int, server_name: str):
        details = await fetch_server_details(guild_id, server_name)
        if details:
            return {"host": details[2], "password": details[3], "port": details[5]}

    async def autocomplete_server(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id if interaction.guild else 0
        server_names = await server_autocomplete(guild_id, current)
        return [app_commands.Choice(name=name, value=name) for name in server_names[:25]]

    @app_commands.command(name="rcon", description="Kill nearest base")
    @app_commands.describe(command="RCON Command", server="Server")
    @app_commands.autocomplete(server=autocomplete_server)
    async def rconcommand(self, interaction: discord.Interaction, command: str, server: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("No guild.", ephemeral=True)
            return
        info = await self.get_server_info(interaction.guild.id, server)
        if not info:
            await interaction.followup.send(f"Server not found: {server}", ephemeral=True)
            return
        response = await self.rcon.rcon_command(info["host"], info["port"], info["password"], f"{command}")
        await interaction.followup.send(response, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(RconCog(bot))
