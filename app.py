import asyncio
import os
import streamlit as st
from edge_tts import Communicate
import tempfile

# មុខងារបង្កើតសម្លេងនិងសរសេរជា File
async def generate_audio_file(text, voice_code):
    # បង្កើត File បណ្ដោះអាសន្ន
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    communicate = Communicate(text, voice_code)
    await communicate.save(temp_file.name)
    temp_file.close()
    return temp_file.name

st.title("🎙️ Vichhai Dubber Pro (File Based)")

# រក្សាអត្ថបទ
if "srt_input" not in st.session_state:
    st.session_state["srt_input"] = "សួស្តី! តេស្តសំឡេង។"

srt_content = st.text_area("អត្ថបទ៖", value=st.session_state["srt_input"], key="srt_input")

if st.button("🎙️ ចាប់ផ្ដើម Generate"):
    try:
        with st.spinner("កំពុងបង្កើត..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # ប្រើសំឡេង Piseth
            file_path = loop.run_until_complete(generate_audio_file(srt_content, "km-KH-PisethNeural"))
            
            if os.path.exists(file_path):
                # លេងសំឡេងពី File Path
                st.audio(file_path, format="audio/mp3")
                
                # ប៊ូតុង Download
                with open(file_path, "rb") as f:
                    st.download_button("🎵 Download MP3", f, "output.mp3", "audio/mp3")
                
                # លុប File បន្ទាប់ពីប្រើរួច (ជម្រើស៖ ទុកចោលក៏បាន)
                # os.remove(file_path)
            else:
                st.error("❌ បង្កើតសម្លេងមិនបានជោគជ័យ។")
    except Exception as e:
        st.error(f"កំហុស៖ {e}")


