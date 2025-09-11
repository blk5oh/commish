@st.cache_data(ttl=3600)
def generate_sleeper_summary(league_id):
    """Generates a human-friendly summary for a Sleeper league - only uses completed weeks."""
    league = SleeperLeague(league_id)
    
    # Use the safest week calculation - guarantees completed scoring
    week = helper.get_safest_week_for_recap(datetime.datetime.now())
    current_nfl_week = helper.get_current_week(datetime.datetime.now())
    
    # Debug info to understand what's happening
    debug_info = helper.debug_week_selection(datetime.datetime.now())
    
    LOGGER.info(f"Week Selection Debug: {debug_info}")
    LOGGER.info(f"Current NFL week: {current_nfl_week}, Using completed week: {week} for data")

    try:
        rosters = league.get_rosters()
        users = league.get_users()
        matchups = league.get_matchups(week)
        standings = league.get_standings(rosters, users)

        # Check if we actually got matchup data
        if not matchups:
            LOGGER.warning(f"No matchup data returned for week {week}")
            return f"No data available for Week {week}. This week may not have started yet or data isn't available."

        # Check if matchup data has actual scores
        has_real_scores = False
        for matchup in matchups:
            if matchup.get('points', 0) > 0:
                has_real_scores = True
                break
            
        if not has_real_scores:
            # Try an even earlier week
            safer_week = max(1, week - 1)
            LOGGER.info(f"Week {week} has no scores, trying week {safer_week}")
            matchups = league.get_matchups(safer_week)
            week = safer_week  # Update week variable for display

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

        # Check if we got real data
        if hs_score == 0 and ls_score == 0 and highest_scoring_team_score == 0:
            return f"""
            ### No Scoring Data Available
            
            **Week {week}** data shows all zeros, which means:
            - This week's games haven't been played yet, OR
            - Scoring hasn't been finalized, OR  
            - There's an issue with the Sleeper API
            
            **Try again after Tuesday 6 AM EST** when scores are typically finalized.
            
            **Debug Info:**
            - Current NFL Week: {current_nfl_week}  
            - Attempted Week: {week}
            - Available Weeks: {debug_info.get('available_weeks', [])}
            """

        # Format summary with Markdown for better readability
        summary_parts = [
            f"### Weekly Standouts (Week {week})\n",
            f"**Top Scoring Team:** {highest_scoring_team_name} with **{highest_scoring_team_score:.2f}** points.\n",
            f"**Top Player:** {hs_player} with **{hs_score:.2f}** points (Team: {hs_team}).\n",
            f"**Lowest Scoring Starter:** {ls_starter} with **{ls_score:.2f}** points (Team: {ls_team}).\n",
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
        LOGGER.info(f"Sleeper Summary Generated for Week {week} with real data")

        return summary
        
    except Exception as e:
        error_msg = f"Error generating Sleeper summary: {str(e)}"
        LOGGER.error(error_msg)
        return error_msg
