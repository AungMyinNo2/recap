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

# Render Cloud ပေါ်တွင် /tmp folder ကိုသာ သုံးရပါမည်
TEMP_DIR = "/tmp"

@app.get("/")
def home():
    return {"message": "Movie Recap API is online!"}

@app.post("/process-movie-recap")
async def process_movie_recap(video: UploadFile = File(...), api_key: str = Form(...)):
    unique_id = str(uuid.uuid4())
    v_in = os.path.join(TEMP_DIR, f"{unique_id}_in.mp4")
    a_out = os.path.join(TEMP_DIR, f"{unique_id}_v.mp3")
    v_out = os.path.join(TEMP_DIR, f"{unique_id}_out.mp4")

    try:
        # 1. Save Video
        content = await video.read()
        with open(v_in, "wb") as f:
            f.write(content)

        # 2. Get Duration
        clip = VideoFileClip(v_in)
        duration = clip.duration

        # 3. Gemini Scripting
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        v_file = genai.upload_file(path=v_in)
        
        while v_file.state.name == "PROCESSING":
            time.sleep(2)
            v_file = genai.get_file(v_file.name)

        prompt = f"Professional Burmese Movie Recap script for {duration} seconds video. Exciting tone."
        response = model.generate_content([v_file, prompt])
        script = response.text

        # 4. Text to Speech
        voice = "my-MM-ThihaNeural"
        tts = edge_tts.Communicate(script, voice)
        await tts.save(a_out)

        # 5. Merge Audio/Video
        new_audio = AudioFileClip(a_out)
        if new_audio.duration > clip.duration:
            new_audio = new_audio.subclip(0, clip.duration)
        
        final = clip.set_audio(new_audio)
        final.write_videofile(v_out, codec="libx264", audio_codec="aac", preset="ultrafast", logger=None)
        
        clip.close()
        new_audio.close()

        # 6. Return Video File
        return FileResponse(v_out, media_type="video/mp4", filename="recap.mp4")

    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)