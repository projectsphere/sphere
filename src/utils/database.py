import aiosqlite
import os
import datetime

DATABASE_PATH = os.path.join('data', 'palworld.db')

async def db_connection():
    conn = None
    try:
        conn = await aiosqlite.connect(DATABASE_PATH)
    except aiosqlite.Error as e:
        print(e)
    return conn

async def initialize_db():
    commands = [
        """CREATE TABLE IF NOT EXISTS servers (
            guild_id INTEGER NOT NULL,
            server_name TEXT NOT NULL,
            host TEXT NOT NULL,
            password TEXT NOT NULL,
            api_port INTEGER,
            rcon_port INTEGER,
            PRIMARY KEY (guild_id, server_name)
        )""",
        """CREATE TABLE IF NOT EXISTS players (
            user_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            account_name TEXT NOT NULL,
            player_id TEXT NOT NULL,
            ip TEXT NOT NULL,
            ping REAL NOT NULL,
            location_x REAL NOT NULL,
            location_y REAL NOT NULL,
            level INTEGER NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS whitelist (
            player_id TEXT PRIMARY KEY,
            whitelisted BOOLEAN NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS whitelist_status (
            guild_id INTEGER NOT NULL,
            server_name TEXT NOT NULL,
            enabled BOOLEAN NOT NULL,
            PRIMARY KEY (guild_id, server_name)
        )""",
        """CREATE TABLE IF NOT EXISTS bans (
            player_id TEXT NOT NULL,
            reason TEXT NOT NULL,
            timestamp DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS server_logs (
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            server_name TEXT NOT NULL,
            PRIMARY KEY (guild_id, server_name)
        )""",
        """CREATE TABLE IF NOT EXISTS query_logs (
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            server_name TEXT NOT NULL,
            message_id INTEGER NOT NULL,
            player_message_id INTEGER NOT NULL,
            PRIMARY KEY (guild_id, server_name)
        )""",
        """CREATE TABLE IF NOT EXISTS player_tracking (
            guild_id INTEGER PRIMARY KEY,
            enabled BOOLEAN NOT NULL
        )""",
        """CREATE TABLE IF NOT EXISTS chat_settings (
            guild_id INTEGER NOT NULL,
            server_name TEXT NOT NULL,
            log_channel_id INTEGER NOT NULL,
            log_path TEXT NOT NULL,
            webhook_url TEXT NOT NULL,
            PRIMARY KEY (guild_id, server_name)
        )""",
        """CREATE TABLE IF NOT EXISTS backups (
            guild_id INTEGER NOT NULL,
            server_name TEXT NOT NULL,
            path TEXT NOT NULL,
            channel_id INTEGER NOT NULL,
            interval_minutes INTEGER NOT NULL,
            PRIMARY KEY (guild_id, server_name)
        )""",
        """CREATE TABLE IF NOT EXISTS player_sessions (
            user_id TEXT PRIMARY KEY,
            total_time INTEGER NOT NULL DEFAULT 0,
            session_start TIMESTAMP,
            last_session INTEGER NOT NULL DEFAULT 0
        )""",
        """CREATE TABLE IF NOT EXISTS link_codes (
            discord_id INTEGER PRIMARY KEY,
            code TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS linked_players (
            discord_id INTEGER PRIMARY KEY,
            player_userid TEXT NOT NULL,
            player_name TEXT NOT NULL,
            linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS economy (
            discord_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            gold INTEGER DEFAULT 0,
            last_work TIMESTAMP,
            PRIMARY KEY (discord_id, guild_id)
        )"""
    ]
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        for command in commands:
            await cursor.execute(command)
        try:
            await cursor.execute("ALTER TABLE servers ADD COLUMN rcon_port INTEGER")
        except:
            pass
        await conn.commit()
        await conn.close()

async def add_player(player):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT OR REPLACE INTO players (user_id, name, account_name, player_id, ip, ping, location_x, location_y, level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            player['userId'],
            player['name'],
            player['accountName'],
            player['playerId'],
            player['ip'],
            player['ping'],
            player['location_x'],
            player['location_y'],
            player['level']
        ))
        await conn.commit()
        await conn.close()

async def fetch_player(user_id):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("SELECT * FROM players WHERE user_id = ?", (user_id,))
        player = await cursor.fetchone()
        await conn.close()
        return player

async def player_autocomplete(current):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("SELECT user_id, name FROM players WHERE name LIKE ?", (f'%{current}%',))
        players = await cursor.fetchall()
        await conn.close()
        return [(player[0], player[1]) for player in players]

async def fetch_all_servers():
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("SELECT * FROM servers")
        servers = await cursor.fetchall()
        await conn.close()
        return servers

async def add_server(guild_id, server_name, host, password, api_port, rcon_port):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("INSERT INTO servers (guild_id, server_name, host, password, api_port, rcon_port) VALUES (?, ?, ?, ?, ?, ?)",
                       (guild_id, server_name, host, password, api_port, rcon_port))
        await conn.commit()
        await conn.close()

async def fetch_server_details(guild_id, server_name):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("SELECT guild_id, server_name, host, password, api_port, rcon_port FROM servers WHERE guild_id = ? AND server_name = ?", (guild_id, server_name))
        server_details = await cursor.fetchone()
        await conn.close()
        return server_details

async def remove_server(guild_id, server_name):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("DELETE FROM servers WHERE guild_id = ? AND server_name = ?", (guild_id, server_name))
        await conn.commit()
        await conn.close()

async def remove_whitelist_status(guild_id, server_name):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("DELETE FROM whitelist_status WHERE guild_id = ? AND server_name = ?", (guild_id, server_name))
        await conn.commit()
        await conn.close()

async def server_autocomplete(guild_id, current):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("SELECT server_name FROM servers WHERE guild_id = ? AND server_name LIKE ?", (guild_id, f'%{current}%'))
        servers = await cursor.fetchall()
        await conn.close()
        return [server[0] for server in servers]
    
# Server Logs
async def add_logchannel(guild_id, channel_id, server_name):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT OR REPLACE INTO server_logs (guild_id, channel_id, server_name)
            VALUES (?, ?, ?)
        """, (guild_id, channel_id, server_name))
        await conn.commit()
        await conn.close()

async def remove_logchannel(guild_id, server_name):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("DELETE FROM server_logs WHERE guild_id = ? AND server_name = ?", (guild_id, server_name))
        await conn.commit()
        await conn.close()

async def fetch_logchannel(guild_id, server_name):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("SELECT channel_id FROM server_logs WHERE guild_id = ? AND server_name = ?", (guild_id, server_name))
        result = await cursor.fetchone()
        await conn.close()
        return result[0] if result else None
    
# Query Server
async def add_query(guild_id, channel_id, server_name, message_id, player_message_id):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT OR REPLACE INTO query_logs (guild_id, channel_id, server_name, message_id, player_message_id)
            VALUES (?, ?, ?, ?, ?)
        """, (guild_id, channel_id, server_name, message_id, player_message_id))
        await conn.commit()
        await conn.close()

async def fetch_query(guild_id, server_name):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("""
            SELECT channel_id, message_id, player_message_id
            FROM query_logs
            WHERE guild_id = ? AND server_name = ?
        """, (guild_id, server_name))
        result = await cursor.fetchone()
        await conn.close()
        return result if result else None

async def delete_query(guild_id, server_name):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("DELETE FROM query_logs WHERE guild_id = ? AND server_name = ?", (guild_id, server_name))
        await conn.commit()
        await conn.close()

# Status Tracking
async def set_tracking(guild_id, enabled: bool):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT OR REPLACE INTO player_tracking (guild_id, enabled) VALUES (?, ?)
        """, (guild_id, enabled))
        await conn.commit()
        await conn.close()

async def get_tracking():
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT guild_id FROM player_tracking WHERE enabled = 1")
        rows = await cursor.fetchall()
        await conn.close()
        return [row[0] for row in rows]
    
# Chat Relay/Feed  
async def set_chat(guild_id, server_name, chat_channel_id, log_path, webhook_url):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT OR REPLACE INTO chat_settings (
                guild_id, server_name, log_channel_id, log_path, webhook_url
            ) VALUES (?, ?, ?, ?, ?)
        """, (guild_id, server_name, chat_channel_id, log_path, webhook_url))
        await conn.commit()
        await conn.close()

async def get_chat(guild_id):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            SELECT server_name, log_channel_id, log_path, webhook_url
            FROM chat_settings WHERE guild_id = ?
        """, (guild_id,))
        result = await cursor.fetchall()
        await conn.close()
        return result

async def delete_chat(guild_id, server_name):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("DELETE FROM chat_settings WHERE guild_id = ? AND server_name = ?", (guild_id, server_name))
        await conn.commit()
        await conn.close()

# Backups
async def set_backup(guild_id, server_name, path, channel_id, interval_minutes):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT OR REPLACE INTO backups (guild_id, server_name, path, channel_id, interval_minutes)
            VALUES (?, ?, ?, ?, ?)
        """, (guild_id, server_name, path, channel_id, interval_minutes))
        await conn.commit()
        await conn.close()

async def all_backups():
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            SELECT guild_id, server_name, path, channel_id, interval_minutes
            FROM backups
        """)
        rows = await cursor.fetchall()
        await conn.close()
        return rows

async def del_backup(guild_id, server_name):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            DELETE FROM backups
            WHERE guild_id = ? AND server_name = ?
        """, (guild_id, server_name))
        await conn.commit()
        await conn.close()

# Player Time Tracking
SESSION_TIMEOUT_SECONDS = 300

async def track_sessions(current_online: set, previous_online: set, timestamp: str):
    conn = await db_connection()
    if not conn:
        return

    cursor = await conn.cursor()
    now = datetime.datetime.fromisoformat(timestamp)

    newly_joined = current_online - previous_online
    for uid in newly_joined:
        await cursor.execute("SELECT session_start, total_time FROM player_sessions WHERE user_id = ?", (uid,))
        row = await cursor.fetchone()
        if row is None:
            await cursor.execute(
                "INSERT INTO player_sessions (user_id, total_time, session_start, last_session) VALUES (?, 0, ?, 0)",
                (uid, timestamp)
            )
        else:
            await cursor.execute(
                "UPDATE player_sessions SET session_start = ? WHERE user_id = ?",
                (timestamp, uid)
            )

    disconnected = previous_online - current_online
    for uid in disconnected:
        await cursor.execute("SELECT session_start, total_time FROM player_sessions WHERE user_id = ?", (uid,))
        row = await cursor.fetchone()
        if row and row[0]:
            dt_start = datetime.datetime.fromisoformat(row[0])
            delta = int((now - dt_start).total_seconds())
            new_total = row[1] + delta
            await cursor.execute(
                "UPDATE player_sessions SET total_time = ?, session_start = NULL, last_session = ? WHERE user_id = ?",
                (new_total, delta, uid)
            )

    await cursor.execute(
        "SELECT user_id, session_start FROM player_sessions WHERE session_start IS NOT NULL"
    )
    all_active = await cursor.fetchall()
    for uid, session_start in all_active:
        if uid not in current_online:
            dt_start = datetime.datetime.fromisoformat(session_start)
            age = int((now - dt_start).total_seconds())
            if age > SESSION_TIMEOUT_SECONDS:
                await cursor.execute("SELECT total_time FROM player_sessions WHERE user_id = ?", (uid,))
                row = await cursor.fetchone()
                if row:
                    new_total = row[0] + age
                    await cursor.execute(
                        "UPDATE player_sessions SET total_time = ?, session_start = NULL, last_session = ? WHERE user_id = ?",
                        (new_total, age, uid)
                    )

    await conn.commit()
    await conn.close()

async def get_player_session(user_id: str):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("SELECT user_id, total_time, session_start FROM player_sessions WHERE user_id = ?", (user_id,))
        row = await cursor.fetchone()
        await conn.close()
        return row

async def create_link_code(discord_id: int, code: str):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT OR REPLACE INTO link_codes (discord_id, code, timestamp)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (discord_id, code))
        await conn.commit()
        await conn.close()

async def get_link_code(discord_id: int):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT code FROM link_codes WHERE discord_id = ?", (discord_id,))
        row = await cursor.fetchone()
        await conn.close()
        return row[0] if row else None

async def verify_link_code(code: str):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT discord_id FROM link_codes WHERE code = ?", (code,))
        row = await cursor.fetchone()
        await conn.close()
        return row[0] if row else None

async def link_player(discord_id: int, player_userid: str, player_name: str):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT OR REPLACE INTO linked_players (discord_id, player_userid, player_name, linked_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (discord_id, player_userid, player_name))
        await cursor.execute("DELETE FROM link_codes WHERE discord_id = ?", (discord_id,))
        await conn.commit()
        await conn.close()

async def get_linked_player(discord_id: int):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT player_userid, player_name FROM linked_players WHERE discord_id = ?", (discord_id,))
        row = await cursor.fetchone()
        await conn.close()
        return row

async def get_discord_from_userid(player_userid: str):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT discord_id FROM linked_players WHERE player_userid = ?", (player_userid,))
        row = await cursor.fetchone()
        await conn.close()
        return row[0] if row else None

if __name__ == "__main__":
    import asyncio
    asyncio.run(initialize_db())
