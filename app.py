import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
from io import BytesIO

# --- CONFIG ---
st.set_page_config(page_title="DataSnap 2.0 - Hybrid Agent", layout="wide")
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

# --- AGENTIC ENGINE (THE BRAIN) ---
def freelancer_agent_process(img):
    # Prompt upgraded for USD detection + Clean fields for GPT's fix
    prompt = """
    You are an Expert AI Tax Agent for Indian Freelancers. 
    Analyze the document and return ONLY a JSON object.
    
    TASKS:
    1. Detect Currency (INR, USD, EUR, etc.).
    2. If Currency is NOT INR, convert Amount_Original to Amount_INR (Use approx rate: 1 USD = 83 INR, 1 EUR = 90 INR).
    3. Calculate GST_Amount (18% for services if INR/Domestic).
    4. Provide TDS_Suggestion (e.g., '10% u/s 194J' for professional fees).
    5. Reasoning: Explain WHY you categorized it this way.

    STRICT JSON STRUCTURE:
    {
      "InvoiceNo": "str",
      "Date": "DD-MM-YYYY",
      "Party": "str",
      "Currency": "USD/INR",
      "Amount_Original": 0.0,
      "Amount_INR": 0.0,
      "GST_Amount": 0.0,
      "TDS_Suggestion": "str",
      "AI_Note": "str"
    }
    """
    response = model.generate_content([prompt, img])
    return safe_json(response.text)

# --- UPDATED DASHBOARD (T2) FOR CLEAN EXCEL ---
with t2:
    if st.session_state.invoice_data:
        # GPT Fix: Converting list of JSONs into a CLEAN Table
        df = pd.DataFrame(st.session_state.invoice_data)
        
        # Ensure column order is perfect for the client
        cols = ["InvoiceNo", "Date", "Party", "Currency", "Amount_Original", "Amount_INR", "GST_Amount", "TDS_Suggestion", "AI_Note"]
        df = df[reindex(columns=cols, fill_value=0)] # Ensuring no missing columns

        st.subheader("📊 Professional Tax Ledger (CA-Ready)")
        st.dataframe(df, use_container_width=True)
        
        # EXCEL EXPORT FIX: Proper Table format, not JSON strings
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Tax_Audit_Report')
            
            # Formatting (Clean look for client)
            workbook = writer.book
            header_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
            worksheet = writer.sheets['Tax_Audit_Report']
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
        
        st.download_button("📥 Download Professional Report", output.getvalue(), file_name="Zenith_Tax_Report.xlsx")