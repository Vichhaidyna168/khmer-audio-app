import asyncio
import os
import re
import edge_tts
import google.generativeai as genai
import streamlit as st

# កំណត់ Code ឈ្មោះសំឡេង Edge-TTS ខ្មែរ
VOICE_MALE = "km-KH-PisethNeural"
VOICE_FEMALE = "km-KH-SreymomNeural"

st.set_page_config(page_title="Vichhai Dubber Pro", layout="wide")

# ==========================================
# 1. SIDEBAR: GEMINI API KEY INTEGRATION
# ==========================================
st.sidebar.header("⚙️ Configuration")
raw_api_key = st.sidebar.text_input(
    "🔑 Paste Gemini API Keys", type="password", key="user_gemini_key"
)
api_key = raw_api_key.strip() if raw_api_key else ""

gemini_ready = False
if api_key:
    try:
        genai.configure(api_key=api_key)
        gemini_ready = True
        st.sidebar.success("✅ Gemini API ភ្ជាប់បានជោគជ័យ!")
    except Exception as e:
        st.sidebar.error(f"❌ API Key មិនត្រឹមត្រូវ: {str(e)}")
else:
    st.sidebar.warning("⚠️ សូមបញ្ចូល Gemini API Key ដើម្បីដំណើរការ")

# ==========================================
# 2. MAIN PAGE: VIDEO PLAYER & SRT AREA
# ==========================================
st.title("Vichhai Dubber Pro Control Panel")

uploaded_file = st.file_uploader(
    "📤 Upload Video File", type=["mp4", "mov", "avi", "mkv"]
)

# ប្រអប់ចាក់វីដេអូខាងលើ
if uploaded_file is not None:
    st.subheader("📹 វីដេអូដើម (Video Preview)")
    st.video(uploaded_file)
    st.divider()

st.subheader("📝 Generated SRT from Video")
srt_content = st.text_area(
    label="",
    value="1\n00:00:01,000 --> 00:00:04,000\n[Male] ជម្រាបសួរ! ស្វាគមន៍មកកាន់ប្រព័ន្ធ Dubbing។\n\n2\n00:00:04,500 --> 00:00:08,000\n[Female] ចាស សួស្តី! តើថ្ងៃនេះមានអ្វីឱ្យខ្ញុំជួយដែរទេ?",
    height=180,
)

st.divider()

# ==========================================
# 3. AI DUBBING: VOICE SELECTION (3 ជម្រើស)
# ==========================================
st.header("2️⃣ AI Dubbing (Edge TTS Studio)")

# ជម្រើសសំឡេងទាំង ៣
voice_mode = st.selectbox(
    "ជ្រើសរើសប្រភេទសំឡេង (Voice Mode):",
    ["Auto (ប្រុស/ស្រី)", "Male Only (ប្រុស)", "Female Only (ស្រី)"],
)


# Function កំណត់សំឡេងតាម Mode
def determine_voice(text_line, mode):
    if mode == "Male Only (ប្រុស)":
        return VOICE_MALE
    elif mode == "Female Only (ស្រី)":
        return VOICE_FEMALE
    else:
        # Mode Auto: ពិនិត្យមើល Tag [Female] ឬ [Male] ក្នុងអត្ថបទ
        if "[Female]" in text_line or "[ស្រី]" in text_line:
            return VOICE_FEMALE
        return VOICE_MALE


# ប៊ូតុង Generate និង Clear
generate_btn = st.button("🎙️ Generate Dubbed Audio (MP3)", type="primary")
clear_btn = st.button("🗑️ Clear / Reset All")

# Async Function សម្រាប់បង្កើត Audio Clips តាមបន្ទាត់នីមួយៗ
async def generate_tts_audio(srt_text, selected_mode):
    lines = srt_text.strip().split("\n\n")
    audio_files = []

    for idx, block in enumerate(lines):
        text_lines = block.split("\n")
        if len(text_lines) >= 3:
            dialogue = text_lines[2]

            # ជ្រើសរើស Voice ID តាម Mode
            chosen_voice = determine_voice(dialogue, selected_mode)

            # លុប Tag សំគាល់ [Male] / [Female] ចោលមុននឹងឱ្យ TTS អាន
            clean_text = re.sub(
                r"\[(Male|Female|ប្រុស|ស្រី)\]", "", dialogue
            ).strip()

            output_file = f"temp_segment_{idx}.mp3"
            communicate = edge_tts.Communicate(clean_text, chosen_voice)
            await communicate.save(output_file)
            audio_files.append(output_file)

    return audio_files


if generate_btn:
    if not gemini_ready and voice_mode == "Auto (ប្រុស/ស្រី)":
        st.warning(
            "⚠️ ប្រព័ន្ធកំពុងប្រើប្រាស់ Local Tagging សម្រាប់ Auto Voice Mode"
        )

    st.info(
        f"⏳ កំពុងបង្កើតសំឡេងតាមជម្រើស៖ {voice_mode}..."
    )

    # ដំណើរការបង្កើត TTS Audio
    generated_files = asyncio.run(generate_tts_audio(srt_content, voice_mode))
    st.success(
        f"✅ បង្កើតសំឡេងបានជោគជ័យចំនួន {len(generated_files)} Segment!"
    )

if clear_btn:
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.rerun()
