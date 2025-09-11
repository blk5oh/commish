@st.cache_data(ttl=3600)
def generate_sleeper_summary(league_id):
    """
    Generates a human-friendly summary for a Sleeper league.
    
    Args:
    - league_id (str): The ID of the Sleeper league.
    
    Returns:
    - str: A human-friendly summary.
    """
    # Initialize the Sleeper API League object
    league = SleeperLeague(league_id)
    current_date_today = datetime.datetime.now()
    week = helper.get_current_week(current_date_today)

    # Get necessary data from the league
    rosters = league.get_rosters()
    users = league.get_users()
    matchups = league.get_matchups(week)
    standings = league.get_standings(rosters, users)

    # Get weekly players data from public json file
    players_url = "https://raw.githubusercontent.com/jeisey/commish/main/players_data.json"
    players_data = sleeper_helper.load_player_data(players_url)

    # Generate mappings
    user_team_mapping = league.map_users_to_team_name(users)
    roster_owner_mapping = league.map_rosterid_to_ownerid(rosters)
    
    # Generate scoreboards for the week
    scoreboards = sleeper_helper.calculate_scoreboards(matchups, user_team_mapping, roster_owner_mapping)

    # --- Generate individual summary components ---
    highest_scoring_team_name, highest_scoring_team_score = sleeper_helper.highest_scoring_team_of_week(scoreboards)
    top_3_teams_result = sleeper_helper.top_3_teams(standings)
    highest_scoring_player_week, weekly_score, highest_scoring_player_team_week = sleeper_helper.highest_scoring_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
    lowest_scoring_starter, lowest_starter_score, lowest_scoring_starter_team = sleeper_helper.lowest_scoring_starter_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
    highest_scoring_benched_player, highest_benched_score, highest_scoring_benched_player_team = sleeper_helper.highest_scoring_benched_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
    blowout_teams, point_differential_blowout = sleeper_helper.biggest_blowout_match_of_week(scoreboards)
    close_teams, point_differential_close = sleeper_helper.closest_match_of_week(scoreboards)
    hottest_streak_team, longest_streak = sleeper_helper.team_on_hottest_streak(rosters, user_team_mapping, roster_owner_mapping)

    # --- Construct the summary string using a list for better readability ---
    summary_parts = [
        f"The highest scoring team of the week: {highest_scoring_team_name} with {round(highest_scoring_team_score, 2)} points.",
        "Standings; Top 3 Teams:",
        f"  1. {top_3_teams_result[0][0]} - {top_3_teams_result[0][3]} points ({top_3_teams_result[0][1]}W-{top_3_teams_result[0][2]}L)",
        f"  2. {top_3_teams_result[1][0]} - {top_3_teams_result[1][3]} points ({top_3_teams_result[1][1]}W-{top_3_teams_result[1][2]}L)",
        f"  3. {top_3_teams_result[2][0]} - {top_3_teams_result[2][3]} points ({top_3_teams_result[2][1]}W-{top_3_teams_result[2][2]}L)",
        f"Highest scoring player of the week: {highest_scoring_player_week} with {weekly_score} points (Team: {highest_scoring_player_team_week}).",
        f"Lowest scoring player of the week that started: {lowest_scoring_starter} with {lowest_starter_score} points (Team: {lowest_scoring_starter_team}).",
        f"Highest scoring benched player of the week: {highest_scoring_benched_player} with {highest_benched_score} points (Team: {highest_scoring_benched_player_team}).",
        f"Biggest blowout match of the week: {blowout_teams[0]} vs {blowout_teams[1]} (Point Differential: {round(point_differential_blowout, 2)}).",
        f"Closest match of the week: {close_teams[0]} vs {close_teams[1]} (Point Differential: {round(point_differential_close, 2)}).",
        f"Team on the hottest streak: {hottest_streak_team} with a {longest_streak} game win streak."
    ]
    
    summary = "\n".join(summary_parts)
    LOGGER.info(f"Sleeper Summary Generated: \n{summary}")

    return summary
