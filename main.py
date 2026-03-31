import streamlit as st
import google.generativeai as genai
import asyncio
import edge_tts
import os
import tempfile
import time
from moviepy.editor import VideoFileClip

# --- Setup Configuration ---
st.set_page_config(page_title="Burmese Movie Recap Ultra AI", layout="wide")

st.title("🎬 Burmese Movie Recap AI (Ultra High Version)")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Model Settings")
    api_key = st.text_input("Gemini API Key:", type="password")
    
    # သင့် API Key တွင် အလုပ်လုပ်သော Model အမြင့်ဆုံးများကို ထည့်ပေးထားပါသည်
    model_map = {
        "💎 Gemini 2.5 Flash (Recommended)": "gemini-2.5-flash",
        "🔥 Gemini 2.5 Pro (Ultra High)": "gemini-2.5-pro",
        "⚡ Gemini 2.0 Flash": "gemini-2.0-flash",
        "🧠 Gemini 2.0 Pro Exp": "gemini-2.0-pro-exp-02-05"
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
    # Video Upload to Gemini
    video_file = genai.upload_file(path=video_path)
    
    status_text = st.empty()
    status_text.info(f"⏳ {selected_model} ဖြင့် ဗီဒီယိုကို အသေးစိတ် လေ့လာနေပါသည်...")
    
    while video_file.state.name == "PROCESSING":
        time.sleep(3)
        video_file = genai.get_file(video_file.name)
    
    # စာလုံးရေ တွက်ချက်ခြင်း (၁ မိနစ်လျှင် ၁၃၀ စာလုံးခန့်)
    # မြန်မာစကားပြောနှုန်းကို အချိန်ကြာချိန်နှင့် ကိုက်ညီအောင် ညှိယူခြင်း
    target_words = int((duration_sec / 60) * 135)

    model = genai.GenerativeModel(model_name=selected_model)
    
    # Script လွဲချော်မှုမရှိစေရန် အသေးစိတ် Prompt ပေးခြင်း
    prompt = f"""
    မင်းက ကမ္ဘာကျော် မြန်မာ Movie Recap YouTuber တစ်ယောက်ပါ။ 
    ဒီဗီဒီယိုကို အစအဆုံး အသေးစိတ် ကြည့်ရှုပြီး ဇာတ်လမ်းကို စိတ်ဝင်စားစရာ အကောင်းဆုံး Recap Script တစ်ခု ရေးပေးပါ။
    
    အရေးကြီးချက်များ:
    ၁။ ဗီဒီယိုကြာချိန်က {int(duration_sec)} စက္ကန့် ဖြစ်သောကြောင့် အသံဖတ်ချိန် {int(duration_sec)} စက္ကန့်နှင့် ကွက်တိဖြစ်စေရန် စာလုံးရေ {target_words} ခန့်သာ ရေးသားပါ။
    ၂။ ဗီဒီယိုထဲက အဖြစ်အပျက်တွေ၊ ဇာတ်ကောင်တွေရဲ့ လုပ်ဆောင်ချက်တွေကို အမှားအယွင်းမရှိဘဲ အသေးစိတ် ရှင်းပြပေးပါ။
    ၃။ အစမှာ 'ဒီနေ့မှာတော့...' လို့ စပြီး အဆုံးမှာ 'နောက်ထပ် ဗီဒီယိုတွေမှာ ပြန်တွေ့ကြမယ်' ဆိုတဲ့ YouTuber ပုံစံမျိုး ရေးပေးပါ။
    ၄။ မြန်မာစာအရေးအသားကို ကြည်လင်ပြီး ဖတ်ရလွယ်ကူအောင် ရေးပေးပါ။
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
    if st.button("Recap Script စတင်ပြုလုပ်မည် (High Quality)", type="primary"):
        if not api_key:
            st.error("API Key ကို Sidebar တွင် အရင်ထည့်ပါ။")
        elif not uploaded_file:
            st.warning("ဗီဒီယို တင်ပေးပါ။")
        else:
            try:
                with st.spinner(f"{selected_display_name} ကို အသုံးပြုနေပါသည်..."):
                    final_script = process_video_with_gemini(video_path, model_choice, video_duration)
                    st.session_state['recap_script'] = final_script
                    st.success("Script ရေးသားပြီးပါပြီ!")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# --- Result Section ---
if 'recap_script' in st.session_state:
    st.divider()
    st.write("### 📜 Generated Recap Script (Pro Version)")
    # AI ထုတ်ပေးတဲ့ script ကို ဒီမှာ ပြင်နိုင်ပါတယ်
    edited_script = st.text_area("Script ကို အချိန်ကြာချိန်နှင့် ကိုက်ညီအောင် ပြင်ဆင်ပါ:", st.session_state['recap_script'], height=300)
    
    if st.button("🔊 မြန်မာအသံဖိုင် (Audio) ဖန်တီးမည်"):
        with st.spinner("ကြည်လင်သော မြန်မာအသံဖိုင် ဖန်တီးနေပါသည်..."):
            audio_output = "recap_audio.mp3"
            asyncio.run(generate_audio(edited_script, audio_output, voice_name, speed_param))
            
            st.audio(audio_output)
            st.info(f"ဗီဒီယိုကြာချိန်: {int(video_duration)}s | အသံဖတ်နှုန်း: {voice_speed}x")
            
            with open(audio_output, "rb") as f:
                st.download_button("Download Audio (MP3)", f, file_name="high_quality_recap.mp3")

st.markdown("---")
st.caption("Powered by Gemini 2.5 & 2.0 Pro Experimental | Ultra High Fidelity Burmese TTS")