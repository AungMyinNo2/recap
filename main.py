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

st.title("🎬 Burmese Movie Recap AI (Ultra Sync)")

# --- Session State Initializing ---
if 'v_speed' not in st.session_state:
    st.session_state.v_speed = 1.0
if 'usage_counter' not in st.session_state:
    st.session_state.usage_counter = 0
if 'current_key_index' not in st.session_state:
    st.session_state.current_key_index = 0

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # API Key Rotation
    keys_input = st.text_area("Gemini API Keys (တစ်ကြောင်းလျှင် တစ်ခု):", height=120)
    api_keys = [k.strip() for k in keys_input.split("\n") if k.strip()]
    
    active_key = None
    if api_keys:
        idx = st.session_state.current_key_index % len(api_keys)
        active_key = api_keys[idx]
        st.info(f"🔑 Key: {idx + 1}/{len(api_keys)} | 📊 Uses: {st.session_state.usage_counter}/10")
    
    # Voice Source Selection
    voice_source = st.radio("အသံအရင်းအမြစ် (Voice Source)", ["Edge-TTS (Burmese Native)", "Gemini Studio (AI Voices)"])
    
    if voice_source == "Edge-TTS (Burmese Native)":
        voice_option = st.selectbox("အသံရွေးပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
        voice_name = voice_option.split(" ")[0]
    else:
        # Google AI Studio Single Speaker Voices
        voice_name = st.selectbox("Gemini Voice ရွေးပါ", ["Aoede", "Charon", "Fenrir", "Kore", "Puck"])
        st.warning("မှတ်ချက်: Gemini AI အသံများသည် မြန်မာလေယူလေသိမ်း အနည်းငယ် လွဲနိုင်ပါသည်။")

    model_choice = st.selectbox("AI Model", ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"])
    
    # Speed Control
    voice_speed = st.slider("အသံနှုန်း (Speed Control)", 0.3, 2.0, value=st.session_state.v_speed, step=0.01)
    st.session_state.v_speed = voice_speed
    speed_param = f"{'+' if st.session_state.v_speed >= 1.0 else '-'}{int(abs(st.session_state.v_speed-1.0)*100)}%"

if active_key:
    genai.configure(api_key=active_key)

# --- Functions ---

async def generate_audio_edge(text, output_file, voice, speed):
    """Microsoft Edge TTS ဖြင့် အသံထုတ်ခြင်း"""
    communicate = edge_tts.Communicate(text, voice, rate=speed)
    await communicate.save(output_file)

def generate_audio_gemini(text, output_file, voice_name):
    """Google AI Studio (Gemini 2.0) ဖြင့် အသံထုတ်ခြင်း"""
    # Gemini 2.0 Flash သည်သာ Audio Generation ကို ကောင်းစွာထောက်ပံ့ပါသည်
    model = genai.GenerativeModel("gemini-2.0-flash")
    # Prompt ကို အသံထွက်ဖတ်ခိုင်းခြင်း
    prompt = f"Please read this Burmese text naturally using the {voice_name} voice style: {text}"
    
    # Speech generation config
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "audio/mpeg"}
    )
    
    # အသံဖိုင်ကို သိမ်းဆည်းခြင်း
    for part in response.candidates[0].content.parts:
        if part.inline_data:
            with open(output_file, "wb") as f:
                f.write(part.inline_data.data)
            return True
    return False

def get_mp3_duration(file_path):
    audio = MP3(file_path)
    return audio.info.length

def clean_script(text):
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
        st.metric("Original Video Duration", f"{int(video_duration)} s")

with col2:
    st.write("### 📝 Step 2: Recap ပြုလုပ်ခြင်း")
    if st.button("Recap Script စတင်ပြုလုပ်မည်", type="primary"):
        if not active_key: st.error("API Key ထည့်ပါ။")
        else:
            try:
                genai.configure(api_key=active_key)
                with st.spinner("AI Script ရေးသားနေပါသည်..."):
                    model = genai.GenerativeModel(model_choice)
                    video_file = genai.upload_file(path=st.session_state.video_path)
                    while video_file.state.name == "PROCESSING": time.sleep(2); video_file = genai.get_file(video_file.name)
                    
                    target_words = int((video_duration / 60) * 140)
                    prompt = f"""
                    ဒီဗီဒီယိုကို ကြည့်ပြီး ပရိသတ်တွေ ရင်ခုန်စိတ်လှုပ်ရှားသွားအောင် မြန်မာ Movie Recap Script ရေးပေးပါ။
                    ၁။ Timestamps တွေ လုံးဝ မထည့်ပါနဲ့။ Narrative Style ပဲ ရေးပါ။
                    ၂။ စကားပြောပုံစံက energetic ဖြစ်ပါစေ။ 'ကဲ... ဒီနေ့မှာတော့', 'တကယ့်ကို ရင်ခုန်ဖို့ကောင်းတာဗျာ' စတာတွေသုံးပါ။
                    ၃။ ဗီဒီယိုအဆုံးမှာ 'ဗီဒီယိုလေးကို ကြိုက်နှစ်သက်ရင် အပေါင်းလေးနှိပ်ပြီး အသဲလေးပေးသွားနော်' လို့ ထည့်ပြောပေးပါ။
                    ၄။ ဗီဒီယိုကြာချိန် {int(video_duration)} စက္ကန့်အတွက် စာလုံးရေ {target_words} ခန့် ရေးပေးပါ။
                    """
                    response = model.generate_content([prompt, video_file])
                    st.session_state['recap_script'] = clean_script(response.text)
                    st.session_state.usage_counter += 1
                    if st.session_state.usage_counter >= 10:
                        st.session_state.current_key_index += 1
                        st.session_state.usage_counter = 0
                    st.rerun()
            except Exception as e:
                if "429" in str(e):
                    st.session_state.current_key_index += 1
                    st.rerun()
                else: st.error(str(e))

# --- Result & Sync Section ---
if 'recap_script' in st.session_state:
    st.divider()
    edited_script = st.text_area("Generated Script:", st.session_state['recap_script'], height=200)
    st.session_state['recap_script'] = edited_script

    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🔊 အသံဖိုင် (Audio) ထုတ်မည်"):
            with st.spinner(f"{voice_source} ဖြင့် အသံဖိုင်ဖန်တီးနေပါသည်..."):
                audio_output = "recap_audio.mp3"
                if voice_source == "Edge-TTS (Burmese Native)":
                    asyncio.run(generate_audio_edge(st.session_state['recap_script'], audio_output, voice_name, speed_param))
                else:
                    generate_audio_gemini(st.session_state['recap_script'], audio_output, voice_name)
                
                st.session_state.actual_audio_dur = get_mp3_duration(audio_output)
                st.session_state.audio_ready = True

    if 'actual_audio_dur' in st.session_state:
        with col_btn2:
            if st.button("⚡ Auto Sync Speed (ဗီဒီယိုနှင့် အချိန်ညှိမည်)"):
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
            st.download_button("Download Synced MP3", f, file_name="final_recap.mp3")