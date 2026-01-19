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

# API Keys from Secrets
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

# --- GPT UPGRADE: SAFE JSON LOAD ---
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
t1, t2 = st.tabs(["🚀 AI Smart Scanner", "📜 History & Logs"])

with t1:
    sheet = get_gsheet()
    total_scans = 0
    if sheet:
        all_data = sheet.get_all_values()
        total_scans = sum(1 for row in all_data if "SHOP NAME" in row)

    c1, c2 = st.columns([3, 1])
    with c2:
        st.metric("Total Scans", total_scans)
        mode = st.radio("🧠 Mode", ["🤖 Auto Detect", "📊 Data Entry", "🧾 GST Mode"])
    
    with c1:
        up = st.file_uploader("Upload Image", type=['jpg','png','jpeg'])
        if up:
            img = Image.open(up)
            st.image(img, width=450)
            
            if st.button("🚀 Start Deep Extraction"):
                with st.spinner("AI is thinking..."):
                    prompt = """Analyze this image. 
                    Extract data in this JSON format:
                    {
                      "confidence": 95,
                      "data": [
                        ["SHOP NAME", "Name", "DATE", "Date", "", "", ""],
                        ["S.No", "Description", "HSN", "Qty", "Rate", "GST %", "Amount"],
                        ["1", "Detailed Description", "HSN", "Qty", "Rate", "GST", "Total"]
                      ]
                    }
                    Rules: 
                    - S.No starts from 1. 
                    - Detailed descriptions are mandatory.
                    - Total/GST rows at the end.
                    Return ONLY JSON."""

                    response = model.generate_content([prompt, img])
                    full_res = safe_json_load(response.text)

                    if full_res and "data" in full_res:
                        data_list = full_res["data"]
                        st.metric("AI Confidence", f"{full_res.get('confidence', 85)}%")
                        df = pd.DataFrame(data_list)
                        st.dataframe(df, use_container_width=True)

                        if sheet:
                            sheet.append_rows(data_list)
                            st.toast("Data Saved!")

                        # --- EXCEL DOUBLE LINE (WRAP) LOGIC ---
                        out = BytesIO()
                        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False, header=False, sheet_name='DataSnap')
                            workbook = writer.book
                            worksheet = writer.sheets['DataSnap']
                            
                            # Wrap Format define karna (Double lines ke liye)
                            wrap_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                            
                            # Column widths aur wrap apply karna
                            worksheet.set_column('B:B', 45, wrap_fmt) # Description box
                            worksheet.set_column('A:A', 10)
                            worksheet.set_column('C:G', 15)
                        
                        st.download_button("📥 Download Pro Excel", out.getvalue(), "DataSnap_Zenith_Pro.xlsx")
                    else:
                        st.error("AI breakdown. Clear image upload karein.")

with t2:
    st.subheader("📜 Recent History (Latest Scans First)")
    if sheet:
        try:
            raw_history = sheet.get_all_values()
            if len(raw_history) > 0:
                # Latest scan hamesha upar aayega
                df_history = pd.DataFrame(raw_history)
                st.dataframe(df_history.iloc[::-1], height=600, use_container_width=True)
            else:
                st.info("No scans yet.")
        except:
            st.warning("History sync ho rahi hai...")