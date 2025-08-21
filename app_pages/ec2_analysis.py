import streamlit as st
import pandas as pd
from utils.auth import show_authentication
from utils.pricing import fetch_ec2_comparison
from utils.models import EC2ExtendedEntry
from typing import Literal

def main():
    st.set_page_config(page_title="EC2 Analysis", layout="centered")
    st.title("🖥️ EC2 Analysis")
    
    st.markdown("## EC2 Input Method")

    input_mode = st.radio(
        "Choose input method:", ["Automatic", "Paste CSV Text", "CSV Upload"]
    )

    if input_mode == "Automatic":
        st.subheader("� Automatic EC2 Instance Discovery")
        region_options = ["All Regions", "Paris", "Frankfurt", "Ireland", "London", "N. Virginia", "Oregon"]
        selected_region = st.selectbox("Select Region", region_options, index=0)

        def get_all_ec2_instances(region_choice):
            import boto3
            import os
            from utils.helpers import REGION_MAP
            # Use credentials from .env
            access_key = os.getenv("AWS_ACCESS_KEY_ID")
            secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
            # If All Regions, use all mapped regions
            regions_to_query = []
            if region_choice == "All Regions":
                regions_to_query = list(REGION_MAP.values())
            else:
                regions_to_query = [REGION_MAP.get(region_choice, region_choice)]
            all_instances = []
            retirement_info = []
            for reg in regions_to_query:
                try:
                    ec2 = boto3.client(
                        "ec2",
                        region_name=reg,
                        aws_access_key_id=access_key,
                        aws_secret_access_key=secret_key,
                    )
                    reservations = ec2.describe_instances()["Reservations"]
                    instance_ids = []
                    for res in reservations:
                        for inst in res["Instances"]:
                            instance_type = inst.get("InstanceType", "")
                            vcpus = inst.get("CpuOptions", {}).get("CoreCount", 0) * inst.get("CpuOptions", {}).get("ThreadsPerCore", 1)
                            memory_gb = None
                            instance_id = inst.get("InstanceId", "")
                            instance_ids.append(instance_id)
                            # Try to get memory from instance type description
                            try:
                                ec2_desc = boto3.client(
                                    "ec2",
                                    region_name=reg,
                                    aws_access_key_id=access_key,
                                    aws_secret_access_key=secret_key,
                                )
                                type_info = ec2_desc.describe_instance_types(InstanceTypes=[instance_type])
                                memory_gb = type_info["InstanceTypes"][0]["MemoryInfo"]["SizeInMiB"] / 1024
                            except Exception:
                                memory_gb = None
                            all_instances.append({
                                "instance_type": instance_type,
                                "vcpus": vcpus,
                                "memory_gb": memory_gb,
                                "region": reg,
                                "instance_id": instance_id,
                            })
                    # Get scheduled events for instances in this region
                    if instance_ids:
                        try:
                            events = ec2.describe_instance_status(InstanceIds=instance_ids)["InstanceStatuses"]
                            for status in events:
                                instance_id = status.get("InstanceId", "")
                                scheduled_events = status.get("Events", [])
                                for event in scheduled_events:
                                    event_info = {
                                        "instance_id": instance_id,
                                        "region": reg,
                                        "event_code": event.get("Code", ""),
                                        "not_before": event.get("NotBefore", ""),
                                        "not_after": event.get("NotAfter", ""),
                                        "description": event.get("Description", ""),
                                    }
                                    retirement_info.append(event_info)
                        except Exception:
                            pass
                except Exception:
                    continue
            return all_instances, retirement_info

        if "ec2_auto_instances" not in st.session_state:
            st.session_state.ec2_auto_instances = None
        if "ec2_auto_results" not in st.session_state:
            st.session_state.ec2_auto_results = None
        if "ec2_auto_filtered" not in st.session_state:
            st.session_state.ec2_auto_filtered = False

        if st.button("� Discover EC2 Instances"):
            instances, retirement_info = get_all_ec2_instances(selected_region)
            st.session_state.ec2_auto_instances = instances
            st.session_state.ec2_auto_retirement = retirement_info
            st.session_state.ec2_auto_results = None
            st.session_state.ec2_auto_filtered = False
            if not instances:
                st.warning("There are no instances in this region, check other regions please.")

        if st.session_state.ec2_auto_instances:
            if len(st.session_state.ec2_auto_instances) == 0:
                st.warning("There are no instances in this region, check other regions please.")
            else:
                st.markdown("### 📋 Discovered EC2 Instances")
                df_auto = pd.DataFrame(st.session_state.ec2_auto_instances)
                st.dataframe(df_auto)
                # Show scheduled events info or message if none
                st.markdown("### ⏳ EC2 Scheduled Events")
                if "ec2_auto_retirement" in st.session_state and st.session_state.ec2_auto_retirement:
                    df_events = pd.DataFrame(st.session_state.ec2_auto_retirement)
                    st.dataframe(df_events)
                else:
                    st.info("No EC2 instances have scheduled events in the selected region(s).")
                if st.button("✅ Run Graviton check", key="auto_run_compare"):
                    results = []
                    for e in st.session_state.ec2_auto_instances:
                        if e["memory_gb"] is not None and e["vcpus"]:
                            candidate_list = fetch_ec2_comparison(
                                e["instance_type"], int(e["vcpus"]), float(e["memory_gb"]), e["region"]
                            )
                            results.extend(candidate_list)
                    df_results = pd.DataFrame(results)
                    st.session_state.ec2_auto_results = df_results
                    st.session_state.ec2_auto_filtered = False
                    st.success("✅ EC2 Graviton check complete.")

        def set_ec2_auto_filtered_true():
            st.session_state.ec2_auto_filtered = True
        def set_ec2_auto_filtered_false():
            st.session_state.ec2_auto_filtered = False

        if st.session_state.ec2_auto_results is not None:
            df = st.session_state.ec2_auto_results.copy()
            if st.session_state.ec2_auto_filtered:
                df["candidate_monthly_raw"] = (
                    df["candidate_monthly"]
                    .replace("[\$,]", "", regex=True)
                    .astype(float)
                )
                # Drop rows with NaN in filter columns
                df_filtered = df.dropna(subset=["input_type", "region", "candidate_monthly_raw"])
                if not df_filtered.empty:
                    filtered_df = df_filtered.loc[
                        df_filtered.groupby(["input_type", "region"])[
                            "candidate_monthly_raw"
                        ].idxmin()
                    ]
                    st.dataframe(filtered_df.drop(columns=["candidate_monthly_raw"]))
                    st.download_button(
                        "Download CSV (Filtered)",
                        filtered_df.drop(columns=["candidate_monthly_raw"]).to_csv(
                            index=False
                        ),
                        "ec2_comparison_filtered.csv",
                        "text/csv",
                    )
                else:
                    st.warning("No valid rows to filter.")
            else:
                st.dataframe(df)
                st.download_button(
                    "Download CSV",
                    df.to_csv(index=False),
                    "ec2_comparison.csv",
                    "text/csv",
                )
            col1, col2 = st.columns(2)
            col1.button("🔍 Filter Cheapest Option", key="auto_filter", on_click=set_ec2_auto_filtered_true)
            col2.button("🔄 Reset Results", key="auto_reset", on_click=set_ec2_auto_filtered_false)

    # --- Manual Input (CSV-style) ---
    elif input_mode == "Paste CSV Text":
        st.subheader("📝 Paste EC2 entries in CSV format")
        st.markdown("**Example Format:**")
        st.code(
            "instance_type,vcpus,memory_gb,region\nm5.large,2,8.0,Paris\nc5.xlarge,4,8.0,Frankfurt",
            language="text",
        )

        csv_template = (
            "instance_type,vcpus,memory_gb,region\n"
            "m5.large,2,8.0,Paris\n"
            "c5.xlarge,4,8.0,Frankfurt"
        )

        csv_text = st.text_area(
            "Paste your EC2 entries here (including header):",
            value=csv_template,
            height=250,
        )

        if "ec2_full_results_csv" not in st.session_state:
            st.session_state.ec2_full_results_csv = None
        if "ec2_filtered_csv" not in st.session_state:
            st.session_state.ec2_filtered_csv = False

        if st.button("✅ Run Comparison", key="run_csv_text"):
            try:
                from io import StringIO

                df_input = pd.read_csv(StringIO(csv_text.strip()))
                required_cols = {"instance_type", "vcpus", "memory_gb", "region"}
                if not required_cols.issubset(df_input.columns):
                    st.error(
                        f"❌ Missing required columns: {required_cols - set(df_input.columns)}"
                    )
                else:
                    results = []
                    for row in df_input.to_dict(orient="records"):
                        candidate_list = fetch_ec2_comparison(
                            row["instance_type"],
                            int(row["vcpus"]),
                            float(row["memory_gb"]),
                            row["region"],
                        )
                        results.extend(candidate_list)  # flatten the list

                    df = pd.DataFrame(results)
                    st.session_state.ec2_full_results_csv = df
                    st.session_state.ec2_filtered_csv = False
                    st.success("✅ EC2 comparison complete.")
            except Exception as e:
                st.error(f"❌ Error processing input: {e}")

        def set_ec2_filtered_csv_true():
            st.session_state.ec2_filtered_csv = True

        def set_ec2_filtered_csv_false():
            st.session_state.ec2_filtered_csv = False

        if st.session_state.ec2_full_results_csv is not None:
            df = st.session_state.ec2_full_results_csv.copy()
            if st.session_state.ec2_filtered_csv:
                df["candidate_monthly_raw"] = (
                    df["candidate_monthly"]
                    .replace("[\$,]", "", regex=True)
                    .astype(float)
                )
                df_filtered = df.dropna(subset=["input_type", "region", "candidate_monthly_raw"])
                if not df_filtered.empty:
                    filtered_df = df_filtered.loc[
                        df_filtered.groupby(["input_type", "region"])[
                            "candidate_monthly_raw"
                        ].idxmin()
                    ]
                    st.dataframe(filtered_df.drop(columns=["candidate_monthly_raw"]))
                    st.download_button(
                        "Download CSV (Filtered)",
                        filtered_df.drop(columns=["candidate_monthly_raw"]).to_csv(
                            index=False
                        ),
                        "ec2_comparison_filtered.csv",
                        "text/csv",
                    )
                else:
                    st.warning("No valid rows to filter.")
            else:
                st.dataframe(df)
                st.download_button(
                    "Download CSV",
                    df.to_csv(index=False),
                    "ec2_comparison.csv",
                    "text/csv",
                )
            col1, col2 = st.columns(2)
            col1.button(
                "🔍 Filter Cheapest Option",
                key="filter_csv",
                on_click=set_ec2_filtered_csv_true,
            )
            col2.button(
                "🔄 Reset Results", key="reset_csv", on_click=set_ec2_filtered_csv_false
            )

    elif input_mode == "CSV Upload":
        st.subheader("📁 Upload CSV File")

        uploaded_file = st.file_uploader("Upload CSV", type=["csv"])

        if "ec2_full_results_upload" not in st.session_state:
            st.session_state.ec2_full_results_upload = None
        if "ec2_filtered_upload" not in st.session_state:
            st.session_state.ec2_filtered_upload = False

        if uploaded_file is not None:
            try:
                df_input = pd.read_csv(uploaded_file)
                entries = [
                    EC2ExtendedEntry(**row)
                    for row in df_input.to_dict(orient="records")
                ]
                results = []
                for e in entries:
                    candidate_list = fetch_ec2_comparison(
                        e.instance_type, e.vcpus, e.memory_gb, e.region
                    )
                    results.extend(candidate_list)  # flatten the list

                df = pd.DataFrame(results)
                st.session_state.ec2_full_results_upload = df
                st.session_state.ec2_filtered_upload = False
                st.success("✅ EC2 comparison complete.")
            except Exception as e:
                st.error(f"❌ Failed to process CSV: {e}")

        def set_ec2_filtered_upload_true():
            st.session_state.ec2_filtered_upload = True

        def set_ec2_filtered_upload_false():
            st.session_state.ec2_filtered_upload = False

        if st.session_state.ec2_full_results_upload is not None:
            df = st.session_state.ec2_full_results_upload.copy()
            if st.session_state.ec2_filtered_upload:
                df["candidate_monthly_raw"] = (
                    df["candidate_monthly"]
                    .replace("[\$,]", "", regex=True)
                    .astype(float)
                )
                df_filtered = df.dropna(subset=["input_type", "region", "candidate_monthly_raw"])
                if not df_filtered.empty:
                    filtered_df = df_filtered.loc[
                        df_filtered.groupby(["input_type", "region"])[
                            "candidate_monthly_raw"
                        ].idxmin()
                    ]
                    st.dataframe(filtered_df.drop(columns=["candidate_monthly_raw"]))
                    st.download_button(
                        "Download CSV (Filtered)",
                        filtered_df.drop(columns=["candidate_monthly_raw"]).to_csv(
                            index=False
                        ),
                        "ec2_comparison_filtered.csv",
                        "text/csv",
                    )
                else:
                    st.warning("No valid rows to filter.")
            else:
                st.dataframe(df)
                st.download_button(
                    "Download CSV",
                    df.to_csv(index=False),
                    "ec2_comparison.csv",
                    "text/csv",
                )
            col1, col2 = st.columns(2)
            col1.button(
                "🔍 Filter Cheapest Option",
                key="filter_upload",
                on_click=set_ec2_filtered_upload_true,
            )
            col2.button(
                "🔄 Reset Results",
                key="reset_upload",
                on_click=set_ec2_filtered_upload_false,
            )