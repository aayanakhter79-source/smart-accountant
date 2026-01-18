import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# --- CONFIG ---
st.set_page_config(page_title="DataSnap AI - Zenith", layout="wide")

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

# --- MAIN UI ---
st.markdown("<h1 style='text-align: center; color: #00ced1;'>📸 DataSnap AI by ZENITH</h1>", unsafe_allow_html=True)
t1, t2 = st.tabs(["🚀 Smart Scanner", "📜 Data History"])

with t1:
    # Scan Counter Metric
    sheet = get_gsheet()
    if sheet:
        all_vals = sheet.get_all_values()
        # Sirf "SHOP NAME" wali rows count karke real scans nikalte hain
        scan_count = sum(1 for row in all_vals if "SHOP NAME" in row)
        st.metric("Total Successful Scans", f"{scan_count}")

    up = st.file_uploader("Upload Image", type=['jpg','png','jpeg'])
    if up:
        img = Image.open(up)
        st.image(img, width=400)
        
        if st.button("🚀 Process & Save"):
            with st.spinner("Processing in your favourite format..."):
                # WAPAS PURANA POWERFUL PROMPT (Jisme description achi aati thi)
                prompt = """Analyze this image and return a JSON list of lists.
                Structure:
                Row 1: ["SHOP NAME", "Name", "DATE", "Date", "", "", ""]
                Row 2: ["S.No", "Description", "HSN", "Qty", "Rate", "GST %", "Amount"]
                Following Rows: Extract items. S.No must start from 1 for this image.
                Keep Descriptions VERY DETAILED.
                Final Rows: Add CGST, SGST, and Grand Total rows.
                Return ONLY the JSON list of lists."""

                response = model.generate_content([prompt, img])
                try:
                    raw_data = response.text.replace("```json","").replace("```","").strip()
                    data_list = json.loads(raw_data)
                    df = pd.DataFrame(data_list)
                    
                    st.success("✅ Excel Ready in Purana Style!")
                    st.dataframe(df)

                    if sheet:
                        sheet.append_rows(data_list)
                    
                    # --- PURANA EXCEL FORMATTING ---
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, header=False, sheet_name='DataSnap_Export')
                        worksheet = writer.sheets['DataSnap_Export']
                        # Column B (Description) ko extra wide karna
                        worksheet.set_column('B:B', 65)
                    st.download_button("📥 Download Excel (Purana Format)", out.getvalue(), "DataSnap_Report.xlsx")
                except:
                    st.error("AI breakdown. Please try again.")

with t2:
    st.subheader("📜 Recent History (Latest Scans First)")
    if sheet:
        data = sheet.get_all_values()
        if len(data) > 0:
            # Pura data dikhayenge bina header chhede, lekin reverse karke
            df_history = pd.DataFrame(data)
            # Latest entry upar dikhane ke liye reverse logic
            st.dataframe(df_history.iloc[::-1], height=600, use_container_width=True)
        else:
            st.info("No history yet.")