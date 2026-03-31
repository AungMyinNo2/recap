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
st.set_page_config(page_title="AI Movie Recap Pro", layout="wide", page_icon="🎙️")

# --- API Key Rotation Logic ---
def get_model_with_rotation():
    """Secrets ထဲက GEMINI_KEYS ကို တစ်ခုပြီးတစ်ခု စမ်းသုံးပေးမည့် Function"""
    if "GEMINI_KEYS" not in st.secrets:
        st.error("❌ Secrets ထဲမှာ 'GEMINI_KEYS' ကို အရင်ထည့်ပေးပါ။")
        st.stop()
    
    keys = st.secrets["GEMINI_KEYS"]
    
    if 'current_key_index' not in st.session_state:
        st.session_state.current_key_index = 0

    # လက်ရှိ index ကနေ စပြီး Key တွေကို ပတ်စစ်မယ်
    for _ in range(len(keys)):
        idx = st.session_state.current_key_index
        current_key = keys[idx].strip() # Space ပါခဲ့ရင် ဖယ်ပစ်မယ်
        
        try:
            genai.configure(api_key=current_key)
            model = genai.GenerativeModel(model_name="gemini-1.5-flash") # Stable version
            return model, current_key
        except Exception:
            st.session_state.current_key_index = (st.session_state.current_key_index + 1) % len(keys)
            continue
            
    st.error("❌ API Keys အားလုံး မှားယွင်းနေပါသည်။")
    st.stop()

if 'recap_script' not in st.session_state:
    st.session_state.recap_script = ""

# --- Sidebar ---
st.sidebar.title("⚙️ Audio Settings")
voice_choice = st.sidebar.radio("Recap ပြောမည့်သူ:", ["နီလာ (အမျိုးသမီးသံ)", "သီဟ (အမျိုးသားသံ)"])
voice_id = "my-MM-NilarNeural" if "နီလာ" in voice_choice else "my-MM-ThihaNeural"
volume_value = st.sidebar.slider("အသံ အတိုး/အလျော့ (%)", -50, 50, 0, step=10)
volume_str = f"{volume_value:+}%"
st.sidebar.markdown(f"🔑 **Active Key:** #{st.session_state.get('current_key_index', 0) + 1}")

# --- Functions ---
async def generate_audio_file(text, output_path, voice, rate="+0%", volume="+0%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(output_path)

def get_recap_script(video_path):
    keys = st.secrets["GEMINI_KEYS"]
    
    for _ in range(len(keys)):
        model, active_key = get_model_with_rotation()
        try:
            video_file = genai.upload_file(path=video_path)
            st.info(f"🤖 AI က Video ကို ဖတ်နေပါတယ်...")

            while video_file.state.name == "PROCESSING":
                time.sleep(2)
                video_file = genai.get_file(video_file.name)
            
            prompt = """
            ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Movie Recap Script တစ်ခု ရေးပေးပါ။
            စည်းကမ်းချက်-
            ၁။ Timestamps တွေ၊ စက္ကန့်တွေကို လုံးဝ မထည့်ပါနဲ့။ Narrative Style ပဲ ရေးပါ။
            ၂။ စာသားကို စာပိုဒ်တဆက်တည်း ရေးပေးပါ။
            ၃။ အဆုံးမှာ 'ဗီဒီယိုလေးကို ကြိုက်နှစ်သက်ရင် အပေါင်းလေးနှိပ် အသဲလေးပေးသွားနော်' လို့ ထည့်ပေးပါ။
            ၄။ မြန်မာစာလုံးရေ ၅၀၀ ထက် မပိုစေဘဲ ဇာတ်လမ်းကို ပရိသတ်စွဲမက်အောင် အကျယ်တဝင့် ရေးပေးပါ။
            ၅။ စာသားသက်သက်ပဲ ပြန်ပေးပါ။
            """
            response = model.generate_content([prompt, video_file])
            genai.delete_file(video_file.name)
            return response.text
            
        except (exceptions.InvalidArgument, exceptions.Unauthenticated):
            # Key မှားနေရင် နောက်တစ်ခုကို ချက်ချင်းပြောင်းမယ်
            st.warning(f"⚠️ Key #{st.session_state.current_key_index + 1} မှားယွင်းနေသဖြင့် နောက်တစ်ခုသို့ ပြောင်းနေသည်...")
            st.session_state.current_key_index = (st.session_state.current_key_index + 1) % len(keys)
            continue
        except exceptions.ResourceExhausted:
            # Quota ပြည့်ရင် နောက်တစ်ခုကို ပြောင်းမယ်
            st.warning(f"⚠️ Key #{st.session_state.current_key_index + 1} Limit ပြည့်သွားသဖြင့် နောက်တစ်ခုသို့ ပြောင်းနေသည်...")
            st.session_state.current_key_index = (st.session_state.current_key_index + 1) % len(keys)
            continue
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.stop()
    return None

# --- UI ---
st.title("🎙️ AI Movie Recap (Auto Key-Switch)")

v_file = st.file_uploader("Video တင်ပါ...", type=["mp4", "mov", "avi"])

if v_file:
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(v_file.read())
        video_path = tmp.name

    v_clip = VideoFileClip(video_path)
    v_dur = int(v_clip.duration)
    st.video(v_file)
    st.write(f"🎞 ဗီဒီယိုကြာချိန် - **{v_dur}** စက္ကန့်")
    
    if st.button("📝 ၁။ Generate Recap Script"):
        st.session_state.recap_script = get_recap_script(video_path)

    if st.session_state.recap_script:
        st.subheader("🖋️ Script ကို ပြင်ဆင်ပါ")
        st.session_state.recap_script = st.text_area("Edit Script:", value=st.session_state.recap_script, height=300)

        if st.button("🚀 ၂။ Generate Audio & Sync"):
            with st.spinner("Sync ညှိနေပါတယ်..."):
                try:
                    mp3_temp = "temp.mp3"
                    asyncio.run(generate_audio_file(st.session_state.recap_script, mp3_temp, voice_id))
                    audio_clip = AudioFileClip(mp3_temp)
                    initial_dur = audio_clip.duration
                    audio_clip.close()

                    speed_change = int((initial_dur / v_dur - 1) * 100)
                    speed_change = max(min(speed_change, 50), -50) 
                    final_rate = f"{speed_change:+}%"
                    
                    final_mp3 = "final_recap.mp3"
                    asyncio.run(generate_audio_file(st.session_state.recap_script, final_mp3, voice_id, rate=final_rate, volume=volume_str))

                    st.success(f"✅ Sync ပြီးပါပြီ!")
                    st.audio(final_mp3)
                    st.download_button("Download MP3", open(final_mp3, "rb"), "recap.mp3")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    v_clip.close()