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

    # Save file to a temporary location
    with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    xls = pd.ExcelFile(tmp_path)
    agents_data = xls.parse('Agents')
    ranks_data = xls.parse('Just Agent Ranks')
    piba_data = xls.parse('PIBA')
    return agents_data, ranks_data, piba_data

# ✅ Download and extract the full headshots ZIP from GitHub Releases
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
                st.error(f"❌ NHL.Headshots.zip is not a valid ZIP archive. Please verify file integrity.")
            except Exception as e:
                st.error(f"❌ Extraction failed: {e}")

# Function to retrieve headshot path based on player name
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

# Function to calculate age from birthdate
def calculate_age(birthdate):
    try:
        birth_date = pd.to_datetime(birthdate)
        today = datetime.today()
        return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
    except:
        return "N/A"

def home_page():
    st.title("🏒 Welcome to the Agent Insights Dashboard")
    st.write("This site provides detailed insights on player agents, rankings, and financial statistics.")
    st.subheader("Key Takeaways")
    st.write("- Agents are ranked based on financial efficiency and contract success.")
    st.write("- Player and agent trends reveal negotiation patterns.")
    st.write("- Use the Agent Dashboard for deep dives into individual agents.")

def agent_dashboard():
    agents_data, ranks_data, piba_data = load_data()
    extract_headshots()

    if agents_data is None or ranks_data is None or piba_data is None:
        st.stop()

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

    # Horizontal card layout for top clients
    agent_players = piba_data[piba_data['Agent Name'] == selected_agent]
    top_clients = agent_players.sort_values(by='Total Cost', ascending=False).head(3)

    client_cols = st.columns(len(top_clients))
    for idx, (_, player) in enumerate(top_clients.iterrows()):
        with client_cols[idx]:
            img_path = get_headshot_path(player['Combined Names'])
            if img_path:
                st.image(img_path, width=200)
            else:
                st.image("https://raw.githubusercontent.com/ethanhetu/agent-dashboard/main/headshots/placeholder.png", width=200)

            st.markdown(f"<h4 style='text-align:center; color:black; font-weight:bold;'>{player['Combined Names']}</h4>", unsafe_allow_html=True)
            st.markdown(f"**Age:** {calculate_age(player['Birth Date'])}")
            st.markdown(f"**Six-Year Agent Delivery:** ${player['Dollars Captured Above/ Below Value']:,.0f}")
            st.markdown(f"**Value Capture Percentage:** {player['Value Capture %']:.2%}")
            st.markdown(f"**Six-Year Player Cost:** ${player['Total Cost']:,.0f}")
            st.markdown(f"**Six-Year Player Contribution:** ${player['Total PC']:,.0f}")

def project_definitions():
    st.title("📚 Project Definitions")
    st.write("This section defines key terms and metrics used throughout the project.")

    st.subheader("Key Terms")
    st.markdown("""
    - **Dollar Index**: Represents the financial efficiency of an agent relative to market value.
    - **Win %**: The percentage of successful contract negotiations based on defined criteria.
    - **Contracts Tracked**: Total number of contracts managed by the agent included in this dataset.
    - **Total Contract Value**: The cumulative monetary value of all tracked contracts for an agent.
    - **Total Player Value**: Estimated total on-ice contributions from all players represented by the agent.
    - **Six-Year Agent Delivery**: Shows how much more or less the player earned compared to their market value over six years.
    - **Value Capture Percentage:** The percentage of the player's market value actually captured in earnings.
    - **Six-Year Player Cost:** The total cost of a player's contract over six years.
    - **Six-Year Player Contribution:** The total on-ice contributions from a player over six years.
    """)

    st.subheader("How to Interpret Rankings")
    st.write("Higher ranks indicate better performance relative to peers in the dataset. For example, a higher Dollar Index rank reflects greater financial efficiency.")

# Navigation menu
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Agent Dashboard", "Project Definitions"])

if page == "Home":
    home_page()
elif page == "Agent Dashboard":
    agent_dashboard()
elif page == "Project Definitions":
    project_definitions()
