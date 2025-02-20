import streamlit as st
import pandas as pd
import requests
from io import BytesIO
import tempfile
from datetime import datetime
import zipfile
import os
import base64
import plotly.graph_objects as go

# ✅ Ensure this is the first Streamlit command
st.set_page_config(page_title="Agent Insights Dashboard", layout="wide")

# Global variable to store the headshots directory
HEADSHOTS_DIR = "headshots_cache"  # Persistent local directory
PLACEHOLDER_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/en/3/3a/05_NHL_Shield.svg"

# Load data from GitHub repository
@st.cache_data(ttl=0)  # Forces reload every time
def load_data():
    url_agents = "https://raw.githubusercontent.com/ethanhetu/agent-dashboard/main/AP%20Final.xlsx"
    response = requests.get(url_agents)

    if response.status_code != 200:
        st.error("Error fetching data. Please check the file URL and permissions.")
        return None, None, None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    xls = pd.ExcelFile(tmp_path)
    agents_data = xls.parse('Agents')
    ranks_data = xls.parse('Just Agent Ranks')
    piba_data = xls.parse('PIBA')
    piba_data.columns = piba_data.columns.str.strip().str.replace(" ", "_")  # Normalize column names
    return agents_data, ranks_data, piba_data

@st.cache_data(ttl=0)
def extract_headshots():
    global HEADSHOTS_DIR
    zip_url = "https://github.com/ethanhetu/agent-dashboard/releases/download/v1.0-headshots-full/NHL.Headshots.zip"

    if not os.path.exists(HEADSHOTS_DIR):
        os.makedirs(HEADSHOTS_DIR, exist_ok=True)
        zip_path = os.path.join(HEADSHOTS_DIR, "NHL.Headshots.zip")
        response = requests.get(zip_url, stream=True)

        if response.status_code == 200:
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(HEADSHOTS_DIR)
            except zipfile.BadZipFile:
                st.error("❌ NHL.Headshots.zip is not a valid ZIP archive.")

# Calculate VCP per year for the agent
def calculate_vcp_per_year(agent_players):
    years = [
        ('2018-19', 'COST_18-19', 'PC_18-19'),
        ('2019-20', 'COST_19-20', 'PC_19-20'),
        ('2020-21', 'COST_20-21', 'PC_20-21'),
        ('2021-22', 'COST_21-22', 'PC_21-22'),
        ('2022-23', 'COST_22-23', 'PC_22-23'),
        ('2023-24', 'COST_23-24', 'PC_23-24')
    ]

    vcp_results = {}
    for year, cost_col, value_col in years:
        if cost_col in agent_players.columns and value_col in agent_players.columns:
            total_cost = agent_players[cost_col].sum()
            total_value = agent_players[value_col].sum()
            vcp_results[year] = round((total_cost / total_value) * 100, 2) if total_value != 0 else None
        else:
            vcp_results[year] = None
    return vcp_results

# Calculate average VCP per year across all players
def calculate_average_vcp_per_year(piba_data):
    years = [
        ('2018-19', 'COST_18-19', 'PC_18-19'),
        ('2019-20', 'COST_19-20', 'PC_19-20'),
        ('2020-21', 'COST_20-21', 'PC_20-21'),
        ('2021-22', 'COST_21-22', 'PC_21-22'),
        ('2022-23', 'COST_22-23', 'PC_22-23'),
        ('2023-24', 'COST_23-24', 'PC_23-24')
    ]

    avg_vcp = {}
    for year, cost_col, value_col in years:
        if cost_col in piba_data.columns and value_col in piba_data.columns:
            total_cost = piba_data[cost_col].sum()
            total_value = piba_data[value_col].sum()
            avg_vcp[year] = round((total_cost / total_value) * 100, 2) if total_value != 0 else None
        else:
            avg_vcp[year] = None
    return avg_vcp

# Plot the VCP line graph using Plotly with customizations
def plot_vcp_line_graph(vcp_per_year, avg_vcp_per_year):
    years = list(vcp_per_year.keys())
    vcp_values = [v if v is not None else None for v in vcp_per_year.values()]
    avg_vcp_values = [v if v is not None else None for v in avg_vcp_per_year.values()]

    fig = go.Figure()

    # Main VCP line
    fig.add_trace(go.Scatter(
        x=years,
        y=vcp_values,
        mode='lines+markers',
        name='Agent VCP',
        line=dict(color='#041E41', width=3),
        hovertemplate='%{y:.2f}%'
    ))

    # 100% reference line (red dotted)
    fig.add_trace(go.Scatter(
        x=years,
        y=[100] * len(years),
        mode='lines',
        name='100% Reference',
        line=dict(color='red', width=2, dash='dot')
    ))

    # Average VCP reference line (yellow)
    fig.add_trace(go.Scatter(
        x=years,
        y=avg_vcp_values,
        mode='lines+markers',
        name='Average VCP (All Players)',
        line=dict(color='#FFB819', width=3, dash='dash'),
        hovertemplate='Avg VCP: %{y:.2f}%'
    ))

    fig.update_layout(
        title="Year-by-Year Value Capture Percentage Trend",
        xaxis=dict(title='Year', tickangle=0),
        yaxis=dict(title='VCP (%)', range=[0, 200]),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

def agent_dashboard():
    agents_data, ranks_data, piba_data = load_data()
    extract_headshots()

    if agents_data is None or ranks_data is None or piba_data is None:
        st.stop()

    st.title("Agent Overview Dashboard")

    agent_names = ranks_data['Agent Name'].dropna().replace(['', '(blank)', 'Grand Total'], pd.NA).dropna()
    agent_names = sorted(agent_names, key=lambda name: name.split()[-1])
    selected_agent = st.selectbox("Select an Agent:", agent_names)

    agent_info = agents_data[agents_data['Agent Name'] == selected_agent].iloc[0]
    rank_info = ranks_data[ranks_data['Agent Name'] == selected_agent].iloc[0]

    st.header(f"{selected_agent} - {agent_info['Agency Name']}")

    st.subheader("📅 Year-by-Year Value Capture Percentage (VCP) Trend")
    agent_players = piba_data[piba_data['Agent Name'] == selected_agent]
    vcp_per_year = calculate_vcp_per_year(agent_players)
    avg_vcp_per_year = calculate_average_vcp_per_year(piba_data)
    plot_vcp_line_graph(vcp_per_year, avg_vcp_per_year)

def project_definitions():
    st.title("📚 Project Definitions")
    st.write("Definitions for key terms and metrics used throughout the project.")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Agent Dashboard", "Project Definitions"])

if page == "Home":
    st.title("Welcome to the Agent Insights Dashboard!")
elif page == "Agent Dashboard":
    agent_dashboard()
elif page == "Project Definitions":
    project_definitions()
