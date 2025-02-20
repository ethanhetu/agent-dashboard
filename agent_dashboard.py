import streamlit as st
import pandas as pd
import requests
from io import BytesIO
import tempfile
from datetime import datetime
import zipfile
import os
import base64
import difflib
import plotly.graph_objects as go
import numpy as np

# ✅ Ensure this is the first Streamlit command
st.set_page_config(page_title="Agent Insights Dashboard", layout="wide")

# Global variables for images
HEADSHOTS_DIR = "headshots_cache"  # For player headshots
PLACEHOLDER_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/en/3/3a/05_NHL_Shield.svg"

# Globals for agent photos (unused in leaderboard now)
AGENT_PHOTOS_DIR = "agent_photos"  # Folder for agent photos from release
AGENT_PLACEHOLDER_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/8/89/Agent_placeholder.png"

# --------------------------------------------------------------------
# 1) Data-Loading & Caching Functions
# --------------------------------------------------------------------
@st.cache_data(ttl=0)
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
    agents_data.columns = agents_data.columns.str.strip()
    
    ranks_data = xls.parse('Just Agent Ranks')
    ranks_data.columns = ranks_data.columns.str.strip()
    
    piba_data = xls.parse('PIBA')
    piba_data.columns = piba_data.columns.str.strip()
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

@st.cache_data(ttl=0)
def extract_agent_photos():
    global AGENT_PHOTOS_DIR
    zip_url = "https://github.com/ethanhetu/agent-dashboard/releases/download/v1.0-agent-photos/PNGs.zip"
    if not os.path.exists(AGENT_PHOTOS_DIR):
        os.makedirs(AGENT_PHOTOS_DIR, exist_ok=True)
        zip_path = os.path.join(AGENT_PHOTOS_DIR, "PNGs.zip")
        response = requests.get(zip_url, stream=True)
        if response.status_code == 200:
            with open(zip_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(AGENT_PHOTOS_DIR)
            except zipfile.BadZipFile:
                st.error("❌ PNGs.zip is not a valid ZIP archive.")

@st.cache_data(ttl=0)
def load_agencies_data():
    url = "https://raw.githubusercontent.com/ethanhetu/agent-dashboard/main/AP%20Final.xlsx"
    response = requests.get(url)
    if response.status_code != 200:
        st.error("Error fetching Agencies data. Please check the file URL and permissions.")
        return None
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name
    xls = pd.ExcelFile(tmp_path)
    agencies_data = xls.parse('Agencies')
    agencies_data.columns = agencies_data.columns.str.strip()
    return agencies_data

# --------------------------------------------------------------------
# 2) Helper Functions
# --------------------------------------------------------------------
def correct_player_name(name):
    corrections = {
        "zotto del": "Michael Del Zotto",
        "riemsdyk van": "James Van Riemsdyk",
        "alexandre carrier a": "Alexandre Carrier",
        "lias andersson l": "Lias Andersson",
        "jesper boqvist j": "Jesper Boqvist",
        "sompel vande": "Mitch Vande Sompel",
    }
    lower_name = name.lower().strip()
    return corrections.get(lower_name, name)

def get_headshot_path(player_name):
    player_name = correct_player_name(player_name)
    formatted_name = player_name.lower().replace(" ", "_")
    if HEADSHOTS_DIR and os.path.exists(HEADSHOTS_DIR):
        try:
            possible_files = [f for f in os.listdir(HEADSHOTS_DIR) if f.lower().endswith(".png") and "_away" not in f.lower()]
            for file in possible_files:
                if file.lower().startswith(formatted_name + "_"):
                    return os.path.join(HEADSHOTS_DIR, file)
            names_dict = {}
            for f in possible_files:
                base = f.lower().replace(".png", "")
                parts = base.split("_")
                if len(parts) >= 2:
                    extracted_name = "_".join(parts[:2])
                    names_dict[extracted_name] = f
            close_matches = difflib.get_close_matches(formatted_name, list(names_dict.keys()), n=1, cutoff=0.75)
            if close_matches:
                best_match = close_matches[0]
                return os.path.join(HEADSHOTS_DIR, names_dict[best_match])
        except Exception as e:
            pass
    return None

def get_agent_photo_path(agent_name):
    formatted_name = agent_name.lower().replace(" ", "_")
    target_prefix = formatted_name + "_converted"
    for root, dirs, files in os.walk(AGENT_PHOTOS_DIR):
        for file in files:
            if file.lower().endswith((".png", ".jpg")):
                if file.lower().startswith(target_prefix):
                    return os.path.join(root, file)
    return None

def image_to_data_uri(image_path):
    try:
        with open(image_path, "rb") as img_file:
            b64_string = base64.b64encode(img_file.read()).decode('utf-8')
        return f"data:image/png;base64,{b64_string}"
    except Exception as e:
        return PLACEHOLDER_IMAGE_URL

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
    # If value is less than 1, assume it is a fraction and convert it to percentage.
    try:
        if value is not None and value < 1:
            value = value * 100
    except Exception as e:
        pass
    color = "#006400" if value >= 100 else "#8B0000"
    return f"<p style='font-weight:bold; text-align:center;'>Value Capture Percentage: <span style='color:{color};'>{value:.0f}%</span></p>"

def compute_vcp_for_agent(agent_players):
    """
    Computes VCP for a single agent (using their filtered PIBA data) for each season.
    Returns a dictionary mapping each season to that agent’s VCP.
    """
    seasons = [
        ('2018-19', 'COST 18-19', 'PC 18-19'),
        ('2019-20', 'COST 19-20', 'PC 19-20'),
        ('2020-21', 'COST 20-21', 'PC 20-21'),
        ('2021-22', 'COST 21-22', 'PC 21-22'),
        ('2022-23', 'COST 22-23', 'PC 22-23'),
        ('2023-24', 'COST 23-24', 'PC 23-24')
    ]
    results = {}
    df = agent_players.copy(deep=True)
    for season, cost_col, pc_col in seasons:
        try:
            total_cost = pd.to_numeric(df[cost_col], errors='coerce').sum()
            total_pc = pd.to_numeric(df[pc_col], errors='coerce').sum()
            if total_pc != 0:
                results[season] = round((total_cost / total_pc) * 100, 2)
            else:
                results[season] = None
        except Exception as e:
            results[season] = None
    return results

def compute_agent_vcp_by_season(piba_data):
    """
    Aggregates PIBA data to compute VCP for each agent by season.
    Converts cost and PC columns to numeric and counts clients.
    Only agents with more than 2 clients in that season are kept.
    Returns a dictionary with seasons as keys and dataframes (Agent Name, VCP) as values.
    """
    seasons = [
        ('2018-19', 'COST 18-19', 'PC 18-19'),
        ('2019-20', 'COST 19-20', 'PC 19-20'),
        ('2020-21', 'COST 20-21', 'PC 20-21'),
        ('2021-22', 'COST 21-22', 'PC 21-22'),
        ('2022-23', 'COST 22-23', 'PC 22-23'),
        ('2023-24', 'COST 23-24', 'PC 23-24')
    ]
    results = {}
    df = piba_data.copy(deep=True)
    for season, cost_col, pc_col in seasons:
        df[cost_col] = pd.to_numeric(df[cost_col], errors='coerce')
        df[pc_col] = pd.to_numeric(df[pc_col], errors='coerce')
        grouped = df.groupby('Agent Name').agg(
            total_cost=(cost_col, 'sum'),
            total_pc=(pc_col, 'sum'),
            client_count=('Agent Name', 'count')
        ).reset_index()
        grouped = grouped[grouped['client_count'] > 2]
        grouped['VCP'] = grouped.apply(
            lambda row: round((row['total_cost'] / row['total_pc']) * 100)
            if pd.notnull(row['total_pc']) and row['total_pc'] != 0 else None,
            axis=1
        )
        results[season] = grouped[['Agent Name', 'VCP']]
    return results

def plot_vcp_line_graph(vcp_per_year):
    seasons = ['2018-19', '2019-20', '2020-21', '2021-22', '2022-23', '2023-24']
    vcp_values = [vcp_per_year.get(season, np.nan) for season in seasons]
    avg_vcp_values = [85.56, 103.17, 115.85, 84.30, 91.87, 108.12]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=seasons,
        y=vcp_values,
        mode='lines+markers',
        name='Agent VCP',
        line=dict(color='#041E41', width=3),
        hovertemplate='%{y:.0f}%',
    ))
    fig.add_trace(go.Scatter(
        x=seasons,
        y=avg_vcp_values,
        mode='lines+markers',
        name='League Average VCP',
        line=dict(color='#FFB819', width=3, dash='dash'),
        hovertemplate='Avg VCP: %{y:.0f}%',
    ))
    fig.update_layout(
        title="Year-by-Year VCP Trend",
        xaxis=dict(title='Year'),
        yaxis=dict(title='VCP (%)', range=[0, 200]),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
    )
    st.plotly_chart(fig, use_container_width=True)

def display_player_section(title, player_df):
    st.subheader(title)
    client_cols = st.columns(3)
    for idx, (_, player) in enumerate(player_df.iterrows()):
        with client_cols[idx % 3]:
            img_path = get_headshot_path(player['Combined Names'])
            if img_path:
                st.markdown(
                    f"""
                    <div style="text-align:center;">
                        <img src="data:image/png;base64,{base64.b64encode(open(img_path, "rb").read()).decode()}"
                             style="width:200px; height:200px; display:block; margin:auto;"/>
                    </div>
                    """, unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"""
                    <div style="text-align:center;">
                        <img src="{PLACEHOLDER_IMAGE_URL}"
                             style="width:200px; height:200px; display:block; margin:auto;"/>
                    </div>
                    """, unsafe_allow_html=True
                )
            display_name = correct_player_name(player['Combined Names'])
            st.markdown(f"<h4 style='text-align:center; color:black; font-weight:bold; font-size:24px;'>{display_name}</h4>", unsafe_allow_html=True)
            box_html = f"""
            <div style="border: 2px solid #ddd; padding: 10px; border-radius: 10px;">
                <p><strong>Age:</strong> {calculate_age(player['Birth Date'])}</p>
                <p><strong>Six-Year Agent Delivery:</strong> {format_delivery_value(player['Dollars Captured Above/ Below Value'])}</p>
                <p><strong>Six-Year Player Cost:</strong> ${player['Total Cost']:,.0f}</p>
                <p><strong>Six-Year Player Value:</strong> ${player['Total PC']:,.0f}</p>
            </div>
            {format_value_capture_percentage(player['Value Capture %'])}
            """
            st.markdown(box_html, unsafe_allow_html=True)

# --------------------------------------------------------------------
# 3) Main Dashboard Pages
# --------------------------------------------------------------------
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
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.header(f"{selected_agent} - {agent_info['Agency Name']}")
    st.subheader("
