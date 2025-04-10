from discord.ext import commands
from discord import app_commands
import discord
import sys
import utils.constants as c
from utils.pagination import Pagination, PaginationView

class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_commands_list(self, app_commands, prefix=''):
        lines = []
        for cmd in app_commands:
            if isinstance(cmd, discord.app_commands.Command):
                lines.append(f"`/{cmd.name}` - {cmd.description}")
            elif isinstance(cmd, discord.app_commands.Group):
                lines.append(f"`/{cmd.name}` - {cmd.description}")
                lines.extend(self.get_commands_list(list(cmd.walk_commands()), f"{prefix}{cmd.name} "))
        return lines

    @app_commands.command(name="help", description="Shows help information for all commands.")
    async def help(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        commands = list(self.bot.tree.walk_commands())
        commands_list = self.get_commands_list(commands)
        paginator = Pagination(commands_list, page_size=10)
        page = 1
        embed = self.help_embed(paginator.get_page(page), page, paginator.total_pages)
        view = PaginationView(paginator, page, self.help_embed)
        await interaction.followup.send(embed=embed, view=view)

    def help_embed(self, commands_list, page, total_pages):
        description = "\n".join(commands_list)
        embed = discord.Embed(title=f"Help Menu", description=description, color=discord.Color.blurple())
        return embed

    @app_commands.command(name="about", description="Shows information about the bot.")
    async def about(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        bot_owner = await self.bot.application_info()

        embed = discord.Embed(
            title=c.SPHERE_NAME,
            description="This bot was created for managing palworld servers. Keep up to date on the latest changes and updates on the [GitHub](https://github.com/projectsphere/sphere).",
            color=discord.Color.blurple(),
            url="https://github.com/projectsphere/sphere"
        )
        embed.add_field(name="Instance Owner", value=f"{bot_owner.owner.name}", inline=True)
        embed.add_field(name="Version", value=f"v{c.SPHERE_VERSION}", inline=True)
        embed.add_field(name="Python", value=f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}", inline=True)
        embed.set_thumbnail(url=c.SPHERE_THUMBNAIL)
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))
