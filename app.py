import streamlit as st
import os
import tempfile
import shutil
import zipfile
import plotly.graph_objects as go
from data_manager import DataManager
from managers import RateLimiter, HistoryManager
from tts_engine import generate_speech

# Constants
GEMINI_VOICES = [
    "Puck", "Charon", "Kore", "Fenrir", "Aoede",
    "Zephyr", "Orus", "Autonoe", "Umbriel", "Erinome",
    "Laomedeia", "Achird", "Sadachbia", "Leda", "Callirrhoe",
    "Enceladus", "Algieba", "Algenib", "Achernar", "Schedar",
    "Gacrux", "Zubenelgenubi", "Vindemiatrix", "Sadaltager",
    "Sulafat", "Iapetus", "Despina", "Rasalgethi", "Alnilam",
    "Pulcherrima"
]

def main():
    st.set_page_config(page_title="Gemini TTS Studio", layout="wide")
    st.title("🎙️ Gemini TTS Studio")
    st.markdown("Generate voiceovers for your characters using **Gemini 2.5 Pro TTS**.")

    # --- Sidebar ---
    with st.sidebar:
        st.header("Settings")

        # API Key
        current_api_key = DataManager.get_api_key()
        api_key_input = st.text_input("Gemini API Key", value=current_api_key, type="password")
        if api_key_input != current_api_key:
            DataManager.save_api_key(api_key_input)
            st.success("API Key saved!")

        # Rate Limits
        limit_min, limit_day = DataManager.get_limits()
        stats = RateLimiter.get_usage_stats()

        st.caption("Rate Limits")
        col_lim1, col_lim2 = st.columns(2)
        with col_lim1:
            new_limit_min = st.number_input("Req / Min", value=limit_min, min_value=1)
            fig_min = create_gauge(stats["used_min"], new_limit_min, "Used / Min")
            st.plotly_chart(fig_min, use_container_width=True)

        with col_lim2:
            new_limit_day = st.number_input("Req / Day", value=limit_day, min_value=1)
            fig_day = create_gauge(stats["used_day"], new_limit_day, "Used / Day")
            st.plotly_chart(fig_day, use_container_width=True)

        if new_limit_min != limit_min or new_limit_day != limit_day:
            DataManager.save_limits(new_limit_min, new_limit_day)
            st.success("Limits saved!")

        st.divider()

        # Character Manager
        st.header("Character Manager")

        # Add New Character
        with st.expander("Add / Edit Character", expanded=False):
            char_name = st.text_input("Character Name")

            # Voice Selection with fallback to text input
            voice_selection = st.selectbox("Voice", options=GEMINI_VOICES + ["Custom..."])
            if voice_selection == "Custom...":
                char_voice = st.text_input("Enter Voice Name manually")
            else:
                char_voice = voice_selection

            char_style = st.text_area("Style Instructions", placeholder="e.g. Speak in a whisper, sound angry...", help="Context for how the character should speak.")

            if st.button("Save Character"):
                if char_name and char_voice:
                    DataManager.add_or_update_character(char_name, char_voice, char_style)
                    st.success(f"Character '{char_name}' saved!")
                    st.rerun()
                else:
                    st.error("Name and Voice are required.")

        # List Existing Characters
        st.subheader("Your Characters")
        characters = DataManager.get_characters()
        if not characters:
            st.info("No characters added yet.")
        else:
            for name, details in characters.items():
                with st.expander(f"👤 {name} ({details['voice']})"):
                    st.write(f"**Style:** {details.get('style', 'None')}")
                    if st.button(f"Delete {name}", key=f"del_{name}"):
                        DataManager.delete_character(name)
                        st.rerun()

    # --- Main Area ---

    st.subheader("Batch Audio Generation")

    with st.expander("ℹ️ Input Format Instructions", expanded=True):
        st.markdown("""
        Enter each line in the following format:
        `Character Name | Text to speak | Filename`

        **Example:**
        ```text
        Narrator | Welcome to our show. | intro_01
        Hero | I will save the world! | hero_line_01
        Villain | Not if I have anything to say about it. | villain_response
        ```
        """)

    script_input = st.text_area("Script Input", height=300, placeholder="Hero | Hello there! | hero_01")

    if st.button("Generate Audio", type="primary"):
        initialize_batch_generation(script_input)

    if "batch_results" in st.session_state:
        render_batch_review()

    # --- History Section ---
    st.divider()
    with st.expander("📜 Request History"):
        render_history_view()

def create_gauge(current, limit, title):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = current,
        title = {'text': title, 'font': {'size': 14}},
        number = {'font': {'size': 16}},
        domain = {'x': [0, 1], 'y': [0, 1]},
        gauge = {
            'axis': {'range': [0, limit], 'tickwidth': 1, 'tickfont': {'size': 10}},
            'bar': {'color': "#1f77b4"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, limit * 0.5], 'color': '#e6f9e6'}, # light green
                {'range': [limit * 0.5, limit * 0.8], 'color': '#ffffe0'}, # light yellow
                {'range': [limit * 0.8, limit], 'color': '#ffe6e6'} # light red
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': limit
            }
        }
    ))
    # Reduced height and margins for smaller footprint
    fig.update_layout(height=140, margin=dict(l=35, r=35, t=30, b=10))
    return fig

def render_history_view():
    col_hist_1, col_hist_2 = st.columns([4, 1])
    with col_hist_1:
        st.write("View past generation requests and results.")
    with col_hist_2:
        if st.button("Clear History", type="secondary"):
            HistoryManager.clear_history()
            st.rerun()

    history = HistoryManager.get_history()
    if not history:
        st.info("No history found.")
        return

    # Pagination or Limit could be useful, but for now show all (maybe limit to last 50 for performance if list gets huge)
    for entry in history:
        with st.container():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.caption(f"{entry['timestamp']} | {entry['char_name']} ({entry['voice']})")
                st.text(entry['text'])
            with col2:
                if os.path.exists(entry['audio_path']):
                    st.audio(entry['audio_path'])
                else:
                    st.warning("File missing")
            st.markdown("---")

def initialize_batch_generation(script_text: str):
    api_key = DataManager.get_api_key()
    if not api_key:
        st.error("Please enter your Gemini API Key in the settings.")
        return

    characters = DataManager.get_characters()
    lines = script_text.strip().split('\n')

    if not lines:
        st.warning("Script is empty.")
        return

    # Parse and Validate
    parsed_tasks = []
    errors = []

    for i, line in enumerate(lines):
        if not line.strip():
            continue

        parts = [p.strip() for p in line.split('|')]
        if len(parts) != 3:
            errors.append(f"Line {i+1}: Invalid format. Expected 3 parts separated by '|'.")
            continue

        char_name, text, filename = parts

        if char_name not in characters:
            errors.append(f"Line {i+1}: Character '{char_name}' not found in settings.")
            continue

        parsed_tasks.append({
            "char_name": char_name,
            "text": text,
            "filename": filename,
            "config": characters[char_name],
            "versions": [],
            "selected_index": 0
        })

    if errors:
        for err in errors:
            st.error(err)
        return

    # Generation Process
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Create persistent temp directory
    # If a temp dir already exists from a previous session, we might want to use it or create a new one.
    if "batch_temp_dir" in st.session_state and os.path.exists(st.session_state["batch_temp_dir"]):
         shutil.rmtree(st.session_state["batch_temp_dir"], ignore_errors=True)

    temp_dir = tempfile.mkdtemp()
    st.session_state["batch_temp_dir"] = temp_dir

    successful_tasks = []

    for idx, task in enumerate(parsed_tasks):
        char_name = task["char_name"]
        status_text.text(f"Generating audio for: {task['filename']} ({char_name})...")

        # Initial version file
        output_filename = f"{task['filename']}_v1.wav"
        output_file = os.path.join(temp_dir, output_filename)
        voice = task["config"]["voice"]
        style = task["config"]["style"]

        # Check Rate Limit
        allowed, msg = RateLimiter.check_limit()
        if not allowed:
            st.error(f"Stopped at {task['filename']}: {msg}")
            break

        try:
            # Call TTS Engine
            success = generate_speech(
                api_key=api_key,
                text=task["text"],
                voice_name=voice,
                style_instructions=style,
                output_path=output_file
            )

            if success:
                RateLimiter.log_request()
                HistoryManager.add_entry(char_name, task["text"], voice, style, output_file)
                task["versions"].append(output_file)
                successful_tasks.append(task)
            else:
                st.error(f"Failed to generate audio for {task['filename']}")
        except Exception as e:
            st.error(f"Error generating {task['filename']}: {str(e)}")

        progress_bar.progress((idx + 1) / len(parsed_tasks))

    if successful_tasks:
        st.session_state["batch_results"] = successful_tasks
        st.rerun()
    else:
        st.warning("No files were generated.")

def render_batch_review():
    st.divider()
    st.subheader("🎧 Review & Download")

    if st.button("Start New Batch", key="start_new_batch_btn"):
        if "batch_temp_dir" in st.session_state and os.path.exists(st.session_state["batch_temp_dir"]):
            shutil.rmtree(st.session_state["batch_temp_dir"], ignore_errors=True)
        if "batch_results" in st.session_state:
            del st.session_state["batch_results"]
        if "batch_temp_dir" in st.session_state:
            del st.session_state["batch_temp_dir"]
        st.rerun()

    results = st.session_state["batch_results"]
    temp_dir = st.session_state.get("batch_temp_dir")

    for idx, task in enumerate(results):
        with st.container():
            st.markdown(f"### {task['filename']} ({task['char_name']})")
            st.text(f"\"{task['text']}\"")

            # Version Selector
            num_versions = len(task["versions"])
            selected_idx = task["selected_index"]

            col1, col2 = st.columns([3, 1])

            with col1:
                # If multiple versions, let user choose
                if num_versions > 1:
                    version_options = [f"Version {i+1}" for i in range(num_versions)]
                    # Create a unique key for this radio button
                    selected_v_label = st.radio(
                        "Select Version",
                        options=version_options,
                        index=selected_idx,
                        key=f"ver_sel_{idx}",
                        horizontal=True
                    )
                    # Update selected index based on selection
                    new_idx = version_options.index(selected_v_label)
                    if new_idx != selected_idx:
                        task["selected_index"] = new_idx
                        st.rerun()

                current_file = task["versions"][task["selected_index"]]
                st.audio(current_file)

            with col2:
                # Regenerate Button
                if st.button(f"Regenerate", key=f"regen_{idx}"):
                    regenerate_task_audio(task, temp_dir)
                    st.rerun()

            st.divider()

    # Download ZIP Button
    st.subheader("Download Final Results")

    # Check if a zip has already been created for this batch, or create one if requested
    if st.button("Prepare Download"):
        zip_path = create_final_zip(results, temp_dir)
        if zip_path:
            st.session_state["final_zip_path"] = zip_path
            st.rerun()

    if "final_zip_path" in st.session_state and os.path.exists(st.session_state["final_zip_path"]):
        with open(st.session_state["final_zip_path"], "rb") as f:
            zip_data = f.read()

        st.download_button(
            label="Download Voiceovers (.zip)",
            data=zip_data,
            file_name="voiceovers.zip",
            mime="application/zip"
        )

def regenerate_task_audio(task, temp_dir):
    api_key = DataManager.get_api_key()
    if not api_key or not temp_dir:
        st.error("Missing API Key or Temp Directory.")
        return

    # Check Rate Limit
    allowed, msg = RateLimiter.check_limit()
    if not allowed:
        st.error(f"Cannot regenerate: {msg}")
        return

    # Generate new version
    version_count = len(task["versions"]) + 1
    output_filename = f"{task['filename']}_v{version_count}.wav"
    output_file = os.path.join(temp_dir, output_filename)

    voice = task["config"]["voice"]
    style = task["config"]["style"]

    try:
        success = generate_speech(
            api_key=api_key,
            text=task["text"],
            voice_name=voice,
            style_instructions=style,
            output_path=output_file
        )

        if success:
            RateLimiter.log_request()
            HistoryManager.add_entry(task["char_name"], task["text"], voice, style, output_file)
            task["versions"].append(output_file)
            task["selected_index"] = len(task["versions"]) - 1
            st.success(f"Regenerated {task['filename']}")
            st.rerun()
        else:
            st.error(f"Failed to regenerate {task['filename']}")
    except Exception as e:
        st.error(f"Error regenerating: {str(e)}")

def create_final_zip(results, temp_dir):
    if not temp_dir or not os.path.exists(temp_dir):
        st.error("Temporary directory not found.")
        return None

    zip_path = os.path.join(temp_dir, "voiceovers_final.zip")

    try:
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            for task in results:
                # Get selected version
                selected_file = task["versions"][task["selected_index"]]
                if os.path.exists(selected_file):
                    # Use original filename for the zip entry
                    zip_entry_name = f"{task['filename']}.wav"
                    zipf.write(selected_file, arcname=zip_entry_name)
        return zip_path
    except Exception as e:
        st.error(f"Error creating ZIP: {str(e)}")
        return None

if __name__ == "__main__":
    import sys
    from streamlit.web import cli as stcli
    from streamlit import runtime

    if runtime.exists():
        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
