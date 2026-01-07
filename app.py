import streamlit as st
import google.generativeai as genai
import pandas as pd
from PIL import Image
import gspread
from google.oauth2.service_account import Credentials
from io import BytesIO
import json

# --- 1. UI CONFIG & STYLING ---
st.set_page_config(page_title="DataSnap AI | Smart Data Entry", layout="wide", page_icon="📸")

# Luxury Neon Dark Theme
st.markdown("""
    <style>
    .main { background-color: #0b0e14; color: #e0e0e0; }
    .stButton>button { 
        background: linear-gradient(90deg, #8a2be2, #00ced1); 
        color: white; border-radius: 25px; border: none; padding: 12px 30px; 
        font-size: 18px; font-weight: bold; transition: 0.3s; width: 100%;
    }
    .stButton>button:hover { transform: scale(1.02); box-shadow: 0 0 20px rgba(138, 43, 226, 0.6); }
    .plan-card { 
        border: 1px solid #2e3440; padding: 25px; border-radius: 20px; 
        text-align: center; background: #161b22; box-shadow: 5px 5px 15px rgba(0,0,0,0.4);
    }
    .header-text { 
        background: -webkit-linear-gradient(#8a2be2, #00ced1); 
        -webkit-background-clip: text; -webkit-text-fill-color: transparent; 
        font-size: 45px; font-weight: bold; text-align: center;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. GOOGLE SERVICES SETUP ---
def init_sheets():
    try:
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_info = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_info, scopes=scope)
        client = gspread.authorize(creds)
        return client.open_by_key(st.secrets["GOOGLE_SHEET_ID"]).sheet1
    except Exception as e:
        return None

# --- 3. AI MODEL INITIALIZATION (Automatic Selection) ---
genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

try:
    # Tera favorite automatic model selection logic
    all_m = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    sel_m = 'models/gemini-1.5-flash' if 'models/gemini-1.5-flash' in all_m else all_m[0]
    model = genai.GenerativeModel(sel_m)
except Exception as e:
    st.error(f"AI Initialization Error: {e}")

# --- 4. NAVIGATION ---
with st.sidebar:
    st.markdown("<h2 style='color:#00ced1;'>📸 DataSnap AI</h2>", unsafe_allow_html=True)
    st.markdown("---")
    menu = st.radio("Navigation", ["🚀 AI Scanner", "💎 Subscriptions", "🔐 Admin Panel"])
    st.markdown("---")
    st.write("Owner: Hussain Bhai")
    st.write("System: **Active** 🟢")

# --- 5. AI SCANNER MODE ---
if menu == "🚀 AI Scanner":
    st.markdown("<h1 class='header-text'>DataSnap AI</h1>", unsafe_allow_html=True)
    st.write("<p style='text-align: center;'>Invoice ho ya Data List—AI sab pehchan lega!</p>", unsafe_allow_html=True)

    uploaded_file = st.file_uploader("Upload Image (JPG, PNG)", type=["jpg", "png", "jpeg"])
    
    if uploaded_file:
        img = Image.open(uploaded_file)
        st.image(img, caption="Document Preview", width=500)
        if st.button("Magic Scan & Save"):
            with st.spinner("AI analyzing your document..."):
                # Intelligent Prompt for structured data
                prompt = """Identify the content.
                - If it's an INVOICE: extract Date, Vendor, GST Number, Total.
                - If it's a DATA LIST/TABLE: extract all items.
                
                IMPORTANT: Return the data ONLY as a JSON list of lists.
                Example for Invoice: [["Date", "Vendor", "GST", "Total"], ["4-Nov-25", "A R ELECTRONICS", "19ABAFA4229L1ZD", "35,300.00"]]
                Example for Table: [["Col1", "Col2"], ["Row1Val1", "Row1Val2"]]
                Do not write any extra text, only the JSON list."""
                
                response = model.generate_content([prompt, img])
                res_text = response.text
                
                try:
                    # AI ke response ko clean karke list mein badalna
                    clean_data = res_text.replace("```json", "").replace("```", "").strip()
                    data_list = json.loads(clean_data)
                    
                    df = pd.DataFrame(data_list[1:], columns=data_list[0])
                    
                    st.success("Extraction Complete!")
                    st.dataframe(df) # Screen par table dikhayega

                    # --- EXCEL DOWNLOAD ---
                    output = BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        df.to_excel(writer, index=False, sheet_name='DataSnap_Export')
                    
                    st.download_button(
                        label="📥 Download Excel File",
                        data=output.getvalue(),
                        file_name="DataSnap_Report.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                    # --- GOOGLE SHEET SYNC ---
                    sheet = init_sheets()
                    if sheet:
                        for row in data_list[1:]:
                            sheet.append_row(row)
                        st.toast("Synced to Cloud! ☁️")
                        st.balloons()

                except Exception as e:
                    st.error("AI ne data table format mein nahi diya. Phir se try karein.")
                    st.info(res_text)
       # --- 6. SUBSCRIPTIONS ---
elif menu == "💎 Subscriptions":
    st.markdown("<h1 class='header-text'>Pricing Plans</h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown('<div class="plan-card"><h3>Starter</h3><h2>₹200</h2><p>20 Scans<br>Basic Support</p></div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="plan-card" style="border: 2px solid #00ced1;"><h3>Pro</h3><h2>₹1200</h2><p><b>Unlimited Scans</b><br>Priority AI Mode</p></div>', unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="plan-card"><h3>Enterprise</h3><h2>₹5000</h2><p>Multi-User Access<br>Custom Export</p></div>', unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Payment QR Code")
    # Replace with your actual UPI details
    qr_url = "https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=upi://pay?pa=YOUR_UPI@okaxis&pn=DataSnap"
    st.image(qr_url, caption="Scan to Pay")
    st.info("Setup Fee: ₹1500 | Discount Price: ₹1200")

# --- 7. ADMIN PANEL ---
elif menu == "🔐 Admin Panel":
    st.markdown("<h1 class='header-text'>Owner Access</h1>", unsafe_allow_html=True)
    passw = st.text_input("Enter Password", type="password")
    
    if passw == st.secrets["ADMIN_PASSWORD"]:
        st.success("Welcome Hussain Bhai!")
        sheet = init_sheets()
        if sheet:
            recs = sheet.get_all_records()
            if recs:
                st.dataframe(pd.DataFrame(recs))
            else:
                st.write("No records yet.")
    elif passw:
        st.error("Wrong Password!")