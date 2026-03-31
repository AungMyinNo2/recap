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

st.title("🎬 Burmese Movie Recap AI (Narrative Style)")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Gemini API Key:", type="password")
    
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
                st.session_state.uploaded_file_name = uploaded_file.n