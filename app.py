import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
from io import BytesIO

# --- 1. CONFIG & SETUP ---
st.set_page_config(page_title="Zenith IN - DataSnap AI", layout="wide")

# API Setup
# --- API Setup (Correct Indentation) ---
try:
   	 all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
   	 model = genai.GenerativeModel('gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])
except Exception as e:
    st.error(f"⚠️ AI Setup Error: {e}")
# --- 2. ROBUST HELPERS ---
def safe_json(text):
    """AI ke kachre ko saaf karke pure JSON nikalta hai"""
    try:
        # Markdown blocks hatao
        clean_text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        # Agar AI ne list bhej di [{}], toh pehla element lo
        if isinstance(data, list) and len(data) > 0:
            return data[0]
        return data if isinstance(data, dict) else None
    except:
        return None

# --- 3. AGENTIC BRAIN ---
def agent_process(input_data, is_image=True):
    prompt = """
    You are the Zenith IN AI Tax Agent. 
    Analyze the provided invoice/data and return ONLY a single JSON object.
    
    FIELDS TO EXTRACT:
    - InvoiceNo, Date (DD-MM-YYYY), Party (Name).
    - Currency (Detect if USD, INR, EUR, etc.).
    - Amount_Original (Value in original currency).
    - Amount_INR (If Currency is NOT INR, convert at 1 USD = 83 INR, 1 EUR = 90 INR).
    - GST_Amount (18% of Amount_INR if Party/Service is Indian, else 0.0).
    - TDS_Suggestion (Suggest TDS section like 194J - 10% for professional fees).
    - AI_Note (Brief reasoning for your choice).

    STRICT JSON STRUCTURE EXAMPLE:
    {"InvoiceNo": "INV-001", "Date": "01-01-2026", "Party": "Name", "Currency": "USD", "Amount_Original": 100.0, "Amount_INR": 8300.0, "GST_Amount": 0.0, "TDS_Suggestion": "No TDS", "AI_Note": "Foreign payment"}
    """
    try:
        if is_image:
            response = model.generate_content([prompt, input_data])
        else:
            response = model.generate_content(prompt + f"\nData Sample: {input_data}")
        return safe_json(response.text)
    except Exception as e:
        st.error(f"AI Call failed: {e}")
        return None

# --- 4. MAIN INTERFACE ---
st.title("🚀 Zenith IN: DataSnap 2.1")
st.subheader("Autonomous Tax Agent for Creators")

if "invoice_data" not in st.session_state:
    st.session_state.invoice_data = []

# Sidebar
with st.sidebar:
    st.header("👤 Profile")
    st.write("**Company:** Zenith IN")
    if st.button("🗑️ Clear Dashboard"):
        st.session_state.invoice_data = []
        st.rerun()

t1, t2 = st.tabs(["📤 Upload", "📊 Dashboard"])

with t1:
    files = st.file_uploader("Upload Images/CSV", type=["jpg","png","jpeg","csv","xlsx"], accept_multiple_files=True)
    if st.button("📊 Audit with Zenith AI"):
        if files:
            for file in files:
                with st.spinner(f"Auditing {file.name}..."):
                    if file.name.endswith(('.csv', '.xlsx')):
                        df_raw = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
                        res = agent_process(df_raw.head(5).to_string(), is_image=False)
                    else:
                        img = Image.open(file)
                        res = agent_process(img, is_image=True)
                    
                    if res and isinstance(res, dict):
                        st.session_state.invoice_data.append(res)
                        st.toast(f"✅ Success: {file.name}")
                    else:
                        st.error(f"❌ AI couldn't read {file.name} properly.")
            st.success("Audit Cycle Complete!")

with t2:
    st.write("### 📊 Zenith IN: Professional Tax Ledger")
    if st.session_state.invoice_data:
        clean_list = [x for x in st.session_state.invoice_data if isinstance(x, dict)]
        if clean_list:
            df = pd.DataFrame(clean_list)
            
            # 1. Column Order Setup
            cols = ["InvoiceNo", "Date", "Party", "Currency", "Amount_Original", "Amount_INR", "GST_Amount", "TDS_Suggestion", "AI_Note"]
            for c in cols:
                if c not in df.columns: df[c] = "N/A"
            
            # 2. THE FIX: Column Configuration for Clarity
            st.data_editor(
                df[cols],
                column_config={
                    "InvoiceNo": st.column_config.TextColumn("Invoice #", width="small"),
                    "Date": st.column_config.TextColumn("Date", width="small"),
                    "Party": st.column_config.TextColumn("Client/Vendor", width="medium"),
                    "Currency": st.column_config.TextColumn("Curr.", width="extrasmall"),
                    "Amount_Original": st.column_config.NumberColumn("Original Amt", format="%.2f"),
                    "Amount_INR": st.column_config.NumberColumn("Amt (INR)", format="₹%.2f", width="medium"),
                    "GST_Amount": st.column_config.NumberColumn("GST (18%)", format="₹%.2f"),
                    "TDS_Suggestion": st.column_config.TextColumn("TDS Logic", width="medium"),
                    "AI_Note": st.column_config.TextColumn("AI Auditor Remarks", width="large"), # Remarks ko bada rakha hai
                },
                hide_index=True,
                use_container_width=True,
                key="zenith_editor"
            )
            
            # 3. Enhanced Excel Export
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df[cols].to_excel(writer, index=False, sheet_name='Zenith_Tax_Report')
                # Auto-adjust columns in Excel too
                worksheet = writer.sheets['Zenith_Tax_Report']
                for idx, col in enumerate(cols):
                    series = df[col].astype(str)
                    max_len = max(series.map(len).max(), len(col)) + 2
                    worksheet.set_column(idx, idx, max_len)
            
            st.download_button("📥 Download CA-Ready Excel Report", output.getvalue(), "Zenith_Audit_Report.xlsx")
        else:
            st.info("No valid data found.")
    else:
        st.info("Upload tab mein files process karein.")