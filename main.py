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

# --- Custom CSS for Modern UI ---
st.markdown("""
    <style>
    .main {
        background-color: #f8f9fa;
    }
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        height: 3em;
        background-color: #FF4B4B;
        color: white;
        font-weight: bold;
        border: none;
        transition: 0.3s;
    }
    .stButton>button:hover {
        background-color: #ff3333;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    .stTextArea textarea {
        border-radius: 10px;
    }
    .reportview-container .main .block-container {
        padding-top: 2rem;
    }
    .status-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        margin-bottom: 20px;
    }
    h1 {
        color: #1E1E1E;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)

# --- API Key Rotation Logic (Randomized) ---
def get_model_with_rotation():
    if "GEMINI_KEYS" not in st.secrets:
        st.error("❌ Secrets ထဲမှာ 'GEMINI_KEYS' (List ပုံစံ) ကို အရင်ထည့်ပေးပါ။")
        st.stop()
    
    keys = list(st.secrets["GEMINI_KEYS"]) 
    random.shuffle(keys)

    for i, current_key in enumerate(keys):
        current_key = current_key.strip()
        try:
            genai.configure(api_key=current_key)
            model = genai.GenerativeModel(model_name="gemini-2.0-flash") # Updated to latest stable flash
            st.session_state.active_key_display = current_key[:10] + "..." 
            return model, current_key
        except Exception:
            continue
            
    st.error("❌ API Keys အားလုံး အလုပ်မလုပ်ပါ။ (Invalid API Key Error ဖြစ်နိုင်ပါသည်)")
    st.stop()

if 'recap_script' not in st.session_state:
    st.session_state.recap_script = ""

# --- Sidebar Settings ---
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/microphone-settings.png", width=80)
    st.title("⚙️ Settings")
    
    keys_list = st.secrets.get("GEMINI_KEYS", [])
    total_keys = len(keys_list)
    
    with st.expander("🔑 API Status", expanded=True):
        st.info(f"Mode: **Random Rotation**")
        st.caption(f"Active Keys: {total_keys}")

    st.divider()
    
    st.subheader("🔊 Voice Options")
    voice_choice = st.radio("Recap ပြောမည့်သူ:", ["နီလာ (Female)", "သီဟ (Male)"])
    voice_id = "my-MM-NilarNeural" if "နီလာ" in voice_choice else "my-MM-ThihaNeural"

    volume_value = st.sidebar.slider("အသံ အတိုး/အလျော့ (%)", -50, 50, 0, step=10)
    volume_str = f"{volume_value:+}%"

# --- Functions ---
async def generate_audio_file(text, output_path, voice, rate="+0%", volume="+0%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(output_path)

def get_recap_script(video_path):
    model, active_key = get_model_with_rotation()
    try:
        video_file = genai.upload_file(path=video_path)
        with st.status("🤖 Gemini AI is analyzing the video...", expanded=True) as status:
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = genai.get_file(video_file.name)
            status.update(label="Analysis Complete!", state="complete")
        
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
        st.warning("⚠️ Key Error! Trying another key...")
        return get_recap_script(video_path)
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.stop()

# --- Main UI ---
st.markdown("<h1 style='text-align: center; margin-bottom: 0px;'>🎙️ Movie Recap Master</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>AI-Powered Video Analysis & Myanmar Voiceover Sync</p>", unsafe_allow_html=True)
st.divider()

v_file = st.file_uploader("📤 ဗီဒီယိုဖိုင် ရွေးချယ်ပါ (MP4, MOV, AVI)", type=["mp4", "mov", "avi"])

if v_file:
    if v_file.size > 200 * 1024 * 1024:
        st.error("❌ ဖိုင်ဆိုဒ်က 200MB ထက် ကြီးနေပါတယ်။ ကျေးဇူးပြု၍ 200MB အောက် ဖိုင်ကိုသာ ရွေးချယ်ပေးပါ။")
    else:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            tmp.write(v_file.read())
            video_path = tmp.name

        v_clip = VideoFileClip(video_path)
        v_dur = v_clip.duration  
        
        col1, col2 = st.columns([1.2, 1])
        
        with col1:
            st.markdown("<div class='status-card'>", unsafe_allow_html=True)
            st.video(v_file)
            st.info(f"🎞 ဗီဒီယိုကြာချိန် - **{v_dur:.2f}** စက္ကန့်")
            
            if st.button("📝 ၁။ Generate Recap Script", use_container_width=True):
                with st.spinner("Gemini 2.5 Flash က Script ရေးနေပါတယ်..."):
                    st.session_state.recap_script = get_recap_script(video_path)
            st.markdown("</div>", unsafe_allow_html=True)

        with col2:
            if st.session_state.recap_script:
                st.markdown("<div class='status-card'>", unsafe_allow_html=True)
                st.subheader("🖋️ Edit Script")
                st.session_state.recap_script = st.text_area("Script Content:", value=st.session_state.recap_script, height=400)
                st.caption(f"📊 စာလုံးရေစုစုပေါင်း: {len(st.session_state.recap_script)}")
                
                if st.button("🚀 ၂။ Generate Audio & Sync", use_container_width=True):
                    with st.spinner("ဗီဒီယိုကြာချိန်နှင့်အညီ အသံနှုန်းကို ညှိနေပါတယ်..."):
                        try:
                            mp3_temp = "temp_audio.mp3"
                            asyncio.run(generate_audio_file(st.session_state.recap_script, mp3_temp, voice_id))
                            
                            audio_clip = AudioFileClip(mp3_temp)
                            initial_dur = audio_clip.duration
                            audio_clip.close()

                            speed_change = round(((initial_dur / v_dur) - 1) * 100)
                            final_rate = f"{speed_change:+}%"
                            
                            final_mp3 = "final_recap.mp3"
                            asyncio.run(generate_audio_file(
                                st.session_state.recap_script, final_mp3, voice_id, 
                                rate=final_rate, 
                                volume=volume_str
                            ))

                            st.success(f"✅ Sync ပြီးပါပြီ!")
                            st.audio(final_mp3)
                            
                            st.divider()
                            f_name = st.text_input("ဖိုင်အမည် (Filename):", value="movie_recap")
                            
                            with open(final_mp3, "rb") as f:
                                st.download_button(
                                    label="📥 Download Recap MP3",
                                    data=f,
                                    file_name=f"{f_name}.mp3",
                                    mime="audio/mpeg",
                                    use_container_width=True
                                )
                        except Exception as e:
                            st.error(f"Error: {str(e)}")
                st.markdown("</div>", unsafe_allow_html=True)
        
        v_clip.close()