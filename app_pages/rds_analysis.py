import streamlit as st
import pandas as pd
import json
from utils.auth import show_authentication
from utils.pricing import fetch_rds_price
from utils.models import Entry
from pydantic import BaseModel, ValidationError
from typing import Literal


def main():
    st.set_page_config(page_title="RDS Analysis", layout="centered")
    st.title("🗂️ RDS Pricing Analysis")
    
    st.markdown("""## RDS Input Method""")
    input_mode = st.radio(
        "Choose input method:", ["Fill In Form", "Manual JSON Input", "JSON Upload"]
    )

    class Entry(BaseModel):
        engine: Literal["PostgreSQL", "MariaDB"]
        instance_type: str
        region: str
        multi_az: Literal["Oui", "Non"]
        start: str
        end: str

    if input_mode == "Fill In Form":
        st.subheader("📄 Add Entries One by One")

        if "entry_list" not in st.session_state:
            st.session_state.entry_list = []

        with st.form("rds_form"):
            engine = st.selectbox("Engine", ["PostgreSQL", "MariaDB"])
            instance_type = st.text_input("Instance Type")
            region = st.text_input("Region (e.g. Paris)", value="Paris")
            multi_az = st.selectbox("Multi-AZ", ["Oui", "Non"])
            start = st.text_input("Start Date (MM/DD/YYYY)", value="6/1/2025")
            end = st.text_input("End Date (MM/DD/YYYY)", value="5/31/2026")

            col1, col2 = st.columns(2)
            add_clicked = col1.form_submit_button("➕ Add Entry")
            run_clicked = col2.form_submit_button("✅ Run Pricing Analysis")

        if add_clicked:
            try:
                entry_data = {
                    "engine": engine,
                    "instance_type": instance_type,
                    "region": region,
                    "multi_az": multi_az,
                    "start": start,
                    "end": end,
                }
                validated_entry = Entry(**entry_data)
                st.session_state.entry_list.append(entry_data)
                st.success("✅ Entry added.")
            except ValidationError as e:
                st.error(f"❌ Invalid entry:\n{e}")

        if st.session_state.entry_list:
            st.markdown("### 🗂️ Current Entries")
            st.dataframe(pd.DataFrame(st.session_state.entry_list))

        if run_clicked:
            try:
                parsed_entries = [Entry(**e) for e in st.session_state.entry_list]
                results = [fetch_rds_price(entry) for entry in parsed_entries]
                df = pd.DataFrame(results)
                st.success("✅ Pricing analysis complete.")
                st.dataframe(df)
                st.download_button(
                    "Download CSV",
                    df.to_csv(index=False),
                    "rds_pricing.csv",
                    "text/csv",
                )
            except Exception as e:
                st.error(f"❌ Error during processing: {e}")

    elif input_mode == "Manual JSON Input":
        st.subheader("📝 Paste JSON Data")

        template = [
            {
                "engine": "PostgreSQL",
                "instance_type": "db.t3.medium",
                "region": "Paris",
                "multi_az": "Oui",
                "start": "6/1/2025",
                "end": "5/31/2026",
            }
        ]
        default_json = json.dumps(template, indent=4)
        user_input = st.text_area(
            "Paste your JSON here:", value=default_json, height=250
        )

        if st.button("✅ Run Pricing Analysis"):
            try:
                parsed_input = json.loads(user_input)
                entries = [Entry(**entry) for entry in parsed_input]
                results = [fetch_rds_price(entry) for entry in entries]
                df = pd.DataFrame(results)
                st.success("✅ Pricing analysis complete.")
                st.dataframe(df)
                st.download_button(
                    "Download CSV",
                    df.to_csv(index=False),
                    "rds_pricing.csv",
                    "text/csv",
                )
            except (json.JSONDecodeError, ValidationError) as e:
                st.error(f"❌ Error parsing input: {e}")

    elif input_mode == "JSON Upload":
        st.subheader("📁 Upload JSON File")

        uploaded_file = st.file_uploader("Upload your JSON file", type="json")

        if uploaded_file is not None:
            try:
                raw_data = uploaded_file.read()
                parsed_input = json.loads(raw_data)
                entries = [Entry(**entry) for entry in parsed_input]
                results = [fetch_rds_price(entry) for entry in entries]
                df = pd.DataFrame(results)
                st.success("✅ Pricing analysis complete.")
                st.dataframe(df)
                st.download_button(
                    "Download CSV",
                    df.to_csv(index=False),
                    "rds_pricing.csv",
                    "text/csv",
                )
            except (json.JSONDecodeError, ValidationError) as e:
                st.error(f"❌ Invalid JSON file: {e}")