import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime, timedelta
import isodate
import numpy as np
import matplotlib.pyplot as plt
from pytube import extract

# Page Configuration
st.set_page_config(
    page_title="YouTube Niche Analyzer",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-box {
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
        background-color: #f0f2f6;
    }
    .progress-container {
        height: 20px;
        background: #e0e0e0;
        border-radius: 10px;
        margin: 10px 0;
    }
    .progress-bar {
        height: 100%;
        border-radius: 10px;
        background: linear-gradient(90deg, #ff4b4b, #ffa34b);
    }
    .video-card {
        border-left: 4px solid #ff4b4b;
        padding: 10px;
        margin: 10px 0;
        background-color: #f9f9f9;
    }
    .big-font {
        font-size:18px !important;
        font-weight: bold;
    }
    .stButton>button {
        background-color: #ff4b4b;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# Initialize YouTube API
@st.cache_resource
def get_youtube_service(AIzaSyAQk4wvU0OKfk3EhUKINI77foI2u76wjmg):
    return build('youtube', 'v3', developerKey=api_key)

class YouTubeAnalyzer:
    def __init__(self, youtube_service):
        self.youtube = youtube_service
    
    def get_channel_id(self, url):
        try:
            return extract.channel_id(url)
        except:
            st.error("Invalid YouTube channel URL")
            return None
    
    def get_channel_stats(self, channel_id):
        request = self.youtube.channels().list(
            part="snippet,contentDetails,statistics",
            id=channel_id
        )
        response = request.execute()
        return response['items'][0] if 'items' in response else None
    
    def get_channel_videos(self, channel_id, max_results=50):
        channel_stats = self.get_channel_stats(channel_id)
        if not channel_stats:
            return []
        
        playlist_id = channel_stats['contentDetails']['relatedPlaylists']['uploads']
        videos = []
        next_page_token = None
        
        while len(videos) < max_results:
            request = self.youtube.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=min(50, max_results - len(videos)),
                pageToken=next_page_token
            )
            response = request.execute()
            videos.extend(response['items'])
            
            next_page_token = response.get('nextPageToken')
            if not next_page_token:
                break
        
        return videos[:max_results]
    
    def get_video_stats(self, video_ids):
        stats = []
        for i in range(0, len(video_ids), 50):
            request = self.youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=','.join(video_ids[i:i+50])
            response = request.execute()
            stats.extend(response['items'])
        return stats
    
    def search_channels(self, query, max_results=5):
        request = self.youtube.search().list(
            part="snippet",
            q=query,
            type="channel",
            maxResults=max_results
        )
        response = request.execute()
        return response['items']
    
    def analyze_channel(self, channel_id):
        channel_stats = self.get_channel_stats(channel_id)
        if not channel_stats:
            return None
        
        videos = self.get_channel_videos(channel_id, 20)
        video_ids = [v['contentDetails']['videoId'] for v in videos]
        video_stats = self.get_video_stats(video_ids)
        
        # Calculate metrics
        sub_count = int(channel_stats['statistics']['subscriberCount'])
        view_count = int(channel_stats['statistics']['viewCount'])
        video_count = int(channel_stats['statistics']['videoCount'])
        
        # Video metrics
        views = []
        likes = []
        comments = []
        durations = []
        
        for video in video_stats:
            views.append(int(video['statistics'].get('viewCount', 0)))
            likes.append(int(video['statistics'].get('likeCount', 0)))
            comments.append(int(video['statistics'].get('commentCount', 0)))
            durations.append(isodate.parse_duration(video['contentDetails']['duration']).total_seconds())
        
        avg_views = np.mean(views) if views else 0
        avg_likes = np.mean(likes) if likes else 0
        avg_comments = np.mean(comments) if comments else 0
        avg_duration = np.mean(durations) if durations else 0
        
        # Engagement rates
        engagement_rate = (avg_likes + avg_comments) / avg_views * 100 if avg_views > 0 else 0
        views_per_sub = view_count / sub_count if sub_count > 0 else 0
        
        return {
            'channel_name': channel_stats['snippet']['title'],
            'subscribers': sub_count,
            'total_views': view_count,
            'videos': video_count,
            'avg_views': avg_views,
            'avg_likes': avg_likes,
            'avg_comments': avg_comments,
            'avg_duration': avg_duration,
            'engagement_rate': engagement_rate,
            'views_per_sub': views_per_sub,
            'video_stats': video_stats
        }

def display_metrics(metrics):
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.subheader("Market Size")
        with st.container():
            market_score = min(100, int(metrics['subscribers'] / 100000))
            st.markdown(f"<div class='metric-box'><h3>{market_score}</h3></div>", unsafe_allow_html=True)
            display_progress_bar(market_score)
            st.markdown(f"""
            <p class="big-font">Viral Potential: {metrics['total_views']:,} views</p>
            <p class="big-font">Subscribers: {metrics['subscribers']:,}</p>
            """, unsafe_allow_html=True)
    
    with col2:
        st.subheader("Engagement")
        with st.container():
            engagement_score = min(100, int(metrics['engagement_rate'] * 10))
            st.markdown(f"<div class='metric-box'><h3>{engagement_score}</h3></div>", unsafe_allow_html=True)
            display_progress_bar(engagement_score)
            st.markdown(f"""
            <p class="big-font">Engagement Rate: {metrics['engagement_rate']:.1f}%</p>
            <p class="big-font">Views/Sub: {metrics['views_per_sub']:.1f}</p>
            """, unsafe_allow_html=True)
    
    with col3:
        st.subheader("Content")
        with st.container():
            content_score = min(100, int(metrics['avg_views'] / 10000))
            st.markdown(f"<div class='metric-box'><h3>{content_score}</h3></div>", unsafe_allow_html=True)
            display_progress_bar(content_score)
            st.markdown(f"""
            <p class="big-font">Avg. Views: {metrics['avg_views']:,.0f}</p>
            <p class="big-font">Video Count: {metrics['videos']}</p>
            """, unsafe_allow_html=True)

def display_progress_bar(score):
    st.markdown(f"""
    <div class="progress-container">
        <div class="progress-bar" style="width: {score}%"></div>
    </div>
    <div style="display: flex; justify-content: space-between;">
        <span>0-49</span>
        <span>50-70</span>
        <span>71-100</span>
    </div>
    """, unsafe_allow_html=True)

def display_video_card(video):
    stats = video['statistics']
    snippet = video['snippet']
    
    title = snippet['title']
    channel = snippet['channelTitle']
    views = int(stats.get('viewCount', 0))
    likes = int(stats.get('likeCount', 0))
    comments = int(stats.get('commentCount', 0))
    published = snippet['publishedAt'][:10]
    
    engagement = (likes + comments) / views * 100 if views > 0 else 0
    
    st.markdown(f"""
    <div class="video-card">
        <p style="font-weight: bold; margin-bottom: 5px;">{title}</p>
        <p style="margin: 0;"><span style="color: #ff4b4b;">{channel}</span> {engagement:.1f}% engagement</p>
        <p style="margin: 0;">{views:,} views | {likes:,} likes | {comments:,} comments</p>
        <p style="margin: 0;">Published: {published}</p>
    </div>
    """, unsafe_allow_html=True)

def main():
    st.title("📊 YouTube Niche Analyzer")
    st.markdown("Analyze YouTube channels and niches using the YouTube Data API")
    
    # API Key Input (for demo purposes - in production use secrets.toml)
    api_key = st.text_input("Enter YouTube API Key:", type="password")
    
    if not api_key:
        st.warning("Please enter a valid YouTube API key to continue")
        return
    
    try:
        youtube_service = get_youtube_service(api_key)
        analyzer = YouTubeAnalyzer(youtube_service)
    except:
        st.error("Failed to initialize YouTube API. Please check your API key.")
        return
    
    tab1, tab2 = st.tabs(["Analyze Channel", "Analyze Niche"])
    
    with tab1:
        st.subheader("Analyze YouTube Channel")
        channel_url = st.text_input("Enter YouTube Channel URL:")
        
        if st.button("Analyze Channel") and channel_url:
            with st.spinner("Fetching channel data..."):
                channel_id = analyzer.get_channel_id(channel_url)
                if channel_id:
                    metrics = analyzer.analyze_channel(channel_id)
                    if metrics:
                        st.success(f"Analyzing channel: {metrics['channel_name']}")
                        display_metrics(metrics)
                        
                        st.subheader("Recent Videos Performance")
                        for video in metrics['video_stats']:
                            display_video_card(video)
                        
                        # Show metrics charts
                        st.subheader("Performance Metrics")
                        plot_metrics(metrics)
    
    with tab2:
        st.subheader("Analyze YouTube Niche")
        niche_query = st.text_input("Enter niche keyword (e.g., 'tech reviews', 'cooking'):")
        
        if st.button("Analyze Niche") and niche_query:
            with st.spinner(f"Searching for {niche_query} channels..."):
                channels = analyzer.search_channels(niche_query, 5)
                if channels:
                    st.success(f"Found {len(channels)} channels for niche: {niche_query}")
                    
                    for channel in channels:
                        channel_id = channel['snippet']['channelId']
                        channel_name = channel['snippet']['channelTitle']
                        
                        with st.expander(f"📺 {channel_name}"):
                            metrics = analyzer.analyze_channel(channel_id)
                            if metrics:
                                display_metrics(metrics)
                                st.markdown(f"[Visit Channel](https://youtube.com/channel/{channel_id})")

def plot_metrics(metrics):
    fig, ax = plt.subplots(1, 2, figsize=(12, 4))
    
    # Views distribution
    views = [int(v['statistics'].get('viewCount', 0)) for v in metrics['video_stats']]
    ax[0].hist(views, bins=10, color='#ff4b4b')
    ax[0].set_title('Views Distribution')
    ax[0].set_xlabel('Views')
    ax[0].set_ylabel('Number of Videos')
    
    # Engagement scatter plot
    likes = [int(v['statistics'].get('likeCount', 0)) for v in metrics['video_stats']]
    comments = [int(v['statistics'].get('commentCount', 0)) for v in metrics['video_stats']]
    ax[1].scatter(views, likes, color='#ff4b4b', label='Likes')
    ax[1].scatter(views, comments, color='#ffa34b', label='Comments')
    ax[1].set_title('Engagement Metrics')
    ax[1].set_xlabel('Views')
    ax[1].set_ylabel('Count')
    ax[1].legend()
    
    st.pyplot(fig)

if __name__ == "__main__":
    main()
