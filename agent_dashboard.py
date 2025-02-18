import streamlit as st
import pandas as pd
import requests
from io import BytesIO
import tempfile

# ✅ Ensure this is the first Streamlit command
st.set_page_config(page_title="Agent Overview", layout="wide")

# Load data from GitHub repository
@st.cache_data(ttl=0)  # Forces reload every time
def load_data():
    url_agents = "https://raw.githubusercontent.com/ethanhetu/agent-dashboard/main/AP%20Final.xlsx"
    response = requests.get(url_agents)
    
    if response.status_code != 200:
        st.error("Error fetching data. Please check the file URL and permissions.")
        return None, None
    
    # Save file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name
    
    xls = pd.ExcelFile(tmp_path)
    agents_data = xls.parse('Agents')
    ranks_data = xls.parse('Just Agent Ranks')
    return agents_data, ranks_data

def agent_dashboard():
    agents_data, ranks_data = load_data()
    
    if agents_data is None or ranks_data is None:
        st.stop()
    
    # Streamlit App
    st.title("Agent Overview Dashboard")
    
    # Search functionality
    agent_names = ranks_data['Agent Name'].dropna().replace(['', '(blank)', 'Grand Total'], pd.NA).dropna()
    agent_names = sorted(agent_names, key=lambda name: name.split()[-1])
    selected_agent = st.selectbox("Select an Agent:", agent_names)
    
    # Filter data
    agent_info = agents_data[agents_data['Agent Name'] == selected_agent].iloc[0]
    rank_info = ranks_data[ranks_data['Agent Name'] == selected_agent].iloc[0]
    
    # Layout for name & image
    header_col1, header_col2 = st.columns([3, 1])
    
    with header_col1:
        st.header(f"{selected_agent} - {agent_info['Agency Name']}")
    
    st.subheader("📊 Financial Breakdown")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Dollar Index", f"${rank_info['Dollar Index']:.2f}")
    col2.metric("Win %", f"{agent_info['Won%']:.3f}")
    col3.metric("Contracts Tracked", int(agent_info['CT']))
    col4.metric("Total Contract Value", f"${agent_info['Total Contract Value']:,.0f}")
    
    st.subheader("📈 Agent Rankings")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Dollar Index Rank", f"#{int(rank_info['Index R'])}/90")
    col2.metric("Win Percentage Rank", f"#{int(rank_info['WinR'])}/90")
    col3.metric("Contracts Tracked Rank", f"#{int(rank_info['CTR'])}/90")
    col4.metric("Total Contract Value Rank", f"#{int(rank_info['TCV R'])}/90")
    col5.metric("Total Player Value Rank", f"#{int(rank_info['TPV R'])}/90")
    
    st.subheader("🏆 Biggest Clients")
    st.write("(Feature Coming Soon: Auto-fetch player images and details)")

# Navigation menu
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Agent Dashboard"])

if page == "Home":
    st.title("Agent Project Insights Dashboard")
    st.subheader("Key Elements")
    st.write("- AGENT PROFILES - each agent has a profile page containing the key metrics used to evaluate agent performance.")
    st.write("- AGENCY PROFILES - similar to agent profiles, only split by agency, rather than by individual agents.")
    st.write("- KEY TAKEAWAYS - an overall look at the findings of the project and what can be learned about agent negotiation patterns")

elif page == "Agent Profiles":
    agent_dashboard()
