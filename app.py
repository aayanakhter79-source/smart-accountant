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
st.set_page_config(page_title="DataSnap AI - GST Agent V6", layout="wide")

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
            if pwd == st.secrets.get("APP_PASSWORD", "admin123"): # Default agar secret bhul jao
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
    if not g or str(g).strip() == "" or str(g).lower() == "nan": return False
    pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$'
    return bool(re.match(pattern, str(g).strip().upper()))

# --- MAIN APP ---
if check_password():
    sheet = get_gsheet()
    
    if "invoice_data" not in st.session_state:
        st.session_state.invoice_data = []

    st.title("🚀 DataSnap AI - GST Pro V6")

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

    t1, t2, t3 = st.tabs(["📤 Upload & Scan", "📊 Smart Dashboard", "📜 History"])

    # ---------------- UPLOAD TAB ----------------
    with t1:
        files = st.file_uploader("Upload GST Invoices", type=["jpg","jpeg","png"], accept_multiple_files=True)

        if st.button("Start AI Processing"):
            if files:
                for file in files:
                    with st.spinner(f"Processing {file.name}..."):
                        img = Image.open(file)
                        prompt = """
                        Extract Indian GST Invoice details. Return ONLY a JSON list:
                        [{
                        "Invoice No":"", "Date":"", "Party Name":"", "GSTIN":"",
                        "HSN":"", "Taxable Value":0, "CGST":0, "SGST":0, "IGST":0, "Total":0
                        }]
                        Note: Extract Supplier GSTIN. If missing, leave empty. No extra text.
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
            else:
                st.warning("File toh upload karo!")

    # ---------------- DASHBOARD TAB ----------------
    with t2:
        if st.session_state.invoice_data:
            df = pd.DataFrame(st.session_state.invoice_data)
            num_cols = ["Taxable Value","CGST","SGST","IGST","Total"]
            for c in num_cols: df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

            # Metrics (Vapas 4 Columns mein)
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Invoices", len(df))
            m2.metric("Taxable Amt", f"₹{df['Taxable Value'].sum():,.2f}")
            m3.metric("Total Tax", f"₹{(df['CGST']+df['SGST']+df['IGST']).sum():,.2f}")
            m4.metric("Grand Total", f"₹{df['Total'].sum():,.2f}")

            # Smart Logic
            df["GSTIN Valid"] = df["GSTIN"].apply(valid_gstin)
            df["Invoice Type"] = df["GSTIN"].apply(lambda x: "B2B" if valid_gstin(x) else "B2C")

            st.subheader("📝 Item-wise Preview")
            st.dataframe(df, use_container_width=True)

            # Excel Export
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index=False, sheet_name="All_Invoices")
                df[df["Invoice Type"]=="B2B"].to_excel(writer, index=False, sheet_name="B2B")
                df[df["Invoice Type"]=="B2C"].to_excel(writer, index=False, sheet_name="B2C")
                
                summary_df = pd.DataFrame({
                    "Parameter": ["Shop", "Month", "Total Bills", "Taxable Sum", "GST Sum", "Final Total"],
                    "Value": [shop_name, month, len(df), df["Taxable Value"].sum(), (df["CGST"]+df["SGST"]+df["IGST"]).sum(), df["Total"].sum()]
                })
                summary_df.to_excel(writer, index=False, sheet_name="Final_Summary")

            st.download_button("📥 Download GST Report", output.getvalue(), file_name=f"DataSnap_{shop_name}.xlsx")
        else:
            st.info("Pehle Upload tab use karein.")

    # ---------------- HISTORY TAB (VAPAS AAYA) ----------------
    with t3:
        st.subheader("📜 Last 50 Scans (Cloud Backup)")
        if sheet:
            try:
                history_data = sheet.get_all_values()
                if len(history_data) > 1:
                    hist_df = pd.DataFrame(history_data[1:], columns=history_data[0])
                    st.dataframe(hist_df.iloc[::-1].head(50), use_container_width=True)
                else:
                    st.info("Cloud mein abhi koi data nahi hai.")
            except:
                st.error("Sheet connect nahi ho saki.")