import asyncio
import time
from typing import Dict, Tuple, Optional
from palworld_api import PalworldAPI
import logging

class CachedServerData:
    def __init__(self, server_info, server_metrics, player_list, timestamp):
        self.server_info = server_info
        self.server_metrics = server_metrics
        self.player_list = player_list
        self.timestamp = timestamp

class APICache:
    def __init__(self, cache_duration: int = 25):
        self.cache: Dict[str, CachedServerData] = {}
        self.cache_duration = cache_duration
        self.locks: Dict[str, asyncio.Lock] = {}
    
    def _get_cache_key(self, host: str, api_port: int) -> str:
        return f"{host}:{api_port}"
    
    def _is_cache_valid(self, cached_data: CachedServerData) -> bool:
        return (time.time() - cached_data.timestamp) < self.cache_duration
    
    async def get_all_server_data(self, host: str, api_port: int, password: str) -> Tuple[Optional[dict], Optional[dict], Optional[dict]]:
        cache_key = self._get_cache_key(host, api_port)
        
        if cache_key not in self.locks:
            self.locks[cache_key] = asyncio.Lock()
        
        async with self.locks[cache_key]:
            if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
                cached = self.cache[cache_key]
                return cached.server_info, cached.server_metrics, cached.player_list
            
            try:
                api = PalworldAPI(f"http://{host}:{api_port}", password)
                
                server_info, server_metrics, player_list = await asyncio.gather(
                    api.get_server_info(),
                    api.get_server_metrics(),
                    api.get_player_list(),
                    return_exceptions=True
                )
                
                if isinstance(server_info, Exception):
                    raise server_info
                if isinstance(server_metrics, Exception):
                    raise server_metrics
                if isinstance(player_list, Exception):
                    raise player_list
                
                self.cache[cache_key] = CachedServerData(
                    server_info=server_info,
                    server_metrics=server_metrics,
                    player_list=player_list,
                    timestamp=time.time()
                )
                
                return server_info, server_metrics, player_list
                
            except Exception as e:
                logging.error(f"Error fetching data for {cache_key}: {e}")
                raise
    
    async def get_server_info(self, host: str, api_port: int, password: str) -> Optional[dict]:
        server_info, _, _ = await self.get_all_server_data(host, api_port, password)
        return server_info
    
    async def get_server_metrics(self, host: str, api_port: int, password: str) -> Optional[dict]:
        _, server_metrics, _ = await self.get_all_server_data(host, api_port, password)
        return server_metrics
    
    async def get_player_list(self, host: str, api_port: int, password: str) -> Optional[dict]:
        _, _, player_list = await self.get_all_server_data(host, api_port, password)
        return player_list
    
    def invalidate_cache(self, host: str, api_port: int):
        cache_key = self._get_cache_key(host, api_port)
        if cache_key in self.cache:
            del self.cache[cache_key]
    
    def clear_all_cache(self):
        self.cache.clear()

api_cache = APICache(cache_duration=25)
