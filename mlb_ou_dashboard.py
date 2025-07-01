import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import time

st.set_page_config(page_title="MLB O/U Tracker v2", layout="wide")
st.title("⚾ MLB Over/Under Tracker (2025) with Live Odds & Trends")

# -------------------------
# Setup
# -------------------------
ODDS_API_KEY = st.secrets.get("odds_api_key") or "YOUR_API_KEY_HERE"
SPORT = "baseball_mlb"
REGION = "us"
MARKET = "totals"
SEASON = 2025

@st.cache_data(ttl=86400)
def get_teams():
    res = requests.get("https://statsapi.mlb.com/api/v1/teams?sportId=1").json()
    return {team["name"]: team["id"] for team in res["teams"] if team["sport"]["id"] == 1}

# -------------------------
# Live Odds API
# -------------------------
def get_live_ou_line(team1, team2):
    if not ODDS_API_KEY or "YOUR_API_KEY_HERE" in ODDS_API_KEY:
        return None

    url = f"https://api.the-odds-api.com/v4/sports/{SPORT}/odds"
    params = {
        "regions": REGION,
        "markets": MARKET,
        "oddsFormat": "decimal",
        "apiKey": ODDS_API_KEY
    }

    res = requests.get(url, params=params)
    if res.status_code != 200:
        return None

    games = res.json()
    for game in games:
        if team1.lower() in game["home_team"].lower() and team2.lower() in game["away_team"].lower():
            for bookmaker in game["bookmakers"]:
                for market in bookmaker["markets"]:
                    if market["key"] == "totals":
                        outcomes = market["outcomes"]
                        if outcomes:
                            return {
                                "line": outcomes[0]["point"],
                                "over_odds": outcomes[0]["odds"],
                                "under_odds": outcomes[1]["odds"]
                            }
    return None

# -------------------------
# Get Team's Last 10 Games
# -------------------------
@st.cache_data(ttl=1800)
def get_team_trend(team_id, ou_line=8.5):
    url = f"https://statsapi.mlb.com/api/v1/schedule?teamId={team_id}&sportId=1&season={SEASON}&gameType=R"
    res = requests.get(url).json()
    games = res.get("dates", [])
    results = []

    for g in games:
        try:
            game = g["games"][0]
            if game["status"]["abstractGameState"] != "Final":
                continue

            game_id = game["gamePk"]
            details = requests.get(f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live").json()
            h = details['gameData']['teams']['home']
            a = details['gameData']['teams']['away']
            hs = details['liveData']['linescore']['teams']['home']['runs']
            as_ = details['liveData']['linescore']['teams']['away']['runs']
            date = details['gameData']['datetime']['originalDate']
            total = hs + as_
            result = "Over" if total > ou_line else "Under"

            results.append({
                "Date": date,
                "Opponent": a["name"] if h["id"] == team_id else h["name"],
                "Total Runs": total,
                "O/U Result": result
            })

            if len(results) >= 10:
                break
        except:
            continue

    return pd.DataFrame(results)

# -------------------------
# UI
# -------------------------
teams = get_teams()
team_names = sorted(teams.keys())
col1, col2 = st.columns(2)
with col1:
    team1 = st.selectbox("Team 1", team_names, index=0)
with col2:
    team2 = st.selectbox("Team 2", team_names, index=1)

st.divider()
st.subheader("🔍 Live Over/Under Line")

live_odds = get_live_ou_line(team1, team2)
if live_odds:
    st.markdown(f"**O/U Line:** {live_odds['line']}  |  **Over Odds:** {live_odds['over_odds']}  |  **Under Odds:** {live_odds['under_odds']}")
    ou_line = live_odds['line']
else:
    ou_line = st.slider("No live line found — set custom O/U line:", 5.0, 12.0, 8.5, 0.5)

# -------------------------
# Team Trend Plot
# -------------------------
st.subheader(f"📈 {team1} O/U Trend (Last 10 Games)")
df_trend = get_team_trend(teams[team1], ou_line)
if not df_trend.empty:
    fig, ax = plt.subplots()
    ax.plot(df_trend["Date"], df_trend["Total Runs"], marker='o')
    for i, row in df_trend.iterrows():
        color = "green" if row["O/U Result"] == "Over" else "red"
        ax.text(i, row["Total Runs"] + 0.2, row["O/U Result"], color=color, ha="center", fontsize=9)
    ax.axhline(ou_line, color="gray", linestyle="--", label="O/U Line")
    ax.set_ylabel("Total Runs")
    ax.set_title(f"{team1} Last 10 Games")
    ax.legend()
    st.pyplot(fig)
else:
    st.info("No recent games found for this team.")
