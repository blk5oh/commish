import streamlit as st
import os
import json
from sleeper_wrapper import League
from utils.sleeper_helper import (
    get_weekly_stats,
    calculate_player_points,
    highest_scoring_player_of_week,
    lowest_scoring_starter_of_week,
    highest_scoring_benched_player_of_week,
    biggest_blowout_match_of_week,
    closest_match_of_week,
    get_team_on_hottest_streak,
    get_top_3_teams,
    highest_scoring_team_of_week
)
from datetime import datetime
import logging

# Configure logging to show up in the console
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s.%(funcName)s] %(message)s')
logger = logging.getLogger(__name__)

def generate_sleeper_summary(league_id, week=None):
    """Generates the weekly summary for a Sleeper league."""
    try:
        # --- BOLD STEP: For debugging, we will FORCE the script to look at Week 1 ---
        week = 1 
        # --- Once this works, you can remove this line to go back to dynamic week calculation ---

        league = League(league_id)
        league_info = league.get_league()
        season = league_info.get("season")

        if not season:
            st.error("Could not determine the season for this league.")
            return "Error: League season not found.", None

        users = league.get_users()
        rosters = league.get_rosters()
        matchups = league.get_matchups(week)
        standings = league.get_standings(rosters, users)
        scoring_settings = league_info.get("scoring_settings")

        logger.info(f"--- DEBUGGING ---")
        logger.info(f"Analyzing League: {league_info.get('name')} for Season: {season}, Week: {week}")
        logger.info(f"LEAGUE SCORING SETTINGS: {json.dumps(scoring_settings, indent=2)}")
        
    except Exception as e:
        logger.error(f"Error during initial data fetch: {e}", exc_info=True)
        st.error(f"Failed to fetch initial data from Sleeper. Please check the League ID ({league_id}). Error: {e}")
        return None, None

    if not matchups:
        st.warning(f"No matchup data found for week {week} of the {season} season.")
        return f"No matchup data available for week {week}.", None

    user_team_mapping = {user['user_id']: user.get('metadata', {}).get('team_name') or user['display_name'] for user in users}
    roster_owner_mapping = {roster['roster_id']: roster['owner_id'] for roster in rosters}

    weekly_stats = get_weekly_stats(week, season)
    if not weekly_stats:
        st.warning(f"CRITICAL: Could not fetch any player stats for week {week}, season {season}.")
        return "Could not fetch player stats.", None
    
    # Log stats for the very first player we find to see what the data looks like
    first_player_with_stats_id = next(iter(weekly_stats), None)
    if first_player_with_stats_id:
        logger.info(f"SAMPLE PLAYER STATS (Player ID {first_player_with_stats_id}): {json.dumps(weekly_stats[first_player_with_stats_id], indent=2)}")

    for matchup in matchups:
        calculated_players_points = {}
        total_team_points = 0.0
        for player_id_str in matchup.get("players", []):
            player_stats = weekly_stats.get(player_id_str, {})
            points = calculate_player_points(player_id_str, player_stats, scoring_settings)
            calculated_players_points[player_id_str] = round(points, 2)
            if player_id_str in matchup.get("starters", []):
                total_team_points += points
        matchup['players_points'] = calculated_players_points
        matchup['points'] = round(total_team_points, 2)

    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        players_file_path = os.path.join(project_root, 'players_data.json')
        with open(players_file_path, 'r') as f:
            players_data = json.load(f)
    except FileNotFoundError:
        st.error(f"Player data file ('players_data.json') not found at: {players_file_path}.")
        return "Player data not found.", None

    # Generate summary components
    highest_score_team_name, highest_score = highest_scoring_team_of_week(matchups, user_team_mapping, roster_owner_mapping)
    top_3_teams_summary = get_top_3_teams(standings)
    hs_player, hs_score, hs_team = highest_scoring_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
    ls_starter, ls_score, ls_team = lowest_scoring_starter_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
    hs_benched, hs_benched_score, hs_benched_team = highest_scoring_benched_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
    (b_t1, b_t2), b_diff = biggest_blowout_match_of_week(matchups, user_team_mapping, roster_owner_mapping)
    (c_t1, c_t2), c_diff = closest_match_of_week(matchups, user_team_mapping, roster_owner_mapping)
    hottest_team, streak = get_team_on_hottest_streak(rosters, user_team_mapping)

    summary_parts = [
        f"The highest scoring team of the week: {highest_score_team_name} with {highest_score:.2f} points.",
        f"Standings; Top 3 Teams:\n{top_3_teams_summary}",
        f"Highest scoring player of the week: {hs_player} with {hs_score:.2f} points (Team: {hs_team}).",
        f"Lowest scoring player of the week that started: {ls_starter} with {ls_score:.2f} points (Team: {ls_team}).",
        f"Highest scoring benched player of the week: {hs_benched} with {hs_benched_score:.2f} points (Team: {hs_benched_team}).",
        f"Biggest blowout match of the week: {b_t1[0]} ({b_t1[1]:.2f}) vs {b_t2[0]} ({b_t2[1]:.2f}) (Point Differential: {b_diff:.2f}).",
        f"Closest match of the week: {c_t1[0]} ({c_t1[1]:.2f}) vs {c_t2[0]} ({c_t2[1]:.2f}) (Point Differential: {c_diff:.2f}).",
        f"Team on the hottest streak: {hottest_team} with a {streak} game win streak."
    ]
    
    full_summary = "\n".join(summary_parts)
    logger.info(f"--- FINAL SUMMARY ---:\n{full_summary}")
    
    return full_summary, matchups
