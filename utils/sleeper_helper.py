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
    """Creates scoreboards from matchup data with proper matchup grouping."""
    # Group matchups by matchup_id to find opponents
    matchup_groups = {}
    
    for matchup in matchups:
        matchup_id = matchup.get('matchup_id')
        if matchup_id:
            if matchup_id not in matchup_groups:
                matchup_groups[matchup_id] = []
            
            owner_id = roster_owner_map.get(matchup['roster_id'])
            team_name = team_name_map.get(owner_id, "Unknown Team")
            points = matchup.get('points', 0)
            
            matchup_groups[matchup_id].append({
                'team_name': team_name,
                'points': points,
                'roster_id': matchup['roster_id']
            })
    
    return matchup_groups

def highest_scoring_team_of_week(scoreboards):
    """Determines the highest-scoring team of the week."""
    highest_score = -1
    highest_team = "Unknown Team"
    
    for matchup_id, teams in scoreboards.items():
        for team in teams:
            if team['points'] > highest_score:
                highest_score = team['points']
                highest_team = team['team_name']
    
    return highest_team, highest_score

def top_3_teams(standings):
    """Gets the top 3 teams from the standings."""
    return standings[:3]

def highest_scoring_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping):
    highest_score = -1
    player_name, team_name = "N/A", "N/A"
    
    for m in matchups:
        owner_id = roster_owner_mapping.get(m['roster_id'])
        current_team_name = user_team_mapping.get(owner_id, "Unknown Team")
        
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
        current_team_name = user_team_mapping.get(owner_id, "Unknown Team")
        
        for player_id in m.get('starters', []):
            score = m.get('players_points', {}).get(str(player_id), 0)
            if score < lowest_score:
                lowest_score = score
                player_name = get_player_name_from_id(player_id, players_data)
                team_name = current_team_name
                
    if lowest_score == float('inf'):
        lowest_score = 0
        
    return player_name, lowest_score, team_name

def highest_scoring_benched_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping):
    highest_score = -1
    player_name, team_name = "N/A", "N/A"
    
    for m in matchups:
        owner_id = roster_owner_mapping.get(m['roster_id'])
        current_team_name = user_team_mapping.get(owner_id, "Unknown Team")
        starters = set(str(p) for p in m.get('starters', []))
        
        for player_id, score in m.get('players_points', {}).items():
            if str(player_id) not in starters and score > highest_score:
                highest_score = score
                player_name = get_player_name_from_id(player_id, players_data)
                team_name = current_team_name
                
    return player_name, highest_score, team_name

def biggest_blowout_match_of_week(scoreboards):
    """Finds the biggest blowout match with actual team names."""
    biggest_diff = -1
    blowout_match = None
    
    for matchup_id, teams in scoreboards.items():
        if len(teams) >= 2:
            # Sort teams by points to get winner and loser
            sorted_teams = sorted(teams, key=lambda x: x['points'], reverse=True)
            point_diff = sorted_teams[0]['points'] - sorted_teams[1]['points']
            
            if point_diff > biggest_diff:
                biggest_diff = point_diff
                blowout_match = (
                    (sorted_teams[0]['team_name'], sorted_teams[0]['points']),
                    (sorted_teams[1]['team_name'], sorted_teams[1]['points'])
                )
    
    if blowout_match is None:
        return (("No match", 0), ("No match", 0)), 0
    
    return blowout_match, biggest_diff

def closest_match_of_week(scoreboards):
    """Finds the closest match with actual team names."""
    smallest_diff = float('inf')
    closest_match = None
    
    for matchup_id, teams in scoreboards.items():
        if len(teams) >= 2:
            # Sort teams by points
            sorted_teams = sorted(teams, key=lambda x: x['points'], reverse=True)
            point_diff = abs(sorted_teams[0]['points'] - sorted_teams[1]['points'])
            
            if point_diff < smallest_diff:
                smallest_diff = point_diff
                closest_match = (
                    (sorted_teams[0]['team_name'], sorted_teams[0]['points']),
                    (sorted_teams[1]['team_name'], sorted_teams[1]['points'])
                )
    
    if closest_match is None:
        return (("No match", 0), ("No match", 0)), 0
    
    if smallest_diff == float('inf'):
        smallest_diff = 0
        
    return closest_match, smallest_diff

def team_on_hottest_streak(rosters, user_team_mapping, roster_owner_mapping):
    """Finds the team on the hottest win streak."""
    hottest_streak = 0
    hottest_team = "N/A"
    
    for r in rosters:
        owner_id = r.get('owner_id')
        team_name = user_team_mapping.get(owner_id, "Unknown Team")
        metadata = r.get('metadata', {})
        
        if metadata:
            streak_str = metadata.get('streak', 'L0')
            if 'W' in streak_str:
                try:
                    current_streak = int(streak_str.replace('W', ''))
                    if current_streak > hottest_streak:
                        hottest_streak = current_streak
                        hottest_team = team_name
                except (ValueError, TypeError):
                    continue
                    
    return hottest_team, hottest_streak
