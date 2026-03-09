import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
from io import BytesIO
import re

# --- 1. CONFIG & SETUP ---
st.set_page_config(page_title="Zenith IN - DataSnap AI", layout="wide")

# API Setup (Make sure GEMINI_API_KEY is in your Streamlit Secrets)
try:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    try:

    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]

    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])

except: st.error("AI Error")


except:
    st.error("⚠️ API Key nahi mil rahi! Streamlit Secrets check karo.")

# --- 2. HELPERS ---
def safe_json(text):
    text = text.replace("```json","").replace("```","").strip()
    try: return json.loads(text)
    except: return None

# --- 3. AGENTIC BRAIN (Handles Images & CSV Text) ---
def agent_process(input_data, is_image=True):
    prompt = """
    You are the Zenith IN AI Tax Agent. 
    Analyze the provided invoice/data and return ONLY a JSON object.
    
    FIELDS TO EXTRACT/CALCULATE:
    - InvoiceNo, Date (DD-MM-YYYY), Party (Name).
    - Currency (Detect if USD, INR, EUR, etc.).
    - Amount_Original (Value in original currency).
    - Amount_INR (If original is NOT INR, convert at 1 USD = 83 INR, 1 EUR = 90 INR).
    - GST_Amount (18% of Amount_INR if Party is Indian).
    - TDS_Suggestion (Suggest TDS section like 194J - 10% for professional fees).
    - AI_Note (Brief reasoning for your choice).

    STRICT JSON STRUCTURE:
    {
      "InvoiceNo": "str", "Date": "str", "Party": "str", "Currency": "str",
      "Amount_Original": 0.0, "Amount_INR": 0.0, "GST_Amount": 0.0,
      "TDS_Suggestion": "str", "AI_Note": "str"
    }
    """
    if is_image:
        response = model.generate_content([prompt, input_data])
    else:
        response = model.generate_content(prompt + f"\nData: {input_data}")
    
    return safe_json(response.text)

# --- 4. MAIN INTERFACE ---
st.title("🚀 Zenith IN: DataSnap 2.1")
st.subheader("Autonomous Tax Agent for Freelancers")

if "invoice_data" not in st.session_state:
    st.session_state.invoice_data = []

# Sidebar for Profile
with st.sidebar:
    st.header("👤 Business Profile")
    st.write("**Owner:** Aayan Akhter")
    st.write("**Company:** Zenith IN")
    if st.button("🗑️ Clear All Records"):
        st.session_state.invoice_data = []
        st.rerun()

# --- 5. TABS DEFINITION (Crucial Fix) ---
t1, t2 = st.tabs(["📤 Upload & Process", "📊 Tax Dashboard"])

with t1:
    st.write("### Step 1: Upload Invoices (Image/CSV)")
    uploaded_files = st.file_uploader("Drop your files here", type=["jpg","png","jpeg","csv","xlsx"], accept_multiple_files=True)
    
    if st.button("📊 Launch AI Agent Audit"):
        if uploaded_files:
            for file in uploaded_files:
                with st.spinner(f"Zenith AI is auditing {file.name}..."):
                    if file.name.endswith(('.csv', '.xlsx')):
                        # CSV/Excel Logic
                        df_raw = pd.read_csv(file) if file.name.endswith('.csv') else pd.read_excel(file)
                        sample_data = df_raw.head(5).to_string()
                        result = agent_process(sample_data, is_image=False)
                    else:
                        # Image Logic
                        img = Image.open(file)
                        result = agent_process(img, is_image=True)
                    
                    if result:
                        st.session_state.invoice_data.append(result)
                        st.toast(f"✅ Processed: {file.name}")
            st.success("Audit Cycle Complete!")
        else:
            st.warning("Bhai, pehle file toh daal!")

with t2:
    st.write("### Step 2: CA-Ready Ledger")
    if st.session_state.invoice_data:
        # Create DataFrame from session state
        df_final = pd.DataFrame(st.session_state.invoice_data)
        
        # Ensure all columns exist (GPT's recommendation)
        required_cols = ["InvoiceNo", "Date", "Party", "Currency", "Amount_Original", "Amount_INR", "GST_Amount", "TDS_Suggestion", "AI_Note"]
        for col in required_cols:
            if col not in df_final.columns:
                df_final[col] = "N/A"
        
        # Display Table
        st.dataframe(df_final[required_cols], use_container_width=True)
        
        # Professional Excel Export
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_final[required_cols].to_excel(writer, index=False, sheet_name='Zenith_Tax_Report')
        
        st.download_button(
            label="📥 Download Professional Excel Report",
            data=output.getvalue(),
            file_name=f"Zenith_Tax_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    else:
        st.info("Abhi koi data nahi hai. Upload tab mein files process karein.")