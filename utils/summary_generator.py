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

# (The rest of your file remains unchanged)
# ...
