import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# --- CONFIG & API SETUP ---
st.set_page_config(page_title="DataSnap AI - Zenith Pro", layout="wide")

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
        return None

# --- MAIN UI ---
st.markdown("<h1 style='text-align: center; color: #00ced1;'>🚀 DataSnap AI Pro by ZENITH</h1>", unsafe_allow_html=True)
t1, t2 = st.tabs(["🚀 AI Scanner", "📜 Data History"])

with t1:
    sheet = get_gsheet()
    c1, c2 = st.columns([3, 1])
    
    with c2:
        mode = st.radio("🧠 Select Mode", ["📊 Advanced Data Entry", "🧾 GST Invoice Mode"])
        st.info(f"Active Mode: {mode}")

    with c1:
        up = st.file_uploader("Upload Image", type=['jpg','png','jpeg'])
        if up:
            img = Image.open(up)
            st.image(img, width=450)
            
            if st.button("🚀 Process & Save"):
                with st.spinner("AI is reading data..."):
                    
                    if mode == "🧾 GST Invoice Mode":
                        # SHOP NAME FIX: Clearly defined single cell
                        prompt = """TASK: GST EXTRACTION.
                        Rules:
                        1. Row 1: ["SHOP NAME", "Write Name Here", "DATE", "Date", "", "", ""] (DO NOT REPEAT NAME).
                        2. Row 2: ["S.No", "Description", "HSN", "Qty", "Rate", "GST %", "Amount"]
                        3. Extract all items with long descriptions.
                        4. Mandatory: CGST, SGST, GRAND TOTAL rows at bottom.
                        Return ONLY JSON list of lists."""
                    else:
                        # DATA ENTRY PRO: High detail for registers/notebooks
                        prompt = """TASK: ADVANCED DATA ENTRY.
                        Rules:
                        1. Scan the entire image for any tabular data, lists, or handwritten notes.
                        2. Create a clean table with appropriate headers.
                        3. Capture EVERY ROW. Do not summarize. 
                        4. If multiple tables exist, add an empty row between them.
                        5. Keep descriptions extremely detailed.
                        Return ONLY JSON list of lists."""

                    try:
                        response = model.generate_content([prompt, img])
                        data_list = safe_json_load(response.text)

                        if data_list:
                            # Safai: Convert everything to string for Google Sheets
                            clean_data = [[str(cell) if cell else "" for cell in row] for row in data_list]
                            df = pd.DataFrame(clean_data)
                            
                            st.success("✅ Extraction Complete!")
                            st.dataframe(df, use_container_width=True)

                            if sheet:
                                sheet.append_rows(clean_data)
                                st.toast("Synced to Cloud!")
                            
                            # --- EXCEL PRO FORMATTING ---
                            out = BytesIO()
                            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                                df.to_excel(writer, index=False, header=False, sheet_name='ZenithData')
                                workbook = writer.book
                                worksheet = writer.sheets['ZenithData']
                                wrap_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                                worksheet.set_column('B:B', 55, wrap_fmt) # Extra width for data entry
                                worksheet.set_column('A:A', 10)
                                worksheet.set_column('C:G', 15)
                            
                            st.download_button("📥 Download Excel", out.getvalue(), "DataSnap_Zenith_Pro.xlsx")
                    except Exception as e:
                        st.error(f"Error: {e}")

with t2:
    if sheet:
        try:
            raw = sheet.get_all_values()
            if raw:
                st.dataframe(pd.DataFrame(raw).iloc[::-1], height=600, use_container_width=True)
        except: st.warning("Syncing history...")