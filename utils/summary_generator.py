import streamlit as st
import os
import json
from espn_api.football import League
from yfpy.query import YahooFantasySportsQuery
from sleeper_wrapper import League as SleeperLeague
from utils import espn_helper, yahoo_helper, sleeper_helper, helper
from openai import OpenAI
import datetime
from streamlit.logger import get_logger

LOGGER = get_logger(__name__)


# (Your other functions like moderate_text, generate_gpt4_summary_streaming, etc. remain here)
# ...


def generate_espn_summary(league, cw):
    """
    Generate a human-friendly summary based on the league stats with improved formatting.
    """
    # ... (all the helper function calls remain the same) ...
    top_teams = espn_helper.top_three_teams(league)
    top_scorer_week = espn_helper.top_scorer_of_week(league, cw)
    worst_scorer_week = espn_helper.worst_scorer_of_week(league, cw)
    top_scorer_szn = espn_helper.top_scorer_of_season(league)
    worst_scorer_szn = espn_helper.worst_scorer_of_season(league)
    most_trans = espn_helper.team_with_most_transactions(league)
    most_injured = espn_helper.team_with_most_injured_players(league)
    highest_bench = espn_helper.highest_scoring_benched_player(league, cw)
    lowest_start = espn_helper.lowest_scoring_starting_player(league, cw)
    biggest_blowout = espn_helper.biggest_blowout_match(league, cw)
    closest_game = espn_helper.closest_game_match(league, cw)
    top_scoring_team_Week = espn_helper.highest_scoring_team(league, cw)
    
    # --- FIX: Re-formatted with Markdown for better readability ---
    summary_parts = [
        f"### Weekly Standouts\n"
        f"**Top Scoring Team:** {top_scoring_team_Week}\n",
        
        f"**Top Player:** {top_scorer_week[0].name} with **{top_scorer_week[1]}** points.",
        f"**Lowest Scoring Starter:** {lowest_start[0].name} with just **{lowest_start[0].points}** points (Rostered by {espn_helper.clean_team_name(lowest_start[1].team_name)}).",
        f"**Best Bench Player:** {highest_bench[0].name} scored **{highest_bench[0].points}** points on the bench for {espn_helper.clean_team_name(highest_bench[1].team_name)}.",
        
        "\n---\n",  # Horizontal Line
        
        f"### Matchup Highlights\n"
        f"**Biggest Blowout:** {espn_helper.clean_team_name(biggest_blowout.home_team.team_name)} (**{biggest_blowout.home_score}**) vs {espn_helper.clean_team_name(biggest_blowout.away_team.team_name)} (**{biggest_blowout.away_score}**)\n",
        f"**Closest Game:** {espn_helper.clean_team_name(closest_game.home_team.team_name)} (**{closest_game.home_score}**) vs {espn_helper.clean_team_name(closest_game.away_team.team_name)} (**{closest_game.away_score}**)\n",

        "\n---\n",  # Horizontal Line

        f"### League Power Rankings\n"
        f"1. **{espn_helper.clean_team_name(top_teams[0].team_name)}**\n"
        f"2. **{espn_helper.clean_team_name(top_teams[1].team_name)}**\n"
        f"3. **{espn_helper.clean_team_name(top_teams[2].team_name)}**\n",

        "\n---\n",  # Horizontal Line

        f"### Season-Long Stats\n"
        f"**Season Top Scorer:** {top_scorer_szn[0].name} with **{top_scorer_szn[1]}** total points.\n",
        f"**Most Active Manager:** {espn_helper.clean_team_name(most_trans[0].team_name)} with **{most_trans[1]}** transactions.\n",
        f"**Most Injured Team:** {espn_helper.clean_team_name(most_injured[0].team_name)} with **{most_injured[1]}** injured players: {', '.join(most_injured[2])}."
    ]
    
    return "\n".join(summary_parts)


@st.cache_data(ttl=3600)
def generate_sleeper_summary(league_id):
    """Generates a human-friendly summary for a Sleeper league with improved formatting."""
    # ... (all the data fetching logic remains the same) ...
    league = SleeperLeague(league_id)
    week = helper.get_current_week(datetime.datetime.now()) - 1
    if week < 1: week = 1
    rosters = league.get_rosters()
    users = league.get_users()
    matchups = league.get_matchups(week)
    standings = league.get_standings(rosters, users)
    players_data = helper.load_player_data()
    user_team_mapping = league.map_users_to_team_name(users)
    roster_owner_mapping = league.map_rosterid_to_ownerid(rosters)
    scoreboards = sleeper_helper.calculate_scoreboards(matchups, user_team_mapping, roster_owner_mapping)

    # Generate individual summary components
    highest_scoring_team_name, highest_scoring_team_score = sleeper_helper.highest_scoring_team_of_week(scoreboards)
    top_3_teams_result = sleeper_helper.top_3_teams(standings)
    hs_player, hs_score, hs_team = sleeper_helper.highest_scoring_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
    ls_starter, ls_score, ls_team = sleeper_helper.lowest_scoring_starter_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
    hs_benched, hs_benched_score, hs_benched_team = sleeper_helper.highest_scoring_benched_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
    blowout_teams, blowout_diff = sleeper_helper.biggest_blowout_match_of_week(scoreboards)
    close_teams, close_diff = sleeper_helper.closest_match_of_week(scoreboards)
    hottest_team, streak = sleeper_helper.team_on_hottest_streak(rosters, user_team_mapping, roster_owner_mapping)

    # --- FIX: Re-formatted with Markdown for better readability ---
    summary_parts = [
        f"### Weekly Standouts\n",
        f"**Top Scoring Team:** {highest_scoring_team_name} with **{highest_scoring_team_score:.2f}** points.\n",
        f"**Top Player:** {hs_player} with **{hs_score:.2f}** points (Team: {hs_team}).\n",
        f"**Lowest Scoring Starter:** {ls_starter} with just **{ls_score:.2f}** points (Team: {ls_team}).\n",
        f"**Best Bench Player:** {hs_benched} scored **{hs_benched_score:.2f}** points on the bench for {hs_benched_team}.\n",
        
        "\n---\n",

        f"### Matchup Highlights\n",
        f"**Biggest Blowout:** {blowout_teams[0]} vs {blowout_teams[1]} (Point Differential: **{blowout_diff:.2f}**).\n",
        f"**Closest Game:** {close_teams[0]} vs {close_teams[1]} (Point Differential: **{close_diff:.2f}**).\n",

        "\n---\n",

        f"### League Power Rankings\n",
        f"1. **{top_3_teams_result[0][0]}** ({top_3_teams_result[0][1]}W-{top_3_teams_result[0][2]}L) - {float(top_3_teams_result[0][3]):.2f} total points\n",
        f"2. **{top_3_teams_result[1][0]}** ({top_3_teams_result[1][1]}W-{top_3_teams_result[1][2]}L) - {float(top_3_teams_result[1][3]):.2f} total points\n",
        f"3. **{top_3_teams_result[2][0]}** ({top_3_teams_result[2][1]}W-{top_3_teams_result[2][2]}L) - {float(top_3_teams_result[2][3]):.2f} total points\n",

        "\n---\n",

        f"### Team Streaks\n",
        f"**Hottest Team:** {hottest_team} is on a **{streak}** game win streak."
    ]
    
    summary = "\n".join(summary_parts)
    LOGGER.info(f"Sleeper Summary Generated: \n{summary}")

    return summary

# (The rest of your file remains unchanged)
