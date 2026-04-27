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

# --- API Key Rotation Logic (Randomized) ---
def get_model_with_rotation():
    """Secrets ထဲက GEMINI_KEYS ကို Random (ကျပန်း) ရွေးချယ်ပေးမည့် Function"""
    if "GEMINI_KEYS" not in st.secrets:
        st.error("❌ Secrets ထဲမှာ 'GEMINI_KEYS' (List ပုံစံ) ကို အရင်ထည့်ပေးပါ။")
        st.stop()
    
    keys = list(st.secrets["GEMINI_KEYS"]) 
    random.shuffle(keys)

    for i, current_key in enumerate(keys):
        current_key = current_key.strip()
        try:
            genai.configure(api_key=current_key)
            model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            st.session_state.active_key_display = current_key[:10] + "..." 
            return model, current_key
        except Exception:
            continue
            
    st.error("❌ API Keys အားလုံး အလုပ်မလုပ်ပါ။ (Invalid API Key Error ဖြစ်နိုင်ပါသည်)")
    st.stop()

if 'recap_script' not in st.session_state:
    st.session_state.recap_script = ""
if 'srt_content' not in st.session_state:
    st.session_state.srt_content = ""
if 'movie_review' not in st.session_state:
    st.session_state.movie_review = ""

# --- Sidebar Settings ---
st.sidebar.title("⚙️ Audio Settings")

keys_list = st.secrets.get("GEMINI_KEYS", [])
total_keys = len(keys_list)

st.sidebar.info(f"🔑 **API System:** ကျပန်း Mode")
st.sidebar.caption(f"စုစုပေါင်း API Key {total_keys} ခုကို Random စနစ်ဖြင့် လှည့်သုံးနေပါသည်။")

st.sidebar.divider()

# သီဟ ကို အပေါ်တင်ပြီး နီလာကို အောက်ချပေးထားပါသည်
voice_choice = st.sidebar.radio("Recap ပြောမည့်သူ:", ["သီဟ", "နီလာ "])
voice_id = "my-MM-ThihaNeural" if "သီဟ" in voice_choice else "my-MM-NilarNeural"

# အသံအတိုးအကျယ် (%)
volume_value = st.sidebar.slider("အသံ အတိုး/အလျော့ (%)", -50, 50, 0, step=10)
volume_str = f"{volume_value:+}%"

# --- Functions ---

async def generate_audio_file(text, output_path, voice, rate="+0%", volume="+0%"):
    """Edge-TTS ဖြင့် အသံဖိုင် ထုတ်ပေးခြင်း"""
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(output_path)

def get_recap_script(video_path):
    """Gemini 2.5 Flash ဖြင့် Script ထုတ်ယူခြင်း"""
    model, active_key = get_model_with_rotation()
    try:
        video_file = genai.upload_file(path=video_path)
        st.info(f"🤖 Gemini 2.5 Flash က Video ကို ဖတ်နေပါတယ်...")

        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
        
        prompt = """
        ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Movie Recap Script တစ်ခု ရေးပေးပါ။
        စည်းကမ်းချက်-
        ၁။ Timestamps တွေ၊ စက္ကန့်တွေ၊ မိနစ်တွေကို လုံးဝ မထည့်ပါနဲ့။ Narrative Style ပဲ ရေးပါ။
        ၂။ စာသားကို စာပိုဒ်တဆက်တည်း ရေးပေးပါ။
        ၃။ အဆုံးမှာ 'ဗီဒီယိုလေးကို ကြိုက်နှစ်သက်ရင် အပေါင်းလေးနှိပ် အသဲလေးပေးသွားနော်' လို့ ထည့်ပေးပါ။
        ၄။ မြန်မာစာလုံးရေ လိုအပ်သလောက်စာလုံးရေ များများရေးနဲ့ ဇာတ်လမ်းကို ပရိသတ်စွဲမက်အောင် အကျယ်တဝင့် ရေးပေးပါ။
        ၅။ စာသားသက်သက်ပဲ ပြန်ပေးပါ။
        """
        response = model.generate_content([prompt, video_file])
        genai.delete_file(video_file.name)
        return response.text
        
    except (exceptions.InvalidArgument, exceptions.Unauthenticated, exceptions.ResourceExhausted):
        st.warning("⚠️ Key အခက်အခဲရှိသဖြင့် အခြား Key တစ်ခုဖြင့် ထပ်မံကြိုးစားနေပါသည်။")
        return get_recap_script(video_path)
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.stop()

def get_movie_review_info(video_path):
    """ဗီဒီယိုအတွက် ဆွဲဆောင်မှုရှိသော အမည်နှင့် Review ရေးသားပေးခြင်း"""
    model, active_key = get_model_with_rotation()
    try:
        video_file = genai.upload_file(path=video_path)
        st.info(f"🤖 Gemini 2.5 Flash က နာမည်နှင့် Review ကို စဉ်းစားနေပါတယ်...")

        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
        
        prompt = """
        ဤဗီဒီယိုကို ကြည့်ပြီး ပရိသတ်စိတ်ဝင်စားသွားအောင် ဆွဲဆောင်မှုရှိသော မြန်မာဘာသာ ရုပ်ရှင်အမည် (Catchy Title) တစ်ခု နှင့် လူကြည့်များစေမည့် စိတ်လှုပ်ရှားဖွယ်ရာ Review တစ်ခုကို ရေးသားပေးပါ။ 
        Title: [အမည်]
        Review: [စာသား] ပုံစံအတိုင်း ပြန်ပေးပါ။
        """
        response = model.generate_content([prompt, video_file])
        genai.delete_file(video_file.name)
        return response.text
    except Exception as e:
        return f"Error: {str(e)}"

def get_srt_subtitles(video_path):
    """Gemini 2.5 Flash ဖြင့် မြန်မာဘာသာ SRT Subtitle ဖိုင် ထုတ်ယူခြင်း"""
    model, active_key = get_model_with_rotation()
    try:
        video_file = genai.upload_file(path=video_path)
        st.info(f"🤖 Gemini 2.5 Flash က SRT စာတန်းထိုး ဖန်တီးနေပါတယ်...")

        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
        
        prompt = """
        ဤဗီဒီယိုကို ကြည့်ပြီး အချိန်ကိုက် မြန်မာဘာသာ SRT Subtitle ဖိုင်တစ်ခု ဖန်တီးပေးပါ။
        စည်းကမ်းချက်-
        ၁။ Standard SRT format အတိုင်း နံပါတ်စဉ်၊ အချိန် (00:00:00,000 --> 00:00:00,000) နှင့် စာသားပုံစံအတိုင်း ရေးပေးပါ။
        ၂။ စာသားများကို မြန်မာဘာသာဖြင့်သာ သဘာဝကျကျ ဘာသာပြန် ရေးသားပါ။
        ၃။ ပြန်စာတွင် SRT data ကလွဲပြီး အခြား ဘာမှမထည့်ပါနှင့်။
        """
        response = model.generate_content([prompt, video_file])
        genai.delete_file(video_file.name)
        clean_srt = response.text.replace("```srt", "").replace("```", "").strip()
        return clean_srt
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.stop()

# --- Main UI ---
st.title("🎙️ Movie Recap Master")

v_file = st.file_uploader("Video တင်ပါ...", type=["mp4", "mov", "avi"])

if v_file:
    if v_file.size > 200 * 1024 * 1024:
        st.error("❌ ဖိုင်ဆိုဒ်က 200MB ထက် ကြီးနေပါသည်။")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(v_file.read())
            video_path = tmp.name

        v_clip = VideoFileClip(video_path)
        v_dur = v_clip.duration  
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.video(v_file)
            st.write(f"🎞 ဗီဒီယိုကြာချိန် - **{v_dur:.2f}** စက္ကန့်")
        
        tab1, tab2, tab3 = st.tabs(["📝 Recap & Voice", "🎯 SRT Subtitles", "🎬 Catchy Title & Review"])
        
        # --- TAB 1: Movie Recap ---
        with tab1:
            if st.button("📝 Generate Recap Script"):
                with st.spinner("Script ရေးနေပါတယ်..."):
                    st.session_state.recap_script = get_recap_script(video_path)

            if st.session_state.recap_script:
                st.session_state.recap_script = st.text_area("Edit Script:", value=st.session_state.recap_script, height=300)
                if st.button("🚀 Generate Audio & Sync"):
                    with st.spinner("အသံနှုန်း ညှိနေပါတယ်..."):
                        try:
                            mp3_temp = "temp_audio.mp3"
                            asyncio.run(generate_audio_file(st.session_state.recap_script, mp3_temp, voice_id))
                            audio_clip = AudioFileClip(mp3_temp)
                            initial_dur = audio_clip.duration
                            audio_clip.close()
                            speed_change = round(((initial_dur / v_dur) - 1) * 100)
                            final_rate = f"{speed_change:+}%"
                            final_mp3 = "final_recap.mp3"
                            asyncio.run(generate_audio_file(st.session_state.recap_script, final_mp3, voice_id, rate=final_rate, volume=volume_str))
                            st.audio(final_mp3)
                            f_name = st.text_input("Filename:", value="movie_recap", key="mp3_n")
                            with open(final_mp3, "rb") as f:
                                st.download_button("📥 Download MP3", f, f"{f_name}.mp3", "audio/mpeg")
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

        # --- TAB 2: SRT Subtitles ---
        with tab2:
            if st.button("🎯 Generate SRT File"):
                with st.spinner("ဖန်တီးနေပါတယ်..."):
                    st.session_state.srt_content = get_srt_subtitles(video_path)
            if st.session_state.srt_content:
                st.session_state.srt_content = st.text_area("Edit SRT:", value=st.session_state.srt_content, height=400)
                srt_n = st.text_input("Filename:", value="subtitles", key="srt_n")
                st.download_button("📥 Download SRT", st.session_state.srt_content, f"{srt_n}.srt", "text/plain")

        # --- TAB 3: Catchy Title & Review (New) ---
        with tab3:
            st.subheader("🌟 Video Title & Compelling Review")
            if st.button("✨ Generate Title & Review"):
                with st.spinner("နာမည်လှလှလေးနှင့် Review ရေးနေပါတယ်..."):
                    st.session_state.movie_review = get_movie_review_info(video_path)
            
            if st.session_state.movie_review:
                st.markdown("### 🖋️ ရလဒ်")
                st.write(st.session_state.movie_review)
                st.info("အပေါ်က စာသားများကို ကူးယူပြီး Social Media များတွင် အသုံးပြုနိုင်ပါသည်။")

        v_clip.close()