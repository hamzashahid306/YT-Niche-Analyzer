import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta
import plotly.express as px
import plotly.graph_objects as go
from urllib.parse import urlparse, parse_qs
import re

# Set page config
st.set_page_config(page_title="YouTube Niche Analyzer", layout="wide")

# Main title
st.title("YouTube Niche Analyzer")
st.markdown("Analyze any YouTube channel or video to understand its performance and niche.")

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
def analyze_niche(videos_data):
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
    
    return {
        'total_videos': total_videos,
        'avg_views': avg_views,
        'avg_likes': avg_likes,
        'avg_comments': avg_comments,
        'avg_duration': avg_duration,
        'avg_engagement_rate': avg_engagement_rate,
        'top_tags': top_tags
    }

# Main app
def main():
    tab1, tab2 = st.tabs(["Channel Analysis", "Video Analysis"])
    
    with tab1:
        st.header("Channel Analysis")
        channel_url = st.text_input("Enter YouTube Channel URL:")
        
        if channel_url and api_key:
            channel_id = extract_channel_id(channel_url)
            
            if channel_id == "custom_url":
                st.warning("Custom channel URLs need special handling. Please try to find the channel ID directly.")
            elif channel_id:
                with st.spinner("Fetching channel data..."):
                    channel_data = get_channel_data(api_key, channel_id)
                    
                    if channel_data:
                        col1, col2 = st.columns([1, 3])
                        
                        with col1:
                            st.image(channel_data['thumbnail'], width=200)
                            st.metric("Subscribers", f"{channel_data['subscribers']:,}")
                            st.metric("Total Views", f"{channel_data['views']:,}")
                            st.metric("Total Videos", f"{channel_data['videos']:,}")
                        
                        with col2:
                            st.subheader(channel_data['title'])
                            st.text_area("Channel Description", channel_data['description'], height=150)
                            
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
                                niche_data = analyze_niche(videos)
                                
                                st.subheader("Channel Performance Metrics")
                                col1, col2, col3, col4 = st.columns(4)
                                
                                with col1:
                                    st.metric("Average Views", f"{niche_data['avg_views']:,.0f}")
                                with col2:
                                    st.metric("Average Likes", f"{niche_data['avg_likes']:,.0f}")
                                with col3:
                                    st.metric("Average Comments", f"{niche_data['avg_comments']:,.0f}")
                                with col4:
                                    st.metric("Engagement Rate", f"{niche_data['avg_engagement_rate']:.2f}%")
                                
                                # Create dataframe for visualization
                                df = pd.DataFrame(videos)
                                df['published_at'] = pd.to_datetime(df['published_at'])
                                df['published_date'] = df['published_at'].dt.date
                                
                                # Views over time
                                st.subheader("Views Over Time")
                                fig = px.line(df, x='published_date', y='views', 
                                             title='Video Views Over Time',
                                             hover_data=['title'])
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Duration analysis
                                st.subheader("Video Duration Analysis")
                                fig = px.histogram(df, x='duration', 
                                                  title='Distribution of Video Durations (seconds)',
                                                  nbins=20)
                                st.plotly_chart(fig, use_container_width=True)
                                
                                # Top tags
                                st.subheader("Top Tags")
                                if niche_data['top_tags']:
                                    tags_df = pd.DataFrame(niche_data['top_tags'], columns=['Tag'])
                                    st.table(tags_df)
                                else:
                                    st.info("No tags found for these videos.")
                                
                                # Top performing videos
                                st.subheader("Top Performing Videos")
                                top_videos = sorted(videos, key=lambda x: x['views'], reverse=True)[:10]
                                for video in top_videos:
                                    with st.expander(f"{video['title']} - {video['views']:,} views"):
                                        col1, col2 = st.columns([1, 3])
                                        with col1:
                                            st.image(video['thumbnail'], width=150)
                                        with col2:
                                            st.write(f"**Published:** {video['published_at']}")
                                            st.write(f"**Likes:** {video['likes']:,}")
                                            st.write(f"**Comments:** {video['comments']:,}")
                                            st.write(f"**Duration:** {video['duration']} seconds")
                                            st.write(f"**Engagement Rate:** {(video['likes'] + video['comments']) / video['views'] * 100:.2f}%")
                            else:
                                st.warning("No videos found for this channel.")
                    else:
                        st.error("Could not fetch channel data. Please check the channel URL and API key.")
    
    with tab2:
        st.header("Video Analysis")
        video_url = st.text_input("Enter YouTube Video URL:")
        
        if video_url and api_key:
            # Extract video ID from URL
            video_id = None
            if 'youtube.com/watch?v=' in video_url:
                video_id = video_url.split('v=')[1].split('&')[0]
            elif 'youtu.be/' in video_url:
                video_id = video_url.split('youtu.be/')[1].split('?')[0]
            
            if video_id:
                with st.spinner("Fetching video data..."):
                    video_stats = get_video_stats(api_key, [video_id])
                    
                    if video_stats:
                        video_data = video_stats[0]
                        
                        # Get video snippet data
                        url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={api_key}"
                        response = requests.get(url)
                        snippet_data = response.json()
                        
                        if 'items' in snippet_data and snippet_data['items']:
                            snippet = snippet_data['items'][0]['snippet']
                            
                            col1, col2 = st.columns([1, 3])
                            
                            with col1:
                                st.image(snippet['thumbnails']['high']['url'], width=300)
                                st.metric("Views", f"{video_data['views']:,}")
                                st.metric("Likes", f"{video_data['likes']:,}")
                                st.metric("Comments", f"{video_data['comments']:,}")
                                st.metric("Duration", f"{video_data['duration']} seconds")
                                
                                engagement_rate = (video_data['likes'] + video_data['comments']) / video_data['views'] * 100 if video_data['views'] > 0 else 0
                                st.metric("Engagement Rate", f"{engagement_rate:.2f}%")
                            
                            with col2:
                                st.subheader(snippet['title'])
                                st.write(f"**Published:** {snippet['publishedAt']}")
                                st.text_area("Description", snippet['description'], height=200)
                                
                                if 'tags' in snippet and snippet['tags']:
                                    st.subheader("Tags")
                                    st.write(", ".join(snippet['tags']))
                    else:
                        st.error("Could not fetch video data. Please check the video URL and API key.")

if __name__ == "__main__":
    main()
