# test_api.py
import requests
import time

url = "https://lol.fandom.com/api.php"
params = {
    'action': 'cargoquery',
    'format': 'json',
    'tables': 'ScoreboardGames',
    'fields': 'GameId, Team1, Team2',
    'where': "OverviewPage='LEC/2024 Season/Spring Season'",
    'limit': 5
}

response = requests.get(url, params=params)
data = response.json()

if 'error' in data:
    print(f"ERROR: {data['error']}")
elif 'cargoquery' in data:
    print(f"SUCCESS: Found {len(data['cargoquery'])} games!")
    for game in data['cargoquery']:
        g = game['title']
        print(f"  {g['Team1']} vs {g['Team2']}")