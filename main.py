import streamlit as st
import pandas as pd
import requests
from datetime import datetime
import plotly.graph_objects as go
import re
import numpy as np

# Set page config
st.set_page_config(
    page_title="TubeLab Niche Analyzer",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .big-font { font-size:18px !important; }
    .metric-box { 
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 15px;
    }
    .video-card {
        border-left: 4px solid #4285F4;
        padding: 10px;
        margin-bottom: 10px;
        background-color: #f9f9f9;
    }
</style>
""", unsafe_allow_html=True)

# Main title
st.title("🔍 YouTube Niche Analyzer")
st.markdown("""
<div class="big-font">
Analyze any YouTube channel to understand market potential, saturation levels, and profitability - just like TubeLab.net
</div>
""", unsafe_allow_html=True)

# API Key Input (built into main interface)
api_key = st.text_input("AIzaSyBesFo-hRJHEGXvRfxXbJ0rCxm5zEC3ZtY:", 
                       type="password",
                       help="Get your API key from Google Cloud Console")

# Function to extract channel ID from URL
def extract_channel_id(url):
    patterns = [
        r'youtube\.com/channel/([a-zA-Z0-9_-]+)',
        r'youtube\.com/c/([a-zA-Z0-9_-]+)',
        r'youtube\.com/user/([a-zA-Z0-9_-]+)',
        r'youtube\.com/@([a-zA-Z0-9_-]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    # Handle custom URLs
    if 'youtube.com' in url:
        return "custom_url"
    
    return None

# Function to get channel data with error handling
def get_channel_data(api_key, channel_id):
    try:
        url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&id={channel_id}&key={api_key}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'error' in data:
            error_msg = data['error']['message']
            if 'quota' in error_msg.lower():
                return {"error": "API quota exceeded. Please try again tomorrow or upgrade your quota."}
            return {"error": error_msg}
        
        if 'items' not in data or not data['items']:
            return {"error": "Channel not found. Please check the URL."}
        
        channel_info = data['items'][0]
        return {
            'title': channel_info['snippet']['title'],
            'description': channel_info['snippet']['description'],
            'subscribers': int(channel_info['statistics']['subscriberCount']),
            'views': int(channel_info['statistics']['viewCount']),
            'videos': int(channel_info['statistics']['videoCount']),
            'thumbnail': channel_info['snippet']['thumbnails']['high']['url']
        }
    except Exception as e:
        return {"error": f"Connection error: {str(e)}"}

# Function to get channel videos with error handling
def get_channel_videos(api_key, channel_id, max_results=50):
    try:
        # Get uploads playlist ID
        url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={channel_id}&key={api_key}"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if 'items' not in data or not data['items']:
            return []
        
        uploads_playlist_id = data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
        
        # Get videos from playlist
        videos = []
        next_page_token = None
        
        while len(videos) < max_results:
            url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=50&key={api_key}"
            if next_page_token:
                url += f"&pageToken={next_page_token}"
            
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if 'items' not in data:
                break
                
            for item in data['items']:
                video_id = item['snippet']['resourceId']['videoId']
                videos.append({
                    'video_id': video_id,
                    'title': item['snippet']['title'],
                    'published_at': item['snippet']['publishedAt'],
                    'thumbnail': item['snippet']['thumbnails']['high']['url']
                })
            
            if 'nextPageToken' in data:
                next_page_token = data['nextPageToken']
            else:
                break
        
        return videos[:max_results]
    except:
        return []

# Function to get video statistics with error handling
def get_video_stats(api_key, video_ids):
    if not video_ids:
        return []
    
    try:
        chunks = [video_ids[i:i + 50] for i in range(0, len(video_ids), 50)]
        all_stats = []
        
        for chunk in chunks:
            video_ids_str = ','.join(chunk)
            url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics,contentDetails,snippet&id={video_ids_str}&key={api_key}"
            response = requests.get(url, timeout=10)
            data = response.json()
            
            if 'items' not in data:
                continue
                
            for item in data['items']:
                stats = item['statistics']
                details = item['contentDetails']
                
                # Parse duration
                duration = details['duration']
                time_match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
                hours = int(time_match.group(1) or 0)
                minutes = int(time_match.group(2) or 0)
                seconds = int(time_match.group(3) or 0)
                total_seconds = hours * 3600 + minutes * 60 + seconds
                
                all_stats.append({
                    'video_id': item['id'],
                    'views': int(stats.get('viewCount', 0)),
                    'likes': int(stats.get('likeCount', 0)),
                    'comments': int(stats.get('commentCount', 0)),
                    'duration': total_seconds,
                    'tags': item['snippet'].get('tags', [])
                })
        
        return all_stats
    except:
        return []

# Enhanced niche analysis function
def analyze_niche(videos_data, channel_data):
    if not videos_data:
        return {}
    
    # Basic metrics
    total_videos = len(videos_data)
    total_views = sum(v['views'] for v in videos_data)
    avg_views = total_views / total_videos
    max_views = max(v['views'] for v in videos_data)
    
    # Engagement metrics
    total_engagement = sum(v['likes'] + v['comments'] for v in videos_data)
    avg_engagement_rate = total_engagement / total_views * 100 if total_views > 0 else 0
    
    # Market size score (0-100)
    market_size_score = min(100, np.log10(max_views) * 20)
    
    # Saturation score (0-100) - lower is better (less saturated)
    if channel_data:
        reach_ratio = avg_views / channel_data['subscribers'] if channel_data['subscribers'] > 0 else 1
        saturation_score = max(0, 100 - (reach_ratio * 100))
    else:
        saturation_score = 50
    
    # RPM estimates (based on English content)
    rpm = 2.0  # Base RPM
    category_bonus = 1.0  # Default
    
    # Adjust RPM based on engagement
    if avg_engagement_rate > 5:
        rpm *= 1.2
    elif avg_engagement_rate < 2:
        rpm *= 0.8
    
    # Profitability score (0-100)
    profitability_score = min(100, (rpm * avg_views / 1000) / 2 * 100)
    
    # Tags analysis
    all_tags = []
    for video in videos_data:
        all_tags.extend(video['tags'])
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    top_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    
    return {
        'total_videos': total_videos,
        'avg_views': avg_views,
        'max_views': max_views,
        'avg_engagement_rate': avg_engagement_rate,
        'market_size_score': market_size_score,
        'saturation_score': saturation_score,
        'profitability_score': profitability_score,
        'estimated_rpm': rpm,
        'top_tags': top_tags,
        'total_engagement': total_engagement
    }

# Create gauge chart function
def create_gauge(value, title, color):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 16}},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': color},
            'bar': {'color': color},
            'steps': [
                {'range': [0, 33], 'color': "#FF6B6B"},
                {'range': [33, 66], 'color': "#FFD166"},
                {'range': [66, 100], 'color': "#06D6A0"}],
            'threshold': {
                'line': {'color': "black", 'width': 4},
                'thickness': 0.75,
                'value': value}
        }
    ))
    fig.update_layout(margin=dict(t=50, b=10), height=250)
    return fig

# Main app function
def main():
    channel_url = st.text_input("Enter YouTube Channel URL:", 
                               placeholder="https://www.youtube.com/@ChannelName",
                               help="Paste any YouTube channel URL")
    
    if channel_url and api_key:
        channel_id = extract_channel_id(channel_url)
        
        if not channel_id:
            st.error("Invalid YouTube URL. Please enter a valid channel URL.")
            return
        
        with st.spinner("Analyzing channel data..."):
            # Get channel data
            channel_data = get_channel_data(api_key, channel_id)
            
            if 'error' in channel_data:
                st.error(f"Error: {channel_data['error']}")
                return
            
            # Get channel videos
            videos = get_channel_videos(api_key, channel_id, 30)
            if not videos:
                st.error("Could not fetch videos. The channel may have no videos or is private.")
                return
            
            # Get video stats
            video_ids = [v['video_id'] for v in videos]
            video_stats = get_video_stats(api_key, video_ids)
            
            # Combine data
            for i, video in enumerate(videos):
                for stat in video_stats:
                    if video['video_id'] == stat['video_id']:
                        videos[i].update(stat)
                        break
            
            # Analyze niche
            niche_data = analyze_niche(videos, channel_data)
            
            # Display results
            st.markdown("---")
            st.subheader("📊 Niche Analysis Results")
            
            # Channel overview
            col1, col2 = st.columns([1, 3])
            with col1:
                st.image(channel_data['thumbnail'], width=200)
                st.metric("Subscribers", f"{channel_data['subscribers']:,}")
                st.metric("Total Views", f"{channel_data['views']:,}")
                st.metric("Total Videos", f"{channel_data['videos']:,}")
            
            with col2:
                st.subheader(channel_data['title'])
                st.markdown(f"**Channel Description:** {channel_data['description'][:300]}...")
                
                # Metrics row
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.metric("Avg. Views", f"{niche_data['avg_views']/1000:.1f}K")
                with m2:
                    st.metric("Max Views", f"{niche_data['max_views']/1000:.1f}K")
                with m3:
                    st.metric("Engagement Rate", f"{niche_data['avg_engagement_rate']:.1f}%")
            
            # Gauge charts
            st.markdown("---")
            st.subheader("📈 Niche Potential")
            
            g1, g2, g3 = st.columns(3)
            with g1:
                st.plotly_chart(create_gauge(
                    niche_data['market_size_score'], 
                    "Market Size", 
                    "#4285F4"
                ), use_container_width=True)
                st.markdown(f"""
                <div class="metric-box">
                    <b>Viral Potential:</b> {niche_data['max_views']/1000000:.1f}M views<br>
                    <b>Avg. Views:</b> {niche_data['avg_views']/1000:.1f}K
                </div>
                """, unsafe_allow_html=True)
            
            with g2:
                st.plotly_chart(create_gauge(
                    niche_data['saturation_score'], 
                    "Unsaturation", 
                    "#34A853"
                ), use_container_width=True)
                st.markdown(f"""
                <div class="metric-box">
                    <b>Reach Ratio:</b> {(niche_data['avg_views']/channel_data['subscribers'] if channel_data['subscribers'] > 0 else 0):.1f}x<br>
                    <b>Loyalty:</b> {niche_data['avg_engagement_rate']:.1f}%
                </div>
                """, unsafe_allow_html=True)
            
            with g3:
                st.plotly_chart(create_gauge(
                    niche_data['profitability_score'], 
                    "Profitability", 
                    "#EA4335"
                ), use_container_width=True)
                st.markdown(f"""
                <div class="metric-box">
                    <b>Est. RPM:</b> ${niche_data['estimated_rpm']:.1f}-${niche_data['estimated_rpm']*1.5:.1f}<br>
                    <b>Per 100K views:</b> ${niche_data['estimated_rpm']*100:.0f}-${niche_data['estimated_rpm']*150:.0f}
                </div>
                """, unsafe_allow_html=True)
            
            # Niche summary
            st.markdown("---")
            st.subheader("📝 Niche Summary")
            
            col1, col2 = st.columns(2)
            with col1:
                if niche_data['market_size_score'] > 70:
                    st.success("**Large Market:** This niche has significant audience potential with videos reaching {:,} views.".format(niche_data['max_views']))
                elif niche_data['market_size_score'] > 40:
                    st.info("**Moderate Market:** Decent audience size with videos typically reaching {:,} views.".format(int(niche_data['avg_views'])))
                else:
                    st.warning("**Small Market:** Limited audience potential in this niche.")
                
                if niche_data['saturation_score'] > 70:
                    st.success("**Low Competition:** This niche appears unsaturated with good growth opportunities.")
                elif niche_data['saturation_score'] > 40:
                    st.info("**Moderate Competition:** Some competition exists but there's still room to grow.")
                else:
                    st.warning("**High Competition:** This niche appears quite saturated.")
            
            with col2:
                if niche_data['profitability_score'] > 70:
                    st.success("**High Profit Potential:** This niche has strong monetization opportunities.")
                elif niche_data['profitability_score'] > 40:
                    st.info("**Moderate Profit Potential:** Decent revenue potential but may require volume.")
                else:
                    st.warning("**Low Profit Potential:** Monetization may be challenging in this niche.")
                
                st.markdown(f"""
                <div class="metric-box">
                    <b>Top Tags:</b> {', '.join([tag[0] for tag in niche_data['top_tags']])}<br>
                    content_types = ['Entertainment', 'Education', 'How-to', 'Vlog', 'Review']
content_index = int(niche_data['avg_engagement_rate']//20)
<b>Content Type:</b> {content_types[content_index]}
                </div>
                """, unsafe_allow_html=True)
            
            # Revenue estimates
            st.markdown("---")
            st.subheader("💰 Revenue Estimates")
            
            rpm_low = niche_data['estimated_rpm']
            rpm_high = niche_data['estimated_rpm'] * 1.5
            
            rev_data = {
                "Views": ["1,000", "10,000", "100,000", "1,000,000"],
                "Low Estimate": [
                    f"${rpm_low * 1:.1f}",
                    f"${rpm_low * 10:.1f}",
                    f"${rpm_low * 100:.1f}",
                    f"${rpm_low * 1000:.1f}K"
                ],
                "High Estimate": [
                    f"${rpm_high * 1:.1f}",
                    f"${rpm_high * 10:.1f}",
                    f"${rpm_high * 100:.1f}",
                    f"${rpm_high * 1000:.1f}K"
                ]
            }
            
            st.table(pd.DataFrame(rev_data))
            st.caption("Note: Estimates are for English-speaking audiences. Actual earnings may vary based on audience demographics, content type, and advertiser demand.")
            
            # Top videos
            st.markdown("---")
            st.subheader("🎬 Top Performing Videos")
            
            top_videos = sorted(videos, key=lambda x: x['views'], reverse=True)[:5]
            
            for video in top_videos:
                days_old = (datetime.now() - datetime.strptime(video['published_at'], "%Y-%m-%dT%H:%M:%SZ")).days
                engagement_rate = ((video['likes'] + video['comments']) / video['views'] * 100) if video['views'] > 0 else 0
                
                st.markdown(f"""
                <div class="video-card">
                    <div style="display:flex">
                        <img src="{video['thumbnail']}" width="120" style="margin-right:15px">
                        <div>
                            <h4>{video['title']}</h4>
                            <p>
                                <b>{video['views']/1000:.1f}K views</b> | 
                                <b>{engagement_rate:.1f}% engagement</b> | 
                                <b>{days_old} days old</b>
                            </p>
                            <p>Vs Average: {(video['views'] - niche_data['avg_views'])/niche_data['avg_views']*100:.1f}%</p>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
