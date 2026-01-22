import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# --- CONFIG ---
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

st.markdown("<h1 style='text-align: center; color: #00ced1;'>🚀 DataSnap AI Pro by ZENITH</h1>", unsafe_allow_html=True)
t1, t2 = st.tabs(["🚀 AI Scanner", "📜 Data History"])

with t1:
    sheet = get_gsheet()
    c1, c2 = st.columns([3, 1])
    with c2:
        mode = st.radio("🧠 Select Mode", ["📊 Data Entry Only", "🧾 GST Invoice Mode"])
    
    with c1:
        up = st.file_uploader("Upload Image", type=['jpg','png','jpeg'])
        if up:
            img = Image.open(up)
            st.image(img, width=450)
            
            if st.button("🚀 Process & Save Data"):
                with st.spinner("AI is Extracting Every Detail..."):
                    # --- POWER PROMPT ---
                    if mode == "🧾 GST Invoice Mode":
                        prompt = """Extract ALL data from this GST invoice. 
                        Return ONLY a JSON list of lists.
                        Include: ["SHOP NAME", "Name", "DATE", "Date", "", "", ""], 
                        ["S.No", "Description", "HSN", "Qty", "Rate", "GST %", "Amount"],
                        Then all items, then ["", "CGST", "", "", "", "", "Value"], 
                        ["", "SGST", "", "", "", "", "Value"], 
                        ["", "GRAND TOTAL", "", "", "", "", "Total"]."""
                    else:
                        prompt = """Extract ALL tables and text from this image as a structured table.
                        Return ONLY a JSON list of lists.
                        Capture every row and column. Keep descriptions very long and detailed."""

                    try:
                        response = model.generate_content([prompt, img])
                        # AI raw response se JSON nikalna
                        raw_text = response.text
                        data_list = safe_json_load(raw_text)

                        if data_list and len(data_list) > 0:
                            # Safai: Sabko text mein badlo
                            clean_data = [[str(c) if c else "" for c in row] for row in data_list]
                            df = pd.DataFrame(clean_data)
                            
                            st.success("✅ Data Extracted!")
                            st.dataframe(df, use_container_width=True)

                            if sheet:
                                sheet.append_rows(clean_data)
                                st.toast("Saved to Google Sheets!")

                            # Excel File Generation
                            out = BytesIO()
                            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                                df.to_excel(writer, index=False, header=False, sheet_name='Data')
                                workbook = writer.book
                                worksheet = writer.sheets['Data']
                                wrap_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                                worksheet.set_column('B:B', 50, wrap_fmt)
                                worksheet.set_column('A:A', 10)
                                worksheet.set_column('C:G', 15)
                            
                            st.download_button("📥 Download Excel", out.getvalue(), "DataSnap_Zenith_Final.xlsx")
                        else:
                            st.error("AI returned empty data. Please try a clearer image.")
                    except Exception as e:
                        st.error(f"Error: {e}")

with t2:
    if sheet:
        try:
            data = sheet.get_all_values()
            if data:
                st.dataframe(pd.DataFrame(data).iloc[::-1], height=500, use_container_width=True)
            else:
                st.info("No history yet.")
        except: st.warning("Syncing history...")