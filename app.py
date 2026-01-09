import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import json
from datetime import datetime

# --- 1. CONFIG & UI ---
st.set_page_config(page_title="DataSnap AI GST Agent", layout="wide")
st.markdown("""
    <style>
    .stApp {background:#0b0e14;color:white;}
    .main-card {background:#161b22;padding:20px;border-radius:15px;border:1px solid #00ced1;}
    .stButton>button {background: linear-gradient(45deg, #00d2ff, #3a7bd5); color:white; border-radius:20px;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. AUTH & MODEL ---
if 'login' not in st.session_state: st.session_state['login'] = False
if not st.session_state['login']:
    st.title("🔐 Access Locked")
    p = st.text_input("Password", type="password")
    if st.button("Unlock"):
        if p == st.secrets["ADMIN_PASSWORD"]: 
            st.session_state['login'] = True
            st.rerun()
    st.stop()

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:
    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])
except: st.error("AI Error")

# --- 3. GOOGLE SHEET HELPER ---
def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        return gspread.authorize(creds).open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
    except: return None

# --- 4. MAIN INTERFACE ---
st.title("🤖 DataSnap AI Accountant")
t1, t2 = st.tabs(["🚀 Scanner", "📜 History"])

with t1:
    up = st.file_uploader("Upload Invoice", type=['jpg','png','jpeg'])
    if up:
        img = Image.open(up)
        st.image(img, width=400)
        if st.button("🚀 Generate GST Report"):
            with st.spinner("AI Agent calculating..."):
                prompt = """Analyze this invoice. Extract data into this EXACT JSON structure.
                Rules: 
                1. FULL DESCRIPTION for items.
                2. Calculate CGST(9%) and SGST(9%) separately.
                3. Structure: [["S.No", "Description", "HSN", "Qty", "Rate", "GST %", "Amount"], ["1", "FULL DESC", "HSN", "1", "100", "18%", "118"]]
                Add Subtotal, CGST, SGST, and Grand Total as final rows.
                Return ONLY the JSON list of lists."""
                
                resp = model.generate_content([prompt, img])
                try:
                    data = json.loads(resp.text.replace("```json","").replace("```","").strip())
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    
                    # --- EXCEL DOWNLOAD ---
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                        df.to_excel(wr, index=False, header=False, sheet_name='GST_Report')
                        # Auto-adjust column width
                        worksheet = wr.sheets['GST_Report']
                        worksheet.set_column('B:B', 50) # Description column wide
                    
                    st.download_button("📥 Download Excel", out.getvalue(), "Report.xlsx")
                    
                    # --- SYNC ---
                    gs = get_gsheet()
                    if gs: gs.append_rows(data)
                except: st.write(resp.text)

with t2:
    st.header("Search History")
    search = st.text_input("Vendor Name/Date")
    if st.button("Search"):
        gs = get_gsheet()
        if gs:
            try:
                raw_data = gs.get_all_values() # get_all_records ki jagah ye safe hai
                if len(raw_data) > 0:
                    hist_df = pd.DataFrame(raw_data)
                    st.dataframe(hist_df)
                else: st.warning("Sheet is empty!")
            except: st.error("History tab error. Pehle koi data scan karein.")

st.sidebar.info("Plan: Business Unlimited")