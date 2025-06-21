import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from urllib.parse import urlparse, parse_qs
import re
import numpy as np

# Set page config
st.set_page_config(page_title="Advanced YouTube Niche Analyzer", layout="wide")

# Main title
st.title("YouTube Niche Analyzer")
st.markdown("Analyze any YouTube niche to understand market size, saturation, and profitability potential.")

# Sidebar for API key input
with st.sidebar:
    st.header("YouTube API Setup")
    api_key = st.text_input("Enter your YouTube API Key:", type="password")
    st.markdown("""
    **How to get a YouTube API key:**
    1. Go to [Google Cloud Console](https://console.cloud.google.com/)
    2. Create a new project
    3. Enable "YouTube Data API v3"
    4. Create credentials (API key)
    """)
    st.markdown("---")
    st.info("This tool uses the YouTube API to fetch channel and video data. Your API key is not stored.")

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
    
    # Handle custom URLs that might redirect
    if 'youtube.com' in url:
        return "custom_url"
    
    return None

# Function to get channel data
def get_channel_data(api_key, channel_id):
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet,statistics&id={channel_id}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    
    if 'items' not in data or not data['items']:
        return None
    
    channel_info = data['items'][0]
    return {
        'title': channel_info['snippet']['title'],
        'description': channel_info['snippet']['description'],
        'subscribers': int(channel_info['statistics']['subscriberCount']),
        'views': int(channel_info['statistics']['viewCount']),
        'videos': int(channel_info['statistics']['videoCount']),
        'thumbnail': channel_info['snippet']['thumbnails']['high']['url']
    }

# Function to get channel videos
def get_channel_videos(api_key, channel_id, max_results=50):
    # First, get the uploads playlist ID
    url = f"https://www.googleapis.com/youtube/v3/channels?part=contentDetails&id={channel_id}&key={api_key}"
    response = requests.get(url)
    data = response.json()
    
    if 'items' not in data or not data['items']:
        return []
    
    uploads_playlist_id = data['items'][0]['contentDetails']['relatedPlaylists']['uploads']
    
    # Now get videos from the uploads playlist
    videos = []
    next_page_token = None
    
    while len(videos) < max_results:
        url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet&playlistId={uploads_playlist_id}&maxResults=50&key={api_key}"
        if next_page_token:
            url += f"&pageToken={next_page_token}"
        
        response = requests.get(url)
        data = response.json()
        
        if 'items' not in data:
            break
            
        for item in data['items']:
            video_id = item['snippet']['resourceId']['videoId']
            videos.append({
                'video_id': video_id,
                'title': item['snippet']['title'],
                'description': item['snippet']['description'],
                'published_at': item['snippet']['publishedAt'],
                'thumbnail': item['snippet']['thumbnails']['high']['url']
            })
        
        if 'nextPageToken' in data:
            next_page_token = data['nextPageToken']
        else:
            break
    
    return videos[:max_results]

# Function to get video statistics
def get_video_stats(api_key, video_ids):
    if not video_ids:
        return []
    
    # YouTube API allows up to 50 videos per request
    chunks = [video_ids[i:i + 50] for i in range(0, len(video_ids), 50)]
    all_stats = []
    
    for chunk in chunks:
        video_ids_str = ','.join(chunk)
        url = f"https://www.googleapis.com/youtube/v3/videos?part=statistics,contentDetails,snippet&id={video_ids_str}&key={api_key}"
        response = requests.get(url)
        data = response.json()
        
        if 'items' not in data:
            continue
            
        for item in data['items']:
            stats = item['statistics']
            snippet = item['snippet']
            details = item['contentDetails']
            
            duration = details['duration']
            # Parse ISO 8601 duration
            hours = 0
            minutes = 0
            seconds = 0
            
            time_match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration)
            if time_match:
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
                'tags': snippet.get('tags', []),
                'category': snippet.get('categoryId', '')
            })
    
    return all_stats

# Function to analyze niche
def analyze_niche(videos_data, channel_data):
    if not videos_data:
        return {}
    
    # Calculate averages
    total_videos = len(videos_data)
    total_views = sum(v['views'] for v in videos_data)
    total_likes = sum(v['likes'] for v in videos_data)
    total_comments = sum(v['comments'] for v in videos_data)
    total_duration = sum(v['duration'] for v in videos_data)
    
    avg_views = total_views / total_videos
    avg_likes = total_likes / total_videos
    avg_comments = total_comments / total_videos
    avg_duration = total_duration / total_videos
    
    # Calculate engagement rates
    avg_engagement_rate = (avg_likes + avg_comments) / avg_views * 100 if avg_views > 0 else 0
    
    # Find most common tags
    all_tags = []
    for video in videos_data:
        all_tags.extend(video['tags'])
    
    tag_counts = {}
    for tag in all_tags:
        tag_counts[tag] = tag_counts.get(tag, 0) + 1
    
    sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
    top_tags = [tag[0] for tag in sorted_tags[:10]]
    
    # Calculate market size score (0-100)
    max_views = max(v['views'] for v in videos_data)
    market_size_score = min(100, max_views / 50000)  # 50K views = score 100
    
    # Calculate saturation score (0-100)
    # Lower score means less saturated
    if channel_data:
        reach_ratio = avg_views / channel_data['subscribers'] if channel_data['subscribers'] > 0 else 1
        saturation_score = max(0, 100 - (reach_ratio * 100))
    else:
        saturation_score = 50
    
    # Calculate profitability score (0-100)
    # Based on RPM estimates ($1.5-$2.8 per 1000 views for English content)
    rpm = 2.0  # Average RPM
    estimated_earnings = (avg_views / 1000) * rpm
    profitability_score = min(100, estimated_earnings / 50 * 100)  # $50 = score 100
    
    return {
        'total_videos': total_videos,
        'avg_views': avg_views,
        'avg_likes': avg_likes,
        'avg_comments': avg_comments,
        'avg_duration': avg_duration,
        'avg_engagement_rate': avg_engagement_rate,
        'top_tags': top_tags,
        'market_size_score': market_size_score,
        'saturation_score': saturation_score,
        'profitability_score': profitability_score,
        'max_views': max_views,
        'estimated_rpm': rpm,
        'estimated_earnings': estimated_earnings
    }

# Function to create gauge chart
def create_gauge_chart(value, title):
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title},
        gauge = {
            'axis': {'range': [None, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 49], 'color': "lightgray"},
                {'range': [50, 70], 'color': "gray"},
                {'range': [71, 100], 'color': "darkgray"}],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': value}
        }
    ))
    fig.update_layout(margin=dict(l=20, r=20, t=50, b=20))
    return fig

# Main app
def main():
    st.header("Niche Analysis")
    channel_url = st.text_input("Enter YouTube Channel URL (e.g., https://www.youtube.com/@ChannelName):")
    
    if channel_url and api_key:
        channel_id = extract_channel_id(channel_url)
        
        if channel_id == "custom_url":
            st.warning("Custom channel URLs need special handling. Please try to find the channel ID directly.")
        elif channel_id:
            with st.spinner("Fetching channel data..."):
                channel_data = get_channel_data(api_key, channel_id)
                
                if channel_data:
                    # Display channel info
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        st.image(channel_data['thumbnail'], width=200)
                        st.metric("Subscribers", f"{channel_data['subscribers']:,}")
                        st.metric("Total Views", f"{channel_data['views']:,}")
                        st.metric("Total Videos", f"{channel_data['videos']:,}")
                    
                    with col2:
                        st.subheader(channel_data['title'])
                        st.text_area("Channel Description", channel_data['description'], height=100, disabled=True)
                        
                        # Get channel videos
                        videos = get_channel_videos(api_key, channel_id, max_results=50)
                        video_ids = [v['video_id'] for v in videos]
                        video_stats = get_video_stats(api_key, video_ids)
                        
                        # Combine video data with stats
                        for i, video in enumerate(videos):
                            for stat in video_stats:
                                if video['video_id'] == stat['video_id']:
                                    videos[i].update(stat)
                                    break
                        
                        if videos:
                            # Analyze niche
                            niche_data = analyze_niche(videos, channel_data)
                            
                            # Display niche analysis
                            st.markdown("---")
                            st.subheader("Niche Analysis Results")
                            
                            # Create columns for gauge charts
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.plotly_chart(create_gauge_chart(niche_data['market_size_score'], "Market Size"), use_container_width=True)
                                st.markdown(f"**Viral Views Potential:** {niche_data['max_views']/1000:.1f}K")
                                st.markdown(f"**Loyal Audience:** {niche_data['avg_views']/1000:.1f}K")
                            
                            with col2:
                                st.plotly_chart(create_gauge_chart(niche_data['saturation_score'], "Unsaturated"), use_container_width=True)
                                st.markdown(f"**Reach Beyond Subscribers:** {niche_data['avg_views']/channel_data['subscribers']:.1f}x")
                                st.markdown(f"**Loyal Subs:** {niche_data['avg_views']/channel_data['subscribers']*100:.0f}%")
                            
                            with col3:
                                st.plotly_chart(create_gauge_chart(niche_data['profitability_score'], "Profitable"), use_container_width=True)
                                st.markdown(f"**RPM Estimation:** ${niche_data['estimated_rpm']:.1f} - ${niche_data['estimated_rpm']*1.8:.1f}")
                                st.markdown(f"**Avg. Views:** {niche_data['avg_views']/1000:.1f}K")
                            
                            # Display summary
                            st.markdown("---")
                            st.subheader("Niche Summary")
                            
                            if niche_data['market_size_score'] > 70:
                                st.success("**Great market size** - A viral video could reach {:,} views.".format(niche_data['max_views']))
                            else:
                                st.warning("**Limited market size** - Maximum views in this niche: {:,}".format(niche_data['max_views']))
                            
                            if niche_data['saturation_score'] > 70:
                                st.success("**Unsaturated niche** - Great opportunity with low competition.")
                            else:
                                st.warning("**Saturated niche** - High competition in this space.")
                            
                            if niche_data['profitability_score'] > 70:
                                st.success("**Highly profitable** - Good revenue potential in this niche.")
                            elif niche_data['profitability_score'] > 30:
                                st.info("**Moderately profitable** - Decent revenue potential.")
                            else:
                                st.warning("**Low profitability** - Limited revenue potential.")
                            
                            # Revenue estimation table
                            st.markdown("---")
                            st.subheader("Revenue Estimations")
                            
                            rpm_low = niche_data['estimated_rpm']
                            rpm_high = niche_data['estimated_rpm'] * 1.8
                            
                            revenue_data = {
                                'Views': ['1,000', '10,000', '100,000', '1,000,000'],
                                'Estimated Revenue (Low)': [
                                    f"${rpm_low * 1:.1f}",
                                    f"${rpm_low * 10:.1f}",
                                    f"${rpm_low * 100:.1f}",
                                    f"${rpm_low * 1000:.1f}K"
                                ],
                                'Estimated Revenue (High)': [
                                    f"${rpm_high * 1:.1f}",
                                    f"${rpm_high * 10:.1f}",
                                    f"${rpm_high * 100:.1f}",
                                    f"${rpm_high * 1000:.1f}K"
                                ]
                            }
                            
                            st.table(pd.DataFrame(revenue_data))
                            st.caption("These estimations are not 100% reliable and are for English-speaking audiences only.")
                            
                            # Top videos analysis
                            st.markdown("---")
                            st.subheader("Top Performing Videos")
                            
                            top_videos = sorted(videos, key=lambda x: x['views'], reverse=True)[:5]
                            
                            for video in top_videos:
                                with st.expander(f"{video['title']} - {video['views']:,} views"):
                                    col1, col2 = st.columns([1, 3])
                                    
                                    with col1:
                                        st.image(video['thumbnail'], width=200)
                                        st.metric("Views", f"{video['views']:,}")
                                        st.metric("Likes", f"{video['likes']:,}")
                                        st.metric("Comments", f"{video['comments']:,}")
                                    
                                    with col2:
                                        engagement_rate = (video['likes'] + video['comments']) / video['views'] * 100 if video['views'] > 0 else 0
                                        st.metric("Engagement Rate", f"{engagement_rate:.1f}%")
                                        
                                        days_old = (datetime.now() - datetime.strptime(video['published_at'], "%Y-%m-%dT%H:%M:%SZ")).days
                                        st.metric("Age", f"{days_old} days")
                                        
                                        # Compare to average
                                        vs_avg = (video['views'] - niche_data['avg_views']) / niche_data['avg_views'] * 100
                                        st.metric("Vs Average", f"{vs_avg:.1f}%")
                            
                            # Tags analysis
                            st.markdown("---")
                            st.subheader("Top Tags")
                            
                            if niche_data['top_tags']:
                                tags_df = pd.DataFrame(niche_data['top_tags'], columns=['Tag'])
                                st.table(tags_df)
                            else:
                                st.info("No tags found for these videos.")
                        else:
                            st.error("Could not fetch videos for this channel. Please check the channel URL and API key.")
                else:
                    st.error("Could not fetch channel data. Please check the channel URL and API key.")

if __name__ == "__main__":
    main()
