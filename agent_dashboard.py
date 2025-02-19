import streamlit as st
import pandas as pd
import requests
from io import BytesIO
import tempfile
from datetime import datetime
import zipfile
import os

# ✅ Ensure this is the first Streamlit command
st.set_page_config(page_title="Agent Insights Dashboard", layout="wide")

# Global variable to store the headshots directory
HEADSHOTS_DIR = "headshots_cache"  # Persistent local directory

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

# Retrieve headshot path
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

# Calculate age
def calculate_age(birthdate):
    try:
        birth_date = pd.to_datetime(birthdate)
        today = datetime.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except:
        return "N/A"

# Color Six-Year Agent Delivery
def format_delivery_value(value):
    if value > 0:
        return f"<span style='color:#228B22;'>${value:,.0f}</span>"
    else:
        return f"<span style='color:#B22222;'>${value:,.0f}</span>"

def home_page():
    st.title("🏒 Welcome to the Agent Insights Dashboard")
    st.write("Detailed insights on player agents, rankings, and financial statistics.")

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
    agent_players = piba_data[piba_data['Agent Name'] == selected_agent]
    top_clients = agent_players.sort_values(by='Total Cost', ascending=False).head(3)

    client_cols = st.columns(len(top_clients))
    for idx, (_, player) in enumerate(top_clients.iterrows()):
        with client_cols[idx]:
            img_path = get_headshot_path(player['Combined Names'])
            if img_path:
                st.image(img_path, width=237, use_container_width=False)
            else:
                st.image("https://raw.githubusercontent.com/ethanhetu/agent-dashboard/main/headshots/placeholder.png", width=237)

            st.markdown(f"<h4 style='text-align:center; color:black; font-weight:bold; font-size:24px;'>{player['Combined Names']}</h4>", unsafe_allow_html=True)
            box_html = f"""
            <div style='border: 2px solid #ddd; padding: 10px; border-radius: 10px;'>
                <p><strong>Age:</strong> {calculate_age(player['Birth Date'])}</p>
                <p><strong>Six-Year Agent Delivery:</strong> {format_delivery_value(player['Dollars Captured Above/ Below Value'])}</p>
                <p><strong>Six-Year Player Cost:</strong> ${player['Total Cost']:,.0f}</p>
                <p><strong>Six-Year Player Value:</strong> ${player['Total PC']:,.0f}</p>
            </div>
            <p style='font-weight:bold; text-align:center;'>Value Capture Percentage: {player['Value Capture %']:.2%}</p>
            """
            st.markdown(box_html, unsafe_allow_html=True)

def project_definitions():
    st.title("📚 Project Definitions")
    st.write("Definitions for key terms and metrics used throughout the project.")

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Agent Dashboard", "Project Definitions"])

if page == "Home":
    home_page()
elif page == "Agent Dashboard":
    agent_dashboard()
elif page == "Project Definitions":
    project_definitions()
