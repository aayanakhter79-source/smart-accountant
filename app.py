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
    for _ in range(2):
        try:
            return json.loads(text)
        except:
            text = text.replace("\n", " ").replace(",]", "]").replace(",}", "}")
    return None

# --- MAIN UI ---
st.markdown("<h1 style='text-align: center; color: #00ced1;'>🚀 DataSnap AI Pro by ZENITH</h1>", unsafe_allow_html=True)
t1, t2 = st.tabs(["🚀 AI Scanner", "📜 Data History"])

with t1:
    sheet = get_gsheet()
    c1, c2 = st.columns([3, 1])
    
    with c2:
        mode = st.radio("🧠 Select Task Type", ["📊 Data Entry Only", "🧾 GST Invoice Mode"])
        st.info(f"Mode: {mode}")

    with c1:
        up = st.file_uploader("Upload Image", type=['jpg','png','jpeg'])
        if up:
            img = Image.open(up)
            st.image(img, width=450)
            
            if st.button("🚀 Process & Save Data"):
                with st.spinner("AI is analyzing..."):
                    # GPT Instruction logic based on mode
                    if mode == "🧾 GST Invoice Mode":
                        prompt = """TASK: GST EXTRACTION.
                        Rules:
                        1. Even if GST missing, calculate 18% logically.
                        2. Row 1: Shop Name & Date.
                        3. Columns: S.No, Description, HSN, Qty, Rate, GST %, Amount.
                        4. Add Mandatory Final Rows: CGST, SGST, GRAND TOTAL.
                        Return ONLY JSON list of lists."""
                    else:
                        prompt = """TASK: DATA ENTRY.
                        Rules:
                        1. Identify and extract all tables.
                        2. Keep descriptions very detailed.
                        3. Add empty rows between different tables.
                        Return ONLY JSON list of lists."""

                    # --- YE HAI TRY BLOCK KI SAHI ALIGNMENT ---
                    try:
                        response = model.generate_content([prompt, img])
                        data_list = safe_json_load(response.text)

                        if data_list:
                            df = pd.DataFrame(data_list)
                            st.success(f"✅ {mode} Done!")
                            st.dataframe(df, use_container_width=True)

                            if sheet:
                                sheet.append_rows(data_list)
                            
                            # Excel formatting (Double line/Wrap)
                            out = BytesIO()
                            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                                df.to_excel(writer, index=False, header=False, sheet_name='ZenithData')
                                workbook = writer.book
                                worksheet = writer.sheets['ZenithData']
                                wrap_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                                worksheet.set_column('B:B', 45, wrap_fmt)
                                worksheet.set_column('A:A', 8)
                                worksheet.set_column('C:G', 15)
                            
                            st.download_button("📥 Download Pro Excel", out.getvalue(), "DataSnap_Zenith.xlsx")
                        else:
                            st.error("AI error: Format not supported.")
                    except Exception as e:
                        st.error(f"Limit Error: {e}")