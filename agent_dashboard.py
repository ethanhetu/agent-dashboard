import streamlit as st
import pandas as pd
import requests
from io import BytesIO
import tempfile

# Load data from GitHub repository
@st.cache_data
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

agents_data, ranks_data = load_data()

if agents_data is None or ranks_data is None:
    st.stop()

# Streamlit App
st.set_page_config(page_title="Agent Overview", layout="wide")
st.title("🏒 Agent Overview Dashboard")

# Search functionality
agent_names = agents_data['Agent Name'].unique()
selected_agent = st.selectbox("Select an Agent:", agent_names)

# Filter data
agent_info = agents_data[agents_data['Agent Name'] == selected_agent].iloc[0]
rank_info = ranks_data[ranks_data['Agent Name'] == selected_agent].iloc[0]

# Display Agent Info
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
st.write(f"Win Percentage Rank: #{int(rank_info['WinR'])}/52")
st.write(f"Contracts Tracked Rank: #{int(rank_info['CTR'])}/52")
st.write(f"Total Contract Value Rank: #{int(rank_info['TCV R'])}/52")
st.write(f"Total Player Value Rank: #{int(rank_info['TPV R'])}/52")

st.subheader("🏆 Biggest Clients")
st.write("(Feature Coming Soon: Auto-fetch player images and details)")
