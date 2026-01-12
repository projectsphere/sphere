import discord
from discord.ext import commands
from discord import app_commands
import random
import datetime
import yaml
import os
from src.utils.economy import get_gold, add_gold, get_last_work, update_last_work

CONFIG_FILE = os.path.join("config", "sftp.yml")

def load_economy_config():
    if not os.path.exists(CONFIG_FILE):
        return {"currency_name": "gold", "work_cooldown": 3600, "work_minamount": 10, "work_maxamount": 50}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        return config.get("economy", {"currency_name": "gold", "work_cooldown": 3600, "work_minamount": 10, "work_maxamount": 50})

class WorkCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.config = load_economy_config()

    @app_commands.command(name="work", description="Work to earn gold.")
    @app_commands.guild_only()
    async def work(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        
        guild_id = interaction.guild.id
        discord_id = interaction.user.id
        
        last_work = await get_last_work(discord_id, guild_id)
        
        if last_work:
            last_work_dt = datetime.datetime.fromisoformat(last_work)
            now = datetime.datetime.now()
            time_diff = (now - last_work_dt).total_seconds()
            cooldown = self.config.get("work_cooldown", 3600)
            
            if time_diff < cooldown:
                remaining = int(cooldown - time_diff)
                hours = remaining // 3600
                minutes = (remaining % 3600) // 60
                seconds = remaining % 60
                
                time_str = []
                if hours > 0:
                    time_str.append(f"{hours}h")
                if minutes > 0:
                    time_str.append(f"{minutes}m")
                if seconds > 0:
                    time_str.append(f"{seconds}s")
                
                await interaction.followup.send(
                    f"You need to wait **{' '.join(time_str)}** before working again.",
                    ephemeral=True
                )
                return
        
        min_gold = self.config.get("work_minamount", 10)
        max_gold = self.config.get("work_maxamount", 50)
        earned = random.randint(min_gold, max_gold)
        currency = self.config.get("currency_name", "gold")
        
        new_balance = await add_gold(discord_id, guild_id, earned)
        await update_last_work(discord_id, guild_id, datetime.datetime.now().isoformat())
        
        embed = discord.Embed(
            title="Work Complete",
            description=f"You worked and earned **{earned} {currency}**!",
            color=discord.Color.green()
        )
        embed.add_field(name="New Balance", value=f"{new_balance} {currency}", inline=False)
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(WorkCog(bot))
