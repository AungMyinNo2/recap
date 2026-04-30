import streamlit as st
import google.generativeai as genai
from google.api_core import exceptions
import edge_tts
import asyncio
import os
import tempfile
import time
import random
from moviepy.editor import VideoFileClip, AudioFileClip

# ─────────────────────────────────────────
# PAGE CONFIG
# ─────────────────────────────────────────
st.set_page_config(
    page_title="Movie Recap Master",
    layout="wide",
    page_icon="🎬",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────
# CUSTOM CSS — Cinematic Dark Theme
# ─────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Nunito:wght@300;400;600;700&display=swap');

/* ── Root palette ── */
:root {
    --bg:       #0a0a0f;
    --surface:  #12121a;
    --card:     #1a1a26;
    --border:   #2a2a3a;
    --accent:   #e8b400;
    --accent2:  #ff5e5b;
    --text:     #e8e8f0;
    --muted:    #7070a0;
    --radius:   14px;
}

/* ── Global ── */
html, body, [data-testid="stAppViewContainer"] {
    background: var(--bg) !important;
    color: var(--text) !important;
    font-family: 'Nunito', sans-serif !important;
}

[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border) !important;
}

/* ── Header strip ── */
.recap-header {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    border-radius: var(--radius);
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    border: 1px solid var(--border);
    position: relative;
    overflow: hidden;
}
.recap-header::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle at 30% 50%, rgba(232,180,0,0.08) 0%, transparent 60%);
    pointer-events: none;
}
.recap-header h1 {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 3.2rem !important;
    letter-spacing: 4px;
    color: var(--accent) !important;
    margin: 0 !important;
    text-shadow: 0 0 40px rgba(232,180,0,0.4);
}
.recap-header p {
    color: var(--muted);
    font-size: 0.95rem;
    margin: 0.3rem 0 0;
    letter-spacing: 1px;
}

/* ── Stat badges ── */
.stat-row { display: flex; gap: 1rem; margin: 1rem 0; flex-wrap: wrap; }
.stat-badge {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    font-size: 0.85rem;
    color: var(--muted);
}
.stat-badge strong { color: var(--accent); font-size: 1rem; }

/* ── Section labels ── */
.section-label {
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.1rem;
    letter-spacing: 3px;
    color: var(--accent);
    margin-bottom: 0.5rem;
    text-transform: uppercase;
}

/* ── Upload zone ── */
[data-testid="stFileUploader"] {
    background: var(--card) !important;
    border: 2px dashed var(--border) !important;
    border-radius: var(--radius) !important;
    transition: border-color 0.3s !important;
}
[data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] button {
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1rem !important;
    letter-spacing: 2px !important;
    color: var(--muted) !important;
    border-radius: 8px 8px 0 0 !important;
    transition: all 0.2s !important;
}
[data-testid="stTabs"] button[aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom: 2px solid var(--accent) !important;
    background: rgba(232,180,0,0.06) !important;
}

/* ── Buttons ── */
.stButton > button {
    background: linear-gradient(135deg, var(--accent) 0%, #c9a200 100%) !important;
    color: #0a0a0f !important;
    font-family: 'Bebas Neue', sans-serif !important;
    font-size: 1rem !important;
    letter-spacing: 2px !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.6rem 2rem !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 15px rgba(232,180,0,0.25) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 25px rgba(232,180,0,0.4) !important;
}
.stButton > button:active { transform: translateY(0) !important; }

/* Download button */
[data-testid="stDownloadButton"] > button {
    background: linear-gradient(135deg, #1e3a5f 0%, #0f3460 100%) !important;
    color: #a0c4ff !important;
    border: 1px solid #2a4a7f !important;
    box-shadow: 0 4px 15px rgba(0,80,200,0.2) !important;
}
[data-testid="stDownloadButton"] > button:hover {
    box-shadow: 0 6px 25px rgba(0,80,200,0.35) !important;
}

/* ── Text areas ── */
.stTextArea textarea {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
    font-family: 'Nunito', sans-serif !important;
    font-size: 0.92rem !important;
}
.stTextArea textarea:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(232,180,0,0.15) !important;
}

/* ── Text input ── */
.stTextInput input {
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
}
.stTextInput input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(232,180,0,0.15) !important;
}

/* ── Radio / slider ── */
.stRadio label, .stSlider label {
    color: var(--text) !important;
    font-size: 0.92rem !important;
}
.stRadio [data-testid="stWidgetLabel"] {
    color: var(--muted) !important;
    font-size: 0.8rem !important;
    letter-spacing: 1px !important;
    text-transform: uppercase !important;
}

/* ── Alerts / info ── */
.stAlert {
    border-radius: 10px !important;
    border-left: 4px solid var(--accent) !important;
    background: rgba(232,180,0,0.07) !important;
}

/* ── Spinner ── */
[data-testid="stSpinner"] { color: var(--accent) !important; }

/* ── Video player ── */
video { border-radius: var(--radius) !important; }

/* ── Sidebar labels ── */
[data-testid="stSidebar"] .section-label {
    font-size: 0.75rem;
    margin-top: 1rem;
}

/* ── Info card in results ── */
.result-card {
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.5rem;
    margin: 1rem 0;
    line-height: 1.8;
}
.result-card p { color: var(--text); margin: 0; }

/* ── Divider ── */
hr { border-color: var(--border) !important; }

/* ── Sidebar title ── */
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    font-family: 'Bebas Neue', sans-serif !important;
    letter-spacing: 2px !important;
    color: var(--accent) !important;
}

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────
for key in ['recap_script', 'srt_content', 'movie_review']:
    if key not in st.session_state:
        st.session_state[key] = ""

# ─────────────────────────────────────────
# API KEY ROTATION — rotate at generate_content level
# ─────────────────────────────────────────
def get_shuffled_keys():
    if "GEMINI_KEYS" not in st.secrets:
        st.error("❌ Secrets ထဲမှာ 'GEMINI_KEYS' (List) ကို ထည့်ပေးပါ။")
        st.stop()
    keys = list(st.secrets["GEMINI_KEYS"])
    random.shuffle(keys)
    return keys

def upload_and_wait(video_path, api_key):
    """Upload video with a specific key and wait for processing."""
    genai.configure(api_key=api_key)
    video_file = genai.upload_file(path=video_path)
    with st.spinner("⏳ Video ကို Gemini ဆီ တင်နေပါသည်..."):
        while video_file.state.name == "PROCESSING":
            time.sleep(2)
            video_file = genai.get_file(video_file.name)
    return video_file

def generate_with_rotation(video_path, prompt, post_process=None):
    """
    Upload video once per key attempt, call generate_content,
    rotate key on 429/quota errors. Returns response text.
    """
    keys = get_shuffled_keys()
    last_error = None

    for i, key in enumerate(keys):
        key = key.strip()
        try:
            st.info(f"🔑 Key {i+1}/{len(keys)} ဖြင့် ကြိုးစားနေပါသည်...")
            video_file = upload_and_wait(video_path, key)
            model = genai.GenerativeModel("gemini-2.5-flash")
            response = model.generate_content([prompt, video_file])
            try:
                genai.delete_file(video_file.name)
            except Exception:
                pass
            result = response.text
            return post_process(result) if post_process else result
        except exceptions.ResourceExhausted as e:
            last_error = e
            st.warning(f"⚠️ Key {i+1} — Quota ပြည့်နေပါသည်။ နောက် Key ဖြင့် ကြိုးစားနေပါသည်...")
            try:
                genai.delete_file(video_file.name)
            except Exception:
                pass
            continue
        except (exceptions.InvalidArgument, exceptions.Unauthenticated) as e:
            last_error = e
            st.warning(f"⚠️ Key {i+1} — Invalid/Unauthenticated။ ကျော်သွားပါသည်...")
            continue
        except Exception as e:
            last_error = e
            st.warning(f"⚠️ Key {i+1} — Error: {str(e)[:80]}। ကျော်သွားပါသည်...")
            continue

    st.error(f"❌ Keys အားလုံး ({len(keys)} ခု) မအောင်မြင်ပါ။ နောက်မှ ထပ်ကြိုးစားပါ။\nLast error: {last_error}")
    st.stop()

# ─────────────────────────────────────────
# CORE FUNCTIONS
# ─────────────────────────────────────────
async def generate_audio_file(text, output_path, voice, rate="+0%", volume="+0%"):
    communicate = edge_tts.Communicate(text, voice, rate=rate, volume=volume)
    await communicate.save(output_path)

def get_recap_script(video_path):
    prompt = """
    ဤဗီဒီယိုကို ကြည့်ပြီး စိတ်လှုပ်ရှားဖွယ် မြန်မာဘာသာ Movie Recap Script တစ်ခု ရေးပေးပါ။
    စည်းကမ်းချက်-
    ၁။ Timestamps တွေ၊ စက္ကန့်တွေ၊ မိနစ်တွေကို လုံးဝ မထည့်ပါနဲ့။ Narrative Style ပဲ ရေးပါ။
    ၂။ စာသားကို စာပိုဒ်တဆက်တည်း ရေးပေးပါ။
    ၃။ အဆုံးမှာ 'ဗီဒီယိုလေးကို ကြိုက်နှစ်သက်ရင် အပေါင်းလေးနှိပ် အသဲလေးပေးသွားနော်' လို့ ထည့်ပေးပါ။
    ၄။ မြန်မာစာလုံးများများဖြင့် ပရိသတ်စွဲမက်အောင် အကျယ်တဝင့် ရေးပေးပါ။
    ၅။ စာသားသက်သက်ပဲ ပြန်ပေးပါ။
    """
    return generate_with_rotation(video_path, prompt)

def get_movie_review_info(video_path):
    prompt = """
    ဤဗီဒီယိုကို ကြည့်ပြီး ပရိသတ်စိတ်ဝင်စားသွားအောင် ဆွဲဆောင်မှုရှိသော မြန်မာဘာသာ
    ရုပ်ရှင်အမည် (Catchy Title) တစ်ခု နှင့် လူကြည့်များစေမည့် Review တစ်ခု ရေးသားပေးပါ။
    Title: [အမည်]
    Review: [စာသား]
    ပုံစံအတိုင်းပဲ ပြန်ပေးပါ။
    """
    return generate_with_rotation(video_path, prompt)

def get_srt_subtitles(video_path):
    prompt = """
    ဤဗီဒီယိုကို ကြည့်ပြီး အချိန်ကိုက် မြန်မာဘာသာ SRT Subtitle ဖိုင်တစ်ခု ဖန်တီးပေးပါ။
    Format ညွှန်ကြားချက်-
    ၁။ HH:MM:SS,mmm --> HH:MM:SS,mmm (Standard SRT) ပုံစံ တိကျစွာ သုံးပါ။
    ၂။ နာရီနေရာ (00:) မကျန်ပါစေနှင့်။
    ၃။ Comma (,) ကိုသာ မီလီစက္ကန့်ကြားသုံးပါ။
    ၄။ မြန်မာဘာသာသက်သက်သာ ရေးပါ။
    ၅။ SRT data သက်သက်သာ ပြန်ပေးပါ။
    Example:
    1
    00:00:01,500 --> 00:00:04,200
    မင်္ဂလာပါ ခင်ဗျာ။
    """
    return generate_with_rotation(
        video_path, prompt,
        post_process=lambda t: t.replace("```srt", "").replace("```", "").strip()
    )

# ─────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🎬 SETTINGS")

    keys_list = st.secrets.get("GEMINI_KEYS", [])
    st.markdown(f"""
    <div style='background:#1a1a26;border:1px solid #2a2a3a;border-radius:10px;padding:1rem;margin-bottom:1rem;'>
        <div style='color:#7070a0;font-size:0.75rem;letter-spacing:2px;text-transform:uppercase;margin-bottom:0.5rem;'>API System</div>
        <div style='color:#e8b400;font-family:"Bebas Neue",sans-serif;font-size:1.1rem;letter-spacing:2px;'>🎲 RANDOM MODE</div>
        <div style='color:#7070a0;font-size:0.8rem;margin-top:0.3rem;'>Keys {len(keys_list)} ခု — Random Rotation</div>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    st.markdown('<div class="section-label">🎙 Voice Selection</div>', unsafe_allow_html=True)
    voice_choice = st.radio(
        "Narrator:",
        ["🎤 သီဟ (Male)", "🎤 နီလာ (Female)"],
        label_visibility="collapsed"
    )
    voice_id = "my-MM-ThihaNeural" if "သီဟ" in voice_choice else "my-MM-NilarNeural"

    st.divider()

    st.markdown('<div class="section-label">🔊 Volume</div>', unsafe_allow_html=True)
    volume_value = st.slider("Volume (%)", -50, 50, 0, step=10, label_visibility="collapsed")
    volume_str = f"{volume_value:+}%"

    st.divider()
    st.markdown("""
    <div style='color:#3a3a5a;font-size:0.75rem;text-align:center;line-height:1.6;'>
        Movie Recap Master<br>Powered by Gemini 2.5 Flash
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────
# MAIN CONTENT
# ─────────────────────────────────────────
st.markdown("""
<div class="recap-header">
    <h1>🎬 MOVIE RECAP MASTER</h1>
    <p>AI-Powered Myanmar Movie Narrator · Gemini 2.5 Flash · Edge TTS</p>
</div>
""", unsafe_allow_html=True)

# Upload zone
st.markdown('<div class="section-label">📁 Upload Video</div>', unsafe_allow_html=True)
v_file = st.file_uploader(
    "MP4, MOV, AVI — Max 200MB",
    type=["mp4", "mov", "avi"],
    label_visibility="collapsed"
)

if v_file:
    if v_file.size > 200 * 1024 * 1024:
        st.error("❌ File ဆိုဒ် 200MB ကျော်နေပါသည်။")
        st.stop()

    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
        tmp.write(v_file.read())
        video_path = tmp.name

    v_clip = VideoFileClip(video_path)
    v_dur = v_clip.duration
    v_clip.close()

    # Video preview + stats
    col_vid, col_info = st.columns([3, 2])
    with col_vid:
        st.video(v_file)

    with col_info:
        size_mb = v_file.size / (1024 * 1024)
        mins = int(v_dur // 60)
        secs = int(v_dur % 60)
        st.markdown(f"""
        <div style='background:#12121a;border:1px solid #2a2a3a;border-radius:14px;padding:1.5rem;height:100%;'>
            <div class='section-label'>📊 Video Info</div>
            <div class='stat-row'>
                <div class='stat-badge'>⏱ <strong>{mins}:{secs:02d}</strong></div>
                <div class='stat-badge'>💾 <strong>{size_mb:.1f} MB</strong></div>
            </div>
            <div style='color:#7070a0;font-size:0.85rem;margin-top:1rem;line-height:1.8;'>
                ✅ Video တင်ပြီးပါပြီ<br>
                ✅ Gemini API Ready<br>
                ✅ {voice_choice} Voice Ready<br>
                ✅ Volume: {volume_str}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── TABS ──
    tab1, tab2, tab3 = st.tabs(["📝  RECAP & VOICE", "🎯  SRT SUBTITLES", "✨  TITLE & REVIEW"])

    # ── TAB 1: Recap ──
    with tab1:
        col_btn1, _ = st.columns([1, 3])
        with col_btn1:
            if st.button("📝 Generate Script", use_container_width=True):
                with st.spinner("🤖 Gemini က Script ရေးနေပါတယ်..."):
                    st.session_state.recap_script = get_recap_script(video_path)

        if st.session_state.recap_script:
            st.markdown('<div class="section-label" style="margin-top:1rem;">✏️ Edit Script</div>', unsafe_allow_html=True)
            st.session_state.recap_script = st.text_area(
                "Script",
                value=st.session_state.recap_script,
                height=280,
                label_visibility="collapsed"
            )

            col_gen, _ = st.columns([1, 3])
            with col_gen:
                if st.button("🚀 Generate Audio & Sync", use_container_width=True):
                    with st.spinner("🎙 အသံ ဖန်တီးနေပါတယ်..."):
                        try:
                            mp3_temp = tempfile.mktemp(suffix=".mp3")
                            asyncio.run(generate_audio_file(
                                st.session_state.recap_script, mp3_temp, voice_id
                            ))
                            audio_clip = AudioFileClip(mp3_temp)
                            audio_dur = audio_clip.duration
                            audio_clip.close()

                            speed_pct = round(((audio_dur / v_dur) - 1) * 100)
                            final_rate = f"{speed_pct:+}%"

                            final_mp3 = tempfile.mktemp(suffix=".mp3")
                            asyncio.run(generate_audio_file(
                                st.session_state.recap_script,
                                final_mp3, voice_id,
                                rate=final_rate, volume=volume_str
                            ))

                            st.markdown('<div class="section-label" style="margin-top:1rem;">🎵 Preview</div>', unsafe_allow_html=True)
                            st.audio(final_mp3)

                            fname = st.text_input("Filename:", value="movie_recap", key="mp3_name")
                            with open(final_mp3, "rb") as f:
                                st.download_button(
                                    "📥 Download MP3",
                                    f, f"{fname}.mp3", "audio/mpeg",
                                    use_container_width=False
                                )
                        except Exception as e:
                            st.error(f"Error: {e}")

    # ── TAB 2: SRT ──
    with tab2:
        col_btn2, _ = st.columns([1, 3])
        with col_btn2:
            if st.button("🎯 Generate SRT", use_container_width=True):
                with st.spinner("🤖 Gemini က SRT ဖန်တီးနေပါတယ်..."):
                    st.session_state.srt_content = get_srt_subtitles(video_path)

        if st.session_state.srt_content:
            st.markdown('<div class="section-label" style="margin-top:1rem;">✏️ Edit SRT</div>', unsafe_allow_html=True)
            st.session_state.srt_content = st.text_area(
                "SRT Content",
                value=st.session_state.srt_content,
                height=350,
                label_visibility="collapsed"
            )
            srt_name = st.text_input("Filename:", value="subtitles", key="srt_name")
            st.download_button(
                "📥 Download SRT",
                st.session_state.srt_content,
                f"{srt_name}.srt",
                "text/plain"
            )

    # ── TAB 3: Title & Review ──
    with tab3:
        col_btn3, _ = st.columns([1, 3])
        with col_btn3:
            if st.button("✨ Generate Title & Review", use_container_width=True):
                with st.spinner("🤖 Gemini က ဖန်တီးနေပါတယ်..."):
                    st.session_state.movie_review = get_movie_review_info(video_path)

        if st.session_state.movie_review:
            st.markdown('<div class="section-label" style="margin-top:1rem;">🎬 Result</div>', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="result-card">
                <p>{st.session_state.movie_review.replace(chr(10), '<br>')}</p>
            </div>
            """, unsafe_allow_html=True)
            st.info("💡 အပေါ်က စာသားများကို Social Media များတွင် ကူးယူ အသုံးပြုနိုင်ပါသည်။")

else:
    # Empty state
    st.markdown("""
    <div style='
        text-align:center;
        padding:4rem 2rem;
        background:#12121a;
        border:2px dashed #2a2a3a;
        border-radius:14px;
        margin-top:1rem;
    '>
        <div style='font-size:3rem;margin-bottom:1rem;'>🎬</div>
        <div style='font-family:"Bebas Neue",sans-serif;font-size:1.5rem;letter-spacing:4px;color:#e8b400;margin-bottom:0.5rem;'>
            VIDEO တင်ပါ
        </div>
        <div style='color:#7070a0;font-size:0.9rem;'>
            MP4 · MOV · AVI &nbsp;|&nbsp; Max 200MB<br>
            Gemini 2.5 Flash ဖြင့် Script · SRT · Review ထုတ်ယူပါ
        </div>
    </div>
    """, unsafe_allow_html=True)