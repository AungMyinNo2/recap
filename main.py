import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import os
import tempfile
import time
from moviepy.editor import VideoFileClip
from pydub import AudioSegment

# --- API Setup ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Secrets ထဲမှာ 'GEMINI_API_KEY' မတွေ့ပါ။")
    st.stop()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

async def generate_audio(text, output_path, rate="+0%"):
    voice = "my-MM-NilarNeural"
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_path)

def get_recap_script(input_data, duration, input_type="video"):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    သင်သည် ကျွမ်းကျင်သော Movie Recap တင်ဆက်သူဖြစ်သည်။
    ပေးထားသော {input_type} ကို အခြေခံ၍ စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Recap Script ကို ရေးပေးပါ။
    စည်းကမ်းချက်-
    ၁။ အသံထွက်ဖတ်ပါက စုစုပေါင်းကြာချိန် {duration} စက္ကန့် အတိအကျ ဖြစ်ရမည်။
    ၂။ စာလုံးရေကို {duration} စက္ကန့်နှင့် ကိုက်ညီအောင် ညှိရေးပေးပါ။
    ၃။ စာသားသက်သက်သာ ပြန်ပေးပါ။
    """
    
    if input_type == "video":
        video_file = genai.upload_file(path=input_data)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
        response = model.generate_content([prompt, video_file])
        genai.delete_file(video_file.name)
    else:
        response = model.generate_content(prompt + f"\nInput Content: {input_data}")
        
    return response.text

# --- UI ---
st.title("🎬 AI Movie Recap (Sync Video & Audio)")

tab1, tab2 = st.tabs(["🎥 Video Upload", "📜 YouTube Transcript"])

with tab1:
    v_file = st.file_uploader("Video (Max 500MB)", type=["mp4", "mov", "avi"])
    if v_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(v_file.read())
            video_path = tmp.name
        clip = VideoFileClip(video_path)
        duration = int(clip.duration)
        st.info(f"Video Duration: {duration}s")
        if st.button("Generate from Video"):
            process_recap(video_path, duration, "video")

with tab2:
    t_input = st.text_area("Paste YouTube Transcript here...")
    t_duration = st.number_input("Target Duration (seconds)", min_value=10, value=60)
    if st.button("Generate from Transcript"):
        process_recap(t_input, t_duration, "transcript")

def process_recap(data, dur, dtype):
    with st.spinner("AI Processing..."):
        try:
            # 1. Get Script
            script = get_recap_script(data, dur, dtype)
            st.subheader("📝 Script:")
            st.write(script)
            
            # 2. Initial Audio
            mp3_out = "output.mp3"
            asyncio.run(generate_audio(script, mp3_out))
            
            # 3. Sync Check
            audio = AudioSegment.from_mp3(mp3_out)
            actual_dur = len(audio) / 1000
            
            # Duration မကိုက်ရင် Rate ပြန်ညှိခြင်း
            if abs(dur - actual_dur) > 2:
                rate_val = int((actual_dur / dur - 1) * 100)
                asyncio.run(generate_audio(script, mp3_out, rate=f"{rate_val:+}%"))
            
            # 4. Final Conversion
            wav_out = "output.wav"
            audio = AudioSegment.from_mp3(mp3_out)
            audio.export(wav_out, format="wav")
            
            st.success("✅ Syncing Complete!")
            st.audio(mp3_out)
            st.download_button("Download WAV", open(wav_out, "rb"), "recap.wav")
            
        except Exception as e:
            st.error(f"Error: {e}")