import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import re
import time

# --- CONFIG ---
st.set_page_config(page_title="DataSnap AI - GST Agent V7", layout="wide")

# API Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:

    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]

    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])

except: st.error("AI Error")



# --- LOGIN SYSTEM ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        st.title("🔐 DataSnap Private Access")
        pwd = st.text_input("Bhai, Access Password dalo:", type="password")
        if st.button("Login"):
            # Secrets mein APP_PASSWORD hona chahiye, nahi toh default 'admin123'
            master_pwd = st.secrets.get("APP_PASSWORD", "admin123")
            if pwd == master_pwd:
                st.session_state["password_correct"] = True
                st.rerun()
            else:
                st.error("😕 Galat Password hai bhai!")
        return False
    return True

# --- GOOGLE SHEETS ---
def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).get_worksheet(0)
    except:
        return None

# --- HELPERS ---
def safe_json(text):
    text = text.replace("```json","").replace("```","").strip()
    try:
        return json.loads(text)
    except:
        return None

def is_valid_gst(g):
    if not g or str(g).strip() == "" or str(g).lower() == "nan": return False
    # Simple regex for Indian GST
    return bool(re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$', str(g).strip().upper()))

# --- MAIN APP ---
if check_password():
    sheet = get_gsheet()
    if "invoice_data" not in st.session_state:
        st.session_state.invoice_data = []

    st.title("🚀 DataSnap AI - GST Agent V7")

    with st.sidebar:
        st.header("🏢 Business Profile")
        shop_name = st.text_input("Shop Name", "My Store")
        month = st.text_input("Reporting Month", "February 2026")
        if st.button("Clear All Data"):
            st.session_state.invoice_data = []
            st.rerun()
        if st.button("Logout"):
            st.session_state["password_correct"] = False
            st.rerun()

    t1, t2, t3 = st.tabs(["📤 Upload & Scan", "📊 Dashboard", "📜 History"])

    with t1:
        files = st.file_uploader("Upload Invoices", type=["jpg","jpeg","png"], accept_multiple_files=True)
        if st.button("📊 Start AI Processing"):
            if files:
                for file in files:
                    with st.spinner(f"Processing {file.name}..."):
                        img = Image.open(file)
                        prompt = """
                        Extract all Indian GST invoice details. Return ONLY a JSON list:
                        [{
                          "Invoice No": "str", "Date": "DD-MM-YYYY", "Party Name": "str", 
                          "GSTIN": "15-digit code", "HSN": "str", "Taxable Value": 0.0, 
                          "CGST": 0.0, "SGST": 0.0, "IGST": 0.0, "Total": 0.0
                        }]
                        Note: Extract Supplier GSTIN. If not found, keep "GSTIN": "".
                        """
                        response = model.generate_content([prompt, img])
                        data = safe_json(response.text)
                        if data:
                            st.session_state.invoice_data.extend(data)
                            if sheet:
                                for d in data:
                                    sheet.append_row(list(d.values()))
                        time.sleep(1)
                st.success("✅ Scanning Complete!")
            else: st.warning("Photo upload karo bhai!")

    with t2:
        if st.session_state.invoice_data:
            df = pd.DataFrame(st.session_state.invoice_data)
            # Numeric Fix
            for c in ["Taxable Value","CGST","SGST","IGST","Total"]:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

            # Dashboard Metrics
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Invoices", len(df))
            m2.metric("Taxable", f"₹{df['Taxable Value'].sum():,.2f}")
            m3.metric("Total Tax", f"₹{(df['CGST']+df['SGST']+df['IGST']).sum():,.2f}")
            m4.metric("Grand Total", f"₹{df['Total'].sum():,.2f}")

            # Smart Separation
            df["Type"] = df["GSTIN"].apply(lambda x: "B2B" if is_valid_gst(x) else "B2C")

            st.subheader("📄 Item-wise Details")
            st.dataframe(df, use_container_width=True)

            # --- PROFESSIONAL EXCEL ---
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # Sheet 1: All Data
                df.to_excel(writer, index=False, sheet_name="All_Invoices")
                
                # Sheet 2: B2B (Jisme GST hai)
                df[df["Type"]=="B2B"].to_excel(writer, index=False, sheet_name="B2B_Report")
                
                # Sheet 3: B2C (Jisme GST nahi hai)
                df[df["Type"]=="B2C"].to_excel(writer, index=False, sheet_name="B2C_Report")
                
                # Sheet 4: Final Summary
                summary_df = pd.DataFrame({
                    "Parameter": ["Shop", "Month", "Total Bills", "Taxable Total", "GST Total", "Grand Total"],
                    "Value": [shop_name, month, len(df), df["Taxable Value"].sum(), (df["CGST"]+df["SGST"]+df["IGST"]).sum(), df["Total"].sum()]
                })
                summary_df.to_excel(writer, index=False, sheet_name="Final_Summary")
                
                # Formatting
                workbook = writer.book
                header_fmt = workbook.add_format({'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white', 'border': 1})
                for sn in writer.sheets:
                    ws = writer.sheets[sn]
                    ws.set_column('A:Z', 20)

            st.download_button("📥 Download GST Report", output.getvalue(), file_name=f"{shop_name}_Report.xlsx")
        else: st.info("Upload tab mein scan karein.")

    with t3:
        st.subheader("📜 History (From Cloud)")
        if sheet:
            try:
                # Using values to avoid header issues
                vals = sheet.get_all_values()
                if len(vals) > 1:
                    h_df = pd.DataFrame(vals[1:], columns=vals[0])
                    st.dataframe(h_df.iloc[::-1].head(50), use_container_width=True)
                else: st.info("History khali hai.")
            except: st.error("Cloud Connection Error.")