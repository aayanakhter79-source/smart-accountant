import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import re

# --- 1. LUXURY DARK UI ---
st.set_page_config(page_title="DataSnap AI", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0e1117; }
    h1, h2, h3 { color: #00ced1 !important; font-family: 'Trebuchet MS'; }
    .stButton>button { 
        background: linear-gradient(45deg, #6200ea, #03dac6); 
        color: white; border-radius: 10px; border: none; font-weight: bold; height: 3em; width: 100%;
    }
    .status-box { padding: 20px; border-radius: 15px; background: #161b22; border: 1px solid #6200ea; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. AI SETUP ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:
    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    sel_m = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0]
    model = genai.GenerativeModel(sel_m)
except:
    st.error("AI Model connect nahi ho raha. Key check karein.")

# --- 3. GOOGLE SHEETS ---
def save_to_sheet(data_row):
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
        sheet.append_row(data_row)
        return True
    except: return False

# --- 4. MAIN APP ---
st.title("📸 DataSnap AI Professional")

tab1, tab2, tab3 = st.tabs(["🚀 Scanner", "💎 Subscriptions", "🔐 Admin"])

with tab1:
    uploaded_file = st.file_uploader("Upload Bill/Data Image", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, width=400)
        
        if st.button("Extract & Process Data"):
            with st.spinner("AI Calculating & Formatting..."):
                prompt = """Extract data from this image. 
                If it's an invoice, find: Date, Vendor, GST_No, Total_Amount.
                If it's a table, extract all rows.
                Format the output as a clean table with | separator. 
                Example: Date | Vendor | GST | Total"""
                
                response = model.generate_content([prompt, img])
                res = response.text
                st.markdown("### 📋 Extracted Results")
                st.code(res)

                # --- EXCEL LOGIC ---
                # Text ko rows mein todna
                lines = [l.split('|') for l in res.split('\n') if '|' in l]
                if lines:
                    df = pd.DataFrame(lines)
                    
                    # Excel Download
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, header=False)
                    
                    st.download_button("📥 Download Excel Report", output.getvalue(), "DataSnap_Report.xlsx")
                    
                    # Sync to Google Sheet
                    if save_to_sheet(lines[0]):
                        st.success("Data Saved to Cloud Sheet! ✅")
                    else:
                        st.warning("Google Sheet sync failed. Share settings check karein.")

with tab2:
    st.header("Subscription Plans")
    col1, col2, col3 = st.columns(3)
    col1.metric("Starter", "₹200", "20 Scans")
    col2.metric("Pro", "₹1200", "Unlimited")
    col3.metric("Enterprise", "₹5000", "Multi-user")
    st.image(f"https://api.qrserver.com/v1/create-qr-code/?size=150x150&data=upi://pay?pa=YOUR_UPI@okaxis")

with tab3:
    passw = st.text_input("Admin Password", type="password")
    if passw == st.secrets["ADMIN_PASSWORD"]:
        st.write("Welcome Hussain Bhai! Aapka database ready hai.")