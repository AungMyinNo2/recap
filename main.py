import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import os
import tempfile
import time
import random  
from moviepy.editor import VideoFileClip, AudioFileClip

# --- Configuration ---
st.set_page_config(page_title="AI Movie Recap Master", layout="wide", page_icon="🎙️")

# --- Fixed API Key Logic (Sticky Key for Session) ---
def get_model_for_session():
    """Session တစ်ခုလုံးအတွက် Key တစ်ခုတည်းကိုပဲ ရွေးချယ်ပေးမည့် Function"""
    if "GEMINI_KEYS" not in st.secrets:
        st.error("❌ Secrets ထဲမှာ 'GEMINI_KEYS' ထည့်ပေးပါ။")
        st.stop()
    
    # Session ထဲမှာ key မရှိသေးရင် တစ်ခု ကျပန်းရွေးပြီး သိမ်းထားမယ်
    if "active_api_key" not in st.session_state:
        keys = list(st.secrets["GEMINI_KEYS"])
        st.session_state.active_api_key = random.choice(keys).strip()

    genai.configure(api_key=st.session_state.active_api_key)
    # မော်ဒယ်အမည်ကို သင်သုံးထားသည့်အတိုင်း ထားပေးထားသည်
    return genai.GenerativeModel(model_name="gemini-2.5-flash")

# --- Session State Initializing ---
if 'recap_script' not in st.session_state: st.session_state.recap_script = ""
if 'srt_content' not in st.session_state: st.session_state.srt_content = ""
if 'movie_review' not in st.session_state: st.session_state.movie_review = ""
if 'gemini_file_obj' not in st.session_state: st.session_state.gemini_file_obj = None
if 'current_video_name' not in st.session_state: st.session_state.current_video_name = ""

# --- Shared Upload Function ---
def upload_once(path, name):
    # ဗီဒီယိုအသစ်ဖြစ်မှသာ Upload တင်မည် (Key တစ်ခုတည်းဖြင့်)
    if st.session_state.gemini_file_obj is None or st.session_state.current_video_name != name:
        model = get_model_for_session() # Key ကို Configure လုပ်ရန်
        with st.spinner("🤖 ဗီဒီယိုကို Gemini ဆီ ပို့နေသည်..."):
            video_file = genai.upload_file(path=path)
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = genai.get_file(video_file.name)
            st.session_state.gemini_file_obj = video_file
            st.session_state.current_video_name = name
    return st.session_state.gemini_file_obj

# --- AI Response Function ---
def get_ai_response(prompt, video_obj):
    model = get_model_for_session()
    try:
        response = model.generate_content([prompt, video_obj])
        return response.text
    except Exception as e:
        # အကယ်၍ key သေနေရင် key အသစ်လဲပြီး ပြန်ကြိုးစားရန်
        if "403" in str(e) or "401" in str(e):
            del st.session_state.active_api_key
            st.rerun()
        return f"Error: {str(e)}"

# --- Main UI ---
st.title("🎙️ Movie Recap Master")

v_file = st.file_uploader("Video တင်ပါ...", type=["mp4", "mov", "avi"])

if v_file:
    # ဗီဒီယိုအသစ်ဆိုလျှင် အရင် data တွေဖျက်မယ်
    if st.session_state.current_video_name != v_file.name:
        st.session_state.recap_script = ""
        st.session_state.srt_content = ""
        st.session_state.gemini_file_obj = None

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(v_file.read())
        video_path = tmp.name

    with VideoFileClip(video_path) as v_clip:
        v_dur = v_clip.duration
        st.video(v_file)
        
        # တစ်ကြိမ်သာ Upload တင်ခြင်း
        video_obj = upload_once(video_path, v_file.name)

        tab1, tab2, tab3 = st.tabs(["📝 Recap & Voice", "🎯 SRT Subtitles", "🎬 Title & Review"])

        with tab1:
            if st.button("📝 Generate Script"):
                prompt = "ဤဗီဒီယိုကို ကြည့်ပြီး Movie Recap Script ရေးပေးပါ။"
                st.session_state.recap_script = get_ai_response(prompt, video_obj)
            st.text_area("Edit:", value=st.session_state.recap_script, height=200)

        with tab2:
            if st.button("🎯 Generate SRT"):
                prompt = "ဤဗီဒီယိုအတွက် SRT Subtitle (HH:MM:SS,mmm) ထုတ်ပေးပါ။"
                st.session_state.srt_content = get_ai_response(prompt, video_obj)
            st.text_area("SRT:", value=st.session_state.srt_content, height=200)
            
    os.remove(video_path)