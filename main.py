import streamlit as st
import google.generativeai as genai
import edge_tts
import asyncio
import os

# Page Settings
st.set_page_config(page_title="Burmese Movie Recap AI", page_icon="🎬")

# Custom CSS for UI
st.markdown("""
    <style>
    .main { background-color: #f0f2f6; }
    .stButton>button { width: 100%; border-radius: 10px; background-color: #e63946; color: white; }
    </style>
    """, unsafe_allow_html=True)

# Sidebar - Settings
with st.sidebar:
    st.title("⚙️ Settings")
    api_key = st.text_input("Gemini API Key ကိုထည့်ပါ", type="password")
    voice_type = st.selectbox("အသံရွေးချယ်ပါ", ["my-MM-ThihaNeural (Male)", "my-MM-NilarNeural (Female)"])
    selected_voice = voice_type.split(" ")[0]

st.title("🎬 မြန်မာ Movie Recap Script & Audio Generator")
st.write("YouTube Transcript ကို ထည့်သွင်းပေးရုံဖြင့် စိတ်လှုပ်ရှားစရာ မြန်မာရုပ်ရှင်အညွှန်း script နှင့် အသံဖိုင်ကို ဖန်တီးပေးမှာဖြစ်ပါတယ်။")

# File Upload (Video) - Max 500MB
uploaded_video = st.file_uploader("Video ဖိုင်တင်ရန် (Optional - Max 500MB)", type=["mp4", "mkv", "mov"])
if uploaded_video:
    st.video(uploaded_video)

# Input - Transcript Area
transcript_input = st.text_area("YouTube Transcript (စာသား) ကို ဤနေရာတွင် Paste လုပ်ပါ:", height=200)

# AI Function to Generate Script
def generate_burmese_recap(transcript, api_key):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompt = f"""
    You are a professional Burmese Movie Recap YouTuber. 
    Rewrite the following transcript into a high-energy, engaging, and dramatic movie recap script in Burmese.
    
    Instructions:
    1. Use an exciting storytelling tone (e.g., 'ဒီနေ့မှာတော့...', 'ဇာတ်လမ်းလေးကတော့...').
    2. Make it sound natural for a narrator.
    3. Break it into a proper story flow.
    
    Transcript:
    {transcript}
    """
    
    response = model.generate_content(prompt)
    return response.text

# Audio Generation Function
async def save_audio(text, voice):
    output_path = "recap_audio.mp3"
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_path)
    return output_path

# Process Button
if st.button("Recap ပြုလုပ်မယ်"):
    if not api_key:
        st.error("ကျေးဇူးပြု၍ API Key အရင်ထည့်ပေးပါ။")
    elif not transcript_input:
        st.warning("Transcript စာသားထည့်ပေးပါ။")
    else:
        try:
            with st.spinner("🤖 AI က မြန်မာစာသား ဖန်တီးနေပါတယ်..."):
                # 1. Generate Burmese Script
                burmese_script = generate_burmese_recap(transcript_input, api_key)
                st.subheader("📝 မြန်မာဘာသာဖြင့် ရုပ်ရှင်အညွှန်း script:")
                st.write(burmese_script)
                
            with st.spinner("🎙️ အသံဖိုင်အဖြစ် ပြောင်းလဲနေပါတယ်..."):
                # 2. Generate Audio
                audio_file_path = asyncio.run(save_audio(burmese_script, selected_voice))
                
                # 3. Display Audio Player
                st.subheader("🔊 အသံဖိုင် နားထောင်ရန်:")
                audio_file = open(audio_file_path, 'rb')
                st.audio(audio_file.read(), format='audio/mp3')
                
                # 4. Download Button
                st.download_button(
                    label="📥 Audio ဖိုင်ကို Download ရယူမယ်",
                    data=audio_file,
                    file_name="burmese_movie_recap.mp3",
                    mime="audio/mp3"
                )
        except Exception as e:
            st.error(f"အမှားအယွင်းရှိနေပါသည်: {e}")

st.markdown("---")
st.caption("Developed for Burmese Movie Recap Creators")