import os
import json
import discord
from discord.ext import commands
from discord import app_commands
from utils.rconutility import RconUtility
from utils.database import fetch_server_details, server_autocomplete

class PalDefenderCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rcon = RconUtility()
        self.servers = []
        self.pals = []
        self.items = []
        self.load_pals()
        self.load_items()
        bot.loop.create_task(self.load_servers())

    async def load_servers(self):
        self.servers = []

    def load_pals(self):
        path = os.path.join("gamedata", "pals.json")
        with open(path, "r", encoding="utf-8") as f:
            self.pals = json.load(f).get("pals", [])

    def load_items(self):
        path = os.path.join("gamedata", "items.json")
        with open(path, "r", encoding="utf-8") as f:
            self.items = json.load(f).get("items", [])

    async def get_server_info(self, guild_id: int, server_name: str):
        details = await fetch_server_details(guild_id, server_name)
        if details:
            return {"host": details[2], "password": details[3], "port": details[5]}

    async def autocomplete_server(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id if interaction.guild else 0
        server_names = await server_autocomplete(guild_id, current)
        return [app_commands.Choice(name=name, value=name) for name in server_names[:25]]

    async def autocomplete_pal(self, interaction: discord.Interaction, current: str):
        results = []
        for pal in self.pals:
            name = pal.get("name", "")
            dev_name = pal.get("id", "")
            if current.lower() in name.lower() or current.lower() in dev_name.lower():
                display = f"{name} ({dev_name})"
                results.append(app_commands.Choice(name=display, value=dev_name))
        return results[:15]

    async def autocomplete_item(self, interaction: discord.Interaction, current: str):
        results = []
        for item in self.items:
            name = item.get("name", "")
            item_id = item.get("id", "")
            if current.lower() in name.lower() or current.lower() in item_id.lower():
                display = f"{name} ({item_id})"
                results.append(app_commands.Choice(name=display, value=item_id))
        return results[:15]

    @app_commands.command(name="reloadcfg", description="Reload server config")
    @app_commands.describe(server="Server name")
    @app_commands.autocomplete(server=autocomplete_server)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def reloadcfg(self, interaction: discord.Interaction, server: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("No guild.", ephemeral=True)
            return
        info = await self.get_server_info(interaction.guild.id, server)
        if not info:
            await interaction.followup.send(f"Server not found: {server}", ephemeral=True)
            return
        response = await self.rcon.rcon_command(info["host"], info["port"], info["password"], "reloadcfg")
        await interaction.followup.send(response, ephemeral=True)

    @app_commands.command(name="destroybase", description="Kill nearest base")
    @app_commands.describe(radius="Radius", server="Server")
    @app_commands.autocomplete(server=autocomplete_server)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def killnearestbase(self, interaction: discord.Interaction, radius: str, server: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("No guild.", ephemeral=True)
            return
        info = await self.get_server_info(interaction.guild.id, server)
        if not info:
            await interaction.followup.send(f"Server not found: {server}", ephemeral=True)
            return
        response = await self.rcon.rcon_command(info["host"], info["port"], info["password"], f"killnearestbase {radius}")
        await interaction.followup.send(response, ephemeral=True)

    @app_commands.command(name="getbase", description="Get nearest base")
    @app_commands.describe(radius="Radius", server="Server")
    @app_commands.autocomplete(server=autocomplete_server)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def getnearestbase(self, interaction: discord.Interaction, radius: str, server: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("No guild.", ephemeral=True)
            return
        info = await self.get_server_info(interaction.guild.id, server)
        if not info:
            await interaction.followup.send(f"Server not found: {server}", ephemeral=True)
            return
        response = await self.rcon.rcon_command(info["host"], info["port"], info["password"], f"getnearestbase {radius}")
        await interaction.followup.send(response, ephemeral=True)

    @app_commands.command(name="givepal", description="Give a Pal")
    @app_commands.describe(userid="User ID", palid="Pal name", level="Level", server="Server")
    @app_commands.autocomplete(server=autocomplete_server, palid=autocomplete_pal)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def givepal(self, interaction: discord.Interaction, userid: str, palid: str, level: str, server: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("No guild.", ephemeral=True)
            return
        info = await self.get_server_info(interaction.guild.id, server)
        if not info:
            await interaction.followup.send(f"Server not found: {server}", ephemeral=True)
            return
        pal_data = next((x for x in self.pals if x["id"] == palid or x["name"] == palid), None)
        if not pal_data:
            await interaction.followup.send(f"Pal not found: {palid}", ephemeral=True)
            return
        cmd = f"givepal {userid} {pal_data['dev_name']} {level}"
        response = await self.rcon.rcon_command(info["host"], info["port"], info["password"], cmd)
        embed = discord.Embed(title=f"GivePal on {server}")
        embed.description = response
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="giveitem", description="Give an item")
    @app_commands.describe(userid="User ID", itemid="Item name", amount="Amount", server="Server")
    @app_commands.autocomplete(server=autocomplete_server, itemid=autocomplete_item)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def giveitem(self, interaction: discord.Interaction, userid: str, itemid: str, amount: str, server: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("No guild.", ephemeral=True)
            return
        info = await self.get_server_info(interaction.guild.id, server)
        if not info:
            await interaction.followup.send(f"Server not found: {server}", ephemeral=True)
            return
        item_data = next((x for x in self.items if x["id"] == itemid or x["name"] == itemid), None)
        if not item_data:
            await interaction.followup.send(f"Item not found: {itemid}", ephemeral=True)
            return
        cmd = f"give {userid} {item_data['id']} {amount}"
        response = await self.rcon.rcon_command(info["host"], info["port"], info["password"], cmd)
        embed = discord.Embed(title=f"GiveItem on {server}")
        embed.description = response
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="deleteitem", description="Delete an item")
    @app_commands.describe(userid="User ID", itemid="Item name", amount="Amount.", server="Server")
    @app_commands.autocomplete(server=autocomplete_server, itemid=autocomplete_item)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def deleteitem(self, interaction: discord.Interaction, userid: str, itemid: str, amount: str, server: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("No guild.", ephemeral=True)
            return
        info = await self.get_server_info(interaction.guild.id, server)
        if not info:
            await interaction.followup.send(f"Server not found: {server}", ephemeral=True)
            return
        item_data = next((x for x in self.items if x["id"] == itemid or x["name"] == itemid), None)
        if not item_data:
            await interaction.followup.send(f"Item not found: {itemid}", ephemeral=True)
            return
        cmd = f"delitem {userid} {item_data['id']} {amount}"
        response = await self.rcon.rcon_command(info["host"], info["port"], info["password"], cmd)
        embed = discord.Embed(title=f"DeleteItem on {server}")
        embed.description = response
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="givexp", description="Give experience")
    @app_commands.describe(userid="User ID", amount="Amount", server="Server")
    @app_commands.autocomplete(server=autocomplete_server)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def givexp(self, interaction: discord.Interaction, userid: str, amount: str, server: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("No guild.", ephemeral=True)
            return
        info = await self.get_server_info(interaction.guild.id, server)
        if not info:
            await interaction.followup.send(f"Server not found: {server}", ephemeral=True)
            return
        cmd = f"give_exp {userid} {amount}"
        response = await self.rcon.rcon_command(info["host"], info["port"], info["password"], cmd)
        embed = discord.Embed(title=f"GiveEXP on {server}")
        embed.description = response
        await interaction.followup.send(embed=embed, ephemeral=True)

    # export pals player userid
    @app_commands.command(name="exportpals", description="Export pals")
    @app_commands.describe(userid="User ID", server="Server")
    @app_commands.autocomplete(server=autocomplete_server)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def exportpals(self, interaction: discord.Interaction, userid: str, server: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("No guild.", ephemeral=True)
            return
        info = await self.get_server_info(interaction.guild.id, server)
        if not info:
            await interaction.followup.send(f"Server not found: {server}", ephemeral=True)
            return
        response = await self.rcon.rcon_command(info["host"], info["port"], info["password"], f"exportpals {userid}")
        embed = discord.Embed(title=f"ExportPals on {server}")
        embed.description = response
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="exportguilds", description="Export guilds")
    @app_commands.describe(server="Server")
    @app_commands.autocomplete(server=autocomplete_server)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def exportguilds(self, interaction: discord.Interaction, server: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("No guild.", ephemeral=True)
            return
        info = await self.get_server_info(interaction.guild.id, server)
        if not info:
            await interaction.followup.send(f"Server not found: {server}", ephemeral=True)
            return
        response = await self.rcon.rcon_command(info["host"], info["port"], info["password"], "exportguilds")
        embed = discord.Embed(title=f"ExportGuilds on {server}")
        embed.description = response
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(PalDefenderCog(bot))
