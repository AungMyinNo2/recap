import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
import tempfile
import time

# --- Setup Configuration ---
st.set_page_config(page_title="Burmese Movie Recap AI", layout="wide", page_icon="🎬")

# Custom CSS for better UI
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 20px; height: 3em; background-color: #FF4B4B; color: white; }
    .stTextArea textarea { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🎬 Burmese Movie Recap AI")
st.subheader("Video (သို့) Transcript မှတစ်ဆင့် မြန်မာ Movie Recap ဖန်တီးပါ")

# Sidebar for Settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Gemini API Key ကိုထည့်ပါ:", type="password")
    voice_option = st.selectbox("အသံရွေးချယ်ပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
    voice_name = voice_option.split(" ")[0]
    st.info("API Key မရှိပါက aistudio.google.com တွင် အခမဲ့ယူနိုင်ပါသည်။")

if api_key:
    genai.configure(api_key=api_key)

# --- Functions ---

async def generate_audio(text, output_file, voice):
    """မြန်မာအသံဖိုင် ဖန်တီးခြင်း"""
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def process_video_with_gemini(video_path):
    """Video ကို Gemini ဆီပို့ပြီး Script ထုတ်ခြင်း"""
    # model နာမည်ကို models/gemini-1.5-flash ဟု အပြည့်အစုံရေးခြင်း
    model = genai.GenerativeModel(model_name='models/gemini-1.5-flash')
    
    # Video Upload
    video_file = genai.upload_file(path=video_path)
    
    # Wait for processing
    progress_bar = st.progress(0)
    st.write("Gemini is analyzing the video...")
    while video_file.state.name == "PROCESSING":
        time.sleep(3)
        video_file = genai.get_file(video_file.name)
    progress_bar.progress(100)

    prompt = """
    ဒီဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားစရာကောင်းတဲ့ မြန်မာ Movie Recap Script တစ်ခု ရေးပေးပါ။ 
    စာသားတွေက YouTuber တစ်ယောက် Movie Recap ပြောနေသလို ပုံစံဖြစ်ရမယ်။ 
    အစမှာ 'ဒီနေ့မှာတော့...' လို့ စပေးပါ။ 
    အရေးကြီးတဲ့ အခန်းတွေကို အသေးစိတ် မြန်မာလို ရေးပေးပါ။
    """
    
    response = model.generate_content([prompt, video_file])
    return response.text

# --- UI Layout ---

col1, col2 = st.columns([1, 1])

with col1:
    st.write("### 📤 Step 1: Video တင်ပါ")
    uploaded_file = st.file_uploader("Video ဖိုင် (MP4, MOV, AVI) - Max 500MB", type=["mp4", "mov", "avi"])
    video_path = None
    if uploaded_file:
        st.video(uploaded_file)
        # Temp file သိမ်းခြင်း
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
            tfile.write(uploaded_file.read())
            video_path = tfile.name

with col2:
    st.write("### 📝 Step 2: Script ထုတ်ယူခြင်း")
    transcript_input = st.text_area("YouTube Transcript (ရှိလျှင်) ဒီမှာ ထည့်နိုင်သည် - မရှိပါက Video မှ Auto ထုတ်မည်", height=200)
    
    generate_btn = st.button("Recap Script စတင်ပြုလုပ်မည်")

if generate_btn:
    if not api_key:
        st.error("Gemini API Key ထည့်ပေးရန် လိုအပ်ပါသည်။")
    else:
        try:
            with st.spinner("AI မှ Script ရေးသားနေပါသည်... ခေတ္တစောင့်ပါ..."):
                # Script logic
                if transcript_input.strip():
                    model = genai.GenerativeModel('models/gemini-1.5-flash')
                    prompt = f"Rewrite this transcript into an engaging Burmese Movie Recap script: {transcript_input}"
                    response = model.generate_content(prompt)
                    final_script = response.text
                elif video_path:
                    final_script = process_video_with_gemini(video_path)
                else:
                    st.warning("Video တင်ပါ သို့မဟုတ် Transcript ထည့်ပါ။")
                    final_script = None

                if final_script:
                    st.session_state['recap_script'] = final_script
                    st.success("Script ဖန်တီးမှု အောင်မြင်သည်!")

        except Exception as e:
            st.error(f"Error: {str(e)}")

# --- Output Section ---
if 'recap_script' in st.session_state:
    st.divider()
    st.write("### 📜 Generated Movie Recap Script")
    edited_script = st.text_area("Script ကို လိုအပ်သလို ပြင်ဆင်နိုင်သည်:", st.session_state['recap_script'], height=300)
    
    if st.button("🔊 အသံဖိုင် (Audio) အဖြစ် ပြောင်းလဲမည်"):
        with st.spinner("ကြည်လင်သော မြန်မာအသံဖိုင် ဖန်တီးနေပါသည်..."):
            audio_output = "recap_audio.mp3"
            asyncio.run(generate_audio(edited_script, audio_output, voice_name))
            
            st.audio(audio_output)
            with open(audio_output, "rb") as f:
                st.download_button("Download MP3 Audio", f, file_name="burmese_recap.mp3")

st.markdown("---")
st.caption("Developed for Burmese Movie Recap Creators | Powered by Gemini 1.5 & Edge TTS")