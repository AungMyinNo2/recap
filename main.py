import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import os
import tempfile
import time
from moviepy.editor import VideoFileClip
from pydub import AudioSegment

# --- API Configuration ---
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Secrets ထဲမှာ 'GEMINI_API_KEY' ထည့်ပေးပါ။")
    st.stop()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# --- Functions ---

async def generate_burmese_audio(text, output_mp3, rate):
    """Burmese Voice Generation with Speed Control"""
    # rate parameter: e.g., "+10%", "-5%"
    voice = "my-MM-NilarNeural"
    communicate = edge_tts.Communicate(text, voice, rate=rate)
    await communicate.save(output_mp3)

def mp3_to_wav(mp3_path, wav_path):
    """Convert MP3 to WAV using pydub"""
    audio = AudioSegment.from_mp3(mp3_path)
    audio.export(wav_path, format="wav")

def get_recap_script(input_data, duration, input_type="transcript"):
    """Gemini AI ကို အချိန်ကိုက် Script ရေးခိုင်းခြင်း"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # မြန်မာလို တစ်မိနစ်ကို စာလုံးရေ ၁၂၀ ခန့် (Syllables/Words) က ပုံမှန်နှုန်းဖြစ်သည်
    # ထို့ကြောင့် duration အလိုက် စာလုံးရေကို တွက်ချက်ခိုင်းပါမည်
    
    prompt = f"""
    သင်သည် ကျွမ်းကျင်သော Movie Recap တင်ဆက်သူတစ်ဦးဖြစ်သည်။
    အောက်ပါ {input_type} ကို အခြေခံ၍ စိတ်လှုပ်ရှားဖွယ်ကောင်းသော၊ ဆွဲဆောင်မှုရှိသော မြန်မာဘာသာ Movie Recap Script တစ်ခုကို ရေးပေးပါ။
    
    သတ်မှတ်ချက်များ:
    ၁။ ဇာတ်လမ်းပြောပြပုံမှာ စိတ်လှုပ်ရှားစရာကောင်းပြီး ပရိသတ်ကို ဆွဲဆောင်နိုင်ရမည်။
    ၂။ အရေးကြီးဆုံးအချက် - ဤ Script ကို အသံထွက်ဖတ်ပါက အတိအကျ စက္ကန့် {duration} ကြာရမည်။
    ၃။ မြန်မာစကားပြောနှုန်းအရ စက္ကန့် {duration} အတွင်း အပြီးဖတ်နိုင်မည့် စာလုံးအရေအတွက်ကိုသာ ချုံ့၍ (သို့မဟုတ်) ချဲ့၍ ရေးပေးပါ။
    ၄။ စာသားသက်သက်သာ ပြန်ပေးပါ။
    
    Input Data: {input_data}
    """
    
    if input_type == "video":
        video_file = genai.upload_file(path=input_data)
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
        response = model.generate_content([prompt, video_file])
        genai.delete_file(video_file.name)
    else:
        response = model.generate_content(prompt)
        
    return response.text

# --- Streamlit UI ---
st.set_page_config(page_title="AI Movie Recap Pro", layout="wide")
st.title("🎬 AI Movie Recap (Sync Video & Audio)")

tab1, tab2 = st.tabs(["🎥 Video Upload", "📜 YouTube Transcript"])

input_data = None
duration = 0
input_type = ""

with tab1:
    video_upload = st.file_uploader("Video တင်ပါ (Max 500MB)", type=["mp4", "mov", "avi"])
    if video_upload:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(video_upload.read())
            video_path = tmp.name
        clip = VideoFileClip(video_path)
        duration = int(clip.duration)
        st.video(video_upload)
        st.info(f"ဗီဒီယိုကြာချိန်: {duration} စက္ကန့်")
        input_data = video_path
        input_type = "video"

with tab2:
    transcript_input = st.text_area("YouTube Transcript ကို ဤနေရာတွင် Paste လုပ်ပါ...")
    target_duration = st.number_input("အသံဖိုင် ထွက်စေချင်သော ကြာချိန် (စက္ကန့်)", min_value=10, value=60)
    if transcript_input:
        input_data = transcript_input
        duration = target_duration
        input_type = "transcript"

# --- Process Button ---
if st.button("Generate Recap & Sync Audio"):
    if input_data:
        with st.spinner("AI က Script ရေးသားပြီး အသံဖိုင် ဖန်တီးနေပါတယ်..."):
            try:
                # 1. Script Generation
                script = get_recap_script(input_data, duration, input_type)
                st.subheader("📝 Generated Script")
                st.write(script)

                # 2. Audio Generation (Initial)
                mp3_file = "recap.mp3"
                wav_file = "recap.wav"
                
                # အသံနှုန်းကို ချိန်ညှိရန် slider (သို့မဟုတ်) auto rate သုံးနိုင်သည်
                # ဒီမှာတော့ default အနေနဲ့ အရင်ထုတ်ပါမယ်
                asyncio.run(generate_burmese_audio(script, mp3_file, rate="+0%"))
                
                # 3. Duration Matching Check
                audio_info = AudioSegment.from_mp3(mp3_file)
                audio_duration = len(audio_info) / 1000 # in seconds
                
                st.write(f"မူလဗီဒီယိုကြာချိန်: {duration}s | ထွက်ပေါ်လာသောအသံကြာချိန်: {audio_duration:.2}s")
                
                # အကယ်၍ အသံက အရမ်းမြန်နေရင် သို့မဟုတ် နှေးနေရင် ပြန်ညှိခြင်း
                diff = duration - audio_duration
                if abs(diff) > 2: # 2 စက္ကန့်ထက် ပိုကွာရင် rate ကို ပြန်ညှိမယ်
                    speed_change = int((audio_duration / duration - 1) * 100)
                    new_rate = f"{speed_change:+}%"
                    asyncio.run(generate_burmese_audio(script, mp3_file, rate=new_rate))
                
                mp3_to_wav(mp3_file, wav_file)

                # 4. Final Output
                st.success("✅ အသံဖိုင်ကို ဗီဒီယိုကြာချိန်နဲ့ အနီးစပ်ဆုံး ချိန်ညှိပေးထားပါတယ်။")
                
                col1, col2 = st.columns(2)
                with col1:
                    st.write("MP3 Format")
                    st.audio(mp3_file)
                    with open(mp3_file, "rb") as f:
                        st.download_button("Download MP3", f, "recap.mp3")
                
                with col2:
                    st.write("WAV Format")
                    st.audio(wav_file)
                    with open(wav_file, "rb") as f:
                        st.download_button("Download WAV", f, "recap.wav")

            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.warning("Data တစ်ခုခု အရင်ထည့်ပေးပါ။")