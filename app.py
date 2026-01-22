import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import json
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO

# --- CONFIG & API SETUP ---
st.set_page_config(page_title="DataSnap AI - Zenith Pro", layout="wide")

genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
try:

    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]

    model = genai.GenerativeModel('models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0])

except: st.error("AI Error")

def get_gsheet():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
    except: return None

def safe_json_load(text):
    text = text.replace("```json","").replace("```","").strip()
    for _ in range(2):
        try:
            return json.loads(text)
        except:
            text = text.replace("\n", " ").replace(",]", "]").replace(",}", "}")
    return None

# --- MAIN UI ---
st.markdown("<h1 style='text-align: center; color: #00ced1;'>🚀 DataSnap AI Pro by ZENITH</h1>", unsafe_allow_html=True)
t1, t2 = st.tabs(["🚀 AI Scanner", "📜 Data History"])

with t1:
    sheet = get_gsheet()
    c1, c2 = st.columns([3, 1])
    
    with c2:
        mode = st.radio("🧠 Select Task Type", ["📊 Data Entry Only", "🧾 GST Invoice Mode"])
    
    with c1:
        up = st.file_uploader("Upload Image", type=['jpg','png','jpeg'])
        if up:
            img = Image.open(up)
            st.image(img, width=450)
            
            if st.button("🚀 Process & Save Data"):
                with st.spinner("Processing..."):
                    # GPT Instructions
                    if mode == "🧾 GST Invoice Mode":
                        prompt = "Extract GST Invoice. Include Shop Name, Items, CGST, SGST, Total. Return JSON list of lists."
                    else:
                        prompt = "Extract all tables. Keep descriptions detailed. Return JSON list of lists."

                    try:
                        response = model.generate_content([prompt, img])
                        data_list = safe_json_load(response.text)

                        if data_list:
                            # 1. Data Safai (String conversion to avoid Sheet Errors)
                            clean_data = [[str(cell).strip() for cell in row] for row in data_list]
                            df = pd.DataFrame(clean_data)
                            
                            st.success("✅ Data Processed!")
                            st.dataframe(df, use_container_width=True)

                            # 2. Safe Save to Google Sheets
                            if sheet:
                                try:
                                    sheet.append_rows(clean_data)
                                    st.toast("Saved to Cloud!")
                                except Exception as e:
                                    st.error(f"Sheet Sync Error: {e}")

                            # 3. Excel File Generation
                            out = BytesIO()
                            with pd.ExcelWriter(out, engine='xlsxwriter') as writer:
                                df.to_excel(writer, index=False, header=False, sheet_name='ZenithData')
                                workbook = writer.book
                                worksheet = writer.sheets['ZenithData']
                                wrap_fmt = workbook.add_format({'text_wrap': True, 'valign': 'top', 'border': 1})
                                worksheet.set_column('B:B', 45, wrap_fmt)
                                worksheet.set_column('A:A', 8)
                                worksheet.set_column('C:G', 15)
                            
                            st.download_button("📥 Download Excel File", out.getvalue(), "DataSnap_Zenith.xlsx")
                        else:
                            st.error("AI couldn't read the data. Try again.")
                    except Exception as e:
                        st.error(f"Process Error: {e}")

with t2:
    st.subheader("📜 Recent History")
    if sheet:
        try:
            # History loading with error protection
            raw_history = sheet.get_all_values()
            if raw_history:
                df_history = pd.DataFrame(raw_history)
                # Latest entries on top
                st.dataframe(df_history.iloc[::-1], height=600, use_container_width=True)
            else:
                st.info("No history found in sheets.")
        except Exception as e:
            st.warning("Wait... History is syncing from Google Sheets.")