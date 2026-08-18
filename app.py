import asyncio
import io
import os
import re
import tempfile
import subprocess
import edge_tts
import google.generativeai as genai
import srt
import streamlit as st
from edge_tts import Communicate

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

    div.stButton > button[key="tab1_gen_dub_btn"] {
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


def run_async(coro):
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    if loop.is_running():
        import nest_asyncio
        nest_asyncio.apply()
        return loop.run_until_complete(coro)
    else:
        return loop.run_until_complete(coro)


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


def generate_clean_mp3_silence(duration_sec):
    if duration_sec <= 0.02:
        return b""
    frame_header = bytes.fromhex("fffb90c4")
    frame_body = b"\x00" * (417 - len(frame_header))
    frame = frame_header + frame_body
    num_frames = int(duration_sec / 0.026122)
    return frame * max(1, num_frames)


def convert_to_capcut_compatible_mp3(raw_bytes):
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as in_f:
            in_f.write(raw_bytes)
            in_path = in_f.name

        out_path = tempfile.mktemp(suffix=".mp3")

        # ប្រើប្រាស់ FFmpeg Re-encode ទៅជា Constant Bitrate (128k, 44.1kHz) ដែល CapCut iOS ស្គាល់ 100%
        cmd = [
            "ffmpeg", "-y", "-i", in_path,
            "-codec:a", "libmp3lame",
            "-b:a", "128k",
            "-ar", "44100",
            "-ac", "2",
            out_path
        ]
        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)

        with open(out_path, "rb") as out_f:
            processed_data = out_f.read()

        if os.path.exists(in_path): os.remove(in_path)
        if os.path.exists(out_path): os.remove(out_path)

        return processed_data
    except Exception:
        return raw_bytes


def polish_srt_with_gemini(srt_text, api_key, model_name):
    clean_key = api_key.strip()
    if not clean_key:
        raise Exception("សូមបញ្ចូល API Key នៅក្នុង Sidebar ជាមុនសិន!")

    genai.configure(api_key=clean_key)

    prompt = f"""
    You are a professional Khmer Voice Dubbing Director.
    Task: Refine and adapt the following SRT subtitle for Text-to-Speech (TTS) dubbing.

    STRICT RULES:
    1. Keep SRT format (index numbers and timestamps like 00:00:00,000 --> 00:00:02,000) 100% INTACT.
    2. Use natural spoken Khmer phrasing.
    3. Add [M] tag for male voices and [F] tag for female voices.
    4. Add punctuation for TTS pauses:
       - Add (,) for short pause / breath
       - Add (...) for emotional pause / thinking
       - Add (!) or (?) for excitement / anger / question
    5. Output ONLY the raw modified SRT text. Do NOT add any explanations, markdown titles, or intro text.

    SRT Content:
    {srt_text}
    """

    working_models = ["gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    
    clean_req_model = model_name.replace("models/", "")
    if clean_req_model in working_models:
        working_models.remove(clean_req_model)
        working_models.insert(0, clean_req_model)

    last_err = None
    for m in working_models:
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(prompt)
            if response and response.text:
                return extract_srt_only(response.text)
        except Exception as e:
            last_err = e
            continue

    raise Exception(f"មិនអាចភ្ជាប់ទៅ Gemini API បានទេ៖ {last_err}")


async def get_audio_bytes(text, voice_code, retries=3):
    for attempt in range(retries):
        try:
            communicate = Communicate(text, voice_code)
            out = io.BytesIO()
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    out.write(chunk["data"])
            val = out.getvalue()
            if len(val) > 0:
                return val
        except Exception:
            await asyncio.sleep(0.3)
    return b""


async def generate_synced_audio(srt_raw_text, voice_mode_selected):
    clean_srt_input = extract_srt_only(srt_raw_text)
    try:
        subs = list(srt.parse(clean_srt_input))
    except Exception:
        raise Exception("ទម្រង់ SRT មានបញ្ហា! សូមពិនិត្យមើលលេខរៀង និង Timecode នៃ SRT ឡើងវិញ។")

    if not subs:
        return None

    valid_subs = []
    for s in subs:
        c = s.content.strip()
        if "ភាគបន្ត" in c or "ទស្សនាភាគបន្ត" in c or c.startswith("("):
            continue
        valid_subs.append(s)

    if not valid_subs:
        valid_subs = subs

    combined_bytes = bytearray()
    current_time_sec = 0.0
    total_subs = len(valid_subs)
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for idx, sub in enumerate(valid_subs):
        start_sec = sub.start.total_seconds()
        end_sec = sub.end.total_seconds()
        raw_content = sub.content.strip()
        cleaned_text = clean_srt_text(raw_content)

        status_text.markdown(f"🎙️ **Generating voice for segment {idx+1}/{total_subs}...**")

        if start_sec > current_time_sec:
            gap_sec = start_sec - current_time_sec
            combined_bytes.extend(generate_clean_mp3_silence(gap_sec))
            current_time_sec = start_sec

        if cleaned_text:
            gender = "Male"
            if voice_mode_selected == "All Female (ស្រីសុទ្ធ)":
                gender = "Female"
            elif voice_mode_selected == "Auto (ប្រុស/ស្រី តាម Tag)":
                if "[F]" in raw_content:
                    gender = "Female"
                elif "[M]" in raw_content:
                    gender = "Male"

            v_code = VOICES.get(gender, VOICES["Male"])

            audio_chunk = await get_audio_bytes(cleaned_text, v_code)
            if audio_chunk:
                combined_bytes.extend(audio_chunk)
                current_time_sec = max(current_time_sec, end_sec)
            else:
                duration = max(end_sec - start_sec, 0.2)
                combined_bytes.extend(generate_clean_mp3_silence(duration))
                current_time_sec += duration
        else:
            duration = max(end_sec - start_sec, 0.2)
            combined_bytes.extend(generate_clean_mp3_silence(duration))
            current_time_sec += duration

        await asyncio.sleep(0.01)
        percent_complete = int((idx + 1) / total_subs * 100)
        progress_bar.progress(percent_complete)

    status_text.empty()
    raw_mp3 = bytes(combined_bytes)
    return convert_to_capcut_compatible_mp3(raw_mp3)


# ==========================================
# --- ២. SIDEBAR CONTROLS ---
# ==========================================
with st.sidebar:
    st.markdown("### 🌍 Target Language (ភាសាបកប្រែ)")
    target_lang = st.selectbox(
        "ជ្រើសរើសភាសា (Select Language):",
        ["Khmer (ខ្មែរ)", "English", "Chinese", "Thai"],
        key="sb_target_lang_select"
    )

    st.markdown("---")
    st.markdown("### 🔑 API Keys Manager")

    default_key = ""
    try:
        default_key = st.secrets.get("GEMINI_API_KEY", "")
    except Exception:
        pass

    if "user_api_key" not in st.session_state:
        st.session_state["user_api_key"] = default_key

    api_input = st.text_area(
        "Paste Gemini API Keys (One per line)",
        value=st.session_state["user_api_key"],
        height=90,
        placeholder="Paste your Gemini API key here...",
        key="sb_input_gemini_key",
    )

    if api_input != st.session_state["user_api_key"]:
        st.session_state["user_api_key"] = api_input

    active_api_key = None
    if st.session_state["user_api_key"].strip():
        keys_list = [
            k.strip()
            for k in st.session_state["user_api_key"].split("\n")
            if k.strip()
        ]
        st.success(f"✅ កំពុងប្រើប្រាស់ {len(keys_list)} Keys")
        active_api_key = keys_list[0]
    else:
        st.error("❌ មិនទាន់មានកូនសោនៅឡើយទេ")

    st.markdown("---")
    st.markdown("### 🎭 Translation Style")
    trans_api = st.radio("", ["Gemini Api", "Google Api"], key="sb_trans_style")

    st.markdown("---")
    st.markdown("### ⚙️ Audio Sync Mode")
    sync_mode = st.radio(
        "",
        [
            "Speed Up Only (ល្បឿន)",
            "Speed Up & Slow Down (ល្បឿន និង យឺត)",
        ],
        key="sb_sync_m",
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
        key="sb_v_mode",
    )

    st.markdown("---")
    st.markdown("### 🧠 AI Model (ម៉ូដែល AI)")
    ai_model = st.radio(
        "ជ្រើសរើសម៉ូដែល (Select Model):",
        [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-flash",
            "gemini-1.5-pro",
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

# Callbacks
def clear_project_callback():
    if "audio_data" in st.session_state:
        del st.session_state["audio_data"]
    st.session_state["srt_input_content"] = ""
    if "custom_file_name" in st.session_state:
        st.session_state["custom_file_name"] = ""

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
    st.caption("ពិនិត្យ និងកែសម្រួលអត្ថបទ SRT ទីនេះមុនពេលបញ្ចូលសំឡេង៖")

    if "srt_input_content" not in st.session_state:
        st.session_state["srt_input_content"] = default_srt

    srt_content = st.text_area(
        "", height=180, key="srt_input_content"
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
        "<h2><span class='num-badge'>2</span>AI Dubbing (Edge TTS Studio)</h2>",
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
                audio_bytes = run_async(
                    generate_synced_audio(srt_content, voice_mode)
                )

                if audio_bytes and len(audio_bytes) > 2000:
                    st.success("✅ Audio Dubbing Complete!")
                    st.session_state["audio_data"] = audio_bytes
                else:
                    st.error(
                        "❌ បរាជ័យ៖ មិនអាចទាញយកសំឡេងបានទេ! សូមចុច Generate ម្តងទៀត"
                    )
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
        "🗑️ ធ្វើថ្មី (Clear Video Project)",
        key="tab1_clear_project_btn",
        use_container_width=True,
        on_click=clear_project_callback,
    )

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
                model = genai.GenerativeModel(ai_model)
                prompt = (
                    "Translate the following subtitle/SRT content into"
                    f" {target_lang}. Keep the SRT timestamps intact:\n\n{srt_to_translate}"
                )
                response = model.generate_content(prompt)
                st.success("✅ បកប្រែជោគជ័យ!")
                st.text_area("លទ្ធផលបកប្រែ៖", value=response.text, height=180, key="tab2_translated_output")
            except Exception as e:
                st.error(f"❌ Gemini Error: {e}")

with tab3:
    st.markdown("<h2>📦 Subtitle to Video</h2>", unsafe_allow_html=True)
    st.info("មុខងារបង្កប់ Subtitle ចូលទៅក្នុង Video (Hardcode Subtitles)")


