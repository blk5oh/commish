import streamlit as st
import openai
from streamlit.logger import get_logger
from utils import summary_generator

LOGGER = get_logger(__name__)


st.set_page_config(
    page_title="Commish.ai",
    page_icon="🏈",
    layout="centered",
    initial_sidebar_state="expanded"
)

def main():
    # st.title("Fantasy Football Weekly Summary Generator")
    st.write("""
    ## Instructions:

    1. **Select your league type** from the sidebar.
    2. **Fill out the required fields** based on your league selection:
    - **ESPN**:
        - *League ID*: [Find it here](https://support.espn.com/hc/en-us/articles/360045432432-League-ID).
        - *SWID and ESPN_S2*: Use this [Chrome extension](https://chrome.google.com/webstore/detail/espn-private-league-key-a/bakealnpgdijapoiibbgdbogehhmaopn) or follow [manual steps](https://www.gamedaybot.com/help/espn_s2-and-swid/).
    - **Yahoo**:
        - *League ID*: Navigate to Yahoo Fantasy Sports → Click your league → Mouse over **League**, click **Settings**. The League ID number is listed first.
    3. **Hit "🤖Generate AI Summary"** to get your weekly summary.
    """)


    with st.sidebar:
        st.sidebar.image('logo.png', use_column_width=True)
        st.header("Start here")
        league_type = st.selectbox("Select League Type", ["Select", "ESPN", "Yahoo"], key='league_type')

    if league_type != "Select":
        with st.sidebar.form(key='my_form'):
            if league_type == "ESPN":
                st.text_input("LeagueID", key='LeagueID')
                st.text_input("SWID", key='SWID')
                st.text_input("ESPN2_Id", key='ESPN2_Id')
            elif league_type == "Yahoo":
                st.text_input("LeagueID", key='LeagueID')
            
            st.text_input("Character Description", key='Character Description', placeholder="Dwight Schrute", help= "Describe a persona for the AI to adopt. E.g. 'Dwight Schrute' or 'A very drunk Captain Jack Sparrow'")
            st.slider("Trash Talk Level", 1, 10, key='Trash Talk Level', value=5, help="Scale of 1 to 10, where 1 is friendly banter and 10 is more extreme trash talk")
            submit_button = st.form_submit_button(label='🤖Generate AI Summary')

    
        # Handling form 
        if submit_button:
            try:
                # with st.spinner('Generating your summary... This will take about 15 seconds.'):
                with st.status("Generating your summary... This will take about 15 seconds", expanded=True) as status:
                    if league_type == "ESPN":
                        required_fields = ['LeagueID', 'SWID', 'ESPN2_Id', 'Character Description', 'Trash Talk Level']
                    else:
                        required_fields = ['LeagueID', 'Character Description', 'Trash Talk Level']
                    # Input validation
                    for field in required_fields:
                        value = st.session_state.get(field, None)
                        if not value:
                            st.error(f"{field} is required.")
                            return  # Stop execution if any required field is empty
                    status.text('Fetching league summary...')
                    if all(st.session_state.get(field, None) for field in required_fields):
                        league_id = st.session_state.get('LeagueID', 'Not provided')
                        character_description = st.session_state.get('Character Description', 'Not provided')
                        trash_talk_level = st.session_state.get('Trash Talk Level', 'Not provided')
                        swid = st.session_state.get('SWID', 'Not provided')
                        espn2 = st.session_state.get('ESPN2_Id', 'Not provided')
                        
                        # st.write(f'League Type: {league_type}')
                        # st.write(f'LeagueID: {league_id}')
                        # st.write(f'SWID: {swid}')
                        # st.write(f'ESPN2_Id: {espn2}')
                        # st.write(f'Character Description: {character_description}')
                        # st.write(f'Trash Talk Level: {trash_talk_level}')

                        # Fetch open ai key
                        openai_api_key=st.secrets["openai_api_key"]
                        openai.api_key=openai_api_key

                        if league_type == "ESPN":
                            summary, debug_info = summary_generator.get_espn_league_summary(
                                league_id, espn2, swid 
                            )
                        elif league_type == "Yahoo":
                            auth_directory = "auth"
                            summary = summary_generator.get_yahoo_league_summary(
                                league_id, auth_directory
                            )
                        # st.write(f'ESPN Summary: {summary}')
                        # st.write(f'Debug Info: {debug_info}')
                        
                        status.text('Generating AI summary...')
                        gpt4_summary_stream = summary_generator.generate_gpt4_summary_streaming(
                            summary, character_description, trash_talk_level
                        )
                        
                        with st.chat_message("Commish"):
                            message_placeholder = st.empty()
                            full_response = ""
                            for chunk in gpt4_summary_stream:
                                full_response += chunk
                                message_placeholder.markdown(full_response + "▌")
                            message_placeholder.markdown(full_response)
                            
                            # Display the full response within a code block which provides a copy button
                            st.markdown("**Click the copy icon** 📋 below in top right corner to copy your summary and paste it wherever you see fit!")
                            st.code(full_response, language="")
                            
            except Exception as e:
                status.error(f"An error occurred: {str(e)}")
                st.error(f"An error occurred: {str(e)}")
                LOGGER.exception(e)
if __name__ == "__main__":
    main()


