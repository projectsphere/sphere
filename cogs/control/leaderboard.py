import discord
from discord.ext import commands
from discord import app_commands
from utils.database import fetch_playtime_leaderboard, server_autocomplete

class LeaderboardCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def format_duration(self, seconds: int) -> str:
        """
        Converts an integer number of seconds to a human-readable string,
        e.g., "1h 2m 3s" or "13m 19s".
        """
        hours = seconds // 3600
        remainder = seconds % 3600
        minutes = remainder // 60
        secs = remainder % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 or hours > 0:
            parts.append(f"{minutes}m")
        parts.append(f"{secs}s")
        return " ".join(parts)

    async def server_names(self, interaction: discord.Interaction, current: str):
        """Autocomplete helper for server names based on user input."""
        guild_id = interaction.guild.id
        names = await server_autocomplete(guild_id, current)
        return [app_commands.Choice(name=name, value=name) for name in names]

    @app_commands.command(name="leaderboard", description="Show the playtime leaderboard for a specific server")
    @app_commands.autocomplete(server=server_names)
    async def leaderboard(self, interaction: discord.Interaction, server: str):
        leaderboard_data = await fetch_playtime_leaderboard(server, limit=10)
        if not leaderboard_data:
            await interaction.response.send_message(f"No playtime data available yet for server '{server}'.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"Playtime Leaderboard for {server}",
            color=discord.Color.blue()
        )

        for idx, (user_id, total_seconds, name) in enumerate(leaderboard_data, start=1):
            display_name = name if name else user_id
            duration_str = self.format_duration(total_seconds)
            embed.add_field(
                name=f"{idx}. {display_name}",
                value=duration_str,
                inline=False
            )

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(LeaderboardCog(bot))
