import streamlit as st
# from openai import OpenAI
# from openai import OpenAI
from streamlit.logger import get_logger
from utils import summary_generator
from utils.helper import check_availability
import traceback
import requests
import json
import tempfile
from requests.auth import HTTPBasicAuth
import time
import os
import shutil

LOGGER = get_logger(__name__)

# COMMENTED OUT FOR TESTING - NO OPENAI NEEDED
# OPEN_AI_ORG_ID = st.secrets["OPENAI_ORG_ID"]
# OPEN_AI_PROJECT_ID = st.secrets["OPENAI_API_PROJECT_ID"]
# OPENAI_API_KEY = st.secrets["OPENAI_COMMISH_API_KEY"]

# client = OpenAI(
#     organization=OPEN_AI_ORG_ID,
#     project=OPEN_AI_PROJECT_ID,
#     api_key=OPENAI_API_KEY
#     )

st.set_page_config(
    page_title="Commish.ai",
    page_icon="🏈",
    layout="centered",
    initial_sidebar_state="expanded"
)

def main():
    st.write("""
    ## Instructions:

    1. **Select your league type** from the sidebar.
    2. **Fill out the required fields** based on your league selection:
    - **ESPN**:
        - *League ID*: [Find it here](https://support.espn.com/hc/en-us/articles/360045432432-League-ID).
        - *SWID and ESPN_S2*: Use this [Chrome extension](https://chrome.google.com/webstore/detail/espn-private-league-key-a/bakealnpgdijapoiibbgdbogehhmaopn) or follow [manual steps](https://www.gamedaybot.com/help/espn_s2-and-swid/).
    - **Yahoo**:
        - *League ID*: Navigate to Yahoo Fantasy Sports → Click your league → Mouse over **League**, click **Settings**. The League ID number is listed first.
        - *Authenticate*: Follow the prompt to enter your authentication code. Then fill in the character description and trash talk levels as your normally would.
    - **Sleeper**:
        - *League ID*: [Find it here](https://support.sleeper.com/en/articles/4121798-how-do-i-find-my-league-id). 
    3. **Hit "🤖 Generate AI Summary"** to get your weekly summary.
    
    **NOTE: AI Summary generation is temporarily disabled for testing. Only data fetching will be tested.**
    """)


    with st.sidebar:
        st.sidebar.image('logo.png', use_container_width=True)
        is_available, today = check_availability()
        if is_available:
            st.success(f"Today is {today}. The most recent week is completed and a recap is available.")
        else:
            st.warning(
                "Recaps are best generated between Tuesday 4am EST and Thursday 7pm EST. "
                "Please come back during this time for the most accurate recap."
            )
        league_type = st.selectbox("Select League Type", ["Select", "ESPN", "Yahoo", "Sleeper"], key='league_type')

    if league_type != "Select":
        with st.sidebar.form(key='my_form'):
            if league_type == "ESPN":
                st.text_input("LeagueID", key='LeagueID')
                st.text_input("SWID", key='SWID')
                st.text_input("ESPN_S2", key='ESPN2_Id')
            elif league_type == "Yahoo":
                st.error("Yahoo testing disabled - requires API keys")
                return
            elif league_type == "Sleeper":
                st.text_input("LeagueID", key='LeagueID')
            
            st.text_input("Character Description", key='Character Description', placeholder="Dwight Schrute", help= "Describe a persona for the AI to adopt. E.g. 'Dwight Schrute' or 'A very drunk Captain Jack Sparrow'")
            st.slider("Trash Talk Level", 1, 10, key='Trash Talk Level', value=5, help="Scale of 1 to 10, where 1 is friendly banter and 10 is more extreme trash talk")
            submit_button = st.form_submit_button(label='🤖 Test Data Fetching (No AI)')

    
        # Handling form 
        if submit_button:
            try:
                progress = st.progress(0)
                progress.text('Starting...')
                
                required_fields = ['LeagueID']  # Simplified for testing
                if league_type == "ESPN":
                    required_fields.extend(['SWID', 'ESPN2_Id'])
                
                # Input validation
                progress.text('Validating credentials...')
                progress.progress(5)
                for field in required_fields:
                    value = st.session_state.get(field, None)
                    if not value:
                        st.error(f"{field} is required.")
                        return  # Stop execution if any required field is empty
                
                league_id = st.session_state.get('LeagueID', 'Not provided')
                character_description = st.session_state.get('Character Description', 'Not provided')
                trash_talk_level = st.session_state.get('Trash Talk Level', 'Not provided')
                swid = st.session_state.get('SWID', 'Not provided')
                espn2 = st.session_state.get('ESPN2_Id', 'Not provided')

                # Skip moderation for testing
                progress.text('Skipping character validation...')
                progress.progress(15)
                
                # Fetching league summary
                progress.text('Fetching league summary...')
                progress.progress(30)
                if league_type == "ESPN":
                    st.error("ESPN testing disabled - requires API keys")
                    return
                elif league_type == "Yahoo":
                    st.error("Yahoo testing disabled - requires API keys")
                    return
                elif league_type == "Sleeper":
                    auth_directory = "auth"
                    summary = summary_generator.generate_sleeper_summary(
                        league_id
                    )
                    LOGGER.debug(summary)
                    LOGGER.info(f"Generated Sleeper Summary: \n{summary}")

                st.markdown("### Stat Summary (Raw Data)")
                st.markdown(summary)

                progress.text('Data fetching complete! AI generation skipped for testing.')
                progress.progress(100)
                
                st.success("✅ Data fetching test completed! Check the summary above to see if player points are now working.")
                st.info("If you see actual player points (not 0.0), the fix worked! You can then add back the OpenAI integration.")
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                LOGGER.exception(e)
                st.text(traceback.format_exc())

if __name__ == "__main__":
    main()
