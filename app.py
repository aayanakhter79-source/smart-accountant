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
st.set_page_config(page_title="DataSnap AI - GST Agent V5", layout="wide")

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
            if pwd == st.secrets["APP_PASSWORD"]:
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

# --- HELPER FUNCTIONS ---
def safe_json(text):
    text = text.replace("```json","").replace("```","").strip()
    try:
        return json.loads(text)
    except:
        return None

def valid_gstin(g):
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$'
    return bool(re.match(pattern, str(g or "")))

# --- MAIN APP ---
if check_password():
    sheet = get_gsheet()
    
    if "invoice_data" not in st.session_state:
        st.session_state.invoice_data = []

    st.title("🚀 DataSnap AI - GST Filing Ready V5")

    with st.sidebar:
        st.header("🏢 Business Profile")
        shop_name = st.text_input("Shop Name", "My Store")
        month = st.text_input("Month", "Feb 2026")
        if st.button("Clear All Data"):
            st.session_state.invoice_data = []
            st.rerun()
        if st.button("Logout"):
            st.session_state["password_correct"] = False
            st.rerun()

    t1, t2 = st.tabs(["📤 Upload & Scan", "📊 Smart Dashboard"])

    # ---------------- UPLOAD TAB ----------------
    with t1:
        files = st.file_uploader("Upload GST Invoices", type=["jpg","jpeg","png"], accept_multiple_files=True)

        if st.button("Start AI Processing"):
            if files:
                for file in files:
                    with st.spinner(f"Processing {file.name}..."):
                        img = Image.open(file)
                        prompt = """
                        You are an Indian GST expert AI. Extract details from this Indian invoice.
                        Return ONLY JSON list:
                        [{
                        "Invoice No":"", "Date":"", "Party Name":"", "GSTIN":"",
                        "HSN":"", "Taxable Value":0, "CGST":0, "SGST":0, "IGST":0, "Total":0
                        }]
                        Rules: Extract Supplier GSTIN. If CGST/SGST missing but IGST present, extract accordingly.
                        """
                        response = model.generate_content([prompt, img])
                        data = safe_json(response.text)

                        if data:
                            st.session_state.invoice_data.extend(data)
                            if sheet:
                                for d in data:
                                    sheet.append_row(list(d.values()))
                        time.sleep(1)
                st.success("✅ Saare bills scan ho gaye!")
            else:
                st.warning("Pehle file toh dalo!")

    # ---------------- DASHBOARD TAB ----------------
    with t2:
        if st.session_state.invoice_data:
            df = pd.DataFrame(st.session_state.invoice_data)

            # Data Cleaning & Logic
            num_cols = ["Taxable Value","CGST","SGST","IGST","Total"]
            for c in num_cols:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

            df["Duplicate"] = df.duplicated(subset=["Invoice No","Date"], keep=False)
            df["GSTIN Valid"] = df["GSTIN"].apply(valid_gstin)
            df["Invoice Type"] = df["GSTIN"].apply(lambda x: "B2B" if valid_gstin(x) else "B2C")

            # Metrics
            c1,c2,c3,c4 = st.columns(4)
            c1.metric("Total Invoices", len(df))
            c2.metric("Taxable Amt", f"₹{df['Taxable Value'].sum():,.2f}")
            c3.metric("Total GST", f"₹{(df['CGST']+df['SGST']+df['IGST']).sum():,.2f}")
            c4.metric("Grand Total", f"₹{df['Total'].sum():,.2f}")

            # Alerts
            if df["Duplicate"].any() or not df["GSTIN Valid"].all():
                st.warning(f"⚠️ Dhayan dein: {df['Duplicate'].sum()} Duplicate bills aur {(~df['GSTIN Valid']).sum()} Invalid GSTIN mile hain!")

            st.subheader("📝 Live Data Preview")
            st.dataframe(df, use_container_width=True)

            # Excel Export
            b2b = df[df["Invoice Type"]=="B2B"]
            b2c = df[df["Invoice Type"]=="B2C"]

            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="All_Invoices")
                b2b.to_excel(writer, index=False, sheet_name="B2B_Report")
                b2c.to_excel(writer, index=False, sheet_name="B2C_Report")
                
                summary_df = pd.DataFrame({
                    "Metric": ["Shop", "Month", "Total Bills", "Taxable", "GST", "Total"],
                    "Value": [shop_name, month, len(df), df["Taxable Value"].sum(), (df["CGST"]+df["SGST"]+df["IGST"]).sum(), df["Total"].sum()]
                })
                summary_df.to_excel(writer, index=False, sheet_name="Summary")

            st.download_button("📥 Download GSTR-Ready Excel", output.getvalue(), file_name=f"DataSnap_{shop_name}_{month}.xlsx")
        else:
            st.info("Pehle Upload tab mein bills scan karein.")