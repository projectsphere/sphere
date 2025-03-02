import asyncio
from gamercon_async import GameRCON, ClientError, TimeoutError, InvalidPassword

class RconUtility:
    def __init__(self, timeout=30):
        self.timeout = timeout

    async def rcon_command(self, host: str, port: int, password: str, command: str):
        try:
            async with GameRCON(host, port, password, self.timeout) as rcon:
                return await rcon.send(command)
        except (ClientError, TimeoutError, InvalidPassword) as e:
            return f"RCON error: {e}"
        except asyncio.TimeoutError:
            return "Timed out."
        except ConnectionResetError as e:
            return f"Connection reset: {e}"
