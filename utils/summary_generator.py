import streamlit as st
from espn_api.football import League
from yfpy.query import YahooFantasySportsQuery
from sleeper_wrapper import League as SleeperLeague
from utils import espn_helper, yahoo_helper, sleeper_helper, helper
from openai import OpenAI
import datetime
import json
from streamlit.logger import get_logger

LOGGER = get_logger(__name__)

# (Your other functions like moderate_text, generate_gpt4_summary_streaming, etc. remain here)
# ...

@st.cache_data(ttl=3600)
def generate_sleeper_summary(league_id):
    """Generates a human-friendly summary for a Sleeper league."""
    league = SleeperLeague(league_id)
    week = helper.get_current_week(datetime.datetime.now()) - 1
    if week < 1:
        week = 1
        
    rosters = league.get_rosters()
    users = league.get_users()
    matchups = league.get_matchups(week)
    standings = league.get_standings(rosters, users)

    # --- FIX: Load player data directly instead of from a helper function ---
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        players_file_path = os.path.join(project_root, 'players_data.json')
        with open(players_file_path, 'r') as f:
            players_data = json.load(f)
    except FileNotFoundError:
        st.error(f"Player data file ('players_data.json') not found at: {players_file_path}.")
        return "Player data not found.", None

    # Create a reliable mapping from roster_id to team name
    user_id_to_display_name = {user['user_id']: user.get('metadata', {}).get('team_name') or user['display_name'] for user in users}
    roster_id_to_team_name_map = {
        roster['roster_id']: user_id_to_display_name.get(roster['owner_id'], 'Unknown Team')
        for roster in rosters
    }
    
    # Generate scoreboards for the week
    scoreboards = sleeper_helper.calculate_scoreboards(matchups, roster_id_to_team_name_map)

    # Generate individual summary components
    highest_scoring_team_name, highest_scoring_team_score = sleeper_helper.highest_scoring_team_of_week(scoreboards)
    top_3_teams_result = sleeper_helper.top_3_teams(standings)
    hs_player, hs_score, hs_team = sleeper_helper.highest_scoring_player_of_week(matchups, players_data, roster_id_to_team_name_map)
    ls_starter, ls_score, ls_team = sleeper_helper.lowest_scoring_starter_of_week(matchups, players_data, roster_id_to_team_name_map)
    hs_benched, hs_benched_score, hs_benched_team = sleeper_helper.highest_scoring_benched_player_of_week(matchups, players_data, roster_id_to_team_name_map)
    blowout_teams, blowout_diff = sleeper_helper.biggest_blowout_match_of_week(scoreboards)
    close_teams, close_diff = sleeper_helper.closest_match_of_week(scoreboards)
    hottest_team, streak = sleeper_helper.team_on_hottest_streak(rosters, roster_id_to_team_name_map)

    # Construct the summary string using a list for better readability
    summary_parts = [
        f"The highest scoring team of the week: {highest_scoring_team_name} with {round(highest_scoring_team_score, 2)} points.",
        "Standings; Top 3 Teams:",
        f"  1. {top_3_teams_result[0][0]} - {float(top_3_teams_result[0][3]):.2f} points ({top_3_teams_result[0][1]}W-{top_3_teams_result[0][2]}L)",
        f"  2. {top_3_teams_result[1][0]} - {float(top_3_teams_result[1][3]):.2f} points ({top_3_teams_result[1][1]}W-{top_3_teams_result[1][2]}L)",
        f"  3. {top_3_teams_result[2][0]} - {float(top_3_teams_result[2][3]):.2f} points ({top_3_teams_result[2][1]}W-{top_3_teams_result[2][2]}L)",
        f"Highest scoring player of the week: {hs_player} with {hs_score:.2f} points (Team: {hs_team}).",
        f"Lowest scoring player of the week that started: {ls_starter} with {ls_score:.2f} points (Team: {ls_team}).",
        f"Highest scoring benched player of the week: {hs_benched} with {hs_benched_score:.2f} points (Team: {hs_benched_team}).",
        f"Biggest blowout match of the week: {blowout_teams[0]} vs {blowout_teams[1]} (Point Differential: {round(blowout_diff, 2)}).",
        f"Closest match of the week: {close_teams[0]} vs {close_teams[1]} (Point Differential: {round(close_diff, 2)}).",
        f"Team on the hottest streak: {hottest_team} with a {streak} game win streak."
    ]
    
    summary = "\n".join(summary_parts)
    LOGGER.info(f"Sleeper Summary Generated: \n{summary}")

    return summary
