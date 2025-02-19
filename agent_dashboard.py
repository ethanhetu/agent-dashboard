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
    ranks_data = xls.parse('Just Agent Ranks')
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

def plot_player_detail(player_data):
    years = ['2018-19', '2019-20', '2020-21', '2021-22', '2022-23', '2023-24']
    cost_columns = ['COST 18-19', 'COST 19-20', 'COST 20-21', 'COST 21-22', 'COST 22-23', 'COST 23-24']
    value_columns = ['PC 18-19', 'PC 19-20', 'PC 20-21', 'PC 21-22', 'PC 22-23', 'PC 23-24']

    cost_values = [player_data.get(col, 0) for col in cost_columns]
    value_values = [player_data.get(col, 0) for col in value_columns]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=years,
        y=cost_values,
        mode='lines+markers',
        name='Cost',
        line=dict(color='#8B0000', width=3),
        hovertemplate='Cost: $%{y:,.0f}'
    ))

    fig.add_trace(go.Scatter(
        x=years,
        y=value_values,
        mode='lines+markers',
        name='Value',
        line=dict(color='#006400', width=3),
        hovertemplate='Value: $%{y:,.0f}'
    ))

    fig.update_layout(
        title=f"Year-by-Year Cost vs. Value for {player_data['Combined Names']}",
        xaxis=dict(title='Year', tickangle=0),
        yaxis=dict(title='Dollars'),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
    )

    st.plotly_chart(fig, use_container_width=True)

def player_page(player_name, piba_data):
    if player_name in piba_data['Combined Names'].values:
        player_data = piba_data[piba_data['Combined Names'] == player_name].iloc[0]
        st.title(f"Player Details: {player_name}")
        plot_player_detail(player_data)
    else:
        st.error("Player data not found. Please return and select a valid player.")

def display_player_section(title, player_df):
    st.subheader(title)
    client_cols = st.columns(3)
    for idx, (_, player) in enumerate(player_df.iterrows()):
        with client_cols[idx % 3]:
            img_path = get_headshot_path(player['Combined Names'])
            if img_path:
                st.image(img_path, width=200)
            else:
                st.image(PLACEHOLDER_IMAGE_URL, width=200)

            if st.button(f"View {player['Combined Names']}", key=player['Combined Names']):
                st.session_state['selected_player'] = player['Combined Names']
                st.experimental_rerun()

            st.markdown(f"""
            <div style='border: 2px solid #ddd; padding: 10px; border-radius: 10px;'>
                <p><strong>Age:</strong> {calculate_age(player['Birth Date'])}</p>
                <p><strong>Six-Year Agent Delivery:</strong> {format_delivery_value(player['Dollars Captured Above/ Below Value'])}</p>
                <p><strong>Six-Year Player Cost:</strong> ${player['Total Cost']:,.0f}</p>
                <p><strong>Six-Year Player Value:</strong> ${player['Total PC']:,.0f}</p>
            </div>
            """, unsafe_allow_html=True)

def agent_dashboard():
    agents_data, ranks_data, piba_data = load_data()
    extract_headshots()

    if 'selected_player' in st.session_state:
        player_page(st.session_state['selected_player'], piba_data)
        return

    st.title("Agent Overview Dashboard")

    agent_names = ranks_data['Agent Name'].dropna().replace(['', '(blank)', 'Grand Total'], pd.NA).dropna()
    agent_names = sorted(agent_names, key=lambda name: name.split()[-1])
    selected_agent = st.selectbox("Select an Agent:", agent_names)

    agent_info = agents_data[agents_data['Agent Name'] == selected_agent].iloc[0]
    rank_info = ranks_data[ranks_data['Agent Name'] == selected_agent].iloc[0]

    st.header(f"{selected_agent} - {agent_info['Agency Name']}")

    agent_players = piba_data[piba_data['Agent Name'] == selected_agent]
    top_clients = agent_players.sort_values(by='Total Cost', ascending=False).head(3)
    display_player_section("Top 3 Clients by Total Cost", top_clients)

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
