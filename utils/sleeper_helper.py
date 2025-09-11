import json
import os
import requests

# ##################################################################
# NEW AND UPDATED HELPER FUNCTIONS
# ##################################################################

def get_weekly_stats(week, season="2024"):
    """Fetches weekly stats for all players from the Sleeper API for a given season."""
    try:
        url = f"https://api.sleeper.app/v1/stats/nfl/{season}/{week}"
        response = requests.get(url)
        response.raise_for_status()  # Will raise an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching weekly stats: {e}")
        return {}

def calculate_player_points(player_stats, scoring_settings):
    """Calculates fantasy points based on player stats and league scoring settings."""
    if not player_stats or not scoring_settings:
        return 0.0
    
    total_points = 0.0
    for stat, value in player_stats.items():
        if stat in scoring_settings:
            total_points += value * scoring_settings[stat]
    return total_points

def get_player_name_from_id(player_id, players_data):
    """Gets a player's name from their ID."""
    player_info = players_data.get(str(player_id))
    if player_info:
        return f"{player_info.get('first_name', '')} {player_info.get('last_name', '')}".strip()
    return "Unknown Player"

# ##################################################################
# EXISTING HELPER FUNCTIONS
# ##################################################################

def highest_scoring_team_of_week(matchups, user_team_mapping, roster_owner_mapping):
    """Determines the highest-scoring team of the week."""
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
    """Formats the top 3 teams from the standings into a string."""
    summary = []
    for i, team in enumerate(standings[:3]):
        team_name = team[0]
        wins = team[1]
        losses = team[2]
        points = team[3]
        summary.append(f"  {i+1}. {team_name} - {points} points ({wins}W-{losses}L)")
    return "\n".join(summary)

def highest_scoring_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping):
    """Finds the highest-scoring player of the week."""
    highest_score = -1
    highest_scoring_player = None
    highest_scoring_player_team = "Unknown Team"
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
    """Finds the lowest-scoring starting player of the week."""
    lowest_score = float('inf')
    lowest_scoring_player = None
    lowest_scoring_player_team = "Unknown Team"
    for matchup in matchups:
        owner_id = roster_owner_mapping.get(matchup['roster_id'])
        team_name = user_team_mapping.get(owner_id, "Unknown Team")
        players_points = matchup.get('players_points', {})
        starters = matchup.get('starters', [])
        for player_id in starters:
            score = players_points.get(player_id, 0)
            if score < lowest_score:
                lowest_score = score
                lowest_scoring_player = get_player_name_from_id(player_id, players_data)
                lowest_scoring_player_team = team_name
    return lowest_scoring_player, lowest_score, lowest_scoring_player_team

def highest_scoring_benched_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping):
    """Finds the highest-scoring benched player of the week."""
    highest_benched_score = -1
    highest_benched_player = None
    highest_benched_player_team = "Unknown Team"
    for matchup in matchups:
        owner_id = roster_owner_mapping.get(matchup['roster_id'])
        team_name = user_team_mapping.get(owner_id, "Unknown Team")
        players_points = matchup.get('players_points', {})
        starters = set(matchup.get('starters', []))
        all_players = set(matchup.get('players', []))
        benched_players = all_players - starters
        for player_id in benched_players:
            score = players_points.get(player_id, 0)
            if score > highest_benched_score:
                highest_benched_score = score
                highest_benched_player = get_player_name_from_id(player_id, players_data)
                highest_benched_player_team = team_name
    return highest_benched_player, highest_benched_score, highest_benched_player_team

def get_match_results(matchups):
    """Pairs up matchups and their scores."""
    results = {}
    for m in matchups:
        matchup_id = m['matchup_id']
        if matchup_id not in results:
            results[matchup_id] = []
        results[matchup_id].append({'roster_id': m['roster_id'], 'points': m['points']})
    return list(results.values())

def biggest_blowout_match_of_week(matchups, user_team_mapping, roster_owner_mapping):
    """Finds the biggest blowout match of the week."""
    biggest_diff = -1
    blowout_match = (("Unknown", 0), ("Unknown", 0))
    
    paired_matches = get_match_results(matchups)

    for match in paired_matches:
        if len(match) == 2:
            team1_roster_id = match[0]['roster_id']
            team2_roster_id = match[1]['roster_id']
            
            team1_owner_id = roster_owner_mapping.get(team1_roster_id)
            team2_owner_id = roster_owner_mapping.get(team2_roster_id)

            team1_name = user_team_mapping.get(team1_owner_id, "Unknown Team")
            team2_name = user_team_mapping.get(team2_owner_id, "Unknown Team")
            
            team1_score = match[0]['points']
            team2_score = match[1]['points']
            
            diff = abs(team1_score - team2_score)
            if diff > biggest_diff:
                biggest_diff = diff
                blowout_match = ((team1_name, team1_score), (team2_name, team2_score))
    
    return blowout_match, biggest_diff

def closest_match_of_week(matchups, user_team_mapping, roster_owner_mapping):
    """Finds the closest match of the week."""
    closest_diff = float('inf')
    closest_matchup = (("Unknown", 0), ("Unknown", 0))

    paired_matches = get_match_results(matchups)

    for match in paired_matches:
        if len(match) == 2:
            team1_roster_id = match[0]['roster_id']
            team2_roster_id = match[1]['roster_id']
            
            team1_owner_id = roster_owner_mapping.get(team1_roster_id)
            team2_owner_id = roster_owner_mapping.get(team2_roster_id)

            team1_name = user_team_mapping.get(team1_owner_id, "Unknown Team")
            team2_name = user_team_mapping.get(team2_owner_id, "Unknown Team")
            
            team1_score = match[0]['points']
            team2_score = match[1]['points']
            
            diff = abs(team1_score - team2_score)
            if diff < closest_diff:
                closest_diff = diff
                closest_matchup = ((team1_name, team1_score), (team2_name, team2_score))

    return closest_matchup, closest_diff

def get_team_on_hottest_streak(rosters, user_team_mapping):
    """Finds the team with the longest winning streak."""
    hottest_streak = 0
    hottest_team = "Unknown"
    for roster in rosters:
        owner_id = roster.get('owner_id')
        team_name = user_team_mapping.get(owner_id, "Unknown Team")
        streak = roster.get('metadata', {}).get('streak', 'W0').replace('W', '')
        if 'W' in roster.get('metadata', {}).get('streak', ''):
            current_streak = int(streak)
            if current_streak > hottest_streak:
                hottest_streak = current_streak
                hottest_team = team_name
    return hottest_team, hottest_streak
