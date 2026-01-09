import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import json
from datetime import datetime

# --- 1. UI SETUP ---
st.set_page_config(page_title="DataSnap AI GST Pro", layout="wide")
st.markdown("""
    <style>
    .stApp {background:#0b0e14; color:white;}
    .main-header {color: #00ced1; text-align: center; font-size: 40px; font-weight: bold;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTH & MODEL ---
if 'auth' not in st.session_state: st.session_state['auth'] = False
if not st.session_state['auth']:
    st.markdown("<h1 class='main-header'>🔐 Access Locked</h1>", unsafe_allow_html=True)
    p = st.text_input("Enter Key", type="password")
    if st.button("Unlock"):
        if p == st.secrets["ADMIN_PASSWORD"]: 
            st.session_state['auth'] = True
            st.rerun()
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:
    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])
except: st.error("AI Error")

# --- 3. GOOGLE SHEET CONNECT (Improved) ---
def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
    except Exception as e:
        st.error(f"Sheet Connection Error: {e}")
        return None

# --- 4. MAIN APP ---
st.markdown("<h1 class='main-header'>📸 DataSnap AI Professional</h1>", unsafe_allow_html=True)
t1, t2 = st.tabs(["🚀 GST Scanner", "📜 Recent History"])

with t1:
    up = st.file_uploader("Upload Bill Image", type=['jpg','png','jpeg'])
    if up:
        img = Image.open(up)
        st.image(img, width=400)
        if st.button("🚀 Process GST Invoice"):
            with st.spinner("AI Generating Report..."):
                today = datetime.now().strftime("%d-%m-%Y")
                prompt = f"""Analyze this invoice image.
                1. EXTRACT Shop/Vendor Name and Bill Date.
                2. EXTRACT FULL Description without shortening.
                3. Structure: [S.No, Description, HSN, Qty, Rate, GST %, Amount].
                4. MUST include a Header row with Shop Name and Date.
                5. Include: Subtotal, CGST, SGST, Grand Total.
                Return ONLY JSON list of lists."""
                
                resp = model.generate_content([prompt, img])
                try:
                    data = json.loads(resp.text.replace("```json","").replace("```","").strip())
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    
                    # Excel Build with Headings
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                        df.to_excel(wr, index=False, header=False, sheet_name='GST_Report')
                        worksheet = wr.sheets['GST_Report']
                        worksheet.set_column('B:B', 60) # Extra wide for full description
                    
                    st.download_button("📥 Download Final Excel", out.getvalue(), "DataSnap_Report.xlsx")
                    
                    # Sync (Top of Sheet)
                    gs = get_gsheet()
                    if gs:
                        gs.insert_rows(data, row=2)
                        st.success("Synced to Cloud (Recent First)! ✅")
                except: st.code(resp.text)

with t2:
    st.header("🔍 Database Records (Newest First)")
    if st.button("🔄 Refresh History"):
        gs = get_gsheet()
        if gs:
            try:
                raw = gs.get_all_values()
                if len(raw) > 1:
                    hist_df = pd.DataFrame(raw[1:], columns=raw[0] if len(raw[0]) == len(raw[1]) else None)
                    st.dataframe(hist_df, use_container_width=True)
                else: st.info("No records yet.")
            except: st.error("Could not fetch data from Sheet.")