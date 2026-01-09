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
st.set_page_config(page_title="DataSnap AI GST Pro", layout="wide")
st.markdown("""
    <style>
    .stApp {background:#0b0e14; color:white;}
    .main-header {color: #00ced1; text-align: center; font-size: 40px; font-weight: bold;}
    </style>
    """, unsafe_allow_html=True)

if 'auth' not in st.session_state: st.session_state['auth'] = False
if not st.session_state['auth']:
    st.markdown("<h1 class='main-header'>🔐 Access Locked</h1>", unsafe_allow_html=True)
    p = st.text_input("Enter Key", type="password")
    if st.button("Unlock"):
        if p == st.secrets["ADMIN_PASSWORD"]: 
            st.session_state['auth'] = True
            st.rerun()
    st.stop()

# --- MODEL & SHEET SETUP ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:
    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])
except: st.error("AI Error")

def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        return gspread.authorize(creds).open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
    except: return None

# --- MAIN APP ---
st.markdown("<h1 class='main-header'>📸 DataSnap AI Professional</h1>", unsafe_allow_html=True)
t1, t2 = st.tabs(["🚀 GST Scanner", "📜 Recent History"])

with t1:
    up = st.file_uploader("Upload Bill Image", type=['jpg','png','jpeg'])
    if up:
        img = Image.open(up)
        st.image(img, width=400)
        if st.button("🚀 Process GST Invoice"):
            with st.spinner("AI is calculating..."):
                prompt = """Analyze this invoice. Extract FULL description.
                Structure: S.No, Description, HSN, Qty, Rate, GST %, Amount.
                Include: Subtotal, CGST (9%), SGST (9%), Grand Total.
                Return ONLY JSON list of lists."""
                
                resp = model.generate_content([prompt, img])
                try:
                    data = json.loads(resp.text.replace("```json","").replace("```","").strip())
                    df = pd.DataFrame(data)
                    st.dataframe(df, use_container_width=True)
                    
                    # Excel Build
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                        df.to_excel(wr, index=False, header=False, sheet_name='GST_Report')
                        worksheet = wr.sheets['GST_Report']
                        worksheet.set_column('B:B', 50)
                    st.download_button("📥 Download Excel", out.getvalue(), "Report.xlsx")
                    
                    # --- RECENT FIRST SYNC (Google Sheet) ---
                    gs = get_gsheet()
                    if gs:
                        # Naya data hamesha Row 2 par insert hoga (Header ke niche)
                        # Isse Google Sheet mein bhi naya data sabse upar rahega
                        gs.insert_rows(data, row=2) 
                        st.success("Synced to Cloud (Top of Sheet)! ✅")
                except: st.code(resp.text)

with t2:
    st.header("🔍 Database Records (Newest First)")
    gs = get_gsheet()
    if gs:
        try:
            # get_all_values() se sara data uthayenge
            raw = gs.get_all_values()
            if len(raw) > 1:
                # Header alag kar lo
                header = raw[0]
                # Baki data ko reverse kar do taaki recent upar dikhe
                records = raw[1:]
                # Note: Agar insert_rows(row=2) use kar rahe ho, toh records pehle se reverse hain
                hist_df = pd.DataFrame(records, columns=header)
                
                q = st.text_input("Search by Name/Date")
                if q:
                    hist_df = hist_df[hist_df.astype(str).apply(lambda x: q.lower() in x.str.lower().values, axis=1)]
                
                st.dataframe(hist_df, use_container_width=True)
            else:
                st.info("No records found yet.")
        except: st.error("Connection problem with Google Sheets.")