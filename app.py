import streamlit as st
import google.generativeai as genai
from streamlit.logger import get_logger
from utils import summary_generator
from utils.helper import check_availability
import traceback
import os
import shutil
import tempfile
import time
import json
from requests.auth import HTTPBasicAuth
import requests

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
    2. **Fill out the required fields** based on your league selection.
    3. **Hit "🤖 Generate AI Summary"** to get your weekly summary.
    """)

    with st.sidebar:
        st.sidebar.image('logo.png', use_container_width=True)
        is_available, today = check_availability()
        if is_available:
            st.success(f"Today is {today}. The most recent week is completed and a recap is available.")
        else:
            st.warning("Recaps are best generated between Tuesday 4am EST and Thursday 7pm EST.")
        league_type = st.selectbox("Select League Type", ["Select", "Sleeper"], key='league_type')

    if league_type != "Select":
        with st.sidebar.form(key='my_form'):
            if league_type == "Sleeper":
                st.text_input("LeagueID", key='LeagueID')
            
            st.text_input("Character Description", key='Character Description', placeholder="Macho Man Randy Savage")
            st.slider("Trash Talk Level", 1, 10, key='Trash Talk Level', value=5)
            submit_button = st.form_submit_button(label='🤖 Generate AI Summary')

        if submit_button:
            try:
                progress = st.progress(0)
                progress.text('Starting...')
                
                if not st.session_state.get('LeagueID'):
                    st.error("LeagueID is required.")
                    return

                league_id = st.session_state.LeagueID
                character_description = st.session_state['Character Description']
                trash_talk_level = st.session_state['Trash Talk Level']

                progress.text('Fetching league summary...')
                progress.progress(30)
                
                summary, is_best_ball, league_type_name = "", False, "redraft"
                
                if league_type == "Sleeper":
                    summary, is_best_ball, league_type_name = summary_generator.generate_sleeper_summary(league_id)
                else:
                    st.error(f"{league_type} league type is not fully supported in this version.")
                    return

                st.markdown("### Stat Summary")
                st.markdown(summary)

                progress.text('Generating AI summary...')
                progress.progress(50)

                gemini_summary_stream = summary_generator.generate_gemini_summary_streaming(
                    summary, character_description, trash_talk_level, is_best_ball, league_type_name
                )
                
                with st.chat_message("Commish", avatar="🤖"):
                    message_placeholder = st.empty()
                    full_response = ""
                    for chunk in gemini_summary_stream:
                        if chunk is not None:
                            full_response += chunk
                            message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
            
                st.markdown("**Click the copy icon** 📋 below in top right corner to copy your summary!")
                st.code(full_response, language="")
                
                progress.text('Done!')
                progress.progress(100)
                
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                LOGGER.exception(e)
                st.text(traceback.format_exc())

if __name__ == "__main__":
    main()
