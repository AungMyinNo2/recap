import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
import tempfile
import time
import re  # စာသားထဲမှ အချိန်များကို ဖြတ်ရန်
from moviepy.editor import VideoFileClip
from mutagen.mp3 import MP3

# --- Setup Configuration ---
st.set_page_config(page_title="Burmese Movie Recap Pro AI", layout="wide")

st.title("🎬 Burmese Movie Recap AI (YouTuber Style)")

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

def clean_script(text):
    """စာသားထဲမှ အချိန် (00:00, 1:20, [15:00]) နှင့် မိနစ် ဟူသော စကားလုံးများကို အကုန်ဖြတ်ထုတ်ခြင်း"""
    # 00:00, 1:20, [05:30] ပုံစံများကို ရှာပြီး ဖြတ်မည်
    text = re.sub(r'(\[?\d{1,2}:\d{2}(:\d{2})?\]?)|(-->)|(\d{1,2}\s?မိနစ်)', '', text)
    # ပိုနေသော space များကို ရှင်းမည်
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
    if st.button("Recap Script စတင်ပြုလုပ်မည် (YouTuber Style)", type="primary"):
        if not api_key: st.error("API Key ထည့်ပါ။")
        else:
            try:
                with st.spinner("YouTuber တစ်ယောက်လို Recap ရေးသားနေပါသည်..."):
                    model = genai.GenerativeModel('gemini-2.0-flash') # Gemini 2.0 ကိုသုံးထားပါသည်
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
                    ၃။ စာသားကို SRT ပုံစံမဟုတ်ဘဲ စာပိုဒ်တဆက်တည်း YouTuber တစ်ယောက် Recap ပြောပြနေသလို ရေးပေးပါ။
                    ၄။ ဗီဒီယိုကြာချိန်က {int(video_duration)} စက္ကန့် ဖြစ်လို့ စာလုံးရေ {target_words} ခန့်ပဲ ရေးပေးပါ။
                    """
                    
                    response = model.generate_content([prompt, video_file])
                    # ထွက်လာတဲ့ စာသားကို နောက်တစ်ကြိမ် Clean လုပ်မည်
                    st.session_state['recap_script'] = clean_script(response.text)
            except Exception as e: st.error(str(e))

# --- Output & Sync Section ---
if 'recap_script' in st.session_state:
    st.divider()
    st.write("### 📜 Generated YouTuber Recap Script")
    
    # Text area ထဲမှာ စာသားကို နောက်ဆုံးအကြိမ် Clean လုပ်ပြီး ပြမည်
    final_clean = clean_script(st.session_state['recap_script'])
    edited_script = st.text_area("Script ကို လိုအပ်သလို ပြင်ဆင်ပါ (အချိန်စာသားများ မပါစေရ):", final_clean, height=250)
    st.session_state['recap_script'] = edited_script

    btn_col1, btn_col2 = st.columns(2)
    
    with btn_col1:
        if st.button("🔊 အသံဖိုင် (Audio) ထုတ်မည်"):
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