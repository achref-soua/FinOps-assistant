import streamlit as st
from app_pages import home, ec2_analysis, rds_analysis

# Page routing
PAGES = {
    "Home": home,
    "EC2 Analysis": ec2_analysis,
    "RDS Analysis": rds_analysis
}

# Main app
def main():
    st.sidebar.image("assets/moovto.png", width=150)
    selection = st.sidebar.radio("Navigation", list(PAGES.keys()))
    
    # Show authentication in sidebar
    from utils.auth import show_authentication
    show_authentication()
    
    # Load selected page
    page = PAGES[selection]
    page.main()

if __name__ == "__main__":
    main()