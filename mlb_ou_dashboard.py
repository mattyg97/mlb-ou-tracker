import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# --------------------------
# Get past MLB games by team matchup
# --------------------------

@st.cache_data(ttl=1800)
def get_head_to_head_results(team1, team2, season=2024, max_games=10):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&season={season}&team={team1_id}&opponent={team2_id}&gameType=R"
    res = requests.get(url).json()

    games = res.get('dates', [])
    results = []

    for game_day in games:
        game = game_day['games'][0]
        if game['status']['abstractGameState'] != "Final":
            continue
        game_id = game['gamePk']
        game_data = requests.get(f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live").json()

        try:
            home = game_data['gameData']['teams']['home']['name']
            away = game_data['gameData']['teams']['away']['name']
            home_score = game_data['liveData']['linescore']['teams']['home']['runs']
            away_score = game_data['liveData']['linescore']['teams']['away']['runs']
            total_runs = home_score + away_score
            game_date = game_data['gameData']['datetime']['originalDate']
        except KeyError:
            continue

        # Use a default O/U line for now (can be updated with bookmaker API)
        ou_line = 8.5
        ou_result = "Over" if total_runs > ou_line else "Under"

        results.append({
            'Date': game_date,
            'Home': home,
            'Away': away,
            'Score': f"{away_score}–{home_score}",
            'Total Runs': total_runs,
            'O/U Line': ou_line,
            'O/U Result': ou_result
        })

        if len(results) >= max_games:
            break

    return results

# --------------------------
# UI
# --------------------------

st.set_page_config(page_title="MLB Head-to-Head O/U Tracker", layout="wide")
st.title("⚾ MLB Over/Under Tracker – Head-to-Head Matchups")

team_name_to_id = {
    "Yankees": 147, "Red Sox": 111, "Dodgers": 119, "Giants": 137,
    "Mets": 121, "Braves": 144, "Phillies": 143, "Cubs": 112,
    "Padres": 135, "Astros": 117, "Rays": 139, "Orioles": 110,
    # Add more teams as needed
}

team_list = list(team_name_to_id.keys())
team1 = st.selectbox("Team 1", team_list, index=0)
team2 = st.selectbox("Team 2", team_list, index=1)

if team1 == team2:
    st.warning("Please select two different teams.")
else:
    team1_id = team_name_to_id[team1]
    team2_id = team_name_to_id[team2]

    data = get_head_to_head_results(team1, team2)
    if not data:
        st.warning("No recent matchups found between these teams.")
    else:
        df = pd.DataFrame(data)
        st.subheader(f"Last {len(df)} Matchups: {team1} vs {team2}")
        st.dataframe(df, use_container_width=True)

        over_count = (df["O/U Result"] == "Over").sum()
        pct = (over_count / len(df)) * 100
        st.markdown(f"📊 **{pct:.1f}%** of the last {len(df)} games went **Over 8.5** runs.")
