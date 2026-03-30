import os
import uuid
import asyncio
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import google.generativeai as genai
import edge_tts
from moviepy.editor import VideoFileClip, AudioFileClip

app = FastAPI()

# Folder များ
UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
for d in [UPLOAD_DIR, OUTPUT_DIR]:
    if not os.path.exists(d): os.makedirs(d)

@app.post("/process-movie-recap")
async def process_movie_recap(video: UploadFile = File(...), api_key: str = Form(...)):
    video_path = os.path.join(UPLOAD_DIR, f"{uuid.uuid4()}_{video.filename}")
    audio_path = os.path.join(OUTPUT_DIR, f"{uuid.uuid4()}.mp3")
    final_video_path = os.path.join(OUTPUT_DIR, f"recap_{video.filename}")

    try:
        # ၁။ ဗီဒီယိုကို သိမ်းဆည်းခြင်း
        content = await video.read()
        with open(video_path, "wb") as f:
            f.write(content)

        # ၂။ ဗီဒီယို ကြာချိန်ကို စစ်ဆေးခြင်း
        clip = VideoFileClip(video_path)
        duration_seconds = clip.duration

        # ၃။ Gemini AI နဲ့ ဇာတ်ညွှန်းရေးခြင်း
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        video_file_ai = genai.upload_file(path=video_path)
        
        # ဗီဒီယိုကြာချိန်နဲ့ အသံဖတ်ချိန် ကိုက်ညီအောင် Prompt ပေးခြင်း
        prompt = f"""
        ဒီဗီဒီယိုကိုကြည့်ပြီး စိတ်လှုပ်ရှားစရာ မြန်မာ Movie Recap ရေးပေးပါ။
        ဗီဒီယိုကြာချိန်က {duration_seconds} စက္ကန့် ဖြစ်ပါတယ်။ 
        စာဖတ်ချိန်ဟာ {duration_seconds} စက္ကန့်ထက် မကျော်စေနဲ့။ 
        မူရင်းအသံနေရာမှာ အစားထိုးမှာဖြစ်လို့ စကားလုံးအရေအတွက်ကို အတိအကျချိန်ညှိပေးပါ။
        """

        import time
        while video_file_ai.state.name == "PROCESSING":
            time.sleep(2)
            video_file_ai = genai.get_file(video_file_ai.name)

        response = model.generate_content([video_file_ai, prompt])
        script_text = response.text

        # ၄။ မြန်မာအသံ (TTS) ထုတ်လုပ်ခြင်း
        voice = "my-MM-ThihaNeural"
        communicate = edge_tts.Communicate(script_text, voice)
        await communicate.save(audio_path)

        # ၅။ ဗီဒီယိုထဲသို့ အသံအသစ်ထည့်ခြင်း (မူရင်းအသံဖျောက်ခြင်း)
        new_audio = AudioFileClip(audio_path)
        # အသံက ဗီဒီယိုထက် ရှည်နေရင် ဗီဒီယိုကြာချိန်အထိပဲ ဖြတ်မယ်
        if new_audio.duration > clip.duration:
            new_audio = new_audio.subclip(0, clip.duration)
            
        final_clip = clip.set_audio(new_audio)
        final_clip.write_videofile(final_video_path, codec="libx264", audio_codec="aac")

        # Cleanup: မလိုအပ်တဲ့ဖိုင်တွေဖျက်မယ်
        clip.close()
        new_audio.close()
        os.remove(video_path)
        os.remove(audio_path)

        return FileResponse(final_video_path, media_type="video/mp4", filename=f"recap_{video.filename}")

    except Exception as e:
        return {"error": str(e)}

# Run: uvicorn main:app --host 0.0.0.0 --port 8000