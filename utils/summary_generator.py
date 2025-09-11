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

def moderate_text(client, text):
    try:
        # Send the moderation request
        response = client.moderations.create(
            input=text,
            model="text-moderation-latest"  # Use the latest moderation model
        )

        # Extract the first result
        result = response.results[0]

        # Check if the content is flagged
        if result.flagged:
            # Log the flagged categories
            flagged_categories = [
                category for category, flagged in result.categories.items() if flagged
            ]
            LOGGER.warning(
                "Moderation flagged the following categories: %s",
                ", ".join(flagged_categories),
            )
            return False  # Return False if any category is flagged
        return True  # Content is not flagged, return True

    except Exception as e:
        LOGGER.error("An error occurred during moderation: %s", str(e))
        return False  # Assume text is inappropriate in case of an error

def generate_gpt4_summary_streaming(client, summary, character_choice, trash_talk_level):
    # Construct the instruction for GPT-4 based on user inputs
    instruction = f"You will be provided a summary below containing the most recent weekly stats for a fantasy football league. \
    Create a weekly recap in the style of {character_choice}. Do not simply repeat every single stat verbatim - be creative while calling out stats and being on theme. You should include trash talk with a level of {trash_talk_level} based on a scale of 1-10 (1 being no trash talk, 10 being excessive hardcore trash talk); feel free to make fun of (or praise) team names and performances, and add a touch of humor related to the chosen character. \
    Keep your summary concise enough (under 800 characters) as to not overwhelm the user with stats but still engaging, funny, thematic, and insightful. You can sprinkle in a few emojis if they are thematic. Only respond in character and do not reply with anything other than your recap. Begin by introducing \
    your character. Here is the provided weekly fantasy summary: {summary}"

    # Create the messages array
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": instruction}
    ]

    try:
        # Send the messages to OpenAI's GPT-4 for analysis
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # Use the appropriate model
            messages=messages,
            max_tokens=1600,  # Control response length
            stream=True
        )
        
        # Extract and yield the GPT-4 generated message
        for chunk in response:
            # Access 'content' directly since 'delta' is an object, not a dictionary
            if hasattr(chunk.choices[0].delta, 'content'):
                yield chunk.choices[0].delta.content

    except Exception as e:
        yield f"Error details: {e}"

def generate_espn_summary(league, cw):
    """
    Generate a human-friendly summary for an ESPN league with improved formatting.
    """
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
    
    summary_parts = [
        f"### Weekly Standouts\n",
        f"**Top Scoring Team:** {top_scoring_team_Week}\n",
        f"**Top Player:** {top_scorer_week[0].name} with **{top_scorer_week[1]}** points.",
        f"**Lowest Scoring Starter:** {lowest_start[0].name} with just **{lowest_start[0].points}** points (Rostered by {espn_helper.clean_team_name(lowest_start[1].team_name)}).",
        f"**Best Bench Player:** {highest_bench[0].name} scored **{highest_bench[0].points}** points on the bench for {espn_helper.clean_team_name(highest_bench[1].team_name)}.",
        "\n---\n",
        f"### Matchup Highlights\n",
        f"**Biggest Blowout:** {espn_helper.clean_team_name(biggest_blowout.home_team.team_name)} (**{biggest_blowout.home_score}**) vs {espn_helper.clean_team_name(biggest_blowout.away_team.team_name)} (**{biggest_blowout.away_score}**)\n",
        f"**Closest Game:** {espn_helper.clean_team_name(closest_game.home_team.team_name)} (**{closest_game.home_score}**) vs {espn_helper.clean_team_name(closest_game.away_team.team_name)} (**{closest_game.away_score}**)\n",
        "\n---\n",
        f"### League Power Rankings\n",
        f"1. **{espn_helper.clean_team_name(top_teams[0].team_name)}**\n",
        f"2. **{espn_helper.clean_team_name(top_teams[1].team_name)}**\n",
        f"3. **{espn_helper.clean_team_name(top_teams[2].team_name)}**\n",
        "\n---\n",
        f"### Season-Long Stats\n",
        f"**Season Top Scorer:** {top_scorer_szn[0].name} with **{top_scorer_szn[1]}** total points.\n",
        f"**Most Active Manager:** {espn_helper.clean_team_name(most_trans[0].team_name)} with **{most_trans[1]}** transactions.\n",
        f"**Most Injured Team:** {espn_helper.clean_team_name(most_injured[0].team_name)} with **{most_injured[1]}** injured players: {', '.join(most_injured[2])}."
    ]
    return "\n".join(summary_parts)

@st.cache_data(ttl=3600)
def get_espn_league_summary(league_id, espn2, SWID):
    # Fetch data from ESPN Fantasy API and compute statistics   
    start_time_league_connect = datetime.datetime.now() 
    league_id = league_id
    year = helper.get_nfl_season_year(datetime.datetime.now())  # Dynamic year
    espn_s2 = espn2
    swid = SWID
    # Initialize league & current week
    try:
        league = League(league_id=league_id, year=year, espn_s2=espn_s2, swid=swid)
    except Exception as e:
        return str(e), "Error occurred during validation"
    end_time_league_connect = datetime.datetime.now()
    league_connect_duration = (end_time_league_connect - start_time_league_connect).total_seconds()
    
    # Use dynamic week calculation
    cw = helper.get_most_recent_completed_week(datetime.datetime.now())
    
    # Generate summary
    start_time_summary = datetime.datetime.now()
    summary = generate_espn_summary(league, cw)
    end_time_summary = datetime.datetime.now()
    summary_duration = (end_time_summary - start_time_summary).total_seconds()
    # Generate debugging information
    debug_info = f"Summary: {summary} ~~~Timings~~~ League Connect Duration: {league_connect_duration} seconds Summary Duration: {summary_duration} seconds Current Week: {cw} Season Year: {year}"
    return summary, debug_info

@st.cache_data(ttl=3600)
def get_yahoo_league_summary(league_id, auth_path):    
    league_id = league_id
    LOGGER.info(f"League id: {league_id}")
    auth_directory = auth_path
    sc = YahooFantasySportsQuery(
        auth_dir=auth_directory,
        league_id=league_id,
        game_code="nfl"
    )
    LOGGER.info(f"sc: {sc}")
    # Use dynamic week calculation instead of hardcoded
    week = helper.get_most_recent_completed_week(datetime.datetime.now())
    recap = yahoo_helper.generate_weekly_recap(sc, week=week)
    return recap

@st.cache_data(ttl=3600)
def generate_sleeper_summary(league_id):
    """Generates a human-friendly summary for a Sleeper league with improved formatting."""
    league = SleeperLeague(league_id)
    
    # Use the dynamic week calculation
    week = helper.get_most_recent_completed_week(datetime.datetime.now())
    current_nfl_week = helper.get_current_week(datetime.datetime.now())
    
    LOGGER.info(f"Current NFL week: {current_nfl_week}, Using completed week: {week} for data")

    rosters = league.get_rosters()
    users = league.get_users()
    matchups = league.get_matchups(week)
    standings = league.get_standings(rosters, users)

    # Load player data directly from the local file
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        players_file_path = os.path.join(project_root, 'players_data.json')
        with open(players_file_path, 'r') as f:
            players_data = json.load(f)
        LOGGER.info(f"Loaded {len(players_data)} players from data file")
    except FileNotFoundError:
        st.error(f"Player data file ('players_data.json') not found at: {players_file_path}.")
        return "Player data not found."

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

    # Format summary with Markdown for better readability
    summary_parts = [
        f"### Weekly Standouts (Week {week})\n",
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
    LOGGER.info(f"Sleeper Summary Generated for Week {week}: \n{summary}")

    return summary
