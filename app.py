import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# --- CONFIG & API SETUP ---
st.set_page_config(page_title="DataSnap AI - Zenith", layout="wide")

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
    except Exception as e:
        return None

# --- FUNCTIONS ---
def detect_image_type(img):
    prompt = "Identify the image type. Options: 1. GST INVOICE, 2. DATA TABLE. Return only one word."
    r = model.generate_content([prompt, img])
    return r.text.strip().upper()

# --- MAIN UI ---
st.markdown("<h1 style='text-align: center; color: #00ced1;'>🚀 DataSnap AI by ZENITH</h1>", unsafe_allow_html=True)
t1, t2 = st.tabs(["🚀 AI Scanner", "📜 Recent History"])

with t1:
    # Mode Selection
    mode = st.radio("🧠 Select Mode", ["🤖 Auto Detect", "📊 Data Entry Only", "🧾 GST Invoice"], horizontal=True)
    
    up = st.file_uploader("Upload Image (Bill or Table)", type=['jpg','png','jpeg'])
    
    if up:
        img = Image.open(up)
        st.image(img, width=400)
        
        if st.button("🚀 Process & Save Data"):
            with st.spinner("Zenith AI is analyzing..."):
                
                # Step 1: Decide Mode
                final_mode = mode
                if mode == "🤖 Auto Detect":
                    detected = detect_image_type(img)
                    final_mode = "🧾 GST Invoice" if "GST" in detected else "📊 Data Entry Only"
                
                # Step 2: Processing based on Mode
                if final_mode == "🧾 GST Invoice":
                    prompt = """Analyze this invoice.
                    Rules:
                    1. ROW 1: ["SHOP NAME", "Full Shop Name Extracted", "DATE", "Bill Date", "", "", ""]
                    2. ROW 2: ["S.No", "Description", "HSN", "Qty", "Rate", "GST %", "Amount"]
                    3. EXTRACT ALL items with full descriptions.
                    4. CALCULATE: CGST (9%), SGST (9%), and Grand Total.
                    Return ONLY as a JSON list of lists."""
                else:
                    prompt = "Extract all tabular data from this image. Convert into rows and columns. Return ONLY a JSON list of lists."

                response = model.generate_content([prompt, img])
                
                try:
                    # Clean JSON
                    raw_data = response.text.replace("```json","").replace("```","").strip()
                    data_list = json.loads(raw_data)
                    df = pd.DataFrame(data_list)
                    
                    st.success(f"✅ {final_mode} Processed Successfully!")
                    st.dataframe(df)

                    # --- SAVE TO GOOGLE SHEET ---
                    sheet = get_gsheet()
                    if sheet:
                        sheet.append_rows(data_list)
                        st.info("📊 Data synced to Google Sheets!")

                    # --- EXCEL DOWNLOAD ---
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='DataSnap_Export')
                    st.download_button("📥 Download Excel Report", out.getvalue(), "DataSnap_Zenith.xlsx")

                except Exception as e:
                    st.error(f"Error reading data: {e}")

with t2:
    st.subheader("Last 10 Entries")
    sheet = get_gsheet()
    if sheet:
        history = sheet.get_all_records()
        if history:
            st.table(pd.DataFrame(history).tail(10))
        else:
            st.write("No history found.")
    else:
        st.error("Google Sheet not connected. Check your Secrets.")