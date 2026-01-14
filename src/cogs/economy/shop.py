import discord
from discord.ext import commands
from discord import app_commands
import yaml
import os
import asyncio
from src.utils.economy import get_gold, remove_gold
from src.utils.database import get_linked_player, fetch_server_details, server_autocomplete
from utils.rconutility import RconUtility
from palworld_api import PalworldAPI

CONFIG_FILE = os.path.join("config", "shop.yml")
SFTP_CONFIG = os.path.join("config", "sftp.yml")

def load_shop_config():
    if not os.path.exists(CONFIG_FILE):
        return []
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        return config.get("shop", [])

def load_economy_config():
    if not os.path.exists(SFTP_CONFIG):
        return {"currency_name": "gold"}
    with open(SFTP_CONFIG, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
        return config.get("economy", {"currency_name": "gold"})

class ShopCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rcon = RconUtility()
        self.shop_items = load_shop_config()
        self.economy_config = load_economy_config()

    async def get_server_info(self, guild_id: int, server_name: str):
        details = await fetch_server_details(guild_id, server_name)
        if details:
            return {"host": details[2], "password": details[3], "api_port": details[4], "rcon_port": details[5]}

    async def autocomplete_server(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id if interaction.guild else 0
        results = await server_autocomplete(guild_id, current)
        return [app_commands.Choice(name=x, value=x) for x in results[:25]]

    async def autocomplete_shop_item(self, interaction: discord.Interaction, current: str):
        results = []
        for item in self.shop_items:
            name = item.get("name", "")
            if current.lower() in name.lower():
                results.append(app_commands.Choice(name=name, value=name))
        return results[:25]

    @app_commands.command(name="shop", description="View available shop items.")
    @app_commands.describe(server="Server to view shop for (optional)")
    @app_commands.autocomplete(server=autocomplete_server)
    @app_commands.guild_only()
    async def shop(self, interaction: discord.Interaction, server: str = None):
        await interaction.response.defer(ephemeral=True)
        
        if not self.shop_items:
            await interaction.followup.send("The shop is currently empty.", ephemeral=True)
            return
        
        filtered_items = []
        for item in self.shop_items:
            item_server = item.get("server")
            if server is None:
                if item_server is None:
                    filtered_items.append(item)
            else:
                if item_server is None or item_server == server:
                    filtered_items.append(item)
        
        if not filtered_items:
            await interaction.followup.send(f"No items available for server '{server}'.", ephemeral=True)
            return
        
        currency = self.economy_config.get("currency_name", "gold")
        
        title = "🛒 Shop" if not server else f"🛒 Shop - {server}"
        embed = discord.Embed(
            title=title,
            description=f"Use `/buy <item_name> <server>` to purchase items",
            color=discord.Color.blue()
        )
        
        for item in filtered_items:
            name = item.get("name", "Unknown")
            description = item.get("description", "No description")
            price = item.get("price", 0)
            items_list = item.get("items", [])
            item_server = item.get("server")
            
            items_preview = ", ".join(items_list[:3])
            if len(items_list) > 3:
                items_preview += f" (+{len(items_list) - 3} more)"
            
            server_tag = "" if item_server is None else f" [{item_server} only]"
            
            embed.add_field(
                name=f"{name} - {price} {currency}{server_tag}",
                value=f"{description}\n*Items: {items_preview}*",
                inline=False
            )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="buy", description="Purchase an item from the shop.")
    @app_commands.describe(item_name="The item to purchase", server="Server to deliver items to")
    @app_commands.autocomplete(item_name=autocomplete_shop_item, server=autocomplete_server)
    @app_commands.guild_only()
    async def buy(self, interaction: discord.Interaction, item_name: str, server: str):
        await interaction.response.defer(ephemeral=True)
        
        if not interaction.guild:
            await interaction.followup.send("This command can only be used in a guild.", ephemeral=True)
            return
        
        linked = await get_linked_player(interaction.user.id)
        if not linked:
            await interaction.followup.send(
                "You must link your account first using `/link`.",
                ephemeral=True
            )
            return
        
        player_userid, player_name = linked
        
        shop_item = next((item for item in self.shop_items if item.get("name", "").lower() == item_name.lower()), None)
        if not shop_item:
            await interaction.followup.send(f"Item '{item_name}' not found in shop.", ephemeral=True)
            return
        
        item_server = shop_item.get("server")
        if item_server is not None and item_server != server:
            await interaction.followup.send(
                f"'{item_name}' is only available on server '{item_server}'.",
                ephemeral=True
            )
            return
        
        price = shop_item.get("price", 0)
        currency = self.economy_config.get("currency_name", "gold")
        
        current_gold = await get_gold(interaction.user.id, interaction.guild.id)
        if current_gold < price:
            await interaction.followup.send(
                f"You don't have enough {currency}. You need {price} {currency} but only have {current_gold} {currency}.",
                ephemeral=True
            )
            return
        
        server_info = await self.get_server_info(interaction.guild.id, server)
        if not server_info:
            await interaction.followup.send(f"Server '{server}' not found.", ephemeral=True)
            return
        
        api = PalworldAPI(f"http://{server_info['host']}:{server_info['api_port']}", server_info['password'])
        
        try:
            players_data = await api.get_player_list()
            online_player = next((p for p in players_data.get("players", []) if p.get("userId") == player_userid), None)
            
            if not online_player:
                await interaction.followup.send(
                    f"You must be online on '{server}' to purchase items.",
                    ephemeral=True
                )
                return
        except Exception as e:
            await interaction.followup.send(
                f"Failed to verify online status: {str(e)}",
                ephemeral=True
            )
            return
        
        success, new_balance = await remove_gold(interaction.user.id, interaction.guild.id, price)
        if not success:
            await interaction.followup.send(
                f"Failed to deduct {currency}. You may not have enough.",
                ephemeral=True
            )
            return
        
        items_to_give = shop_item.get("items", [])
        
        for item_str in items_to_give:
            cmd = f"giveitems {player_userid} {item_str}"
            try:
                await self.rcon.rcon_command(
                    server_info["host"],
                    server_info["rcon_port"],
                    server_info["password"],
                    cmd
                )
                await asyncio.sleep(0.5)
            except Exception as e:
                await interaction.followup.send(
                    f"Error giving items: {str(e)}\nYour {currency} has been refunded.",
                    ephemeral=True
                )
                await remove_gold(interaction.user.id, interaction.guild.id, -price)
                return
        
        embed = discord.Embed(
            title="Purchase Successful",
            description=f"You purchased **{shop_item.get('name')}**!",
            color=discord.Color.green()
        )
        embed.add_field(name="Price", value=f"{price} {currency}", inline=True)
        embed.add_field(name="New Balance", value=f"{new_balance} {currency}", inline=True)
        embed.add_field(name="Server", value=server, inline=True)
        embed.add_field(
            name="Items Received",
            value="\n".join([f"• {item}" for item in items_to_give]),
            inline=False
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ShopCog(bot))
