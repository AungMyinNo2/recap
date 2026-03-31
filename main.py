import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
import tempfile
import time

# --- Setup Configuration ---
st.set_page_config(page_title="Burmese Movie Recap AI", layout="wide")

st.title("🎬 Burmese Movie Recap AI (Final Fix)")

# Sidebar for Settings
with st.sidebar:
    st.header("⚙️ Settings")
    api_key = st.text_input("Gemini API Key ကိုထည့်ပါ:", type="password")
    
    # Model ရွေးချယ်မှုအပိုင်း (404 ဖြစ်ပါက Pro ကို ပြောင်းသုံးရန်)
    model_choice = st.selectbox("AI Model ရွေးချယ်ပါ", ["gemini-1.5-flash", "gemini-1.5-pro"])
    
    voice_option = st.selectbox("အသံရွေးချယ်ပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
    voice_name = voice_option.split(" ")[0]

if api_key:
    genai.configure(api_key=api_key)

# --- Functions ---

async def generate_audio(text, output_file, voice):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

def process_video_with_gemini(video_path, selected_model):
    # Video Upload
    video_file = genai.upload_file(path=video_path)
    
    status_text = st.empty()
    status_text.info(f"⏳ {selected_model} ကို အသုံးပြုပြီး ဗီဒီယိုကို စစ်ဆေးနေပါတယ်...")
    
    # Wait for processing
    while video_file.state.name == "PROCESSING":
        time.sleep(3)
        video_file = genai.get_file(video_file.name)
    
    if video_file.state.name == "FAILED":
        return "Video processing failed."

    status_text.success("✅ ဗီဒီယိုဖတ်ပြီးပါပြီ။ Script ရေးသားနေပါတယ်။")

    model = genai.GenerativeModel(model_name=selected_model)
    prompt = "မင်းက ကျွမ်းကျင်တဲ့ မြန်မာ Movie Recap YouTuber တစ်ယောက်ပါ။ ဒီဗီဒီယိုကို ကြည့်ပြီး စိတ်ဝင်စားစရာကောင်းတဲ့ Recap Script တစ်ခုကို မြန်မာလို အသေးစိတ် ရေးပေးပါ။"
    
    response = model.generate_content([prompt, video_file])
    return response.text

# --- UI Layout ---

col1, col2 = st.columns([1, 1])

with col1:
    st.write("### 📤 Step 1: Video တင်ပါ")
    uploaded_file = st.file_uploader("Video ဖိုင် (MP4, MOV)", type=["mp4", "mov", "avi"])
    if uploaded_file:
        st.video(uploaded_file)
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
            tfile.write(uploaded_file.read())
            video_path = tfile.name

with col2:
    st.write("### 📝 Step 2: Recap ပြုလုပ်ခြင်း")
    transcript_input = st.text_area("စာသား (ရှိလျှင်) ထည့်ပါ", height=150)
    
    if st.button("Recap Script စတင်ပြုလုပ်မည်", type="primary"):
        if not api_key:
            st.error("Gemini API Key ကို အရင်ထည့်ပါ။")
        else:
            try:
                with st.spinner("လုပ်ဆောင်နေပါသည်..."):
                    if transcript_input.strip():
                        model = genai.GenerativeModel(model_name=model_choice)
                        response = model.generate_content(f"Rewrite this as an exciting Burmese Movie Recap script: {transcript_input}")
                        final_script = response.text
                    elif uploaded_file:
                        final_script = process_video_with_gemini(video_path, model_choice)
                    else:
                        st.warning("Video သို့မဟုတ် စာသားထည့်ပါ။")
                        final_script = None

                    if final_script:
                        st.session_state['recap_script'] = final_script
                        st.success("အောင်မြင်သည်!")
            except Exception as e:
                st.error(f"Error: {str(e)}")
                # Debugging: ရနိုင်တဲ့ model တွေကို ပြပေးမယ်
                st.write("သင့် API Key ဖြင့် အောက်ပါ Model များကို သုံးနိုင်သည်-")
                try:
                    models = [m.name for m in genai.list_models()]
                    st.write(models)
                except:
                    pass

# --- Result Section ---
if 'recap_script' in st.session_state:
    st.divider()
    st.write("### 📜 Generated Script")
    edited_script = st.text_area("Script ပြင်ဆင်ရန်:", st.session_state['recap_script'], height=300)
    
    if st.button("🔊 အသံဖိုင် (Audio) ထုတ်မည်"):
        with st.spinner("အသံဖိုင် ဖန်တီးနေပါတယ်..."):
            audio_output = "recap_audio.mp3"
            asyncio.run(generate_audio(edited_script, audio_output, voice_name))
            st.audio(audio_output)
            with open(audio_output, "rb") as f:
                st.download_button("Download MP3", f, file_name="recap.mp3")