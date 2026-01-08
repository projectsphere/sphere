import os
import json
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import aiosqlite
from utils.rconutility import RconUtility
from utils.database import fetch_server_details, server_autocomplete

# This is all temporary till I separate the database stuff into its own utility file.
DATABASE_PATH = os.path.join("data", "palworld.db")

async def db_connection():
    conn = None
    try:
        conn = await aiosqlite.connect(DATABASE_PATH)
    except aiosqlite.Error as e:
        print(e)
    return conn

async def ensure_kits_table():
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("""
            CREATE TABLE IF NOT EXISTS kits (
                kit_name TEXT PRIMARY KEY,
                commands TEXT NOT NULL,
                description TEXT NOT NULL
            )
        """)
        await conn.commit()
        await conn.close()

async def get_kit(kit_name: str):
    conn = await db_connection()
    if conn is None:
        return None
    cursor = await conn.cursor()
    await cursor.execute("SELECT commands, description FROM kits WHERE kit_name = ?", (kit_name,))
    kit = await cursor.fetchone()
    await conn.close()
    return kit

async def save_kit(kit_name: str, commands_data: str, desc: str):
    conn = await db_connection()
    if conn is None:
        return
    cursor = await conn.cursor()
    await cursor.execute("""
        INSERT INTO kits (kit_name, commands, description)
        VALUES (?, ?, ?)
        ON CONFLICT(kit_name) DO UPDATE
        SET commands=excluded.commands,
            description=excluded.description
    """,(kit_name, commands_data, desc))
    await conn.commit()
    await conn.close()

async def delete_kit(kit_name: str):
    conn = await db_connection()
    if conn is None:
        return
    cursor = await conn.cursor()
    await cursor.execute("DELETE FROM kits WHERE kit_name = ?", (kit_name,))
    await conn.commit()
    await conn.close()

async def autocomplete_kits(interaction: discord.Interaction, current: str):
    conn = await db_connection()
    if conn is None:
        return []
    cursor = await conn.cursor()
    await cursor.execute("SELECT kit_name FROM kits WHERE kit_name LIKE ?", (f"%{current}%",))
    rows = await cursor.fetchall()
    await conn.close()
    return [app_commands.Choice(name=r[0], value=r[0]) for r in rows]

class KitModal(discord.ui.Modal):
    def __init__(self, title, default_name="", default_commands="[]", default_desc=""):
        super().__init__(title=title)
        self.kit_name = discord.ui.TextInput(label="Kit Name", default=default_name)
        self.commands = discord.ui.TextInput(label="Commands (JSON)", style=discord.TextStyle.paragraph, default=default_commands)
        self.description = discord.ui.TextInput(label="Description", default=default_desc)
        self.add_item(self.kit_name)
        self.add_item(self.commands)
        self.add_item(self.description)

    async def on_submit(self, interaction: discord.Interaction):
        kit_name = self.kit_name.value.strip()
        commands_data = self.commands.value.strip()
        desc = self.description.value.strip()
        if not kit_name:
            await interaction.response.send_message("Kit name is required.", ephemeral=True)
            return
        try:
            json.loads(commands_data)
        except:
            await interaction.response.send_message("Commands must be valid JSON.", ephemeral=True)
            return
        await save_kit(kit_name, commands_data, desc)
        await interaction.response.send_message(f"Kit '{kit_name}' has been saved.", ephemeral=True)

class KitsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.rcon = RconUtility()
        self.servers = []
        bot.loop.create_task(ensure_kits_table())
        bot.loop.create_task(self.load_servers())

    async def load_servers(self):
        self.servers = []

    async def get_server_info(self, guild_id: int, server_name: str):
        details = await fetch_server_details(guild_id, server_name)
        if details:
            return {"host": details[2], "password": details[3], "port": details[5]}

    async def autocomplete_server(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id if interaction.guild else 0
        results = await server_autocomplete(guild_id, current)
        return [app_commands.Choice(name=x, value=x) for x in results[:25]]

    @app_commands.command(name="givekit", description="Give a kit to a user")
    @app_commands.describe(userid="User ID", kit_name="Kit Name", server="Server Name")
    @app_commands.autocomplete(server=autocomplete_server, kit_name=autocomplete_kits)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def givekit(self, interaction: discord.Interaction, userid: str, kit_name: str, server: str):
        await interaction.response.defer(ephemeral=True)
        if not interaction.guild:
            await interaction.followup.send("No guild.", ephemeral=True)
            return
        server_info = await self.get_server_info(interaction.guild.id, server)
        if not server_info:
            await interaction.followup.send(f"Server not found: {server}", ephemeral=True)
            return
        kit = await get_kit(kit_name)
        if not kit:
            await interaction.followup.send(f"Kit not found: {kit_name}", ephemeral=True)
            return
        commands_str, desc = kit
        try:
            commands_list = json.loads(commands_str)
        except:
            await interaction.followup.send("Commands data is not valid JSON.", ephemeral=True)
            return
        for cmd_template in commands_list:
            final_cmd = cmd_template.format(userid=userid)
            await self.rcon.rcon_command(server_info["host"], server_info["port"], server_info["password"], final_cmd)
            await asyncio.sleep(1)
        await interaction.followup.send(f"Kit '{kit_name}' given to {userid} on '{server}'.", ephemeral=True)

    @app_commands.command(name="managekit", description="Create or update a kit.")
    @app_commands.describe(kit_name="Kit name (optional). If it exists, it will be loaded.")
    @app_commands.autocomplete(kit_name=autocomplete_kits)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def manage_kit(self, interaction: discord.Interaction, kit_name: str = ""):
        if kit_name:
            existing = await get_kit(kit_name)
            if existing:
                commands_str, desc = existing
                modal = KitModal("Manage Kit", default_name=kit_name, default_commands=commands_str, default_desc=desc)
            else:
                modal = KitModal("Manage Kit")
        else:
            modal = KitModal("Manage Kit")
        await interaction.response.send_modal(modal)

    @app_commands.command(name="deletekit", description="Remove a kit from the database.")
    @app_commands.describe(kit_name="Kit name to remove")
    @app_commands.autocomplete(kit_name=autocomplete_kits)
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def deletekit(self, interaction: discord.Interaction, kit_name: str):
        await interaction.response.defer(ephemeral=True)
        await delete_kit(kit_name)
        await interaction.followup.send(f"Kit '{kit_name}' has been deleted.", ephemeral=True)

    @app_commands.command(name="importkits", description="Import multiple kits from a JSON file.")
    @app_commands.describe(file="JSON file containing kits to import")
    @app_commands.default_permissions(administrator=True)
    @app_commands.guild_only()
    async def importkits(self, interaction: discord.Interaction, file: discord.Attachment):
        await interaction.response.defer(ephemeral=True)
        
        if not file.filename.endswith('.json'):
            await interaction.followup.send("Please upload a JSON file.", ephemeral=True)
            return
        
        try:
            content = await file.read()
            kits_data = json.loads(content.decode('utf-8'))
            
            if not isinstance(kits_data, list):
                await interaction.followup.send("JSON must be an array of kit objects.", ephemeral=True)
                return
            
            imported = 0
            errors = []
            
            for kit in kits_data:
                if not isinstance(kit, dict):
                    errors.append(f"Skipped invalid kit entry (not an object)")
                    continue
                
                kit_name = kit.get('kit_name', '').strip()
                commands = kit.get('commands')
                description = kit.get('description', '').strip()
                
                if not kit_name:
                    errors.append(f"Skipped kit with missing name")
                    continue
                
                if not commands:
                    errors.append(f"Skipped '{kit_name}': missing commands")
                    continue
                
                try:
                    if isinstance(commands, list):
                        commands_str = json.dumps(commands)
                    elif isinstance(commands, str):
                        json.loads(commands)
                        commands_str = commands
                    else:
                        errors.append(f"Skipped '{kit_name}': invalid commands format")
                        continue
                    
                    await save_kit(kit_name, commands_str, description)
                    imported += 1
                    
                except json.JSONDecodeError:
                    errors.append(f"Skipped '{kit_name}': commands not valid JSON")
                except Exception as e:
                    errors.append(f"Skipped '{kit_name}': {str(e)}")
            
            response = f"Successfully imported {imported} kit(s)."
            if errors:
                response += f"\n\nErrors:\n" + "\n".join(errors[:10])
                if len(errors) > 10:
                    response += f"\n... and {len(errors) - 10} more errors"
            
            await interaction.followup.send(response, ephemeral=True)
            
        except json.JSONDecodeError:
            await interaction.followup.send("Invalid JSON file.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"Error importing kits: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(KitsCog(bot))
