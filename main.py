import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import os
import tempfile
from moviepy.editor import VideoFileClip

# --- Configuration ---
st.set_page_config(page_title="AI Movie Recap Myanmar", layout="wide")

# 1. API Key Setup (ပိုပြီးသေချာအောင် ပြင်ထားပါတယ်)
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ API Key မတွေ့ပါ။ Streamlit Secrets မှာ 'GEMINI_API_KEY' ကို အရင်ထည့်ပေးပါ။")
    st.stop()  # API Key မရှိရင် ဒီမှာတင် ရပ်တန့်မယ်
else:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

async def generate_audio(text, output_path):
    """ကြည်လင်ပြတ်သားတဲ့ မြန်မာအသံ ထုတ်ပေးတဲ့ function"""
    voice = "my-MM-NilarNeural"
    # အသံနှုန်းကို အနည်းငယ် နှေးပေးထားပါတယ် (ပိုကြည်အောင်)
    communicate = edge_tts.Communicate(text, voice, rate="-5%")
    await communicate.save(output_path)

def get_recap_script(video_file_path, duration_seconds):
    """Gemini AI ကို Video ကြည့်ခိုင်းခြင်း"""
    # Model name ကို အသစ်ဆုံး version ပြောင်းထားပါတယ်
    model = genai.GenerativeModel('gemini-1.5-flash-latest')
    
    video_file = genai.upload_file(path=video_file_path)
    
    prompt = f"""
    ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်ဝင်စားစရာကောင်းသော Movie Recap ကို မြန်မာဘာသာဖြင့် ရေးပေးပါ။
    သတ်မှတ်ချက်-
    ၁။ အသံထွက်ဖတ်ပါက စုစုပေါင်းကြာချိန် {duration_seconds} စက္ကန့်နှင့် အတိအကျတူညီရမည်။
    ၂။ စာသားသက်သက်သာ ပြန်ပေးပါ။
    """
    
    response = model.generate_content([prompt, video_file])
    return response.text

# --- UI Interface ---
st.title("🎬 AI Movie Recap (Burmese Voice)")

uploaded_file = st.file_uploader("Recap လုပ်မည့် Video ကို ရွေးချယ်ပါ", type=["mp4", "mov", "avi"])

if uploaded_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_video:
        tmp_video.write(uploaded_file.read())
        video_path = tmp_video.name

    clip = VideoFileClip(video_path)
    duration = int(clip.duration)
    st.write(f"🎞 ဗီဒီယိုကြာချိန် - **{duration}** စက္ကန့်")

    if st.button("Generate Recap Audio"):
        with st.spinner("AI က Recap လုပ်နေပါတယ်..."):
            try:
                # Script ယူခြင်း
                recap_text = get_recap_script(video_path, duration)
                st.info("📝 AI Script:")
                st.write(recap_text)

                # အသံဖိုင်လုပ်ခြင်း
                audio_output = "recap_burmese.mp3"
                asyncio.run(generate_audio(recap_text, audio_output))

                # ရလဒ်ပြခြင်း
                st.success(f"✅ ပြီးပါပြီ!")
                st.audio(audio_output)
                
            except Exception as e:
                st.error(f"Error ဖြစ်သွားပါတယ်: {str(e)}")
            finally:
                clip.close()
                if os.path.exists(video_path):
                    os.remove(video_path)