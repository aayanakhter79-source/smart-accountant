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

except: st.error("AI Error")


# --- GOOGLE SHEETS SETUP ---
def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
    except:
        return None

# --- SESSION STATE ---
if "invoice_data" not in st.session_state:
    st.session_state.invoice_data = []

def safe_json(text):
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
                    prompt = """
Extract all GST invoice details with 100% accuracy.
Focus especially on the 'Party GSTIN' (The GST number of the supplier/party).

Return ONLY a JSON list of objects:
[
 {
  "Invoice No": "Search for Bill No/Inv No",
  "Date": "Format: DD-MM-YYYY",
  "Party Name": "Full Name of the Supplier",
  "GSTIN": "Look for a 15-digit alphanumeric code starting with State Code (e.g., 09, 07, 19, etc.)",
  "HSN": "Extract HSN code if available",
  "Taxable Value": 0,
  "CGST": 0,
  "SGST": 0,
  "IGST": 0,
  "Total": 0
 }
]

Rules:
1. If GSTIN is present on the bill, you MUST extract it.
2. Ensure all numeric values are numbers, not strings.
3. No explanation, only JSON.
""" 
                    
                    if data:
                        st.session_state.invoice_data.extend(data)
                        if sheet:
                            # Convert list of dicts to list of lists for GSheets
                            for d in data:
                                sheet.append_row(list(d.values()))
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

        
       # ---------------- PROFESSIONAL EXCEL EXPORT V4 ----------------
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            # 1. Detailed Invoice Sheet
            df.to_excel(writer, index=False, sheet_name="Invoice_Details")
            
            # 2. Party-wise Summary Sheet
            party_summary = df.groupby("Party Name")[["Taxable Value", "CGST", "SGST", "IGST", "Total"]].sum().reset_index()
            party_summary.to_excel(writer, index=False, sheet_name="Party_Summary")
            
            # 3. Final Report Summary
            summary_data = {
                "Report Parameter": ["Shop Name", "Report Month", "Total Invoices", "Total Taxable Value", "Total GST", "Grand Total"],
                "Details/Values": [
                    shop_name, 
                    month, 
                    len(df), 
                    df["Taxable Value"].sum(), 
                    (df["CGST"] + df["SGST"] + df["IGST"]).sum(), 
                    df["Total"].sum()
                ]
            }
            summary_df = pd.DataFrame(summary_data)
            summary_df.to_excel(writer, index=False, sheet_name="Overall_Summary")

            # --- FORMATTING MAGIC ---
            workbook  = writer.book
            header_fmt = workbook.add_format({'bold': True, 'font_color': 'white', 'bg_color': '#4F81BD', 'border': 1})
            num_fmt = workbook.add_format({'num_format': '₹ #,##0.00', 'border': 1})
            border_fmt = workbook.add_format({'border': 1})

            # Formatting Har Sheet ke liye
            for sheet_name in ["Invoice_Details", "Party_Summary", "Overall_Summary"]:
                ws = writer.sheets[sheet_name]
                curr_df = df if sheet_name=="Invoice_Details" else (party_summary if sheet_name=="Party_Summary" else summary_df)
                
                # Headers Format karna
                for col_num, value in enumerate(curr_df.columns.values):
                    ws.write(0, col_num, value, header_fmt)
                    ws.set_column(col_num, col_num, 22) # Column width set karna
                
                # Filters lagana (Detailed and Party sheet pe)
                if sheet_name != "Overall_Summary":
                    ws.autofilter(0, 0, len(curr_df), len(curr_df.columns) - 1)

        st.download_button(
            label="📥 Download Professional GST Report (v4)",
            data=output.getvalue(),
            file_name=f"DataSnap_GST_{shop_name}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )              
    else:
        st.info("Scanner tab mein photo upload karke scan karein.")

with t3:
    st.subheader("📜 Last Scanned Data (Google Sheets Sync)")
    if sheet:
        try:
            history = pd.DataFrame(sheet.get_all_values())
            st.dataframe(history.iloc[::-1], use_container_width=True)
        except:
            st.error("Google Sheet connect nahi ho rahi.")
    else:
        st.warning("Secrets mein Google Sheet ID daalein.")