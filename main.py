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

st.title("🎬 Burmese Movie Recap AI (YouTuber Style)")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Gemini API Key:", type="password")
    
    # 429 Error သက်သာစေရန် Model ရွေးချယ်မှု ပြန်ထည့်ပေးထားပါသည်
    model_choice = st.selectbox(
        "AI Model ကိုရွေးပါ (429 Error တက်ပါက 1.5 ကို သုံးပါ)", 
        ["gemini-1.5-flash", "gemini-2.0-flash"]
    )
    
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
    """စာသားထဲမှ အချိန်များနှင့် စက္ကန့်/မိနစ် များကို အလိုအလျောက် ဖြတ်ထုတ်ခြင်း"""
    text = re.sub(r'(\[?\d{1,2}:\d{2}(:\d{2})?\]?)|(-->)|(\d{1,2}\s?မိနစ်)|(\d{1,2}\s?စက္ကန့်)', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

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
        if not api_key: 
            st.error("Sidebar တွင် API Key အရင်ထည့်ပါ။")
        elif not uploaded_file: 
            st.warning("ဗီဒီယို အရင်တင်ပါ။")
        else:
            try:
                with st.spinner(f"{model_choice} စနစ်ဖြင့် YouTuber Recap ရေးသားနေပါသည်..."):
                    model = genai.GenerativeModel(model_choice)
                    video_file = genai.upload_file(path=st.session_state.video_path)
                    
                    while video_file.state.name == "PROCESSING": 
                        time.sleep(2)
                        video_file = genai.get_file(video_file.name)
                    
                    target_words = int((video_duration / 60) * 140)
                    
                    prompt = f"""
                    မင်းက အရမ်းနာမည်ကြီးတဲ့ မြန်မာ Movie Recap YouTuber တစ်ယောက်ပါ။ 
                    ဒီဗီဒီယိုကို ကြည့်ပြီး ပရိသတ်တွေ ရင်ခုန်စိတ်လှုပ်ရှားသွားအောင် Recap Script ရေးပေးပါ။
                    
                    လိုအပ်ချက်များ (Strict Requirements):
                    ၁။ 00:00 (Timestamps) တွေ၊ စက္ကန့်တွေ၊ မိနစ်တွေကို လုံးဝ(လုံးဝ) မထည့်ပါနဲ့။ စာသားသက်သက် Narrative Style ပဲ ရေးပါ။
                    ၂။ စကားပြောပုံစံက အရမ်း energetic ဖြစ်ပါစေ။ 'ကဲ... ဒီနေ့မှာတော့', 'တကယ့်ကို ရင်ခုန်ဖို့ကောင်းတာဗျာ', 'ဇာတ်လမ်းလေးကတော့' စတဲ့ ဆွဲဆောင်မှုရှိတဲ့ စကားလုံးတွေ သုံးပါ။
                    ၃။ စာသားကို စာပိုဒ်တဆက်တည်း YouTuber တစ်ယောက် Recap ပြောပြနေသလို ရေးပေးပါ။
                    ၄။ ဗီဒီယိုကြာချိန်က {int(video_duration)} စက္ကန့် ဖြစ်လို့ စာလုံးရေ {target_words} ခန့်ပဲ ရေးပေးပါ။
                    """
                    
                    response = model.generate_content([prompt, video_file])
                    st.session_state['recap_script'] = clean_script(response.text)
                    st.success("အောင်မြင်စွာ ရေးသားပြီးပါပြီ!")
            except Exception as e: 
                if "429" in str(e):
                    st.error("Error 429: အခမဲ့အသုံးပြုနိုင်သည့် အကြိမ်ရေ ပြည့်သွားပါပြီ။ ၁ မိနစ်ခန့်စောင့်ပါ သို့မဟုတ် Sidebar တွင် 'gemini-1.5-flash' သို့ ပြောင်းလဲအသုံးပြုကြည့်ပါ။")
                else:
                    st.error(f"Error Details: {str(e)}")

# --- Output & Sync Section ---
if 'recap_script' in st.session_state:
    st.divider()
    st.write("### 📜 Generated YouTuber Recap Script")
    
    final_clean = clean_script(st.session_state['recap_script'])
    edited_script = st.text_area("Script ကို လိုအပ်သလို ပြင်ဆင်ပါ (အချိန်စာသားများ မပါစေရ):", final_clean, height=250)
    st.session_state['recap_script'] = edited_script

    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        if st.button("🔊 အသံဖိုင် (Audio) ထုတ်မည်"):
            with st.spinner("အသံဖိုင် ဖန်တီးနေပါသည်..."):
                audio_output = "recap_audio.mp3"
                asyncio.run(generate_audio(st.session_state['recap_script'], audio_output, voice_name, speed_param))
                st.session_state.actual_audio_dur = get_mp3_duration(audio_output)

    if 'actual_audio_dur' in st.session_state:
        with btn_col2:
            if st.button("⚡ Auto Sync Speed (ဗီဒီယိုနှင့် အချိန်ညှိမည်)"):
                ratio = st.session_state.actual_audio_dur / video_duration
                new_speed = st.session_state.v_speed * ratio
                st.session_state.v_speed = max(0.3, min(2.0, round(new_speed, 2)))
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