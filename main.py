import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
import tempfile
import time

# --- Setup Configuration ---
st.set_page_config(page_title="Burmese Movie Recap AI", layout="wide")

st.title("🎬 Burmese Movie Recap AI")

# Sidebar for Settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Gemini API Key ကိုထည့်ပါ:", type="password")
    voice_option = st.selectbox("အသံရွေးချယ်ပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
    voice_name = voice_option.split(" ")[0]

# API Configuration
if api_key:
    genai.configure(api_key=api_key)

# --- Functions ---

async def generate_audio(text, output_file, voice):
    """မြန်မာအသံဖိုင် ဖန်တီးခြင်း"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def get_model_response(content_list):
    """Model နာမည် ပုံစံအမျိုးမျိုးဖြင့် စမ်းသပ်ခေါ်ဆိုခြင်း (404 Error ကာကွယ်ရန်)"""
    # စမ်းသပ်မည့် Model နာမည်များ
    model_names = ['gemini-1.5-flash', 'gemini-1.5-flash-latest', 'models/gemini-1.5-flash']
    
    last_error = ""
    for name in model_names:
        try:
            model = genai.GenerativeModel(model_name=name)
            response = model.generate_content(content_list)
            return response.text
        except Exception as e:
            last_error = str(e)
            continue # နောက်ထပ် Model နာမည်တစ်ခုဖြင့် ထပ်စမ်းမည်
            
    raise Exception(f"Model အားလုံး Error တက်နေပါသည်: {last_error}")

def process_video_with_gemini(video_path):
    """Video ကို Gemini ဆီပို့ပြီး Script ထုတ်ခြင်း"""
    # Video Upload to Gemini Cloud
    video_file = genai.upload_file(path=video_path)
    
    status_text = st.empty()
    status_text.info("⏳ Gemini က ဗီဒီယိုကို စစ်ဆေးနေပါတယ်။ (၁ မိနစ်ခန့် ကြာနိုင်သည်)")
    
    # Wait for processing
    while video_file.state.name == "PROCESSING":
        time.sleep(3)
        video_file = genai.get_file(video_file.name)
    
    if video_file.state.name == "FAILED":
        return "Video processing failed on Gemini side."

    status_text.success("✅ ဗီဒီယိုဖတ်ပြီးပါပြီ။ Script ရေးသားနေပါတယ်။")

    prompt = "မင်းက ကျွမ်းကျင်တဲ့ မြန်မာ Movie Recap YouTuber တစ်ယောက်ပါ။ ဒီဗီဒီယိုကို ကြည့်ပြီး စိတ်ဝင်စားစရာကောင်းတဲ့ Recap Script တစ်ခုကို မြန်မာလို အသေးစိတ် ရေးပေးပါ။"
    
    # Model ကို ပုံစံမျိုးစုံဖြင့် ခေါ်ယူခြင်း
    return get_model_response([prompt, video_file])

# --- UI Layout ---

col1, col2 = st.columns([1, 1])

with col1:
    st.write("### 📤 Step 1: Video တင်ပါ")
    uploaded_file = st.file_uploader("Video ဖိုင် (MP4, MOV)", type=["mp4", "mov", "avi"])
    if uploaded_file:
        st.video(uploaded_file)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
            tfile.write(uploaded_file.read())
            video_path = tfile.name

with col2:
    st.write("### 📝 Step 2: Recap ပြုလုပ်ခြင်း")
    transcript_input = st.text_area("စာသား (ရှိလျှင်) ထည့်ပါ (မရှိလျှင် Video မှ Auto ထုတ်မည်)", height=200)
    
    if st.button("Recap Script စတင်ပြုလုပ်မည်", type="primary"):
        if not api_key:
            st.error("Gemini API Key ကို Sidebar မှာ အရင်ထည့်ပါ။")
        else:
            try:
                with st.spinner("AI လုပ်ဆောင်နေပါတယ်..."):
                    if transcript_input.strip():
                        final_script = get_model_response([f"Rewrite this as an exciting Burmese Movie Recap script: {transcript_input}"])
                    elif uploaded_file:
                        final_script = process_video_with_gemini(video_path)
                    else:
                        st.warning("Video တင်ပါ သို့မဟုတ် စာသားထည့်ပါ။")
                        final_script = None

                    if final_script:
                        st.session_state['recap_script'] = final_script
                        st.success("Script ရေးသားပြီးပါပြီ!")
            except Exception as e:
                st.error(f"Error Details: {str(e)}")
                st.info("အကြံပြုချက်: API Key အသစ်တစ်ခုဖြင့် ထပ်စမ်းကြည့်ပါ။")

# --- Result Section ---
if 'recap_script' in st.session_state:
    st.divider()
    st.write("### 📜 Generated Script")
    edited_script = st.text_area("Script ပြင်ဆင်ရန်:", st.session_state['recap_script'], height=300)
    
    if st.button("🔊 အသံဖိုင် (Audio) ထုတ်မည်"):
        with st.spinner("ကြည်လင်တဲ့ မြန်မာအသံဖိုင် ဖန်တီးနေပါတယ်..."):
            audio_output = "recap_audio.mp3"
            asyncio.run(generate_audio(edited_script, audio_output, voice_name))
            st.audio(audio_output)
            with open(audio_output, "rb") as f:
                st.download_button("Download MP3", f, file_name="recap.mp3")