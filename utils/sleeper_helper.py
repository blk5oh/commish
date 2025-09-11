import json
import os
import requests
import logging

logger = logging.getLogger(__name__)

# ##################################################################
# STAT MAPPING DICTIONARY
# ##################################################################
# This is the most critical part. It translates API stat names to your league's setting names.
# This list has been expanded to include many common scoring settings.
STAT_MAPPING = {
    # Passing
    'pass_yd': 'pass_yd',
    'pass_td': 'pass_td',
    'pass_int': 'pass_int',
    'pass_2pt': 'pass_2pt',
    # Rushing
    'rush_yd': 'rush_yd',
    'rush_td': 'rush_td',
    'rush_2pt': 'rush_2pt',
    # Receiving
    'rec': 'rec',
    'rec_yd': 'rec_yd',
    'rec_td': 'rec_td',
    'rec_2pt': 'rec_2pt',
    # Miscellaneous Offense
    'fum_lost': 'fum_lost',
    'fum_rec_td': 'fum_rec_td',
    'st_td': 'st_td',
    # Kicking
    'fgm': 'fgm', 'fga': 'fga',
    'xpm': 'xpm', 'xpa': 'xpa',
    'fgm_0_19': 'fgm_0_19', 'fgm_20_29': 'fgm_20_29',
    'fgm_30_39': 'fgm_30_39', 'fgm_40_49': 'fgm_40_49',
    'fgm_50p': 'fgm_50p',
    # Defense/Special Teams
    'def_sack': 'sack',
    'def_int': 'int',
    'def_fum_rec': 'fum_rec',
    'def_td': 'def_td',
    'def_st_td': 'st_td',
    'def_safety': 'safe',
    'pts_allow_0': 'pts_allow_0',
    'pts_allow_1_6': 'pts_allow_1_6',
    'pts_allow_7_13': 'pts_allow_7_13',
    'pts_allow_14_20': 'pts_allow_14_20',
    'pts_allow_21_27': 'pts_allow_21_27',
    'pts_allow_28_34': 'pts_allow_28_34',
    'pts_allow_35p': 'pts_allow_35p',
}

# ##################################################################
# HELPER FUNCTIONS
# ##################################################################

def get_weekly_stats(week, season="2024"):
    """Fetches weekly stats for all players from the Sleeper API for a given season."""
    try:
        url = f"https://api.sleeper.app/v1/stats/nfl/regular/{season}/{week}"
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching weekly stats: {e}")
        return {}

def calculate_player_points(player_id, player_stats, scoring_settings):
    """Calculates fantasy points based on player stats and league scoring settings."""
    if not player_stats or not scoring_settings:
        return 0.0
    
    total_points = 0.0
    calculation_log = []

    # Use the STAT_MAPPING to correctly calculate points
    for api_stat_name, setting_stat_name in STAT_MAPPING.items():
        if api_stat_name in player_stats and setting_stat_name in scoring_settings:
            value = player_stats[api_stat_name]
            score_per_stat = scoring_settings[setting_stat_name]
            points_for_stat = value * score_per_stat
            total_points += points_for_stat
            if points_for_stat != 0:
                 calculation_log.append(f"  - {api_stat_name}: {value} * {score_per_stat} = {points_for_stat:.2f} pts")

    if calculation_log:
        logger.info(f"Point calculation for Player ID {player_id}:\n" + "\n".join(calculation_log) + f"\n  - TOTAL: {total_points:.2f}")

    return total_points

def get_player_name_from_id(player_id, players_data):
    """Gets a player's name from their ID."""
    player_info = players_data.get(str(player_id))
    if player_info:
        return f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()
    return "Unknown Player"

# (The rest of the functions: highest_scoring_team_of_week, get_top_3_teams, etc. remain the same)
def highest_scoring_team_of_week(matchups, user_team_mapping, roster_owner_mapping):
    highest_score = -1
    highest_scoring_team_name = "Unknown"
    for matchup in matchups:
        owner_id = roster_owner_mapping.get(matchup['roster_id'])
        team_name = user_team_mapping.get(owner_id, "Unknown Team")
        score = matchup.get('points', 0)
        if score > highest_score:
            highest_score = score
            highest_scoring_team_name = team_name
    return highest_scoring_team_name, highest_score

def get_top_3_teams(standings):
    summary = []
    for i, team in enumerate(standings[:3]):
        team_name, wins, losses, points = team
        summary.append(f"  {i+1}. {team_name} - {points} points ({wins}W-{losses}L)")
    return "\n".join(summary)

def highest_scoring_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping):
    highest_score = -1
    highest_scoring_player = "N/A"
    highest_scoring_player_team = "N/A"
    for matchup in matchups:
        owner_id = roster_owner_mapping.get(matchup['roster_id'])
        team_name = user_team_mapping.get(owner_id, "Unknown Team")
        players_points = matchup.get('players_points', {})
        for player_id, score in players_points.items():
            if score > highest_score:
                highest_score = score
                highest_scoring_player = get_player_name_from_id(player_id, players_data)
                highest_scoring_player_team = team_name
    return highest_scoring_player, highest_score, highest_scoring_player_team

def lowest_scoring_starter_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping):
    lowest_score = float('inf')
    lowest_scoring_player = "N/A"
    lowest_scoring_player_team = "N/A"
    for matchup in matchups:
        owner_id = roster_owner_mapping.get(matchup['roster_id'])
        team_name = user_team_mapping.get(owner_id, "Unknown Team")
        players_points = matchup.get('players_points', {})
        starters = matchup.get('starters', [])
        for player_id in starters:
            score = players_points.get(str(player_id), 0)
            if score < lowest_score:
                lowest_score = score
                lowest_scoring_player = get_player_name_from_id(player_id, players_data)
                lowest_scoring_player_team = team_name
    return lowest_scoring_player, lowest_score, lowest_scoring_player_team

def highest_scoring_benched_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping):
    highest_benched_score = -1
    highest_benched_player = "N/A"
    highest_benched_player_team = "N/A"
    for matchup in matchups:
        owner_id = roster_owner_mapping.get(matchup['roster_id'])
        team_name = user_team_mapping.get(owner_id, "Unknown Team")
        players_points = matchup.get('players_points', {})
        starters = set(matchup.get('starters', []))
        all_players = set(map(str, matchup.get('players', [])))
        benched_players = all_players - starters
        for player_id in benched_players:
            score = players_points.get(player_id, 0)
            if score > highest_benched_score:
                highest_benched_score = score
                highest_benched_player = get_player_name_from_id(player_id, players_data)
                highest_benched_player_team = team_name
    return highest_benched_player, highest_benched_score, highest_benched_player_team

def get_match_results(matchups):
    results = {}
    for m in matchups:
        matchup_id = m.get('matchup_id')
        if matchup_id is None: continue
        if matchup_id not in results:
            results[matchup_id] = []
        results[matchup_id].append({'roster_id': m['roster_id'], 'points': m.get('points', 0)})
    return list(results.values())

def biggest_blowout_match_of_week(matchups, user_team_mapping, roster_owner_mapping):
    biggest_diff = -1
    blowout_match = (("Unknown", 0), ("Unknown", 0))
    for match in get_match_results(matchups):
        if len(match) == 2:
            team1_owner_id = roster_owner_mapping.get(match[0]['roster_id'])
            team2_owner_id = roster_owner_mapping.get(match[1]['roster_id'])
            team1_name = user_team_mapping.get(team1_owner_id, "Team 1")
            team2_name = user_team_mapping.get(team2_owner_id, "Team 2")
            score1 = match[0].get('points', 0)
            score2 = match[1].get('points', 0)
            diff = abs(score1 - score2)
            if diff > biggest_diff:
                biggest_diff = diff
                blowout_match = ((team1_name, score1), (team2_name, score2))
    return blowout_match, biggest_diff

def closest_match_of_week(matchups, user_team_mapping, roster_owner_mapping):
    closest_diff = float('inf')
    closest_matchup = (("Unknown", 0), ("Unknown", 0))
    for match in get_match_results(matchups):
        if len(match) == 2:
            team1_owner_id = roster_owner_mapping.get(match[0]['roster_id'])
            team2_owner_id = roster_owner_mapping.get(match[1]['roster_id'])
            team1_name = user_team_mapping.get(team1_owner_id, "Team 1")
            team2_name = user_team_mapping.get(team2_owner_id, "Team 2")
            score1 = match[0].get('points', 0)
            score2 = match[1].get('points', 0)
            diff = abs(score1 - score2)
            if diff < closest_diff:
                closest_diff = diff
                closest_matchup = ((team1_name, score1), (team2_name, score2))
    return closest_matchup, closest_diff

def get_team_on_hottest_streak(rosters, user_team_mapping):
    hottest_streak = 0
    hottest_team = "N/A"
    for roster in rosters:
        owner_id = roster.get('owner_id')
        team_name = user_team_mapping.get(owner_id, "Unknown Team")
        streak_str = roster.get('metadata', {}).get('streak', 'L0')
        if 'W' in streak_str:
            try:
                current_streak = int(streak_str.replace('W', ''))
                if current_streak > hottest_streak:
                    hottest_streak = current_streak
                    hottest_team = team_name
            except (ValueError, TypeError):
                continue
    return hottest_team, hottest_streak
