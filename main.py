import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import os
import tempfile
import time
from moviepy.editor import VideoFileClip, AudioFileClip

# --- Configuration ---
st.set_page_config(page_title="AI Movie Recap Myanmar", layout="wide")

# API Key Setup
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Secrets ထဲမှာ 'GEMINI_API_KEY' ကို အရင်ထည့်ပေးပါ။")
    st.stop()
else:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

async def generate_audio(text, output_path, rate="+0%"):
    """ကြည်လင်တဲ့ မြန်မာအသံ ထုတ်ပေးခြင်း"""
    voice = "my-MM-NilarNeural"
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await asyncio.wait_for(communicate.save(output_path), timeout=60)

def get_recap_script(video_path, duration):
    """Gemini AI ကို Script ရေးခိုင်းခြင်း"""
    # Model အမည်ကို version အသစ်ဆုံး သုံးထားပါသည်
    model = genai.GenerativeModel(model_name="gemini-1.5-flash")
    
    # ၁။ Video Upload
    video_file = genai.upload_file(path=video_path)
    st.info("AI က Video ကို လေ့လာနေပါတယ်။ ခဏစောင့်ပေးပါ...")

    # ၂။ Video Processing ပြီးအောင် စောင့်ခြင်း (Processing state မပြီးခင် ခေါ်မိပါက 404 တက်တတ်ပါသည်)
    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    
    if video_file.state.name == "FAILED":
        raise Exception("Video processing failed on Gemini server.")

    # ၃။ Prompt ပေးခြင်း
    prompt = f"""
    ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Movie Recap Script တစ်ခု ရေးပေးပါ။
    စည်းကမ်းချက်-
    ၁။ အသံထွက်ဖတ်ပါက စုစုပေါင်းကြာချိန် {duration} စက္ကန့် အတိအကျ ဖြစ်ရမည်။
    ၂။ စကားလုံး အထားအသိုကို ဆွဲဆောင်မှုရှိပါစေ။
    ၃။ စာသားသက်သက်သာ ပြန်ပေးပါ။
    """
    
    response = model.generate_content([prompt, video_file])
    
    # Server ပေါ်က file ကို ချက်ချင်းဖျက်ပါ
    genai.delete_file(video_file.name)
    
    return response.text

# --- UI Interface ---
st.title("🎬 AI Movie Recap (Burmese Sync)")
st.write("Video တင်ပေးပါ၊ AI က ကြာချိန်နဲ့အကိုက် မြန်မာအသံဖိုင် ထုတ်ပေးပါမယ်။")

v_file = st.file_uploader("Video ရွေးချယ်ပါ", type=["mp4", "mov", "avi"])

if v_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(v_file.read())
        video_path = tmp.name

    # Video ကြာချိန်တိုင်းခြင်း
    v_clip = VideoFileClip(video_path)
    v_dur = int(v_clip.duration)
    st.video(v_file)
    st.info(f"🎞 ဗီဒီယိုကြာချိန် - **{v_dur}** စက္ကန့်")

    if st.button("Generate Recap Audio"):
        with st.spinner("AI က Recap Script နဲ့ အသံဖိုင် ဖန်တီးနေပါတယ်..."):
            try:
                # ၁။ Script ရယူခြင်း
                script_text = get_recap_script(video_path, v_dur)
                st.subheader("📝 Generated Script:")
                st.write(script_text)

                # ၂။ အသံထုတ်ခြင်း
                mp3_out = "recap.mp3"
                asyncio.run(generate_audio(script_text, mp3_out))

                # ၃။ ကြာချိန် ချိန်ညှိခြင်း (Sync Logic)
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

                # ၅။ ရလဒ်ပြသခြင်း
                st.success(f"✅ အောင်မြင်စွာ ဖန်တီးပြီးပါပြီ!")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("MP3 Format")
                    st.audio(mp3_out)
                with col2:
                    st.write("WAV Format")
                    st.audio(wav_out)
                    with open(wav_out, "rb") as f:
                        st.download_button("Download WAV", f, "recap.wav")

            except Exception as e:
                st.error(f"Error: {str(e)}")
            finally:
                v_clip.close()
                if os.path.exists(video_path):
                    os.remove(video_path)