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

# ✅ Ensure this is the first Streamlit command
st.set_page_config(page_title="Agent Insights Dashboard", layout="wide")

# Global variable to store the headshots directory
HEADSHOTS_DIR = "headshots_cache"  # Persistent local directory
PLACEHOLDER_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/en/3/3a/05_NHL_Shield.svg"

# --------------------------------------------------------------------
# 1) Data-Loading & Caching Functions
# --------------------------------------------------------------------
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
    piba_data.columns = piba_data.columns.str.strip()  # Remove extra spaces in column names
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
    return agencies_data

# --------------------------------------------------------------------
# 2) Helper Functions
# --------------------------------------------------------------------
def get_headshot_path(player_name):
    """
    Attempts to retrieve the headshot path for a given player name.
    First, it tries for an exact match (ignoring DOB parts), then uses fuzzy matching
    on the first and last names if no exact match is found.
    """
    # Convert the player's name to lower-case and replace spaces with underscores.
    formatted_name = player_name.lower().replace(" ", "_")
    if HEADSHOTS_DIR and os.path.exists(HEADSHOTS_DIR):
        try:
            # Gather all headshot PNG files (excluding those with "_away")
            possible_files = [
                f for f in os.listdir(HEADSHOTS_DIR)
                if f.lower().endswith(".png") and "_away" not in f.lower()
            ]
            
            # 1) Exact matching: if any file starts with the formatted name (which is "firstname_lastname")
            for file in possible_files:
                if file.lower().startswith(formatted_name + "_"):
                    return os.path.join(HEADSHOTS_DIR, file)
            
            # 2) Fuzzy matching: build a dictionary mapping the "name part" of the file 
            # (i.e., the first two components) to the full filename.
            names_dict = {}
            for f in possible_files:
                base = f.lower().replace(".png", "")
                parts = base.split("_")
                if len(parts) >= 2:
                    # Only consider the first two parts (firstname and lastname)
                    extracted_name = "_".join(parts[:2])
                    names_dict[extracted_name] = f
            
            # Use fuzzy matching on these extracted names.
            close_matches = difflib.get_close_matches(
                formatted_name, list(names_dict.keys()), n=1, cutoff=0.75
            )
            if close_matches:
                best_match = close_matches[0]
                return os.path.join(HEADSHOTS_DIR, names_dict[best_match])
            
        except Exception as e:
            # Optionally, you can log the exception if needed.
            pass

    # Fallback: return None to trigger the placeholder image
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
        return f"<span style='color:#006400;'>${value:,.0f}</span>"  # Dark green
    else:
        return f"<span style='color:#8B0000;'>${value:,.0f}</span>"  # Dark red

def format_value_capture_percentage(value):
    color = "#006400" if value >= 1 else "#8B0000"  # Dark green if >=100%, dark red otherwise
    return f"<p style='font-weight:bold; text-align:center;'>Value Capture Percentage: <span style='color:{color};'>{value:.2%}</span></p>"

def calculate_vcp_per_year(agent_players):
    years = [
        ('2018-19', 'COST 18-19', 'PC 18-19'),
        ('2019-20', 'COST 19-20', 'PC 19-20'),
        ('2020-21', 'COST 20-21', 'PC 20-21'),
        ('2021-22', 'COST 21-22', 'PC 21-22'),
        ('2022-23', 'COST 22-23', 'PC 22-23'),
        ('2023-24', 'COST 23-24', 'PC 23-24')
    ]

    vcp_results = {}
    for year, cost_col, value_col in years:
        try:
            total_cost = agent_players[cost_col].sum()
            total_value = agent_players[value_col].sum()
            if total_value != 0:
                vcp_results[year] = round((total_cost / total_value) * 100, 2)
            else:
                vcp_results[year] = None
        except KeyError:
            vcp_results[year] = None
    return vcp_results

def plot_vcp_line_graph(vcp_per_year):
    years = list(vcp_per_year.keys())
    vcp_values = [v if v is not None else None for v in vcp_per_year.values()]

    # Manually provided average VCP values per year (yellow reference line)
    avg_vcp_values = [85.56, 103.17, 115.85, 84.30, 91.87, 108.12]

    fig = go.Figure()

    # Main VCP line
    fig.add_trace(go.Scatter(
        x=years,
        y=vcp_values,
        mode='lines+markers',
        name='Agent Value Capture Percentage',
        line=dict(color='#041E41', width=3),
        hovertemplate='%{y:.2f}%',
    ))

    # Yellow average reference line
    fig.add_trace(go.Scatter(
        x=years,
        y=avg_vcp_values,
        mode='lines+markers',
        name='Average VCP of All Agents',
        line=dict(color='#FFB819', width=3, dash='dash'),
        hovertemplate='Avg VCP: %{y:.2f}%',
    ))

    fig.update_layout(
        title="Year-by-Year Value Capture Percentage Trend",
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
                    <div style='text-align:center;'>
                        <img src="data:image/png;base64,{base64.b64encode(open(img_path, "rb").read()).decode()}" 
                             style='width:200px; height:200px; display:block; margin:auto;'/>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
                    <div style='text-align:center;'>
                        <img src="{PLACEHOLDER_IMAGE_URL}" 
                             style='width:200px; height:200px; display:block; margin:auto;'/>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            st.markdown(f"<h4 style='text-align:center; color:black; font-weight:bold; font-size:24px;'>{player['Combined Names']}</h4>", unsafe_allow_html=True)
            box_html = f"""
            <div style='border: 2px solid #ddd; padding: 10px; border-radius: 10px;'>
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

    # --- Financial Breakdown ---
    st.subheader("📊 Financial Breakdown")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Dollar Index", f"${rank_info['Dollar Index']:.2f}")
    col2.metric("Win %", f"{agent_info['Won%']:.3f}")
    col3.metric("Contracts Tracked", int(agent_info['CT']))
    col4.metric("Total Contract Value", f"${agent_info['Total Contract Value']:,.0f}")

    # --- Agent Rankings ---
    st.subheader("📈 Agent Rankings")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Dollar Index Rank", f"#{int(rank_info['Index R'])}/90")
    col2.metric("Win Percentage Rank", f"#{int(rank_info['WinR'])}/90")
    col3.metric("Contracts Tracked Rank", f"#{int(rank_info['CTR'])}/90")
    col4.metric("Total Contract Value Rank", f"#{int(rank_info['TCV R'])}/90")
    col5.metric("Total Player Value Rank", f"#{int(rank_info['TPV R'])}/90")

    # --- VCP Trend ---
    st.subheader("📅 Year-by-Year Value Capture Percentage (VCP) Trend")
    agent_players = piba_data[piba_data['Agent Name'] == selected_agent]
    vcp_per_year = calculate_vcp_per_year(agent_players)
    plot_vcp_line_graph(vcp_per_year)

    # --- Biggest Clients ---
    st.subheader("🏆 Biggest Clients")
    top_clients = agent_players.sort_values(by='Total Cost', ascending=False).head(3)
    display_player_section("Top 3 Clients by Total Cost", top_clients)

    # --- Agent 'Wins' ---
    top_delivery_clients = agent_players.sort_values(by='Dollars Captured Above/ Below Value', ascending=False).head(3)
    display_player_section("🏅 Agent 'Wins' (Top 3 by Six-Year Agent Delivery)", top_delivery_clients)

    # --- Agent 'Losses' ---
    bottom_delivery_clients = agent_players.sort_values(by='Dollars Captured Above/ Below Value', ascending=True).head(3)
    display_player_section("❌ Agent 'Losses' (Bottom 3 by Six-Year Agent Delivery)", bottom_delivery_clients)

    st.markdown("""<hr style='border: 2px solid #ccc; margin: 40px 0;'>""", unsafe_allow_html=True)

    # --- All Clients (alphabetical) ---
    st.subheader("📋 All Clients")
    agent_players['Last Name'] = agent_players['Combined Names'].apply(lambda x: x.split()[-1])
    all_clients_sorted = agent_players.sort_values(by='Last Name')
    display_player_section("All Clients (Alphabetical by Last Name)", all_clients_sorted)

def agency_dashboard():
    # Load agencies and PIBA data
    agencies_data = load_agencies_data()
    _, _, piba_data = load_data()  # from the original load_data()

    if agencies_data is None or piba_data is None:
        st.error("Error loading data for Agency Dashboard.")
        st.stop()

    st.title("Agency Overview Dashboard")

    # --- Agency Selection ---
    agency_names = agencies_data['Agency Name'].dropna().unique()
    agency_names = sorted(agency_names)
    selected_agency = st.selectbox("Select an Agency:", agency_names)

    # Pull row for selected agency
    agency_info = agencies_data[agencies_data['Agency Name'] == selected_agency].iloc[0]

    # --- Page Header ---
    st.header(f"{selected_agency}")

    # --- Financial Breakdown ---
    st.subheader("📊 Financial Breakdown")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Dollar Index", f"${agency_info['Dollar Index']:.2f}")
    col2.metric("Win %", f"{agency_info['Won%']:.3f}")
    col3.metric("Contracts Tracked", int(agency_info['CT']))
    col4.metric("Total Contract Value", f"${agency_info['Total Contract Value']:,.0f}")

    # --- Agency Rankings ---
    st.subheader("📈 Agency Rankings")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Dollar Index Rank", f"#{int(agency_info['Index R'])}/74")
    col2.metric("Win Percentage Rank", f"#{int(agency_info['WinR'])}/74")
    col3.metric("Contracts Tracked Rank", f"#{int(agency_info['CTR'])}/74")
    col4.metric("Total Contract Value Rank", f"#{int(agency_info['TCV R'])}/74")
    col5.metric("Total Player Value Rank", f"#{int(agency_info['TPV R'])}/74")

    # --- Year-by-Year VCP Trend ---
    st.subheader("📅 Year-by-Year Value Capture Percentage (VCP) Trend")
    agency_players = piba_data[piba_data['Agency Name'] == selected_agency]
    vcp_per_year = calculate_vcp_per_year(agency_players)
    plot_vcp_line_graph(vcp_per_year)

    # --- Biggest Clients ---
    st.subheader("🏆 Biggest Clients")
    top_clients = agency_players.sort_values(by='Total Cost', ascending=False).head(3)
    display_player_section("Top 3 Clients by Total Cost", top_clients)

    # --- Agency 'Wins' ---
    top_delivery_clients = agency_players.sort_values(by='Dollars Captured Above/ Below Value', ascending=False).head(3)
    display_player_section("🏅 Agency 'Wins' (Top 3 by Six-Year Agency Delivery)", top_delivery_clients)

    # --- Agency 'Losses' ---
    bottom_delivery_clients = agency_players.sort_values(by='Dollars Captured Above/ Below Value', ascending=True).head(3)
    display_player_section("❌ Agency 'Losses' (Bottom 3 by Six-Year Agency Delivery)", bottom_delivery_clients)

    st.markdown("""<hr style='border: 2px solid #ccc; margin: 40px 0;'>""", unsafe_allow_html=True)

    # --- All Clients (alphabetical) ---
    st.subheader("📋 All Clients")
    if 'Combined Names' in agency_players.columns:
        agency_players['Last Name'] = agency_players['Combined Names'].apply(lambda x: x.split()[-1])
        all_clients_sorted = agency_players.sort_values(by='Last Name')
        display_player_section("All Clients (Alphabetical by Last Name)", all_clients_sorted)
    else:
        st.write("No client names available for sorting.")

def project_definitions():
    st.title("📚 Project Definitions")
    st.write("Definitions for key terms and metrics used throughout the project.")

# --------------------------------------------------------------------
# 4) Navigation
# --------------------------------------------------------------------
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
