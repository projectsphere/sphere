import discord
from discord.ext import commands
from discord import app_commands
from utils.database import fetch_server_details, server_autocomplete
from palworld_api import PalworldAPI
import logging

class PlayersCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_api_instance(self, guild_id, server_name):
        server_config = await fetch_server_details(guild_id, server_name)
        if not server_config:
            return None, f"Server '{server_name}' configuration not found."
        
        host = server_config[2]
        password = server_config[3]
        api_port = server_config[4]
        
        api = PalworldAPI(f"http://{host}:{api_port}", password)
        return api, None

    async def server_autocomplete(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id
        server_names = await server_autocomplete(guild_id, current)
        choices = [app_commands.Choice(name=name, value=name) for name in server_names]
        return choices

    @app_commands.command(name="players", description="Get the full player list of a selected server.")
    @app_commands.describe(server="The name of the server to retrieve the player list from")
    @app_commands.autocomplete(server=server_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def player_list(self, interaction: discord.Interaction, server: str):
        await interaction.response.defer(thinking=True, ephemeral=True)
        try:
            api, error = await self.get_api_instance(interaction.guild.id, server)
            if error:
                await interaction.followup.send(error, ephemeral=True)
                return
            
            player_list = await api.get_player_list()
            if player_list and 'players' in player_list:
                embed = self.playerlist_embed(server, player_list['players'])
                await interaction.followup.send(embed=embed, ephemeral=True)
            else:
                await interaction.followup.send(f"No players found on server '{server}'.", ephemeral=True)
                logging.info(f"No players found on server '{server}'.")
        except Exception as e:
            await interaction.followup.send(f"An unexpected error occurred: {str(e)}", ephemeral=True)
            logging.error(f"An unexpected error occurred while fetching player list: {str(e)}")

    def playerlist_embed(self, server_name, players):
        embed = discord.Embed(title=f"Player List for {server_name}", color=discord.Color.green())

        player_names = "\n".join([f"`{player['name']} ({str(player['level'])})`" for player in players])
        player_ids = "\n".join([f"`{player['userId']}`" for player in players])
        player_location = "\n".join([f"`{player['location_x']}`,`{player['location_y']}`" for player in players])

        embed.add_field(name="Name", value=player_names if player_names else "No players online", inline=True)
        embed.add_field(name="PlayerID", value=player_ids if player_ids else "No players online", inline=True)
        embed.add_field(name="Location", value=player_location if player_location else "No players online", inline=True)

        return embed

async def setup(bot):
    await bot.add_cog(PlayersCog(bot))
