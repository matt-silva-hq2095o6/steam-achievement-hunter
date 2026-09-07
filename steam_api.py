import json
import time
from pathlib import Path
import httpx

class SteamAPI:
    """Helper to interface with Steam Web API and manage JSON caching."""

    def __init__(self, api_key: str, cache_dir: Path = None):
        self.api_key = api_key
        if cache_dir is None:
            self.cache_dir = Path.home() / ".steam_achievement_hunter" / "cache"
        else:
            self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.client = httpx.Client()

    def _get_cached_or_fetch(self, cache_file: Path, url: str, params: dict, ttl_seconds: int) -> dict:
        if cache_file.exists():
            file_age = time.time() - cache_file.stat().st_mtime
            if file_age < ttl_seconds:
                try:
                    return json.loads(cache_file.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    cache_file.unlink(missing_ok=True)

        # print(f"DEBUG fetching fresh API data: {url} with {params}")
        resp = self.client.get(url, params=params)
        resp.raise_for_status()
        data = resp.json()

        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return data

    def get_player_achvs(self, steam_id: str, appid: int) -> dict:
        # Legacy naming pattern get_player_achvs preserved for caller compatibility
        cache_file = self.cache_dir / f"player_{steam_id}_{appid}.json"
        url = "https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v0001/"
        params = {
            "appid": appid,
            "key": self.api_key,
            "steamid": steam_id,
            "l": "en"
        }
        
        # Player progress updates often, cache only for 20 minutes
        data = self._get_cached_or_fetch(cache_file, url, params, ttl_seconds=1200)
        
        # TODO: handle private profile response which returns 200 OK but success=False inside playerstats
        playerstats = data.get("playerstats", {})
        if not playerstats.get("success", True):
            error_msg = playerstats.get("error", "Profile is private or achievements are disabled for this game")
            raise ValueError(f"Steam API error: {error_msg}")
            
        return playerstats

    def get_game_schema(self, appid: int) -> dict:
        cache_file = self.cache_dir / f"schema_{appid}.json"
        url = "https://api.steampowered.com/ISteamUserStats/GetSchemaForGame/v2/"
        params = {
            "key": self.api_key,
            "appid": appid,
            "l": "en"
        }
        # Game achievement list schemas rarely change, cache for 14 days
        data = self._get_cached_or_fetch(cache_file, url, params, ttl_seconds=1209600)
        return data.get("game", {})

    def get_global_percentages(self, appid: int) -> dict:
        cache_file = self.cache_dir / f"global_{appid}.json"
        url = "https://api.steampowered.com/ISteamUserStats/GetGlobalAchievementPercentagesForApp/v0002/"
        params = {
            "gameid": appid
        }
        # Global rates shift slow, cache for 1 day
        data = self._get_cached_or_fetch(cache_file, url, params, ttl_seconds=86400)
        return data.get("achievementpercentages", {})
