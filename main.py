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
    keys_with_indices = list(enumerate(st.secrets["GEMINI_KEYS"], start=1))
    random.shuffle(keys_with_indices)
    return keys_with_indices

# --- Session States ---
if 'recap_script' not in st.session_state: st.session_state.recap_script = ""
if 'srt_content' not in st.session_state: st.session_state.srt_content = ""
if 'movie_review' not in st.session_state: st.session_state.movie_review = ""
if 'gemini_video_file' not in st.session_state: st.session_state.gemini_video_file = None
if 'last_uploaded_file_name' not in st.session_state: st.session_state.last_uploaded_file_name = ""

# --- Sidebar Settings ---
st.sidebar.title("⚙️ Audio Settings")
keys_list = st.secrets.get("GEMINI_KEYS", [])
st.sidebar.info(f"🔑 **API System:** ကျပန်း Mode")
st.sidebar.caption(f"စုစုပေါင်း API Key {len(keys_list)} ခုကို လှည့်သုံးနေပါသည်။")
st.sidebar.divider()

voice_choice = st.sidebar.radio("Recap ပြောမည့်သူ:", ["သီဟ", "နီလာ "])
voice_id = "my-MM-ThihaNeural" if "သီဟ" in voice_choice else "my-MM-NilarNeural"
volume_value = st.sidebar.slider("အသံ အတိုး/အလျော့ (%)", -50, 50, 0, step=10)
volume_str = f"{volume_value:+}%"

# --- Functions ---

async def generate_audio_file(text, output_path, voice, rate="+0%", volume="+0%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(output_path)

def upload_to_gemini(video_path):
    """Video ကို Gemini ပေါ်သို့ တစ်ကြိမ်သာ တင်ပြီး အဆင်သင့်ဖြစ်အောင် စောင့်ပေးမည့် Function"""
    indexed_keys = get_model_with_rotation()
    for key_no, current_key in indexed_keys:
        try:
            genai.configure(api_key=current_key.strip())
            # Note: Model version gemini-2.5-flash (as requested to not change)
            video_file = genai.upload_file(path=video_path)
            
            with st.status(f"🤖 Ai က ဗီဒီယိုကို စတင်ဖတ်နေပါတယ်... (Key - {key_no})", expanded=True) as status:
                while video_file.state.name == "PROCESSING":
                    time.sleep(2)
                    video_file = genai.get_file(video_file.name)
                status.update(label="✅ ဗီဒီယိုဖတ်ပြီးပါပြီ။", state="complete")
            return video_file, current_key # အောင်မြင်ရင် ပြန်ပေးမယ်
        except Exception as e:
            continue
    return None, None

def get_ai_response(video_file, api_key, prompt):
    """Upload လုပ်ပြီးသား Video ကိုသုံးပြီး AI Response ယူရန်"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name="gemini-2.5-flash")
        response = model.generate_content([prompt, video_file])
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

# --- Main UI ---
st.title("🎙️ Movie Recap Master")
v_file = st.file_uploader("Video တင်ပါ...", type=["mp4", "mov", "avi"])

if v_file:
    # ဖိုင်အသစ်တင်တိုင်း Gemini ဆီ တစ်ခါပဲ ပို့မယ်
    if st.session_state.last_uploaded_file_name != v_file.name:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(v_file.read())
            video_path = tmp.name
        
        gemini_file, used_key = upload_to_gemini(video_path)
        if gemini_file:
            st.session_state.gemini_video_file = gemini_file
            st.session_state.current_api_key = used_key
            st.session_state.last_uploaded_file_name = v_file.name
            st.session_state.video_local_path = video_path # local path သိမ်းထားမယ် Duration အတွက်
        else:
            st.error("❌ Video Upload လုပ်ရာတွင် အမှားအယွင်းရှိနေပါသည်။")
            st.stop()

    # Video Preview and Information
    v_clip = VideoFileClip(st.session_state.video_local_path)
    v_dur = v_clip.duration  
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.video(v_file)
        st.write(f"🎞 ဗီဒီယိုကြာချိန် - **{v_dur:.2f}** စက္ကန့်")

    tab1, tab2, tab3 = st.tabs(["📝 Recap & Voice", "🎯 SRT Subtitles", "🎬 Catchy Title & Review"])

    with tab1:
        if st.button("📝 Generate Recap Script"):
            with st.spinner("Script ရေးနေပါတယ်..."):
                prompt = """
                ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Movie Recap Script တစ်ခု ရေးပေးပါ။
                စည်းကမ်းချက်- ၁။ Timestamps လုံးဝ မထည့်ပါနဲ့။ ၂။ စာသားကို စာပိုဒ်တဆက်တည်း ရေးပါ။ ၃။ အဆုံးမှာ 'ဗီဒီယိုလေးကို ကြိုက်နှစ်သက်ရင် အပေါင်းလေးနှိပ် အသဲလေးပေးသွားနော်' လို့ ထည့်ပါ။ ၄။ ဇာတ်လမ်းကို စိတ်ဝင်စားစရာ အကျယ်တဝင့် ရေးပါ။
                """
                st.session_state.recap_script = get_ai_response(st.session_state.gemini_video_file, st.session_state.current_api_key, prompt)

        if st.session_state.recap_script:
            st.session_state.recap_script = st.text_area("Edit Script:", value=st.session_state.recap_script, height=250)
            if st.button("🚀 Generate Audio & Sync"):
                with st.spinner("အသံဖန်တီးနေပါတယ်..."):
                    try:
                        mp3_temp = "temp_audio.mp3"
                        asyncio.run(generate_audio_file(st.session_state.recap_script, mp3_temp, voice_id))
                        audio_clip = AudioFileClip(mp3_temp)
                        initial_dur = audio_clip.duration
                        audio_clip.close()
                        speed_change = round(((initial_dur / v_dur) - 1) * 100)
                        final_mp3 = "final_recap.mp3"
                        asyncio.run(generate_audio_file(st.session_state.recap_script, final_mp3, voice_id, rate=f"{speed_change:+}%", volume=volume_str))
                        st.audio(final_mp3)
                        st.download_button("📥 Download MP3", open(final_mp3, "rb"), "recap.mp3", "audio/mpeg")
                    except Exception as e: st.error(f"Error: {str(e)}")

    with tab2:
        if st.button("🎯 Generate SRT File"):
            with st.spinner("SRT ဖန်တီးနေပါတယ်..."):
                prompt = """
                ဤဗီဒီယိုကို ကြည့်ပြီး အချိန်ကိုက် မြန်မာဘာသာ SRT Subtitle ဖိုင်တစ်ခု ဖန်တီးပေးပါ။ 
                Format: HH:MM:SS,mmm --> HH:MM:SS,mmm ပုံစံအတိအကျဖြစ်ရမည်။ SRT data သက်သက်သာ ပြန်ပေးပါ။
                """
                res = get_ai_response(st.session_state.gemini_video_file, st.session_state.current_api_key, prompt)
                st.session_state.srt_content = res.replace("```srt", "").replace("```", "").strip()

        if st.session_state.srt_content:
            st.session_state.srt_content = st.text_area("Edit SRT:", value=st.session_state.srt_content, height=300)
            st.download_button("📥 Download SRT", st.session_state.srt_content, "subtitles.srt", "text/plain")

    with tab3:
        if st.button("✨ Generate Title & Review"):
            with st.spinner("စဉ်းစားနေပါတယ်..."):
                prompt = "ဤဗီဒီယိုအတွက် ဆွဲဆောင်မှုရှိသော မြန်မာ Title နှင့် Review ကို 'Title: [အမည်]' 'Review: [စာသား]' ပုံစံဖြင့် ရေးပေးပါ။"
                st.session_state.movie_review = get_ai_response(st.session_state.gemini_video_file, st.session_state.current_api_key, prompt)
        
        if st.session_state.movie_review:
            st.info(st.session_state.movie_review)

    v_clip.close()