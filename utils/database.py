import aiosqlite
import os
from datetime import datetime, timezone

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
        """CREATE TABLE IF NOT EXISTS player_playtimes (
            server_name TEXT NOT NULL,
            user_id TEXT NOT NULL,
            total_playtime INTEGER NOT NULL DEFAULT 0,
            PRIMARY KEY (server_name, user_id)
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
        """CREATE TABLE IF NOT EXISTS active_sessions (
            server_name TEXT NOT NULL,
            user_id TEXT NOT NULL,
            join_time INTEGER NOT NULL,
            PRIMARY KEY (server_name, user_id)
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
        result = await cursor.fetchone()
        await conn.close()
        return result

async def delete_chat(guild_id, server_name):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("DELETE FROM chat_settings WHERE guild_id = ? AND server_name = ?", (guild_id, server_name))
        await conn.commit()
        await conn.close()

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

async def update_player_playtime(server_name: str, user_id: str, session_seconds: int):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute(
            """
            INSERT INTO player_playtimes (server_name, user_id, total_playtime)
            VALUES (?, ?, ?)
            ON CONFLICT(server_name, user_id) DO UPDATE SET total_playtime = total_playtime + ?
            """, 
            (server_name, user_id, session_seconds, session_seconds)
        )
        await conn.commit()
        await conn.close()

async def fetch_player_playtime(server_name: str, user_id: str):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute("SELECT total_playtime FROM player_playtimes WHERE server_name = ? AND user_id = ?", (server_name, user_id))
        result = await cursor.fetchone()
        await conn.close()
        return result[0] if result else 0

async def fetch_playtime_leaderboard(server_name: str, limit: int = 10):
    conn = await db_connection()
    if conn is not None:
        cursor = await conn.cursor()
        await cursor.execute(
            """
            SELECT pp.user_id, pp.total_playtime, IFNULL(p.name, pp.user_id)
            FROM player_playtimes pp
            LEFT JOIN players p ON pp.user_id = p.user_id
            WHERE pp.server_name = ?
            ORDER BY pp.total_playtime DESC
            LIMIT ?
            """, 
            (server_name, limit)
        )
        rows = await cursor.fetchall()
        await conn.close()
        return rows

async def add_active_session(server_name: str, user_id: str, join_time: int):
    """Persist the active session with join_time as Unix timestamp."""
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """
            INSERT OR REPLACE INTO active_sessions (server_name, user_id, join_time)
            VALUES (?, ?, ?)
            """,
            (server_name, user_id, join_time)
        )
        await conn.commit()
        await conn.close()

async def remove_active_session(server_name: str, user_id: str):
    """Remove a stored active session."""
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """
            DELETE FROM active_sessions
            WHERE server_name = ? AND user_id = ?
            """,
            (server_name, user_id)
        )
        await conn.commit()
        await conn.close()

async def load_active_sessions(server_name: str):
    """Load active sessions from the database; returns a dict {user_id: join_time (as UTC datetime)}."""
    conn = await db_connection()
    sessions = {}
    if conn:
        cursor = await conn.cursor()
        await cursor.execute(
            """
            SELECT user_id, join_time FROM active_sessions
            WHERE server_name = ?
            """,
            (server_name,)
        )
        rows = await cursor.fetchall()
        await conn.close()
        for user_id, ts in rows:
            sessions[user_id] = datetime.fromtimestamp(ts, tz=timezone.utc)
    return sessions

async def load_total_playtimes_for_server(server_name: str) -> dict:
    """Return a dictionary {user_id: total_playtime_in_seconds} for the given server."""
    conn = await db_connection()
    totals = {}
    if conn:
        cursor = await conn.cursor()
        await cursor.execute(
            "SELECT user_id, total_playtime FROM player_playtimes WHERE server_name = ?",
            (server_name,)
        )
        rows = await cursor.fetchall()
        await conn.close()
        for user_id, total in rows:
            totals[user_id] = total
    return totals

if __name__ == "__main__":
    import asyncio
    asyncio.run(initialize_db())
