import discord
from discord.ext import commands
from discord import app_commands
import random
import string
from src.utils.database import create_link_code, get_link_code, get_linked_player, fetch_player

def generate_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

class LinkCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="link", description="Generate a code to link your discord to your in-game account.")
    async def link(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        existing_link = await get_linked_player(interaction.user.id)
        if existing_link:
            player_userid, player_name = existing_link
            await interaction.followup.send(
                f"You are already linked to player: **{player_name}** (UserID: `{player_userid}`)\n"
                f"If you need to re-link, please contact an admin.",
                ephemeral=True
            )
            return
        
        code = generate_code()
        await create_link_code(interaction.user.id, code)
        
        embed = discord.Embed(
            title="Link Code Generated",
            description=f"Your verification code is: `{code}`",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="How to Link",
            value="1. Join the game server\n2. Type in chat: `/link {code}` or `!link {code}`\n3. You will receive a DM confirmation when linked",
            inline=False
        )
        embed.set_footer(text="This code will remain valid until you successfully link or generate a new code.")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="profile", description="View your linked player profile information.")
    async def profile(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        linked = await get_linked_player(interaction.user.id)
        if not linked:
            await interaction.followup.send(
                "You are not linked to any player. Use `/link` to link your account.",
                ephemeral=True
            )
            return
        
        player_userid, player_name = linked
        player_data = await fetch_player(player_userid)
        
        if not player_data:
            await interaction.followup.send(
                "Player data not found. You may need to join the server first.",
                ephemeral=True
            )
            return
        
        user_id, name, account_name, player_id, ip, ping, location_x, location_y, level = player_data
        
        embed = discord.Embed(
            title=f"{name}'s Profile",
            color=discord.Color.blue()
        )
        embed.add_field(name="In-Game Name", value=name, inline=True)
        embed.add_field(name="Account Name", value=account_name, inline=True)
        embed.add_field(name="Level", value=str(level), inline=True)
        embed.add_field(name="User ID", value=f"||`{user_id}`||", inline=False)
        embed.add_field(name="Player ID", value=f"||`{player_id}`||", inline=False)
        embed.add_field(name="Location", value=f"X: {location_x:.2f}, Z: {location_y:.2f}", inline=True)
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(LinkCog(bot))
