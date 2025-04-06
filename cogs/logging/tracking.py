import discord
from discord.ext import commands, tasks
from discord import app_commands
from utils.database import fetch_all_servers, get_tracking, set_tracking
from palworld_api import PalworldAPI
import logging

class PlayerTrackerCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.player_tracking.start()

    def cog_unload(self):
        self.player_tracking.cancel()

    @tasks.loop(minutes=2)
    async def player_tracking(self):
        try:
            guilds = await get_tracking()
            if not guilds:
                return

            servers = await fetch_all_servers()
            total_players = 0

            for server in servers:
                try:
                    guild_id, _, host, password, api_port, _ = server
                    if guild_id not in guilds:
                        continue
                    api = PalworldAPI(f"http://{host}:{api_port}", "admin", password)
                    metrics = await api.get_server_metrics()
                    total_players += metrics.get('currentplayernum', 0)
                except Exception as e:
                    logging.error(f"Error fetching metrics from {server[1]}: {e}")
                    continue

            try:
                activity = discord.Activity(type=discord.ActivityType.watching, name=f"{total_players} Players")
                await self.bot.change_presence(activity=activity)
                logging.info(f"Updated presence to: Watching {total_players} Players")
            except Exception as e:
                logging.error(f"Error updating bot presence: {e}")

        except Exception as e:
            logging.error(f"Error in player_tracking loop: {e}")

    async def bool_autocomplete(self, interaction: discord.Interaction, current: str):
        return [
            app_commands.Choice(name="True", value="true"),
            app_commands.Choice(name="False", value="false")
        ]

    @app_commands.command(name="trackplayers", description="Enable or disable status-based player tracking.")
    @app_commands.describe(status="Enable or disable tracking")
    @app_commands.autocomplete(status=bool_autocomplete)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def trackplayers(self, interaction: discord.Interaction, status: str):
        try:
            enabled = status.lower() == "true"
            await set_tracking(interaction.guild.id, enabled)
            await interaction.response.send_message(f"Player tracking set to `{enabled}` for this server.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message("Failed to update tracking status.", ephemeral=True)
            logging.error(f"Failed to set tracking: {e}")

    @player_tracking.before_loop
    async def before_loop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(PlayerTrackerCog(bot))
