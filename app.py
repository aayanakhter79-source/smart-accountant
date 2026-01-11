import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import json
from datetime import datetime

# --- UI & LOGIN ---
st.set_page_config(page_title="DataSnap AI ", layout="wide")
st.markdown("<style>.stApp{background:#0b0e14; color:white;}.main-header{color:#00ced1; text-align:center; font-size:40px; font-weight:bold;}</style>", unsafe_allow_html=True)

if 'auth' not in st.session_state: st.session_state['auth'] = False
if not st.session_state['auth']:
    st.markdown("<h1 class='main-header'>🔐 Access Locked</h1>", unsafe_allow_html=True)
    p = st.text_input("Enter Access Key", type="password")
    if st.button("Unlock"):
        if p == st.secrets["ADMIN_PASSWORD"]: 
            st.session_state['auth'] = True
            st.rerun()
    st.stop()

# --- MODEL SELECTION ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:
    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])
except: st.error("AI Error")

# --- GOOGLE SHEET CONNECT ---
def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
    except: return None

# --- MAIN APP ---
st.markdown("<h1 class='main-header'>📸 DataSnap AI </h1>", unsafe_allow_html=True)
t1, t2 = st.tabs(["🚀 GST Scanner", "📜 Recent History"])

with t1:
    up = st.file_uploader("Upload Bill Image", type=['jpg','png','jpeg'])
    if up:
        img = Image.open(up)
        st.image(img, width=400)
        if st.button("🚀 Process & Save Invoice"):
            with st.spinner("AI Agent is fixing headers..."):
                prompt = """Analyze this invoice.
                Rules:
                1. ROW 1: Must be exactly like this: ["SHOP NAME", "Full Shop Name Extracted", "DATE", "Bill Date", "", "", ""]
                2. ROW 2: Header row: ["S.No", "Description", "HSN", "Qty", "Rate", "GST %", "Amount"]
                3. EXTRACT FULL Descriptions for every item.
                4. CALCULATE: Subtotal, CGST (9%), SGST (9%), and Grand Total.
                Return ONLY as a JSON list of lists."""
                
                resp = model.generate_content([prompt, img])
                try:
                    data = json.loads(resp.text.replace("```json","").replace("```","").strip())
                    df = pd.DataFrame(data)
                    st.success("✅ Header & Description Fixed!")
                    st.dataframe(df, use_container_width=True)
                    
                    # Excel Formatting
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                        df.to_excel(wr, index=False, header=False, sheet_name='GST_Report')
                        workbook, worksheet = wr.book, wr.sheets['GST_Report']
                        header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D3D3D3', 'border': 1})
                        worksheet.set_column('B:B', 60) # Full Name width
                        worksheet.set_row(0, 20, header_fmt) # Shop Name Row
                        worksheet.set_row(1, 15, header_fmt) # Heading Row
                    
                    st.download_button("📥 Download Final Excel", out.getvalue(), "DataSnap_Report.xlsx")
                    
                    # Sync to Sheet (Fixed Alignment)
                    gs = get_gsheet()
                    if gs:
                        gs.insert_rows(data, row=2)
                        st.success("Synced to Cloud (Newest First)! ✅")
                except: st.code(resp.text)

with t2:
    st.header("🔍 Records Database")
    if st.button("Refresh History"):
        gs = get_gsheet()
        if gs:
            try:
                raw = gs.get_all_values()
                if len(raw) > 1:
                    # History mein data thik dikhane ke liye cleanup
                    st.dataframe(pd.DataFrame(raw[1:]))
                else: st.info("No records yet.")
            except: st.error("History fetch error.")