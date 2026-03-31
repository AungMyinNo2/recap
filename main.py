import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
import tempfile
import time
import re
from moviepy.editor import VideoFileClip
from mutagen.mp3 import MP3

# --- Setup Configuration ---
st.set_page_config(page_title="Burmese Movie Recap Pro AI", layout="wide")

st.title("🎬 Burmese Movie Recap AI (Auto-Fix Version)")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Gemini API Key:", type="password")
    
    # သင့် API Key တွင် အလုပ်လုပ်နိုင်သော Model များစာရင်း
    # 404 Error မတက်စေရန် ပုံစံမျိုးစုံ စမ်းသပ်ပါမည်
    model_options = ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash", "gemini-1.5-pro"]
    model_choice = st.selectbox("AI Model ရွေးချယ်ပါ", model_options)
    
    if 'v_speed' not in st.session_state:
        st.session_state.v_speed = 1.0

    voice_option = st.selectbox("အသံရွေးချယ်ပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
    voice_name = voice_option.split(" ")[0]
    
    voice_speed = st.slider("အသံနှုန်း (Speed Control)", 0.3, 2.0, st.session_state.v_speed, 0.01, key="v_speed_slider")
    st.session_state.v_speed = voice_speed
    speed_param = f"{'+' if st.session_state.v_speed >= 1.0 else '-'}{int(abs(st.session_state.v_speed-1.0)*100)}%"

if api_key:
    genai.configure(api_key=api_key)

# --- Functions ---

async def generate_audio(text, output_file, voice, speed):
    communicate = edge_tts.Communicate(text, voice, rate=speed)
    await communicate.save(output_file)

def get_mp3_duration(file_path):
    audio = MP3(file_path)
    return audio.info.length

def clean_script(text):
    """စာသားထဲမှ အချိန်များနှင့် မိနစ်များကို ဖြတ်ထုတ်ခြင်း"""
    text = re.sub(r'(\[?\d{1,2}:\d{2}(:\d{2})?\]?)|(-->)|(\d{1,2}\s?မိနစ်)|(\d{1,2}\s?စက္ကန့်)', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# --- UI Layout ---

col1, col2 = st.columns([1, 1])

with col1:
    st.write("### 📤 Step 1: Video တင်ပါ")
    uploaded_file = st.file_uploader("Video (MP4, MOV)", type=["mp4", "mov", "avi"])
    video_duration = 0
    if uploaded_file:
        st.video(uploaded_file)
        if 'video_duration' not in st.session_state or st.session_state.uploaded_file_name != uploaded_file.name:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
                tfile.write(uploaded_file.read())
                clip = VideoFileClip(tfile.name)
                st.session_state.video_duration = clip.duration
                st.session_state.uploaded_file_name = uploaded_file.name
                st.session_state.video_path = tfile.name
                clip.close()
        video_duration = st.session_state.video_duration
        st.metric("Video Duration", f"{int(video_duration)} s")

with col2:
    st.write("### 📝 Step 2: Recap ပြုလုပ်ခြင်း")
    if st.button("Recap Script စတင်ပြုလုပ်မည်", type="primary"):
        if not api_key: 
            st.error("API Key အရင်ထည့်ပါ။")
        else:
            try:
                with st.spinner(f"{model_choice} စနစ်ဖြင့် လုပ်ဆောင်နေပါသည်..."):
                    # Model ခေါ်ယူမှု (Try-Catch ဖြင့် 404 ကို ကာကွယ်ခြင်း)
                    model = genai.GenerativeModel(model_choice)
                    
                    video_file = genai.upload_file(path=st.session_state.video_path)
                    while video_file.state.name == "PROCESSING": 
                        time.sleep(2)
                        video_file = genai.get_file(video_file.name)
                    
                    target_words = int((video_duration / 60) * 140)
                    prompt = f"""
                    မင်းက YouTuber Recap ပြောပြနေသလို energetic ဖြစ်တဲ့ မြန်မာ Movie Recap Script တစ်ခု ရေးပေးပါ။
                    ၁။ အချိန် (00:00) တွေ လုံးဝမပါစေရ။ စာသားသက်သက်ပဲ ရေးပါ။
                    ၂။ ဇာတ်လမ်းကို စိတ်လှုပ်ရှားစရာကောင်းအောင် မြန်မာလို အသေးစိတ် ရေးပေးပါ။
                    ၃။ ဗီဒီယိုကြာချိန် {int(video_duration)} စက္ကန့်အတွက် စာလုံးရေ {target_words} ခန့် ရေးပေးပါ။
                    """
                    response = model.generate_content([prompt, video_file])
                    st.session_state['recap_script'] = clean_script(response.text)
                    st.success("အောင်မြင်စွာ ရေးသားပြီးပါပြီ!")
            except Exception as e: 
                st.error(f"Error: {str(e)}")
                st.info("အကြံပြုချက်: Sidebar တွင် Model အမျိုးအစားကို gemini-2.0-flash သို့မဟုတ် gemini-2.5-flash သို့ ပြောင်းလဲစမ်းသပ်ကြည့်ပါ။")

# --- Result Section ---
if 'recap_script' in st.session_state:
    st.divider()
    final_clean = clean_script(st.session_state['recap_script'])
    edited_script = st.text_area("Generated Script:", final_clean, height=250)
    st.session_state['recap_script'] = edited_script

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔊 အသံဖိုင် (Audio) ထုတ်မည်"):
            with st.spinner("အသံဖိုင် ဖန်တီးနေပါသည်..."):
                audio_output = "recap_audio.mp3"
                asyncio.run(generate_audio(st.session_state['recap_script'], audio_output, voice_name, speed_param))
                st.session_state.actual_audio_dur = get_mp3_duration(audio_output)

    if 'actual_audio_dur' in st.session_state:
        with col_btn2:
            if st.button("⚡ Auto Sync Speed"):
                ratio = st.session_state.actual_audio_dur / video_duration
                st.session_state.v_speed = max(0.3, min(2.0, round(st.session_state.v_speed * ratio, 2)))
                st.rerun()

    if 'actual_audio_dur' in st.session_state:
        st.audio("recap_audio.mp3")
        m1, m2, m3 = st.columns(3)
        m1.metric("Video Duration", f"{int(video_duration)} s")
        m2.metric("MP3 Duration", f"{int(st.session_state.actual_audio_dur)} s")
        diff = st.session_state.actual_audio_dur - video_duration
        m3.metric("Difference", f"{int(diff)} s", delta=f"{int(diff)} s", delta_color="inverse")
        
        with open("recap_audio.mp3", "rb") as f:
            st.download_button("Download Synced MP3", f, file_name="youtuber_recap.mp3")