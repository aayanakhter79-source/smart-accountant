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

    with c1:
        up = st.file_uploader("Upload Image", type=['jpg','png','jpeg'])
        if up:
            img = Image.open(up)
            st.image(img, width=450)
            
            if st.button("🚀 Process & Save"):
                with st.spinner("AI is scanning every line..."):
                    
                    if mode == "🧾 GST Invoice Mode":
                        # SHOP NAME REPEAT FIX
                        prompt = """Extract GST Data. 
                        Row 1 MUST BE EXACTLY: ["SHOP NAME", "Only Name", "DATE", "Only Date", "", "", ""]
                        Row 2: ["S.No", "Description", "HSN", "Qty", "Rate", "GST %", "Amount"]
                        Include Tax & Totals at the end. Return JSON list of lists."""
                    else:
                        # DATA ENTRY PRO (HANDWRITTEN SPECIAL)
                        prompt = """Identify all text in this image. 
                        Convert every handwritten row into a structured table row.
                        Rules:
                        1. Capture every name, number, and date.
                        2. If columns are not clear, create 3-4 general columns like 'Date', 'Description', 'Value', 'Notes'.
                        3. Do not skip any line. Do not summarize.
                        Return ONLY JSON list of lists."""

                    try:
                        response = model.generate_content([prompt, img])
                        data_list = safe_json_load(response.text)

                        if data_list:
                            # Safai: Har cell ko simple text mein convert karna
                            clean_data = [[str(c) if c else "" for c in row] for row in data_list]
                            df = pd.DataFrame(clean_data)
                            
                            st.success("✅ Extraction Complete!")
                            st.dataframe(df, use_container_width=True)

                            if sheet:
                                sheet.append_rows(clean_data)
                                st.toast("Synced to Cloud!")
                            
                            # Excel Formatting
                            out = BytesIO()
                            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                                df.to_excel(writer, index=False, header=False, sheet_name='ZenithData')
                                workbook = writer.book
                                worksheet = writer.sheets['ZenithData']
                                wrap_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                                worksheet.set_column('B:B', 60, wrap_fmt) # Badi description ke liye
                                worksheet.set_column('A:A', 10)
                                worksheet.set_column('C:G', 15)
                            
                            st.download_button("📥 Download Final Excel", out.getvalue(), "DataSnap_Zenith_Final.xlsx")
                    except Exception as e:
                        st.error(f"Error: {e}")