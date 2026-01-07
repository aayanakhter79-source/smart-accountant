import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import json

# --- 1. SET PAGE CONFIG ---
st.set_page_config(page_title="DataSnap AI Premium", layout="wide")

# --- 2. LUXURY DESIGN (CSS) ---
st.markdown("""
    <style>
    .stApp { background: #0b0e14; color: white; }
    .main-header { font-size: 50px; font-weight: bold; background: -webkit-linear-gradient(#00d2ff, #3a7bd5); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-align: center; }
    .plan-card { background: rgba(255, 255, 255, 0.05); border: 1px solid #3a7bd5; padding: 20px; border-radius: 15px; text-align: center; height: 100%; }
    .stButton>button { background: linear-gradient(45deg, #00d2ff, #3a7bd5); color: white; border-radius: 20px; border: none; width: 100%; height: 3em; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. PASSWORD PROTECTION (Lock Screen) ---
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False

if not st.session_state['authenticated']:
    st.markdown("<h1 class='main-header'>🔐 DataSnap AI Lock</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        pwd = st.text_input("Enter Access Password", type="password")
        if st.button("Unlock Website"):
            if pwd == st.secrets["ADMIN_PASSWORD"]:
                st.session_state['authenticated'] = True
                st.rerun()
            else:
                st.error("Wrong Password! Contact Hussain Bhai.")
    st.stop() # Yahin rok dega jab tak password sahi na ho

# --- 4. AUTO-MODEL SELECTION LOGIC ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:
    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    sel_m = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0]
    model = genai.GenerativeModel(sel_m)
except Exception as e:
    st.error(f"AI Connection Error: {e}")

# --- 5. GOOGLE SHEET SYNC ---
def sync_data(data_row):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
        sheet.append_row(data_row)
        return True
    except: return False

# --- 6. MAIN CONTENT (After Login) ---
st.markdown("<h1 class='main-header'>📸 DataSnap AI PRO</h1>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["🚀 Scanner", "💎 Subscriptions", "📊 Admin Panel"])

with tab1:
    up_file = st.file_uploader("Upload Image", type=["jpg", "png", "jpeg"])
    if up_file:
        img = Image.open(up_file)
        st.image(img, width=400)
        if st.button("Start Analysis"):
            with st.spinner("AI processing..."):
                prompt = """Extract invoice details. Output as JSON list of lists only. 
                Include: Date, Vendor, GSTIN, Taxable_Amt, GST_Amt, Total.
                Example: [['Date', 'Vendor', 'GSTIN', 'Taxable', 'GST', 'Total'], ['01-01-26', 'XYZ', '123', '100', '18', '118']]"""
                response = model.generate_content([prompt, img])
                try:
                    res_json = json.loads(response.text.replace("```json", "").replace("```", ""))
                    df = pd.DataFrame(res_json[1:], columns=res_json[0])
                    st.dataframe(df, use_container_width=True)
                    
                    # Excel Download
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False)
                    st.download_button("📥 Download Excel", output.getvalue(), "Report.xlsx")
                    
                    if sync_data(res_json[1]): st.success("Synced to Cloud!")
                except: st.code(response.text)

with tab2:
    col1, col2, col3 = st.columns(3)
    with col1: st.markdown("<div class='plan-card'><h3>Starter</h3><h2>₹200</h2><p>20 Scans</p></div>", unsafe_allow_html=True)
    with col2: st.markdown("<div class='plan-card' style='border-color:#00d2ff'><h3>Business</h3><h2>₹1200</h2><p>Unlimited Scans</p></div>", unsafe_allow_html=True)
    with col3: st.markdown("<div class='plan-card'><h3>Enterprise</h3><h2>₹5000</h2><p>Multi-user</p></div>", unsafe_allow_html=True)
    st.markdown("<br><h4 style='text-align:center;'>Scan QR to Pay & WhatsApp Screenshot</h4>", unsafe_allow_html=True)
    st.image("https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=upi://pay?pa=YOUR_UPI@okaxis")

with tab3:
    st.subheader("Database History")
    # Yahan aayan Bhai apna data dekh sakte hain