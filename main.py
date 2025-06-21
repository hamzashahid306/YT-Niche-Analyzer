import streamlit as st
from googleapiclient.discovery import build
import pandas as pd

st.title("🔍 YouTube Niche Analyzer")

API_KEY = st.secrets["youtube"]["AIzaSyAQk4wvU0OKfk3EhUKINI77foI2u76wjmg"]
yt = build("youtube", "v3", developerKey=API_KEY)

def fetch_channels(q):
    res = yt.search().list(q=q, type="channel", part="snippet", maxResults=10).execute()
    stats = []
    for item in res["items"]:
        cid = item["snippet"]["channelId"]
        ch = yt.channels().list(id=cid, part="statistics").execute()
        s = ch["items"][0]["statistics"]
        stats.append({
            "Channel Name": item["snippet"]["title"],
            "Subscribers": int(s.get("subscriberCount", 0)),
            "Total Views": int(s.get("viewCount", 0)),
            "Video Count": int(s.get("videoCount", 0))
        })
    return pd.DataFrame(stats)

query = st.text_input("Enter a niche to analyze (e.g. fitness, AI, gaming)")
if st.button("Analyze"):
    with st.spinner("Collecting data..."):
        df = fetch_channels(query)
        st.dataframe(df)
