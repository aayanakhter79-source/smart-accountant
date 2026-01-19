import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# --- CONFIG ---
st.set_page_config(page_title="DataSnap AI Pro - Zenith", layout="wide")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:

    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]

    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])

except: st.error("AI Error")

def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
    except: return None

def safe_json_load(text):
    text = text.replace("```json","").replace("```","").strip()
    try:
        return json.loads(text)
    except:
        try:
            fixed = text.replace("\n", " ").replace(",]", "]").replace(",}", "}")
            return json.loads(fixed)
        except: return None

st.markdown("<h1 style='text-align: center; color: #00ced1;'>🚀 DataSnap AI Pro by ZENITH</h1>", unsafe_allow_html=True)
t1, t2 = st.tabs(["🚀 AI Smart Scanner", "📜 History & Logs"])

with t1:
    sheet = get_gsheet()
    total_scans = 0
    if sheet:
        all_rows = sheet.get_all_values()
        total_scans = sum(1 for r in all_rows if "SHOP NAME" in r)
    
    c1, c2 = st.columns([3, 1])
    with c2:
        st.metric("Total Successful Scans", total_scans)
        mode = st.radio("🧠 Mode", ["🤖 Auto Detect", "📊 Data Entry", "🧾 GST Mode"])

    with c1:
        up = st.file_uploader("Upload Image", type=['jpg','png','jpeg'])
        if up:
            img = Image.open(up)
            st.image(img, width=400)
            if st.button("🚀 Process & Save"):
                with st.spinner("Calculating Totals & Extracting..."):
                    # UPDATED PROMPT: Total par focus karke
                    prompt = """Extract data and return ONLY JSON.
                    { "confidence": 95, "data": [
                    ["SHOP NAME", "Name", "DATE", "Date", "", "", ""],
                    ["S.No", "Description", "HSN", "Qty", "Rate", "GST %", "Amount"],
                    ["1", "Detail", "HSN", "Qty", "Rate", "GST", "Amount"],
                    ["", "CGST", "", "", "", "", "Value"],
                    ["", "SGST", "", "", "", "", "Value"],
                    ["", "GRAND TOTAL", "", "", "", "", "Value"]
                    ]}
                    Rules: 
                    - MUST INCLUDE CGST, SGST, and GRAND TOTAL rows at the end.
                    - S.No starts from 1. 
                    - Keep descriptions very detailed."""
                    
                    try:
                        res = model.generate_content([prompt, img])
                        js = safe_json_load(res.text)
                        if js:
                            df = pd.DataFrame(js['data'])
                            st.dataframe(df, use_container_width=True)
                            if sheet: sheet.append_rows(js['data'])
                            
                            # --- EXCEL FORMATTING (TOTALS & WRAP) ---
                            out = BytesIO()
                            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                                df.to_excel(writer, index=False, header=False, sheet_name='DataSnap')
                                workbook = writer.book
                                worksheet = writer.sheets['DataSnap']
                                
                                # Wrap Text + Professional Borders
                                wrap_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                                
                                worksheet.set_column('B:B', 45, wrap_fmt) # Description wrapped
                                worksheet.set_column('A:A', 8)
                                worksheet.set_column('C:G', 15)
                            
                            st.download_button("📥 Download Excel with Totals", out.getvalue(), "DataSnap_Zenith_Final.xlsx")
                    except Exception as e:
                        st.error(f"API Error: {e}")

with t2:
    st.subheader("📜 History (Newest Scans Top)")
    if sheet:
        data = sheet.get_all_values()
        if len(data) > 0:
            df_hist = pd.DataFrame(data)
            st.dataframe(df_hist.iloc[::-1], height=600, use_container_width=True)