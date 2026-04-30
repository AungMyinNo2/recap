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
def get_all_keys():
    if "GEMINI_KEYS" not in st.secrets:
        st.error("❌ Secrets ထဲမှာ 'GEMINI_KEYS' ကို အရင်ထည့်ပေးပါ။")
        st.stop()
    keys = list(enumerate(st.secrets["GEMINI_KEYS"], start=1))
    random.shuffle(keys) # အလှည့်ကျ သုံးနိုင်အောင် ရောမွှေထားမယ်
    return keys

# --- Session States ---
if 'recap_script' not in st.session_state: st.session_state.recap_script = ""
if 'srt_content' not in st.session_state: st.session_state.srt_content = ""
if 'movie_review' not in st.session_state: st.session_state.movie_review = ""
if 'video_local_path' not in st.session_state: st.session_state.video_local_path = None

# --- Sidebar Settings ---
st.sidebar.title("⚙️ Audio Settings")
keys_list = st.secrets.get("GEMINI_KEYS", [])
st.sidebar.info(f"🔑 **API System:** Auto Rotation Mode")
st.sidebar.caption(f"စုစုပေါင်း API Key {len(keys_list)} ခုကို Limit စစ်ပြီး သုံးပေးနေပါသည်။")
st.sidebar.divider()

voice_choice = st.sidebar.radio("Recap ပြောမည့်သူ:", ["သီဟ", "နီလာ "])
voice_id = "my-MM-ThihaNeural" if "သီဟ" in voice_choice else "my-MM-NilarNeural"
volume_value = st.sidebar.slider("အသံ အတိုး/အလျော့ (%)", -50, 50, 0, step=10)
volume_str = f"{volume_value:+}%"

# --- Core logic to handle 429 Quota Error ---
def run_gemini_task(video_path, prompt):
    """Key တစ်ခု Limit ပြည့်ရင် နောက်တစ်ခုကို အလိုအလျောက် ပြောင်းသုံးပေးမည့် Function"""
    indexed_keys = get_all_keys()
    
    for key_no, current_key in indexed_keys:
        try:
            genai.configure(api_key=current_key.strip())
            # Note: User request မို့ model name မပြောင်းပါ (gemini-2.5-flash)
            model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            
            with st.status(f"🤖 Key-{key_no} ဖြင့် ကြိုးစားနေသည်...", expanded=False) as status:
                video_file = genai.upload_file(path=video_path)
                while video_file.state.name == "PROCESSING":
                    time.sleep(2)
                    video_file = genai.get_file(video_file.name)
                
                response = model.generate_content([prompt, video_file])
                genai.delete_file(video_file.name) # clean up
                status.update(label=f"✅ Key-{key_no} အောင်မြင်သည်!", state="complete")
                return response.text
                
        except exceptions.ResourceExhausted:
            st.warning(f"⚠️ Key-{key_no} က Quota (Limit) ပြည့်သွားပါပြီ။ နောက်တစ်ခုကို ပြောင်းသုံးနေပါတယ်။")
            continue # နောက် Key တစ်ခုကို ဆက်သွားမယ်
        except Exception as e:
            st.error(f"❌ Key-{key_no} မှာ Error တက်သည်- {str(e)}")
            continue
            
    st.error("🚫 API Keys အားလုံး Limit ပြည့်နေပါတယ်။ ခဏစောင့်ပြီးမှ ပြန်ကြိုးစားပါ။")
    return None

# --- Main UI ---
st.title("🎙️ Movie Recap Master")
v_file = st.file_uploader("Video တင်ပါ...", type=["mp4", "mov", "avi"])

if v_file:
    if st.session_state.video_local_path is None or v_file.name != st.session_state.get('last_v_name'):
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(v_file.read())
            st.session_state.video_local_path = tmp.name
            st.session_state.last_v_name = v_file.name

    v_clip = VideoFileClip(st.session_state.video_local_path)
    v_dur = v_clip.duration  
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.video(v_file)
        st.write(f"🎞 ဗီဒီယိုကြာချိန် - **{v_dur:.2f}** စက္ကန့်")

    tab1, tab2, tab3 = st.tabs(["📝 Recap & Voice", "🎯 SRT Subtitles", "🎬 Catchy Title & Review"])

    with tab1:
        if st.button("📝 Generate Recap Script"):
            prompt = "ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ် မြန်မာ Movie Recap Script တစ်ခု ရေးပေးပါ။ Timestamp မထည့်ပါနဲ့။"
            res = run_gemini_task(st.session_state.video_local_path, prompt)
            if res: st.session_state.recap_script = res

        if st.session_state.recap_script:
            st.session_state.recap_script = st.text_area("Edit Script:", value=st.session_state.recap_script, height=250)
            if st.button("🚀 Generate Audio & Sync"):
                async def make_audio():
                    mp3_temp = "temp.mp3"
                    comm = edge_tts.Communicate(st.session_state.recap_script, voice_id)
                    await comm.save(mp3_temp)
                    aud = AudioFileClip(mp3_temp)
                    speed = f"{round(((aud.duration / v_dur) - 1) * 100):+}%"
                    aud.close()
                    final_mp3 = "final_recap.mp3"
                    comm = edge_tts.Communicate(st.session_state.recap_script, voice_id, rate=speed, volume=volume_str)
                    await comm.save(final_mp3)
                    return final_mp3
                
                f_mp3 = asyncio.run(make_audio())
                st.audio(f_mp3)
                st.download_button("📥 Download MP3", open(f_mp3, "rb"), "recap.mp3")

    with tab2:
        if st.button("🎯 Generate SRT File"):
            prompt = "ဤဗီဒီယိုကို ကြည့်ပြီး အချိန်ကိုက် မြန်မာ SRT Subtitle ဖန်တီးပေးပါ။ Standard format သာ သုံးပါ။"
            res = run_gemini_task(st.session_state.video_local_path, prompt)
            if res: st.session_state.srt_content = res.replace("```srt", "").replace("```", "").strip()

        if st.session_state.srt_content:
            st.session_state.srt_content = st.text_area("Edit SRT:", value=st.session_state.srt_content, height=300)
            st.download_button("📥 Download SRT", st.session_state.srt_content, "subtitles.srt")

    with tab3:
        if st.button("✨ Generate Title & Review"):
            prompt = "ဤဗီဒီယိုအတွက် ဆွဲဆောင်မှုရှိသော မြန်မာ Title နှင့် Review ကို ရေးပေးပါ။"
            res = run_gemini_task(st.session_state.video_local_path, prompt)
            if res: st.session_state.movie_review = res
        
        if st.session_state.movie_review:
            st.info(st.session_state.movie_review)

    v_clip.close()