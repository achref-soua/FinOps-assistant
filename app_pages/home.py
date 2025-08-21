import streamlit as st

def main():
    st.set_page_config(page_title="AWS Pricing Tool", layout="centered")
    st.title("💰 AWS Pricing Analysis Tool")
    st.markdown("""
        Welcome to the AWS Pricing Analysis Tool! This application helps you analyze and compare the costs of your AWS resources, including EC2 instances and RDS databases. 
        
        **Features:**
        - Interactive cost analysis for EC2 and RDS
        - Visual breakdowns and recommendations
        - Easy-to-use interface for quick insights
        
        **How to use:**
        - Select a service from the sidebar menu to begin your analysis.
        - Review the cost breakdown and recommendations for optimization.
        
        _This tool is designed to help FinOps teams and cloud engineers optimize AWS spending and make informed decisions._
    """)
    st.info("Select a Service from the sidebar menu to start your analysis.")
    