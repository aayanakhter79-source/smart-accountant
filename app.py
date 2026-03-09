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

# --- AGENTIC ENGINE ---
def process_with_ai(img, context="Image Data"):
    prompt = f"""
    Analyze this {context} for an Indian Freelancer. 
    Return ONLY JSON:
    {{
      "InvoiceNo": "str", "Date": "DD-MM-YYYY", "Party": "str",
      "Currency": "INR/USD", "Amount_INR": 0.0, "GST_Amount": 0.0,
      "TDS_Suggestion": "str", "AI_Note": "Why?"
    }}
    """
    response = model.generate_content([prompt, img])
    return safe_json(response.text)

# --- MAIN APP ---
st.title("🤖 DataSnap 2.0: Hybrid Tax Agent")

if "invoice_data" not in st.session_state:
    st.session_state.invoice_data = []

t1, t2 = st.tabs(["📤 Upload (Image/CSV)", "📊 Tax Dashboard"])

with t1:
    # Yahan humne type mein CSV aur Excel bhi add kar diya hai
    files = st.file_uploader("Upload Files", type=["jpg","png","jpeg","csv","xlsx"], accept_multiple_files=True)
    
    if st.button("🚀 Run Agentic Audit"):
        if files:
            for file in files:
                with st.spinner(f"Processing {file.name}..."):
                    # CHECK FILE TYPE
                    if file.name.endswith(('.csv', '.xlsx')):
                        # CSV/Excel Logic
                        if file.name.endswith('.csv'):
                            df_temp = pd.read_csv(file)
                        else:
                            df_temp = pd.read_excel(file)
                        
                        st.info(f"📁 CSV/Excel detected. Analyzing first 5 rows...")
                        # AI ko CSV ka text bhej rahe hain analysis ke liye
                        csv_text = df_temp.head(10).to_string()
                        result = process_with_ai(f"Data Sample: {csv_text}", context="Table Data")
                    else:
                        # Image Logic
                        img = Image.open(file)
                        result = process_with_ai(img, context="Image")

                    if result:
                        st.session_state.invoice_data.append(result)
            st.success("Audit Complete!")

with t2:
    if st.session_state.invoice_data:
        df = pd.DataFrame(st.session_state.invoice_data)
        st.subheader("📝 Audited Ledger")
        st.dataframe(df, use_container_width=True)
        
        output = BytesIO()
        df.to_excel(output, index=False)
        st.download_button("📥 Export for CA", output.getvalue(), file_name="Tax_Audit.xlsx")