import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# Load data from GitHub repository
@st.cache_data
def load_data():
    url_agents = "https://raw.githubusercontent.com/ethanhetu/agent-dashboard/main/AP%20Final.xlsx"
    response = requests.get(url_agents)
    xls = pd.ExcelFile(BytesIO(response.content))
    agents_data = xls.parse('Agents')
    ranks_data = xls.parse('Just Agent Ranks')
    return agents_data, ranks_data

agents_data, ranks_data = load_data()

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
col1.metric("Dollar Index", f"{rank_info['Dollar Index']:.2f}")
col2.metric("Win %", f"{agent_info['Won%']:.3f}")
col3.metric("Contracts Tracked", int(agent_info['CT']))
col4.metric("Total Contract Value", f"${agent_info['Total Contract Value']:,.0f}")

st.subheader("📈 Agent Rankings")
st.write(f"Dollar Index Rank: #{int(rank_info['Index R'])}/52")
st.write(f"Win Percentage Rank: #{int(rank_info['WinR'])}/52")
st.write(f"Contracts Tracked Rank: #{int(rank_info['CTR'])}/52")
st.write(f"Total Contract Value Rank: #{int(rank_info['TCV R'])}/52")
st.write(f"Total Player Value Rank: #{int(rank_info['TPV R'])}/52")

st.subheader("🏆 Biggest Clients")
st.write("(Feature Coming Soon: Auto-fetch player images and details)")
