import streamlit as st
import os
import tempfile
import shutil
import zipfile
from data_manager import DataManager
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
        generate_audio_batch(script_input)

def generate_audio_batch(script_text: str):
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
            "config": characters[char_name]
        })

    if errors:
        for err in errors:
            st.error(err)
        return

    # Generation Process
    progress_bar = st.progress(0)
    status_text = st.empty()

    # Create temp directory
    with tempfile.TemporaryDirectory() as temp_dir:
        generated_files = []

        for idx, task in enumerate(parsed_tasks):
            char_name = task["char_name"]
            status_text.text(f"Generating audio for: {task['filename']} ({char_name})...")

            output_file = os.path.join(temp_dir, f"{task['filename']}.wav")
            voice = task["config"]["voice"]
            style = task["config"]["style"]

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
                    generated_files.append(output_file)
                else:
                    st.error(f"Failed to generate audio for {task['filename']}")
            except Exception as e:
                st.error(f"Error generating {task['filename']}: {str(e)}")

            progress_bar.progress((idx + 1) / len(parsed_tasks))

        if generated_files:
            # Create ZIP
            zip_path = os.path.join(temp_dir, "voiceovers.zip")
            with zipfile.ZipFile(zip_path, 'w') as zipf:
                for file_path in generated_files:
                    zipf.write(file_path, arcname=os.path.basename(file_path))

            # Read ZIP into memory for download button
            with open(zip_path, "rb") as f:
                zip_data = f.read()

            st.success("Generation Complete!")
            st.download_button(
                label="Download Voiceovers (.zip)",
                data=zip_data,
                file_name="voiceovers.zip",
                mime="application/zip"
            )
        else:
            st.warning("No files were generated.")

if __name__ == "__main__":
    import sys
    from streamlit.web import cli as stcli
    sys.argv = ["streamlit", "run", sys.argv[0]]
    sys.exit(stcli.main())

main()
