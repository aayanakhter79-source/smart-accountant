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
st.set_page_config(page_title="DataSnap AI - Freelancer Tax Agent", layout="wide")

# API Setup
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:

    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]

    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])

except: st.error("AI Error")



# --- HELPERS ---
def safe_json(text):
    text = text.replace("```json","").replace("```","").strip()
    try: return json.loads(text)
    except: return None

def is_valid_gst(g):
    if not g or str(g).strip() == "" or str(g).lower() == "nan": return False
    return bool(re.match(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[A-Z0-9]{1}Z[A-Z0-9]{1}$', str(g).strip().upper()))

# --- AGENTIC ENGINE (THE HEART) ---
def freelancer_agent_process(img, user_currency="INR"):
    prompt = f"""
    You are an AI Tax Consultant for Indian Freelancers/Creators. 
    Analyze this document and return ONLY a JSON object:
    
    1. EXTRACT: Invoice No, Date, Party Name, GSTIN (if any), Total Amount, Currency.
    2. CONVERSION: If Currency is NOT INR, estimate the INR value (Current approx rate).
    3. TAX LOGIC: 
       - If International: Mark as 'Export' (0% GST with LUT).
       - If Domestic: Apply GST rules.
    4. TDS: Suggest if TDS (e.g., 1%, 2%, 10%) should be deducted.
    
    JSON Format:
    {{
      "InvoiceNo": "str",
      "Date": "DD-MM-YYYY",
      "Party": "str",
      "Currency": "USD/INR/etc",
      "Amount_Original": 0.0,
      "Amount_INR": 0.0,
      "GST_Amount": 0.0,
      "TDS_Suggestion": "str",
      "Category": "Software/Service/Equip",
      "AI_Note": "Why you did this?"
    }}
    """
    response = model.generate_content([prompt, img])
    return safe_json(response.text)

# --- MAIN APP ---
st.title("🤖 DataSnap 2.0: Freelancer Agentic SaaS")
st.markdown("---")

with st.sidebar:
    st.header("👤 Freelancer Profile")
    user_name = st.text_input("Creator Name", "Abhi")
    has_lut = st.checkbox("Do you have LUT? (For Export)", value=True)
    if st.button("Clear Data"):
        st.session_state.invoice_data = []
        st.rerun()

if "invoice_data" not in st.session_state:
    st.session_state.invoice_data = []

t1, t2 = st.tabs(["📤 Upload & Agent Sync", "📊 Tax Dashboard"])

with t1:
    files = st.file_uploader("Upload Bills/Invoices", type=["jpg","png","jpeg"], accept_multiple_files=True)
    if st.button("🚀 Run Agentic Audit"):
        if files:
            for file in files:
                with st.spinner(f"Agent auditing {file.name}..."):
                    img = Image.open(file)
                    result = freelancer_agent_process(img)
                    if result:
                        st.session_state.invoice_data.append(result)
                        with st.expander(f"AI Reasoning: {result['InvoiceNo']}"):
                            st.write(f"**Note:** {result['AI_Note']}")
                            st.write(f"**TDS Tip:** {result['TDS_Suggestion']}")
            st.success("Audit Complete!")

with t2:
    if st.session_state.invoice_data:
        df = pd.DataFrame(st.session_state.invoice_data)
        
        # Metrics
        c1, c2, c3 = st.columns(3)
        total_inr = df["Amount_INR"].sum()
        c1.metric("Total Income (INR)", f"₹{total_inr:,.2f}")
        c2.metric("GST Payable", f"₹{df['GST_Amount'].sum():,.2f}")
        c3.metric("Docs Audited", len(df))
        
        st.subheader("📝 Audited Ledger")
        st.dataframe(df, use_container_width=True)
        
        # Download
        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button("📥 Export for CA", output.getvalue(), file_name="Tax_Audit_Ready.xlsx")
    else:
        st.info("Agent waiting for data...")