import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import os
import tempfile
from moviepy.editor import VideoFileClip

# --- Configuration ---
st.set_page_config(page_title="AI Movie Recap Myanmar", layout="wide")

# Streamlit Secrets မှ API Key ကို ယူခြင်း
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=API_KEY)
except Exception as e:
    st.error("API Key မတွေ့ပါ။ Streamlit Secrets မှာ 'GEMINI_API_KEY' ထည့်ထားလား ပြန်စစ်ပေးပါ။")

# --- Functions ---

async def generate_audio(text, output_path):
    """ကြည်လင်ပြတ်သားတဲ့ မြန်မာအသံ ထုတ်ပေးတဲ့ function"""
    # 'my-MM-NilarNeural' (အမျိုးသမီး) သို့မဟုတ် 'my-MM-KhinNeural' (အမျိုးသား)
    voice = "my-MM-NilarNeural"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)

def get_recap_script(video_file_path, duration_seconds):
    """Gemini AI ကို Video ကြည့်ခိုင်းပြီး ကြာချိန်နဲ့ကိုက်တဲ့ Script ရေးခိုင်းခြင်း"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Video upload to Gemini
    uploaded_video = genai.upload_file(path=video_file_path)
    
    # Prompt: ကြာချိန်ကိုပါ ထည့်သွင်းတွက်ချက်ခိုင်းထားပါတယ်
    prompt = f"""
    ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်ဝင်စားစရာကောင်းသော Movie Recap (ဇာတ်လမ်းအကျဉ်း) ကို မြန်မာဘာသာဖြင့် ရေးပေးပါ။
    
    သတ်မှတ်ချက်များ:
    ၁။ စကားလုံးအသုံးအနှုန်းမှာ ဆွဲဆောင်မှုရှိပြီး ကြည့်ရှုသူကို ဖမ်းစားနိုင်ရမည်။
    ၂။ အရေးကြီးဆုံးအချက် - ဤ Recap ကို အသံထွက်ဖတ်ပါက စုစုပေါင်းကြာချိန် {duration_seconds} စက္ကန့်နှင့် အတိအကျတူညီရမည်။
    ၃။ စာလုံးရေကို {duration_seconds} စက္ကန့်အတွင်း အေးအေးဆေးဆေး ဖတ်နိုင်မည့် ပမာဏသာ ရေးပေးပါ။
    ၄။ မလိုအပ်သော စကားများကို ချန်လှပ်ပြီး ဇာတ်လမ်း၏ စိတ်လှုပ်ရှားစရာ အစိတ်အပိုင်းများကိုသာ အဓိကထားပါ။
    ၅။ စာသားသက်သက်သာ ပြန်ပေးပါ။
    """
    
    response = model.generate_content([prompt, uploaded_video])
    return response.text

# --- UI Interface ---
st.title("🎬 AI Movie Recap (Burmese Voice)")
st.subheader("Video ပို့ပေးပါ၊ AI က ကြာချိန်နဲ့အကိုက် မြန်မာအသံဖိုင် ပြန်ထုတ်ပေးပါမယ်။")

uploaded_file = st.file_uploader("Recap လုပ်မည့် Video ကို ရွေးချယ်ပါ", type=["mp4", "mov", "avi"])

if uploaded_file:
    # ယာယီဖိုင် သိမ်းဆည်းခြင်း
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp_video:
        tmp_video.write(uploaded_file.read())
        video_path = tmp_video.name

    # Video ကြာချိန်ကို တိုင်းခြင်း
    clip = VideoFileClip(video_path)
    duration = int(clip.duration)
    st.write(f"🎞 ဗီဒီယိုကြာချိန် - **{duration}** စက္ကန့်")

    if st.button("Generate Recap Audio"):
        with st.spinner("AI က Video ကို လေ့လာပြီး Script ရေးနေပါတယ်..."):
            try:
                # ၁။ Gemini ဆီက Script ယူခြင်း
                recap_text = get_recap_script(video_path, duration)
                
                st.info("📝 AI Generated Script (မြန်မာလို):")
                st.write(recap_text)

                # ၂။ အသံဖိုင်အဖြစ် ပြောင်းလဲခြင်း
                audio_output = "recap_burmese.mp3"
                with st.spinner("ကြည်လင်တဲ့ မြန်မာအသံဖိုင် ထုတ်လုပ်နေပါတယ်..."):
                    asyncio.run(generate_audio(recap_text, audio_output))

                # ၃။ ရလဒ်ပြသခြင်း
                st.success(f"✅ ပြီးပါပြီ! {duration} စက္ကန့်စာ အသံဖိုင်ကို အောက်မှာ နားထောင်နိုင်ပါတယ်။")
                st.audio(audio_output, format='audio/mp3')
                
                with open(audio_output, "rb") as f:
                    st.download_button("Download MP3", f, file_name="recap_audio.mp3")

            except Exception as e:
                st.error(f"Error ဖြစ်သွားပါတယ်: {e}")
            finally:
                clip.close()
                if os.path.exists(video_path):
                    os.remove(video_path)

st.markdown("---")
st.caption("Powered by Gemini 1.5 Flash & Microsoft Edge TTS")