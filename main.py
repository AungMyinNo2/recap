import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import os
from moviepy.editor import VideoFileClip
import tempfile

# 1. API Key Setup (Streamlit Secrets ကနေယူမှာဖြစ်ပါတယ်)
try:
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("Gemini API Key ကို Secrets မှာ မသတ်မှတ်ရသေးပါ။")

async def generate_burmese_voice(text, output_filename):
    """ကြည်လင်တဲ့ မြန်မာအသံ (Nilar - Female) ထုတ်ပေးခြင်း"""
    voice = "my-MM-NilarNeural" 
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_filename)

def analyze_video_with_gemini(video_path, duration):
    """Gemini ကို အချိန်ကိုက် Script ရေးခိုင်းခြင်း"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    video_file = genai.upload_file(path=video_path)
    
    # မြန်မာဘာသာစကားအတွက် အထူးညွှန်ကြားချက်
    prompt = f"""
    ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်ဝင်စားစရာကောင်းသော Movie Recap တစ်ခုကို မြန်မာဘာသာဖြင့် ရေးပေးပါ။ 
    ဇာတ်လမ်းပြောပြတဲ့ပုံစံက ဆွဲဆောင်မှုရှိပါစေ။ 
    အရေးကြီးဆုံးအချက်မှာ အသံထွက်ဖတ်ပါက စက္ကန့် {duration} အတွင်း အပြီးဖတ်နိုင်မည့် စာလုံးအရေအတွက်ကိုသာ ချုံ့ရေးပေးပါ။
    သရော်စာပုံစံ (သို့) စိတ်လှုပ်ရှားစရာပုံစံ ရေးပေးပါ။ စာသားသက်သက်ပဲပေးပါ။
    """
    
    response = model.generate_content([prompt, video_file])
    return response.text

# --- UI Setup ---
st.set_page_config(page_title="AI Movie Recap", page_icon="🎬")
st.title("🎬 Burmese Movie Recap AI")

uploaded_file = st.file_uploader("Video ဖိုင် တင်ပေးပါ...", type=["mp4", "mov", "avi"])

if uploaded_file is not None:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tfile:
        tfile.write(uploaded_file.read())
        video_path = tfile.name

    clip = VideoFileClip(video_path)
    duration = int(clip.duration)
    st.info(f"ဗီဒီယိုကြာချိန်: {duration} စက္ကန့်")

    if st.button("Generate Movie Recap"):
        with st.spinner("AI က Recap Script နဲ့ အသံဖိုင် ဖန်တီးနေပါတယ်။ ခဏစောင့်ပါ..."):
            try:
                # Script ရေးခြင်း
                recap_script = analyze_video_with_gemini(video_path, duration)
                st.subheader("📝 Generated Script:")
                st.write(recap_script)

                # အသံဖိုင်လုပ်ခြင်း
                audio_output = "recap_audio.mp3"
                asyncio.run(generate_burmese_voice(recap_script, audio_output))

                # ရလဒ်ပြခြင်း
                st.success("ပြီးပါပြီ!")
                st.audio(audio_output)
                
                with open(audio_output, "rb") as file:
                    st.download_button("Download Audio", data=file, file_name="recap.mp3")

            except Exception as e:
                st.error(f"Error: {str(e)}")
            finally:
                clip.close()
                if os.path.exists(video_path):
                    os.remove(video_path)