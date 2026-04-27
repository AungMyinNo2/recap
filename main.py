import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions
import edge_tts
import asyncio
import os
import tempfile
import time
import random  
from moviepy.editor import VideoFileClip, AudioFileClip

# --- Configuration ---
st.set_page_config(page_title="AI Movie Recap Master", layout="wide", page_icon="🎙️")

# --- Session State Initializing ---
if 'recap_script' not in st.session_state: st.session_state.recap_script = ""
if 'srt_content' not in st.session_state: st.session_state.srt_content = ""
if 'current_key_index' not in st.session_state: st.session_state.current_key_index = 0
if 'video_objects' not in st.session_state: st.session_state.video_objects = {} # Key တစ်ခုချင်းစီအတွက် file object သိမ်းရန်

# --- API Key Management ---
def get_all_keys():
    if "GEMINI_KEYS" not in st.secrets:
        st.error("❌ Secrets ထဲမှာ 'GEMINI_KEYS' ထည့်ပေးပါ။")
        st.stop()
    return list(st.secrets["GEMINI_KEYS"])

def configure_next_key():
    keys = get_all_keys()
    st.session_state.current_key_index = (st.session_state.current_key_index + 1) % len(keys)
    new_key = keys[st.session_state.current_key_index].strip()
    genai.configure(api_key=new_key)
    return new_key

# --- Robust Upload & Generation Function ---
def process_with_ai(video_path, prompt):
    keys = get_all_keys()
    # လက်ရှိ key ကို အရင်သုံးကြည့်မယ်
    for _ in range(len(keys)):
        current_key = keys[st.session_state.current_key_index].strip()
        genai.configure(api_key=current_key)
        
        try:
            # ၁။ ဒီ Key အတွက် ဗီဒီယို upload တင်ပြီးသားရှိမရှိ စစ်မယ်
            if current_key not in st.session_state.video_objects:
                with st.spinner(f"♻️ Key ပြောင်းလဲနေသည်... ဗီဒီယိုကို အသစ်ပြန်တင်နေပါသည်..."):
                    video_file = genai.upload_file(path=video_path)
                    while video_file.state.name == "PROCESSING":
                        time.sleep(2)
                        video_file = genai.get_file(video_file.name)
                    st.session_state.video_objects[current_key] = video_file
            
            # ၂။ Content ထုတ်မယ်
            video_obj = st.session_state.video_objects[current_key]
            model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            response = model.generate_content([prompt, video_obj])
            return response.text

        except exceptions.ResourceExhausted:
            st.warning(f"⚠️ Key {st.session_state.current_key_index + 1} Quota ပြည့်သွားပါပြီ။ နောက် Key တစ်ခုကို ကြိုးစားနေသည်...")
            configure_next_key() # Key ပြောင်းမယ်
            continue # ပတ်လမ်းအစက ပြန်စမယ်
        except Exception as e:
            st.error(f"❌ Error ဖြစ်သွားပါသည်: {str(e)}")
            return None
    return "API Keys အားလုံး Quota ပြည့်သွားပါပြီ။ ခေတ္တစောင့်ပြီးမှ ပြန်စမ်းပါ။"

# --- Audio Logic ---
async def generate_audio(text, output, voice, rate="+0%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output)

# --- Main UI ---
st.title("🎙️ Movie Recap Master (Stable Version)")

v_file = st.file_uploader("Video တင်ပါ...", type=["mp4", "mov", "avi"])

if v_file:
    # ဗီဒီယိုအသစ်တင်လျှင် Cache များရှင်းလင်းရန်
    if "last_v_name" not in st.session_state or st.session_state.last_v_name != v_file.name:
        st.session_state.video_objects = {}
        st.session_state.recap_script = ""
        st.session_state.srt_content = ""
        st.session_state.last_v_name = v_file.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(v_file.read())
        video_path = tmp.name

    with VideoFileClip(video_path) as v_clip:
        v_dur = v_clip.duration
        st.video(v_file)

        tab1, tab2 = st.tabs(["📝 Recap & Voice", "🎯 SRT Subtitles"])

        with tab1:
            if st.button("📝 Generate Recap Script"):
                prompt = "ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Movie Recap Script တစ်ခု ရေးပေးပါ။"
                result = process_with_ai(video_path, prompt)
                if result: st.session_state.recap_script = result
            
            if st.session_state.recap_script:
                st.session_state.recap_script = st.text_area("Edit Script:", st.session_state.recap_script, height=250)
                if st.button("🚀 Generate Voice"):
                    mp3_temp = "temp.mp3"
                    asyncio.run(generate_audio(st.session_state.recap_script, mp3_temp, "my-MM-ThihaNeural"))
                    with AudioFileClip(mp3_temp) as ac:
                        speed = f"{round(((ac.duration/v_dur)-1)*100):+}%"
                    final_mp3 = "final.mp3"
                    asyncio.run(generate_audio(st.session_state.recap_script, final_mp3, "my-MM-ThihaNeural", rate=speed))
                    st.audio(final_mp3)

        with tab2:
            if st.button("🎯 Generate SRT File"):
                prompt = "ဤဗီဒီယိုအတွက် အချိန်ကိုက် မြန်မာဘာသာ SRT Subtitle ထုတ်ပေးပါ။"
                result = process_with_ai(video_path, prompt)
                if result: st.session_state.srt_content = result
            
            if st.session_state.srt_content:
                st.text_area("SRT:", st.session_state.srt_content, height=250)

    os.remove(video_path)