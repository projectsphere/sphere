import discord
from discord.ext import commands
from discord import app_commands
from utils.database import server_autocomplete, fetch_server_details
from palworld_api import PalworldAPI

class RestAPICog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def server_autocomplete(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id
        server_names = await server_autocomplete(guild_id, current)
        choices = [app_commands.Choice(name=name, value=name) for name in server_names]
        return choices

    @app_commands.command(name="serverinfo", description="Get server info from the API.")
    @app_commands.describe(server="The name of the server to get info for.")
    @app_commands.default_permissions(administrator=True)
    @app_commands.autocomplete(server=server_autocomplete)
    async def server_info(self, interaction: discord.Interaction, server: str):
        try:
            guild_id = interaction.guild.id
            server_config = await fetch_server_details(guild_id, server)
            if not server_config:
                await interaction.response.send_message(f"Server '{server}' configuration not found.", ephemeral=True)
                return
            
            await interaction.response.defer()
            
            host = server_config[2]
            api_port = server_config[5]
            password = server_config[4]
            
            api = PalworldAPI(f"http://{host}:{api_port}", "admin", password)
            server_info = await api.get_server_info()
            server_metrics = await api.get_server_metrics()
            
            embed = discord.Embed(title=f"{server_info.get('servername', {server})}", description=f"{server_info.get('description', 'N/A')}", color=discord.Color.blurple())
            embed.add_field(name="Players", value=f"{server_metrics.get('currentplayernum', 'N/A')}/{server_metrics.get('maxplayernum', 'N/A')}", inline=False)
            embed.add_field(name="Version", value=server_info.get('version', 'N/A'), inline=False)
            
            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(RestAPICog(bot))