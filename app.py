
import asyncio
import io
import os
import re
import time
from edge_tts import Communicate
import google.generativeai as genai
import streamlit as st

# ==========================================
# --- ១. កំណត់ Page Config & CSS Styling ---
# ==========================================
st.set_page_config(
    page_title="Vichhai Dubber Pro",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    .main-header {
        border: 2px solid #BF40BF;
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        margin-bottom: 25px;
        background-color: #161B22;
        box-shadow: 0 0 20px rgba(191, 64, 191, 0.35);
    }
    .main-header h1 {
        color: #FFFFFF;
        font-weight: 800;
        font-size: 32px;
        margin-bottom: 5px;
    }
    .main-header p {
        color: #00D2FF;
        letter-spacing: 2px;
        font-size: 13px;
        font-weight: bold;
    }
    div.stButton > button[key="gen_dub"] {
        background-color: #D000F0 !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        height: 50px !important;
        font-size: 16px !important;
        border: none !important;
    }
    div.stButton > button[key="clear_proj"] {
        background-color: #6A008A !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        height: 45px !important;
        border: none !important;
    }
    .num-badge {
        background-color: #3B4252;
        color: #ECEFF4;
        padding: 4px 12px;
        border-radius: 8px;
        font-size: 22px;
        font-weight: bold;
        margin-right: 10px;
    }
</style>
""",
    unsafe_allow_html=True,
)

VOICES = {"Male": "km-KH-PisethNeural", "Female": "km-KH-SreymomNeural"}

default_srt = """1
00:00:00,000 --> 00:00:02,000
[E] សួស្តីអ្នកទាំងអស់គ្នា!

2
00:00:02,500 --> 00:00:05,000
[M] ថ្ងៃនេះយើងមកសិក្សាអំពី Vichhai Dubber Pro។

3
00:00:05,500 --> 00:00:08,500
[F] កម្មវិធីនេះដំណើរការលឿន និងស្រួលប្រើប្រាស់មែនទែន។"""

# មុខងារទាញយក Audio Bytes ដោយផ្ទាល់
async def get_audio_bytes(text, voice_code):
    communicate = Communicate(text, voice_code)
    out = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            out.write(chunk["data"])
    return out.getvalue()

def clean_srt_line(text):
    text = re.sub(r"^\d+\s*$", "", text)
    text = re.sub(
        r"\d{2}:\d{2}:\d{2}[,\.]\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}[,\.]\d{3}",
        "",
        text,
    )
    text = re.sub(r"\[[EMF]\]\s*", "", text)
    return text.strip()

# ==========================================
# --- ២. SIDEBAR CONTROLS ---
# ==========================================
with st.sidebar:
    st.markdown("### 🌍 Target Language (ភាសាបកប្រែ)")
    target_lang = st.selectbox(
        "ជ្រើសរើសភាសា (Select Language):",
        ["Khmer (ខ្មែរ)", "English", "Chinese", "Thai"],
    )

    st.markdown("---")
    st.markdown("### 🔑 API Keys Manager")
    api_input = st.text_area(
        "Paste Gemini API Keys (One per line)",
        height=90,
        placeholder="AQ.Ab8RN6K78eU6946...",
    )

    active_api_key = None
    if api_input.strip():
        keys_list = [k.strip() for k in api_input.split("\n") if k.strip()]
        st.success(f"✅ កំពុងប្រើប្រាស់ {len(keys_list)} Keys")
        active_api_key = keys_list[0]
    else:
        st.error("❌ មិនទាន់មានកូនសោនៅឡើយទេ")

    st.markdown("---")
    st.markdown("### 🎭 Translation Style")
    trans_api = st.radio("", ["Gemini Api", "Google Api"], key="trans_style")

    st.markdown("---")
    st.markdown("### ⚙️ Audio Sync Mode")
    sync_mode = st.radio(
        "",
        [
            "Speed Up Only (ល្បឿន)",
            "Speed Up & Slow Down (ល្បឿន និង យឺត)",
        ],
        key="sync_m",
    )

    st.markdown("---")
    st.markdown("### 🗣️ Voice Mode (ជម្រើសសំឡេង)")
    voice_mode = st.radio(
        "",
        [
            "Auto (ប្រុស/ស្រី តាម Tag)",
            "All Male (ប្រុសសុទ្ធ)",
            "All Female (ស្រីសុទ្ធ)",
        ],
        key="v_mode",
    )

# ==========================================
# --- ៣. MAIN WORKSPACE ---
# ==========================================
st.markdown(
    """
<div class="main-header">
    <h1>Vichhai Dubber Pro</h1>
    <p>GLOBAL AI DUBBING & SUBTITLING WORKSTATION</p>
</div>
""",
    unsafe_allow_html=True,
)

tab1, tab2, tab3 = st.tabs(["🎬 AI Video Dubbing", "🌐 AI SRT Translator", "📦 Subtitle to Video"])

with tab1:
    st.markdown("<h2><span class='num-badge'>1</span>Generate Subtitles</h2>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload Video", type=["mp4", "mov", "avi", "mkv"])

    if uploaded_file is not None:
        st.video(uploaded_file)

    st.markdown("### Generated SRT from Video")
    if "srt_input_content" not in st.session_state:
        st.session_state["srt_input_content"] = default_srt

    srt_content = st.text_area("", height=180, value=st.session_state["srt_input_content"], key="srt_input_content")

    st.markdown("---")
    st.markdown("<h2><span class='num-badge'>2</span>AI Dubbing Studio</h2>", unsafe_allow_html=True)

    if st.button("🎙️ Generate Dubbed Audio (MP3)", key="gen_dub", use_container_width=True):
        if not srt_content.strip():
            st.warning("⚠️ សូមបញ្ចូលអត្ថបទ SRT សិន!")
        else:
            try:
                with st.spinner("កំពុងបង្កើតសម្លេង..."):
                    clean_text = re.sub(r'\[.*?\]', '', srt_content)
                    clean_text = re.sub(r'\d+\n\d\d:\d\d:\d\d,\d+ --> \d\d:\d\d:\d\d,\d+', '', clean_text)
                    
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    audio_bytes = loop.run_until_complete(get_audio_bytes(clean_text, "km-KH-PisethNeural"))
                    
                    if audio_bytes and len(audio_bytes) > 100:
                        st.success("✅ Audio Dubbing Complete!")
                        st.audio(audio_bytes, format="audio/mp3")
                        st.download_button(
                            label="🎵 Download MP3",
                            data=audio_bytes,
                            file_name="Vichhai_Dubbed_Output.mp3",
                            mime="audio/mp3",
                            use_container_width=True,
                        )
                    else:
                        st.error("❌ មិនអាចទាញយកសម្លេងបានទេ!")
            except Exception as e:
                st.error(f"❌ កើតបញ្ហា៖ {e}")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ ធ្វើថ្មី (Clear Project)", key="clear_proj", use_container_width=True):
        st.session_state["srt_input_content"] = ""
        st.rerun()

with tab2:
    st.markdown("<h2>🌐 AI SRT Translator</h2>", unsafe_allow_html=True)
    srt_to_translate = st.text_area("បញ្ចូល SRT ដើម៖", height=150, key="trans_input")
    if st.button("🌐 បកប្រែដោយ Gemini"):
        if not active_api_key:
            st.error("❌ សូមใส่ API Key ใน Sidebar សិន!")
        elif not srt_to_translate.strip():
            st.warning("⚠️ សូមបញ្ចូលអត្ថបទ SRT!")
        else:
            try:
                genai.configure(api_key=active_api_key)
                model = genai.GenerativeModel("gemini-1.5-flash")
                response = model.generate_content(f"Translate subtitle to {target_lang}. Keep timestamps intact:\n\n{srt_to_translate}")
                st.success("✅ បកប្រែជោគជ័យ!")
                st.text_area("លទ្ធផល:", value=response.text, height=180)
            except Exception as e:
                st.error(f"❌ Error: {e}")

with tab3:
    st.markdown("<h2>📦 Subtitle to Video</h2>", unsafe_allow_html=True)
    st.info("មុខងារបង្កប់ Subtitle ចូល Video")

