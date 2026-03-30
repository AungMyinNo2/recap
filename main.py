import os
import uuid
import time
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
import google.generativeai as genai
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip

app = FastAPI()

# Render လိုမျိုး Cloud ပေါ်မှာ ဖိုင်သိမ်းဖို့ /tmp folder ကို သုံးရပါမယ်
TEMP_DIR = "/tmp"

@app.get("/")
def home():
    return {"message": "Movie Recap API is running!"}

@app.post("/process-movie-recap")
async def process_movie_recap(video: UploadFile = File(...), api_key: str = Form(...)):
    # ဖိုင်နာမည်များကို Unique ဖြစ်အောင် သတ်မှတ်ခြင်း
    unique_id = str(uuid.uuid4())
    video_in_path = os.path.join(TEMP_DIR, f"{unique_id}_in.mp4")
    audio_out_path = os.path.join(TEMP_DIR, f"{unique_id}_voice.mp3")
    video_out_path = os.path.join(TEMP_DIR, f"{unique_id}_final.mp4")

    try:
        # ၁။ ပေးပို့လိုက်သော ဗီဒီယိုကို ခေတ္တသိမ်းဆည်းခြင်း
        with open(video_in_path, "wb") as f:
            f.write(await video.read())

        # ၂။ ဗီဒီယို ကြာချိန်ကို စစ်ဆေးခြင်း
        clip = VideoFileClip(video_in_path)
        duration = clip.duration

        # ၃။ Gemini AI နဲ့ မြန်မာဇာတ်ညွှန်းရေးခြင်း
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')

        # ဗီဒီယိုကို Gemini ဆီ တင်ခြင်း
        video_file_ai = genai.upload_file(path=video_in_path)
        while video_file_ai.state.name == "PROCESSING":
            time.sleep(2)
            video_file_ai = genai.get_file(video_file_ai.name)

        prompt = f"""
        You are a professional Burmese Movie Recap YouTuber.
        Analyze this video and write an exciting storytelling script in Burmese.
        Video duration is {duration} seconds.
        Tone: Engaging, fast-paced, and catchy.
        """

        response = model.generate_content([video_file_ai, prompt])
        script_text = response.text

        # ၄။ မြန်မာအသံ (TTS) ထုတ်လုပ်ခြင်း
        voice = "my-MM-ThihaNeural"
        communicate = edge_tts.Communicate(script_text, voice)
        await communicate.save(audio_out_path)

        # ၅။ ဗီဒီယိုနှင့် အသံကို ပေါင်းစပ်ခြင်း
        new_audio = AudioFileClip(audio_out_path)
        
        if new_audio.duration > clip.duration:
            new_audio = new_audio.subclip(0, clip.duration)

        final_clip = clip.set_audio(new_audio)
        
        # Render Free Tier အတွက် preset="ultrafast" သုံးပါသည်
        final_clip.write_videofile(
            video_out_path, 
            codec="libx264", 
            audio_codec="aac", 
            temp_audiofile=os.path.join(TEMP_DIR, f"{unique_id}_temp.m4a"),
            remove_temp=True,
            preset="ultrafast"
        )

        clip.close()
        new_audio.close()

        # ၆။ အချောသတ်ဗီဒီယိုကို ပို့ပေးခြင်း
        return FileResponse(
            video_out_path, 
            media_type="video/mp4", 
            filename=f"recap_{video.filename}"
        )

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPExceptio