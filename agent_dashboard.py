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

st.set_page_config(
    page_title="Agent Insights Dashboard", 
    page_icon="https://www.dropbox.com/s/o1u29fyz5kzffze/2011NP.png?dl=1", 
    layout="wide"
)

# Global variables for images
HEADSHOTS_DIR = "headshots_cache"  # For player headshots
PLACEHOLDER_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/en/3/3a/05_NHL_Shield.svg"

# Globals for agent photos (unused in leaderboard now)
AGENT_PHOTOS_DIR = "agent_photos"  # Folder for agent photos from release
AGENT_PLACEHOLDER_IMAGE_URL = "https://upload.wikimedia.org/wikipedia/commons/8/89/Agent_placeholder.png"

# --------------------------------------------------------------------
# Manual photo overrides (lower-case keys)
# --------------------------------------------------------------------
manual_photo_overrides = {
    "ryan macinnis": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3115000.png",
    "sam miletic": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4272149.png",
    "olli maatta": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/2976850.png",
    "griffin mendel": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4319915.png",
    "gustav rydahl": "https://assets.leaguestat.com/ahl/240x240/9495.jpg",
    "lucas wallmark": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3151037.png",
    "cole bardreau": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3942676.png&w=350&h=254",
    "andrew oglevie": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4392269.png?w=350&h=254",
    "mikkel boedker": "https://a.espncdn.com/i/headshots/nhl/players/full/3976.png",
    "strauss mann": "https://lscluster.hockeytech.com/download.php?client_code=ahl&file_path=media/ce280ff2dbcf376687996c79d462797d.png",
    "ian mccoshen": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3041989.png",
    "marc michaelis": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4319942.png",
    "keith yandle": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3330.png",
    "bryan little": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3508.png",
    "michael dal colle": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3114733.png?w=350&h=254",
    "phil di giuseppe": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3069834.png&w=350&h=254",
    "philippe desrosiers": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3042047.png&w=350&h=254",
    "jeremy bracco": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4392564.png",
    "sami niku": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3942047.png",
    "joel kellman": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4421961.png",
    "german rubtsov": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4024976.png?w=350&h=254",
    "otto somppi": "https://lscluster.hockeytech.com/download.php?client_code=ahl&file_path=media/5b9d58ab2a1abc1549ebc64c0eab7752.jpg",
    "ty ronning": "https://lscluster.hockeytech.com/download.php?client_code=ahl&file_path=media/38cec9f5a8ff976e9518678a7c717182.png",
    "matt tennyson": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3020635.png",
    "chris bigras": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3041990.png?w=350&h=254",
    "tyler persons": "https://lscluster.hockeytech.com/download.php?client_code=ahl&file_path=media/4b6fc4df5795f36b4e0678e32ba38fbe.jpg",
    "chase pearson": "https://b.fssta.com/uploads/application/nhl/headshots/6279.vresize.350.350.medium.81.png",
    "taylor fedun": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/2304599.png",
    "jonathan dahlen": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4122196.png",
    "colton point": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4272104.png&w=350&h=254",
    "christopher gibson": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/2563040.png",
    "andreas borgman": "https://a.espncdn.com/i/headshots/nhl/players/full/4220708.png",
    "shane gersich": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3151090.png",
    "joel l'esperance": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3648041.png",
    "landon bow": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4272107.png?w=350&h=254",
    "brett connolly": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/5479.png",
    "brennan menell": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4271611.png",
    "blake speers": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3942745.png",
    "julius honka": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3114754.png?w=350&h=254",
    "teemu kivihalme": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3042206.png",
    "petteri lindbohm": "https://a.espncdn.com/i/headshots/nhl/players/full/3069344.png",
    "joachim blichfeld": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4063456.png",
    "christian djoos": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3069440.png",
    "mikhail grigorenko": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/2976841.png",
    "maxim mamin": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4271946.png",
    "alexander volkov": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4233883.png",
    "michael mcniven": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3942205.png",
    "bobby ryan": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3264.png",
    "pontus aberg": "https://a.espncdn.com/i/headshots/nhl/players/full/3069396.png",
    "filip chlapik": "https://a.espncdn.com/i/headshots/nhl/players/full/3904182.png",
    "jayden halbgewachs": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4588292.png",
    "tanner kaspick": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4062250.png",
    "maxim letunov": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3115020.png",
    "stelio mattheos": "https://b.fssta.com/uploads/application/nhl/headshots/5577.vresize.350.350.medium.94.png",
    "ben thomas": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3151191.png",
    "lukas vejdemo": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3942258.png",
    "anton lindholm": "https://a.espncdn.com/i/headshots/nhl/players/full/3942563.png",
    "dominic turgeon": "https://a.espncdn.com/i/headshots/nhl/players/full/3151315.png",
    "kyle turris": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3892.png",
    "remi elie": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3042006.png",
    "cole kehler": "https://assets.leaguestat.com/ahl/240x240/7148.jpg",
    "xavier ouellet": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/2563079.png",
    "frederik gauthier": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3042039.png&w=350&h=254",
    "tyrell goulbourne": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3042078.png",
    "brendan guhle": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3904184.png",
    "juho lammikko": "https://a.espncdn.com/i/headshots/nhl/players/full/3150520.png",
    "tyler lewington": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3042264.png",
    "cedric paquette": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3067906.png",
    "kole sherwood": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3942294.png",
    "josh teves": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4319865.png",
    "dmytro timashov": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3938809.png",
    "zachary leslie": "https://lscluster.hockeytech.com/download.php?client_code=ahl&file_path=media/1e285de00c52b9054900d983e82fcaf9.jpg",
    "ilya kovalchuk": "https://a.espncdn.com/i/headshots/nhl/players/full/1175.png",
    "josh currie": "https://a.espncdn.com/i/headshots/nhl/players/full/4063257.png",
    "marko dano": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3042058.png",
    "adam huska": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4588215.png&w=350&h=254",
    "adam werner": "https://a.espncdn.com/i/headshots/nhl/players/full/4272283.png",
    "jordan weal": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/5557.png",
    "callum booth": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/4392501.png",
    "cal foote": "https://e7.pngegg.com/pngimages/56/770/png-clipart-california-state-university-los-angeles-business-company-management-information-headshot-silhouette-angle-company-thumbnail.png",
    "carter hart": "https://upload.wikimedia.org/wikipedia/en/thumb/3/3a/05_NHL_Shield.svg/1200px-05_NHL_Shield.svg.png",
    "dillon dube": "https://upload.wikimedia.org/wikipedia/en/thumb/3/3a/05_NHL_Shield.svg/1200px-05_NHL_Shield.svg.png",
    "michael mcLeod": "https://upload.wikimedia.org/wikipedia/en/thumb/3/3a/05_NHL_Shield.svg/1200px-05_NHL_Shield.svg.png",
    "alex formenton": "https://upload.wikimedia.org/wikipedia/en/thumb/3/3a/05_NHL_Shield.svg/1200px-05_NHL_Shield.svg.png",
    "reid duke": "https://a.espncdn.com/combiner/i?img=/i/headshots/nhl/players/full/3150433.png"
}

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
        "Colle Dal": "Michael Dal Colle",
        "Giuseppe Di": "Phil Di Giuseppe",
    }
    lower_name = name.lower().strip()
    return corrections.get(lower_name, name)

def get_headshot_path(player_name):
    # Check if we have a manual override first
    name_lower = player_name.lower().strip()
    if name_lower in manual_photo_overrides:
        return manual_photo_overrides[name_lower]
    
    # Otherwise, continue with existing local-file logic
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
                if img_path.startswith("http"):
                    st.markdown(
                        f"""
                        <div style="text-align:center;">
                            <img src="{img_path}"
                                 style="width:200px; height:200px; display:block; margin:auto;"/>
                        </div>
                        """, unsafe_allow_html=True
                    )
                else:
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
            # Override the cost (and agent delivery) for Evgeny Svechnikov
            if display_name == "Evgeny Svechnikov":
                cost_value = 2300000
                delivery_value = 2300000
            else:
                cost_value = player['Total Cost']
                delivery_value = player['Dollars Captured Above/ Below Value']
            st.markdown(f"<h4 style='text-align:center; color:black; font-weight:bold; font-size:24px;'>{display_name}</h4>", unsafe_allow_html=True)
            try:
                vcp_value = (cost_value / player['Total PC']) * 100
            except Exception:
                vcp_value = None
            box_html = f"""
            <div style="border: 2px solid #ddd; padding: 10px; border-radius: 10px;">
                <p><strong>Age:</strong> {calculate_age(player['Birth Date'])}</p>
                <p><strong>Six-Year Agent Delivery:</strong> {format_delivery_value(delivery_value)}</p>
                <p><strong>Six-Year Player Cost:</strong> ${cost_value:,.0f}</p>
                <p><strong>Six-Year Player Value:</strong> ${player['Total PC']:,.0f}</p>
            </div>
            """
            st.markdown(box_html, unsafe_allow_html=True)
            if vcp_value is not None:
                color = "#006400" if vcp_value >= 100 else "#8B0000"
                st.markdown(f"<p style='font-weight:bold; text-align:center;'>Percent of Value Captured: <span style='color:{color};'>{vcp_value:.0f}%</span></p>", unsafe_allow_html=True)

# --------------------------------------------------------------------
# Arbitration Page
# --------------------------------------------------------------------
def arbitration_page():
    st.title("Arbitration")
    st.subheader("Which agents most frequently utilize the arbitration process?")
    st.write("Agents are ranked based on the number of times they file for arbitration per client. The agents who less frequently file for arbitration, who therefore more frequently come to agreements before needing arbitration, are ranked more highly.")
    
    # Load data to get CT and Agency info
    _, ranks_data, _ = load_data()
    # Build lookup dictionaries from ranks data:
    ct_map = dict(zip(ranks_data["Agent Name"].str.strip(), ranks_data["CT"]))
    agency_map = dict(zip(ranks_data["Agent Name"].str.strip(), ranks_data["Agency Name"].str.strip()))
    
    # Manual arbitration data (agent name and Arb Filings Per Client)
    arb_data = [
        {"Agent Name": "Gerry Johannson", "Arb": 0.0000},
        {"Agent Name": "Ben Hankinson", "Arb": 0.0000},
        {"Agent Name": "Paul Capizzano", "Arb": 0.0000},
        {"Agent Name": "Brian & Scott Bartlett", "Arb": 0.0000},
        {"Agent Name": "Andrew Scott", "Arb": 0.0000},
        {"Agent Name": "Ian Pulver", "Arb": 0.0000},
        {"Agent Name": "Kevin Epp", "Arb": 0.0000},
        {"Agent Name": "Matt Keator", "Arb": 0.0000},
        {"Agent Name": "Peter Wallen", "Arb": 0.0000},
        {"Agent Name": "Philippe Lecavalier", "Arb": 0.0000},
        {"Agent Name": "Joseph Resnick", "Arb": 0.0000},
        {"Agent Name": "Jason Davidson", "Arb": 0.0000},
        {"Agent Name": "Ritchie Winter", "Arb": 0.0000},
        {"Agent Name": "David Gagner", "Arb": 0.0000},
        {"Agent Name": "Richard Evans", "Arb": 0.0000},
        {"Agent Name": "Jarrett Bousquet", "Arb": 0.0000},
        {"Agent Name": "Andre Rufener", "Arb": 0.0000},
        {"Agent Name": "Ross Gurney", "Arb": 0.0000},
        {"Agent Name": "Dean Grillo", "Arb": 0.0000},
        {"Agent Name": "Murray Koontz", "Arb": 0.0000},
        {"Agent Name": "Michael Deutsch", "Arb": 0.0000},
        {"Agent Name": "Pete Rutili", "Arb": 0.0000},
        {"Agent Name": "Olivier Fortier", "Arb": 0.0000},
        {"Agent Name": "Doug Shepherd", "Arb": 0.0000},
        {"Agent Name": "Allan Walsh", "Arb": 0.0000},
        {"Agent Name": "Paul Theofanous", "Arb": 0.0000},
        {"Agent Name": "Mark Gandler", "Arb": 0.0000},
        {"Agent Name": "Neil Sheehy", "Arb": 0.0000},
        {"Agent Name": "Richard Curran", "Arb": 0.0000},
        {"Agent Name": "Jordan Neumann & George Bazos", "Arb": 0.0000},
        {"Agent Name": "Ray (Raynold) Petkau", "Arb": 0.0000},
        {"Agent Name": "Eustace King", "Arb": 0.0000},
        {"Agent Name": "Bayne Pettinger", "Arb": 0.0000},
        {"Agent Name": "John Thornton", "Arb": 0.0000},
        {"Agent Name": "Matthew Oates", "Arb": 0.0000},
        {"Agent Name": "Kevin Magnuson", "Arb": 0.0000},
        {"Agent Name": "Rick Valette", "Arb": 0.0000},
        {"Agent Name": "Michael Curran", "Arb": 0.0000},
        {"Agent Name": "Scott Bartlett", "Arb": 0.0000},
        {"Agent Name": "Marc Levine", "Arb": 0.0000},
        {"Agent Name": "Stephen Screnci", "Arb": 0.0000},
        {"Agent Name": "Stephen Bartlett", "Arb": 0.0000},
        {"Agent Name": "Shawn Hunwick", "Arb": 0.0000},
        {"Agent Name": "Ron Salcer", "Arb": 0.0000},
        {"Agent Name": "Robert Murray", "Arb": 0.0000},
        {"Agent Name": "Robert Sauve", "Arb": 0.0000},
        {"Agent Name": "Maxim Moliver", "Arb": 0.0000},
        {"Agent Name": "Monir Kalgoum", "Arb": 0.0000},
        {"Agent Name": "Erik Lupien", "Arb": 0.0000},
        {"Agent Name": "Stephen F. Reich", "Arb": 0.0000},
        {"Agent Name": "Paul Corbeil", "Arb": 0.0000},
        {"Agent Name": "Mark Stowe", "Arb": 0.0000},
        {"Agent Name": "Robert Norton", "Arb": 0.0000},
        {"Agent Name": "Justin Duberman", "Arb": 0.0000},
        {"Agent Name": "Jerry Buckley", "Arb": 0.0000},
        {"Agent Name": "Peter MacTavish", "Arb": 0.0000},
        {"Agent Name": "Brian MacDonald", "Arb": 0.0000},
        {"Agent Name": "Dave Cowan", "Arb": 0.0000},
        {"Agent Name": "Jeff Helperl", "Arb": 0.0000},
        {"Agent Name": "Jiri Hamal", "Arb": 0.0000},
        {"Agent Name": "Andrew Maloney", "Arb": 0.0000},
        {"Agent Name": "Cameron Stewart", "Arb": 0.0000},
        {"Agent Name": "Jay Grossman", "Arb": 0.0000},
        {"Agent Name": "Matthew Federico", "Arb": 0.0000},
        {"Agent Name": "Georges Mueller", "Arb": 0.0000},
        {"Agent Name": "Eric Quinlan & Nicholas Martino", "Arb": 0.0000},
        {"Agent Name": "Allain Roy", "Arb": 0.0167},
        {"Agent Name": "Pat Brisson", "Arb": 0.0182},
        {"Agent Name": "J.P. Barry", "Arb": 0.0217},
        {"Agent Name": "Craig Oster", "Arb": 0.0278},
        {"Agent Name": "Markus Lehto", "Arb": 0.0417},
        {"Agent Name": "Darren Ferris", "Arb": 0.0435},
        {"Agent Name": "Lewis Gross", "Arb": 0.0526},
        {"Agent Name": "Patrick Morris", "Arb": 0.0556},
        {"Agent Name": "Wade Arnott", "Arb": 0.0556},
        {"Agent Name": "Daniel Milstein", "Arb": 0.0571},
        {"Agent Name": "Judd Moldaver", "Arb": 0.0588},
        {"Agent Name": "Claude Lemieux", "Arb": 0.0690},
        {"Agent Name": "Peter Fish", "Arb": 0.0833},
        {"Agent Name": "Kurt Overhardt", "Arb": 0.0909},
        {"Agent Name": "Todd Diamond", "Arb": 0.0909},
        {"Agent Name": "Robert Hooper", "Arb": 0.1000},
        {"Agent Name": "Daniel Plante", "Arb": 0.1000},
        {"Agent Name": "Todd Reynolds", "Arb": 0.1111},
        {"Agent Name": "Mika Rautakallio", "Arb": 0.1429},
        {"Agent Name": "Don Meehan", "Arb": 0.2000},
        {"Agent Name": "Joakim Persson", "Arb": 0.2500},
        {"Agent Name": "Serge Payer", "Arb": 0.2500},
        {"Agent Name": "Thane Campbell", "Arb": 0.5000},
        {"Agent Name": "Matthew Ebbs", "Arb": 1.0000},
    ]
    
    # Filter out agents with 0 Arb if desired
    filter_zero = st.checkbox("Only show agents with non-zero Arb Filings Per Client", value=True)
    if filter_zero:
        arb_data = [d for d in arb_data if d["Arb"] > 0]
    
    # Enrich arb_data with CT (formatted as an integer) and Agency info
    for d in arb_data:
        agent = d["Agent Name"].strip()
        d["CT"] = int(ct_map.get(agent, 0))
        d["Agency"] = agency_map.get(agent, "N/A")
    
    # Sort the data in ascending order so that lower Arb values (0's) appear at the top
    arb_data_sorted = sorted(arb_data, key=lambda x: x["Arb"])
    
    st.write("### Arbitration Leaderboard - Agents ranked by # of Arbitration Filings Per Client")
    for rank, d in enumerate(arb_data_sorted, start=1):
        card_html = f"""
        <div style="display: flex; align-items: center; border: 1px solid #ccc; border-radius: 8px; padding: 8px; margin-bottom: 8px;">
            <div style="flex: 0 0 40px; text-align: center; font-size: 18px; font-weight: bold;">
                {rank}.
            </div>
            <div style="flex: 1; margin-left: 16px; font-size: 18px; font-weight: bold;">
                {d["Agent Name"]} <br/><span style="font-size: 14px; font-weight: normal;">{d["Agency"]}</span>
            </div>
            <div style="flex: 0 0 170px; text-align: right; font-size: 16px;">
                <div style="border-left: 1px solid #ccc; padding-left: 8px;">
                    <div style="font-weight: bold;">{d["Arb"]:.4f}</div>
                    <div style="font-size: 14px;">CT: {d["CT"]}</div>
                </div>
            </div>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

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
    valid_agents = set(agents_data['Agent Name'].dropna().str.strip()) - excluded_agents
    ranks_data = ranks_data[ranks_data['Agent Name'].str.strip().isin(valid_agents)]
    piba_data = piba_data[piba_data['Agent Name'].str.strip().isin(valid_agents)]
    
    st.subheader("Which agents are delivering the most value to their clients?")
    st.write("Agents are ranked based on Dollar Index. (see 'definitions' tab for more information) The higher an agent's Dollar Index, the more effective he or she is at delivering surplus value to clients - in some cases, more dollars than their clients are actually worth on the ice.")
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

def second_contracts_leaderboard_page():
    st.title("Second Contracts Leaderboard")
    st.subheader("Which agents are delivering the most surplus value to clients with second contracts?")
    st.write("The 'second contract' is often a high-leverage game of risk and reward. Teams, players, and their representatives often grapple with how to appropriately price future performance. Given the inherent uncertainty of that exercise, one side of the equation typically ends up disproportionately benefitting from the agreement. Below, agents are ranked based on their Dollar Index, but ONLY looking at long-term contracts signed for RFA players coming off of their entry-level deals.")
    agents_data, ranks_data, piba_data = load_data()
    agency_map = dict(zip(ranks_data["Agent Name"].str.strip(), ranks_data["Agency Name"].str.strip()))
    second_contracts_data = [
        {"Agent Name": "Peter Wallen", "Dollar Index": 0.68, "Total Contract Value": 35600000},
        {"Agent Name": "Mika Rautakallio", "Dollar Index": 0.81, "Total Contract Value": 42270000},
        {"Agent Name": "Brian & Scott Bartlett", "Dollar Index": 0.81, "Total Contract Value": 86500000},
        {"Agent Name": "Jordan Neumann & George Bazos", "Dollar Index": 0.82, "Total Contract Value": 24150000},
        {"Agent Name": "Judd Moldaver", "Dollar Index": 0.83, "Total Contract Value": 133170000},
        {"Agent Name": "Pat Brisson", "Dollar Index": 0.87, "Total Contract Value": 116885714},
        {"Agent Name": "Richard Evans", "Dollar Index": 0.92, "Total Contract Value":  35714285},
        {"Agent Name": "Paul Capizzano", "Dollar Index": 0.95, "Total Contract Value": 17825000},
        {"Agent Name": "Kurt Overhardt", "Dollar Index": 0.96, "Total Contract Value": 97650000},
        {"Agent Name": "Claude Lemieux", "Dollar Index": 1.02, "Total Contract Value": 48200000},
        {"Agent Name": "Andre Rufener", "Dollar Index": 1.05, "Total Contract Value": 36000000},
        {"Agent Name": "Craig Oster", "Dollar Index": 1.06, "Total Contract Value": 72500000},
        {"Agent Name": "Darren Ferris", "Dollar Index": 1.06, "Total Contract Value": 54465000},
        {"Agent Name": "Patrick Morris", "Dollar Index": 1.13, "Total Contract Value": 27500000},
        {"Agent Name": "Allain Roy", "Dollar Index": 1.15, "Total Contract Value": 36100000},
        {"Agent Name": "David Gagner", "Dollar Index": 1.15, "Total Contract Value": 15750000},
        {"Agent Name": "Philippe Lecavalier", "Dollar Index": 1.20, "Total Contract Value": 29250000},
        {"Agent Name": "Ian Pulver", "Dollar Index": 1.29, "Total Contract Value": 57350000},
        {"Agent Name": "Kevin Magnuson", "Dollar Index": 1.39, "Total Contract Value":  22250000},
        {"Agent Name": "Lewis Gross", "Dollar Index": 1.57, "Total Contract Value":  61666668},
        {"Agent Name": "Ben Hankinson", "Dollar Index": 1.61, "Total Contract Value":  8350000},
        {"Agent Name": "Peter Fish", "Dollar Index": 1.63, "Total Contract Value":  76500000},
        {"Agent Name": "Gerry Johannson", "Dollar Index": 1.67, "Total Contract Value":  6725000},
    ]
    second_contracts_data_sorted = sorted(second_contracts_data, key=lambda x: x["Dollar Index"], reverse=True)
    for rank, row in enumerate(second_contracts_data_sorted, start=1):
        agent_name = row['Agent Name']
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
    st.title("Classifications")
    # ----- Agent Tendency Classifications (STATIC) -----
    st.subheader("Looking at player performance and cost between 2018-19 and 2023-24, how can agent behavior be classified?")
    st.write("Ultimately, every agent is acting on behalf of the best interests of his or her client. Often, that best interest means extracting as much money as possible. But sometimes it does not, such as when a client is willing to accept a lower wage in exchange for stability measures, such as no-trade protection. With all that said, looking broadly at the work of each agent, as has been done in this project, trends emerge. Below, each agent and agency has been sorted into one of three general tendency categories: 'Team Friendly' which are agents whose work generally favors NHL clubs, 'Market Aligned' which are agents whose work generally aligns with proper player value, and 'Player Friendly' which are agents whose work generally tends to favor their clients.")
    col1, col2, col3 = st.columns(3)
    team_friendly = [
        "Joakim Persson",
        "Dean Grillo",
        "Daniel Plante",
        "Michael Deutsch",
        "Ray (Raynold) Petkau",
        "Richard Evans",
        "Jerry Buckley",
        "Matt Keator",
        "Markus Lehto",
        "David Gagner",
        "Todd Reynolds",
        "Jason Davidson",
        "Murray Koontz",
    ]
    market_oriented = [
        "Craig Oster",
        "Ross Gurney",
        "Jordan Neumann & George Bazos",
        "Joseph Resnick",
        "Brian & Scott Bartlett",
        "Andrew Scott",
        "Judd Moldaver",
        "Todd Diamond",
        "Allan Walsh",
        "Peter Wallen",
        "Paul Corbeil",
        "Allain Roy",
        "Pete Rutili",
        "Peter Fish",
        "Ben Hankinson",
        "Daniel Milstein",
        "Shawn Hunwick",
        "Ritchie Winter",
        "Mika Rautakallio",
        "Lewis Gross",
    ]
    player_friendly = [
        "Matthew Oates",
        "Justin Duberman",
        "Richard Curran",
        "Eustace King",
        "Jay Grossman",
        "Jarrett Bousquet",
        "Gerry Johannson",
        "Neil Sheehy",
        "Robert Hooper",
        "Kevin Epp",
        "Patrick Morris",
        "Ian Pulver",
        "J.P. Barry",
        "Darren Ferris",
        "Paul Capizzano",
        "Paul Theofanous",
        "Don Meehan",
        "Pat Brisson",
        "Mark Gandler",
        "Wade Arnott",
        "Kurt Overhardt",
        "Jeff Helperl",
        "Michael Curran",
        "Claude Lemieux",
        "Philippe Lecavalier",
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
    # ----- Agency Tendency Classifications (STATIC) -----
    st.subheader("Agency Tendency Classifications")
    col1, col2, col3 = st.columns(3)
    team_friendly = [
        "KMJ Sports & Entertainment AB",
        "Forward Hockey",
        "Eclipse Sports Management",
        "Alpha Hockey Inc.",
        "Buckley Sports Management",
        "WIN Hockey Agency",
        "Raze Sports",
        "WD Sports & Entertainment",
        "Thunder Creek Professional Player Management",
    ]
    market_oriented = [
        "International Sports Advisors Co.",
        "R.W.G. Sport Management",
        "Edge Sports Management, LLC",
        "Octagon Athlete Representation",
        "Alterno Global Management LLC",
        "Paraphe Sports-Management",
        "RSG Hockey, LLC",
        "Global Hockey Consultants",
        "Gold Star Hockey",
        "Sports Professional Management Inc.",
        "MPR-Hockey Oy",
        "Wasserman Media Group, LLC",
        "Wintersports Ltd. Operating as Raze Sports",
    ]
    player_friendly = [
        "Achieve Sports Management",
        "Puck Agency, LLC",
        "The Sports Corporation",
        "I-C-E Hockey Agency",
        "The Orr Hockey Group",
        "Titan Sports Management, Inc.",
        "The Will Sports Group",
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
    # ----- End Agency Tendency Classifications Section -----
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
    st.title("Project Definitions")
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
    "Second Contracts Leaderboard",
    "Classifications",
    "Arbitration",
    "Project Definitions",
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
elif page == "Classifications":
    overall_visualizations()
elif page == "Arbitration":
    arbitration_page()
elif page == "Project Definitions":
    project_definitions()
