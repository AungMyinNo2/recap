import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
import tempfile
import time

# --- Setup Configuration ---
st.set_page_config(page_title="Burmese Movie Recap AI", layout="wide")
st.title("🎬 Burmese Movie Recap AI (Auto Video Analysis)")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Gemini API Key ကိုထည့်ပါ:", type="password")
    voice_option = st.selectbox("အသံရွေးချယ်ပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
    voice_name = voice_option.split(" ")[0]

if api_key:
    genai.configure(api_key=api_key)

# --- Functions ---

async def generate_audio(text, output_file, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def process_video_with_gemini(video_path):
    """Video ဖိုင်ကို Gemini ဆီပို့ပြီး Recap ထုတ်ခိုင်းခြင်း"""
    model = genai.GenerativeModel('gemini-1.5-flash') # မြန်ဆန်ဖို့ flash ကိုသုံးထားပါတယ်
    
    # Video ဖိုင်ကို Gemini Cloud ပေါ်တင်ခြင်း
    video_file = genai.upload_file(path=video_path)
    
    # Video ကို Processing လုပ်ပြီးတဲ့အထိ ခေတ္တစောင့်ခြင်း
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)

    prompt = """
    ဒီဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားစရာကောင်းတဲ့ မြန်မာ Movie Recap Script တစ်ခု ရေးပေးပါ။ 
    စကားပြောပုံက YouTuber တစ်ယောက် ပြောနေသလို ဖြစ်ရမယ်။ 
    အစမှာ 'ဒီနေ့မှာတော့...' လို့ စပေးပါ။ 
    ဇာတ်လမ်းအစအဆုံးကို မြန်မာလိုပဲ အသေးစိတ် ရေးပေးပါ။
    """
    
    response = model.generate_content([prompt, video_file])
    return response.text

# --- UI Layout ---

col1, col2 = st.columns([1, 1])

with col1:
    uploaded_file = st.file_uploader("Video ဖိုင်တင်ပါ (MP4, MOV)", type=["mp4", "mov", "avi"])
    if uploaded_file:
        st.video(uploaded_file)
        # Temporary file အနေနဲ့ သိမ်းပါ
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
            tfile.write(uploaded_file.read())
            video_path = tfile.name

with col2:
    st.write("### YouTube Transcript (သို့) Auto Generate")
    transcript_input = st.text_area("စာသားကို ဒီမှာ တိုက်ရိုက်ထည့်နိုင်သည် (သို့) Video မှ Auto ထုတ်မည်", height=200)
    
    if st.button("Recap ပြုလုပ်မယ်", type="primary"):
        if not api_key:
            st.error("API Key ထည့်ပေးပါဦး။")
        else:
            with st.spinner("Gemini က Video ကို ကြည့်ပြီး Script ရေးနေပါတယ်..."):
                try:
                    # အကယ်၍ Transcript မရှိရင် Video ကနေ Auto ထုတ်မယ်
                    if not transcript_input and uploaded_file:
                        final_script = process_video_with_gemini(video_path)
                    else:
                        # Transcript ရှိရင် အဲဒါကိုပဲ သုံးမယ်
                        model = genai.GenerativeModel('gemini-1.5-flash')
                        final_script = model.generate_content(f"Rewrite this as a Burmese Movie Recap: {transcript_input}").text
                    
                    st.session_state['recap_result'] = final_script
                    st.success("Script ထွက်လာပါပြီ!")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

# ရလဒ်ပြသခြင်းနှင့် အသံထုတ်ခြင်း
if 'recap_result' in st.session_state:
    st.divider()
    st.write("### 📜 Generated Recap Script")
    edited_script = st.text_area("Script ကို ပြင်ဆင်နိုင်သည်:", st.session_state['recap_result'], height=300)
    
    if st.button("အသံဖိုင်အဖြစ် ပြောင်းလဲမည်"):
        with st.spinner("ကြည်လင်တဲ့ မြန်မာအသံဖိုင် ဖန်တီးနေပါတယ်..."):
            audio_path = "recap_audio.mp3"
            asyncio.run(generate_audio(edited_script, audio_path, voice_name))
            st.audio(audio_path)
            with open(audio_path, "rb") as f:
                st.download_button("Download MP3", f, file_name="movie_recap.mp3")