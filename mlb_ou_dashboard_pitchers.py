import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="MLB O/U Tracker - Pitcher Filters", layout="wide")
st.title("⚾ MLB Over/Under Tracker with Pitcher Filters (2025)")

SEASON = 2025
MLB_API_BASE = "https://statsapi.mlb.com/api/v1"

@st.cache_data(ttl=86400)
def get_teams():
    res = requests.get(f"{MLB_API_BASE}/teams?sportId=1").json()
    return {team["name"]: team["id"] for team in res["teams"] if team["sport"]["id"] == 1}

teams = get_teams()
team_names = sorted(teams.keys())

# ------------------------
# User Inputs
# ------------------------
col1, col2 = st.columns(2)
with col1:
    team1 = st.selectbox("Team 1", team_names, index=0)
with col2:
    team2 = st.selectbox("Team 2", team_names, index=1)

ou_line = st.slider("Set Over/Under Line", 5.0, 12.0, 8.5, 0.5)

st.markdown("### Optional Pitcher Filters")
pitcher_name = st.text_input("Filter by Pitcher Name (either team, optional):", "")
hand_filter = st.radio("Filter by Handedness", ["All", "RHP", "LHP"], index=0)
hand_side = st.radio("Apply Hand Filter to:", ["Team 1 only", "Team 2 only", "Both"], index=2)

# ------------------------
# Fetch Matchups with Starters
# ------------------------
@st.cache_data(ttl=1800)
def get_matchups(team1_id, team2_id, ou_line):
    url = f"{MLB_API_BASE}/schedule?sportId=1&season={SEASON}&teamId={team1_id}&opponentId={team2_id}&gameType=R"
    res = requests.get(url).json()
    games = res.get("dates", [])
    results = []

    for g in games:
        try:
            game = g["games"][0]
            if game["status"]["abstractGameState"] != "Final":
                continue

            game_id = game["gamePk"]
            boxscore = requests.get(f"{MLB_API_BASE}/game/{game_id}/boxscore").json()
            live = requests.get(f"{MLB_API_BASE}/game/{game_id}/feed/live").json()

            h_name = live["gameData"]["teams"]["home"]["name"]
            a_name = live["gameData"]["teams"]["away"]["name"]
            h_id = live["gameData"]["teams"]["home"]["id"]
            a_id = live["gameData"]["teams"]["away"]["id"]

            h_runs = live["liveData"]["linescore"]["teams"]["home"]["runs"]
            a_runs = live["liveData"]["linescore"]["teams"]["away"]["runs"]
            total = h_runs + a_runs
            date = live["gameData"]["datetime"]["originalDate"]
            ou_result = "Over" if total > ou_line else "Under"

            # Get starters
            starters = live["gameData"].get("probablePitchers", {})
            h_starter = starters.get("home", {}).get("fullName", "")
            a_starter = starters.get("away", {}).get("fullName", "")
            h_hand = starters.get("home", {}).get("pitchHand", {}).get("code", "")
            a_hand = starters.get("away", {}).get("pitchHand", {}).get("code", "")

            results.append({
                "Date": date,
                "Home": h_name,
                "Away": a_name,
                "Home Starter": f"{h_starter} ({h_hand})" if h_starter else "N/A",
                "Away Starter": f"{a_starter} ({a_hand})" if a_starter else "N/A",
                "Pitcher 1": h_starter,
                "Pitcher 2": a_starter,
                "Hand 1": h_hand,
                "Hand 2": a_hand,
                "Total Runs": total,
                "O/U Result": ou_result
            })

        except Exception as e:
            continue

    return pd.DataFrame(results)

# ------------------------
# Filter & Display Results
# ------------------------
if team1 == team2:
    st.warning("Please select two different teams.")
else:
    df = get_matchups(teams[team1], teams[team2], ou_line)

    if pitcher_name:
        df = df[df[["Pitcher 1", "Pitcher 2"]].apply(lambda row: pitcher_name.lower() in row[0].lower() or pitcher_name.lower() in row[1].lower(), axis=1)]

    if hand_filter != "All":
        if hand_side == "Team 1 only":
            df = df[df["Hand 1"] == hand_filter.lower()]
        elif hand_side == "Team 2 only":
            df = df[df["Hand 2"] == hand_filter.lower()]
        else:
            df = df[(df["Hand 1"] == hand_filter.lower()) & (df["Hand 2"] == hand_filter.lower())]

    if df.empty:
        st.warning("No results match your filters.")
    else:
        st.subheader(f"{team1} vs {team2} - {len(df)} Matchups")
        st.dataframe(df[["Date", "Home", "Away", "Home Starter", "Away Starter", "Total Runs", "O/U Result"]], use_container_width=True)

        over_pct = (df["O/U Result"] == "Over").mean() * 100
        st.markdown(f"📊 **{over_pct:.1f}%** of games went Over {ou_line}.")

        fig, ax = plt.subplots()
        ax.plot(df["Date"], df["Total Runs"], marker='o', label="Total Runs")
        ax.axhline(ou_line, color="gray", linestyle="--", label="O/U Line")
        ax.set_ylabel("Runs")
        ax.set_title("O/U Totals Over Time")
        ax.legend()
        st.pyplot(fig)
