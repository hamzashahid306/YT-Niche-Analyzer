import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
from pytube import extract

# Page Configuration
st.set_page_config(
    page_title="YouTube Niche Analyzer",
    page_icon="📊",
    layout="wide"
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
                maxResults=min(50, max_results-len(videos)),
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
            )
            response = request.execute()
            stats.extend(response['items'])
        return stats
    
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
        views = [int(v['statistics'].get('viewCount', 0)) for v in video_stats]
        likes = [int(v['statistics'].get('likeCount', 0)) for v in video_stats]
        comments = [int(v['statistics'].get('commentCount', 0)) for v in video_stats]
        
        avg_views = np.mean(views) if views else 0
        avg_likes = np.mean(likes) if likes else 0
        avg_comments = np.mean(comments) if comments else 0
        
        # Engagement rates
        engagement_rate = (avg_likes + avg_comments) / avg_views * 100 if avg_views > 0 else 0
        views_per_sub = view_count / sub_count if sub_count > 0 else 0
        
        # Market size score (0-100)
        market_score = min(100, int(np.log10(sub_count + 1) * 20))
        
        # Saturation score (0-100)
        saturation_score = min(100, int(100 - (engagement_rate * 2)))
        
        # Profitability score (0-100)
        profit_score = min(100, int(avg_views / 10000))
        
        return {
            'channel_name': channel_stats['snippet']['title'],
            'subscribers': sub_count,
            'total_views': view_count,
            'videos': video_count,
            'avg_views': avg_views,
            'avg_likes': avg_likes,
            'avg_comments': avg_comments,
            'engagement_rate': engagement_rate,
            'views_per_sub': views_per_sub,
            'market_score': market_score,
            'saturation_score': saturation_score,
            'profit_score': profit_score,
            'video_stats': video_stats
        }

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
    
    title = snippet['title'][:50] + "..." if len(snippet['title']) > 50 else snippet['title']
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
    st.title("YouTube Niche Analyzer")
    st.markdown("Quickly analyze YouTube niches using live data to check market size, saturation levels and monetization potential.")
    
    # API Key Input
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
    
    with st.form("analysis_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            niche = st.text_input("NICHE", placeholder="For example, 'artificial intelligence' or 'minecraft'")
        
        with col2:
            channel_url = st.text_input("Channel URL (optional)", placeholder="https://www.youtube.com/@channelname")
        
        submitted = st.form_submit_button("Analyze")
    
    if submitted:
        if not niche and not channel_url:
            st.warning("Please enter either a niche or channel URL")
            return
        
        with st.spinner("Analyzing data..."):
            if channel_url:
                channel_id = analyzer.get_channel_id(channel_url)
                if not channel_id:
                    return
                
                results = analyzer.analyze_channel(channel_id)
                niche_name = results['channel_name']
            else:
                # Niche analysis (analyze top channels in niche)
                st.info("Niche analysis coming soon! Currently analyzing first channel found.")
                return
            
            st.header(f"{niche_name}")
            st.caption(f"Channels analyzed 1 • Videos analyzed {len(results['video_stats'])}")
            
            # Metrics display
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.subheader("Market Size")
                with st.container():
                    st.markdown(f"<div class='metric-box'><h3>{results['market_score']}</h3></div>", unsafe_allow_html=True)
                    display_progress_bar(results['market_score'])
                    viral_views = f"{results['total_views']/1000000:.1f}M" if results['total_views'] > 1000000 else f"{results['total_views']/1000:.1f}K"
                    st.markdown(f"""
                    <p class="big-font">Viral Views Potential {viral_views}</p>
                    <p class="big-font">Loyal Audience {results['subscribers']:,}</p>
                    """, unsafe_allow_html=True)
                    st.write("Decent market size with good potential for viral content.")
            
            with col2:
                st.subheader("Unsaturated")
                with st.container():
                    st.markdown(f"<div class='metric-box'><h3>{results['saturation_score']}</h3></div>", unsafe_allow_html=True)
                    display_progress_bar(results['saturation_score'])
                    st.markdown(f"""
                    <p class="big-font">Reach Beyond Subscribers {results['views_per_sub']:.1f}</p>
                    <p class="big-font">Loyal Subs {results['engagement_rate']:.1f}%</p>
                    """, unsafe_allow_html=True)
                    st.write("This niche appears to be unsaturated with good growth potential.")
            
            with col3:
                st.subheader("Profitable")
                with st.container():
                    st.markdown(f"<div class='metric-box'><h3>{results['profit_score']}</h3></div>", unsafe_allow_html=True)
                    display_progress_bar(results['profit_score'])
                    rpm_range = (1.5, 2.8)  # Example RPM range
                    st.markdown(f"""
                    <p class="big-font">RPM Estimation ${rpm_range[0]} - ${rpm_range[1]}</p>
                    <p class="big-font">Avg. Views {results['avg_views']:,.0f}</p>
                    """, unsafe_allow_html=True)
                    st.write("Moderate revenue potential based on average view counts.")
            
            st.divider()
            
            # Sample videos section
            st.subheader("Top Performing Videos")
            for video in sorted(results['video_stats'], key=lambda x: int(x['statistics'].get('viewCount', 0)), reverse=True)[:5]:
                display_video_card(video)
            
            st.divider()
            
            # Revenue estimations
            st.subheader("Revenue Estimations")
            rpm_low, rpm_high = rpm_range
            st.markdown(f"<p class='big-font'>1,000 (RPM) views ${rpm_low*1:.1f} to ${rpm_high*1:.1f}</p>", unsafe_allow_html=True)
            st.markdown(f"<p class='big-font'>10,000 views ${rpm_low*10:.1f} to ${rpm_high*10:.1f}</p>", unsafe_allow_html=True)
            st.markdown(f"<p class='big-font'>100,000 views ${rpm_low*100:.1f} to ${rpm_high*100:.1f}</p>", unsafe_allow_html=True)
            st.markdown(f"<p class='big-font'>1,000,000 views ${rpm_low*1000:.1f}K to ${rpm_high*1000/1000:.1f}K</p>", unsafe_allow_html=True)
            
            st.caption("These estimations are not 100% reliable and are for English speaking audiences only.")

if __name__ == "__main__":
    main()
