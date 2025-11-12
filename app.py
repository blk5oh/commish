import streamlit as st
import google.generativeai as genai
from streamlit.logger import get_logger
from utils import summary_generator
from utils.helper import check_availability
import traceback
import os

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
            
            st.write("Choose one or two characters for the recap:")
            col1, col2 = st.columns(2)
            with col1:
                st.text_input("Character 1", key='Character1', placeholder="Macho Man Randy Savage")
            with col2:
                st.text_input("Character 2 (Optional)", key='Character2', placeholder="Snoop Dogg")
            
            st.slider("Trash Talk Level", 1, 10, key='Trash Talk Level', value=5)
            submit_button = st.form_submit_button(label='🤖 Generate AI Summary')

        if submit_button:
            summary, is_best_ball, league_type_name = "", False, "redraft"
            try:
                progress = st.progress(0)
                progress.text('Starting...')
                
                if not st.session_state.get('LeagueID') or not st.session_state.get('Character1'):
                    st.error("LeagueID and at least Character 1 are required.")
                    return

                league_id = st.session_state.LeagueID
                character1 = st.session_state.Character1
                character2 = st.session_state.Character2
                trash_talk_level = st.session_state['Trash Talk Level']

                progress.text('Validating character(s)...')
                progress.progress(15)
                if not summary_generator.moderate_text_gemini(character1, trash_talk_level) or (character2 and not summary_generator.moderate_text_gemini(character2, trash_talk_level)):
                    st.error("A character description contains inappropriate content. Please try again.")
                    return
                
                progress.text('Fetching league summary...')
                progress.progress(30)
                
                if league_type == "Sleeper":
                    summary, is_best_ball, league_type_name = summary_generator.generate_sleeper_summary(league_id)
                else:
                    st.error(f"{league_type} league type is not fully supported in this version.")
                    return

                st.markdown("### Stat Summary")
                st.markdown(summary)

                progress.text('Generating AI summary...')
                progress.progress(50)

                # --- FIX: Try to stream the summary ---
                gemini_summary_stream = summary_generator.generate_gemini_summary_streaming(
                    summary, character1, character2, trash_talk_level, is_best_ball, league_type_name
                )
                
                with st.chat_message("Commish", avatar="🤖"):
                    message_placeholder = st.empty()
                    full_response = ""
                    
                    first_chunk_received = False
                    for chunk in gemini_summary_stream:
                        if not first_chunk_received:
                            # Check the first chunk for the error
                            if chunk and chunk.startswith("Error generating recap:"):
                                # This is our API error, re-raise it to trigger the 'except' block
                                raise Exception(chunk)
                            first_chunk_received = True
                        
                        if chunk is not None:
                            full_response += chunk
                            message_placeholder.markdown(full_response + "▌")
                    message_placeholder.markdown(full_response)
            
                st.markdown("**Click the copy icon** 📋 below in top right corner to copy your summary!")
                st.code(full_response, language="")
                
                progress.text('Done!')
                progress.progress(100)
                
            except Exception as e:
                # --- FIX: Fallback logic ---
                # This block will catch the error we raised
                st.error(f"An error occurred: {str(e)}")
                LOGGER.warning(f"API call failed, falling back to prompt generation. Error: {str(e)}")
                
                if str(e).startswith("Error generating recap:"):
                    st.warning("The API call failed (likely due to quota). Here is the prompt you can use in another LLM.")
                    
                    try:
                        # We need the variables from the 'try' block
                        llm_prompt = summary_generator.generate_llm_prompt(
                            summary, 
                            st.session_state.Character1, 
                            st.session_state.Character2, 
                            st.session_state['Trash Talk Level'], 
                            is_best_ball, 
                            league_type_name
                        )
                        st.markdown("### Your Prompt is Ready 📋")
                        st.text_area("Prompt to copy:", llm_prompt, height=300)
                    except Exception as prompt_e:
                        st.error(f"Failed to generate fallback prompt: {prompt_e}")
                else:
                    st.error("An unexpected error occurred.")
                    LOGGER.exception(e)
                    st.text(traceback.format_exc())

if __name__ == "__main__":
    main()
