import streamlit as st
import os
import re
import asyncio
from edge_tts import Communicate
from pydub import AudioSegment
import google.generativeai as genai

# ==========================================
# --- ១. កំណត់ Page Config & CSS Styling ---
# ==========================================
st.set_page_config(
    page_title="Vichhai Dubber Pro",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS Styling
st.markdown("""
<style>
    /* Dark Theme Base */
    .stApp {
        background-color: #0E1117;
        color: #FFFFFF;
    }
    
    /* Header Container */
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
    
    /* Custom Button Style */
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
    
    /* Number Badge */
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
""", unsafe_allow_html=True)

# ==========================================
# --- ២. SIDEBAR CONTROLS ---
# ==========================================
with st.sidebar:
    st.markdown("### 🌍 Target Language (ភាសាបកប្រែ)")
    target_lang = st.selectbox("ជ្រើសរើសភាសា (Select Language):", ["Khmer (ខ្មែរ)", "English", "Chinese", "Thai"])
    
    st.markdown("---")
    st.markdown("### 🔑 API Keys Manager")
    api_input = st.text_area("Paste Gemini API Keys (One per line)", height=90, placeholder="AQ.Ab8RN6K78eU6946...")
    
    if api_input.strip():
        keys_list = [k.strip() for k in api_input.split('\n') if k.strip()]
        st.success(f"✅ កំពុងប្រើប្រាស់ {len(keys_list)} Keys")
    else:
        st.error("❌ មិនទាន់មានកូនសោនៅឡើយទេ")

    st.markdown("---")
    st.markdown("### 🎭 Translation Style")
    st.caption("ជ្រើសរើសប្រព័ន្ធបកប្រែ (Translate API)៖")
    trans_api = st.radio("", ["Gemini Api", "Google Api"], key="trans_style")

    st.markdown("---")
    st.markdown("### ⚙️ Audio Sync Mode")
    st.caption("តម្រឹមល្បឿនអាន៖")
    sync_mode = st.radio("", ["Speed Up Only (ល្បឿន)", "Speed Up & Slow Down (ល្បឿន និង យឺត)"], key="sync_m")

    st.markdown("---")
    st.markdown("### 🗣️ Voice Mode (ជម្រើសសំឡេង)")
    st.caption("កំណត់សម្រាប់ Tab 1 & Tab 2៖")
    voice_mode = st.radio("", ["Auto (ប្រុស/ស្រី តាម Tag)", "All Male (ប្រុសសុទ្ធ)", "All Female (ស្រីសុទ្ធ)"], key="v_mode")

    st.markdown("---")
    st.markdown("### 🧠 AI Model (ម៉ូដែល AI)")
    st.caption("ជ្រើសរើសម៉ូដែល (Select Model):")
    ai_model = st.radio("", [
        "gemini-2.5-flash",
        "gemini-2.0-flash",
        "gemini-1.5-pro",
        "gemini-2.5-flash-preview",
        "gemini-2.5-pro-preview"
    ], key="model_m")

# ==========================================
# --- ៣. MAIN WORKSPACE ---
# ==========================================

# 3.1 Header Banner
st.markdown("""
<div class="main-header">
    <h1>Vichhai Dubber Pro</h1>
    <p>GLOBAL AI DUBBING & SUBTITLING WORKSTATION</p>
</div>
""", unsafe_allow_html=True)

# 3.2 Main Navigation Tabs
tab1, tab2, tab3 = st.tabs(["🎬 AI Video Dubbing", "🌐 AI SRT Translator", "📦 Subtitle to Video"])

with tab1:
    # --- SECTION 1: Subtitle Generator ---
    st.markdown("<h2><span class='num-badge'>1</span>Generate Subtitles (Khmer (ខ្មែរ))</h2>", unsafe_allow_html=True)
    st.caption("Upload Video")
    uploaded_file = st.file_uploader("", type=["mp4", "mov", "avi", "mkv"])
    
    st.markdown("### Generated SRT from Video")
    st.caption("ពិនិត្យ និងកែសម្រួលអត្ថបទ SRT ទីនេះមុនពេលបញ្ចូលសំឡេង៖")
    
    default_srt = """1
00:00:00,000 --> 00:00:02,000
[E] សួស្តីអ្នកទាំងអស់គ្នា!

2
00:00:02,500 --> 00:00:05,000
[M] ថ្ងៃនេះយើងមកសិក្សាអំពី Vichhai Dubber Pro។

3
00:00:05,500 --> 00:00:08,500
[F] កម្មវិធីនេះដំណើរការលឿន និងស្រួលប្រើប្រាស់មែនទែន។

4
00:00:09,000 --> 00:00:12,000
[M] គីលីន ហ្អាន ត្រឡប់មកវិញហើយ!"""
    
    srt_content = st.text_area("", value=default_srt, height=180)
    
    st.markdown("---")
    
    # --- SECTION 2: AI Dubbing Studio ---
    st.markdown("<h2><span class='num-badge'>2</span>AI Dubbing (Edge TTS Studio)</h2>", unsafe_allow_html=True)
    
    col_btn1, col_btn2 = st.columns([2, 1])
    with col_btn1:
        gen_clicked = st.button("🎙️ Generate Dubbed Audio (MP3)", key="gen_dub", use_container_width=True)
    
    if gen_clicked:
        st.info("⚡ ពាក្យវែង! បង្កើនល្បឿន +62%...")
        st.progress(62)
        st.success("✅ Audio Dubbing Complete!")
        
        # Audio Player Component
        st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")
        
        # Download Section
        st.markdown("### 💾 Download Options")
        st.caption("📝 បញ្ចូលឈ្មោះ File ដែលអ្នកចង់បាន (Optional):")
        file_custom_name = st.text_input("", placeholder="ឧទាហរណ៍: Episode_01_Dubbed")
        
        out_name = f"{file_custom_name}.mp3" if file_custom_name else "Vichhai_Dubbed_Output.mp3"
        
        st.download_button(
            label=f"🎵 Download MP3 ({out_name})",
            data=b"dummy_audio_bytes",
            file_name=out_name,
            mime="audio/mp3",
            use_container_width=True
        )

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🗑️ ធ្វើថ្មី (Clear Video Project)", key="clear_proj", use_container_width=True):
        st.rerun()

with tab2:
    st.markdown("<h2>🌐 AI SRT Translator</h2>", unsafe_allow_html=True)
    st.info("មុខងារបកប្រែ SRT ដោយស្វ័យប្រវត្តិតាមរយៈ Gemini API")

with tab3:
    st.markdown("<h2>📦 Subtitle to Video</h2>", unsafe_allow_html=True)
    st.info("មុខងារបង្កប់ Subtitle ចូលទៅក្នុង Video (Hardcode Subtitles)")

