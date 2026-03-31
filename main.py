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
if 'last_sync_speed' not in st.session_state: st.session_state.last_sync_speed = 1.0

# --- Sidebar Settings ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Secrets ထဲမှ GEMINI_KEYS ကို အလိုအလျောက် ဖတ်ယူခြင်း
    try:
        keys_from_secrets = st.secrets["GEMINI_KEYS"]
        api_keys = [k.strip() for k in keys_from_secrets.split("\n") if k.strip()]
        
        idx = st.session_state.current_key_index % len(api_keys)
        active_key = api_keys[idx]
        st.success(f"🔑 Key {idx + 1} ကို သုံးနေပါသည် (Auto-loaded)")
        st.info(f"📊 Key {len(api_keys)} ခု အသင့်ရှိနေပါသည်")
        genai.configure(api_key=active_key)
    except:
        st.error("Secrets ထဲမှာ GEMINI_KEYS မတွေ့ပါ။ Dashboard > Settings > Secrets မှာ အရင်ထည့်ပေးပါ။")
        api_keys = []
        active_key = None

    voice_source = st.radio("အသံအရင်းအမြစ်", ["Edge-TTS (Burmese Native)", "Gemini Studio (AI Voices)"])
    if voice_source == "Edge-TTS (Burmese Native)":
        voice_option = st.selectbox("အသံရွေးပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
        voice_name = voice_option.split(" ")[0]
    else:
        voice_name = st.selectbox("Gemini Voice", ["Aoede", "Charon", "Fenrir", "Kore", "Puck"])

    # Model Version များကို အရင်ကုဒ်အတိုင်း ပြန်ထားပေးထားပါသည်
    model_mapping = {
        "gemini-2.0-flash": "gemini-2.0-flash",
        "gemini-2.5-flash (Thinking)": "gemini-2.0-flash-thinking-exp-01-21",
        "gemini-1.5-flash": "gemini-1.5-flash"
    }
    model_ui_choice = st.selectbox("AI Model (Recap အတွက်)", list(model_mapping.keys()))
    model_choice = model_mapping[model_ui_choice]
    
    voice_speed = st.slider("အသံနှုန်း (Speed Control)", 0.3, 2.0, value=st.session_state.v_speed, step=0.01)
    st.session_state.v_speed = voice_speed
    speed_param = f"{'+' if st.session_state.v_speed >= 1.0 else '-'}{int(abs(st.session_state.v_speed-1.0)*100)}%"

# --- Functions ---
async def generate_audio_edge(text, output_file, voice, speed):
    communicate = edge_tts.Communicate(text, voice, rate=speed)
    await communicate.save(output_file)

def get_mp3_duration(file_path):
    try: return MP3(file_path).info.length
    except: return 0

def clean_script(text):
    # Timestamps နှင့် Thinking tags များ ရှင်းထုတ်ခြင်း
    text = re.sub(r'(\[?\d{1,2}:\d{2}(:\d{2})?\]?)|(-->)|(\d{1,2}\s?မိနစ်)|(\d{1,2}\s?စက္ကန့်)', '', text)
    text = re.sub(r'<[^>]+>', '', text)
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
        if not active_key:
            st.error("API Key မရှိသေးပါ။")
        else:
            try:
                with st.spinner(f"{model_ui_choice} ဖြင့် Script ရေးသားနေပါသည်..."):
                    model = genai.GenerativeModel(model_choice)
                    video_file = genai.upload_file(path=st.session_state.video_path)
                    while video_file.state.name == "PROCESSING": 
                        time.sleep(2)
                        video_file = genai.get_file(video_file.name)
                    
                    target_words = int((video_duration / 60) * 140)
                    
                    # --- Prompt အပိုင်း ---
                    prompt = f"""
                    ဒီဗီဒီယိုကို ကြည့်ပြီး ပရိသတ်တွေ ရင်ခုန်စိတ်လှုပ်ရှားသွားအောင် Recap Script ရေးပေးပါ။
                    ၁။ Timestamps တွေ လုံးဝ မထည့်ပါနဲ့။ Narrative Style ပဲ ရေးပါ။
                    ၂။ စကားပြောပုံစံက အရမ်း energetic ဖြစ်ပါစေ။ 'ကဲ... ဒီနေ့မှာတော့', 'တကယ့်ကို ရင်ခုန်ဖို့ကောင်းတာဗျာ' စတဲ့ စကားလုံးတွေ သုံးပါ။
                    ၃။ အဆုံးမှာ 'ဗီဒီယိုလေးကို ကြိုက်နှစ်သက်ရင် အပေါင်းလေးနှိပ် အသဲလေးပေးသွားနော်' လို့ ထည့်ပေးပါ။
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

# --- Result & Sync Section ---
if 'recap_script' in st.session_state:
    st.divider()
    edited_script = st.text_area("Generated Script:", st.session_state['recap_script'], height=200)
    st.session_state['recap_script'] = edited_script

    col_btn1, col_btn2 = st.columns(2)
    with col_btn1:
        if st.button("🔊 အသံဖိုင် (Audio) ထုတ်မည်"):
            with st.spinner("အသံဖန်တီးနေသည်..."):
                try:
                    audio_output = "recap_audio.mp3"
                    asyncio.run(generate_audio_edge(st.session_state['recap_script'], audio_output, voice_name, speed_param))
                    st.session_state.actual_audio_dur = get_mp3_duration(audio_output)
                    st.session_state.last_sync_speed = st.session_state.v_speed
                except Exception as e:
                    st.error(f"Audio Error: {str(e)}")

    if 'actual_audio_dur' in st.session_state:
        with col_btn2:
            if st.button("⚡ Auto Sync Speed"):
                if video_duration > 0:
                    current_audio_dur = st.session_state.actual_audio_dur
                    current_speed = st.session_state.get('last_sync_speed', 1.0)
                    new_speed = (current_audio_dur * current_speed) / video_duration
                    st.session_state.v_speed = max(0.3, min(2.0, round(new_speed, 2)))
                    st.success(f"Speed ကို {st.session_state.v_speed} သို့ ညှိလိုက်ပါပြီ။ '🔊 အသံဖိုင် ထုတ်မည်' ကို ထပ်နှိပ်ပါ။")
                    time.sleep(1)
                    st.rerun()

    if 'actual_audio_dur' in st.session_state:
        st.audio("recap_audio.mp3")
        m1, m2, m3 = st.columns(3)
        m1.metric("Video Duration", f"{int(video_duration)} s")
        m2.metric("MP3 Duration", f"{int(st.session_state.actual_audio_dur)} s")
        diff = st.session_state.actual_audio_dur - video_duration
        m3.metric("Difference", f"{int(diff)} s", delta=f"{int(diff)} s", delta_color="inverse")
        
        with open("recap_audio.mp3", "rb") as f:
            st.download_button("Download MP3", f, file_name="recap.mp3")