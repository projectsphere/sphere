import discord
from discord.ext import commands
import os
import zipfile
import datetime
import logging
import asyncio
import yaml
import tempfile
import shutil
import stat
from paramiko import SSHClient, AutoAddPolicy

CONFIG_FILE = os.path.join("config", "sftp.yml")

def load_yaml_config():
    if not os.path.exists(CONFIG_FILE):
        return {"servers": []}
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {"servers": []}

class SFTPBackupCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = load_yaml_config().get("servers", [])
        self.last_run = {}
        self.poll_seconds = 60
        self.task = asyncio.create_task(self._loop())

    def cog_unload(self):
        if self.task:
            self.task.cancel()

    def _sftp_connect(self, cfg):
        ssh = SSHClient()
        ssh.set_missing_host_key_policy(AutoAddPolicy())
        ssh.connect(
            hostname=cfg["host"],
            username=cfg["username"],
            password=cfg["password"],
            port=int(cfg.get("port", 2022)),
            timeout=15,
        )
        sftp = ssh.open_sftp()
        return ssh, sftp

    def _safe_exists_dir(self, sftp, path):
        try:
            return stat.S_ISDIR(sftp.stat(path).st_mode)
        except:
            return False

    def _safe_exists_file(self, sftp, path):
        try:
            return stat.S_ISREG(sftp.stat(path).st_mode)
        except:
            return False

    def _sftp_fetch_recursive(self, sftp, remote_dir, local_dir):
        os.makedirs(local_dir, exist_ok=True)
        for entry in sftp.listdir_attr(remote_dir):
            rpath = f"{remote_dir}/{entry.filename}"
            lpath = os.path.join(local_dir, entry.filename)
            if stat.S_ISDIR(entry.st_mode):
                self._sftp_fetch_recursive(sftp, rpath, lpath)
            else:
                sftp.get(rpath, lpath)

    def _download_remote_save(self, cfg, staging_dir):
        ssh = None
        sftp = None
        try:
            ssh, sftp = self._sftp_connect(cfg)
            remote_root = cfg.get("save_path") or ""
            if not remote_root:
                return False
            players_dir = f"{remote_root}/Players"
            level_sav = f"{remote_root}/Level.sav"
            meta_sav = f"{remote_root}/LevelMeta.sav"
            if self._safe_exists_dir(sftp, players_dir):
                self._sftp_fetch_recursive(sftp, players_dir, os.path.join(staging_dir, "Players"))
            if self._safe_exists_file(sftp, level_sav):
                sftp.get(level_sav, os.path.join(staging_dir, "Level.sav"))
            if self._safe_exists_file(sftp, meta_sav):
                sftp.get(meta_sav, os.path.join(staging_dir, "LevelMeta.sav"))
            return True
        except Exception as e:
            logging.error(f"[{cfg.get('name','?')}] SFTP fetch error: {e}")
            return False
        finally:
            try:
                if sftp: sftp.close()
            except: pass
            try:
                if ssh: ssh.close()
            except: pass

    async def _run_backup_once(self, cfg):
        channel_id = int(cfg.get("backup_channel", 0) or 0)
        if not channel_id:
            return
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            try:
                channel = await self.bot.fetch_channel(channel_id)
            except:
                return
        staging_dir = tempfile.mkdtemp(prefix=f"backup_{cfg.get('name','srv')}_", dir="logs" if os.path.isdir("logs") else None)
        ok = await asyncio.to_thread(self._download_remote_save, cfg, staging_dir)
        if not ok:
            shutil.rmtree(staging_dir, ignore_errors=True)
            return
        zip_name = f"{cfg.get('name','server')}_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.zip"
        zip_path = os.path.join(staging_dir, zip_name)
        try:
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
                for root, dirs, files in os.walk(staging_dir):
                    for f in files:
                        if f == os.path.basename(zip_path):
                            continue
                        fp = os.path.join(root, f)
                        rel = os.path.relpath(fp, staging_dir)
                        z.write(fp, rel)
            file_size = os.path.getsize(zip_path)
            ts = discord.utils.utcnow()
            embed = discord.Embed(
                title=f"Backup Completed - {cfg.get('name','server')}",
                color=discord.Color.blurple(),
                description="Backup created successfully."
            )
            embed.add_field(name="Filename", value=zip_name, inline=False)
            embed.add_field(name="Size", value=f"{file_size/1024:.2f} KB", inline=False)
            embed.add_field(name="Time", value=f"<t:{int(ts.timestamp())}:F>", inline=False)
            await channel.send(embed=embed)
            await channel.send(file=discord.File(zip_path))
        except Exception as e:
            logging.error(f"[{cfg.get('name','?')}] Backup packaging/send error: {e}")
        finally:
            try:
                shutil.rmtree(staging_dir, ignore_errors=True)
            except: pass

    async def _loop(self):
        while True:
            now = datetime.datetime.utcnow().timestamp()
            for cfg in self.config:
                name = cfg.get("name", "server")
                key = name
                minutes = int(cfg.get("backup_interval", 30))
                interval = max(1, minutes) * 60
                if key not in self.last_run:
                    self.last_run[key] = 0
                if now - self.last_run[key] >= interval:
                    self.last_run[key] = now
                    try:
                        await self._run_backup_once(cfg)
                    except Exception as e:
                        logging.error(f"[{name}] Backup loop error: {e}")
            await asyncio.sleep(self.poll_seconds)

async def setup(bot):
    if not os.path.exists(CONFIG_FILE):
        logging.warning("sftp.yml not found, SFTP Backup cog not loaded.")
        return
    await bot.add_cog(SFTPBackupCog(bot))
