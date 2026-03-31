import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import os
import tempfile
import time
from moviepy.editor import VideoFileClip, AudioFileClip

# --- Configuration ---
st.set_page_config(page_title="AI Movie Recap Pro", layout="wide", page_icon="🎬")

# Sidebar: Settings & Model Selection
st.sidebar.title("⚙️ AI Settings")

# API Key Handling
if "GEMINI_API_KEY" not in st.secrets:
    api_key = st.sidebar.text_input("Gemini API Key ကိုရိုက်ထည့်ပါ:", type="password")
else:
    api_key = st.secrets["GEMINI_API_KEY"]

# Gemini Model ရွေးချယ်မှု (Gemini 2.5 ကိုပါ ထည့်ပေးထားပါတယ်)
model_choice = st.sidebar.selectbox(
    "အသုံးပြုမည့် Model ကိုရွေးပါ:",
    [
        "gemini-1.5-flash", 
        "gemini-1.5-pro", 
        "gemini-2.0-flash-exp", 
        "gemini-2.5-flash", # Future model placeholder
        "gemini-2.5-pro"    # Future model placeholder
    ],
    index=0
)

st.sidebar.info("""
💡 **Model အကြံပြုချက်:**
- **1.5 Flash:** အမြန်ဆုံးနှင့် အငြိမ်ဆုံး။
- **1.5 Pro:** ပိုမိုနက်နဲသော Script ရေးလိုလျှင်။
- **2.0 Flash:** လက်ရှိ အသစ်ဆုံး (Experimental)။
- **2.5:** Google က ထုတ်ပေးမှသာ အလုပ်လုပ်ပါမည်။
""")

if not api_key:
    st.warning("⚠️ API Key မရှိဘဲ ဆက်သွားလို့မရပါ။ Sidebar မှာ API Key ထည့်ပေးပါ။")
    st.stop()
else:
    genai.configure(api_key=api_key)

async def generate_audio(text, output_path, rate="+0%"):
    """ကြည်လင်တဲ့ မြန်မာအသံ ထုတ်ပေးခြင်း"""
    voice = "my-MM-NilarNeural"
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)

def get_recap_script(video_path, duration, model_name):
    """Gemini AI ကို Script ရေးခိုင်းခြင်း"""
    model = genai.GenerativeModel(model_name=model_name)
    
    # ၁။ Video Upload
    video_file = genai.upload_file(path=video_path)
    st.info(f"🤖 {model_name} က Video ကို ဖတ်နေပါတယ်...")

    # ၂။ Video Processing ပြီးအောင် စောင့်ခြင်း
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    
    if video_file.state.name == "FAILED":
        raise Exception("Video processing failed on Gemini server.")

    # ၃။ Script Prompt
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
st.title("🎬 AI Movie Recap Master")
st.subheader(f"လက်ရှိ Model: `{model_choice}`")

v_file = st.file_uploader("Recap လုပ်မည့် Video တင်ပါ (Max 500MB)...", type=["mp4", "mov", "avi"])

if v_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(v_file.read())
        video_path = tmp.name

    v_clip = VideoFileClip(video_path)
    v_dur = int(v_clip.duration)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.video(v_file)
    with col2:
        st.write(f"🎞 ဗီဒီယိုကြာချိန် - **{v_dur}** စက္ကန့်")

    if st.button("🚀 Start AI Movie Recap"):
        with st.spinner(f"AI ({model_choice}) က Recap လုပ်နေပါတယ်..."):
            try:
                # ၁။ Script ရယူခြင်း
                script_text = get_recap_script(video_path, v_dur, model_choice)
                st.subheader("📝 Recap Script (Myanmar):")
                st.success(script_text)

                # ၂။ MP3 ထုတ်ခြင်း
                mp3_out = "recap.mp3"
                asyncio.run(generate_audio(script_text, mp3_out))

                # ၃။ Sync Logic (အသံကြာချိန် ချိန်ညှိခြင်း)
                audio_clip = AudioFileClip(mp3_out)
                actual_dur = audio_clip.duration
                
                if abs(v_dur - actual_dur) > 1:
                    speed_change = int((actual_dur / v_dur - 1) * 100)
                    speed_change = max(min(speed_change, 50), -50)
                    final_rate = f"{speed_change:+}%"
                    
                    audio_clip.close()
                    asyncio.run(generate_audio(script_text, mp3_out, rate=final_rate))
                    audio_clip = AudioFileClip(mp3_out)

                # ၄။ WAV သို့ ပြောင်းလဲခြင်း
                wav_out = "recap.wav"
                audio_clip.write_audiofile(wav_out, codec='pcm_s16le', verbose=False, logger=None)
                audio_clip.close()

                # ၅။ ရလဒ်ပြခြင်း
                st.success(f"✅ အောင်မြင်စွာ ဖန်တီးပြီးပါပြီ!")
                st.audio(mp3_out)
                
                with open(wav_out, "rb") as f:
                    st.download_button("Download WAV", f, "movie_recap.wav")

            except Exception as e:
                if "404" in str(e):
                    st.error(f"Error 404: `{model_choice}` ကို ရှာမတွေ့ပါ။ ဤ Model ကို Google က သင့် API အတွက် မဖွင့်ပေးသေးပါ သို့မဟုတ် မထုတ်သေးပါ။ ကျေးဇူးပြု၍ Gemini 1.5 Flash သို့မဟုတ် 2.0 Flash ကို ရွေးပေးပါ။")
                else:
                    st.error(f"Error: {str(e)}")
            finally:
                v_clip.close()
                if os.path.exists(video_path):
                    os.remove(video_path)