import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import time

# --- CONFIG ---
st.set_page_config(page_title="DataSnap AI - GST Agent", layout="wide")

# Secrets se keys uthana
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:
    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])
except: 
    st.error("AI Model Error. Please check Gemini API Key.")

# --- GOOGLE SHEETS SETUP ---
def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        # Yahan .sheet1 ki jagah pehla worksheet uthayega taaki tab name ka issue na ho
        return client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).get_worksheet(0)
    except:
        return None

# --- SESSION STATE ---
if "invoice_data" not in st.session_state:
    st.session_state.invoice_data = []

def safe_json(text):
    # JSON extract karne ke liye clean up
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(text)
    except:
        return None

# --- UI ---
st.title("🚀 DataSnap AI - GST Accountant Agent V3")

sheet = get_gsheet()

# Sidebar for Shop Details
with st.sidebar:
    st.header("🏢 Business Profile")
    shop_name = st.text_input("Shop Name", value="My Store")
    month = st.text_input("Reporting Month", value="February 2026")
    if st.button("Clear All Data"):
        st.session_state.invoice_data = []
        st.rerun()

# Tabs
t1, t2, t3 = st.tabs(["📤 Upload & Scan", "📊 Dashboard", "📜 History"])

with t1:
    files = st.file_uploader("Upload Invoices (Multiple Allowed)", type=["jpg","jpeg","png"], accept_multiple_files=True)
    
    if st.button("📊 Start AI Processing"):
        if files:
            for file in files:
                with st.spinner(f"Processing {file.name}..."):
                    image = Image.open(file)
                    
                    # POWER PROMPT (Added GSTIN focus)
                    prompt = """
                    Extract all GST invoice details with 100% accuracy.
                    Return ONLY a JSON list of objects:
                    [{
                      "Invoice No": "str",
                      "Date": "DD-MM-YYYY",
                      "Party Name": "str",
                      "GSTIN": "15-digit alphanumeric code of Supplier",
                      "HSN": "str",
                      "Taxable Value": float,
                      "CGST": float,
                      "SGST": float,
                      "IGST": float,
                      "Total": float
                    }]
                    Rules: Extract Supplier GSTIN strictly. No explanation.
                    """ 
                    
                    # --- AI GENERATION (Missing lines added back) ---
                    response = model.generate_content([prompt, image])
                    data = safe_json(response.text)
                    
                    if data:
                        st.session_state.invoice_data.extend(data)
                        if sheet:
                            for d in data:
                                try:
                                    sheet.append_row(list(d.values()))
                                except Exception as e:
                                    st.error(f"Sheet Append Error: {e}")
                    else:
                        st.error(f"AI couldn't read {file.name} properly.")
                        
                    time.sleep(1) # Rate limit protection
            st.success("✅ All Invoices Processed!")
        else:
            st.warning("Pehle photo toh upload karo bhai!")

with t2:
    if st.session_state.invoice_data:
        df = pd.DataFrame(st.session_state.invoice_data)
        
        # Clean Data
        num_cols = ["Taxable Value","CGST","SGST","IGST","Total"]
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)

        # Metrics
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Invoices", len(df))
        c2.metric("Taxable Amt", f"₹{df['Taxable Value'].sum():,.2f}")
        c3.metric("Total Tax", f"₹{(df['CGST']+df['SGST']+df['IGST']).sum():,.2f}")
        c4.metric("Grand Total", f"₹{df['Total'].sum():,.2f}")

        # Party-wise Summary
        st.subheader("👥 Party-wise Summary")
        party_df = df.groupby("Party Name")[["Taxable Value", "Total"]].sum().reset_index()
        st.table(party_df)

        # Detailed Table
        st.subheader("📄 Item-wise Details")
        st.dataframe(df, use_container_width=True)

        # Excel Export Logic
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name="Invoice_Details")
            
            party_summary = df.groupby("Party Name")[["Taxable Value", "CGST", "SGST", "IGST", "Total"]].sum().reset_index()
            party_summary.to_excel(writer, index=False, sheet_name="Party_Summary")
            
            summary_df = pd.DataFrame({
                "Parameter": ["Shop", "Month", "Count", "Taxable", "GST", "Total"],
                "Value": [shop_name, month, len(df), df["Taxable Value"].sum(), (df["CGST"]+df["SGST"]+df["IGST"]).sum(), df["Total"].sum()]
            })
            summary_df.to_excel(writer, index=False, sheet_name="Overall_Summary")
            
            # Formatting
            workbook = writer.book
            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#4F81BD', 'font_color': 'white'})
            for sn in ["Invoice_Details", "Party_Summary", "Overall_Summary"]:
                ws = writer.sheets[sn]
                ws.set_column('A:Z', 18)

        st.download_button(label="📥 Download Professional GST Report", data=output.getvalue(), file_name=f"GST_Report_{shop_name}.xlsx")
    else:
        st.info("Scanner tab mein photo upload karke scan karein.")

with t3:
    st.subheader("📜 History (Direct from Sheet)")
    if sheet:
        try:
            history = pd.DataFrame(sheet.get_all_records())
            st.dataframe(history.iloc[::-1], use_container_width=True)
        except:
            st.info("Sheet khali hai ya connect nahi hui.")