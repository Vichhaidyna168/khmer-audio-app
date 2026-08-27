import asyncio
import io
import os
import re
import tempfile
import subprocess
import google.generativeai as genai
import srt
import streamlit as st
import edge_tts

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
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #0E1117 !important;
        color: #FFFFFF !important;
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
        color: #FFFFFF !important;
        font-weight: 800;
        font-size: 32px;
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

    div.stButton > button[key="tab1_gen_dub_btn"], div.stButton > button[key="tab3_gen_video_btn"] {
        background-color: #D000F0 !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        height: 50px !important;
        font-size: 16px !important;
        border: none !important;
        box-shadow: 0 0 15px rgba(208, 0, 240, 0.6) !important;
    }

    div.stButton > button[key="tab1_polish_script_btn"] {
        background-color: #008CBA !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        height: 45px !important;
        border: none !important;
        margin-bottom: 10px;
    }

    div.stButton > button[key="tab1_clear_project_btn"] {
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

    div[data-testid="stProgressBar"] > div {
        background-color: #00D2FF !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

default_srt = ""


def extract_tag_and_text(raw_text):
    gender = "MALE"
    if "[F]" in raw_text or "[f]" in raw_text:
        gender = "FEMALE"
    elif "[M]" in raw_text or "[m]" in raw_text:
        gender = "MALE"

    clean_txt = re.sub(r"\[[EMFemf]\]\s*", "", raw_text)
    clean_txt = re.sub(r"[\r\n]+", " ", clean_txt)
    return gender, clean_txt.strip()


def extract_srt_only(text):
    if not text:
        return ""
    match = re.search(r'(?:^|\n)(\d+\s*[\r\n]+\d\d:\d\d:\d\d)', text)
    if match:
        text = text[match.start():]
    text = re.sub(r"^```(srt)?\n?", "", text, flags=re.MULTILINE)
    text = re.sub(r"\n?```$", "", text, flags=re.MULTILINE)
    return text.strip()


def get_audio_duration(file_path):
    """ វាស់ប្រវែងវិនាទីនៃ File សំឡេង MP3 ដោយប្រើ FFprobe """
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return float(res.stdout.strip())
    except Exception:
        return 0.0


def make_ffmpeg_silence(duration_sec, out_path):
    """ បង្កើតសំឡេងស្ងាត់តាមប្រវែង Timecode ទំនេរ """
    if duration_sec <= 0.05:
        return False
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi",
        "-i", "anullsrc=r=44100:cl=stereo",
        "-t", str(duration_sec),
        "-c:a", "libmp3lame", "-b:a", "192k",
        out_path
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0 and os.path.exists(out_path)
    except Exception:
        return False


def adjust_audio_speed(in_path, target_duration, out_path):
    """ តម្រឹមល្បឿនសំឡេងឱ្យត្រូវតាមប្រវែង Timecode នៃ SRT (កុំឱ្យដើរលឿនពេក ឬខុសចង្វាក់) """
    actual_duration = get_audio_duration(in_path)
    if actual_duration <= 0.1 or target_duration <= 0.1:
        try:
            with open(in_path, "rb") as rf, open(out_path, "wb") as wf:
                wf.write(rf.read())
            return True
        except Exception:
            return False

    # ប្រសិនបើសំឡេង AI វែងជាង Timecode ក្នុង SRT ៖ បង្កើនល្បឿន (Speed Up) បន្តិចឱ្យទាន់ពេល
    if actual_duration > target_duration:
        speed_factor = actual_duration / target_duration
        speed_factor = min(speed_factor, 2.0)
        cmd = [
            "ffmpeg", "-y", "-i", in_path,
            "-filter:a", f"atempo={speed_factor}",
            "-c:a", "libmp3lame", "-b:a", "192k",
            out_path
        ]
    else:
        cmd = ["ffmpeg", "-y", "-i", in_path, "-c", "copy", out_path]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return res.returncode == 0 and os.path.exists(out_path)
    except Exception:
        return False


async def generate_edge_audio_file(text, voice, out_path):
    try:
        communicate = edge_tts.Communicate(text, voice, rate="-3%")
        await communicate.save(out_path)
        return os.path.exists(out_path)
    except Exception:
        return False


def get_working_gemini_model_name(selected_name):
    clean = str(selected_name).lower().strip()
    if "pro" in clean:
        return "gemini-1.5-pro"
    return "gemini-1.5-flash"


def polish_srt_with_gemini(srt_text, api_key, model_name):
    clean_key = api_key.strip()
    if not clean_key:
        raise Exception("សូមបញ្ចូល API Key នៅក្នុង Sidebar ឬ Streamlit Secrets ជាមុនសិន!")

    genai.configure(api_key=clean_key)

    prompt = f"""
    You are a professional Khmer Voice Dubbing Director.
    Task: Refine and adapt the following SRT subtitle for Text-to-Speech (TTS) dubbing.

    STRICT RULES:
    1. Keep SRT format (index numbers and timestamps like 00:00:00,000 --> 00:00:02,000) 100% INTACT.
    2. Use natural spoken Khmer phrasing.
    3. Add [M] tag for male voices and [F] tag for female voices.
    4. Output ONLY the raw modified SRT text. Do NOT add any explanations.

    SRT Content:
    {srt_text}
    """

    target_model = get_working_gemini_model_name(model_name)

    try:
        model = genai.GenerativeModel(target_model)
        response = model.generate_content(prompt)
        if response and response.text:
            return extract_srt_only(response.text)
    except Exception as e:
        try:
            model = genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            if response and response.text:
                return extract_srt_only(response.text)
        except Exception as err2:
            raise Exception(f"មិនអាចភ្ជាប់ទៅ Gemini API បានទេ៖ {e}")


def generate_synced_audio_km(srt_raw_text, voice_mode_selected):
    clean_srt_input = extract_srt_only(srt_raw_text)
    clean_srt_input = re.sub(r'(?:\r?\n)+\d+\s*$', '', clean_srt_input.strip())

    try:
        subs = list(srt.parse(clean_srt_input))
    except Exception:
        raise Exception("ទម្រង់ SRT មានបញ្ហា! សូមពិនិត្យមើល Timecode នៃ SRT ឡើងវិញ។")

    if not subs:
        return None

    temp_dir = tempfile.mkdtemp()
    file_list = []
    current_time_sec = 0.0
    total_subs = len(subs)
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    KHMER_MALE_VOICE = "km-KH-PisethNeural"
    KHMER_FEMALE_VOICE = "km-KH-SreymomNeural"

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    for idx, sub in enumerate(subs):
        start_sec = sub.start.total_seconds()
        end_sec = sub.end.total_seconds()
        target_slot_duration = end_sec - start_sec
        raw_content = sub.content.strip()
        gender, cleaned_text = extract_tag_and_text(raw_content)

        if voice_mode_selected == "All Male (ប្រុសសុទ្ធ)":
            chosen_voice = KHMER_MALE_VOICE
        elif voice_mode_selected == "All Female (ស្រីសុទ្ធ)":
            chosen_voice = KHMER_FEMALE_VOICE
        else:
            chosen_voice = KHMER_MALE_VOICE if gender == "MALE" else KHMER_FEMALE_VOICE

        status_text.markdown(f"🎙️ **កំពុងបង្កើតសំឡេងផ្នែកទី {idx+1}/{total_subs}...**")

        # ១. ថែម Silence Gap ប្រសិនបើមានចន្លោះទំនេររវាង Subtitle
        if start_sec > current_time_sec:
            gap_sec = start_sec - current_time_sec
            silence_path = os.path.join(temp_dir, f"gap_{idx}.mp3")
            if make_ffmpeg_silence(gap_sec, silence_path):
                file_list.append(silence_path)
            current_time_sec = start_sec

        # ២. បង្កើតសំឡេង និងតម្រឹមល្បឿនឱ្យត្រូវ Timecode
        if cleaned_text:
            raw_audio_path = os.path.join(temp_dir, f"raw_speech_{idx}.mp3")
            synced_audio_path = os.path.join(temp_dir, f"synced_speech_{idx}.mp3")

            success = loop.run_until_complete(generate_edge_audio_file(cleaned_text, chosen_voice, raw_audio_path))
            if success:
                adjust_audio_speed(raw_audio_path, target_slot_duration, synced_audio_path)
                file_list.append(synced_audio_path)
                current_time_sec = max(current_time_sec, end_sec)
            else:
                duration = max(target_slot_duration, 0.2)
                silence_path = os.path.join(temp_dir, f"silence_{idx}.mp3")
                if make_ffmpeg_silence(duration, silence_path):
                    file_list.append(silence_path)
                current_time_sec += duration
        else:
            duration = max(target_slot_duration, 0.2)
            silence_path = os.path.join(temp_dir, f"silence_{idx}.mp3")
            if make_ffmpeg_silence(duration, silence_path):
                file_list.append(silence_path)
            current_time_sec += duration

        percent_complete = int((idx + 1) / total_subs * 100)
        progress_bar.progress(percent_complete)

    status_text.empty()

    if not file_list:
        return None

    # ផ្គុំ File សំឡេងទាំងអស់ចូលគ្នាជាឯកសារ Master MP3
    list_txt_path = os.path.join(temp_dir, "files.txt")
    with open(list_txt_path, "w", encoding="utf-8") as f:
        for filepath in file_list:
            escaped_path = filepath.replace("\\", "/")
            f.write(f"file '{escaped_path}'\n")

    final_output_path = os.path.join(temp_dir, "final_master.mp3")
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", list_txt_path,
        "-c:a", "libmp3lame", "-b:a", "192k",
        final_output_path
    ]

    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0 and os.path.exists(final_output_path):
            with open(final_output_path, "rb") as f:
                return f.read()
    except Exception:
        pass

    return None


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

    secret_key = ""
    try:
        if "GEMINI_API_KEY" in st.secrets:
            secret_key = st.secrets["GEMINI_API_KEY"]
    except Exception:
        pass

    if "user_api_key" not in st.session_state or not st.session_state["user_api_key"]:
        st.session_state["user_api_key"] = secret_key

    api_input = st.text_area(
        "Paste Gemini API Keys",
        value=st.session_state["user_api_key"],
        height=90,
        placeholder="Paste your Gemini API key here...",
        key="sb_input_gemini_key",
    )

    st.session_state["user_api_key"] = api_input
    active_api_key = api_input.strip()

    st.markdown("---")
    st.markdown("### 🗣️ Voice Mode (ជម្រើសសំឡេង)")
    voice_mode = st.radio(
        "",
        [
            "Auto (ប្រុស/ស្រី តាម Tag)",
            "All Male (ប្រុសសុទ្ធ)",
            "All Female (ស្រីសុទ្ធ)",
        ],
        key="sb_v_mode",
    )

    st.markdown("---")
    st.markdown("### 🧠 AI Model (ម៉ូដែល AI)")
    ai_model = st.radio(
        "ជ្រើសរើសម៉ូដែល (Select Model):",
        [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
            "gemini-2.0-flash",
            "gemini-3.5-flash",
            "gemini-3.6-flash",
            "gemini-3.1-pro",
        ],
        key="sb_model_m",
    )

    st.markdown("---")
    if st.button("🔄 Reboot App / Reset Workspace", key="sb_reboot_app_btn", use_container_width=True):
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

tab1, tab2, tab3 = st.tabs(
    ["🎬 AI Video Dubbing", "🌐 AI SRT Translator", "📦 Subtitle to Video"]
)

def clear_project_callback():
    if "audio_data" in st.session_state:
        del st.session_state["audio_data"]
    st.session_state["srt_input_content"] = ""

def polish_callback():
    if not active_api_key:
        st.session_state["polish_msg"] = ("error", "❌ សូម Paste Gemini API Key នៅក្នុង Sidebar ជាមុនសិន!")
        return
    current_srt = st.session_state.get("srt_input_content", "")
    if not current_srt.strip():
        st.session_state["polish_msg"] = ("warning", "⚠️ សូមបញ្ចូលអត្ថបទ SRT ជាមុនសិន!")
        return
    try:
        res = polish_srt_with_gemini(current_srt, active_api_key, ai_model)
        st.session_state["srt_input_content"] = res
        st.session_state["polish_msg"] = ("success", "✅ សម្រួលស្គ្រីបត្រូវតាមស្តង់ដារបញ្ចូលសំឡេងរួចរាល់!")
    except Exception as e:
        st.session_state["polish_msg"] = ("error", f"❌ កើតមានបញ្ហាជាមួយ Gemini: {e}")

# --- TAB 1: AI VIDEO DUBBING ---
with tab1:
    st.markdown(
        "<h2><span class='num-badge'>1</span>Generate Subtitles (Khmer (ខ្មែរ))</h2>",
        unsafe_allow_html=True,
    )
    st.caption("Upload Video")
    uploaded_file = st.file_uploader("", type=["mp4", "mov", "avi", "mkv"], key="tab1_video_uploader")

    if uploaded_file is not None:
        st.video(uploaded_file)

    st.markdown("### Generated SRT from Video")
    st.caption("ពិនិត្យ និងកែសម្រួលអត្ថបទ SRT ទីនេះមុនពេលបញ្ចូលសំឡេង (អាចលុប ឬវាយបញ្ចូលដោយដៃ):")

    if "srt_input_content" not in st.session_state:
        st.session_state["srt_input_content"] = default_srt

    srt_content = st.text_area(
        "", 
        value=st.session_state["srt_input_content"],
        height=220, 
        key="srt_input_content"
    )

    col_polish1, col_polish2 = st.columns([2, 1])
    with col_polish1:
        st.button(
            "✨ ឱ្យ AI សម្រួលចង្វាក់ដកដង្ហើម & អារម្មណ៍សាច់រឿង (AI Polish Script)",
            key="tab1_polish_script_btn",
            use_container_width=True,
            on_click=polish_callback,
        )

    if "polish_msg" in st.session_state:
        msg_type, msg_txt = st.session_state["polish_msg"]
        if msg_type == "success":
            st.success(msg_txt)
        elif msg_type == "warning":
            st.warning(msg_txt)
        else:
            st.error(msg_txt)
        del st.session_state["polish_msg"]

    st.markdown("---")
    st.markdown(
        "<h2><span class='num-badge'>2</span>AI Dubbing (Khmer TTS Studio)</h2>",
        unsafe_allow_html=True,
    )

    col_btn1, col_btn2 = st.columns([2, 1])
    with col_btn1:
        gen_clicked = st.button(
            "🎙️ Generate Dubbed Audio (MP3)",
            key="tab1_gen_dub_btn",
            use_container_width=True,
        )

    if gen_clicked:
        if not srt_content.strip():
            st.warning("⚠️ សូមបញ្ចូលអត្ថបទ SRT ឬអក្សរជាមុនសិន!")
        else:
            try:
                audio_bytes = generate_synced_audio_km(srt_content, voice_mode)

                if audio_bytes and len(audio_bytes) > 500:
                    st.success("✅ Audio Dubbing Complete!")
                    st.session_state["audio_data"] = audio_bytes
                else:
                    st.error("❌ បរាជ័យ៖ មិនអាចទាញយកសំឡេងបានទេ!")
            except Exception as e:
                st.error(f"❌ កើតមានបញ្ហា៖ {e}")

    if "audio_data" in st.session_state:
        st.audio(st.session_state["audio_data"], format="audio/mp3")

        st.markdown("### 💾 Download Options")

        file_custom_name = st.text_input(
            "📝 បញ្ចូលឈ្មោះ File ដែលអ្នកចង់បាន (Optional):",
            placeholder="ឧទាហរណ៍: Episode_01_Dubbed",
            key="tab1_custom_filename_input",
        )

        clean_name = re.sub(r'[^\w\-]', '_', file_custom_name.strip())
        final_filename = (
            f"{clean_name}.mp3" if clean_name else "Vichhai_Dubbed_Output.mp3"
        )

        st.download_button(
            label=f"🎵 Download MP3 ({final_filename})",
            data=st.session_state["audio_data"],
            file_name=final_filename,
            mime="audio/mp3",
            key="tab1_download_audio_btn",
            use_container_width=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.button(
        "🗑️ ធ្វើថ្មី (Reset Default Project)",
        key="tab1_clear_project_btn",
        use_container_width=True,
        on_click=clear_project_callback,
    )

# --- TAB 2: AI SRT TRANSLATOR ---
with tab2:
    st.markdown("<h2>🌐 AI SRT Translator</h2>", unsafe_allow_html=True)
    srt_to_translate = st.text_area("បញ្ចូល SRT ដើមដើម្បកប្រែ៖", height=150, key="tab2_srt_to_translate")
    if st.button("🌐 បកប្រែដោយ Gemini", key="tab2_translate_btn"):
        if not active_api_key:
            st.error("❌ សូម Paste Gemini API Key នៅក្នុង Sidebar ជាមុនសិន!")
        elif not srt_to_translate.strip():
            st.warning("⚠️ សូមបញ្ចូលអត្ថបទ SRT!")
        else:
            try:
                genai.configure(api_key=active_api_key)
                actual_mod = get_working_gemini_model_name(ai_model)
                model = genai.GenerativeModel(actual_mod)
                prompt = (
                    "Translate the following subtitle/SRT content into"
                    f" {target_lang}. Keep the SRT timestamps intact:\n\n{srt_to_translate}"
                )
                response = model.generate_content(prompt)
                st.success("✅ បកប្រែជោគជ័យ!")
                st.text_area("លទ្ធផលបកប្រែ៖", value=response.text, height=180, key="tab2_translated_output")
            except Exception as e:
                st.error(f"❌ Gemini Error: {e}")

# --- TAB 3: SUBTITLE TO VIDEO ---
with tab3:
    st.markdown("<h2>📦 Subtitle to Video (Hardcode Subtitles)</h2>", unsafe_allow_html=True)
    st.caption("មុខងារបង្កប់អក្សរ Subtitle ចូលទៅក្នុងវីដេអូដោយផ្ទាល់")
    
    v_input = st.file_uploader("១. Upload Video File (MP4/MOV)", type=["mp4", "mov"], key="tab3_v_file")
    s_input = st.file_uploader("២. Upload SRT File", type=["srt"], key="tab3_s_file")

    if st.button("🎬 Generate Video ជាមួយ Subtitle (MP4)", key="tab3_gen_video_btn", use_container_width=True):
        if not v_input or not s_input:
            st.warning("⚠️ សូម Upload ទាំង Video និង SRT File ជាមុនសិន!")
        else:
            try:
                with st.spinner("កំពុងដំណើរការបង្កប់ Subtitle ចូលក្នុងវីដេអូ..."):
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp_v:
                        tmp_v.write(v_input.read())
                        v_path = tmp_v.name
                    
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".srt") as tmp_s:
                        tmp_s.write(s_input.read())
                        s_path = tmp_s.name

                    out_video_path = tempfile.mktemp(suffix=".mp4")

                    cmd = [
                        "ffmpeg", "-y", "-i", v_path,
                        "-vf", f"subtitles='{s_path}':force_style='FontName=Khmer OS,FontSize=18,PrimaryColour=&H00FFFF&'",
                        "-c:a", "copy",
                        out_video_path
                    ]
                    
                    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    
                    if os.path.exists(out_video_path) and os.path.getsize(out_video_path) > 1000:
                        st.success("✅ បង្កើតវីដេអូមាន Subtitle រួចរាល់!")
                        with open(out_video_path, "rb") as vf:
                            st.video(vf.read())
                        with open(out_video_path, "rb") as vf:
                            st.download_button("💾 Download Video (MP4)", data=vf.read(), file_name="Video_With_Subtitles.mp4", mime="video/mp4")
                    else:
                        st.error("❌ កើតមានបញ្ហាពេលបង្កប់ Subtitle!")

            except Exception as e:
                st.error(f"❌ បរាជ័យ៖ {e}")

