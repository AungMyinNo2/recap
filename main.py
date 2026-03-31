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
    await communicate.save(output_path)

def get_recap_script(input_data, duration, input_type="video"):
    """Gemini AI ကို Script ရေးခိုင်းခြင်း"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    သင်သည် ကျွမ်းကျင်သော Movie Recap တင်ဆက်သူဖြစ်သည်။
    ပေးထားသော {input_type} ကို အခြေခံ၍ စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Recap Script ကို ရေးပေးပါ။
    
    စည်းကမ်းချက်-
    ၁။ အသံထွက်ဖတ်ပါက စုစုပေါင်းကြာချိန် {duration} စက္ကန့် အတိအကျ ဖြစ်ရမည်။
    ၂။ စာသားသက်သက်သာ ပြန်ပေးပါ။
    """
    
    if input_type == "video":
        video_file = genai.upload_file(path=input_data)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
        response = model.generate_content([prompt, video_file])
        genai.delete_file(video_file.name)
    else:
        response = model.generate_content(prompt + f"\nInput Data: {input_data}")
        
    return response.text

# --- UI Interface ---
st.title("🎬 AI Movie Recap (Sync Video & Audio)")
st.write("Video (သို့မဟုတ်) Transcript ထည့်ပေးပါ၊ AI က ကြာချိန်နဲ့အကိုက် မြန်မာအသံဖိုင် ထုတ်ပေးပါမယ်။")

tab1, tab2 = st.tabs(["🎥 Video Upload", "📜 YouTube Transcript"])

def run_process(data, dur, dtype):
    with st.spinner("AI က Recap Script နဲ့ အသံဖိုင် ဖန်တီးနေပါတယ်..."):
        try:
            # 1. Script ယူခြင်း
            script_text = get_recap_script(data, dur, dtype)
            st.subheader("📝 Generated Script:")
            st.write(script_text)

            # 2. ပထမအကြိမ် အသံထုတ်ခြင်း
            mp3_out = "recap.mp3"
            asyncio.run(generate_audio(script_text, mp3_out))

            # 3. ကြာချိန် ချိန်ညှိခြင်း (MoviePy ကို သုံး၍ စစ်ဆေးခြင်း)
            audio_clip = AudioFileClip(mp3_out)
            actual_dur = audio_clip.duration
            
            if abs(dur - actual_dur) > 1:
                speed_change = int((actual_dur / dur - 1) * 100)
                speed_change = max(min(speed_change, 50), -50)
                final_rate = f"{speed_change:+}%"
                audio_clip.close() # ဖိုင်ကို ပိတ်ပြီးမှ အသစ်ပြန်ထုတ်မည်
                asyncio.run(generate_audio(script_text, mp3_out, rate=final_rate))
                audio_clip = AudioFileClip(mp3_out)
            
            # 4. WAV သို့ ပြောင်းလဲခြင်း
            wav_out = "recap.wav"
            audio_clip.write_audiofile(wav_out, codec='pcm_s16le')
            audio_clip.close()

            # 5. Result ပြခြင်း
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

with tab1:
    v_file = st.file_uploader("Video ရွေးချယ်ပါ", type=["mp4", "mov", "avi"])
    if v_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(v_file.read())
            video_path = tmp.name
        v_clip = VideoFileClip(video_path)
        v_dur = int(v_clip.duration)
        st.video(v_file)
        st.info(f"🎞 ဗီဒီယိုကြာချိန် - **{v_dur}** စက္ကန့်")
        if st.button("Generate from Video"):
            run_process(video_path, v_dur, "video")
        v_clip.close()

with tab2:
    t_input = st.text_area("YouTube Transcript ကို ဒီမှာ Paste လုပ်ပါ...")
    t_dur = st.number_input("Target Duration (seconds)", min_value=10, value=60)
    if st.button("Generate from Transcript"):
        if t_input:
            run_process(t_input, t_dur, "transcript")