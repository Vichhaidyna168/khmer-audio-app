import streamlit as st
import asyncio
import edge_tts
import tempfile
import os
import re
from datetime import datetime
from pydub import AudioSegment

# កំណត់ទម្រង់ទំព័រ Web App
st.set_page_config(
    page_title="Vichhai Dubber Pro",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling (CSS)
st.markdown("""
<style>
    .stApp {
        background-color: #0d0e15;
        color: #ffffff;
    }
    .main-banner {
        border: 2px solid #a855f7;
        border-radius: 16px;
        padding: 24px;
        text-align: center;
        background: linear-gradient(180deg, #13111c 0%, #0d0e15 100%);
        box-shadow: 0 4px 20px rgba(168, 85, 247, 0.2);
        margin-bottom: 25px;
    }
    .main-banner h1 {
        color: #ffffff;
        font-size: 32px;
        font-weight: 800;
        margin-bottom: 8px;
    }
    .main-banner p {
        color: #38bdf8;
        font-weight: 700;
        letter-spacing: 1.5px;
        font-size: 13px;
        margin: 0;
    }
    .step-header {
        font-size: 24px;
        font-weight: 700;
        margin-top: 20px;
        margin-bottom: 15px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .step-number {
        background-color: #3b82f6;
        color: white;
        padding: 2px 10px;
        border-radius: 6px;
    }
    .user-card {
        border: 1.5px solid #0284c7;
        background-color: #0f172a;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 20px;
    }
    .user-card h3 {
        margin: 0 0 10px 0;
        color: #ffffff;
        font-size: 18px;
    }
    .user-card p {
        margin: 4px 0;
        color: #94a3b8;
        font-size: 13px;
    }
    .success-box {
        background-color: #581c87;
        border: 1px solid #7e22ce;
        color: #ffffff;
        padding: 12px;
        border-radius: 8px;
        font-weight: 600;
        margin: 15px 0;
    }
    .stButton>button {
        width: 100%;
        border-radius: 8px;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# SIDEBAR
with st.sidebar:
    st.markdown("""
    <div class="user-card">
        <h3>👋 Vichhai Dubber Pro</h3>
        <p><b>ROLE:</b> ADMIN_USER</p>
        <p>📅 <b>PLAN:</b> 2026-12-31</p>
        <p>⏳ <b>365 DAYS LEFT</b></p>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🚪 ចាកចេញ (Logout)", key="logout"):
        st.info("បានចាកចេញពីប្រព័ន្ធ")

    st.divider()

    st.subheader("🌐 Target Language (ភាសាបកប្រែ)")
    target_lang = st.selectbox(
        "ជ្រើសរើសភាសា (Select Language):",
        ["Khmer (ខ្មែរ)", "English", "Thai", "Chinese"]
    )

    st.divider()

    st.subheader("🔑 API Keys Manager")
    api_keys_text = st.text_area(
        "Paste Gemini API Keys (One per line)",
        placeholder="AIzaSy...",
        height=80
    )
    
    if not api_keys_text.strip():
        st.warning("⚠️ សូមបញ្ចូល API Key ក្នុងប្រអប់ខាងឆ្វេងជាមុនសិន!")

    st.divider()

    st.subheader("🎭 Translation Style")
    trans_style = st.radio(
        "ជ្រើសរើសប្រព័ន្ធបកប្រែ (Translate API)៖",
        ["Gemini Api", "Google Api"]
    )

    st.divider()

    st.subheader("⚙️ Audio Sync Mode")
    sync_mode = st.radio(
        "តម្រឹមល្បឿនអាន៖",
        ["Speed Up Only (លឿន)", "Speed Up & Slow Down (លឿន និង យឺត)"]
    )

    st.divider()

    st.subheader("🗣️ Voice Mode (ជម្រើសសំឡេង)")
    voice_mode = st.radio(
        "កំណត់សម្រាប់ Tab 1 & Tab 2៖",
        ["Auto (ប្រុស/ស្រី តាម Tag)", "All Male (ប្រុសសុទ្ធ)", "All Female (ស្រីសុទ្ធ)"]
    )

    st.divider()

    st.subheader("🧠 AI Model (ម៉ូដែល AI)")
    ai_model = st.radio(
        "ជ្រើសរើសម៉ូដែល (Select Model):",
        [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ]
    )

# MAIN CONTENT
st.markdown("""
<div class="main-banner">
    <h1>Vichhai Dubber Pro</h1>
    <p>GLOBAL AI DUBBING & SUBTITLING WORKSTATION</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs([
    "🎬 AI Video Dubbing", 
    "🌐 AI SRT Translator", 
    "📜 Subtitle to Audio"
])

with tab1:
    st.markdown('<div class="step-header"><span class="step-number">1</span> Generate Subtitles (Khmer (ខ្មែរ))</div>', unsafe_allow_html=True)
    
    uploaded_video = st.file_uploader(
        "Upload Video", 
        type=["mp4", "mov", "avi", "mkv"],
        help="500MB per file • MP4, MOV, AVI, MKV"
    )

    st.subheader("Generated SRT from Video")
    st.caption("ពិនិត្យ និងកែសម្រួលអត្ថបទ SRT ទីនេះមុនពេលបញ្ចូលសំឡេង៖")
    
    sample_srt = """1
00:00:01,000 --> 00:00:04,000
ជម្រាបសួរ! ស្វាគមន៍មកកាន់ Vichhai Dubber Pro។

2
00:00:04,500 --> 00:00:08,000
ប្រព័ន្ធបង្កើត និងកាត់តសំឡេងស្វ័យប្រវត្តិដោយ AI។"""

    srt_content = st.text_area("", value=sample_srt, height=120)

    st.divider()

    st.markdown('<div class="step-header"><span class="step-number">2</span> AI Dubbing (Edge TTS Studio)</div>', unsafe_allow_html=True)
    
    if st.button("🎙️ Generate Dubbed Audio (MP3)", type="primary"):
        progress_text = st.empty()
        progress_bar = st.progress(0)
        
        for percent in range(1, 101):
            progress_bar.progress(percent)
            segment_num = int((percent / 100) * 23)
            progress_text.info(f"🎙️ Generating voice for segment {segment_num}/23...")
            asyncio.sleep(0.02)
        
        progress_text.empty()
        progress_bar.empty()
        
        st.markdown('<div class="success-box">✅ Audio Dubbing Complete!</div>', unsafe_allow_html=True)
        st.audio("https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")

        st.divider()

        st.subheader("💾 Download Options")
        custom_filename = st.text_input(
            "📝 បញ្ចូលឈ្មោះ File ដែលអ្នកចង់បាន (Optional):",
            placeholder="ឧទាហរណ៍: Episode_01_Dubbed"
        )

        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        final_name = custom_filename.strip() if custom_filename.strip() else f"Vichhai_Dubbed_Output_({date_str})"
        
        st.download_button(
            label=f"🎵 Download MP3 ({final_name}.mp3)",
            data=b"Audio content placeholder",
            file_name=f"{final_name}.mp3",
            mime="audio/mp3",
            type="primary"
        )

    st.write("")
    if st.button("🗑️ ធ្វើថ្មី (Clear Video Project)"):
        st.rerun()

with tab2:
    st.subheader("🌐 AI SRT Translator")
    st.info("មុខងារបកប្រែឯកសារ SRT ស្វ័យប្រវត្តិ")

with tab3:
    st.subheader("📜 Subtitle to Audio")
    st.info("មុខងារបំប្លែង Subtitle ទៅជាសំឡេង MP3")

