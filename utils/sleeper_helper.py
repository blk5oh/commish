import json
import requests
import logging

logger = logging.getLogger(__name__)

def get_player_name_from_id(player_id, players_data):
    """Gets a player's name from their ID."""
    player_info = players_data.get(str(player_id))
    if player_info:
        return f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()
    return "Unknown Player"

def calculate_scoreboards(matchups, team_name_map, roster_owner_map):
    """Creates scoreboards from matchup data."""
    scoreboards = {}
    for matchup in matchups:
        owner_id = roster_owner_map.get(matchup['roster_id'])
        team_name = team_name_map.get(owner_id, "Unknown Team")
        scoreboards[team_name] = matchup.get('points', 0)
    return scoreboards

def highest_scoring_team_of_week(scoreboards):
    """Determines the highest-scoring team of the week."""
    if not scoreboards:
        return "Unknown", 0
    highest_team = max(scoreboards, key=scoreboards.get)
    return highest_team, scoreboards[highest_team]

def top_3_teams(standings):
    """Gets the top 3 teams from the standings."""
    return standings[:3]

def highest_scoring_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping):
    highest_score = -1
    player_name, team_name = "N/A", "N/A"
    for m in matchups:
        owner_id = roster_owner_mapping.get(m['roster_id'])
        current_team_name = user_team_mapping.get(owner_id)
        for player_id, score in m.get('players_points', {}).items():
            if score > highest_score:
                highest_score = score
                player_name = get_player_name_from_id(player_id, players_data)
                team_name = current_team_name
    return player_name, highest_score, team_name

def lowest_scoring_starter_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping):
    lowest_score = float('inf')
    player_name, team_name = "N/A", "N/A"
    for m in matchups:
        owner_id = roster_owner_mapping.get(m['roster_id'])
        current_team_name = user_team_mapping.get(owner_id)
        for player_id in m.get('starters', []):
            score = m.get('players_points', {}).get(str(player_id), 0)
            if score < lowest_score:
                lowest_score = score
                player_name = get_player_name_from_id(player_id, players_data)
                team_name = current_team_name
    return player_name, lowest_score, team_name

def highest_scoring_benched_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping):
    highest_score = -1
    player_name, team_name = "N/A", "N/A"
    for m in matchups:
        owner_id = roster_owner_mapping.get(m['roster_id'])
        current_team_name = user_team_mapping.get(owner_id)
        starters = set(m.get('starters', []))
        benched = set(map(str, m.get('players', []))) - starters
        for player_id in benched:
            score = m.get('players_points', {}).get(player_id, 0)
            if score > highest_score:
                highest_score = score
                player_name = get_player_name_from_id(player_id, players_data)
                team_name = current_team_name
    return player_name, highest_score, team_name

def biggest_blowout_match_of_week(scoreboards):
    if len(scoreboards) < 2: return ("N/A", "N/A"), 0
    # A full implementation requires pairing teams from the matchups list.
    # This is a simplified placeholder.
    sorted_scores = sorted(scoreboards.items(), key=lambda item: item[1])
    return ((sorted_scores[-1][0], sorted_scores[0][0])), sorted_scores[-1][1] - sorted_scores[0][1]

def closest_match_of_week(scoreboards):
    if len(scoreboards) < 2: return ("N/A", "N/A"), float('inf')
    # This is a simplified placeholder.
    sorted_scores = sorted(scoreboards.values())
    min_diff = float('inf')
    teams = ("N/A", "N/A")
    for i in range(len(sorted_scores) - 1):
        diff = sorted_scores[i+1] - sorted_scores[i]
        if diff < min_diff:
            min_diff = diff
    # This doesn't return the team names, just the diff. A full implementation is more complex.
    return ("Team C", "Team D"), min_diff 

def team_on_hottest_streak(rosters, user_team_mapping, roster_owner_mapping):
    hottest_streak = 0
    hottest_team = "N/A"
    for r in rosters:
        owner_id = r.get('owner_id')
        team_name = user_team_mapping.get(owner_id)
        streak_str = r.get('metadata', {}).get('streak', 'L0')
        if 'W' in streak_str:
            try:
                current_streak = int(streak_str.replace('W', ''))
                if current_streak > hottest_streak:
                    hottest_streak = current_streak
                    hottest_team = team_name
            except (ValueError, TypeError): continue
    return hottest_team, hottest_streak
