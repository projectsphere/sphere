import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import logging
import os
from utils.pagination import Pagination, PaginationView

class GlobalBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_url = os.getenv("API_URL")
        self.bearer_token = os.getenv("API_KEY")

    async def api_request(self, method: str, endpoint: str, json: dict = None, params: dict = None):
        url = f"{self.api_url}{endpoint}"
        headers = {"Authorization": f"Bearer {self.bearer_token}"}
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, headers=headers, json=json, params=params) as response:
                if response.status == 200:
                    return await response.json()
                raise Exception(f"API request failed: {response.status}, {await response.text()}")

    api_group = app_commands.Group(
        name="api",
        description="API related commands.",
        default_permissions=discord.Permissions(administrator=True),
        guild_only=True
    )

    @api_group.command(name="ban", description="Ban a user.")
    @app_commands.describe(name="The username to ban", user_id="The user ID to ban", reason="Reason for banning")
    async def ban_user(self, interaction: discord.Interaction, name: str, user_id: str, reason: str):
        await interaction.response.defer(ephemeral=True)
        try:
            payload = {"name": name, "id": user_id, "reason": reason}
            await self.api_request("POST", "/api/banuser", json=payload)
            await interaction.followup.send(f"User `{name}` (ID: {user_id}) has been banned for: {reason}", ephemeral=True)
        except Exception as e:
            logging.error(f"Failed to ban user: {e}")
            await interaction.followup.send(f"An error occurred while banning the user: {str(e)}", ephemeral=True)

    @api_group.command(name="unban", description="Unban a user.")
    @app_commands.describe(user_id="The user ID to unban")
    async def unban_user(self, interaction: discord.Interaction, user_id: str):
        await interaction.response.defer(ephemeral=True)
        try:
            await self.api_request("POST", "/api/unbanuser", params={"steamid": user_id})
            await interaction.followup.send(f"User with ID `{user_id}` has been unbanned successfully.", ephemeral=True)
        except Exception as e:
            logging.error(f"Failed to unban user: {e}")
            await interaction.followup.send(f"An error occurred while unbanning the user: {str(e)}", ephemeral=True)

    @api_group.command(name="banlist", description="Get detailed banned users list.")
    @app_commands.describe(name="Filter the banlist by name")
    async def banned_users(self, interaction: discord.Interaction, name: str = None):
        await interaction.response.defer(ephemeral=True)
        try:
            params = {"name": name} if name else None
            bans = await self.api_request("GET", "/api/bannedusers", params=params)
            if not bans:
                await interaction.followup.send("No users are currently banned.", ephemeral=True)
                return

            def create_embed(ban_page, current_page, total_pages):
                embed = discord.Embed(
                    title="Banned Users",
                    color=discord.Color.red()
                )
                for ban in ban_page:
                    embed.add_field(
                        name=f"**Name:** {ban['name']}",
                        value=(
                            f"**ID:** `{ban['id']}`\n"
                            f"**Reason:** {ban['reason']}"
                        ),
                        inline=False
                    )
                embed.set_footer(text=f"Page {current_page} of {total_pages}")
                return embed

            paginator = Pagination(bans, page_size=5)
            embed = create_embed(paginator.get_page(1), 1, paginator.total_pages)
            view = PaginationView(paginator, 1, create_embed)

            await interaction.followup.send(embed=embed, view=view, ephemeral=True)
        except Exception as e:
            logging.error(f"Failed to fetch banned users: {e}")
            await interaction.followup.send(f"An error occurred while fetching banned users: {str(e)}", ephemeral=True)

async def setup(bot):
    api_url = os.getenv("API_URL")
    api_key = os.getenv("API_KEY")

    if not api_url or not api_key:
        logging.error("GlobalBan not loaded due to missing api key and url.")
        return

    await bot.add_cog(GlobalBan(bot))
