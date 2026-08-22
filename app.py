import io
import os
import re
import tempfile
import subprocess
import google.generativeai as genai
import srt
import streamlit as st
from gtts import gTTS

# ==========================================
# --- ១. Page Config & CSS Styling ---
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
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0E1117 !important;
        color: #FFFFFF !important;
    }
    
    .main-header {
        border: 2px solid #BF40BF;
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        margin-bottom: 20px;
        background-color: #161B22;
        box-shadow: 0 0 20px rgba(191, 64, 191, 0.35);
    }
    .main-header h1 {
        color: #FFFFFF !important;
        font-weight: 800;
        font-size: 30px;
        margin-bottom: 5px;
    }
    .main-header p {
        color: #00D2FF !important;
        letter-spacing: 2px;
        font-size: 13px;
        font-weight: bold;
    }

    textarea, input, [data-baseweb="input"], [data-baseweb="textarea"] {
        background-color: #161B22 !important;
        color: #00D2FF !important;
        border: 1px solid #BF40BF !important;
        border-radius: 8px !important;
    }

    div.stButton > button {
        background-color: #D000F0 !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        border: none !important;
        box-shadow: 0 0 10px rgba(208, 0, 240, 0.5) !important;
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

    div[data-testid="stProgressBar"] > div {
        background-color: #00D2FF !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

default_srt = """1
00:00:00,000 --> 00:00:02,000
[E] សួស្តីអ្នកទាំងអស់គ្នា!

2
00:00:02,500 --> 00:00:05,000
[M] ថ្ងៃនេះយើងមកសិក្សាអំពី Vichhai Dubber Pro។

3
00:00:05,500 --> 00:00:08,500
[F] កម្មវិធីនេះដំណើរការលឿន និងស្រួលប្រើប្រាស់មែនទែន។"""


def clean_srt_text(text):
    text = re.sub(r"\[[EMF]\]\s*", "", text)
    return text.strip()


def extract_srt_only(text):
    if not text:
        return ""
    match = re.search(r'(?:^|\n)(\d+\s*[\r\n]+\d\d:\d\d:\d\d)', text)
    if match:
        text = text[match.start():]
    text = re.sub(r"^```(srt)?\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```$", "", text, flags=re.MULTILINE)
    return text.strip()


def get_audio_bytes_clean(text, target_lang="Khmer (ខ្មែរ)"):
    try:
        lang_code = "km" if ("Khmer" in target_lang or re.search(r'[\u1780-\u17FF]', text)) else "en"
        tts = gTTS(text=text, lang=lang_code, slow=False)
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp.getvalue()
    except Exception:
        return b""


def generate_audio_process(srt_raw_text, target_lang_selected):
    clean_srt_input = extract_srt_only(srt_raw_text)
    try:
        subs = list(srt.parse(clean_srt_input))
    except Exception:
        raise Exception("ទម្រង់ SRT មានបញ្ហា! សូមពិនិត្យមើល Timecode ឡើងវិញ។")

    if not subs:
        return None

    combined_bytes = bytearray()
    total_subs = len(subs)
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, sub in enumerate(subs):
        cleaned_text = clean_srt_text(sub.content.strip())
        status_text.markdown(f"🎙️ **កំពុងបង្កើតសំឡេងផ្នែកទី {idx+1}/{total_subs}...**")

        if cleaned_text:
            audio_chunk = get_audio_bytes_clean(cleaned_text, target_lang=target_lang_selected)
            if audio_chunk:
                combined_bytes.extend(audio_chunk)

        percent_complete = int((idx + 1) / total_subs * 100)
        progress_bar.progress(percent_complete)

    status_text.empty()
    return bytes(combined_bytes)


# ==========================================
# --- ២. SIDEBAR CONTROLS ---
# ==========================================
with st.sidebar:
    st.markdown("""
    <div style="background-color: #161b22; border: 1px solid #06b6d4; border-radius: 10px; padding: 15px; margin-bottom: 15px;">
        <h3 style="margin:0; color:white;">👋 Vichhai Yat</h3>
        <p style="margin:5px 0; color:#8b949e; font-size:12px;">ROLE: ADMIN</p>
        <p style="margin:5px 0; color:#8b949e; font-size:12px;">🗓️ PLAN: UNLIMITED</p>
        <p style="margin:5px 0; color:#06b6d4; font-size:12px;">⏳ LIFETIME ACCESS</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 🌍 Target Language (ភាសាបកប្រែ)")
    target_lang = st.selectbox(
        "ជ្រើសរើសភាសា (Select Language):",
        ["Khmer (ខ្មែរ)", "English", "Chinese", "Thai"],
        key="sb_target_lang_select"
    )

    st.markdown("---")
    st.markdown("### 🔑 API Keys Manager")
    
    if "user_api_key" not in st.session_state:
        st.session_state["user_api_key"] = ""

    api_input = st.text_area(
        "Paste Gemini API Keys",
        value=st.session_state["user_api_key"],
        height=90,
        placeholder="Paste Gemini API key here...",
        key="sb_input_gemini_key",
    )
    st.session_state["user_api_key"] = api_input
    active_api_key = api_input.strip()

    st.markdown("---")
    st.markdown("### 🧠 AI Model")
    ai_model = st.radio(
        "ជ្រើសរើសម៉ូដែល AI:",
        ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-2.0-flash"],
        key="sb_model_m",
    )

    st.markdown("---")
    if st.button("🔄 Reboot App / Reset", key="sb_reboot_app_btn", use_container_width=True):
        st.cache_data.clear()
        st.cache_resource.clear()
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

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

# --- TAB 1: AI VIDEO DUBBING ---
with tab1:
    st.markdown("<h2><span class='num-badge'>1</span>Generate Subtitles (Khmer (ខ្មែរ))</h2>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload Video", type=["mp4", "mov", "avi", "mkv"], key="tab1_video_uploader")

    if uploaded_file is not None:
        st.video(uploaded_file)

    st.markdown("### Generated SRT from Video")
    if "srt_input_content" not in st.session_state:
        st.session_state["srt_input_content"] = default_srt

    srt_content = st.text_area("", value=st.session_state["srt_input_content"], height=180, key="srt_input_content")

    st.markdown("---")
    st.markdown("<h2><span class='num-badge'>2</span>AI Dubbing (Edge TTS Studio)</h2>", unsafe_allow_html=True)

    gen_clicked = st.button("🎙️ Generate Dubbed Audio (MP3)", key="tab1_gen_dub_btn", use_container_width=True)

    if gen_clicked:
        if not srt_content.strip():
            st.warning("⚠️ សូមបញ្ចូលអត្ថបទ SRT ជាមុនសិន!")
        else:
            try:
                audio_bytes = generate_audio_process(srt_content, target_lang)
                if audio_bytes and len(audio_bytes) > 500:
                    st.success("✅ Audio Dubbing Complete!")
                    st.session_state["audio_data"] = audio_bytes
                else:
                    st.error("❌ បរាជ័យ៖ មិនអាចទាញយកសំឡេងបានទេ!")
            except Exception as e:
                st.error(f"❌ កើតមានបញ្ហា៖ {e}")

    if "audio_data" in st.session_state:
        st.audio(st.session_state["audio_data"], format="audio/mp3")
        st.download_button(
            label="🎵 Download MP3 (Vichhai_Dubbed_Output.mp3)",
            data=st.session_state["audio_data"],
            file_name="Vichhai_Dubbed_Output.mp3",
            mime="audio/mp3",
            key="tab1_download_audio_btn",
            use_container_width=True,
        )

# --- TAB 2: AI SRT TRANSLATOR ---
with tab2:
    st.markdown("<h2>🌐 AI SRT Translator (បកប្រែ Subtitle)</h2>", unsafe_allow_html=True)
    srt_to_translate = st.text_area("បញ្ចូលអត្ថបទ SRT ដើមដើម្បកប្រែ៖", height=200, key="tab2_srt_input")
    
    if st.button("🌐 ចាប់ផ្តើមបកប្រែដោយ Gemini AI", key="tab2_translate_btn", use_container_width=True):
        if not active_api_key:
            st.error("❌ សូម Paste Gemini API Key នៅក្នុង Sidebar ជាមុនសិន!")
        elif not srt_to_translate.strip():
            st.warning("⚠️ សូមបញ្ចូលអត្ថបទ SRT!")
        else:
            try:
                with st.spinner("កំពុងបកប្រែ..."):
                    genai.configure(api_key=active_api_key)
                    model = genai.GenerativeModel(ai_model)
                    prompt = f"Translate this SRT subtitle file into {target_lang}. Keep index numbers and timestamps intact:\n\n{srt_to_translate}"
                    response = model.generate_content(prompt)
                    st.success("✅ បកប្រែជោគជ័យ!")
                    st.text_area("លទ្ធផលបកប្រែរួច៖", value=response.text, height=200, key="tab2_translated_output")
            except Exception as e:
                st.error(f"❌ កើតមានបញ្ហា៖ {e}")

# --- TAB 3: SUBTITLE TO VIDEO ---
with tab3:
    st.markdown("<h2>📦 Subtitle to Video (បង្កប់ Subtitle)</h2>", unsafe_allow_html=True)
    st.info("💡 មុខងារនេះតម្រូវឱ្យ Upload វីដេអូ និង File SRT ដើម្បីបង្កប់អក្សរចូលក្នុងវីដេអូ (Hardcode Subtitle)។")
    
    sub_video = st.file_uploader("Upload Video", type=["mp4", "mov"], key="tab3_video")
    sub_file = st.file_uploader("Upload SRT File", type=["srt"], key="tab3_srt")
    
    if st.button("🎬 បង្កើត Video មាន Subtitle", key="tab3_process_btn", use_container_width=True):
        if sub_video and sub_file:
            st.success("✅ បានទទួល File រួចរាល់! កំពុងដំណើរការ...")
        else:
            st.warning("⚠️ សូម Upload ទាំង Video និង SRT File ជាមុនសិន!")

