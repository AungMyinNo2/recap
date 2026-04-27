import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions
import edge_tts
import asyncio
import os
import tempfile
import time
import random  
from moviepy.editor import VideoFileClip, AudioFileClip

# --- Configuration ---
st.set_page_config(page_title="AI Movie Recap Master", layout="wide", page_icon="🎙️")

# --- API Key Rotation Logic ---
def get_model_with_rotation():
    if "GEMINI_KEYS" not in st.secrets:
        st.error("❌ Secrets ထဲမှာ 'GEMINI_KEYS' ကို အရင်ထည့်ပေးပါ။")
        st.stop()
    
    keys = list(st.secrets["GEMINI_KEYS"]) 
    random.shuffle(keys)

    for current_key in keys:
        try:
            genai.configure(api_key=current_key.strip())
            # မော်ဒယ်ကို user သတ်မှတ်ထားသည့်အတိုင်း ထားရှိခြင်း
            model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            return model
        except Exception:
            continue
    st.error("❌ API Keys အားလုံး အလုပ်မလုပ်ပါ။")
    st.stop()

# --- Session State Initialization ---
if 'recap_script' not in st.session_state: st.session_state.recap_script = ""
if 'srt_content' not in st.session_state: st.session_state.srt_content = ""
if 'movie_review' not in st.session_state: st.session_state.movie_review = ""
if 'gemini_file_obj' not in st.session_state: st.session_state.gemini_file_obj = None
if 'current_video_name' not in st.session_state: st.session_state.current_video_name = ""

# --- Shared Upload Function (The Speed Secret) ---
def upload_video_to_gemini_once(video_path, video_name):
    """ဗီဒီယိုကို တစ်ကြိမ်သာ Upload တင်ပြီး Session ထဲတွင် သိမ်းထားရန်"""
    # ဗီဒီယိုအသစ်ဖြစ်မှသာ Upload တင်မည်
    if st.session_state.gemini_file_obj is None or st.session_state.current_video_name != video_name:
        with st.spinner("🤖 Gemini ထံသို့ ဗီဒီယို ပေးပို့နေသည် (တစ်ကြိမ်သာ)..."):
            video_file = genai.upload_file(path=video_path)
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = genai.get_file(video_file.name)
            st.session_state.gemini_file_obj = video_file
            st.session_state.current_video_name = video_name
    return st.session_state.gemini_file_obj

# --- Modified AI Functions (Accepting file object instead of path) ---

def generate_ai_content(video_obj, prompt_text):
    """Gemini ဆီက Content ယူရန် Shared Function"""
    model = get_model_with_rotation()
    try:
        response = model.generate_content([prompt_text, video_obj])
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

async def generate_audio_file(text, output_path, voice, rate="+0%", volume="+0%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(output_path)

# --- Sidebar Settings ---
st.sidebar.title("⚙️ Audio Settings")
voice_choice = st.sidebar.radio("Recap ပြောမည့်သူ:", ["သီဟ", "နီလာ "])
voice_id = "my-MM-ThihaNeural" if "သီဟ" in voice_choice else "my-MM-NilarNeural"
volume_value = st.sidebar.slider("အသံ အတိုး/အလျော့ (%)", -50, 50, 0, step=10)
volume_str = f"{volume_value:+}%"

# --- Main UI ---
st.title("🎙️ Movie Recap Master")

v_file = st.file_uploader("Video တင်ပါ...", type=["mp4", "mov", "avi"])

if v_file:
    # ဗီဒီယိုအသစ်တင်တိုင်း Session Clear လုပ်ရန်
    if st.session_state.current_video_name != v_file.name:
        st.session_state.recap_script = ""
        st.session_state.srt_content = ""
        st.session_state.movie_review = ""

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(v_file.read())
        video_path = tmp.name

    with VideoFileClip(video_path) as v_clip:
        v_dur = v_clip.duration
        st.video(v_file)
        st.write(f"🎞 ဗီဒီယိုကြာချိန် - **{v_dur:.2f}** စက္ကန့်")

        # ဗီဒီယိုကို တစ်ကြိမ်သာ Upload လုပ်ပြီး အားလုံးအတွက် သုံးမည်
        video_obj = upload_video_to_gemini_once(video_path, v_file.name)

        tab1, tab2, tab3 = st.tabs(["📝 Recap & Voice", "🎯 SRT Subtitles", "🎬 Catchy Title & Review"])
        
        # --- TAB 1 ---
        with tab1:
            if st.button("📝 Generate Recap Script"):
                prompt = """ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Movie Recap Script တစ်ခု ရေးပေးပါ။ စာသားကို စာပိုဒ်တဆက်တည်း ရေးပေးပြီး အဆုံးမှာ 'ဗီဒီယိုလေးကို ကြိုက်နှစ်သက်ရင် အပေါင်းလေးနှိပ် အသဲလေးပေးသွားနော်' လို့ ထည့်ပေးပါ။"""
                st.session_state.recap_script = generate_ai_content(video_obj, prompt)

            if st.session_state.recap_script:
                st.session_state.recap_script = st.text_area("Edit Script:", value=st.session_state.recap_script, height=300)
                if st.button("🚀 Generate Audio & Sync"):
                    with st.spinner("အသံဖိုင် ဖန်တီးနေပါတယ်..."):
                        mp3_temp = "temp_audio.mp3"
                        asyncio.run(generate_audio_file(st.session_state.recap_script, mp3_temp, voice_id))
                        with AudioFileClip(mp3_temp) as audio_clip:
                            initial_dur = audio_clip.duration
                        speed_change = round(((initial_dur / v_dur) - 1) * 100)
                        final_rate = f"{speed_change:+}%"
                        final_mp3 = "final_recap.mp3"
                        asyncio.run(generate_audio_file(st.session_state.recap_script, final_mp3, voice_id, rate=final_rate, volume=volume_str))
                        st.audio(final_mp3)
                        st.download_button("📥 Download MP3", open(final_mp3, "rb"), "recap.mp3")

        # --- TAB 2 ---
        with tab2:
            if st.button("🎯 Generate SRT File"):
                prompt = "ဤဗီဒီယိုကို ကြည့်ပြီး အချိန်ကိုက် မြန်မာဘာသာ Standard SRT format (HH:MM:SS,mmm) ဖြင့် Subtitle ဖိုင်တစ်ခု ဖန်တီးပေးပါ။"
                st.session_state.srt_content = generate_ai_content(video_obj, prompt)
            
            if st.session_state.srt_content:
                st.session_state.srt_content = st.text_area("Edit SRT:", value=st.session_state.srt_content, height=400)
                st.download_button("📥 Download SRT", st.session_state.srt_content, "sub.srt")

        # --- TAB 3 ---
        with tab3:
            if st.button("✨ Generate Title & Review"):
                prompt = "ဤဗီဒီယိုအတွက် ဆွဲဆောင်မှုရှိသော မြန်မာဘာသာ ရုပ်ရှင်အမည် (Catchy Title) နှင့် Review တစ်ခုကို 'Title: [အမည်] Review: [စာသား]' ပုံစံဖြင့် ရေးပေးပါ။"
                st.session_state.movie_review = generate_ai_content(video_obj, prompt)
            
            if st.session_state.movie_review:
                st.markdown("### 🖋️ ရလဒ်")
                st.write(st.session_state.movie_review)

    os.remove(video_path)