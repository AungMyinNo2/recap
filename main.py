import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions
import edge_tts
import asyncio
import os
import tempfile
import time
from moviepy.editor import VideoFileClip, AudioFileClip

# --- Configuration ---
st.set_page_config(page_title="AI Movie Recap Master", layout="wide", page_icon="🎙️")

# --- API Key Rotation Logic ---
def get_model_with_rotation():
    """Secrets ထဲက GEMINI_KEYS ကို တစ်ခုပြီးတစ်ခု စမ်းသုံးပေးမည့် Function"""
    if "GEMINI_KEYS" not in st.secrets:
        st.error("❌ Secrets ထဲမှာ 'GEMINI_KEYS' (List ပုံစံ) ကို အရင်ထည့်ပေးပါ။")
        st.stop()
    
    keys = st.secrets["GEMINI_KEYS"]
    
    if 'current_key_index' not in st.session_state:
        st.session_state.current_key_index = 0

    # Key တစ်ခုချင်းစီကို ပတ်စစ်မယ်
    for _ in range(len(keys)):
        idx = st.session_state.current_key_index
        current_key = keys[idx].strip() 
        
        try:
            genai.configure(api_key=current_key)
            # အသုံးပြုသူတောင်းဆိုထားသည့် Gemini 2.5 Flash version ကို အသုံးပြုထားပါသည်
            model = genai.GenerativeModel(model_name="gemini-2.5-flash")
            return model, current_key
        except Exception:
            # Error ဖြစ်လျှင် နောက် Key တစ်ခုသို့ ပြောင်းရန်
            st.session_state.current_key_index = (st.session_state.current_key_index + 1) % len(keys)
            continue
            
    st.error("❌ API Keys အားလုံး အလုပ်မလုပ်ပါ။ (Invalid API Key Error ဖြစ်နိုင်ပါသည်)")
    st.stop()

if 'recap_script' not in st.session_state:
    st.session_state.recap_script = ""

# --- Sidebar Settings ---
st.sidebar.title("⚙️ Audio Settings")

# API Keys အရေအတွက်နှင့် လက်ရှိသုံးနေသော Key ကို ပြသရန်
keys_list = st.secrets.get("GEMINI_KEYS", [])
total_keys = len(keys_list)
current_key_num = st.session_state.get('current_key_index', 0) + 1

st.sidebar.info(f"🔑 **API Status:** Using Key **{current_key_num}** of **{total_keys}**")
if total_keys > 1:
    st.sidebar.caption(f"စုစုပေါင်း API Key {total_keys} ခု ချိတ်ဆက်ထားပါသည်။")

st.sidebar.divider()

voice_choice = st.sidebar.radio("Recap ပြောမည့်သူ:", ["နီလာ (အမျိုးသမီးသံ)", "သီဟ (အမျိုးသားသံ)"])
voice_id = "my-MM-NilarNeural" if "နီလာ" in voice_choice else "my-MM-ThihaNeural"

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
    keys = st.secrets["GEMINI_KEYS"]
    
    for _ in range(len(keys)):
        model, active_key = get_model_with_rotation()
        try:
            video_file = genai.upload_file(path=video_path)
            st.info(f"🤖 Gemini 2.5 Flash က Video ကို ဖတ်နေပါတယ်... (Key #{st.session_state.current_key_index + 1} ကို သုံးနေသည်)")

            # Processing ပြီးအောင် စောင့်ခြင်း
            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = genai.get_file(video_file.name)
            
            prompt = """
            ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Movie Recap Script တစ်ခု ရေးပေးပါ။
            စည်းကမ်းချက်-
            ၁။ Timestamps တွေ၊ စက္ကန့်တွေ၊ မိနစ်တွေကို လုံးဝ မထည့်ပါနဲ့။ Narrative Style ပဲ ရေးပါ။
            ၂။ စာသားကို စာပိုဒ်တဆက်တည်း ရေးပေးပါ။
            ၃။ အဆုံးမှာ 'ဗီဒီယိုလေးကို ကြိုက်နှစ်သက်ရင် အပေါင်းလေးနှိပ် အသဲလေးပေးသွားနော်' လို့ ထည့်ပေးပါ။
            ၄။ မြန်မာစာလုံးရေ ၅၀၀ ထက် မပိုစေဘဲ ဇာတ်လမ်းကို ပရိသတ်စွဲမက်အောင် အကျယ်တဝင့် ရေးပေးပါ။
            ၅။ စာသားသက်သက်ပဲ ပြန်ပေးပါ။
            """
            
            response = model.generate_content([prompt, video_file])
            genai.delete_file(video_file.name)
            return response.text
            
        except (exceptions.InvalidArgument, exceptions.Unauthenticated):
            st.warning(f"⚠️ Key #{st.session_state.current_key_index + 1} မှားယွင်းနေသဖြင့် နောက်တစ်ခုသို့ ပြောင်းနေသည်...")
            st.session_state.current_key_index = (st.session_state.current_key_index + 1) % len(keys)
            st.rerun() 
        except exceptions.ResourceExhausted:
            st.warning(f"⚠️ Key #{st.session_state.current_key_index + 1} Limit ပြည့်သွားသဖြင့် နောက်တစ်ခုသို့ ပြောင်းနေသည်...")
            st.session_state.current_key_index = (st.session_state.current_key_index + 1) % len(keys)
            st.rerun()
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.stop()
    return None

# --- Main UI ---
st.title("🎙️ AI Movie Recap (Gemini 2.5 Flash)")

v_file = st.file_uploader("Video တင်ပါ...", type=["mp4", "mov", "avi"])

if v_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(v_file.read())
        video_path = tmp.name

    v_clip = VideoFileClip(video_path)
    v_dur = int(v_clip.duration)
    
    col1, col2 = st.columns([1, 1])
    with col1:
        st.video(v_file)
        st.write(f"🎞 ဗီဒီယိုကြာချိန် - **{v_dur}** စက္ကန့်")
    
    if st.button("📝 ၁။ Generate Recap Script"):
        with st.spinner("Gemini 2.5 Flash က Script ရေးနေပါတယ်..."):
            st.session_state.recap_script = get_recap_script(video_path)

    if st.session_state.recap_script:
        st.subheader("🖋️ Script ကို ပြင်ဆင်ပါ")
        st.caption(f"စာလုံးရေ: {len(st.session_state.recap_script)}")
        st.session_state.recap_script = st.text_area("Edit Script:", value=st.session_state.recap_script, height=300)

        if st.button("🚀 ၂။ Generate Audio & Sync"):
            with st.spinner("Sync ညှိနေပါတယ်..."):
                try:
                    mp3_temp = "temp_audio.mp3"
                    asyncio.run(generate_audio_file(st.session_state.recap_script, mp3_temp, voice_id))
                    
                    audio_clip = AudioFileClip(mp3_temp)
                    initial_dur = audio_clip.duration
                    audio_clip.close()

                    # Auto Sync Logic
                    speed_change = int((initial_dur / v_dur - 1) * 100)
                    speed_change = max(min(speed_change, 50), -50) 
                    final_rate = f"{speed_change:+}%"
                    
                    final_mp3 = "final_recap.mp3"
                    asyncio.run(generate_audio_file(
                        st.session_state.recap_script, final_mp3, voice_id, 
                        rate=final_rate, 
                        volume=volume_str
                    ))

                    st.success(f"✅ Sync ပြီးပါပြီ! (နှုန်းညှိချက်: {final_rate})")
                    st.audio(final_mp3)
                    with open(final_mp3, "rb") as f:
                        st.download_button("Download Recap MP3", f, "movie_recap.mp3")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    v_clip.close()