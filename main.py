import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import os
import tempfile
import time
import random  
from moviepy.editor import VideoFileClip

# --- Configuration ---
st.set_page_config(page_title="AI Movie Recap Master", layout="wide", page_icon="🎙️")

# --- API Key Logic ---
def configure_genai():
    if "GEMINI_KEYS" not in st.secrets:
        st.error("❌ Secrets ထဲမှာ 'GEMINI_KEYS' ထည့်ပေးပါ။")
        st.stop()
    
    if "active_api_key" not in st.session_state:
        keys = list(st.secrets["GEMINI_KEYS"])
        st.session_state.active_api_key = random.choice(keys).strip()

    genai.configure(api_key=st.session_state.active_api_key)
    # မော်ဒယ်အမည်ကို gemini-1.5-flash ပြောင်းလိုက်ပါ (ဒါက အလုပ်လုပ်တဲ့ အမည်ပါ)
    return genai.GenerativeModel(model_name="gemini-1.5-flash")

# --- Initialize Session States ---
if 'recap_script' not in st.session_state: st.session_state.recap_script = ""
if 'srt_content' not in st.session_state: st.session_state.srt_content = ""
if 'gemini_file_obj' not in st.session_state: st.session_state.gemini_file_obj = None
if 'current_v_name' not in st.session_state: st.session_state.current_v_name = ""

# --- Helper Functions ---
def upload_video_to_gemini(path):
    """ဗီဒီယိုကို Gemini ဆီ တစ်ကြိမ်ပဲ Upload တင်မယ်"""
    model = configure_genai()
    with st.status("🚀 Gemini ထံသို့ ဗီဒီယို ပေးပို့နေသည်...", expanded=True) as status:
        st.write("ဗီဒီယိုဖိုင်ကို ဖတ်နေသည်...")
        video_file = genai.upload_file(path=path)
        st.write(f"ပို့ပြီးပါပြီ။ Processing လုပ်နေသည် (File ID: {video_file.name})...")
        
        # Processing ပြီးတဲ့အထိ စောင့်မယ်
        while video_file.state.name == "PROCESSING":
            time.sleep(3)
            video_file = genai.get_file(video_file.name)
        
        status.update(label="✅ ဗီဒီယို အဆင်သင့်ဖြစ်ပါပြီ!", state="complete", expanded=False)
    return video_file

# --- Main UI ---
st.title("🎙️ Movie Recap Master")

v_file = st.file_uploader("ဗီဒီယို ရွေးပါ...", type=["mp4", "mov", "avi"])

if v_file:
    # ဗီဒီယိုအသစ်ဖြစ်လျှင် Reset လုပ်မယ်
    if st.session_state.current_v_name != v_file.name:
        st.session_state.gemini_file_obj = None
        st.session_state.recap_script = ""
        st.session_state.srt_content = ""
        st.session_state.current_v_name = v_file.name

    # ဗီဒီယိုကို Temp သိမ်းမယ်
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(v_file.read())
        video_path = tmp.name

    st.video(v_file)

    # ဗီဒီယိုကို Gemini ဆီ ပို့မယ် (မပို့ရသေးရင်)
    if st.session_state.gemini_file_obj is None:
        st.session_state.gemini_file_obj = upload_video_to_gemini(video_path)

    tab1, tab2 = st.tabs(["📝 Script & Voice", "🎯 SRT Subtitles"])

    with tab1:
        if st.button("📝 Generate Script Now"):
            if st.session_state.gemini_file_obj:
                with st.spinner("AI က ဇာတ်လမ်းကို ကြည့်ပြီး Script ရေးနေပါတယ်..."):
                    model = configure_genai()
                    prompt = "ဤဗီဒီယိုကိုကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ်ရာ မြန်မာဘာသာ Movie Recap Script တစ်ခုကို Narrative Style ဖြင့် ရေးပေးပါ။"
                    try:
                        response = model.generate_content([prompt, st.session_state.gemini_file_obj])
                        st.session_state.recap_script = response.text
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        if st.session_state.recap_script:
            st.session_state.recap_script = st.text_area("Script ကို ပြင်ဆင်ရန်:", value=st.session_state.recap_script, height=300)

    with tab2:
        if st.button("🎯 Generate SRT Now"):
            if st.session_state.gemini_file_obj:
                with st.spinner("အချိန်ကိုက် စာတန်းထိုး ထုတ်နေပါတယ်..."):
                    model = configure_genai()
                    prompt = "ဤဗီဒီယိုအတွက် မြန်မာဘာသာ SRT format (00:00:00,000) စာတန်းထိုး ထုတ်ပေးပါ။"
                    try:
                        response = model.generate_content([prompt, st.session_state.gemini_file_obj])
                        st.session_state.srt_content = response.text
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        if st.session_state.srt_content:
            st.text_area("SRT Result:", value=st.session_state.srt_content, height=300)

    # ရှင်းလင်းရေး
    if os.path.exists(video_path):
        os.remove(video_path)