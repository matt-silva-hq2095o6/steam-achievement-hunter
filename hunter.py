"""
Main command-line entry point for scanning your Steam library and sorting
unlocked achievements by global completion rates.
"""

import argparse
import json
import os
import sys
from pathlib import Path
import httpx

from steam_achievement_hunter import steam_api

CONFIG_FILE = Path.home() / ".steam_achievement_hunter.json"

def load_config():
    """Load saved credentials to prevent constant re-typing on execution."""
    if not CONFIG_FILE.exists():
        return {}
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        # Config file is messed up or locked, ignore it
        return {}

def save_config(api_key, steam_id):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"api_key": api_key, "steam_id": steam_id}, f, indent=2)
    except OSError:
        pass

def main():
    parser = argparse.ArgumentParser(
        description="Scan your Steam library, find missing achievements, and sort them by how common they are.",
        epilog="Usage: steam-achievement-hunter --limit 15"
    )
    parser.add_argument("--key", help="Steam Web API Key")
    parser.add_argument("--steamid", help="Steam ID64 (17 digits)")
    parser.add_argument("--limit", type=int, default=20, help="Number of achievements to display")
    parser.add_argument("--min-playtime", type=int, default=0, help="Only scan games with at least this many minutes played")
    parser.add_argument("--save", action="store_true", help="Save credentials locally to avoid typing them again")
    args = parser.parse_args()

    config = load_config()

    api_key = args.key or os.environ.get("STEAM_API_KEY") or config.get("api_key")
    steamID = args.steamid or os.environ.get("STEAM_USER_ID") or config.get("steam_id")

    if not api_key:
        print("Error: Steam Web API Key is missing. Pass it with --key or set STEAM_API_KEY.", file=sys.stderr)
        sys.exit(1)
    
    if not steamID:
        print("Error: Steam ID is missing. Pass it with --steamid or set STEAM_USER_ID.", file=sys.stderr)
        sys.exit(1)

    if args.save:
        save_config(api_key, steamID)
        print("Saved credentials to local config file.")

    print("Fetching your owned games library...")
    try:
        games = steam_api.get_owned_games(api_key, steamID)
    except httpx.HTTPStatusError as e:
        print(f"Steam API returned HTTP error: {e.response.status_code}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Network error while reaching Steam: {e}", file=sys.stderr)
        sys.exit(1)

    if not games:
        print("No games found or library is private.", file=sys.stderr)
        sys.exit(1)

    scannable_games = [g for g in games if g.get("playtime_forever", 0) >= args.min_playtime]
    print(f"Scanning {len(scannable_games)} games for missing achievements...")

    missing_achievements = []

    # FIXME: Speed up fetching by skipping games known to have no achievements.
    for idx, game in enumerate(scannable_games, 1):
        appid = game["appid"]
        game_name = game["name"]
        
        # print(f"DEBUG: Processing game {game_name} ({appid})")
        
        try:
            player_ach = steam_api.get_player_achievements(api_key, steamID, appid)
            if not player_ach:
                continue
            
            unlocked_count = sum(1 for a in player_ach if a["achieved"])
            if unlocked_count == len(player_ach):
                continue

            global_rates = steam_api.get_global_achievements(appid)
        except httpx.HTTPError:
            continue
        except KeyError:
            # Game might have stats/achievements disabled on Steam backend
            continue

        for ach in player_ach:
            if not ach["achieved"]:
                api_name = ach["apiname"]
                pct = global_rates.get(api_name, 0.0)
                missing_achievements.append({
                    "game": game_name,
                    "name": ach.get("name", api_name),
                    "description": ach.get("description", ""),
                    "pct": pct
                })

        sys.stdout.write(f"\rAnalyzed {idx}/{len(scannable_games)} games...")
        sys.stdout.flush()

    print("\n")

    if not missing_achievements:
        print("No missing achievements found. You are either fully completed or those games have no achievements.")
        return

    missing_achievements.sort(key=lambda x: x["pct"], reverse=True)

    print(f"Top {args.limit} Easiest Missing Achievements:")
    print("=" * 90)
    print(f"{'Global %':<10} | {'Game':<25} | {'Achievement Name':<30}")
    print("-" * 90)
    
    for ach in missing_achievements[:args.limit]:
        game_disp = ach["game"][:23] + ".." if len(ach["game"]) > 25 else ach["game"]
        name_disp = ach["name"][:28] + ".." if len(ach["name"]) > 30 else ach["name"]
        
        print(f"{ach['pct']:8.2f}% | {game_disp:<25} | {name_disp:<30}")
        if ach["description"]:
            print(f"           ↳ {ach['description']}")
            print("-" * 90)

    # TODO: add CSV output arg to export results to spreadsheet

if __name__ == "__main__":
    main()
