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
if 'usage_counter' not in st.session_state: st.session_state.usage_counter = 0
if 'current_key_index' not in st.session_state: st.session_state.current_key_index = 0
if 'v_speed' not in st.session_state: st.session_state.v_speed = 1.0

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Secrets ထဲက Key ကို အလိုအလျောက် ဖတ်ယူခြင်း
    try:
        keys_from_secrets = st.secrets["GEMINI_KEYS"]
        api_keys = [k.strip() for k in keys_from_secrets.split("\n") if k.strip()]
        
        idx = st.session_state.current_key_index % len(api_keys)
        active_key = api_keys[idx]
        st.success(f"🔑 Key {idx + 1} အသင့်ဖြစ်ပါပြီ (Auto-loaded)")
        st.info(f"📊 Uses: {st.session_state.usage_counter}/10")
        genai.configure(api_key=active_key)
    except:
        st.error("Secrets ထဲမှာ Key မတွေ့ပါ။ Dashboard Settings > Secrets မှာ အရင်ထည့်ပေးပါ။")
        active_key = None

    voice_source = st.radio("အသံအရင်းအမြစ်", ["Edge-TTS (Burmese Native)", "Gemini Studio (AI Voices)"])
    if voice_source == "Edge-TTS (Burmese Native)":
        voice_option = st.selectbox("အသံရွေးပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
        voice_name = voice_option.split(" ")[0]
    else:
        voice_name = st.selectbox("Gemini Voice", ["Aoede", "Charon", "Fenrir", "Kore", "Puck"])

    model_choice = st.selectbox("AI Model", ["gemini-2.0-flash", "gemini-2.5-flash", "gemini-1.5-flash"])
    
    voice_speed = st.slider("အသံနှုန်း", 0.3, 2.0, value=st.session_state.v_speed, step=0.01)
    st.session_state.v_speed = voice_speed
    speed_param = f"{'+' if st.session_state.v_speed >= 1.0 else '-'}{int(abs(st.session_state.v_speed-1.0)*100)}%"

# --- Functions (အပြောင်းအလဲမရှိပါ) ---
async def generate_audio_edge(text, output_file, voice, speed):
    communicate = edge_tts.Communicate(text, voice, rate=speed)
    await communicate.save(output_file)

def get_mp3_duration(file_path):
    try: return MP3(file_path).info.length
    except: return 0

def clean_script(text):
    text = re.sub(r'(\[?\d{1,2}:\d{2}(:\d{2})?\]?)|(-->)|(\d{1,2}\s?မိနစ်)|(\d{1,2}\s?စက္ကန့်)', '', text)
    return re.sub(r'\s+', ' ', text).strip()

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
        st.metric("Video Duration", f"{int(video_duration)} s")

with col2:
    st.write("### 📝 Step 2: Recap ပြုလုပ်ခြင်း")
    if st.button("Recap Script စတင်ပြုလုပ်မည်", type="primary"):
        if not active_key: st.error("API Key မရှိပါ။")
        else:
            try:
                with st.spinner("AI Script ရေးသားနေပါသည်..."):
                    model = genai.GenerativeModel(model_choice)
                    video_file = genai.upload_file(path=st.session_state.video_path)
                    while video_file.state.name == "PROCESSING": time.sleep(2); video_file = genai.get_file(video_file.name)
                    
                    target_words = int((video_duration / 60) * 140)
                    prompt = f"ဒီဗီဒီယိုကို ကြည့်ပြီး မြန်မာ Movie Recap Script ရေးပေးပါ။ စာလုံးရေ {target_words} ခန့်။"
		
                    ဒီဗီဒီယိုကို ကြည့်ပြီး ပရိသတ်တွေ ရင်ခုန်စိတ်လှုပ်ရှားသွားအောင် Recap Script ရေးပေးပါ။
                    
                    လိုအပ်ချက်များ (Strict Requirements):
                    ၁။ 00:00 (Timestamps) တွေ၊ စက္ကန့်တွေ၊ မိနစ်တွေကို လုံးဝ(လုံးဝ) မထည့်ပါနဲ့။ စာသားသက်သက် Narrative Style ပဲ ရေးပါ။
                    ၂။ စကားပြောပုံစံက အရမ်း energetic ဖြစ်ပါစေ။ 'ကဲ... ဒီနေ့မှာတော့', 'တကယ့်ကို ရင်ခုန်ဖို့ကောင်းတာဗျာ', 'ဇာတ်လမ်းလေးကတော့' စတဲ့ ဆွဲဆောင်မှုရှိတဲ့ စကားလုံးတွေ သုံးပါ။
                    ၃။ စာသားကို စာပိုဒ်တဆက်တည်း လူတစ်ယောက် Recap ပြောပြနေသလို ရေးပေးပါ။
		       အဆုံးမှာ 'အပေါင်းလေးနှိပ် အသဲလေးပေးသွားနော်' ဆိုတဲ့  ပုံစံမျိုး ရေးပေးပါ။

                    ၄။ ဗီဒီယိုကြာချိန်က {int(video_duration)} စက္ကန့် ဖြစ်လို့ စာလုံးရေ {target_words} ခန့်ပဲ ရေးပေးပါ။
                    """
                    
                    response = model.generate_content([prompt, video_file])
                    st.session_state['recap_script'] = clean_script(response.text)
                    st.session_state.usage_counter += 1
                    if st.session_state.usage_counter >= 10:
                        st.session_state.current_key_index += 1
                        st.session_state.usage_counter = 0
                    st.rerun()
            except Exception as e:
                st.error(f"Script Error: {str(e)}")

# --- Final Section ---
if 'recap_script' in st.session_state:
    st.divider()
    edited_script = st.text_area("Generated Script:", st.session_state['recap_script'], height=200)
    st.session_state['recap_script'] = edited_script

    if st.button("🔊 အသံဖိုင် ထုတ်မည်"):
        with st.spinner("အသံဖန်တီးနေသည်..."):
            audio_output = "recap_audio.mp3"
            asyncio.run(generate_audio_edge(st.session_state['recap_script'], audio_output, voice_name, speed_param))
            st.session_state.actual_audio_dur = get_mp3_duration(audio_output)
            st.audio(audio_output)