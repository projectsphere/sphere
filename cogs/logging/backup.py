import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import zipfile
import datetime
import logging
from utils.database import (
    set_backup,
    del_backup,
    all_backups,
    server_autocomplete,
    fetch_server_details
)
from utils.servermodal import BackupModal
from palworld_api import PalworldAPI

class BackupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_run = {}
        self.runloop.start()

    def cog_unload(self):
        self.runloop.cancel()

    @tasks.loop(seconds=60)
    async def runloop(self):
        data = await all_backups()
        for row in data:
            gid, name, path, cid, interval = row
            key = f"{gid}-{name}"
            now = datetime.datetime.utcnow().timestamp()
            if key not in self.last_run:
                self.last_run[key] = 0
            if now - self.last_run[key] >= interval * 60:
                self.last_run[key] = now

                try:
                    server_config = await fetch_server_details(gid, name)
                    if not server_config:
                        continue

                    host = server_config[2]
                    password = server_config[3]
                    api_port = server_config[4]

                    api = PalworldAPI(f"http://{host}:{api_port}", password)
                    info = await api.get_server_info()

                    if not info or "version" not in info:
                        logging.error(f"Skipping backup for {name}: Invalid API response.")
                        continue
                except Exception as e:
                    logging.error(f"Skipping backup for {name} because API unreachable: {e}")
                    continue

                channel = self.bot.get_channel(cid)
                if channel:
                    zip_name = f"{name}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
                    zip_dir = path
                    if not os.path.exists(zip_dir):
                        os.makedirs(zip_dir)
                    zip_path = os.path.join(zip_dir, zip_name)
                    try:
                        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                            players = os.path.join(path, "Players")
                            level_sav = os.path.join(path, "Level.sav")
                            meta_sav = os.path.join(path, "LevelMeta.sav")
                            if os.path.isdir(players):
                                for root, dirs, files in os.walk(players):
                                    for f in files:
                                        fp = os.path.join(root, f)
                                        rel = os.path.relpath(fp, path)
                                        z.write(fp, rel)
                            if os.path.isfile(level_sav):
                                z.write(level_sav, "Level.sav")
                            if os.path.isfile(meta_sav):
                                z.write(meta_sav, "LevelMeta.sav")
                        await channel.send(file=discord.File(zip_path))
                        os.remove(zip_path)
                        logging.info(f"Backup created and uploaded: {zip_path}")
                    except Exception as e:
                        logging.error(f"Error creating or sending backup: {e}")

    async def server_names(self, interaction: discord.Interaction, current: str):
        guild_id = interaction.guild.id
        names = await server_autocomplete(guild_id, current)
        return [app_commands.Choice(name=n, value=n) for n in names]

    backup_group = app_commands.Group(name="backup", description="Manage backup settings", default_permissions=discord.Permissions(administrator=True), guild_only=True)

    @backup_group.command(name="setup", description="Setup backup for a server.")
    @app_commands.describe(server="Select the server name")
    @app_commands.autocomplete(server=server_names)
    async def setupbackup(self, interaction: discord.Interaction, server: str):
        async def handle_submit(modal_interaction: discord.Interaction, modal: BackupModal):
            await modal_interaction.response.defer(ephemeral=True)
            cid = int(modal.children[0].value)
            path = modal.children[1].value
            minutes = int(modal.children[2].value)
            try:
                await set_backup(interaction.guild_id, server, path, cid, minutes)
                await modal_interaction.followup.send("Backup config saved.", ephemeral=True)
            except Exception as e:
                logging.error(f"Failed to set backup: {e}")
                await modal_interaction.followup.send(f"Failed: {e}", ephemeral=True)

        modal = BackupModal(title=server, on_submit_callback=handle_submit)
        await interaction.response.send_modal(modal)

    @backup_group.command(name="remove", description="Remove backup config for a server.")
    @app_commands.describe(server="Select the server name to remove")
    @app_commands.autocomplete(server=server_names)
    async def removebackup(self, interaction: discord.Interaction, server: str):
        try:
            await del_backup(interaction.guild.id, server)
            await interaction.response.send_message("Backup config removed.", ephemeral=True)
            logging.info(f"Removed backup config for {server} in guild {interaction.guild.id}")
        except Exception as e:
            logging.error(f"Error removing backup: {e}")
            await interaction.response.send_message("Failed to remove backup config.", ephemeral=True)

    @backup_group.command(name="wipe", description="Remove all backup configs for this server")
    async def wipebackups(self, interaction: discord.Interaction):
        try:
            data = await all_backups()
            deleted = False
            for row in data:
                gid, name, *_ = row
                if gid == interaction.guild.id:
                    await del_backup(gid, name)
                    deleted = True
            if deleted:
                await interaction.response.send_message("All backup configs wiped for this server.", ephemeral=True)
            else:
                await interaction.response.send_message("No backup configs found to wipe.", ephemeral=True)
        except Exception as e:
            logging.error(f"Error wiping backups: {e}")
            await interaction.response.send_message("Failed to wipe backup configs.", ephemeral=True)

    @runloop.before_loop
    async def before_runloop(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(BackupCog(bot))
