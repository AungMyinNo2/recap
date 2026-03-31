import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
import tempfile
import time
from moviepy.editor import VideoFileClip

# --- Setup Configuration ---
st.set_page_config(page_title="Burmese Movie Recap AI (Ultimate)", layout="wide")

st.title("🎬 Burmese Movie Recap AI (Gemini 2.0 Generation)")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Model Settings")
    api_key = st.text_input("Gemini API Key:", type="password")
    
    # ဖုန်းမှာ မြင်ရတဲ့အတိုင်း Model များကို ခွဲခြားပေးထားပါတယ်
    model_map = {
        "🚀 Fast (Gemini 2.0 Flash)": "gemini-2.0-flash",
        "🧠 Thinking (Gemini 2.0 Flash-Thinking)": "gemini-2.0-flash-thinking-exp-01-21",
        "💎 Pro (Gemini 2.0 Pro Experimental)": "gemini-2.0-pro-exp-02-05",
        "⚖️ Standard (Gemini 1.5 Pro)": "gemini-1.5-pro"
    }
    
    selected_display_name = st.selectbox("အသုံးပြုမည့် Model ကိုရွေးပါ", list(model_map.keys()))
    model_choice = model_map[selected_display_name]
    
    voice_option = st.selectbox("အသံရွေးချယ်ပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
    voice_name = voice_option.split(" ")[0]
    
    voice_speed = st.slider("အသံနှုန်း (Speed Control)", 0.8, 1.5, 1.0, 0.05)
    speed_param = f"{'+' if voice_speed >= 1.0 else '-'}{int(abs(voice_speed-1.0)*100)}%"

if api_key:
    genai.configure(api_key=api_key)

# --- Functions ---

async def generate_audio(text, output_file, voice, speed):
    communicate = edge_tts.Communicate(text, voice, rate=speed)
    await communicate.save(output_file)

def process_video_with_gemini(video_path, selected_model, duration_sec):
    video_file = genai.upload_file(path=video_path)
    
    status_text = st.empty()
    status_text.info(f"⏳ {selected_model} စနစ်ဖြင့် ဗီဒီယိုကို လေ့လာနေပါသည်...")
    
    while video_file.state.name == "PROCESSING":
        time.sleep(3)
        video_file = genai.get_file(video_file.name)
    
    # ဗီဒီယို ကြာချိန်အရ စာလုံးရေ တွက်ချက်ခြင်း
    target_words = int((duration_sec / 60) * 130)

    model = genai.GenerativeModel(model_name=selected_model)
    
    # Thinking Model အတွက် ပိုမိုနက်နဲသော Prompt ကို သုံးပါမည်
    prompt = f"""
    မင်းက ကမ္ဘာကျော် မြန်မာ Movie Recap YouTuber တစ်ယောက်ပါ။ 
    ဒီဗီဒီယိုကို အသေးစိတ် ကြည့်ရှု လေ့လာပြီး ဇာတ်လမ်းကို စိတ်ဝင်စားစရာ အကောင်းဆုံး Recap Script တစ်ခု ရေးပေးပါ။
    
    လမ်းညွှန်ချက်များ:
    ၁။ ဗီဒီယိုကြာချိန်က {int(duration_sec)} စက္ကန့် ဖြစ်သောကြောင့် အသံဖတ်ချိန် စက္ကန့် {int(duration_sec)} ဝန်းကျင်တွင် ပြီးဆုံးရန် စာလုံးရေ {target_words} ခန့်သာ ရေးသားပါ။
    ၂။ Thinking Mode ၏ စွမ်းဆောင်ရည်ကို အသုံးပြု၍ ဇာတ်လမ်း၏ အနှစ်သာရနှင့် စိတ်လှုပ်ရှားစရာ အခန်းများကို ထင်ရှားအောင် ရေးပေးပါ။
    ၃။ စကားပြောပုံမှာ မြန်မာပရိသတ် ကြိုက်နှစ်သက်မည့် YouTuber Recap ပုံစံမျိုး ဖြစ်ရပါမည်။
    """
    
    response = model.generate_content([prompt, video_file])
    return response.text

# --- UI Layout ---

col1, col2 = st.columns([1, 1])

with col1:
    st.write("### 📤 Step 1: Video တင်ပါ")
    uploaded_file = st.file_uploader("Video (MP4, MOV, AVI)", type=["mp4", "mov", "avi"])
    video_duration = 0
    if uploaded_file:
        st.video(uploaded_file)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
            tfile.write(uploaded_file.read())
            video_path = tfile.name
            try:
                clip = VideoFileClip(video_path)
                video_duration = clip.duration
                st.warning(f"ဗီဒီယိုကြာချိန်: {int(video_duration)} စက္ကန့်")
                clip.close()
            except:
                pass

with col2:
    st.write("### 📝 Step 2: Recap Script ထုတ်ယူခြင်း")
    if st.button("Recap Script စတင်ပြုလုပ်မည် (Ultra Pro)", type="primary"):
        if not api_key:
            st.error("API Key ကို Sidebar တွင် ထည့်သွင်းပေးပါ။")
        elif not uploaded_file:
            st.warning("ဗီဒီယို အရင်တင်ပေးပါ။")
        else:
            try:
                with st.spinner(f"{selected_display_name} ဖြင့် လုပ်ဆောင်နေပါသည်..."):
                    final_script = process_video_with_gemini(video_path, model_choice, video_duration)
                    st.session_state['recap_script'] = final_script
                    st.success("Script ရေးသားမှု ပြီးမြောက်ပါပြီ!")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# --- Result Section ---
if 'recap_script' in st.session_state:
    st.divider()
    st.write("### 📜 Generated Recap Script")
    edited_script = st.text_area("Script ကို လိုအပ်သလို ပြင်ဆင်ပါ:", st.session_state['recap_script'], height=300)
    
    if st.button("🔊 အသံဖိုင် (Audio) ဖန်တီးမည်"):
        with st.spinner("ကြည်လင်သော မြန်မာအသံဖိုင် ဖန်တီးနေပါသည်..."):
            audio_output = "recap_audio.mp3"
            asyncio.run(generate_audio(edited_script, audio_output, voice_name, speed_param))
            st.audio(audio_output)
            with open(audio_output, "rb") as f:
                st.download_button("Download Audio (MP3)", f, file_name="movie_recap_pro.mp3")

st.markdown("---")
st.caption("Advanced AI Recap Engine | Support for Thinking & Pro Models")