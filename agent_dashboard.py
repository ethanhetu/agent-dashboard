import streamlit as st
import pandas as pd
import requests
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
        except Exception:
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
    except Exception:
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
    try:
        if value is not None and value < 2:
            value = value * 100
    except Exception:
        pass
    color = "#006400" if value >= 100 else "#8B0000"
    return f"<p style='font-weight:bold; text-align:center;'>Value Capture Percentage: <span style='color:{color};'>{value:.0f}%</span></p>"

def compute_vcp_for_agent(agent_players):
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
        except Exception:
            results[season] = None
    return results

def compute_agent_vcp_by_season(piba_data):
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
            try:
                vcp_value = (player['Total Cost'] / player['Total PC']) * 100
            except Exception:
                vcp_value = None
            box_html = f"""
            <div style="border: 2px solid #ddd; padding: 10px; border-radius: 10px;">
                <p><strong>Age:</strong> {calculate_age(player['Birth Date'])}</p>
                <p><strong>Six-Year Agent Delivery:</strong> {format_delivery_value(player['Dollars Captured Above/ Below Value'])}</p>
                <p><strong>Six-Year Player Cost:</strong> ${player['Total Cost']:,.0f}</p>
                <p><strong>Six-Year Player Value:</strong> ${player['Total PC']:,.0f}</p>
            </div>
            """
            st.markdown(box_html, unsafe_allow_html=True)
            if vcp_value is not None:
                color = "#006400" if vcp_value >= 100 else "#8B0000"
                st.markdown(f"<p style='font-weight:bold; text-align:center;'>Percent of Value Captured: <span style='color:{color};'>{vcp_value:.0f}%</span></p>", unsafe_allow_html=True)

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
    st.subheader("📅 Year-by-Year VCP Trend")
    agent_players = piba_data[piba_data['Agent Name'] == selected_agent]
    vcp_for_agent = compute_vcp_for_agent(agent_players)
    plot_vcp_line_graph(vcp_for_agent)
    st.subheader("🏆 Biggest Clients")
    top_clients = agent_players.sort_values(by='Total Cost', ascending=False).head(3)
    display_player_section("Top 3 Clients by Total Cost", top_clients)
    top_delivery_clients = agent_players.sort_values(by='Dollars Captured Above/ Below Value', ascending=False).head(3)
    display_player_section("🏅 Agent 'Wins' (Top 3 by Six-Year Agent Delivery)", top_delivery_clients)
    bottom_delivery_clients = agent_players.sort_values(by='Dollars Captured Above/ Below Value', ascending=True).head(3)
    display_player_section("❌ Agent 'Losses' (Bottom 3 by Six-Year Agent Delivery)", bottom_delivery_clients)
    st.markdown("""<hr style="border: 2px solid #ccc; margin: 40px 0;">""", unsafe_allow_html=True)
    st.subheader("📋 All Clients")
    agent_players['Last Name'] = agent_players['Combined Names'].apply(lambda x: x.split()[-1])
    all_clients_sorted = agent_players.sort_values(by='Last Name')
    display_player_section("All Clients (Alphabetical by Last Name)", all_clients_sorted)

def agency_dashboard():
    agencies_data = load_agencies_data()
    _, _, piba_data = load_data()
    if agencies_data is None or piba_data is None:
        st.error("Error loading data for Agency Dashboard.")
        st.stop()
    st.title("Agency Overview Dashboard")
    agency_names = agencies_data['Agency Name'].dropna().unique()
    agency_names = sorted(agency_names)
    selected_agency = st.selectbox("Select an Agency:", agency_names)
    agency_info = agencies_data[agencies_data['Agency Name'] == selected_agency].iloc[0]
    st.header(f"{selected_agency}")
    st.subheader("📊 Financial Breakdown")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Dollar Index", f"${agency_info['Dollar Index']:.2f}")
    col2.metric("Win %", f"{agency_info['Won%']:.3f}")
    col3.metric("Contracts Tracked", int(agency_info['CT']))
    col4.metric("Total Contract Value", f"${agency_info['Total Contract Value']:,.0f}")
    st.subheader("📈 Agency Rankings")
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Dollar Index Rank", f"#{int(agency_info['Index R'])}/74")
    col2.metric("Win Percentage Rank", f"#{int(agency_info['WinR'])}/74")
    col3.metric("Contracts Tracked Rank", f"#{int(agency_info['CTR'])}/74")
    col4.metric("Total Contract Value Rank", f"#{int(agency_info['TCV R'])}/74")
    col5.metric("Total Player Value Rank", f"#{int(agency_info['TPV R'])}/74")
    st.subheader("📅 Year-by-Year VCP Trend")
    agency_players = piba_data[piba_data['Agency Name'] == selected_agency]
    vcp_for_agency = compute_vcp_for_agent(agency_players)
    plot_vcp_line_graph(vcp_for_agency)
    st.subheader("🏆 Biggest Clients")
    top_clients = agency_players.sort_values(by='Total Cost', ascending=False).head(3)
    display_player_section("Top 3 Clients by Total Cost", top_clients)
    top_delivery_clients = agency_players.sort_values(by='Dollars Captured Above/ Below Value', ascending=False).head(3)
    display_player_section("🏅 Agency 'Wins' (Top 3 by Six-Year Agent Delivery)", top_delivery_clients)
    bottom_delivery_clients = agency_players.sort_values(by='Dollars Captured Above/ Below Value', ascending=True).head(3)
    display_player_section("❌ Agency 'Losses' (Bottom 3 by Six-Year Agent Delivery)", bottom_delivery_clients)
    st.markdown("""<hr style="border: 2px solid #ccc; margin: 40px 0;">""", unsafe_allow_html=True)
    st.subheader("📋 All Clients")
    if 'Combined Names' in agency_players.columns:
        agency_players['Last Name'] = agency_players['Combined Names'].apply(lambda x: x.split()[-1])
        all_clients_sorted = agency_players.sort_values(by='Last Name')
        display_player_section("All Clients (Alphabetical by Last Name)", all_clients_sorted)
    else:
        st.write("No client names available for sorting.")

def leaderboard_page():
    st.title("Agent Leaderboard")
    agents_data, ranks_data, piba_data = load_data()
    if agents_data is None or ranks_data is None or piba_data is None:
        st.error("Error loading data for leaderboard.")
        st.stop()

    # Define manual exclusion list.
    excluded_agents = {"Patrik Aronsson", "Chris McAlpine", "David Kaye", "Thomas Lynn", "Patrick Sullivan"}

    # Build valid agent list from the Agents tab and exclude manually.
    valid_agents = set(agents_data['Agent Name'].dropna().str.strip())
    valid_agents = valid_agents - excluded_agents
    # Filter out agents not in valid_agents from both ranks_data and piba_data.
    ranks_data = ranks_data[ranks_data['Agent Name'].str.strip().isin(valid_agents)]
    piba_data = piba_data[piba_data['Agent Name'].str.strip().isin(valid_agents)]
    
    st.subheader("Overall Standings (by Dollar Index)")
    filter_option = st.checkbox("Only show agents with at least 10 Contracts Tracked", value=False)

    overall_table = ranks_data[['Agent Name', 'Agency Name', 'Dollar Index', 'CT']].sort_values(by='Dollar Index', ascending=False)
    if filter_option:
        overall_table = overall_table[overall_table['CT'] >= 10]
    overall_table = overall_table.head(90)

    for rank, (_, row) in enumerate(overall_table.iterrows(), start=1):
        agent_name = row['Agent Name']
        agency = row['Agency Name']
        dollar_index = row['Dollar Index']
        contracts = row['CT']
        card_html = f"""
        <div style="display: flex; align-items: center; border: 1px solid #ccc; border-radius: 8px; padding: 8px; margin-bottom: 8px;">
            <div style="flex: 0 0 40px; text-align: center; font-size: 18px; font-weight: bold;">
                {rank}.
            </div>
            <div style="flex: 1; margin-left: 16px; font-size: 18px; font-weight: bold;">
                {agent_name} <br/><span style="font-size: 14px; font-weight: normal;">{agency}</span>
            </div>
            <div style="flex: 0 0 150px; text-align: right; font-size: 16px;">
                <div style="border-left: 1px solid #ccc; padding-left: 8px;">
                    <div style="font-weight: bold;">${dollar_index:,.2f}</div>
                    <div style="font-size: 14px;">Contracts Tracked: {int(round(contracts))}</div>
                </div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Year-by-Year, Which Agents Did Best and Worst?")
    # Create mapping from agent name to agency using filtered ranks_data.
    agency_map = dict(zip(ranks_data["Agent Name"].str.strip(), ranks_data["Agency Name"].str.strip()))
    agent_vcp_by_season = compute_agent_vcp_by_season(piba_data)

    for season in sorted(agent_vcp_by_season.keys(), reverse=True):
        df = agent_vcp_by_season[season]
        st.markdown(f"### {season}")
        winners = df.sort_values(by='VCP', ascending=False).head(5).reset_index(drop=True)
        losers = df.sort_values(by='VCP', ascending=True).head(5).reset_index(drop=True)

        col_head1, col_head2 = st.columns(2)
        with col_head1:
            st.markdown("#### Five Biggest 'Winners' of the Year")
        with col_head2:
            st.markdown("#### Five Biggest 'Losers' of the Year")

        for i in range(max(len(winners), len(losers))):
            cols = st.columns(2)
            with cols[0]:
                if i < len(winners):
                    w = winners.loc[i]
                    agency = agency_map.get(w['Agent Name'].strip(), "")
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; border: 1px solid #ccc; border-radius: 8px; padding: 8px; margin-bottom: 8px;">
                        <div style="flex: 1; font-size: 16px; font-weight: bold;">
                            {w['Agent Name']}<br/><span style="font-size: 14px; font-weight: normal;">{agency}</span>
                        </div>
                        <div style="flex: 0 0 80px; text-align: right; font-size: 16px; border-left: 1px solid #ccc; padding-left: 8px;">
                            <span style="font-weight: bold;">{w['VCP']:.0f}%</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
            with cols[1]:
                if i < len(losers):
                    l = losers.loc[i]
                    agency = agency_map.get(l['Agent Name'].strip(), "")
                    st.markdown(f"""
                    <div style="display: flex; align-items: center; border: 1px solid #ccc; border-radius: 8px; padding: 8px; margin-bottom: 8px;">
                        <div style="flex: 1; font-size: 16px; font-weight: bold;">
                            {l['Agent Name']}<br/><span style="font-size: 14px; font-weight: normal;">{agency}</span>
                        </div>
                        <div style="flex: 0 0 80px; text-align: right; font-size: 16px; border-left: 1px solid #ccc; padding-left: 8px;">
                            <span style="font-weight: bold;">{l['VCP']:.0f}%</span>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

# --------------------------------------------------------------------
# 4) NEW: Second Contracts Leaderboard Page
# --------------------------------------------------------------------
def second_contracts_leaderboard_page():
    """
    Displays a page similar to the 'leaderboard' page, but for second contracts only.
    We automatically map agent names to their agencies from ranks_data.
    """
    st.title("Second Contracts Leaderboard")
    st.subheader("Overall Standings - Second Contracts (by Dollar Index)")

    # 1) Load main data so we can build the agency_map
    agents_data, ranks_data, piba_data = load_data()

    # 2) Create a map from agent name -> agency name
    agency_map = dict(zip(ranks_data["Agent Name"].str.strip(), ranks_data["Agency Name"].str.strip()))

    # 3) Manually defined data from your attached image (without Agency Name).
    #    We'll look up the Agency Name using the map above.
    second_contracts_data = [
        {"Agent Name": "Peter Wallen",                   "Dollar Index": 0.68, "Total Contract Value": 35600000},
        {"Agent Name": "Mika Rautakallio",               "Dollar Index": 0.72, "Total Contract Value": 42270000},
        {"Agent Name": "Brian & Scott Bartlett",         "Dollar Index": 0.81, "Total Contract Value": 86500000},
        {"Agent Name": "Jordan Neumann & George Bazos",  "Dollar Index": 0.82, "Total Contract Value": 82500000},
        {"Agent Name": "Judd Moldaver",                  "Dollar Index": 0.83, "Total Contract Value": 133170000},
        {"Agent Name": "Pat Brisson",                    "Dollar Index": 0.87, "Total Contract Value": 116885714},
        {"Agent Name": "Richard Evans",                  "Dollar Index": 0.95, "Total Contract Value": 85000000},
        {"Agent Name": "Paul Capizzano",                 "Dollar Index": 0.97, "Total Contract Value": 17825000},
        {"Agent Name": "Kurt Overhardt",                 "Dollar Index": 1.00, "Total Contract Value": 97650000},
        {"Agent Name": "Claude Lemieux",                 "Dollar Index": 1.02, "Total Contract Value": 48000000},
        {"Agent Name": "Andre Rufener",                  "Dollar Index": 1.06, "Total Contract Value": 36000000},
        {"Agent Name": "Craig Oster",                    "Dollar Index": 1.06, "Total Contract Value": 72500000},
        {"Agent Name": "Darren Ferris",                  "Dollar Index": 1.10, "Total Contract Value": 54465000},
        {"Agent Name": "Patrick Morris",                 "Dollar Index": 1.13, "Total Contract Value": 29000000},
        {"Agent Name": "Allan Roy",                      "Dollar Index": 1.18, "Total Contract Value": 30000000},
        {"Agent Name": "David Gagner",                   "Dollar Index": 1.20, "Total Contract Value": 15750000},
        {"Agent Name": "Philippe Lecavalier",            "Dollar Index": 1.20, "Total Contract Value": 29250000},
        {"Agent Name": "Don Meehan",                     "Dollar Index": 1.29, "Total Contract Value": 22750000},
        {"Agent Name": "Markus Lehto",                   "Dollar Index": 1.39, "Total Contract Value": 27350000},
        {"Agent Name": "Kevin Magnuson",                 "Dollar Index": 1.42, "Total Contract Value": 61666668},
        {"Agent Name": "Robert Norton",                  "Dollar Index": 1.49, "Total Contract Value": 40800000},
        {"Agent Name": "Matt Keator",                    "Dollar Index": 1.51, "Total Contract Value": 35600000},
        {"Agent Name": "Jordan Neumann & George Bazos",  "Dollar Index": 1.60, "Total Contract Value": 80000000},
    ]

    # 4) Build a styled card for each row
    for rank, row in enumerate(second_contracts_data, start=1):
        agent_name = row['Agent Name']
        # auto-lookup agency name
        agency = agency_map.get(agent_name.strip(), "N/A")
        dollar_index = row['Dollar Index']
        total_val = row['Total Contract Value']
        
        card_html = f"""
        <div style="display: flex; align-items: center; border: 1px solid #ccc; border-radius: 8px; padding: 8px; margin-bottom: 8px;">
            <div style="flex: 0 0 40px; text-align: center; font-size: 18px; font-weight: bold;">
                {rank}.
            </div>
            <div style="flex: 1; margin-left: 16px; font-size: 18px; font-weight: bold;">
                {agent_name} <br/><span style="font-size: 14px; font-weight: normal;">{agency}</span>
            </div>
            <div style="flex: 0 0 170px; text-align: right; font-size: 16px;">
                <div style="border-left: 1px solid #ccc; padding-left: 8px;">
                    <div style="font-weight: bold;">${dollar_index:,.2f}</div>
                    <div style="font-size: 14px;">Total Value: ${total_val:,.0f}</div>
                </div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

# --------------------------------------------------------------------
# 5) Visualizations and Project Definitions
# --------------------------------------------------------------------
def overall_visualizations():
    st.title("Visualizations and Takeaways")
    st.write("""
    The scatter plot below shows each agent as a dot. The X axis represents the number of Contracts Tracked (CT),
    and the Y axis represents the Dollar Index. This chart helps reveal whether agents with more contracts 
    tend to have a higher Dollar Index.
    """)
    
    # ----- Agent Tendency Classifications (STATIC) -----
    st.subheader("Agent Tendency Classifications")
    
    col1, col2, col3 = st.columns(3)
    
    team_friendly = [
        "Peter Fish",
        "Daniel Milstein",
        "Murray Koontz",
        "Georges Mueller",
        "Shawn Hunwick",
        "Jerry Buckley",
        "David Gagner",
        "Mika Rautakallio",
        "Lewis Gross",
        "Paul Corbeil",
        "Stephen F. Reich",
        "Rick Valette",
        "Todd Reynolds",
        "Jason Davidson",
        "Dave Cowan",
        "Markus Lehto",
        "Matt Keator",
        "Ray (Raynold) Petkau",
        "Richard Evans",
        "Matthew Federico",
        "Brian MacDonald",
        "Dean Grillo",
        "Serge Payer",
        "Daniel Plante",
        "Michael Deutsch",
        "Eric Quinlan & Nicholas Martino",
        "Monir Kalgoum",
        "Matthew Ebbs",
        "Joakim Persson",
        "Maxim Moliver"
    ]
    
    market_oriented = [
        "Darren Ferris",
        "Paul Theofanous",
        "Paul Capizzano",
        "Jeff Helperl",
        "Kurt Overhardt",
        "Pat Brisson",
        "Wade Arnott",
        "Ross Gurney",
        "Mark Gandler",
        "Don Meehan",
        "Claude Lemieux",
        "Craig Oster",
        "Philippe Lecavalier",
        "Andre Rufener",
        "Jordan Neumann & George Bazos",
        "Kevin Magnuson",
        "Robert Norton",
        "Brian & Scott Bartlett",
        "Michael Curran",
        "Andrew Scott",
        "Joseph Resnick",
        "Judd Moldaver",
        "Allan Walsh",
        "Todd Diamond",
        "Allain Roy",
        "Peter Wallen",
        "Ritchie Winter",
        "Peter MacTavish",
        "Ben Hankinson",
        "Pete Rutili"
    ]
    
    player_friendly = [
        "Robert Sauve",
        "Robert Murray",
        "Mark Stowe",
        "John Thornton",
        "Matthew Oates",
        "Stephen Bartlett",
        "Ryan Barnes",
        "Stephen Screnci",
        "Justin Duberman",
        "Richard Curran",
        "Erik Lupien",
        "Cameron Stewart",
        "Marc Levine",
        "Eustace King",
        "Jarrett Bousquet",
        "Thane Campbell",
        "Andrew Maloney",
        "Jay Grossman",
        "Gerry Johannson",
        "Neil Sheehy",
        "Kevin Epp",
        "Jiri Hamal",
        "Robert Hooper",
        "Scott Bartlett",
        "Patrick Morris",
        "Ian Pulver",
        "Bayne Pettinger",
        "Olivier Fortier",
        "Ron Salcer",
        "J.P. Barry"
    ]
    
    with col1:
        st.markdown("<h3 style='color:#006400; text-align:center;'>Team Friendly</h3>", unsafe_allow_html=True)
        for name in team_friendly:
            st.markdown(f"<div style='border: 1px solid #006400; padding: 8px; margin: 4px; border-radius: 5px; text-align:center;'>{name}</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<h3 style='color:black; text-align:center;'>Market-Oriented</h3>", unsafe_allow_html=True)
        for name in market_oriented:
            st.markdown(f"<div style='border: 1px solid black; padding: 8px; margin: 4px; border-radius: 5px; text-align:center;'>{name}</div>", unsafe_allow_html=True)
    
    with col3:
        st.markdown("<h3 style='color:#8B0000; text-align:center;'>Player-Friendly</h3>", unsafe_allow_html=True)
        for name in player_friendly:
            st.markdown(f"<div style='border: 1px solid #8B0000; padding: 8px; margin: 4px; border-radius: 5px; text-align:center;'>{name}</div>", unsafe_allow_html=True)
    # ----- End Agent Tendency Classifications Section -----
    
    # ----- SCATTER PLOT with Yellow Trend Line -----
    _, ranks_data, _ = load_data()
    fig = go.Figure(data=go.Scatter(
        x=ranks_data['CT'],
        y=ranks_data['Dollar Index'],
        mode='markers',
        marker=dict(size=10, color='blue', opacity=0.7),
        text=ranks_data['Agent Name']
    ))
    fig.update_layout(
        title="Contracts Tracked vs Dollar Index",
        xaxis_title="Contracts Tracked (CT)",
        yaxis_title="Dollar Index",
        yaxis=dict(range=[0.5, 1.5]),
        template="plotly_white"
    )
    
    x = ranks_data['CT'].astype(float)
    y = ranks_data['Dollar Index'].astype(float)
    mask = np.isfinite(x) & np.isfinite(y)
    if mask.sum() > 1:
        try:
            slope, intercept = np.polyfit(x[mask], y[mask], 1)
            x_line = np.linspace(x.min(), x.max(), 100)
            y_line = slope * x_line + intercept
            fig.add_trace(go.Scatter(
                x=x_line,
                y=y_line,
                mode='lines',
                name='Average Dollar Index Trend',
                line=dict(color='yellow', width=3)
            ))
        except np.linalg.LinAlgError:
            st.write("Trend line could not be computed due to a numerical error.")
    else:
        st.write("Not enough data to compute a trend line.")
    
    st.plotly_chart(fig, use_container_width=True)
    # ----- End Scatter Plot Section -----
    
def project_definitions():
    st.title("📚 Project Definitions")
    definitions = [
        ("Dollar Index", "This metric evaluates agent performance. It answers: For every dollar of on-ice value a client provides, how many dollars does the agent capture?"),
        ("Win %", "The percentage of contract years considered a 'win' for the agent. A win occurs when the dollars captured exceed the player's on-ice value."),
        ("Contracts Tracked", "The number of negotiated contracts that qualify for this project (excluding entry-level contracts but including two-way contracts)."),
        ("VCP", "Value Capture Percentage – the percentage of a player's on-ice value that the agent is able to capture as compensation."),
        ("Six-Year Agent Delivery", "An aggregate measure over six seasons (2018-19 through 2023-24) of the dollars delivered by an agent relative to on-ice contribution."),
        ("Player Contributions", "Also known as 'PC', this metric assigns a financial value to a player's on-ice performance using comprehensive NHL and AHL data.")
    ]
    for term, definition in definitions:
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"**{term}**")
        with col2:
            st.markdown(definition)
        st.markdown("---")

# --------------------------------------------------------------------
# 5) Navigation
# --------------------------------------------------------------------
st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", [
    "Home",
    "Agent Dashboard",
    "Agency Dashboard",
    "Leaderboard",
    "Second Contracts Leaderboard",  # <--- Our new page
    "Visualizations and Takeaways",
    "Project Definitions"
])

if page == "Home":
    st.title("Landing Page - Agent Analysis Project")
elif page == "Agent Dashboard":
    agent_dashboard()
elif page == "Agency Dashboard":
    agency_dashboard()
elif page == "Leaderboard":
    leaderboard_page()
elif page == "Second Contracts Leaderboard":
    second_contracts_leaderboard_page()
elif page == "Visualizations and Takeaways":
    overall_visualizations()
elif page == "Project Definitions":
    project_definitions()
