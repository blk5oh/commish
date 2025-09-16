import streamlit as st
import os
import json
from espn_api.football import League
from yfpy.query import YahooFantasySportsQuery
from sleeper_wrapper import League as SleeperLeague
from utils import espn_helper, yahoo_helper, sleeper_helper, helper
import google.generativeai as genai
import datetime
from streamlit.logger import get_logger

LOGGER = get_logger(__name__)

def moderate_text_gemini(text):
    """
    Simple content moderation using basic checks.
    You could enhance this with Google's safety settings if needed.
    """
    try:
        # Basic inappropriate content check
        inappropriate_words = ['hate', 'violence', 'explicit', 'nsfw']
        text_lower = text.lower()
        
        for word in inappropriate_words:
            if word in text_lower:
                LOGGER.warning(f"Content moderation flagged word: {word}")
                return False
        return True
    except Exception as e:
        LOGGER.error("An error occurred during moderation: %s", str(e))
        return False

def generate_gemini_summary_streaming(summary, character_choice, trash_talk_level):
    """
    Generate streaming fantasy football recap using Google Gemini with enhanced prompting.
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # --- FIX: Updated prompt with all user requests ---
        prompt = f"""You are a world-class fantasy football commentator, tasked with creating a weekly recap that is clever, insightful, and hilarious.

Here are your instructions:

**PERSONA:** Adopt the voice and style of {character_choice}. Be completely committed to this persona.

**TRASH TALK LEVEL:** {trash_talk_level}/10. 
- A 1 should be friendly and light-hearted.
- A 10 should be absolutely brutal and savage, holding nothing back.

**TONE & STYLE:**
- **Be Clever:** Use witty wordplay, metaphors, and sharp analysis. Don't just list stats.
- **Use Puns:** Make clever puns based on player names, team names, or owner names.
- **Add Emojis:** Sprinkle in thematic emojis to add flair and personality. 
- **Be Entertaining:** The goal is to create a recap that is so good, the league members will be talking about it all week.

**SPECIFIC INSTRUCTIONS:**
- **High Points on the Bench:** This is a sign of terrible management. Mercilessly make fun of any manager who left a high-scoring player on their bench. It's a fireable offense! 🔥
- **Celebrate the Victor:** Praise the top-scoring team and player.
- **Roast the Losers:** Mock the lowest-scoring players and teams, especially the starters who flopped.
- **Analyze the Matchups:** Highlight the biggest blowout and the closest nail-biter.
- **Length:** Keep it under 250 words but make it extremely engaging.

**FANTASY DATA TO ANALYZE:**
{summary}

Your task: Create a witty, character-appropriate fantasy football recap. Start by introducing yourself as your character, then dive into the analysis. Make it memorable!"""
        
        response = model.generate_content(
            prompt,
            stream=True,
            generation_config=genai.types.GenerationConfig(
                temperature=0.85,  # Increased for more creativity
                max_output_tokens=1200,
            )
        )
        
        for chunk in response:
            if chunk.text:
                yield chunk.text
                
    except Exception as e:
        yield f"Error generating recap: {str(e)}"

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
        # Get matchup data
        blowout_match, blowout_diff = sleeper_helper.biggest_blowout_match_of_week(scoreboards)
        close_match, close_diff = sleeper_helper.closest_match_of_week(scoreboards)
        
        # Format blowout match display
        if blowout_match and len(blowout_match) >= 2:
            blowout_winner = blowout_match[0]
            blowout_loser = blowout_match[1]
            blowout_text = f"{blowout_winner[0]} ({blowout_winner[1]:.1f}) vs {blowout_loser[0]} ({blowout_loser[1]:.1f})"
        else:
            blowout_text = "No matchup data available"
        
        # Format closest match display  
        if close_match and len(close_match) >= 2:
            close_winner = close_match[0]
            close_loser = close_match[1]
            close_text = f"{close_winner[0]} ({close_winner[1]:.1f}) vs {close_loser[0]} ({close_loser[1]:.1f})"
        else:
            close_text = "No matchup data available"
        
        # Generate individual summary components
        highest_scoring_team_name, highest_scoring_team_score = sleeper_helper.highest_scoring_team_of_week(scoreboards)
        top_3_teams_result = sleeper_helper.top_3_teams(standings)
        hs_player, hs_score, hs_team = sleeper_helper.highest_scoring_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
        ls_starter, ls_score, ls_team = sleeper_helper.lowest_scoring_starter_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
        hs_benched, hs_benched_score, hs_benched_team = sleeper_helper.highest_scoring_benched_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
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
            f"**Biggest Blowout:** {blowout_text} (Point Differential: **{blowout_diff:.2f}**)\n",
            f"**Closest Game:** {close_text} (Point Differential: **{close_diff:.2f}**)\n",
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
