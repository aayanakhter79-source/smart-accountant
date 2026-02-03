import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# ---------------- CONFIG ----------------
st.set_page_config(page_title="DataSnap AI for GST Accountants", layout="wide")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:

    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]

    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])

except: st.error("AI Error")


# ---------------- GOOGLE SHEET ----------------
def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets",
                 "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"], scopes=scope
        )
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
    except:
        return None

# ---------------- JSON CLEANER ----------------
def safe_json_load(text):
    text = text.replace("```json","").replace("```","").strip()
    try:
        return json.loads(text)
    except:
        return None

# ---------------- UI ----------------
st.markdown(
    "<h1 style='text-align:center;color:#00ced1;'>🚀 DataSnap AI for GST Accountants</h1>"
    "<p style='text-align:center;'>Turn invoice photos into Excel in seconds</p>",
    unsafe_allow_html=True
)

sheet = get_gsheet()
st.subheader("Upload GST Invoice")
up = st.file_uploader("Upload Invoice Image", type=["jpg","jpeg","png"])

if up:
    img = Image.open(up)
    st.image(img, width=400)

    if st.button("📊 Scan Invoice & Generate Excel"):
        with st.spinner("Scanning invoice..."):
            prompt = """
            You are an expert GST Accountant. Analyze this invoice image carefully.
            Extract the data into a structured table format.

            RULES:
            1. First Row (Headers): ["Invoice No", "Date", "Party Name", "GSTIN", "Taxable Value", "CGST", "SGST", "IGST", "Grand Total"]
            2. For every item/product in the bill, create a new row.
            3. Repeat the Invoice No, Date, and Party Name for every row (this is important for Excel accounting).
            4. If it's a Local sale, fill CGST/SGST. If it's Inter-state, fill IGST. 
            5. Calculate mathematically: Taxable Value + Taxes = Grand Total.
            6. Return ONLY a JSON list of lists. No extra text.
            """

            response = model.generate_content([prompt, img])
            data_list = safe_json_load(response.text)

            if data_list:
                clean = [[str(c) if c else "" for c in row] for row in data_list]
                df = pd.DataFrame(clean)
                st.success("✅ Invoice extracted!")
                st.dataframe(df, use_container_width=True)

                if sheet:
                    sheet.append_rows(clean)
                    st.toast("📡 Synced to Google Sheet")

                # Excel export
                out = BytesIO()
                with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                    df.to_excel(writer, index=False, header=False, sheet_name="Invoices")
                    workbook = writer.book
                    worksheet = writer.sheets["Invoices"]
                    fmt = workbook.add_format({"border":1, "text_wrap":True})
                    worksheet.set_column("A:I", 18, fmt)

                st.download_button(
                    "📥 Download Excel",
                    out.getvalue(),
                    file_name="DataSnap_GST.xlsx"
                )
            else:
                st.error("❌ Could not read invoice. Try a clearer photo.")
