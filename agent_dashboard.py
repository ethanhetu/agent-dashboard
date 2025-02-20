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
        return None, None, None, None

    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    xls = pd.ExcelFile(tmp_path)
    agents_data = xls.parse('Agents')
    agencies_data = xls.parse('Agencies')
    ranks_data = xls.parse('Just Agent Ranks')
    piba_data = xls.parse('PIBA')
    piba_data.columns = piba_data.columns.str.strip()  # Remove extra spaces in column names
    return agents_data, agencies_data, ranks_data, piba_data

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

def get_headshot_path(player_name):
    formatted_name = player_name.lower().replace(" ", "_")
    if HEADSHOTS_DIR and os.path.exists(HEADSHOTS_DIR):
        try:
            for file in os.listdir(HEADSHOTS_DIR):
                if file.lower().startswith(formatted_name + "_") and file.endswith(".png"):
                    if "_away" not in file:
                        return os.path.join(HEADSHOTS_DIR, file)
            for file in os.listdir(HEADSHOTS_DIR):
                if file.lower().startswith(formatted_name + "_"):
                    return os.path.join(HEADSHOTS_DIR, file)
        except:
            pass
    return None

def calculate_age(birthdate):
    try:
        birth_date = pd.to_datetime(birthdate)
        today = datetime.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except:
        return "N/A"

def format_delivery_value(value):
    if value > 0:
        return f"<span style='color:#006400;'>${value:,.0f}</span>"
    else:
        return f"<span style='color:#8B0000;'>${value:,.0f}</span>"

def format_value_capture_percentage(value):
    color = "#006400" if value >= 1 else "#8B0000"
    return f"<p style='font-weight:bold; text-align:center;'>Value Capture Percentage: <span style='color:{color};'>{value:.2%}</span></p>"

def plot_vcp_line_graph(vcp_per_year):
    years = list(vcp_per_year.keys())
    vcp_values = [v if v is not None else None for v in vcp_per_year.values()]
    avg_vcp_values = [85.56, 103.17, 115.85, 84.30, 91.87, 108.12]

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=vcp_values, mode='lines+markers', name='VCP', line=dict(color='#041E41', width=3)))
    fig.add_trace(go.Scatter(x=years, y=[100] * len(years), mode='lines', name='100% Reference', line=dict(color='red', width=2, dash='dot')))
    fig.add_trace(go.Scatter(x=years, y=avg_vcp_values, mode='lines+markers', name='Average VCP', line=dict(color='#FFB819', width=3, dash='dash')))

    fig.update_layout(title="Year-by-Year Value Capture Percentage Trend", xaxis=dict(title='Year', tickangle=0), yaxis=dict(title='VCP (%)', range=[0, 200]), legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))

    st.plotly_chart(fig, use_container_width=True)

def display_financial_overview(group_info, total_entities=None):
    st.subheader("📊 Financial Overview")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Dollar Index", f"${group_info['Dollar Index']:.2f}")
    col2.metric("Win %", f"{group_info['Won%']:.3f}")
    col3.metric("Contracts Tracked", int(group_info['CT']))
    col4.metric("Total Contract Value", f"${group_info['Total Contract Value']:,.0f}")
    if total_entities is not None and 'Overall Rank' in group_info:
        col5.metric("Ranking", f"#{int(group_info['Overall Rank'])}/{total_entities}")

def dashboard_template(group_name, group_by_column, summary_data, piba_data, total_entities):
    st.title(f"{group_name} Overview Dashboard")
    unique_groups = summary_data[group_by_column].dropna().unique()
    selected_group = st.selectbox(f"Select a {group_name}:", sorted(unique_groups))

    group_info = summary_data[summary_data[group_by_column] == selected_group].iloc[0]
    display_financial_overview(group_info, total_entities)

    group_players = piba_data[piba_data[group_by_column] == selected_group]
    vcp_per_year = calculate_vcp_per_year(group_players)
    plot_vcp_line_graph(vcp_per_year)

    st.subheader("🏆 Biggest Clients")
    top_clients = group_players.sort_values(by='Total Cost', ascending=False).head(3)
    display_player_section("Top 3 Clients by Total Cost", top_clients)

    top_delivery_clients = group_players.sort_values(by='Dollars Captured Above/ Below Value', ascending=False).head(3)
    display_player_section("🏅 'Wins' (Top 3 by Six-Year Agent Delivery)", top_delivery_clients)

    bottom_delivery_clients = group_players.sort_values(by='Dollars Captured Above/ Below Value', ascending=True).head(3)
    display_player_section("❌ 'Losses' (Bottom 3 by Six-Year Agent Delivery)", bottom_delivery_clients)

    st.markdown("""<hr style='border: 2px solid #ccc; margin: 40px 0;'>""", unsafe_allow_html=True)

    st.subheader("📋 All Clients")
    group_players['Last Name'] = group_players['Combined Names'].apply(lambda x: x.split()[-1])
    all_clients_sorted = group_players.sort_values(by='Last Name')
    display_player_section("All Clients (Alphabetical by Last Name)", all_clients_sorted)

def agent_dashboard():
    agents_data, agencies_data, ranks_data, piba_data = load_data()
    extract_headshots()
    dashboard_template("Agent", "Agent Name", agents_data, piba_data, 90)

def agency_dashboard():
    agents_data, agencies_data, ranks_data, piba_data = load_data()
    extract_headshots()
    dashboard_template("Agency", "Agency Name", agencies_data, piba_data, 74)

def project_definitions():
    st.title("📚 Project Definitions")
    st.write("Definitions for key terms and metrics used throughout the project.")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Agent Dashboard", "Agency Dashboard", "Project Definitions"])

if page == "Home":
    st.title("Welcome to the Agent Insights Dashboard!")
elif page == "Agent Dashboard":
    agent_dashboard()
elif page == "Agency Dashboard":
    agency_dashboard()
elif page == "Project Definitions":
    project_definitions()
