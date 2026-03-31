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

st.title("🎬 Burmese Movie Recap AI (Time-Sync Mode)")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Model & Voice Settings")
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
    
    # Speed Control Slider
    voice_speed = st.slider("အသံနှုန်း (Speed Control)", 0.5, 2.0, 1.0, 0.05)
    speed_param = f"{'+' if voice_speed >= 1.0 else '-'}{int(abs(voice_speed-1.0)*100)}%"

if api_key:
    genai.configure(api_key=api_key)

# --- Functions ---

async def generate_audio(text, output_file, voice, speed):
    communicate = edge_tts.Communicate(text, voice, rate=speed)
    await communicate.save(output_file)

def estimate_duration(text, speed):
    """မြန်မာစာလုံးရေပေါ်မူတည်ပြီး အသံကြာချိန်ကို ခန့်မှန်းတွက်ချက်ခြင်း"""
    # မြန်မာစာအတွက် ပျမ်းမျှ ၁ စက္ကန့်လျှင် စာလုံးရေ (characters) ၅.၅ လုံးခန့် ဖတ်သည်ဟု ယူဆသည်
    if not text: return 0
    base_duration = len(text) / 5.5
    return base_duration / speed

def process_video_with_gemini(video_path, selected_model, duration_sec):
    video_file = genai.upload_file(path=video_path)
    status_text = st.empty()
    status_text.info(f"⏳ {selected_model} က ဗီဒီယိုကို လေ့လာနေသည်...")
    
    while video_file.state.name == "PROCESSING":
        time.sleep(3)
        video_file = genai.get_file(video_file.name)
    
    # ၁ မိနစ်လျှင် ၁၃၅ စာလုံးနှုန်းဖြင့် ဗီဒီယိုကြာချိန်နှင့် ကိုက်အောင် ချိန်ညှိခြင်း
    target_words = int((duration_sec / 60) * 135)

    model = genai.GenerativeModel(model_name=selected_model)
    prompt = f"""
    မင်းက Movie Recap YouTuber တစ်ယောက်ပါ။ ဒီဗီဒီယိုကို ကြည့်ပြီး ဇာတ်လမ်းကို မြန်မာလို အသေးစိတ် ရေးပေးပါ။
    အရေးကြီးချက်: ဗီဒီယိုကြာချိန်က {int(duration_sec)} စက္ကန့် ဖြစ်လို့ စာလုံးရေ {target_words} ခန့်ပဲ ရေးပေးပါ။
    """
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
        st.metric("Video Duration", f"{int(video_duration)} s")

with col2:
    st.write("### 📝 Step 2: Recap ပြုလုပ်ခြင်း")
    if st.button("Recap Script စတင်ပြုလုပ်မည်", type="primary"):
        if not api_key: st.error("API Key ထည့်ပါ။")
        elif not uploaded_file: st.warning("Video တင်ပါ။")
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
    col_a, col_b = st.columns([2, 1])
    
    with col_a:
        st.write("### 📜 Generated Script")
        edited_script = st.text_area("Script ပြင်ဆင်ရန်:", st.session_state['recap_script'], height=300)
        # စာသားပြောင်းလဲမှုကို session state တွင် သိမ်းဆည်းရန်
        st.session_state['recap_script'] = edited_script

    with col_b:
        st.write("### ⏱️ Time Sync Check")
        # အသံကြာချိန်ကို Speed slider အပေါ်မူတည်ပြီး Real-time တွက်ချက်ခြင်း
        est_audio_dur = estimate_duration(st.session_state['recap_script'], voice_speed)
        
        diff = est_audio_dur - video_duration
        
        st.metric("Estimated Audio Duration", f"{int(est_audio_dur)} s", delta=f"{int(diff)} s vs Video", delta_color="inverse")
        
        if abs(diff) > 10:
            st.warning("⚠️ အသံကြာချိန်နှင့် ဗီဒီယိုကြာချိန် ကွာဟနေပါသည်။ Speed ကို ချိန်ညှိပါ သို့မဟုတ် စာသား လျှော့ပါ/တိုးပါ။")
        else:
            st.success("✅ အချိန်ကိုက်ရန် အဆင်ပြေနိုင်ပါသည်။")

        if st.button("🔊 အသံဖိုင် ထုတ်မည်"):
            with st.spinner("MP3 ဖန်တီးနေပါသည်..."):
                audio_output = "recap_audio.mp3"
                asyncio.run(generate_audio(st.session_state['recap_script'], audio_output, voice_name, speed_param))
                st.audio(audio_output)
                with open(audio_output, "rb") as f:
                    st.download_button("Download MP3", f, file_name="synced_recap.mp3")

st.markdown("---")
st.caption("Auto Time-Sync Feature Enabled | Burmese Recap Engine")