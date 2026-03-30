import os
import uuid
import time
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import google.generativeai as genai
import edge_tts

app = FastAPI()
TEMP_DIR = "/tmp"

# အသံဖိုင်ကို URL နဲ့ လှမ်းခေါ်လို့ရအောင် static folder သတ်မှတ်မယ်
app.mount("/static", StaticFiles(directory=TEMP_DIR), name="static")

@app.get("/")
def home():
    return {"message": "Movie Recap Audio API is online!"}

@app.post("/process-movie-recap")
async def process_movie_recap(video: UploadFile = File(...), api_key: str = Form(...)):
    unique_id = str(uuid.uuid4())
    v_path = os.path.join(TEMP_DIR, f"{unique_id}_video.mp4")
    a_path = os.path.join(TEMP_DIR, f"{unique_id}_audio.mp3")

    try:
        # 1. ဗီဒီယိုကို သိမ်းဆည်းခြင်း
        with open(v_path, "wb") as f:
            f.write(await video.read())

        # 2. Gemini AI နဲ့ ဇာတ်ညွှန်းရေးခြင်း
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        v_file = genai.upload_file(path=v_path)
        
        while v_file.state.name == "PROCESSING":
            time.sleep(2)
            v_file = genai.get_file(v_file.name)

        prompt = "ဒီဗီဒီယိုကိုကြည့်ပြီး စိတ်လှုပ်ရှားစရာ Movie Recap မြန်မာဇာတ်ညွှန်း ရေးပေးပါ။"
        response = model.generate_content([v_file, prompt])
        script_text = response.text

        # 3. မြန်မာအသံ (TTS) ထုတ်လုပ်ခြင်း
        voice = "my-MM-ThihaNeural"
        communicate = edge_tts.Communicate(script_text, voice)
        await communicate.save(a_path)

        # 4. စာသားနဲ့ အသံ URL ကို JSON အနေနဲ့ ပြန်ပို့ပေးမယ်
        return {
            "script": script_text,
            "audio_url": f"static/{unique_id}_audio.mp3"
        }

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        if os.path.exists(v_path): os.remove(v_path)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)