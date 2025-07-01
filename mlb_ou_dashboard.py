import streamlit as st
import requests
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime

st.set_page_config(page_title="MLB O/U Tracker", layout="wide")
st.title("⚾ MLB Head-to-Head Over/Under Tracker (2025)")

# -----------------------------
# Get All MLB Teams (Dynamic)
# -----------------------------
@st.cache_data(ttl=86400)
def get_teams():
    url = "https://statsapi.mlb.com/api/v1/teams?sportId=1"
    res = requests.get(url).json()
    teams = {
        team["name"]: team["id"]
        for team in res["teams"] if team["sport"]["id"] == 1
    }
    return teams

# -----------------------------
# Get Matchup Results (2025)
# -----------------------------
@st.cache_data(ttl=1800)
def get_matchups(team1_id, team2_id, ou_line=8.5, max_games=15):
    url = f"https://statsapi.mlb.com/api/v1/schedule?sportId=1&season=2025&teamId={team1_id}&opponentId={team2_id}&gameType=R"
    res = requests.get(url).json()
    games = res.get('dates', [])
    results = []

    for g in games:
        game = g['games'][0]
        if game['status']['abstractGameState'] != "Final":
            continue

        game_id = game['gamePk']
        details = requests.get(f"https://statsapi.mlb.com/api/v1.1/game/{game_id}/feed/live").json()

        try:
            home = details['gameData']['teams']['home']['name']
            away = details['gameData']['teams']['away']['name']
            h_score = details['liveData']['linescore']['teams']['home']['runs']
            a_score = details['liveData']['linescore']['teams']['away']['runs']
            total = h_score + a_score
            date = details['gameData']['datetime']['originalDate']
            ou_result = "Over" if total > ou_line else "Under"
        except:
            continue

        results.append({
            "Date": date,
            "Home": home,
            "Away": away,
            "Final Score": f"{a_score}-{h_score}",
            "Total Runs": total,
            "O/U Line": ou_line,
            "O/U Result": ou_result
        })

        if len(results) >= max_games:
            break

    return pd.DataFrame(results)

# -----------------------------
# Heatmap Generator
# -----------------------------
@st.cache_data(ttl=1800)
def generate_heatmap_df(teams, ou_line=8.5):
    records = []
    for team1_name, team1_id in teams.items():
        for team2_name, team2_id in teams.items():
            if team1_name == team2_name:
                continue
            df = get_matchups(team1_id, team2_id, ou_line=ou_line, max_games=10)
            if not df.empty:
                pct_over = (df['O/U Result'] == "Over").mean()
                records.append([team1_name, team2_name, round(pct_over, 2)])

    return pd.DataFrame(records, columns=["Team 1", "Team 2", "% Over"])

# -----------------------------
# User Interface
# -----------------------------
teams = get_teams()
team_names = sorted(teams.keys())
col1, col2 = st.columns(2)
with col1:
    selected_team_1 = st.selectbox("Select Team 1", team_names)
with col2:
    selected_team_2 = st.selectbox("Select Team 2", team_names)

ou_line = st.slider("Set Over/Under Line", min_value=5.0, max_value=12.0, value=8.5, step=0.5)

if selected_team_1 == selected_team_2:
    st.warning("Select two different teams.")
else:
    df_results = get_matchups(
        teams[selected_team_1],
        teams[selected_team_2],
        ou_line=ou_line,
        max_games=15
    )

    if df_results.empty:
        st.error("No completed matchups found for 2025.")
    else:
        st.subheader(f"{selected_team_1} vs {selected_team_2} - Last {len(df_results)} Matchups")
        st.dataframe(df_results, use_container_width=True)

        pct = (df_results["O/U Result"] == "Over").mean() * 100
        st.markdown(f"📈 **{pct:.1f}%** of these games went Over {ou_line} runs.")

# -----------------------------
# Heatmap Display
# -----------------------------
st.header("🔥 League-Wide Over % Heatmap (Last 10 Matchups per Pair)")
if st.button("Generate Heatmap (Takes ~30s)"):
    heat_df = generate_heatmap_df(teams, ou_line=ou_line)
    pivot = heat_df.pivot(index="Team 1", columns="Team 2", values="% Over")

    fig, ax = plt.subplots(figsize=(14, 10))
    sns.heatmap(pivot, annot=True, fmt=".0%", cmap="coolwarm", ax=ax, linewidths=0.5)
    st.pyplot(fig)
