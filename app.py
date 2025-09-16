import streamlit as st
import google.generativeai as genai
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

# Configure Google Gemini
GOOGLE_API_KEY = st.secrets["GOOGLE_API_KEY"]
genai.configure(api_key=GOOGLE_API_KEY)

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
                # Client_ID and Secret from https://developer.yahoo.com/apps/
                league_id = st.text_input("LeagueID", key='LeagueID')
                cid = st.secrets["YAHOO_CLIENT_ID"]
                cse = st.secrets["YAHOO_CLIENT_SECRET"]

                # Ensure that the Client ID and Secret are set
                if cid is None or cse is None:
                    st.error("Client ID or Client Secret is not set. Please set the YAHOO_CLIENT_ID and YAHOO_CLIENT_SECRET environment variables.")
                    st.stop()

                # URL for st button with Client ID in query string
                redirect_uri = "oob"
                auth_page = f'https://api.login.yahoo.com/oauth2/request_auth?client_id={cid}&redirect_uri={redirect_uri}&response_type=code'

                # Show ST Button to open Yahoo OAuth2 Page
                if 'auth_code' not in st.session_state:
                    st.session_state['auth_code'] = ''

                if 'access_token' not in st.session_state:
                    st.session_state['access_token'] = ''

                if 'refresh_token' not in st.session_state:
                    st.session_state['refresh_token'] = ''
                
                temp_dir = None

                st.write("1. Click the link below to authenticate with Yahoo and get the authorization code.")
                st.write(f"[Authenticate with Yahoo]({auth_page})")

                # Get Auth Code pasted by user
                st.write("2. Paste the authorization code here:")
                auth_code = st.text_input("Authorization Code")

                if auth_code:
                    st.session_state['auth_code'] = auth_code
                    st.success('Authorization code received!')

                # Get the token
                if st.session_state['auth_code'] and not st.session_state['access_token']:
                    basic = HTTPBasicAuth(cid, cse)
                    _data = {
                        'redirect_uri': redirect_uri,
                        'code': st.session_state['auth_code'],
                        'grant_type': 'authorization_code'
                    }

                    try:
                        r = requests.post('https://api.login.yahoo.com/oauth2/get_token', data=_data, auth=basic)
                        r.raise_for_status()
                        token_data = r.json()
                        st.session_state['access_token'] = token_data.get('access_token', '')
                        st.session_state['refresh_token'] = token_data.get('refresh_token', '')
                        st.session_state['token_time'] = time.time()
                        st.success('Access token received!')
                    except requests.exceptions.HTTPError as err:
                        st.error(f"HTTP error occurred: {err}")
                    except Exception as err:
                        st.error(f"An error occurred: {err}")

                # Use the access token
                if st.session_state['access_token']:
                    temp_dir = tempfile.mkdtemp()
                    if league_id:
                        # Define the paths to the token and private files
                        token_file_path = os.path.join(temp_dir, "token.json")
                        private_file_path = os.path.join(temp_dir, "private.json")

                        # Create the token file with all necessary details
                        token_data = {
                            "access_token": st.session_state['access_token'],
                            "consumer_key": cid,
                            "consumer_secret": cse,
                            "guid": None,
                            "refresh_token": st.session_state['refresh_token'],
                            "expires_in": 3600, 
                            "token_time": st.session_state['token_time'],
                            "token_type": "bearer"
                        }
                        with open(token_file_path, 'w') as f:
                            json.dump(token_data, f)

                        # Create the private file with consumer key and secret
                        private_data = {
                            "consumer_key": cid,
                            "consumer_secret": cse,
                        }
                        with open(private_file_path, 'w') as f:
                            json.dump(private_data, f)
            elif league_type == "Sleeper":
                st.text_input("LeagueID", key='LeagueID')
            
            st.text_input("Character Description", key='Character Description', placeholder="Dwight Schrute", help="Describe a persona for the AI to adopt. E.g. 'Dwight Schrute' or 'A very drunk Captain Jack Sparrow'")
            st.slider("Trash Talk Level", 1, 10, key='Trash Talk Level', value=5, help="Scale of 1 to 10, where 1 is friendly banter and 10 is more extreme trash talk")
            submit_button = st.form_submit_button(label='🤖 Generate AI Summary')

        # Handling form 
        if submit_button:
            try:
                progress = st.progress(0)
                progress.text('Starting...')
                
                required_fields = ['LeagueID', 'Character Description', 'Trash Talk Level']
                if league_type == "ESPN":
                    required_fields.extend(['SWID', 'ESPN2_Id'])
                
                # Input validation
                progress.text('Validating credentials...')
                progress.progress(5)
                for field in required_fields:
                    value = st.session_state.get(field, None)
                    if not value:
                        st.error(f"{field} is required.")
                        return
                
                league_id = st.session_state.get('LeagueID', 'Not provided')
                character_description = st.session_state.get('Character Description', 'Not provided')
                trash_talk_level = st.session_state.get('Trash Talk Level', 'Not provided')
                swid = st.session_state.get('SWID', 'Not provided')
                espn2 = st.session_state.get('ESPN2_Id', 'Not provided')

                # Moderate the character description using simple check
                progress.text('Validating character...')
                progress.progress(15)
                if not summary_generator.moderate_text_gemini(character_description):
                    st.error("The character description contains inappropriate content. Please try again.")
                    return
                
                # Fetching league summary
                progress.text('Fetching league summary...')
                progress.progress(30)
                if league_type == "ESPN":
                    LOGGER.debug("Attempting ESPN summary generator...")
                    summary, debug_info = summary_generator.get_espn_league_summary(
                        league_id, espn2, swid 
                    )
                    LOGGER.debug("~~ESPN DEBUG BELOW~~")
                    LOGGER.debug(debug_info)
                    LOGGER.debug("~~ESPN SUMMARY BELOW~~")
                    LOGGER.debug(summary)
                elif league_type == "Yahoo":
                    summary = summary_generator.get_yahoo_league_summary(league_id, temp_dir)
                    LOGGER.debug(summary)
                    st.write("Completed summary query, cleaning up...")
                    if temp_dir and os.path.isdir(temp_dir):
                        try:
                            shutil.rmtree(temp_dir)
                        except OSError as e:
                            LOGGER.warning("Failed to remove temp dir %s: %s", temp_dir, e)
                    st.write("Done with cleanup! Creating AI summary now...")
                elif league_type == "Sleeper":
                    summary = summary_generator.generate_sleeper_summary(league_id)
                    LOGGER.debug(summary)
                    LOGGER.info(f"Generated Sleeper Summary: \n{summary}")

                st.markdown("### Stat Summary")
                st.markdown(summary)

                progress.text('Generating AI summary...')
                progress.progress(50)

                LOGGER.debug("Initializing Gemini Summary Stream...")
                try:
                    gemini_summary_stream = summary_generator.generate_gemini_summary_streaming(
                        summary, character_description, trash_talk_level
                    )
                    LOGGER.debug(f"Generator object initialized: {gemini_summary_stream}")
                    
                    with st.chat_message("Commish", avatar="🤖"):
                        message_placeholder = st.empty()
                        full_response = ""
                
                        for chunk in gemini_summary_stream:
                            if chunk is not None:
                                full_response += chunk
                                message_placeholder.markdown(full_response + "▌")
                                LOGGER.debug(f"Received chunk: {chunk}")
                            
                        message_placeholder.markdown(full_response)
                
                    LOGGER.debug("Gemini Stream completed!")
                    
                    st.markdown("**Click the copy icon** 📋 below in top right corner to copy your summary and paste it wherever you see fit!")
                    st.code(full_response, language="")
                
                except Exception as e:
                    LOGGER.error(f"An error occurred while streaming Gemini response: {str(e)}")
                    st.error(f"An error occurred: {str(e)}")
                    LOGGER.exception(e)
                    st.text(traceback.format_exc())
                    
                LOGGER.debug("Summary generation complete!")
                progress.text('Done!')
                progress.progress(100)
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                LOGGER.exception(e)
                st.text(traceback.format_exc())

if __name__ == "__main__":
    main()
