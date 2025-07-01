import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

st.set_page_config(page_title="MLB O/U Tracker - Pitcher Filters", layout="wide")
st.title("⚾ MLB O/U Tracker with Starting Pitcher Filters (2025)")

SEASON = 2025
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

# -------------------------
# Load Team List
# -------------------------
@st.cache_data(ttl=86400)
def get_teams():
    res = requests.get(f"{MLB_API_BASE}/teams?sportId=1").json()
    return {team["name"]: team["id"] for team in res["teams"] if team["sport"]["id"] == 1}

teams = get_teams()
team_names = sorted(teams.keys())

# -------------------------
# UI Inputs
# -------------------------
col1, col2 = st.columns(2)
with col1:
    team1 = st.selectbox("Team 1", team_names, index=0)
with col2:
    team2 = st.selectbox("Team 2", team_names, index=1)

st.markdown("### Optional Pitcher Filter")

filter_pitcher = st.text_input("Filter by Pitcher Name (Optional)", "")
filter_handedness = st.radio("Filter by Opposing Pitcher Handedness", ["All", "RHP", "LHP"], index=0)

ou_line = st.slider("Set Over/Under Line", 5.0, 12.0, 8.5, 0.5)

# -------------------------
# Game + Pitcher Fetcher
# -------------------------
@st.cache_data(ttl=3600)
def get_matchups_with_pitchers(team1_id, team2_id, ou_line):
    url = f"{MLB_API_BASE}/schedule?sportId=1&season={SEASON}&teamId={team1_id}&opponentId={team2_id}&gameType=R"
    res = requests.get(url).json()
    games = res.get("dates", [])
    matchups = []

    for g in games:
        try:
            game = g["games"][0]
            if game["status"]["abstractGameState"] != "Final":
                continue

            game_id = game["gamePk"]
            feed = requests.get(f"{MLB_API_BASE}/game/{game_id}/boxscore").json()
            live = requests.get(f"{MLB_API_BASE}/v1.1/game/{game_id}/feed/live").json()

            h_name = live["gameData"]["teams"]["home"]["name"]
            a_name = live["gameData"]["teams"]["away"]["name"]
            h_id = live["gameData"]["teams"]["home"]["id"]
            a_id = live["gameData"]["teams"]["away"]["id"]

            h_runs = live["liveData"]["linescore"]["teams"]["home"]["runs"]
            a_runs = live["liveData"]["linescore"]["teams"]["away"]["runs"]
            total = h_runs + a_runs

            date = live["gameData"]["datetime"]["originalDate"]
            ou_result = "Over" if total > ou_line else "Under"

            h_pitcher = feed["teams"]["home"]["pitchers"][0]
            a_pitcher = feed["teams"]["away"]["pitchers"][0]

            h_info = feed["players"][f"ID{h_pitcher}"]
            a_info = feed["players"][f"ID{a_pitcher}"]

            matchups.append({
                "Date": date,
                "Home": h_name,
                "Away": a_name,
                "Home Starter": f"{h_info['fullName']} ({h_info.get('pitchHand', {}).get('code', '')})",
                "Away Starter": f"{a_info['fullName']} ({a_info.get('pitchHand', {}).get('code', '')})",
                "Total Runs": total,
                "O/U Result": ou_result,
                "Pitchers": [h_info["fullName"], a_info["fullName"]],
                "Hands": [h_info.get("pitchHand", {}).get("code", ""), a_info.get("pitchHand", {}).get("code", "")]
            })

        except:
            continue

    return pd.DataFrame(matchups)

# -------------------------
# Filtered Data Display
# -------------------------
if team1 == team2:
    st.warning("Please select two different teams.")
else:
    df = get_matchups_with_pitchers(teams[team1], teams[team2], ou_line)

    # Apply pitcher filter
    if filter_pitcher:
        df = df[df["Pitchers"].apply(lambda p: any(filter_pitcher.lower() in name.lower() for name in p))]

    if filter_handedness != "All":
        df = df[df["Hands"].apply(lambda h: filter_handedness.lower() in [hand.lower() for hand in h])]

    if df.empty:
        st.warning("No results found for this matchup and filter.")
    else:
        st.subheader(f"Matchups ({len(df)} games)")
        st.dataframe(df[["Date", "Home", "Away", "Home Starter", "Away Starter", "Total Runs", "O/U Result"]], use_container_width=True)

        over_pct = (df["O/U Result"] == "Over").mean() * 100
        st.markdown(f"📊 **{over_pct:.1f}%** of filtered games went Over {ou_line}.")

        # Plot
        fig, ax = plt.subplots()
        ax.plot(df["Date"], df["Total Runs"], marker='o', label="Total Runs")
        ax.axhline(ou_line, color="gray", linestyle="--", label="O/U Line")
        ax.set_title("Total Runs Over Time")
        ax.set_ylabel("Runs")
        ax.legend()
        st.pyplot(fig)
