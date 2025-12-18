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

        st.divider()

        # Model Selection
        st.subheader("Model Selection")
        available_models = DataManager.get_models()
        active_model = DataManager.get_active_model()

        # Ensure active_model is valid (handle edge cases where list might be empty or out of sync)
        if not available_models:
             # Should be handled by DataManager logic, but just in case
             available_models = ["gemini-2.5-pro-tts"]
             active_model = "gemini-2.5-pro-tts"

        selected_model = st.selectbox(
            "Select Gemini Model",
            options=available_models,
            index=available_models.index(active_model) if active_model in available_models else 0
        )

        if selected_model != active_model:
            DataManager.set_active_model(selected_model)
            st.rerun()

        # Manage Models
        with st.expander("Manage Models"):
            new_model_name = st.text_input("Add new model", placeholder="e.g. gemini-1.5-pro")
            if st.button("Add Model"):
                if new_model_name and new_model_name.strip():
                    DataManager.add_model(new_model_name.strip())
                    st.success(f"Added {new_model_name}")
                    st.rerun()

            st.caption("Existing Models:")
            for m in available_models:
                col_m1, col_m2 = st.columns([4, 1])
                with col_m1:
                    st.write(m)
                with col_m2:
                    if st.button("🗑️", key=f"del_model_{m}", help=f"Delete {m}"):
                        DataManager.delete_model(m)
                        st.rerun()

        # Rate Limits (Per Selected Model)
        limit_min, limit_day = DataManager.get_limits(selected_model)
        st.caption(f"Rate Limits for **{selected_model}**")
        col_lim1, col_lim2 = st.columns(2)
        # Rate Limit Charts
        stats = RateLimiter.get_usage_stats(selected_model)

        with col_lim1:
            new_limit_min = st.number_input("Req / Min", value=limit_min, min_value=1, key=f"lim_min_{selected_model}")
            fig_min = create_donut_chart(stats["used_min"], new_limit_min, "Used")
            st.plotly_chart(fig_min, use_container_width=True, config={'displayModeBar': False})

        with col_lim2:
            new_limit_day = st.number_input("Req / Day", value=limit_day, min_value=1, key=f"lim_day_{selected_model}")
            fig_day = create_donut_chart(stats["used_day"], new_limit_day, "Used")
            st.plotly_chart(fig_day, use_container_width=True, config={'displayModeBar': False})

        if new_limit_min != limit_min or new_limit_day != limit_day:
            DataManager.save_limits(new_limit_min, new_limit_day, selected_model)
            st.success(f"Limits saved for {selected_model}!")

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


def create_donut_chart(current, limit, title):
    remaining = max(0, limit - current)
    # If over limit, remaining is 0, but current shows full usage

    # Colors: Used (Blue), Remaining (Light Gray)
    # If over limit, Used becomes Red
    color_used = "#1f77b4"
    if current >= limit:
        color_used = "#d62728" # Red

    fig = go.Figure(data=[go.Pie(
        labels=['Used', 'Remaining'],
        values=[current, remaining],
        hole=.7,
        marker_colors=[color_used, "#e6e6e6"],
        textinfo='none', # Hide labels on the chart itself
        sort=False
    )])

    fig.update_layout(
        annotations=[dict(text=f"{current}/{limit}", x=0.5, y=0.5, font_size=20, showarrow=False)],
        showlegend=False,
        height=120,
        margin=dict(l=20, r=20, t=20, b=0),
        paper_bgcolor='rgba(0,0,0,0)'
    )
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

    # Get Active Model
    active_model = DataManager.get_active_model()

    for idx, task in enumerate(parsed_tasks):
        char_name = task["char_name"]
        status_text.text(f"Generating audio for: {task['filename']} ({char_name})...")

        # Initial version file
        output_filename = f"{task['filename']}_v1.wav"
        output_file = os.path.join(temp_dir, output_filename)
        voice = task["config"]["voice"]
        style = task["config"]["style"]

        # Check Rate Limit
        allowed, msg = RateLimiter.check_limit(active_model)
        if not allowed:
            st.error(f"Stopped at {task['filename']}: {msg}")
            break

        try:
            # Get Active Model for generation
            active_model = DataManager.get_active_model()

            # Call TTS Engine
            success = generate_speech(
                api_key=api_key,
                text=task["text"],
                voice_name=voice,
                style_instructions=style,
                output_path=output_file,
                model_name=active_model
            )

            if success:
                RateLimiter.log_request(active_model)
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

    # Get Active Model
    active_model = DataManager.get_active_model()

    # Check Rate Limit
    allowed, msg = RateLimiter.check_limit(active_model)
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
            output_path=output_file,
            model_name=active_model
        )

        if success:
            RateLimiter.log_request(active_model)
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
