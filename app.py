import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client, Client

# ==================================================
# ☁️ SUPABASE CONFIGURATION (SECURE VERSION)
# ==================================================
# We securely load the keys from Streamlit's "Secrets" manager
# DO NOT paste your keys here
try:
    SUPABASE_URL = st.secrets["SUPABASE_URL"]
    SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
except Exception as e:
    st.error("❌ Connection Error: Please check your Streamlit Cloud 'Secrets' configuration.")
    st.stop()

# ==================================================
# ⚙️ PAGE CONFIG & GLOBAL STYLES (Run Once)
# ==================================================
st.set_page_config(page_title="AQI Dashboard", layout="wide", page_icon="☁️")

# 🚀 GLOBAL STYLES (Prevents blinking)
st.markdown("""
<style>
    /* CSS for the AQI Bar */
    .aqi-bar-container { display: flex; height: 45px; border-radius: 10px; overflow: hidden; margin-top: 10px; }
    .seg { flex: 1; text-align: center; font-weight: bold; padding-top: 12px; color: white; font-family: sans-serif; font-size: 14px; }
    
    /* Colors */
    .good { background: #00e400; }
    .moderate { background: #ffff00; color: black !important; }
    .poor { background: #ff7e00; }
    .unhealthy { background: #ff0000; }
    .veryunhealthy { background: #8f3f97; }
    .hazardous { background: #7e0023; }

    /* Ticks and Text */
    .ticks { width: 100%; display: flex; justify-content: space-between; margin-top: 4px; font-size: 12px; color: #aaa; }
    .big-aqi-value { font-size: 48px; font-weight: 800; text-align: center; margin-top: 15px; transition: color 0.5s ease; }
    .status-text { font-size: 24px; text-align: center; margin-bottom: 10px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# ---------------- SIDEBAR ----------------
st.sidebar.title("⚙️ Settings")
refresh_seconds = st.sidebar.slider("⏱ Refresh Speed", 2, 60, 2)

st.sidebar.title("📌 Navigation")
choice = st.sidebar.radio("Select View", ["Current Data", "Stored Data", "Future Data"])

# ==================================================
# 📥 DATA FETCHING
# ==================================================
def get_latest_data(limit=50):
    try:
        # Fetch data ordered by ID Descending (Newest First)
        response = supabase.table("sensordata").select("*").order("id", desc=True).limit(limit).execute()
        return response.data
    except:
        return []

# ==================================================
# 🟢 CURRENT DATA (Silent Fragment)
# ==================================================
@st.fragment(run_every=refresh_seconds)
def show_live_monitor():
    rows = get_latest_data(50) # Get last 50 rows for live trend
    
    if rows:
        df = pd.DataFrame(rows)
        # Rename & Fix Time
        df.rename(columns={'created_at': 'Timestamp', 'mq135': 'MQ135', 'temperature': 'Temperature', 'humidity': 'Humidity', 'aqi': 'AQI'}, inplace=True)
        df['Timestamp'] = pd.to_datetime(df['Timestamp']).dt.tz_convert('Asia/Kolkata')
        
        # Latest Values
        latest = df.iloc[0]
        aqi = int(latest['AQI'])
        temp = latest['Temperature']
        hum = latest['Humidity']
        time_str = latest['Timestamp'].strftime("%H:%M:%S")

        # Color Logic
        if aqi <= 50: status, color = "Good 😊", "#00e400"
        elif aqi <= 100: status, color = "Moderate 🙂", "#ffff00"
        elif aqi <= 150: status, color = "Unhealthy (Sens.) 😐", "#ff7e00"
        elif aqi <= 200: status, color = "Unhealthy 😷", "#ff0000"
        elif aqi <= 300: status, color = "Very Unhealthy 🤢", "#8f3f97"
        else: status, color = "Hazardous ☠️", "#7e0023"

        # 1. METRICS
        st.title("🟢 Live AQI Monitoring")
        
        m1, m2, m3 = st.columns(3)
        m1.metric("AQI Level", aqi)
        m2.metric("Temperature", f"{temp} °C")
        m3.metric("Humidity", f"{hum} %")
        
        st.caption(f"Last Updated: {time_str}")

        # 2. HTML BAR
        st.markdown(f"""
        <div class="status-text">Current Status: {status}</div>
        <div class="aqi-bar-container">
            <div class="seg good">Good</div>
            <div class="seg moderate">Moderate</div>
            <div class="seg poor">Poor</div>
            <div class="seg unhealthy">Unhealthy</div>
            <div class="seg veryunhealthy">Severe</div>
            <div class="seg hazardous">Hazardous</div>
        </div>
        <div class="ticks">
            <span>0</span><span>50</span><span>100</span><span>150</span><span>200</span><span>300</span><span>301+</span>
        </div>
        <div class="big-aqi-value" style="color: {color};">{aqi} AQI</div>
        """, unsafe_allow_html=True)

        # 3. CHART
        st.markdown("---")
        st.subheader("📈 Live Trend")
        df_sorted = df.sort_values('Timestamp')
        fig = px.line(df_sorted, x="Timestamp", y="AQI", markers=True, height=300)
        st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("Connecting to cloud...")

# ==================================================
# 📁 STORED DATA VIEW (UPDATED WITH GRAPH)
# ==================================================
def show_history():
    st.title("📁 Historical Data")
    
    # Fetch larger history (e.g., 1000 rows)
    with st.spinner("Downloading history from Cloud..."):
        rows = get_latest_data(1000)

    if rows:
        df = pd.DataFrame(rows)
        
        # Rename & Process Time
        df.rename(columns={'created_at': 'Timestamp', 'mq135': 'MQ135', 'temperature': 'Temperature', 'humidity': 'Humidity', 'aqi': 'AQI'}, inplace=True)
        df['Timestamp'] = pd.to_datetime(df['Timestamp']).dt.tz_convert('Asia/Kolkata')
        
        # Sort Oldest -> Newest for the Graph
        df_sorted = df.sort_values(by='Timestamp')

        # 1. THE GRAPH (New Addition!)
        st.subheader("📊 Full History Trends")
        fig = px.line(
            df_sorted, 
            x="Timestamp", 
            y=["AQI", "Temperature", "Humidity"],
            title="Environmental Data Over Time",
            markers=False # Removed markers to make large graphs cleaner
        )
        st.plotly_chart(fig, use_container_width=True)

        # 2. THE TABLE
        st.subheader("📄 Data Log (Newest First)")
        st.dataframe(df, use_container_width=True)
    else:
        st.write("No data found.")

# ==================================================
# 🔮 FUTURE DATA VIEW
# ==================================================
def show_future():
    st.title("🔮 Future AQI Forecasting")
    st.info("Model training in progress...")

# ==================================================
# 🚀 ROUTER
# ==================================================
if choice == "Current Data":
    show_live_monitor()
elif choice == "Stored Data":
    show_history()
elif choice == "Future Data":
    show_future()
