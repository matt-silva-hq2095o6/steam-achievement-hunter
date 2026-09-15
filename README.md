# steam-achievement-hunter

A small command-line utility to hunt down the easiest achievements you are missing across your Steam library. It pulls your owned games, fetches your achievement status, compares them with global completion percentages, and displays a sorted list of the most reachable goals.

To avoid hitting Steam API limits and to keep runs fast, it caches fetched game details locally and focuses on games you have actually played.

## Installation

Clone the repository and install the single dependency:

```cmd
pip install -r requirements.txt
```

## Configuration

You need a Steam API Key and your SteamID64.
- Get an API key from: https://steamcommunity.com/dev/apikey
- Find your SteamID64 using online lookup tools or your profile URL.

You can set these as environment variables or save them in a local config file so you do not have to pass them to the command line every time.

```cmd
set STEAM_API_KEY=your_key_here
set STEAM_USER_ID=76561198xxxxxxxxx
```

Alternatively, run the tool once with the setup flags to write them to `~/.steam_hunter.json`:

```cmd
python hunter.py --set-key your_key_here --set-id 76561198xxxxxxxxx
```

## Usage

Show the easiest unearned achievements across your top 10 most played games:
```cmd
python hunter.py
```

Scan your top 25 games instead of the default 10:
```cmd
python hunter.py --games-limit 25
```

Target a single specific game by its AppID:
```cmd
python hunter.py --appid 400
```

Show your rarest unlocked achievements (bragging rights mode):
```cmd
python hunter.py --mode rare
```

Force refresh the local cache for all queried games:
```cmd
python hunter.py --refresh
```

<!-- checked: 2026-09-15 -->
