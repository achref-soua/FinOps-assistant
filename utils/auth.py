import streamlit as st
import os
from dotenv import load_dotenv

def show_authentication():
    st.sidebar.title("🔐 AWS Credentials")
    use_saved = st.sidebar.checkbox("Use saved credentials (.env)")

    if not use_saved:
        aws_access_key = st.sidebar.text_input("AWS Access Key", type="password")
        aws_secret_key = st.sidebar.text_input("AWS Secret Key", type="password")
        aws_region = st.sidebar.text_input("Default Region", value="us-east-1")

        if st.sidebar.button("Save & Login"):
            with open(".env", "w") as f:
                f.write(f"AWS_ACCESS_KEY_ID={aws_access_key}\n")
                f.write(f"AWS_SECRET_ACCESS_KEY={aws_secret_key}\n")
                f.write(f"AWS_DEFAULT_REGION={aws_region}\n")
            st.sidebar.success("Credentials saved!")
    
    load_dotenv(override=True)
    return os.environ