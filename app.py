import streamlit as st
import os
import re
import asyncio
from edge_tts import Communicate
from pydub import AudioSegment
import google.generativeai as genai

# ==========================================
# --- ១. កំណត់ការកំណត់ទូទៅរបស់ទំព័រ (ដូចគំរូ) ---
# ==========================================
st.set_page_config(
    page_title="AI Dubbing studio",
    page_icon="🎙️",
    layout="centered"
)

# --- កំណត់កូនសោ Gemini API (ជំនួស "YOUR_API_KEY" ដោយ Key ពិតប្រាកដរបស់អ្នក) ---
GOOGLE_API_KEY = "YOUR_API_KEY" # <--- ប្តូរត្រង់នេះ
genai.configure(api_key=GOOGLE_API_KEY)

# --- កំណត់ Code ឈ្មោះសំឡេង Edge-TTS (ខ្មែរ) ---
VOICES = {
    "Male": "km-KH-PisethNeural",
    "Female": "km-KH-SreymomNeural"
}

# ==========================================
# --- ២. កូដ CSS ដើម្បីកំណត់ពណ៌ និង Layout ឱ្យដូចគំរូ ---
# ==========================================
st.markdown("""
<style>
    /* កំណត់ពណ៌ប៊ូតុងពណ៌ស្វាយ (Generate Dubbed Audio) */
    div.stButton > button[key="generate_btn"] {
        background-color: #BF40BF; /* ពណ៌ស្វាយ */
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 5px;
        font-weight: bold;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 100%;
    }
    
    /* កំណត់ពណ៌ប៊ូតុង Clear (ពណ៌ស្វាយចាស់) */
    div.stButton > button[key="clear_btn"] {
        background-color: #4B0082; /* ពណ៌ស្វាយចាស់ */
        color: white;
        border: none;
        width: 100%;
        font-weight: bold;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    /* តម្រៀបឱ្យ Status Alerts នៅកណ្តាល */
    .stAlert {
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# --- ៣. ផ្នែក Logic (អនុគមន៍ជំនួយ) ---
# ==========================================

# -- អនុគមន៍សំអាតអក្សរ និងដក [E]/[M] ចេញ --
def clean_text(text):
    return re.sub(r'\[[EMF]\]\s*', '', text).strip()

# -- អនុគមន៍ហៅ Gemini API ដើម្បីបែងចែកភេទតួអង្គ (Male/Female) --
def predict_gender_gemini(raw_text):
    if not GOOGLE_API_KEY or GOOGLE_API_KEY == "YOUR_API_KEY":
        st.error("❌ សូមដាក់ Google Gemini API Key របស់អ្នកជាមុនសិន!")
        return "Male" # Default if no Key

    model = genai.GenerativeModel('gemini-pro')
    prompt = f"""
    Read this Khmer text and predict if it's spoken by a 'Male' or 'Female'.
    Analyze the structure, polite particles (បាទ/ចាស), self-references (ខ្ញុំ/អូន/បង), or overall context.
    Return only a single word: 'Male' or 'Female'.
    
    Khmer text: "{raw_text}"
    Result:
    """
    try:
        response = model.generate_content(prompt)
        result = response.text.strip()
        if result in ["Male", "Female"]:
            return result
    except Exception as e:
        # st.warning(f"⚠️ Gemini failed, defaulting to Male. Error: {e}")
        pass
    return "Male" # Default if failed

# -- អនុគមន៍បង្កើតសំឡេង (Async) សម្រាប់ Edge-TTS --
async def generate_voice_async(text, voice_code, output_path):
    communicate = Communicate(text, voice_code)
    await communicate.save(output_path)

# ==========================================
# --- ៤. UI តាមរូបភាពគំរូ ---
# ==========================================

# ก. ចំណងជើងធំ ជាមួយរូបតំណាង និងលេខ ២ ក្នុងប្រអប់ (ដូចគំរូ)
st.markdown("""
    <h1 style='display: flex; align-items: center;'>
        <span style='background-color: #f0f2f6; color: #31333F; padding: 5px 15px; border-radius: 10px; margin-right: 15px;'>2</span> 
        AI Dubbing (Edge TTS Studio)
    </h1>
""", unsafe_allow_html=True)

# ខ. ប្រអប់ជ្រើសរើសប្រភេទសំឡេង (Voice Mode)
voice_mode_ui = st.selectbox(
    "ជ្រើសរើសប្រភេទសំឡេង (Voice Mode):",
    ("Auto (ប្រុស/ស្រី)", "All Male (ប្រុសសុទ្ធ)", "All Female (ស្រីសុទ្ធ)", "ប្រើ Gemini API បែងចែកភេទ")
)

# គ. ប្រអប់បញ្ចូលអក្សរសម្រាប់បញ្ចូលសំឡេង (Text Input for Dubbing)
input_text = st.text_area("✍️ បញ្ចូលអក្សរសម្រាប់បញ្ចូលសំឡេង (Khmer Text):", height=200, placeholder="ឧទាហរណ៍៖\n[M] សួស្តីបាទ\n[F] សួស្តីចាស\n(ឬដាក់ Gemini API ដើម្បីបែងចែកដោយស្វ័យប្រវត្តិ)")

# ឃ. ប៊ូតុង Generate Dubbed Audio (ពណ៌ស្វាយ មានរូបមីក្រូហ្វូន)
# ប្រើ Container ដើម្បីដាក់ប៊ូតុងឱ្យនៅខាងឆ្វេង (សន្សំលំហ UI)
with st.container():
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        generate_btn = st.button("🎙️ Generate Dubbed Audio (MP3)", key="generate_btn")
    with col2:
        # ប៊ូតុង Clear / Reset All (មានរូបធុងសំរាម ប្រើ Key ដើម្បីកំណត់ CSS)
        clear_btn = st.button("🗑️ Clear / Reset All", key="clear_btn")

# បន្ថែមចន្លោះ
st.markdown("<br>", unsafe_allow_html=True)

# ==========================================
# --- ៥. ផ្នែក logic ចម្បង (Main Execution) ---
# ==========================================

# -- លុបគ្រប់យ៉ាង (Reset) ពេលចុច Clear --
if clear_btn:
    if os.path.exists("final_dubbed.mp3"):
        os.remove("final_dubbed.mp3")
    st.rerun()

# -- ដំណើរការ ពេលចុច Generate --
if generate_btn and input_text:
    # ⌛ Status: Processing
    status_processing = st.info("⌛ Processing: កំពុងបង្កើតសំឡេងតាមជម្រើស...")
    
    temp_files = []
    final_audio = AudioSegment.empty()
    combined_status = []
    
    # បំបែកអក្សរជាបន្ទាត់ៗ
    lines = input_text.strip().split('\n')
    
    for i, line in enumerate(lines):
        if not line.strip(): continue
        
        cleaned = clean_text(line)
        gender = "Male" # Default
        
        # សម្រេចចិត្តជ្រើសរើសសំឡេង (Voice Mode)
        if voice_mode_ui == "All Male (ប្រុសសុទ្ធ)":
            gender = "Male"
        elif voice_mode_ui == "All Female (ស្រីសុទ្ធ)":
            gender = "Female"
        elif voice_mode_ui == "ប្រើ Gemini API បែងចែកភេទ":
            gender = predict_gender_gemini(cleaned) # ហៅ Gemini
        else: # Auto (ប្រុស/ស្រី)
            # ពិនិត្យ Tag [M] ឬ [F]
            if "[F]" in line:
                gender = "Female"
            elif "[M]" in line:
                gender = "Male"
            else:
                gender = "Male" # Default if no Tag

        # កំណត់ Code ឈ្មោះសំឡេង
        voice_code = VOICES.get(gender, VOICES["Male"])
        temp_filename = f"temp_segment_{i}.mp3"
        temp_files.append(temp_filename)
        
        # បង្កើតសំឡេង (Async)
        asyncio.run(generate_voice_async(cleaned, voice_code, temp_filename))
        
        # បញ្ចូលសំឡេងទៅជា File តែមួយ (pydub)
        segment_audio = AudioSegment.from_mp3(temp_filename)
        final_audio += segment_audio
        final_audio += AudioSegment.silent(duration=300) # បន្ថែមចន្លោះ 0.3 វិនាទី
        
        icon = "👨" if gender == "Male" else "👩"
        combined_status.append(f"{icon} ជួរទី {i+1} ({gender})")

    # រក្សាទុក File សម្រេច
    final_audio.export("final_dubbed.mp3", format="mp3")
    
    # លុប File បណ្តោះអាសន្ន
    for f in temp_files:
        if os.path.exists(f): os.remove(f)
        
    # លុប Processing Status
    status_processing.empty()
    
    # ✅ Status: Success
    st.success(f"✅ Success: បង្កើតសំឡេងបានជោគជ័យចំនួន {len(combined_status)} Segment!")
    
    # បង្ហាញលទ្ធផលឱ្យស្តាប់ និងទាញយក
    with st.expander("🎙️ ស្តាប់ និងទាញយកសំឡេងដែលបាន Dub"):
        st.audio("final_dubbed.mp3", format="audio/mp3")
        with open("final_dubbed.mp3", "rb") as f:
            st.download_button("💾 ទាញយកសំឡេង (MP3)", f, file_name="ai_dubbed_output.mp3", mime="audio/mp3")
            
    # បង្ហាញព័ត៌មានលម្អិតពីសំឡេងនីមួយៗ
    with st.expander("📝 ព័ត៌មានលម្អិតនៃការបែងចែកសំឡេង"):
        for stat in combined_status:
            st.write(stat)

elif generate_btn and not input_text:
    st.warning("⚠️ សូមបញ្ចូលអក្សរជាមុនសិន!")

