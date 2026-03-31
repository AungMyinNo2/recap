import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
import tempfile
import time
from moviepy.editor import VideoFileClip
from mutagen.mp3 import MP3

# --- Setup Configuration ---
st.set_page_config(page_title="Burmese Movie Recap Pro AI", layout="wide")

st.title("🎬 Burmese Movie Recap AI (Auto Time-Sync)")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Gemini API Key:", type="password")
    
    # Session state ကိုသုံးပြီး Slider တန်ဖိုးကို သိမ်းပါမယ်
    if 'v_speed' not in st.session_state:
        st.session_state.v_speed = 1.0

    voice_option = st.selectbox("အသံရွေးချယ်ပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
    voice_name = voice_option.split(" ")[0]
    
    # Slider value ကို session state နဲ့ ချိတ်ဆက်ထားပါတယ်
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

# --- UI Layout ---

col1, col2 = st.columns([1, 1])

with col1:
    st.write("### 📤 Step 1: Video တင်ပါ")
    uploaded_file = st.file_uploader("Video တင်ပါ", type=["mp4", "mov", "avi"])
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
        if not api_key: st.error("API Key ထည့်ပါ။")
        else:
            try:
                with st.spinner("AI Script ရေးသားနေပါသည်..."):
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    video_file = genai.upload_file(path=st.session_state.video_path)
                    while video_file.state.name == "PROCESSING": time.sleep(2); video_file = genai.get_file(video_file.name)
                    
                    target_words = int((video_duration / 60) * 135)
                    prompt = f"Movie Recap script in Burmese for {int(video_duration)}s video. Keep it around {target_words} words."
                    response = model.generate_content([prompt, video_file])
                    st.session_state['recap_script'] = response.text
            except Exception as e: st.error(str(e))

# --- Output & Sync Section ---
if 'recap_script' in st.session_state:
    st.divider()
    st.write("### 📜 Generated Script & Sync Tool")
    
    edited_script = st.text_area("Script ပြင်ဆင်ရန်:", st.session_state['recap_script'], height=200)
    st.session_state['recap_script'] = edited_script

    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        if st.button("🔊 အသံဖိုင် (Audio) ထုတ်မည်"):
            audio_output = "recap_audio.mp3"
            asyncio.run(generate_audio(st.session_state['recap_script'], audio_output, voice_name, speed_param))
            st.session_state.actual_audio_dur = get_mp3_duration(audio_output)
            st.session_state.audio_created = True

    # Audio ဖန်တီးပြီးမှသာ Auto Sync ခလုတ်ကို ပြပါမည်
    if 'actual_audio_dur' in st.session_state:
        with btn_col2:
            if st.button("⚡ Auto Sync Speed (ဗီဒီယိုနှင့် အချိန်ညှိမည်)"):
                # Ratio ကို တွက်ချက်ခြင်း (Target / Current)
                # Speed အသစ် = Current Speed * (Audio Duration / Video Duration)
                ratio = st.session_state.actual_audio_dur / video_duration
                new_speed = st.session_state.v_speed * ratio
                
                # Speed ကို limit အတွင်းထားခြင်း (0.3 to 2.0)
                st.session_state.v_speed = max(0.3, min(2.0, round(new_speed, 2)))
                
                st.success(f"Speed ကို {st.session_state.v_speed} သို့ အလိုအလျောက် ပြင်ဆင်ပြီးပါပြီ။ အသံဖိုင် ပြန်ထုတ်ပေးနေပါသည်။")
                st.rerun()

    if 'actual_audio_dur' in st.session_state:
        st.audio("recap_audio.mp3")
        m1, m2, m3 = st.columns(3)
        m1.metric("Video Duration", f"{int(video_duration)} s")
        m2.metric("MP3 Duration", f"{int(st.session_state.actual_audio_dur)} s")
        diff = st.session_state.actual_audio_dur - video_duration
        m3.metric("Difference", f"{int(diff)} s", delta=f"{int(diff)} s", delta_color="inverse")
        
        st.info(f"လက်ရှိ Speed: {st.session_state.v_speed}x")

        with open("recap_audio.mp3", "rb") as f:
            st.download_button("Download Synced MP3", f, file_name="final_recap.mp3")