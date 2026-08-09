import streamlit as st
import asyncio
import edge_tts
import tempfile
import os

st.set_page_config(
    page_title="Vichhai Dubber Pro",
    page_icon="🎬",
    layout="wide"
)

st.title("🎬 Vichhai Dubber Pro")
st.caption("GLOBAL AI DUBBING & SUBTITLING WORKSTATION")

with st.sidebar:
    st.header("👋 Vichhai Dubber Pro")
    st.text("ROLE: ADMIN_USER")
    st.text("PLAN: 2026-12-31")
    
    if st.button("🚪 ចាកចេញ (Logout)", key="logout"):
        st.info("បានចាកចេញពីប្រព័ន្ធ")

    st.divider()
    target_lang = st.selectbox("🌐 Target Language:", ["Khmer (ខ្មែរ)", "English", "Thai", "Chinese"])
    api_keys_text = st.text_area("🔑 Paste Gemini API Keys", placeholder="AIzaSy...", height=80)
    trans_style = st.radio("🎭 Translation Style", ["Gemini Api", "Google Api"])
    sync_mode = st.radio("⚙️ Audio Sync Mode", ["Speed Up Only (លឿន)", "Speed Up & Slow Down"])
    voice_mode = st.radio("🗣️ Voice Mode", ["Auto (ប្រុស/ស្រី)", "All Male", "All Female"])
    ai_model = st.radio("🧠 AI Model", ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-1.5-flash"])

tab1, tab2, tab3 = st.tabs(["🎬 AI Video Dubbing", "🌐 AI SRT Translator", "📜 Subtitle to Audio"])

async def generate_audio_file(text, voice_name, output_path):
    communicate = edge_tts.Communicate(text, voice_name)
    await communicate.save(output_path)

with tab1:
    st.subheader("1️⃣ Generate Subtitles (Khmer (ខ្មែរ))")
    uploaded_video = st.file_uploader("Upload Video", type=["mp4", "mov", "avi", "mkv"])
    
    sample_srt = "1\n00:00:01,000 --> 00:00:04,000\nជម្រាបសួរ! ស្វាគមន៍មកកាន់ Vichhai Dubber Pro Control Panel។"
    srt_content = st.text_area("Generated SRT from Video", value=sample_srt, height=120)

    st.divider()
    st.subheader("2️⃣ AI Dubbing (Edge TTS Studio)")
    
    voice_choice = st.selectbox("ជ្រើសរើសសំឡេង (Khmer Voice):", ["km-KH-PisethNeural", "km-KH-SreymomNeural"])
    
    if st.button("🎙️ Generate Dubbed Audio (MP3)", type="primary"):
        if not srt_content.strip():
            st.warning("សូមបញ្ចូលអត្ថបទជាមុនសិន!")
        else:
            with st.spinner("កំពុងបង្កើតសំឡេង..."):
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
                        output_file = tmp_file.name

                    lines = [line for line in srt_content.split('\n') if not line.isdigit() and '-->' not in line and line.strip()]
                    clean_text = " ".join(lines)
                    
                    asyncio.run(generate_audio_file(clean_text, voice_choice, output_file))

                    st.success("✅ Audio Dubbing Complete!")
                    st.audio(output_file, format="audio/mp3")
                    
                    st.divider()
                    custom_filename = st.text_input("📝 បញ្ចូលឈ្មោះ File ដែលអ្នកចង់បាន (Optional):")
                    final_name = custom_filename.strip() if custom_filename.strip() else "Vichhai_Dubbed_Output"
                    
                    with open(output_file, "rb") as f:
                        st.download_button(
                            label=f"🎵 Download MP3 ({final_name}.mp3)",
                            data=f,
                            file_name=f"{final_name}.mp3",
                            mime="audio/mp3",
                            type="primary"
                        )
                except Exception as e:
                    st.error(f"កើតមានបញ្ហា៖ {e}")

with tab2:
    st.info("🌐 មុខងារបកប្រែឯកសារ SRT ស្វ័យប្រវត្តិ")

with tab3:
    st.info("📜 មុខងារបំប្លែង Subtitle ទៅជាសំឡេង MP3")



