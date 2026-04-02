import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
from io import BytesIO

# --- 1. CONFIG & SETUP ---
st.set_page_config(page_title="Zenith IN - DataSnap Pro", layout="wide")

# API Setup (Fixed Configuration Logic)
try:
    # Ensure secret key is fetched correctly
    api_key = st.secrets["GEMINI_API_KEY"]
    genai.configure(api_key=api_key)
    
    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    model_name = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0]
    model = genai.GenerativeModel(model_name)
except Exception as e: 
    st.error(f"AI Connection Error: {e}")
    st.info("Tip: Make sure GEMINI_API_KEY is in your .streamlit/secrets.toml file")

# --- 2. HELPERS ---
def safe_json(text):
    try:
        clean_text = text.replace("```json", "").replace("```", "").strip()
        data = json.loads(clean_text)
        return data[0] if isinstance(data, list) else data
    except: return None

# --- 3. AGENTIC BRAIN (Updated with Export & PDF Logic) ---
def agent_process(input_file, is_data=False, exchange_rate=83.0):
    prompt = f"""
    You are the Zenith IN AI Tax Agent. 
    Analyze the document and return ONLY a JSON object.
    
    LOGIC RULES:
    1. If Currency is NOT INR, set GST_Amount to 0.0 and mention 'Export of Service/LUT' in AI_Note.
    2. Convert Amount_Original to INR using the rate: {exchange_rate}.
    3. Categorize Indian payments under 18% GST and suggest TDS (e.g., 194J).

    RETURN JSON:
    {{"InvoiceNo": "str", "Date": "DD-MM-YYYY", "Party": "str", "Currency": "str", 
      "Amount_Original": 0.0, "Amount_INR": 0.0, "GST_Amount": 0.0, 
      "TDS_Suggestion": "str", "AI_Note": "str"}}
    """
    try:
        if is_data:
            # For CSV/Text data
            response = model.generate_content(prompt + f"\nData: {input_file}")
        else:
            # Handles PDF and Images
            file_bytes = input_file.getvalue()
            mime_type = input_file.type
            response = model.generate_content([
                prompt, 
                {'mime_type': mime_type, 'data': file_bytes}
            ])
        return safe_json(response.text)
    except Exception as e:
        st.error(f"Audit failed: {e}")
        return None

# --- 4. MAIN INTERFACE ---
st.title("🚀 Zenith IN: DataSnap Pro")

if "invoice_data" not in st.session_state:
    st.session_state.invoice_data = []

with st.sidebar:
    st.header("⚙️ Settings")
    ex_rate = st.number_input("Today's USD to INR Rate", value=83.5, step=0.1)
    st.divider()
    st.write("**Founder:** Aayan Akhter")
    if st.button("🗑️ Reset Ledger"):
        st.session_state.invoice_data = []
        st.rerun()

t1, t2 = st.tabs(["📤 Smart Upload", "📊 Tax Ledger"])

with t1:
    files = st.file_uploader("Upload Invoice (PDF, JPG, PNG, CSV)", 
                            type=["pdf", "jpg", "png", "jpeg", "csv"], 
                            accept_multiple_files=True)
    
    if st.button("📊 Run AI Audit"):
        if files:
            for file in files:
                with st.spinner(f"Auditing {file.name}..."):
                    if file.name.endswith('.csv'):
                        df_raw = pd.read_csv(file)
                        res = agent_process(df_raw.head(10).to_string(), is_data=True, exchange_rate=ex_rate)
                    else:
                        res = agent_process(file, is_data=False, exchange_rate=ex_rate)
                    
                    if res:
                        st.session_state.invoice_data.append(res)
            st.success("Audit Cycle Complete!")

with t2:
    if st.session_state.invoice_data:
        df = pd.DataFrame(st.session_state.invoice_data)
        st.data_editor(df, use_container_width=True, hide_index=True)
        
        # Excel Export logic
        output = BytesIO()
        # Using openpyxl for Excel export
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button("📥 Download Business Report", output.getvalue(), "Zenith_Pro_Report.xlsx")
    else:
        st.info("No data yet. Upload invoices to begin.")