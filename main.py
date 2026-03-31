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
    try:
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"API Configuration Error: {e}")

# --- Functions ---

async def generate_audio(text, output_file, voice):
    """မြန်မာအသံဖိုင် ဖန်တီးခြင်း"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def process_video_with_gemini(video_path):
    """Video ကို Gemini ဆီပို့ပြီး Script ထုတ်ခြင်း"""
    # Model name ကို အသစ်ဆုံး version ပြောင်းသုံးထားပါတယ်
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    # Video Upload
    video_file = genai.upload_file(path=video_path)
    
    status_text = st.empty()
    status_text.write("⏳ Gemini က ဗီဒီယိုကို စစ်ဆေးနေပါတယ်။ ခေတ္တစောင့်ပါ။")
    
    # Wait for processing
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    
    if video_file.state.name == "FAILED":
        st.error("ဗီဒီယိုကို ဖတ်လို့မရပါ။ ဖိုင်အမျိုးအစား ပြန်စစ်ပါ။")
        return None

    status_text.write("✅ ဗီဒီယိုဖတ်ပြီးပါပြီ။ Script ရေးသားနေပါတယ်။")

    prompt = """
    မင်းက ကျွမ်းကျင်တဲ့ မြန်မာ Movie Recap YouTuber တစ်ယောက်ပါ။ 
    ဒီဗီဒီယိုကို ကြည့်ပြီး စိတ်ဝင်စားစရာကောင်းတဲ့ Recap Script တစ်ခုကို မြန်မာလို ရေးပေးပါ။
    အရေးကြီးတဲ့ အခန်းတွေကို အစအဆုံး အသေးစိတ် ရေးပေးပါ။
    """
    
    response = model.generate_content([prompt, video_file])
    return response.text

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
                        model = genai.GenerativeModel('gemini-1.5-flash-latest')
                        response = model.generate_content(f"Rewrite this as a Burmese Movie Recap script: {transcript_input}")
                        final_script = response.text
                    elif uploaded_file:
                        final_script = process_video_with_gemini(video_path)
                    else:
                        st.warning("Video တင်ပါ သို့မဟုတ် စာသားထည့်ပါ။")
                        final_script = None

                    if final_script:
                        st.session_state['recap_script'] = final_script
                        st.success("Script ရေးသားပြီးပါပြီ!")
            except Exception as e:
                # Error ကို သေချာပြရန်
                st.error(f"Error Details: {str(e)}")

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