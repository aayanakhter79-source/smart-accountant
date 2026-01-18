import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# --- CONFIG ---
st.set_page_config(page_title="DataSnap AI v2 - Zenith", layout="wide")

# API Keys
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

# --- JSON AUTO-REPAIR FUNCTION ---
def safe_json_load(text):
    text = text.replace("```json","").replace("```","").strip()
    try:
        return json.loads(text)
    except:
        # Basic repair for trailing commas or missing brackets
        try:
            fixed_text = text.replace(",]", "]").replace(",}", "}")
            return json.loads(fixed_text)
        except: return None

# --- MAIN UI ---
st.markdown("<h1 style='text-align: center; color: #00ced1;'>📸 DataSnap AI Pro </h1>", unsafe_allow_html=True)
t1, t2 = st.tabs(["🚀 Smart Scanner", "📜 Data History"])

with t1:
    col1, col2 = st.columns([2, 1])
    with col2:
        mode = st.radio("🧠 AI Mode", ["🤖 Auto Detect", "📊 Data Entry", "🧾 GST Pro"], horizontal=False)
        # Scan Counter Logic
        sheet = get_gsheet()
        if sheet:
            total_rows = len(sheet.get_all_values()) - 1
            st.metric("Total AI Scans Done", f"{total_rows}")

    with col1:
        up = st.file_uploader("Upload Image (Bill/Register)", type=['jpg','png','jpeg'])
        if up:
            img = Image.open(up)
            st.image(img, width=450)
            
            if st.button("🚀 Process & Sync Data"):
                with st.spinner("Zenith AI Engine is extracting data..."):
                    # Standard Prompt with Reset S.No Logic
                    prompt = """Extract data from this image.
                    RULES:
                    1. If it's a bill: Row 1 must be [SHOP NAME, Value, DATE, Value, '', '', ''].
                    2. Data Rows must start with S.No 1 for THIS specific image.
                    3. Standard Columns: [S.No, Description, HSN, Qty, Rate, GST %, Amount].
                    4. Return ONLY a valid JSON list of lists."""

                    response = model.generate_content([prompt, img])
                    data_list = safe_json_load(response.text)

                    if data_list:
                        df = pd.DataFrame(data_list)
                        st.success("✅ Data Extracted Successfully")
                        st.dataframe(df, use_container_width=True)

                        # Save to G-Sheet
                        if sheet:
                            sheet.append_rows(data_list)
                            st.toast("Synced to Cloud!", icon="☁️")

                        # Excel Export with Width Fix
                        out = BytesIO()
                        with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                            df.to_excel(writer, index=False, header=False, sheet_name='DataSnap_Export')
                            worksheet = writer.sheets['DataSnap_Export']
                            worksheet.set_column('B:B', 60) # Super wide for descriptions
                        st.download_button("📥 Download Excel Report", out.getvalue(), "DataSnap_Report.xlsx")
                    else:
                        st.error("AI couldn't format JSON. Please try a clearer image.")

with t2:
    st.subheader("📜 Recent History (Newest First)")
    sheet = get_gsheet()
    if sheet:
        raw_history = sheet.get_all_values()
        if len(raw_history) > 1:
            # Reverse only the data rows, keeping header logic intact
            # Note: Since each invoice has its own mini-header (Shop name), 
            # we show the full raw data reversed
            df_hist = pd.DataFrame(raw_history[1:]) 
            st.dataframe(df_hist.iloc[::-1], height=600, use_container_width=True)
        else:
            st.info("No scans found yet.")