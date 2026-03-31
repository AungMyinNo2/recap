# --- API Key များကို သိမ်းဆည်း/ပြန်ဖတ်ရန် Function များ ---
KEYS_FILE = "api_keys.txt"

def save_keys(keys_text):
    with open(KEYS_FILE, "w") as f:
        f.write(keys_text)

def load_keys():
    if os.path.exists(KEYS_FILE):
        with open(KEYS_FILE, "r") as f:
            return f.read()
    return ""

# --- Sidebar Settings ---
with st.sidebar:
    st.header("⚙️ Settings")
    
    # ဖိုင်ထဲက အရင်သိမ်းထားတဲ့ Key တွေကို ဆွဲထုတ်မယ်
    saved_keys = load_keys()
    
    # Text area ထဲမှာ အရင်ရှိပြီးသား Key တွေကို default ပေါ်နေအောင် value=saved_keys ထည့်မယ်
    keys_input = st.text_area("Gemini API Keys (တစ်ကြောင်းလျှင် တစ်ခု):", value=saved_keys, height=120)
    
    # Save Button အသစ်တစ်ခုထည့်မယ်
    if st.button("💾 Save Keys (မှတ်ထားရန်)"):
        save_keys(keys_input)
        st.success("API Keys များကို မှတ်ထားလိုက်ပါပြီ။")
        time.sleep(1)
        st.rerun()

    api_keys = [k.strip() for k in keys_input.split("\n") if k.strip()]
    # ... ကျန်တဲ့ code များအတိုင်း ...