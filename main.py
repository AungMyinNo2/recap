import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
import tempfile
import time
from moviepy.editor import VideoFileClip
from mutagen.mp3 import MP3  # MP3 ကြာချိန် တိုင်းရန်

# --- Setup Configuration ---
st.set_page_config(page_title="Burmese Movie Recap Ultra AI", layout="wide")

st.title("🎬 Burmese Movie Recap AI (Exact Time Sync)")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Gemini API Key:", type="password")
    
    model_map = {
        "💎 Gemini 2.5 Flash": "gemini-2.5-flash",
        "🔥 Gemini 2.5 Pro": "gemini-2.5-pro",
        "⚡ Gemini 2.0 Flash": "gemini-2.0-flash",
        "🧠 Gemini 2.0 Pro Exp": "gemini-2.0-pro-exp-02-05"
    }
    selected_display_name = st.selectbox("Model ရွေးချယ်ပါ", list(model_map.keys()))
    model_choice = model_map[selected_display_name]
    
    voice_option = st.selectbox("အသံရွေးချယ်ပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
    voice_name = voice_option.split(" ")[0]
    
    voice_speed = st.slider("အသံနှုန်း (Speed Control)", 0.5, 2.0, 1.0, 0.05)
    speed_param = f"{'+' if voice_speed >= 1.0 else '-'}{int(abs(voice_speed-1.0)*100)}%"

if api_key:
    genai.configure(api_key=api_key)

# --- Functions ---

async def generate_audio(text, output_file, voice, speed):
    communicate = edge_tts.Communicate(text, voice, rate=speed)
    await communicate.save(output_file)

def get_mp3_duration(file_path):
    """MP3 ဖိုင်၏ တကယ့်ကြာချိန်ကို စက္ကန့်ဖြင့် တိုင်းတာခြင်း"""
    audio = MP3(file_path)
    return audio.info.length

def process_video_with_gemini(video_path, selected_model, duration_sec):
    video_file = genai.upload_file(path=video_path)
    status_text = st.empty()
    status_text.info(f"⏳ {selected_model} က ဗီဒီယိုကို လေ့လာနေသည်...")
    
    while video_file.state.name == "PROCESSING":
        time.sleep(3)
        video_file = genai.get_file(video_file.name)
    
    target_words = int((duration_sec / 60) * 135)
    model = genai.GenerativeModel(model_name=selected_model)
    prompt = f"""မင်းက Movie Recap YouTuber တစ်ယောက်ပါ။ ဒီဗီဒီယိုကိုကြည့်ပြီး ဇာတ်လမ်းကို မြန်မာလို အသေးစိတ် ရေးပေးပါ။ 
    ဗီဒီယိုကြာချိန်က {int(duration_sec)} စက္ကန့် ဖြစ်လို့ စာလုံးရေ {target_words} ခန့်ပဲ ရေးပေးပါ။"""
    
    response = model.generate_content([prompt, video_file])
    return response.text

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
        st.metric("Original Video Duration", f"{int(video_duration)} s")

with col2:
    st.write("### 📝 Step 2: Recap ပြုလုပ်ခြင်း")
    if st.button("Recap Script စတင်ပြုလုပ်မည်", type="primary"):
        if not api_key: st.error("API Key ထည့်ပါ။")
        else:
            try:
                with st.spinner("AI Script ရေးသားနေပါသည်..."):
                    final_script = process_video_with_gemini(st.session_state.video_path, model_choice, video_duration)
                    st.session_state['recap_script'] = final_script
            except Exception as e:
                st.error(f"Error: {str(e)}")

# --- Output Section ---
if 'recap_script' in st.session_state:
    st.divider()
    st.write("### 📜 Generated Script & Final Sync")
    
    edited_script = st.text_area("Script ကို ပြင်ဆင်နိုင်သည်:", st.session_state['recap_script'], height=250)
    st.session_state['recap_script'] = edited_script

    if st.button("🔊 အသံဖိုင် (Audio) ထုတ်မည်"):
        with st.spinner("MP3 ဖန်တီးနေပါသည်..."):
            audio_output = "recap_audio.mp3"
            asyncio.run(generate_audio(st.session_state['recap_script'], audio_output, voice_name, speed_param))
            
            # အသံဖိုင်ဖန်တီးပြီးနောက် တကယ့်ကြာချိန်ကို တိုင်းတာခြင်း
            actual_audio_dur = get_mp3_duration(audio_output)
            
            # ရလဒ်များကို ပြသခြင်း
            st.audio(audio_output)
            
            # Metric များဖြင့် နှိုင်းယှဉ်ပြသခြင်း
            m_col1, m_col2, m_col3 = st.columns(3)
            m_col1.metric("Video Duration", f"{int(video_duration)} s")
            m_col2.metric("Actual MP3 Duration", f"{int(actual_audio_dur)} s")
            
            diff = actual_audio_dur - video_duration
            m_col3.metric("Difference", f"{int(diff)} s", delta=f"{int(diff)} s", delta_color="inverse")
            
            if abs(diff) < 5:
                st.success("✅ အချိန်ကိုက်မှု အလွန်ကောင်းမွန်ပါသည်။")
            elif diff > 0:
                st.warning(f"⚠️ အသံက ဗီဒီယိုထက် {int(diff)} စက္ကန့် ပိုရှည်နေပါသည်။ (Speed တင်ပါ သို့မဟုတ် စာသားလျှော့ပါ)")
            else:
                st.warning(f"⚠️ အသံက ဗီဒီယိုထက် {int(abs(diff))} စက္ကန့် ပိုတိုနေပါသည်။ (Speed လျှော့ပါ သို့မဟုတ် စာသားတိုးပါ)")

            with open(audio_output, "rb") as f:
                st.download_button("Download Synced MP3", f, file_name="final_recap.mp3")

st.markdown("---")
st.caption("Advanced Time-Sync Logic with Actual MP3 Duration Measurement")