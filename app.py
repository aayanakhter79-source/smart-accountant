import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import json
from datetime import datetime

# --- 1. CONFIG & UI ---
st.set_page_config(page_title="DataSnap AI GST Engine", layout="wide")
st.markdown("<style>.stApp{background:#0b0e14;color:white;}</style>", unsafe_allow_html=True)

# --- 2. LOGIN (Tera Screen Lock) ---
if 'login' not in st.session_state: st.session_state['login'] = False
if not st.session_state['login']:
    st.title("🔐 DataSnap AI Lock")
    p = st.text_input("Enter Access Password", type="password")
    if st.button("Unlock"):
        if p == st.secrets["ADMIN_PASSWORD"]: 
            st.session_state['login'] = True
            st.rerun()
    st.stop()

# --- 3. AUTOMATIC MODEL FINDER (Jo Tune Manga) ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:
    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    sel_m = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0]
    model = genai.GenerativeModel(sel_m)
except Exception as e:
    st.error(f"AI Connection Error: {e}")

# --- 4. GOOGLE SHEET CONNECT ---
def get_sheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        return gspread.authorize(creds).open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
    except: return None

# --- 5. MAIN APP ---
st.title("🤖 DataSnap AI Agent + GST Engine")

tab1, tab2 = st.tabs(["🚀 Smart Scan", "📜 Billing History"])

with tab1:
    up = st.file_uploader("Upload Bill/Invoice", type=['jpg','png','jpeg'])
    if up:
        img = Image.open(up)
        st.image(img, width=400)
        
        if st.button("🚀 Run GST Engine Analysis"):
            with st.spinner("AI Agent calculating taxes..."):
                # Ye hai hamara Powerful Prompt (GST Engine)
                prompt = """You are a GST Engine Expert. Analyze this invoice image.
                1. EXTRACT FULL DESCRIPTION: Do not cut any words.
                2. IDENTIFY GST SLAB: Identify if item is 5%, 12%, 18%, or 28% GST.
                3. CALCULATE TAX: Split GST into CGST (Half) and SGST (Half).
                4. FORMAT: Return ONLY as a JSON list of lists.
                
                Columns needed: [S.No, Description, HSN, Qty, Rate, Taxable_Amt, GST_%, CGST_Amt, SGST_Amt, Total]
                Include 'Subtotal', 'Total Tax', and 'Grand Total' as final rows.
                """
                
                resp = model.generate_content([prompt, img])
                try:
                    raw_data = resp.text.replace("```json","").replace("```","").strip()
                    data_list = json.loads(raw_data)
                    df = pd.DataFrame(data_list)
                    
                    st.success("✅ Analysis Complete with GST Engine")
                    st.dataframe(df, use_container_width=True)
                    
                    # Professional Excel Download
                    out = BytesIO()
                    with pd.ExcelWriter(out, engine='xlsxwriter') as wr:
                        df.to_excel(wr, index=False, header=False, sheet_name='GST_Report')
                    st.download_button("📥 Download GST Excel Report", out.getvalue(), "GST_Report_Pro.xlsx")
                    
                    # Sync to Sheet
                    gs = get_sheet()
                    if gs:
                        gs.append_rows(data_list)
                        st.toast("Data Synced! ☁️")
                        st.balloons()
                except:
                    st.warning("AI Formatting Error. Direct Data:")
                    st.code(resp.text)

with tab2:
    st.header("🔍 Monthly/Daily History")
    search_q = st.text_input("Enter Date or Vendor Name")
    if st.button("Find History"):
        gs = get_sheet()
        if gs:
            data = pd.DataFrame(gs.get_all_records())
            if not data.empty:
                res = data[data.astype(str).apply(lambda x: search_q.lower() in x.str.lower().values, axis=1)]
                st.dataframe(res)
            else: st.info("No data found.")

# --- SIDEBAR PLANS ---
st.sidebar.markdown("### 💎 DataSnap Plans")
st.sidebar.info("₹200 - 20 Scans\n₹1200 - Unlimited (Pro)\n₹5000 - Enterprise")