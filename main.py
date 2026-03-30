import os
import uuid
import time
import asyncio
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
import google.generativeai as genai
import edge_tts

app = FastAPI()

# Render Cloud ပေါ်တွင် /tmp folder ကိုသာ သုံးရပါမည်
TEMP_DIR = "/tmp"

# အသံဖိုင်များကို URL ဖြင့် လှမ်းခေါ်နိုင်ရန် Static Folder သတ်မှတ်ခြင်း
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
        # ၁။ ဗီဒီယိုကို သိမ်းဆည်းခြင်း
        content = await video.read()
        with open(v_path, "wb") as f:
            f.write(content)

        # ၂။ Gemini AI Configuration
        genai.configure(api_key=api_key)
        
        # မော်ဒယ်အမည်ကို အတိအကျ သတ်မှတ်ခြင်း
        model = genai.GenerativeModel(model_name="gemini-1.5-flash")
        
        # ဗီဒီယိုကို Gemini ဆီသို့ Upload တင်ခြင်း
        v_file = genai.upload_file(path=v_path)
        
        # AI က ဗီဒီယိုကို ဖတ်နေစဉ် စောင့်ဆိုင်းခြင်း
        retry_count = 0
        while v_file.state.name == "PROCESSING" and retry_count < 30:
            time.sleep(2)
            v_file = genai.get_file(v_file.name)
            retry_count += 1

        # ၃။ မြန်မာဇာတ်ညွှန်း ရေးသားခြင်း
        prompt = "ဒီဗီဒီယိုကိုကြည့်ပြီး စိတ်လှုပ်ရှားစရာ Movie Recap မြန်မာဇာတ်ညွှန်း ရေးပေးပါ။"
        
        try:
            response = model.generate_content([v_file, prompt])
            script_text = response.text
        except Exception as ai_err:
            return JSONResponse(status_code=500, content={"error": f"AI Error: {str(ai_err)}", "script": None})

        # ၄။ မြန်မာအသံ (TTS) ထုတ်လုပ်ခြင်း
        voice = "my-MM-ThihaNeural" # မြန်မာအမျိုးသားအသံ
        communicate = edge_tts.Communicate(script_text, voice)
        await communicate.save(a_path)

        # ၅။ အောင်မြင်လျှင် စာသားနှင့် အသံ URL ကို ပြန်ပို့ပေးခြင်း
        return {
            "script": script_text,
            "audio_url": f"static/{unique_id}_audio.mp3"
        }

    except Exception as e:
        print(f"Server Error: {e}")
        return JSONResponse(status_code=500, content={"error": str(e), "script": None})
    
    finally:
        # မူရင်းဗီဒီယိုကို ဖျက်ပစ်ခြင်း (Storage ချွေတာရန်)
        if os.path.exists(v_path):
            try: os.remove(v_path)
            except: pass

if __name__ == "__main__":
    import uvicorn
    # Render တွင် run ရန် port သတ်မှတ်ချက်
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)