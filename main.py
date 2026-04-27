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

# --- API Key Logic (Sticky Key - Session တစ်ခုလုံးအတွက် Key တစ်ခုပဲ သုံးမည်) ---
def initialize_gemini():
    if "GEMINI_KEYS" not in st.secrets:
        st.error("❌ Secrets ထဲမှာ 'GEMINI_KEYS' ထည့်ပေးပါ။")
        st.stop()
    
    # Session စစချင်းမှာ Key တစ်ခုပဲ ရွေးပြီး အသေမှတ်ထားမယ်
    if "active_api_key" not in st.session_state:
        keys = list(st.secrets["GEMINI_KEYS"])
        st.session_state.active_api_key = random.choice(keys).strip()
    
    genai.configure(api_key=st.session_state.active_api_key)
    # Model အမည်ကို သင်အသုံးပြုလိုသည့်အတိုင်း 2.5-flash ထားရှိပါသည်
    return genai.GenerativeModel(model_name="gemini-2.5-flash")

# --- Initialize Session States ---
if 'recap_script' not in st.session_state: st.session_state.recap_script = ""
if 'srt_content' not in st.session_state: st.session_state.srt_content = ""
if 'gemini_file_obj' not in st.session_state: st.session_state.gemini_file_obj = None
if 'current_v_name' not in st.session_state: st.session_state.current_v_name = ""

# --- Functions ---
async def generate_audio_file(text, output_path, voice, rate="+0%", volume="+0%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(output_path)

def upload_to_gemini(path):
    """ဗီဒီယိုကို Gemini ဆီ တစ်ကြိမ်သာ Upload တင်ရန်"""
    model = initialize_gemini()
    with st.status("🚀 Video ကို Gemini ထံ ပေးပို့နေသည်...", expanded=True) as status:
        video_file = genai.upload_file(path=path)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
        status.update(label="✅ Video အဆင်သင့်ဖြစ်ပါပြီ!", state="complete", expanded=False)
    return video_file

# --- Sidebar ---
st.sidebar.title("⚙️ Audio Settings")
voice_choice = st.sidebar.radio("Recap ပြောမည့်သူ:", ["သီဟ", "နီလာ "])
voice_id = "my-MM-ThihaNeural" if "သီဟ" in voice_choice else "my-MM-NilarNeural"
volume_value = st.sidebar.slider("အသံ အတိုး/အလျော့ (%)", -50, 50, 0, step=10)
volume_str = f"{volume_value:+}%"

# --- Main UI ---
st.title("🎙️ Movie Recap Master")

v_file = st.file_uploader("Video တင်ပါ...", type=["mp4", "mov", "avi"])

if v_file:
    # ဗီဒီယိုအသစ်တင်လျှင် အရင် data များ ရှင်းထုတ်ရန်
    if st.session_state.current_v_name != v_file.name:
        st.session_state.gemini_file_obj = None
        st.session_state.recap_script = ""
        st.session_state.srt_content = ""
        st.session_state.current_v_name = v_file.name

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(v_file.read())
        video_path = tmp.name

    # ဗီဒီယိုပြသခြင်းနှင့် ကြာချိန်ယူခြင်း
    with VideoFileClip(video_path) as v_clip:
        v_dur = v_clip.duration
        st.video(v_file)
        st.info(f"🎞 ဗီဒီယိုကြာချိန် - {v_dur:.2f} စက္ကန့်")

        # တစ်ကြိမ်သာ Upload တင်ခြင်း (Permission Error မတက်စေရန်)
        if st.session_state.gemini_file_obj is None:
            st.session_state.gemini_file_obj = upload_to_gemini(video_path)
        
        video_obj = st.session_state.gemini_file_obj

        tab1, tab2 = st.tabs(["📝 Recap & Voice", "🎯 SRT Subtitles"])

        # --- Recap Tab ---
        with tab1:
            if st.button("📝 Generate Recap Script"):
                with st.spinner("Gemini 2.5 က Script ရေးနေပါတယ်..."):
                    model = initialize_gemini()
                    prompt = "ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Movie Recap Script တစ်ခု ရေးပေးပါ။ စာသားသက်သက်ပဲ ပြန်ပေးပါ။"
                    response = model.generate_content([prompt, video_obj])
                    st.session_state.recap_script = response.text
            
            if st.session_state.recap_script:
                st.session_state.recap_script = st.text_area("Edit Script:", value=st.session_state.recap_script, height=250)
                if st.button("🚀 Generate Audio & Sync"):
                    with st.spinner("အသံနှုန်း ညှိနေပါတယ်..."):
                        mp3_temp = "temp_audio.mp3"
                        asyncio.run(generate_audio_file(st.session_state.recap_script, mp3_temp, voice_id))
                        with AudioFileClip(mp3_temp) as audio_clip:
                            initial_dur = audio_clip.duration
                        speed_change = round(((initial_dur / v_dur) - 1) * 100)
                        final_mp3 = "final_recap.mp3"
                        asyncio.run(generate_audio_file(st.session_state.recap_script, final_mp3, voice_id, rate=f"{speed_change:+}%", volume=volume_str))
                        st.audio(final_mp3)
                        st.download_button("📥 Download MP3", open(final_mp3, "rb"), "recap.mp3")

        # --- SRT Tab ---
        with tab2:
            if st.button("🎯 Generate SRT File"):
                with st.spinner("SRT ဖန်တီးနေပါတယ်..."):
                    model = initialize_gemini()
                    prompt = "ဤဗီဒီယိုကို ကြည့်ပြီး အချိန်ကိုက် မြန်မာဘာသာ Standard SRT format (HH:MM:SS,mmm) ဖြင့် Subtitle ထုတ်ပေးပါ။"
                    response = model.generate_content([prompt, video_obj])
                    st.session_state.srt_content = response.text
            
            if st.session_state.srt_content:
                st.text_area("SRT Content:", value=st.session_state.srt_content, height=300)
                st.download_button("📥 Download SRT", st.session_state.srt_content, "subtitles.srt")

    os.remove(video_path)