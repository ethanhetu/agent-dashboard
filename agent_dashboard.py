import streamlit as st
import pandas as pd
import requests
from io import BytesIO
import tempfile
from datetime import datetime

# ✅ Ensure this is the first Streamlit command
st.set_page_config(page_title="Agent Insights Dashboard", layout="wide")

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

# Function to retrieve headshot URL based on player name
def get_headshot_url(player_name):
    base_url = "https://raw.githubusercontent.com/ethanhetu/agent-dashboard/main/headshots/"
    formatted_name = player_name.lower().replace(" ", "_")

    # Fetch headshot file list from GitHub
    headshots_list = requests.get(
        "https://api.github.com/repos/ethanhetu/agent-dashboard/contents/headshots"
    ).json()

    # Filter matching files ignoring extra suffixes
    matches = [file["name"] for file in headshots_list if file["name"].lower().startswith(formatted_name + "_")]

    if matches:
        # Prioritize the file without '_away' if duplicates exist
        matches.sort(key=lambda x: 1 if "_away" in x else 0)
        return base_url + matches[0]

    # Default placeholder image if no match found
    return "https://raw.githubusercontent.com/ethanhetu/agent-dashboard/main/headshots/placeholder.png"

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

    # Filter PIBA data for the selected agent and get top 3 clients by Total Cost
    agent_players = piba_data[piba_data['Agent Name'] == selected_agent]
    top_clients = agent_players.sort_values(by='Total Cost', ascending=False).head(3)

    for _, player in top_clients.iterrows():
        player_col1, player_col2 = st.columns([1, 4])
        with player_col1:
            st.image(get_headshot_url(player['Combined Names']), width=100)
        with player_col2:
            st.markdown(f"**{player['Combined Names']}**")
            st.write(f"**Age:** {calculate_age(player['Birth Date'])}")
            st.write(f"**Dollars Captured Above/Below Market Value:** ${player['Dollars Captured Above/ Below Value']:,.0f}")
            st.write(f"**Value Capture Percentage:** {player['Value Capture %']:.2%}")
            st.write(f"**Total Cost:** ${player['Total Cost']:,.0f}")
            st.write(f"**Total PC:** ${player['Total PC']:,.0f}")

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
    - **Dollars Captured Above/Below Market Value**: Shows how much more or less the player earned compared to their market value.
    - **Value Capture Percentage**: The percentage of the player's market value actually captured in earnings.
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
