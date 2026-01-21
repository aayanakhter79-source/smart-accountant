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
        # GPT style Mode Selection
        mode = st.radio("🧠 Select Task Type", ["📊 Data Entry Only", "🧾 GST Invoice Mode"])
        st.info(f"Current Mode: {mode}")

    with c1:
        up = st.file_uploader("Upload Image", type=['jpg','png','jpeg'])
        if up:
            img = Image.open(up)
            st.image(img, width=450)
            
            if st.button("🚀 Process & Save Data"):
                with st.spinner("AI is analyzing based on selected mode..."):
                    
                    # LOGIC: Agar mode GST hai toh tax extraction mandatory hai
                    if mode == "🧾 GST Invoice Mode":
                        prompt = """TASK: GST EXTRACTION.
                        Rules:
                        1. Even if GST is not mentioned in image, CALCULATE 18% GST logically.
                        2. ROW 1: ["SHOP NAME", "Found Name", "DATE", "Found Date", "", "", ""]
                        3. ROW 2: ["S.No", "Description", "HSN", "Qty", "Rate", "GST %", "Amount"]
                        4. Extract all items. Description must be VERY DETAILED (double line style).
                        5. Add FINAL ROWS for: CGST, SGST, and GRAND TOTAL.
                        Return ONLY JSON list of lists."""
                    else:
                        # Simple Data Entry Mode
                        prompt = """TASK: SIMPLE DATA ENTRY.
                        Rules:
                        1. Extract all tabular data as it is.
                        2. Do not add extra tax rows unless they are in the image.
                        3. Keep descriptions extremely detailed.
                        4. Return ONLY JSON list of lists."""

                    try:
                        response = model.generate_content([prompt, img])
                        data_list = safe_json_load(response.text)

                        if data_list:
                            df = pd.DataFrame(data_list)
                            st.success(f"✅ {mode} Completed Successfully!")
                            st.dataframe(df, use_container_width=True)

                            if sheet:
                                sheet.append_rows(data_list)
                            
                            # --- EXCEL PRO FORMATTING ---
                            out = BytesIO()
                            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                                df.to_excel(writer, index=False, header=False, sheet_name='ZenithData')
                                workbook = writer.book
                                worksheet = writer.sheets['ZenithData']
                                wrap_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top'})
                                worksheet.set_column('B:B', 45, wrap_fmt) # Description wrap
                                worksheet.set_column('A:A', 8)
                                worksheet.set_column('C:G', 15)
                            
                            st.download_button("📥 Download Pro Excel", out.getvalue(), "DataSnap_Zenith.xlsx")
                    except Exception as e:
                        st.error(f"Error: {e}")

with t2:
    st.subheader("📜 Recent History (Newest on Top)")
    if sheet:
        raw = sheet.get_all_values()
        if raw:
            st.dataframe(pd.DataFrame(raw).iloc[::-1], height=600, use_container_width=True)