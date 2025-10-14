import streamlit as st
import os
import json
from sleeper_wrapper import League as SleeperLeague
from utils import sleeper_helper, helper
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold
import datetime
from streamlit.logger import get_logger

LOGGER = get_logger(__name__)

def moderate_text_gemini(text, trash_talk_level=5):
    """
    Simple content moderation that allows 'explicit' if trash_talk_level is 10.
    """
    try:
        inappropriate_words = ['hate', 'violence', 'nsfw']
        if trash_talk_level < 10:
            inappropriate_words.append('explicit')

        text_lower = text.lower()
        for word in inappropriate_words:
            if word in text_lower:
                LOGGER.warning(f"Content moderation flagged word: {word}")
                return False
        return True
    except Exception as e:
        LOGGER.error("An error occurred during moderation: %s", str(e))
        return False

def generate_gemini_summary_streaming(summary, character1, character2, trash_talk_level, is_best_ball=False, league_type='redraft'):
    """
    Generate streaming fantasy football recap using Google Gemini, handling one or two characters.
    """
    try:
        # --- FIX: Use the 'gemini-2.0-flash-exp' model as specified ---
        model = genai.GenerativeModel('gemini-2.0-flash-exp')
        
        safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }
        if trash_talk_level == 10:
            safety_settings[HarmCategory.HARM_CATEGORY_HARASSMENT] = HarmBlockThreshold.BLOCK_NONE
            safety_settings[HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT] = HarmBlockThreshold.BLOCK_NONE

        if character2:
            # BANTER PROMPT
            prompt = f"""You are a scriptwriter for a fantasy football recap show. Your task is to write a script for a playful banter and debate between two co-hosts: {character1} and {character2}.

Here are your instructions:

**FORMAT:**
- Write the script as a dialogue. For example:
  {character1}: [dialogue]
  {character2}: [dialogue]
- The hosts should interrupt, react to, and build upon each other's points while still delivering the weekly recap.

**PERSONAS:**
- {character1} must speak and act exactly like their real-life persona.
- {character2} must also be perfectly in character.
- Their personalities should clash or combine in a funny and engaging way.

**TRASH TALK LEVEL:** {trash_talk_level}/10. (1=friendly, 10=savage, can include explicit language).

**TONE & STYLE:**
- The banter should be witty, clever, and reflect the personalities of the hosts.
- They should have different opinions on the performances to create a debate.
- Keep the total word count under 250 words.
- Use emojis and pop culture references.

**FANTASY DATA TO ANALYZE:**
{summary}

Your task: Write the script for this recap show. The hosts must stay in character, debate the weekly results, and make it hilarious."""

        else:
            # SINGLE CHARACTER PROMPT
            bench_player_instruction = ""
            if not is_best_ball:
                bench_player_instruction = """- **High Points on the Bench:** This is a sign of terrible management. Mercilessly make fun of any manager who left a high-scoring player on their bench. It's a fireable offense! 🔥"""
            else:
                bench_player_instruction = """- **This is a Best Ball league, so there's no need to analyze bench players.**"""

            prompt = f"""You are a world-class fantasy football commentator, tasked with creating a weekly recap for a '{league_type}' league.

**PERSONA:** Adopt the voice and style of {character1}. Be completely committed to this persona.
**TRASH TALK LEVEL:** {trash_talk_level}/10 (1=friendly, 10=savage and can include explicit language).

**TONE & STYLE:**
- Be clever, witty, and use puns and pop culture references.
- Be original and do not reuse phrases from the data below.
- Use emojis.
- Keep the summary under 250 words.

**SPECIFIC INSTRUCTIONS:**
{bench_player_instruction}
- Celebrate the victors and roast the losers.
- Analyze the biggest blowout and the closest game.

**FANTASY DATA TO ANALYZE:**
{summary}

Your task: Create a witty, character-appropriate fantasy football recap. Start by introducing yourself as {character1}, then dive into the analysis. Make it memorable!"""
        
        response = model.generate_content(
            prompt,
            stream=True,
            generation_config=genai.types.GenerationConfig(temperature=0.9, max_output_tokens=1000),
            safety_settings=safety_settings
        )
        
        for chunk in response:
            if chunk.text:
                yield chunk.text
                
    except Exception as e:
        yield f"Error generating recap: {str(e)}"

@st.cache_data(ttl=3600)
def generate_sleeper_summary(league_id):
    """Generates a human-friendly summary for a Sleeper league, now aware of Best Ball leagues."""
    league = SleeperLeague(league_id)
    week = helper.get_safest_week_for_recap(datetime.datetime.now())
    
    try:
        league_data = league.get_league()
        settings = league_data.get('settings', {})
        is_best_ball = settings.get('best_ball', 0) == 1
        league_type_name = league_data.get('type', 'redraft')
        
        rosters = league.get_rosters()
        users = league.get_users()
        matchups = league.get_matchups(week)
        standings = league.get_standings(rosters, users)

        if not matchups:
            return f"No data available for Week {week}. This week may not have started yet.", is_best_ball, league_type_name

        try:
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            players_file_path = os.path.join(project_root, 'players_data.json')
            with open(players_file_path, 'r') as f:
                players_data = json.load(f)
        except FileNotFoundError:
            st.error(f"Player data file ('players_data.json') not found at: {players_file_path}.")
            return "Player data not found.", is_best_ball, league_type_name

        user_team_mapping = league.map_users_to_team_name(users)
        roster_owner_mapping = league.map_rosterid_to_ownerid(rosters)
        scoreboards = sleeper_helper.calculate_scoreboards(matchups, user_team_mapping, roster_owner_mapping)
        
        blowout_match, blowout_diff = sleeper_helper.biggest_blowout_match_of_week(scoreboards)
        close_match, close_diff = sleeper_helper.closest_match_of_week(scoreboards)
        
        blowout_text = "No matchup data available"
        if blowout_match and len(blowout_match) >= 2:
            blowout_winner, blowout_loser = blowout_match
            blowout_text = f"{blowout_winner[0]} ({blowout_winner[1]:.1f}) vs {blowout_loser[0]} ({blowout_loser[1]:.1f})"

        close_text = "No matchup data available"
        if close_match and len(close_match) >= 2:
            close_winner, close_loser = close_match
            close_text = f"{close_winner[0]} ({close_winner[1]:.1f}) vs {close_loser[0]} ({close_loser[1]:.1f})"
        
        highest_scoring_team_name, highest_scoring_team_score = sleeper_helper.highest_scoring_team_of_week(scoreboards)
        top_3_teams_result = sleeper_helper.top_3_teams(standings)
        hs_player, hs_score, hs_team = sleeper_helper.highest_scoring_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
        ls_starter, ls_score, ls_team = sleeper_helper.lowest_scoring_starter_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
        hottest_team, streak = sleeper_helper.team_on_hottest_streak(rosters, user_team_mapping, roster_owner_mapping)

        summary_parts = [
            f"### Weekly Standouts (Week {week})\n",
            f"**Top Scoring Team:** {highest_scoring_team_name} with **{highest_scoring_team_score:.2f}** points.\n",
            f"**Top Player:** {hs_player} with **{hs_score:.2f}** points (Team: {hs_team}).\n",
            f"**Lowest Scoring Starter:** {ls_starter} with **{ls_score:.2f}** points (Team: {ls_team}).\n",
        ]

        if not is_best_ball:
            hs_benched, hs_benched_score, hs_benched_team = sleeper_helper.highest_scoring_benched_player_of_week(matchups, players_data, user_team_mapping, roster_owner_mapping)
            summary_parts.append(f"**Best Bench Player:** {hs_benched} scored **{hs_benched_score:.2f}** points on the bench for {hs_benched_team}.\n")

        summary_parts.extend([
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
        ])
        
        summary = "".join(summary_parts)
        LOGGER.info(f"Sleeper Summary Generated for Week {week} with real data")

        return summary, is_best_ball, league_type_name
        
    except Exception as e:
        error_msg = f"Error generating Sleeper summary: {str(e)}"
        LOGGER.error(error_msg, exc_info=True)
        return error_msg, False, 'redraft'
