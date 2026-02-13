import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# --- CONFIG ---
st.set_page_config(page_title="DataSnap AI Pro - GST Edition", layout="wide")
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:

    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]

    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])

except: st.error("AI Error")


# --- UI ---
st.markdown("<h1 style='text-align:center;color:#00ced1;'>💼 DataSnap AI: Accountant V2</h1>", unsafe_allow_html=True)

t1, t2 = st.tabs(["🚀 Professional Scanner", "📜 Audit History"])

with t1:
    up = st.file_uploader("Upload GST Invoice", type=["jpg","jpeg","png"])
    if up:
        img = Image.open(up)
        st.image(img, width=400)
        
        if st.button("📊 Generate Accountant-Ready Excel"):
            with st.spinner("Analyzing GST Compliance..."):
                # UPGRADED PROMPT FOR V2
                prompt = """
                You are a Senior GST Consultant. Extract data for GSTR-1 filing.
                
                Columns Required:
                ["Invoice No", "Date", "Party Name", "GSTIN", "Item Description", "HSN", "Qty", "Taxable Value", "GST %", "CGST", "SGST", "IGST", "Total"]
                
                Rules:
                1. Extract every line item separately.
                2. Repeat Invoice No, Date, and GSTIN for every line item (for Tally import).
                3. Identify HSN codes from the items.
                4. Logic: Taxable Value * GST% = Total Tax.
                5. Return ONLY a JSON list of lists.
                """
                
                try:
                    response = model.generate_content([prompt, img])
                    data_list = json.loads(response.text.replace("```json","").replace("```","").strip())
                    
                    if data_list:
                        df = pd.DataFrame(data_list)
                        st.success("✅ GSTR-1 Compatible Data Extracted!")
                        st.dataframe(df, use_container_width=True)

                        # Excel Formatting Pro
                        out = BytesIO()
                        with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                            df.to_excel(writer, index=False, header=False, sheet_name="GST_Data")
                            workbook = writer.book
                            worksheet = writer.sheets["GST_Data"]
                            
                            # Professional Excel Styling
                            header_fmt = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC', 'border': 1})
                            cell_fmt = workbook.add_format({'border': 1, 'text_wrap': True})
                            
                            for col_num, value in enumerate(df.columns.values):
                                worksheet.write(0, col_num, value, header_fmt)
                            
                            worksheet.set_column("A:M", 15, cell_fmt) # All columns wide
                            worksheet.set_column("E:E", 35, cell_fmt) # Description extra wide

                        st.download_button("📥 Download V2 Accountant Excel", out.getvalue(), "DataSnap_V2_Pro.xlsx")
                except Exception as e:
                    st.error(f"Error: {e}")