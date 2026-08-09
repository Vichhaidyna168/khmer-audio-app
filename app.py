import streamlit as st
import asyncio
import edge_tts
import tempfile
import os
import re
from datetime import datetime
from pydub import AudioSegment
from google import genai
from google.genai import types
import shutil
import imageio_ffmpeg
ffmpeg_path = shutil.which("ffmpeg")
if not ffmpeg_path:
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()

AudioSegment.converter = ffmpeg_path
AudioSegment.ffmpeg = ffmpeg_path
AudioSegment.ffprobe = ffmpeg_path
os.environ["PATH"] += os.pathsep + os.path.dirname(ffmpeg_path)

# Set page layout
st.set_page_config(
    page_title="Vichhai Dubber Pro",
    page_icon="🎬",
    layout="wide"
)

# Custom Styling to match the dark / purple theme in screenshots
st.markdown("""
    <style>
    .main-header {
        border: 2px solid #8a2be2;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        background-color: #0e0e17;
        margin-bottom: 20px;
    }
    .main-header h1 {
        color: #ffffff;
        font-weight: 800;
        margin-bottom: 5px;
    }
    .main-header p {
        color: #00d2ff;
        font-weight: 600;
        letter-spacing: 1.5px;
    }
    .stButton>button {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- SIDEBAR CONFIGURATION -----------------
with st.sidebar:
    st.title("🌍 Target Language (ភាសាបកប្រែ)")
    target_lang = st.selectbox(
        "ជ្រើសរើសភាសា (Select Language):",
        ["Khmer (ខ្មែរ)", "English", "Thai", "Chinese", "Vietnamese"]
    )
    
    st.markdown("---")
    st.title("🔑 API Keys Manager")
    api_keys_raw = st.text_area(
        "Paste Gemini API Keys (One per line)",
        height=100,
        placeholder="AIzaSy..."
    )
    
    api_keys = [k.strip() for k in api_keys_raw.split("\n") if k.strip()]
    
    if not api_keys:
        st.warning("⚠️ សូមបញ្ចូល API Key ក្នុងប្រអប់ខាងឆ្វេងជាមុនសិន!")
    
    st.markdown("---")
    st.title("🎭 Translation Style")
    translate_api = st.radio(
        "ជ្រើសរើសប្រព័ន្ធបកប្រែ (Translate API)៖",
        ["Gemini Api", "Google Api"]
    )
    
    st.markdown("---")
    st.title("⚙️ Audio Sync Mode")
    sync_mode = st.radio(
        "តម្រឹមកម្រិតល្បឿនអាន៖",
        ["Speed Up Only (លឿន)", "Speed Up & Slow Down (លឿន និង យឺត)"]
    )
    
    st.markdown("---")
    st.title("🗣️ Voice Mode (ជម្រើសសំឡេង)")
    st.caption("កំណត់សម្រាប់ Tab 1 & Tab 2៖")
    voice_mode = st.radio(
        "Voice Mode Option",
        ["Auto (ប្រុស/ស្រី តាម Tag)", "All Male (ប្រុសសុទ្ធ)", "All Female (ស្រីសុទ្ធ)"],
        label_visibility="collapsed"
    )
    
    st.markdown("---")
    st.title("🧠 AI Model (ម៉ូដែល AI)")
    ai_model = st.radio(
        "ជ្រើសរើសម៉ូដែល (Select Model):",
        [
            "gemini-2.5-flash",
            "gemini-2.5-pro",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro"
        ]
    )

# ----------------- MAIN INTERFACE -----------------

st.markdown("""
    <div class="main-header">
        <h1>Matly Dubber Pro</h1>
        <p>GLOBAL AI DUBBING & SUBTITLING WORKSTATION</p>
    </div>
""", unsafe_allow_html=True)

# Tabs
tab1, tab2, tab3 = st.tabs([
    "🎬 AI Video Dubbing", 
    "🌐 AI SRT Translator", 
    "📦 Subtitle to Voice"
])

# Utility Functions
def parse_srt(srt_text):
    """Parse SRT text into segments with timestamps and text."""
    pattern = re.compile(r'(\d+)\n(\d{2}:\d{2}:\d{2},\d{3}) --> (\d{2}:\d{2}:\d{2},\d{3})\n([\s\S]*?)(?=\n\d+\n|\Z)')
    matches = pattern.findall(srt_text)
    segments = []
    for m in matches:
        index, start_str, end_str, text = m
        text = text.strip()
        
        # Gender tagging detection
        gender = "M"
        if text.startswith("[F]") or "[ស្រី]" in text:
            gender = "F"
            text = re.sub(r'\[(F|ស្រី)\]', '', text).strip()
        elif text.startswith("[M]") or "[ប្រុស]" in text:
            gender = "M"
            text = re.sub(r'\[(M|ប្រុស)\]', '', text).strip()

        segments.append({
            "index": index,
            "start": start_str,
            "end": end_str,
            "text": text,
            "gender": gender
        })
    return segments

def timestamp_to_ms(ts):
    """Convert SRT timestamp (HH:MM:SS,mmm) to milliseconds."""
    parts = ts.replace(',', ':').split(':')
    hours, minutes, seconds, millis = map(int, parts)
    return (hours * 3600 + minutes * 60 + seconds) * 1000 + millis

async def generate_single_audio(text, voice, output_file):
    """Generate audio using Edge TTS."""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

# --- TAB 1: AI VIDEO DUBBING ---
with tab1:
    st.header("1️⃣ Generate Subtitles (Khmer (ខ្មែរ))")
    
    uploaded_video = st.file_uploader(
        "Upload Video", 
        type=["mp4", "mov", "avi", "mkv"],
        help="500MB per file • MP4, MOV, AVI, MKV"
    )
    
    if "srt_content" not in st.session_state:
        st.session_state.srt_content = ""

    if uploaded_video is not None:
        if st.button("🎙️ ទាញយក Subtitle ចេញពីវីដេអូ (Generate SRT)"):
            if not api_keys:
                st.error("សូមបញ្ចូល Gemini API Key នៅក្នុង Sidebar ជាមុនសិន!")
            else:
                with st.spinner("កំពុងស្តាប់ និងបង្កើត Subtitle ភាសាខ្មែរ..."):
                    try:
                        # Save temp video
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_file:
                            tmp_file.write(uploaded_video.read())
                            tmp_path = tmp_file.name

                        client = genai.Client(api_key=api_keys[0])
                        video_file = client.files.upload(file=tmp_path)
                        
                        prompt = (
                            "Listen to this video and generate a precise SRT subtitle in Khmer script. "
                            "Add gender tags [M] for male speaker and [F] for female speaker before each line text. "
                            "Example:\n1\n00:00:01,000 --> 00:00:04,000\n[M] ជំរាបសួរអ្នកទាំងអស់គ្នា"
                        )
                        
                        response = client.models.generate_content(
                            model=ai_model,
                            contents=[video_file, prompt]
                        )
                        
                        st.session_state.srt_content = response.text
                        os.remove(tmp_path)
                        st.success("បង្កើត Subtitle ជោគជ័យ!")
                    except Exception as e:
                        st.error(f"មានបញ្ហាក្នុងការដំណើរការ៖ {str(e)}")

    st.subheader("Generated SRT from Video")
    st.caption("ពិនិត្យ និងកែសម្រួលអត្ថបទ SRT ទីនេះមុនពេលបញ្ចូលសំឡេង៖")
    
    edited_srt = st.text_area(
        "SRT Content Editor",
        value=st.session_state.srt_content,
        height=200,
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.header("2️⃣ AI Dubbing (Edge TTS Studio)")
    
    col1, col2 = st.columns([1, 1])
    
    if "dubbed_audio_path" not in st.session_state:
        st.session_state.dubbed_audio_path = None

    with col1:
        if st.button("🎤 Generate Dubbed Audio (MP3)", type="primary"):
            if not edited_srt.strip():
                st.warning("សូមបញ្ជូល ឬបង្កើតអត្ថបទ SRT ជាមុនសិន!")
            else:
                segments = parse_srt(edited_srt)
                if not segments:
                    st.error("ទម្រង់ SRT មិនត្រឹមត្រូវទេ!")
                else:
                    status_box = st.info("កំពុងរៀបចំបង្កើតសំឡេង...")
                    progress_bar = st.progress(0)
                    
                    combined_audio = AudioSegment.silent(duration=1000) # Start with silent base
                    
                    # Voices mapping for Khmer
                    male_voice = "km-KH-PisethNeural"
                    female_voice = "km-KH-SreymomNeural"
                    
                    for idx, seg in enumerate(segments):
                        status_box.text(f"🎙️ Generating voice for segment {idx+1}/{len(segments)}...")
                        
                        # Voice selection logic based on sidebar
                        if "All Male" in voice_mode:
                            selected_voice = male_voice
                        elif "All Female" in voice_mode:
                            selected_voice = female_voice
                        else:
                            selected_voice = female_voice if seg["gender"] == "F" else male_voice
                        
                        temp_segment_file = f"seg_{idx}.mp3"
                        asyncio.run(generate_single_audio(seg["text"], selected_voice, temp_segment_file))
                        
                        if os.path.exists(temp_segment_file):
                            seg_audio = AudioSegment.from_file(temp_segment_file)
                            
                            # Speed sync adjustment
                            target_duration = timestamp_to_ms(seg["end"]) - timestamp_to_ms(seg["start"])
                            actual_duration = len(seg_audio)
                            
                            if target_duration > 0 and actual_duration > 0:
                                speed_factor = actual_duration / target_duration
                                if "Speed Up Only" in sync_mode and speed_factor > 1.0:
                                    seg_audio = seg_audio.speedup(playback_speed=speed_factor)
                                elif "Speed Up & Slow Down" in sync_mode:
                                    if speed_factor != 1.0:
                                        seg_audio = seg_audio.speedup(playback_speed=speed_factor)

                            combined_audio += seg_audio
                            os.remove(temp_segment_file)
                        
                        progress_bar.progress((idx + 1) / len(segments))
                    
                    output_filename = f"AI_Dubbed_Output_({datetime.now().strftime('%Y-%m-%d_%H-%m-%S')}).mp3"
                    combined_audio.export(output_filename, format="mp3")
                    st.session_state.dubbed_audio_path = output_filename
                    status_box.empty()
                    st.success("✅ Audio Dubbing Complete!")

    if st.session_state.dubbed_audio_path and os.path.exists(st.session_state.dubbed_audio_path):
        st.audio(st.session_state.dubbed_audio_path)
        
        st.markdown("---")
        st.subheader("💾 Download Options")
        
        custom_name = st.text_input(
            "📝 បញ្ចូលឈ្មោះ File ដែលអ្នកចង់បាន (Optional):",
            placeholder="ឧទាហរណ៍: Episode_01_Dubbed"
        )
        
        final_download_name = st.session_state.dubbed_audio_path
        if custom_name.strip():
            final_download_name = f"{custom_name.strip()}.mp3"
            
        with open(st.session_state.dubbed_audio_path, "rb") as fp:
            st.download_button(
                label=f"🎵 Download MP3 ({final_download_name})",
                data=fp,
                file_name=final_download_name,
                mime="audio/mp3"
            )

    st.markdown("---")
    if st.button("🗑️ ធ្វើថ្មី (Clear Video Project)"):
        st.session_state.srt_content = ""
        st.session_state.dubbed_audio_path = None
        st.rerun()

# --- TAB 2 & 3 PLACEHOLDERS ---
with tab2:
    st.info("🌐 AI SRT Translator feature interface")

with tab3:
    st.info("📦 Subtitle to Voice Studio interface")
