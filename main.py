import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import os
import tempfile
import time
from moviepy.editor import VideoFileClip, AudioFileClip

# --- Configuration ---
st.set_page_config(page_title="Editable AI Movie Recap", layout="wide", page_icon="🎙️")

# API Key Handling
if "GEMINI_API_KEY" not in st.secrets:
    st.error("❌ Secrets ထဲမှာ 'GEMINI_API_KEY' ကို အရင်ထည့်ပေးပါ။")
    st.stop()
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

# Session State Initialize (Script ကို မှတ်ထားရန်)
if 'recap_script' not in st.session_state:
    st.session_state.recap_script = ""

# --- Sidebar Settings ---
st.sidebar.title("⚙️ Audio Settings")

# ၁။ အသံရွေးချယ်ခြင်း
voice_choice = st.sidebar.radio(
    "Recap ပြောမည့်သူကို ရွေးပါ:",
    ["နီလာ (အမျိုးသမီးသံ)", "သီဟ (အမျိုးသားသံ)"],
    index=0
)
voice_id = "my-MM-NilarNeural" if "နီလာ" in voice_choice else "my-MM-ThihaNeural"

# ၂။ အသံအတိုးအကျယ်
volume_value = st.sidebar.slider("အသံ အတိုး/အလျော့ (%)", -50, 50, 0, step=10)
volume_str = f"{volume_value:+}%"

st.sidebar.info("💡 **အသုံးပြုပုံ:** \n1. Video တင်ပါ။ \n2. Generate Script နှိပ်ပါ။ \n3. စာသားကို ပြင်ချင်တာပြင်ပါ။ \n4. Generate Audio နှိပ်ပါ။")

# --- Functions ---

async def generate_audio_file(text, output_path, voice, rate="+0%", volume="+0%"):
    """Edge-TTS ဖြင့် အသံဖိုင် ထုတ်ပေးခြင်း"""
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(output_path)

def get_recap_script(video_path):
    """Gemini 2.5 Flash ကို Script ရေးခိုင်းခြင်း"""
    model = genai.GenerativeModel(model_name="gemini-2.5-flash")
    video_file = genai.upload_file(path=video_path)
    
    status_placeholder = st.empty()
    status_placeholder.info("🤖 AI က Video ကို အသေးစိတ် ဖတ်နေပါတယ်...")

    while video_file.state.name == "PROCESSING":
        time.sleep(2)
        video_file = genai.get_file(video_file.name)
    
    prompt = """
    ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Movie Recap Script တစ်ခု ရေးပေးပါ။
    စည်းကမ်းချက်-
    ၁။ Timestamps တွေ၊ စက္ကန့်တွေကို လုံးဝ မထည့်ပါနဲ့။ Narrative Style ပဲ ရေးပါ။
    ၂။ 'ကဲ... ဒီနေ့မှာတော့'၊ 'တကယ့်ကို ရင်ခုန်ဖို့ကောင်းတာဗျာ' စတဲ့ energetic ဖြစ်တဲ့ စကားလုံးတွေ သုံးပါ။
    ၃။ မြန်မာစာလုံးရေ ၅၀၀ ထက် မပိုစေဘဲ လိုအပ်သလောက် ရှည်ရှည် ရေးပေးပါ။
    ၄။ အဆုံးမှာ 'ဗီဒီယိုလေးကို ကြိုက်နှစ်သက်ရင် အပေါင်းလေးနှိပ် အသဲလေးပေးသွားနော်' လို့ ထည့်ပေးပါ။
    ၅။ စာသားသက်သက်ပဲ ပြန်ပေးပါ။
    """
    
    response = model.generate_content([prompt, video_file])
    genai.delete_file(video_file.name)
    status_placeholder.empty()
    return response.text

# --- Main UI ---
st.title("🎙️ AI Movie Recap (Edit & Sync)")

v_file = st.file_uploader("Recap လုပ်မည့် Video တင်ပါ...", type=["mp4", "mov", "avi"])

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
    
    # အဆင့် ၁ - Script ထုတ်ယူခြင်း
    if st.button("📝 ၁။ Generate Recap Script"):
        with st.spinner("AI က Script ရေးနေပါတယ်..."):
            try:
                st.session_state.recap_script = get_recap_script(video_path)
            except Exception as e:
                st.error(f"Error: {str(e)}")

    # အဆင့် ၂ - Script ပြင်ဆင်ခြင်း UI
    if st.session_state.recap_script:
        st.subheader("🖋️ Recap Script ကို ပြင်ဆင်ပါ")
        
        # စာလုံးရေ ဖော်ပြခြင်း
        char_count = len(st.session_state.recap_script)
        st.caption(f"လက်ရှိစာလုံးရေ (Characters): {char_count} (အများဆုံး ၅၀၀ ခန့် အကြံပြုပါသည်)")
        
        # Editable Text Area
        st.session_state.recap_script = st.text_area(
            "စာသားကို စိတ်ကြိုက် ပြင်ဆင်နိုင်ပါတယ် -",
            value=st.session_state.recap_script,
            height=300
        )

        # အဆင့် ၃ - အသံဖိုင်ထုတ်ခြင်း
        if st.button("🚀 ၂။ Generate Audio & Auto Sync"):
            if not st.session_state.recap_script.strip():
                st.warning("စာသား အရင်ထည့်ပေးပါ။")
            else:
                with st.spinner("အသံဖိုင် ထုတ်လုပ်ပြီး Video နဲ့ Sync ညှိနေပါတယ်..."):
                    try:
                        # ကြာချိန်တိုင်းရန် အရင်ထုတ်
                        mp3_temp = os.path.join(tempfile.gettempdir(), "temp.mp3")
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

                        st.success(f"✅ Syncing Complete! (အသံနှုန်း: {final_rate})")
                        st.audio(final_mp3)
                        
                        with open(final_mp3, "rb") as f:
                            st.download_button("Download Recap MP3", f, "movie_recap.mp3")

                    except Exception as e:
                        st.error(f"Error: {str(e)}")
    
    # Cleanup
    v_clip.close()