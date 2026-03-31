import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
from moviepy.editor import VideoFileClip
import tempfile

# --- Setup Configuration ---
st.set_page_config(page_title="Burmese Movie Recap AI", layout="centered")
st.title("🎬 Burmese Movie Recap Generator")
st.subheader("YouTube Transcript (သို့) Video မှတစ်ဆင့် Recap ဖန်တီးပါ")

# API Key input
api_key = st.sidebar.text_input("Enter Gemini API Key:", type="password")
if api_key:
    genai.configure(api_key=api_key)

# --- Functions ---

async def generate_audio(text, output_file):
    """မြန်မာအသံ ထွက်ပေါ်လာစေရန် edge-tts ကိုအသုံးပြုခြင်း"""
    # မြန်မာအသံအတွက် my-MM-ThihaNeural (Male) သို့မဟုတ် my-MM-NilarNeural (Female)
    VOICE = "my-MM-ThihaNeural" 
    communicate = edge_tts.Communicate(text, VOICE)
    await communicate.save(output_file)

def get_gemini_recap(transcript):
    """Gemini AI သုံးပြီး Recap Script ရေးသားခြင်း"""
    model = genai.GenerativeModel('gemini-1.5-pro')
    prompt = f"""
    You are a professional Burmese Movie Recap YouTuber. 
    Rewrite the following movie transcript into an engaging, exciting, and storytelling movie recap in Burmese (Myanmar) language.
    Guidelines:
    - Use a casual and energetic tone (Recap Style).
    - Use words like 'ဒီနေ့မှာတော့...', 'ဇာတ်လမ်းလေးကတော့...', 'နောက်ဆုံးမှာတော့...'.
    - Ensure the story flow is smooth and easy to understand for Burmese audience.
    - Don't just translate, rewrite it to be interesting.
    
    Transcript:
    {transcript}
    """
    response = model.generate_content(prompt)
    return response.text

# --- UI Components ---

# 1. Video Upload
uploaded_file = st.file_uploader("Video ဖိုင်တင်ပါ (Max 500MB)", type=["mp4", "mov", "avi"])
video_duration = 0

if uploaded_file:
    tfile = tempfile.NamedTemporaryFile(delete=False)
    tfile.write(uploaded_file.read())
    clip = VideoFileClip(tfile.name)
    video_duration = clip.duration
    st.info(f"ဗီဒီယိုကြာချိန်: {int(video_duration // 60)} မိနစ် {int(video_duration % 60)} စက္ကန့်")

# 2. Transcript Input
transcript_input = st.text_area("YouTube Transcript ကို ဒီမှာ Paste လုပ်ပါ:", height=200)

if st.button("Generate Recap Script & Audio"):
    if not api_key:
        st.error("ကျေးဇူးပြု၍ Gemini API Key ထည့်ပေးပါ။")
    elif not transcript_input:
        st.error("Transcript ထည့်ပေးရန် လိုအပ်ပါသည်။")
    else:
        with st.spinner("AI မှ Script ရေးသားနေသည်... ခေတ္တစောင့်ပါ..."):
            try:
                # Step 1: Generate Burmese Script
                recap_script = get_gemini_recap(transcript_input)
                st.success("Script ရေးသားပြီးပါပြီ!")
                st.text_area("Generated Burmese Script:", recap_script, height=250)
                
                # Step 2: Generate Audio
                audio_file = "recap_audio.mp3"
                with st.spinner("အသံဖိုင် ဖန်တီးနေသည်..."):
                    asyncio.run(generate_audio(recap_script, audio_file))
                
                # Step 3: Display Audio Player
                st.audio(audio_file, format='audio/mp3')
                
                # Download button
                with open(audio_file, "rb") as f:
                    st.download_button("Download Recap Audio (MP3)", f, file_name="recap_burmese.mp3")
                
                # Note about duration
                if video_duration > 0:
                    st.warning(f"မှတ်ချက်: AI အသံဖိုင်၏ ကြာချိန်သည် မူရင်း Video ကြာချိန် ({int(video_duration)}s) နှင့် အနည်းငယ် ကွာခြားနိုင်ပါသည်။")

            except Exception as e:
                st.error(f"Error: {str(e)}")

# UI Styling
st.markdown("""
<style>
    .stButton>button {
        width: 100%;
        background-color: #FF4B4B;
        color: white;
        border-radius: 10px;
    }
</style>
""", unsafe_allow_html=True)