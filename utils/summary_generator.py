import streamlit as st
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
        response = client.moderations.create(input=text, model="text-moderation-latest")
        result = response.results[0]
        if result.flagged:
            flagged_categories = [category for category, flagged in result.categories.items() if flagged]
            LOGGER.warning("Moderation flagged the following categories: %s", ", ".join(flagged_categories))
            return False
        return True
    except Exception as e:
        LOGGER.error("An error occurred during moderation: %s", str(e))
        return False

def generate_gpt4_summary_streaming(client, summary, character_choice, trash_talk_level):
    instruction = (
        f"You will be provided a summary below containing the most recent weekly stats for a fantasy football league. "
        f"Create a weekly recap in the style of {character_choice}. Do not simply repeat every single stat verbatim - be creative while calling out stats and being on theme. "
        f"You should include trash talk with a level of {trash_talk_level} based on a scale of 1-10 (1 being no trash talk, 10 being excessive hardcore trash talk); "
        f"feel free to make fun of (or praise) team names and performances, and add a touch of humor related to the chosen character. "
        f"Keep your summary concise enough (under 800 characters) as to not overwhelm the user with stats but still engaging, funny, thematic, and insightful. "
        f"You can sprinkle in a few emojis if they are thematic. Only respond in character and do not reply with anything other than your recap. Begin by introducing "
        f"your character. Here is the provided weekly fantasy summary: {summary}"
    )
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": instruction}
    ]
    try:
        response = client.chat.completions.create(model="gpt-4o-mini", messages=messages, max_tokens=1600, stream=True)
        for chunk in response:
            if hasattr(chunk.choices[0].delta, 'content'):
                yield chunk.choices[0].delta.content
    except Exception as e:
        yield f"Error details: {e}"

def generate_espn_summary(league, cw):
    # (This function appears correct, no changes made)
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
        f"- Top scoring fantasy team this week: {top_scoring_team_Week}",
        f"- Top 3 fantasy teams: {espn_helper.clean_team_name(top_teams[0].team_name)}, {espn_helper.clean_team_name(top_teams[1].team_name)}, {espn_helper.clean_team_name(top_teams[2].team_name)}",
        f"- Top scoring NFL player of the week: {top_scorer_week[0].name} with {top_scorer_week[1]} points.",
        f"- Worst scoring NFL player of the week: {worst_scorer_week[0].name} with {worst_scorer_week[1]} points.",
        f"- Top scoring NFL player of the season: {top_scorer_szn[0].name} with {top_scorer_szn[1]} points.",
        f"- Worst scoring NFL player of the season: {worst_scorer_szn[0].name} with {worst_scorer_szn[1]} points.",
        f"- Fantasy Team with the most transactions: {espn_helper.clean_team_name(most_trans[0].team_name)} ({most_trans[1]} transactions)",
        f"- Fantasy Team with the most injured players: {espn_helper.clean_team_name(most_injured[0].team_name)} ({most_injured[1]} players: {', '.join(most_injured[2])})",
        f"- Highest scoring benched player: {highest_bench[0].name} with {highest_bench[0].points} points (Rostered by {espn_helper.clean_team_name(highest_bench[1].team_name)})",
        f"- Lowest scoring starting player of the week: {lowest_start[0].name} with {lowest_start[0].points} points (Rostered by {espn_helper.clean_team_name(lowest_start[1].team_name)})",
        f"- Biggest blowout match of the week: {espn_helper.clean_team_name(biggest_blowout.home_team.team_name)} ({biggest_blowout.home_score} points) vs {espn_helper.clean_team_name(biggest_blowout.away_team.team_name)} ({biggest_blowout.away_score} points)",
        f"- Closest game of the week: {espn_helper.clean_team_name(closest_game.home_team.team_name)} ({closest_game.home_score} points) vs {espn_helper.clean_team_name(closest_game.away_team.team_name)} ({closest_game.away_score} points)"
    ]
    return "\n".join(summary_parts)

@st.cache_data(ttl=3600)
def get_espn_league_summary(league_id, espn2, SWID):
    try:
        league = League(league_id=league_id, year=2024, espn_s2=espn2, swid=SWID)
        cw = league.current_week - 1
        summary = generate_espn_summary(league, cw)
        return summary, "Debug info placeholder"
    except Exception as e:
        return str(e), "Error occurred during validation"

@st.cache_data(ttl=3600)
def get_yahoo_league_summary(league_id, auth_path):    
    sc = YahooFantasySportsQuery(auth_dir=auth_path, league_id=league_id, game_code="nfl")
    mrw = yahoo_helper.get_most_recent_week(sc)
    recap = yahoo_helper.generate_weekly_recap(sc, week=mrw)
    return recap

@st.cache_data(ttl=3600)
def generate_sleeper_summary(league_id):
    """Generates a human-friendly summary for a Sleeper league."""
    league = SleeperLeague(league_id)
    week = helper.get_current_week(datetime.datetime.now())
    rosters = league.get_rosters()
    users = league.get_users()
    matchups = league.get_matchups(week)
    standings = league.get_standings(rosters, users)

    players_url = "https://raw.githubusercontent.com/jeisey/commish/main/players_data.json"
    players_data = sleeper_helper.load_player_data(players_url)

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

    # Construct the summary string using a list for better readability
    summary_parts = [
        f"The highest scoring team of the week: {highest_scoring_team_name} with {round(highest_scoring_team_score, 2)} points.",
        "Standings; Top 3 Teams:",
        f"  1. {top_3_teams_result[0][0]} - {top_3_teams_result[0][3]} points ({top_3_teams_result[0][1]}W-{top_3_teams_result[0][2]}L)",
        f"  2. {top_3_teams_result[1][0]} - {top_3_teams_result[1][3]} points ({top_3_teams_result[1][1]}W-{top_3_teams_result[1][2]}L)",
        f"  3. {top_3_teams_result[2][0]} - {top_3_teams_result[2][3]} points ({top_3_teams_result[2][1]}W-{top_3_teams_result[2][2]}L)",
        f"Highest scoring player of the week: {hs_player} with {hs_score} points (Team: {hs_team}).",
        f"Lowest scoring player of the week that started: {ls_starter} with {ls_score} points (Team: {ls_team}).",
        f"Highest scoring benched player of the week: {hs_benched} with {hs_benched_score} points (Team: {hs_benched_team}).",
        f"Biggest blowout match of the week: {blowout_teams[0]} vs {blowout_teams[1]} (Point Differential: {round(blowout_diff, 2)}).",
        f"Closest match of the week: {close_teams[0]} vs {close_teams[1]} (Point Differential: {round(close_diff, 2)}).",
        f"Team on the hottest streak: {hottest_team} with a {streak} game win streak."
    ]
    
    summary = "\n".join(summary_parts)
    LOGGER.info(f"Sleeper Summary Generated: \n{summary}")

    return summary
