import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import json
from datetime import datetime

# --- CONFIG & UI ---
st.set_page_config(page_title="DataSnap AI Agent PRO", layout="wide")
st.markdown("<style>.stApp{background:#0b0e14;color:white;}</style>", unsafe_allow_html=True)

# --- LOGIN ---
if 'login' not in st.session_state: st.session_state['login'] = False
if not st.session_state['login']:
    st.title("🔐 AI Agent Portal")
    p = st.text_input("Access Key", type="password")
    if st.button("Unlock"):
        if p == st.secrets["ADMIN_PASSWORD"]: 
            st.session_state['login'] = True
            st.rerun()
    st.stop()

# --- AGENT SETUP ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:
    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])
except: st.error("AI Error")

# --- GOOGLE SHEET SYNC FUNCTION ---
def sync_to_google(data_list):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        # Apni Sheet ID check kar lena secrets mein sahi hai na
        sheet = client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
        sheet.append_rows(data_list)
        return True
    except Exception as e:
        st.error(f"Sync Error: {e}")
        return False

# --- AGENT BRAIN ---
def process_with_ai_agent(image):
    today = datetime.now().strftime("%d-%m-%Y")
    # Description fix karne ke liye instruction:
    agent_instruction = f"""
    You are an AI Digital Accountant. Analyze this invoice image.
    1. EXTRACT FULL DESCRIPTION: Do not shorten or truncate product names. Extract the COMPLETE text for each item.
    2. Extract: S.No, HSN, Qty, Rate, GST %, Amount.
    3. Mathematical Check: Subtotal, CGST (9%), SGST (9%), Grand Total.
    
    OUTPUT FORMAT: Return ONLY a JSON list of lists.
    Format example:
    [
        ["BUSINESS REPORT", "VENDOR NAME", "", "", "", "", ""],
        ["DATE: {today}", "", "", "", "", "", ""],
        ["", "", "", "", "", "", ""],
        ["S.No", "Description", "HSN", "Qty", "Rate", "GST %", "Amount"],
        ["1", "FULL PRODUCT NAME HERE WITHOUT CUTTING", "HSNCODE", "1", "100", "18%", "118"],
        ["Subtotal", "", "", "", "", "", "TotalValue"],
        ["CGST", "9%", "", "", "", "", "TaxValue"],
        ["SGST", "9%", "", "", "", "", "TaxValue"],
        ["GRAND TOTAL", "", "", "", "", "", "FinalValue"]
    ]
    """
    response = model.generate_content([agent_instruction, image])
    return response.text

# --- APP MAIN ---
st.title("🤖 DataSnap AI Agent V9")
up = st.file_uploader("Upload Invoice", type=['jpg','png','jpeg'])

if up:
    img = Image.open(up)
    st.image(img, width=400)
    if st.button("🚀 Full Analysis Start"):
        with st.spinner("AI Agent is reading full descriptions..."):
            raw_res = process_with_ai_agent(img)
            try:
                clean_json = raw_res.replace("```json","").replace("```","").strip()
                data = json.loads(clean_json)
                df = pd.DataFrame(data)
                
                st.subheader("📋 Professional Report Preview")
                st.dataframe(df, use_container_width=True)
                
                # Excel Build
                out = BytesIO()
                with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                    df.to_excel(wr, index=False, header=False, sheet_name='GST_Report')
                
                st.download_button("📥 Download Full GST Excel", out.getvalue(), "AI_GST_Report_Full.xlsx")
                
                # Google Sheet Sync
                if sync_to_google(data):
                    st.success("✅ Full Data Synced to Google Sheets!")
                    st.balloons()
                else:
                    st.warning("⚠️ Excel ready, but Google Sheet sync failed.")
                    
            except Exception as e:
                st.error("Format Error. Please try a clearer photo.")
                st.write(raw_res)

# --- PLANS ---
st.sidebar.title("💎 Business Plans")
st.sidebar.info("₹200 - 20 Scans\n₹1200 - Unlimited\n₹5000 - Enterprise")