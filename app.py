import asyncio
import io
import os
import re
import tempfile
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
    div.stButton > button[key="polish_script"] {
        background-color: #008CBA !important;
        color: white !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        height: 45px !important;
        border: none !important;
        margin-bottom: 10px;
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


# --- Function លុបទិន្នន័យ (កែសម្រួលឱ្យលុបប្រអប់ SRT ស្អាត) ---
def clear_project_callback():
    if "audio_data" in st.session_state:
        del st.session_state["audio_data"]
    st.session_state["srt_text_box_input"] = ""
    if "custom_file_name" in st.session_state:
        st.session_state["custom_file_name"] = ""


def clean_srt_text(text):
    text = re.sub(r"\[[EMF]\]\s*", "", text)
    return text.strip()


def generate_clean_mp3_silence(duration_sec):
    """បង្កើត MP3 Silence Bytes ដែលមាន Frame Header ត្រូវតាមស្ដង់ដារ"""
    if duration_sec <= 0.02:
        return b""
    frame_header = bytes.fromhex(
        "fff354c40000000000000000000000000000000000000000000000000000"
    )
    frame = frame_header + (b"\x00" * (288 - len(frame_header)))
    num_frames = int(duration_sec / 0.024)
    return frame * max(1, num_frames)


def polish_srt_with_gemini(srt_text, api_key, model_name):
    """ប្រើ Gemini ដើម្បីសម្រួលប្រយោគខ្មែរឱ្យមានចង្វាក់និយាយ ដកដង្ហើម និងអារម្មណ៍សមស្របតាមសាច់រឿង"""
    clean_key = api_key.strip()
    if not clean_key:
        raise Exception("សូមបញ្ចូល API Key នៅក្នុង Sidebar ជាមុនសិន!")

    genai.configure(api_key=clean_key)

    prompt = f"""
    អ្នកគឺជាអ្នកជំនាញសម្រួលស្គ្រីបបញ្ចូលសំឡេងរឿងភាគ និងវីដេអូអាជីព (Khmer Voice Dubbing Director)។
    ភារកិច្ច៖ កែសម្រួលអត្ថបទ SRT ខាងក្រោម ឱ្យសមស្របបំផុតសម្រាប់ការអានបង្កើតសំឡេង (Text-to-Speech) ឱ្យដើរតួស៊ីអារម្មណ៍ដូចមនុស្សពិតនិយាយ។

    គោលការណ៍ម៉ឺងម៉ាត់បំផុត៖
    ១. រក្សាទម្រង់ SRT (លេខរៀង និង Timestamp) ឱ្យនៅដដែល ១០០% ហាមលុប ឬកាត់ជួរពេលវេលា!
    ២. សម្រួលពាក្យពេចន៍ជាភាសាខ្មែរនិយាយធម្មជាតិ (Spoken Khmer)។
    ៣. បន្ថែមសញ្ញា [M] សម្រាប់សំឡេងប្រុស និង [F] សម្រាប់សំឡេងស្រី តាមសាច់រឿង។
    ៤. បន្ថែមសញ្ញាវណ្ណយុត្តិបញ្ជាចង្វាក់ TTS៖
       - បន្ថែម (,) សម្រាប់បង្អង់ដកដង្ហើមខ្លី
       - បន្ថែម (...) សម្រាប់រំភើប/គិត
       - បន្ថែម (!) ឬ (?) សម្រាប់ខឹង/ភ្ញាក់ផ្អើល
    ៥. ហាមបន្ថែមអក្សរនាំមុខ បង្ហាញតែទម្រង់ SRT ដែលបានកែរួចប៉ុណោះ។

    អត្ថបទ SRT ដើម៖
    {srt_text}
    """

    # ១. សាកល្បង Model ដែលអ្នកប្រើជ្រើសរើស និង Model ស្តង់ដារ
    candidates = [model_name, "gemini-1.5-flash", "gemini-1.5-pro", "models/gemini-1.5-flash", "models/gemini-1.5-pro"]
    for m in candidates:
        if not m:
            continue
        try:
            model = genai.GenerativeModel(m)
            response = model.generate_content(prompt)
            if response and response.text:
                cleaned_res = response.text.strip()
                cleaned_res = re.sub(r"^```(srt)?\n", "", cleaned_res)
                cleaned_res = re.sub(r"\n```$", "", cleaned_res)
                return cleaned_res.strip()
        except Exception:
            continue

    # ២. បើ Model ខាងលើលោត 404 ឱ្យប្រព័ន្ធស្រង់ទាញយក Active Model ស្វ័យប្រវត្តិ
    try:
        for m_info in genai.list_models():
            if "generateContent" in m_info.supported_generation_methods:
                try:
                    model = genai.GenerativeModel(m_info.name)
                    response = model.generate_content(prompt)
                    if response and response.text:
                        cleaned_res = response.text.strip()
                        cleaned_res = re.sub(r"^```(srt)?\n", "", cleaned_res)
                        cleaned_res = re.sub(r"\n```$", "", cleaned_res)
                        return cleaned_res.strip()
                except Exception:
                    continue
    except Exception as e:
        raise Exception(f"មិនអាចភ្ជាប់ទៅ Gemini API បានទេ៖ {e}")

    raise Exception("មិនអាចភ្ជាប់ទៅ Gemini បានទេ! សូមពិនិត្យមើល API Key របស់អ្នកឡើងវិញ។")


async def get_audio_bytes(text, voice_code, retries=3):
    """ទាញយកសំឡេងពី Edge-TTS"""
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
    subs = list(srt.parse(srt_raw_text))
    if not subs:
        return None

    combined_bytes = bytearray()
    current_time_sec = 0.0
    total_subs = len(subs)
    progress_bar = st.progress(0)

    for idx, sub in enumerate(subs):
        start_sec = sub.start.total_seconds()
        end_sec = sub.end.total_seconds()
        raw_content = sub.content.strip()
        cleaned_text = clean_srt_text(raw_content)

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
                duration = max(end_sec - start_sec, 0.5)
                combined_bytes.extend(generate_clean_mp3_silence(duration))
                current_time_sec += duration
        else:
            duration = max(end_sec - start_sec, 0.5)
            combined_bytes.extend(generate_clean_mp3_silence(duration))
            current_time_sec += duration

        await asyncio.sleep(0.02)
        progress_bar.progress(int((idx + 1) / total_subs * 100))

    last_sub_end = subs[-1].end.total_seconds()
    if last_sub_end > current_time_sec:
        remaining_gap = last_sub_end - current_time_sec
        combined_bytes.extend(generate_clean_mp3_silence(remaining_gap))

    return bytes(combined_bytes)


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

    if "user_api_key" not in st.session_state:
        st.session_state["user_api_key"] = st.secrets.get(
            "GEMINI_API_KEY", ""
        )

    api_input = st.text_area(
        "Paste Gemini API Keys (One per line)",
        value=st.session_state["user_api_key"],
        height=90,
        placeholder="Paste your Gemini API key here...",
        key="input_gemini_key",
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

    st.markdown("---")
    st.markdown("### 🧠 AI Model (ម៉ូដែល AI)")
    ai_model = st.radio(
        "",
        [
            "gemini-1.5-flash",
            "gemini-1.5-pro",
        ],
        key="model_m",
    )

    st.markdown("---")
    if st.button("🔄 Reboot App / Reset Workspace", use_container_width=True):
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

with tab1:
    st.markdown(
        "<h2><span class='num-badge'>1</span>Generate Subtitles (Khmer (ខ្មែរ))</h2>",
        unsafe_allow_html=True,
    )
    st.caption("Upload Video")
    uploaded_file = st.file_uploader("", type=["mp4", "mov", "avi", "mkv"])

    if uploaded_file is not None:
        st.video(uploaded_file)

    st.markdown("### Generated SRT from Video")
    st.caption("ពិនិត្យ និងកែសម្រួលអត្ថបទ SRT ទីនេះមុនពេលបញ្ចូលសំឡេង៖")

    if "srt_text_box_input" not in st.session_state:
        st.session_state["srt_text_box_input"] = default_srt

    srt_content = st.text_area(
        "", height=180, key="srt_text_box_input"
    )

    col_polish1, col_polish2 = st.columns([2, 1])
    with col_polish1:
        if st.button(
            "✨ ឱ្យ AI សម្រួលចង្វាក់ដកដង្ហើម & អារម្មណ៍សាច់រឿង (AI Polish Script)",
            key="polish_script",
            use_container_width=True,
        ):
            if not active_api_key:
                st.error(
                    "❌ សូម Paste Gemini API Key នៅក្នុង Sidebar ជាមុនសិន!"
                )
            elif not srt_content.strip():
                st.warning("⚠️ សូមបញ្ចូលអត្ថបទ SRT ជាមុនសិន!")
            else:
                with st.spinner(
                    "⌛ កំពុងឱ្យ Gemini វិភាគសាច់រឿង ដាក់ចង្វាក់ដកដង្ហើម និងបែងចែកតួអង្គ..."
                ):
                    try:
                        polished_res = polish_srt_with_gemini(
                            srt_content, active_api_key, ai_model
                        )
                        st.session_state["srt_text_box_input"] = polished_res
                        st.success(
                            "✅ សម្រួលស្គ្រីបត្រូវតាមស្តង់ដារបញ្ចូលសំឡេងរួចរាល់!"
                        )
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ កើតមានបញ្ហាជាមួយ Gemini: {e}")

    st.markdown("---")
    st.markdown(
        "<h2><span class='num-badge'>2</span>AI Dubbing (Edge TTS Studio)</h2>",
        unsafe_allow_html=True,
    )

    col_btn1, col_btn2 = st.columns([2, 1])
    with col_btn1:
        gen_clicked = st.button(
            "🎙️ Generate Dubbed Audio (MP3)",
            key="gen_dub",
            use_container_width=True,
        )

    if gen_clicked:
        if not srt_content.strip():
            st.warning("⚠️ សូមបញ្ចូលអត្ថបទ SRT ឬអក្សរជាមុនសិន!")
        else:
            status_box = st.info("⌛ កំពុងដំណើរការបង្កើតសំឡេងតម្រឹមតាម SRT...")
            try:
                audio_bytes = asyncio.run(
                    generate_synced_audio(srt_content, voice_mode)
                )

                status_box.empty()
                if audio_bytes and len(audio_bytes) > 2000:
                    st.success("✅ Audio Dubbing Complete!")
                    st.session_state["audio_data"] = audio_bytes
                else:
                    st.error(
                        "❌ បរាជ័យ៖ មិនអាចទាញយកសំឡេងបានទេ! សូមចុច Generate ម្តងទៀត"
                    )
            except Exception as e:
                status_box.empty()
                st.error(f"❌ កើតមានបញ្ហា៖ {e}")

    if "audio_data" in st.session_state:
        st.audio(st.session_state["audio_data"], format="audio/mp3")

        st.markdown("### 💾 Download Options")

        file_custom_name = st.text_input(
            "📝 បញ្ចូលឈ្មោះ File ដែលអ្នកចង់បាន (Optional):",
            placeholder="ឧទាហរណ៍: Episode_01_Dubbed",
            key="custom_file_name",
        )

        clean_name = file_custom_name.strip()
        final_filename = (
            f"{clean_name}.mp3" if clean_name else "Vichhai_Dubbed_Oup3"
        )

        st.download_button(
            label=f"🎵 Download MP3 ({final_filename})",
            data=st.session_state["audio_data"],
            file_name=final_filename,
            mime="audio/mp3",
            use_container_width=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.button(
        "🗑️ ធ្វើថ្មី (Clear Video Project)",
        key="clear_proj",
        use_container_width=True,
        on_click=clear_project_callback,
    )

with tab2:
    st.markdown("<h2>🌐 AI SRT Translator</h2>", unsafe_allow_html=True)
    srt_to_translate = st.text_area("បញ្ចូល SRT ដើមដើម្បកប្រែ៖", height=150)
    if st.button("🌐 បកប្រែដោយ Gemini"):
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
                st.text_area("លទ្ធផលបកប្រែ៖", value=response.text, height=180)
            except Exception as e:
                st.error(f"❌ Gemini Error: {e}")

with tab3:
    st.markdown("<h2>📦 Subtitle to Video</h2>", unsafe_allow_html=True)
    st.info("មុខងារបង្កប់ Subtitle ចូលទៅក្នុង Video (Hardcode Subtitles)")

