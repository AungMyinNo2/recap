# --- Python 3.13+ Compatibility Fix ---
try:
    import audioop
except ImportError:
    import audioop_lpmud as audioop
    import sys
    sys.modules['audioop'] = audioop
# --------------------------------------

import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import os
import tempfile
import time
from moviepy.editor import VideoFileClip, AudioFileClip
from pydub import AudioSegment

# --- Configuration ---
st.set_page_config(page_title="AI Movie Recap Sync", layout="wide", page_icon="🎙️")

# API Key Handling
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Secrets ထဲမှာ 'GEMINI_API_KEY' ကို အရင်ထည့်ပေးပါ။")
    st.stop()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- Sidebar Settings ---
st.sidebar.title("⚙️ Audio Settings")

# ၁။ အသံရွေးချယ်ခြင်း
voice_choice = st.sidebar.radio(
    "Recap ပြောမည့်သူကို ရွေးပါ:",
    ["နီလာ (အမျိုးသမီးသံ)", "သီဟ (အမျိုးသားသံ)"],
    index=0
)
voice_id = "my-MM-NilarNeural" if "နီလာ" in voice_choice else "my-MM-ThihaNeural"

# ၂။ အသံအတိုးအကျယ် (Volume)
volume_adj = st.sidebar.slider("အသံ အတိုး/အလျော့ (dB):", -10, 10, 0)

st.sidebar.info("💡 **Sync System:** Video ကြာချိန်နဲ့ ကိုက်အောင် AI က အသံနှုန်း (Rate) ကို အလိုအလျောက် ညှိပေးပါမည်။")

# --- Functions ---

async def generate_audio_file(text, output_path, voice, rate="+0%"):
    """Edge-TTS ဖြင့် အသံဖိုင် ထုတ်ပေးခြင်း"""
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)

def get_recap_script(video_path, duration):
    """Gemini 2.5 Flash ကို Script ရေးခိုင်းခြင်း"""
    # User အသုံးပြုလိုသော Model နာမည်
    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    
    video_file = genai.upload_file(path=video_path)
    st.info(f"🤖 Gemini 2.5 Flash က Video ကို ဖတ်နေပါတယ်...")

    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    
    prompt = f"""
    ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Movie Recap Script တစ်ခု ရေးပေးပါ။
    စည်းကမ်းချက်-
    ၁။ အသံထွက်ဖတ်ပါက စုစုပေါင်းကြာချိန် {duration} စက္ကန့် အတိအကျ ဖြစ်ရမည်။
    ၂။ ဇာတ်လမ်းပြောပြပုံမှာ ပရိသတ်ကို ဆွဲဆောင်နိုင်ရမည်။
    ၃။ စာသားသက်သက်သာ ပြန်ပေးပါ။
    """
    
    response = model.generate_content([prompt, video_file])
    genai.delete_file(video_file.name)
    return response.text

# --- Main UI ---
st.title("🎙️ AI Movie Recap (Auto Sync)")

v_file = st.file_uploader("Recap လုပ်မည့် Video တင်ပါ...", type=["mp4", "mov", "avi"])

if v_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(v_file.read())
        video_path = tmp.name

    v_clip = VideoFileClip(video_path)
    v_dur = int(v_clip.duration)
    st.video(v_file)
    st.write(f"🎞 ဗီဒီယိုကြာချိန် - **{v_dur}** စက္ကန့်")

    if st.button("🚀 Start Recap & Auto Sync"):
        with st.spinner("AI က အလုပ်လုပ်နေပါတယ်..."):
            try:
                # ၁။ Script ရယူခြင်း
                script_text = get_recap_script(video_path, v_dur)
                st.subheader("📝 Recap Script (Myanmar):")
                st.success(script_text)

                # ၂။ အခြေခံအသံဖိုင်ကို အရင်ထုတ်ခြင်း (ကြာချိန်တိုင်းရန်)
                mp3_temp = "temp.mp3"
                asyncio.run(generate_audio_file(script_text, mp3_temp, voice_id))
                
                audio_clip = AudioFileClip(mp3_temp)
                initial_dur = audio_clip.duration
                audio_clip.close()

                # ၃။ Auto Sync Logic (ကြာချိန်ကိုက်အောင် နှုန်းညှိခြင်း)
                # Formula: (Initial/Target - 1) * 100
                speed_change = int((initial_dur / v_dur - 1) * 100)
                speed_change = max(min(speed_change, 50), -50) # အရမ်းမြန်/နှေးမသွားအောင် limit လုပ်ခြင်း
                final_rate = f"{speed_change:+}%"
                
                final_mp3 = "final_recap.mp3"
                asyncio.run(generate_audio_file(script_text, final_mp3, voice_id, rate=final_rate))

                # ၄။ Volume အတိုးအကျော့လုပ်ခြင်း (Pydub သုံး၍)
                sound = AudioSegment.from_mp3(final_mp3)
                final_sound = sound.apply_gain(volume_adj)
                final_sound.export(final_mp3, format="mp3")

                # ၅။ ရလဒ်ပြသခြင်း
                st.success(f"✅ Syncing Complete! (နှုန်းညှိချက်: {final_rate})")
                st.write(f"အသုံးပြုထားသော အသံ: **{voice_choice}**")
                
                st.audio(final_mp3)
                
                with open(final_mp3, "rb") as f:
                    st.download_button("Download Recap MP3", f, "movie_recap.mp3")

            except Exception as e:
                st.error(f"Error: {str(e)}")
            finally:
                v_clip.close()
                if os.path.exists(video_path):
                    os.remove(video_path)