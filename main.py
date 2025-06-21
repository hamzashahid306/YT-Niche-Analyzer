import streamlit as st
import pandas as pd
from googleapiclient.discovery import build
import random

st.set_page_config(layout="wide")
st.title("📊 YouTube Niche Analyzer")

# YouTube API key
API_KEY = st.secrets["youtube"]["api_key"]
yt = build("youtube", "v3", developerKey=API_KEY)

def fetch_niche_stats(niche, max_results=10):
    # Step 1: Search channels
    res = yt.search().list(q=niche, type="channel", part="snippet", maxResults=max_results).execute()
    stats = []
    for item in res["items"]:
        cid = item["snippet"]["channelId"]
        ch = yt.channels().list(id=cid, part="statistics").execute()
        s = ch["items"][0]["statistics"]
        stats.append({
            "Channel": item["snippet"]["title"],
            "Subscribers": int(s.get("subscriberCount", 0)),
            "Views": int(s.get("viewCount", 0)),
            "Videos": int(s.get("videoCount", 0))
        })
    return pd.DataFrame(stats)

def estimate_rpm():
    return round(random.uniform(1.5, 2.8), 2)

# UI
niche = st.text_input("🎯 Enter a YouTube Niche", value="Bull Rescue Stories")
if st.button("Analyze Niche") and niche:
    with st.spinner("Analyzing niche..."):
        df = fetch_niche_stats(niche, max_results=8)
        total_views = df["Views"].sum()
        loyal_audience = int(df["Subscribers"].sum() * 0.1)
        avg_views = int(df["Views"].mean())
        rpm_est = estimate_rpm()
        score_market = 77 if total_views > 2000000 else 50
        score_saturation = 100 if len(df) < 10 else 60
        score_profit = 21 if rpm_est < 3 else 60

    # Layout
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("📈 Market Size", f"{total_views/1e6:.1f}M Views")
        st.markdown(f"**Score:** {score_market}/100")
        st.caption("Decent market size, decent loyal audience.")

    with col2:
        st.metric("🌱 Saturation Level", f"{len(df)} Channels")
        st.markdown(f"**Score:** {score_saturation}/100")
        st.caption("Looks unsaturated.")

    with col3:
        st.metric("💰 Profitability", f"${rpm_est} RPM")
        st.markdown(f"**Score:** {score_profit}/100")
        st.caption("Lower RPM, but niche may still be valuable.")

    st.divider()
    st.subheader("📊 Channels Found")
    st.dataframe(df, use_container_width=True)
