import aiosqlite
import os

DATABASE_PATH = os.path.join('data', 'palworld.db')

async def db_connection():
    conn = None
    try:
        conn = await aiosqlite.connect(DATABASE_PATH)
    except aiosqlite.Error as e:
        print(e)
    return conn

async def get_gold(discord_id: int, guild_id: int):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT gold FROM economy WHERE discord_id = ? AND guild_id = ?", (discord_id, guild_id))
        row = await cursor.fetchone()
        await conn.close()
        return row[0] if row else 0

async def add_gold(discord_id: int, guild_id: int, amount: int):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT INTO economy (discord_id, guild_id, gold)
            VALUES (?, ?, ?)
            ON CONFLICT(discord_id, guild_id) DO UPDATE
            SET gold = gold + excluded.gold
        """, (discord_id, guild_id, amount))
        await conn.commit()
        await cursor.execute("SELECT gold FROM economy WHERE discord_id = ? AND guild_id = ?", (discord_id, guild_id))
        new_balance = await cursor.fetchone()
        await conn.close()
        return new_balance[0] if new_balance else amount

async def set_gold(discord_id: int, guild_id: int, amount: int):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT INTO economy (discord_id, guild_id, gold)
            VALUES (?, ?, ?)
            ON CONFLICT(discord_id, guild_id) DO UPDATE
            SET gold = ?
        """, (discord_id, guild_id, amount, amount))
        await conn.commit()
        await conn.close()

async def remove_gold(discord_id: int, guild_id: int, amount: int):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT gold FROM economy WHERE discord_id = ? AND guild_id = ?", (discord_id, guild_id))
        row = await cursor.fetchone()
        current_gold = row[0] if row else 0
        
        if current_gold < amount:
            await conn.close()
            return False, current_gold
        
        new_gold = current_gold - amount
        await cursor.execute("""
            UPDATE economy SET gold = ? WHERE discord_id = ? AND guild_id = ?
        """, (new_gold, discord_id, guild_id))
        await conn.commit()
        await conn.close()
        return True, new_gold

async def get_last_work(discord_id: int, guild_id: int):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("SELECT last_work FROM economy WHERE discord_id = ? AND guild_id = ?", (discord_id, guild_id))
        row = await cursor.fetchone()
        await conn.close()
        return row[0] if row else None

async def update_last_work(discord_id: int, guild_id: int, timestamp: str):
    conn = await db_connection()
    if conn:
        cursor = await conn.cursor()
        await cursor.execute("""
            INSERT INTO economy (discord_id, guild_id, last_work)
            VALUES (?, ?, ?)
            ON CONFLICT(discord_id, guild_id) DO UPDATE
            SET last_work = ?
        """, (discord_id, guild_id, timestamp, timestamp))
        await conn.commit()
        await conn.close()
