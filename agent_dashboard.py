import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# Load data from GitHub repository
@st.cache_data
def load_data():
    url = "https://raw.githubusercontent.com/ethanhetu/agent-dashboard/main/AP%20Final.xlsx"
    response = requests.get(url)
    xls = pd.ExcelFile(BytesIO(response.content))
    return xls.parse('Agents')

agent_data = load_data()

# Streamlit App
st.set_page_config(page_title="Agent Overview", layout="wide")
st.title("🏒 Agent Overview Dashboard")

# Search functionality
agent_names = agent_data['Agent Name'].unique()
selected_agent = st.selectbox("Select an Agent:", agent_names)

# Filter data
agent_info = agent_data[agent_data['Agent Name'] == selected_agent].iloc[0]

# Display Agent Info
st.header(f"{selected_agent} - {agent_info['Agency Name']}")
st.subheader("📊 Financial Breakdown")

col1, col2, col3, col4 = st.columns(4)
col1.metric("Market Value Capture", f"{agent_info['Market Value Capture %']:.1%}")
col2.metric("Win %", f"{agent_info['Won%']:.3f}")
col3.metric("Contracts Tracked", int(agent_info['CT']))
col4.metric("Total Contract Value", f"${agent_info['Total Contract Value']:,.0f}")

st.subheader("📈 Agent Rankings")
st.write(f"Market Value Capture Rank: #{int(agent_info['Market Value Capture %'])}/52")
st.write(f"Win Percentage Rank: #{int(agent_info['Won%'])}/52")
st.write(f"Contracts Tracked Rank: #{int(agent_info['CT'])}/52")
st.write(f"Total Contract Value Rank: #{int(agent_info['Total Contract Value'])}/52")

st.subheader("🏆 Biggest Clients")
st.write("(Feature Coming Soon: Auto-fetch player images and details)")
