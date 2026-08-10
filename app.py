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

    st.markdown("---")
    st.markdown("### 🧠 AI Model (ម៉ូដែល AI)")
    ai_model = st.radio(
        "",
        [
            "gemini-2.5-flash",
            "gemini-2.0-flash",
            "gemini-1.5-pro",
            "gemini-2.5-flash-preview",
            "gemini-2.5-pro-preview",
        ],
        key="model_m",
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

tab1, tab2, tab3 = st.tabs(
    ["🎬 AI Video Dubbing", "🌐 AI SRT Translator", "📦 Subtitle to Video"]
)

with tab1:
    st.markdown(
        "<h2><span class='num-badge'>1</span>Generate Subtitles (Khmer"
        " (ខ្មែរ))</h2>",
        unsafe_allow_html=True,
    )
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
[F] កម្មវិធីនេះដំណើរការលឿន និងស្រួលប្រើប្រាស់មែនទែន។"""

    # កែសម្រួលចំណុចទី ១ ៖ រក្សាទុកតម្លៃ SRT ក្នុង Session State
    if "srt_input_text" not in st.session_state:
        st.session_state["srt_input_text"] = default_srt

    srt_content = st.text_area(
        "", height=180, key="srt_input_text"
    )

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
            progress_bar = st.progress(0)
            status_box = st.info("⌛ កំពុងដំណើរការបង្កើតសំឡេងពិតប្រាកដ...")

            lines = [l for l in srt_content.split("\n") if l.strip()]
            processed_lines = []
            for line in lines:
                cleaned = clean_srt_line(line)
                if cleaned:
                    gender = "Male"
                    if voice_mode == "All Female (ស្រីសុទ្ធ)":
                        gender = "Female"
                    elif voice_mode == "Auto (ប្រុស/ស្រី តាម Tag)":
                        if "[F]" in line:
                            gender = "Female"
                        elif "[M]" in line:
                            gender = "Male"
                    processed_lines.append((cleaned, gender))

            if not processed_lines:
                st.error("❌ មិនមានអត្ថបទត្រូវបង្កើតសំឡេងទេ!")
            else:
                combined_bytes = bytearray()

                for idx, (text, gender) in enumerate(processed_lines):
                    progress_bar.progress(
                        int((idx + 1) / len(processed_lines) * 100)
                    )
                    v_code = VOICES.get(gender, VOICES["Male"])

                    try:
                        chunk = asyncio.run(get_audio_bytes(text, v_code))
                        if chunk:
                            combined_bytes.extend(chunk)
                    except Exception as e:
                        st.error(
                            f"កំហុសត្រង់ជួរទី {idx+1} ៖ {text} (រំលងការបង្កើត)"
                        )

                status_box.empty()

                if len(combined_bytes) > 0:
                    st.success("✅ Audio Dubbing Complete!")
                    st.session_state["audio_data"] = bytes(combined_bytes)
                else:
                    st.error("❌ ការបង្កើតសំឡេងបរាជ័យ ៖ គ្មានទិន្នន័យសំឡេង!")

    if "audio_data" in st.session_state:
        st.audio(st.session_state["audio_data"], format="audio/mp3")

        st.markdown("### 💾 Download Options")

        # កែសម្រួលចំណុចទី ២ ៖ បន្ថែម key ឱ្យប្រអប់បញ្ចូលឈ្មោះ file
        file_custom_name = st.text_input(
            "📝 បញ្ចូលឈ្មោះ File ដែលអ្នកចង់បាន (Optional):",
            placeholder="ឧទាហរណ៍: Episode_01_Dubbed",
            key="custom_file_name",
        )

        clean_name = file_custom_name.strip()
        final_filename = (
            f"{clean_name}.mp3" if clean_name else "Vichhai_Dubbed_Output.mp3"
        )

        st.download_button(
            label=f"🎵 Download MP3 ({final_filename})",
            data=st.session_state["audio_data"],
            file_name=final_filename,
            mime="audio/mp3",
            use_container_width=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # កែសម្រួលចំណុចទី ១ ៖ លុបទាំងអត្ថបទ និងសំឡេងពេលចុច "ធ្វើថ្មី"
    if st.button(
        "🗑️ ធ្វើថ្មី (Clear Video Project)",
        key="clear_proj",
        use_container_width=True,
    ):
        if "audio_data" in st.session_state:
            del st.session_state["audio_data"]
        st.session_state["srt_input_text"] = ""
        st.rerun()

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
                model = genai.GenerativeModel("gemini-1.5-flash")
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

