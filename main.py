import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
import tempfile
import time
from moviepy.editor import VideoFileClip

# --- Setup Configuration ---
st.set_page_config(page_title="Burmese Movie Recap Pro AI", layout="wide")

st.title("🎬 Burmese Movie Recap AI (Pro Version)")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Advanced Settings")
    api_key = st.text_input("Gemini API Key:", type="password")
    
    # အမြင့်ဆုံး Pro Model ကို သုံးပါမယ်
    model_choice = st.selectbox("AI Model (အမြင့်ဆုံး)", 
                                ["gemini-2.0-pro-exp-02-05", "gemini-2.0-flash"])
    
    voice_option = st.selectbox("အသံရွေးချယ်ပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
    voice_name = voice_option.split(" ")[0]
    
    # အသံ အနှေး/အမြန် ချိန်ရန် (အချိန်ညှိရန်)
    voice_speed = st.slider("အသံနှုန်း (Speed)", 0.8, 1.5, 1.0, 0.05)
    speed_param = f"{'+' if voice_speed >= 1.0 else '-'}{int(abs(voice_speed-1.0)*100)}%"

if api_key:
    genai.configure(api_key=api_key)

# --- Functions ---

async def generate_audio(text, output_file, voice, speed):
    """မြန်မာအသံဖိုင်ကို speed ချိန်ညှိပြီး ဖန်တီးခြင်း"""
    communicate = edge_tts.Communicate(text, voice, rate=speed)
    await communicate.save(output_file)

def process_video_with_gemini(video_path, selected_model, duration_sec):
    # Video Upload to Gemini
    video_file = genai.upload_file(path=video_path)
    
    status_text = st.empty()
    status_text.info(f"⏳ {selected_model} က ဗီဒီယိုကို အသေးစိတ် လေ့လာနေပါတယ်...")
    
    while video_file.state.name == "PROCESSING":
        time.sleep(3)
        video_file = genai.get_file(video_file.name)
    
    # စက္ကန့်အလိုက် စာလုံးရေ တွက်ချက်ခြင်း (မြန်မာစာအတွက် ၁ မိနစ်ကို စာလုံးရေ ၁၂၀ ခန့်က အသင့်တော်ဆုံး)
    target_words = int((duration_sec / 60) * 130)

    model = genai.GenerativeModel(model_name=selected_model)
    prompt = f"""
    မင်းက ကမ္ဘာကျော် မြန်မာ Movie Recap YouTuber တစ်ယောက်ပါ။ 
    ဒီဗီဒီယိုကို အသေးစိတ်ကြည့်ပြီး ဇာတ်လမ်းအစအဆုံးကို စိတ်ဝင်စားစရာကောင်းအောင် မြန်မာလို ပြန်ပြောပြပေးပါ။
    
    အရေးကြီးချက်:
    ၁။ ဗီဒီယိုကြာချိန်က {int(duration_sec)} စက္ကန့် ဖြစ်တဲ့အတွက် စာသားကို စာလုံးရေ {target_words} ခန့်ပဲ ရေးပေးပါ။ (အရမ်းမရှည်ပါစေနဲ့)။
    ၂။ အသံထွက်ဖတ်တဲ့အခါ ဗီဒီယိုကြာချိန်နဲ့ ကိုက်ညီအောင် ဇာတ်လမ်းကို အဓိက အချက်အလက်တွေပဲ ပါဝင်ပါစေ။
    ၃။ စကားပြောပုံက သဘာဝကျကျနဲ့ ဆွဲဆောင်မှုရှိပါစေ။
    """
    
    response = model.generate_content([prompt, video_file])
    return response.text

# --- UI Layout ---

col1, col2 = st.columns([1, 1])

with col1:
    st.write("### 📤 Step 1: Video တင်ပါ")
    uploaded_file = st.file_uploader("Video ဖိုင် တင်ပါ", type=["mp4", "mov", "avi"])
    video_duration = 0
    if uploaded_file:
        st.video(uploaded_file)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
            tfile.write(uploaded_file.read())
            video_path = tfile.name
            # ဗီဒီယို ကြာချိန် တိုင်းတာခြင်း
            clip = VideoFileClip(video_path)
            video_duration = clip.duration
            st.warning(f"ဗီဒီယိုကြာချိန်: {int(video_duration)} စက္ကန့်")

with col2:
    st.write("### 📝 Step 2: Recap ပြုလုပ်ခြင်း")
    if st.button("Recap Script စတင်ပြုလုပ်မည် (Pro)", type="primary"):
        if not api_key:
            st.error("Gemini API Key ထည့်ပါ။")
        elif not uploaded_file:
            st.warning("ဗီဒီယို အရင်တင်ပါ။")
        else:
            try:
                with st.spinner("အမြင့်ဆုံး AI စနစ်ဖြင့် တွက်ချက်နေပါသည်..."):
                    final_script = process_video_with_gemini(video_path, model_choice, video_duration)
                    st.session_state['recap_script'] = final_script
                    st.success("Script ရေးသားပြီးပါပြီ!")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# --- Result Section ---
if 'recap_script' in st.session_state:
    st.divider()
    st.write("### 📜 Generated Script (Pro)")
    # AI ရေးပေးတဲ့ script ကို ဒီမှာ ပြင်လို့ရတယ်
    edited_script = st.text_area("Script ကို အချိန်နဲ့ကိုက်အောင် ပြင်ဆင်နိုင်သည်:", st.session_state['recap_script'], height=300)
    
    if st.button("🔊 အသံဖိုင် ထုတ်မည်"):
        with st.spinner("ကြည်လင်တဲ့ မြန်မာအသံဖိုင် ဖန်တီးနေပါတယ်..."):
            audio_output = "recap_audio.mp3"
            asyncio.run(generate_audio(edited_script, audio_output, voice_name, speed_param))
            
            # Audio ပြန်ပြခြင်း
            st.audio(audio_output)
            
            # အချိန်တိုက်စစ်ခြင်း
            st.info(f"ဗီဒီယိုကြာချိန်: {int(video_duration)}s")
            with open(audio_output, "rb") as f:
                st.download_button("Download Recap MP3", f, file_name="pro_recap.mp3")

st.markdown("---")
st.caption("Pro Version with Video Duration Sync & Gemini 2.0 Pro Support")