import streamlit as st
import requests
from urllib.parse import parse_qs, urlparse

st.set_page_config(page_title="Watch Video", layout="wide")

# Get video ID from URL query parameters
query_params = st.query_params
video_id = query_params.get("v", None)

if not video_id:
    st.error("No video specified")
    st.stop()

# Fetch video details from API
API_URL = "http://localhost:8002"
try:
    resp = requests.get(f"{API_URL}/videos/{video_id}", timeout=5)
    resp.raise_for_status()
    video = resp.json()
except requests.RequestException as e:
    st.error(f"Failed to load video: {e}")
    st.stop()

# Display video player
st.title(video.get("title", "Untitled"))
st.caption(f"{video.get('views', 0):,} views")

if video.get("script"):
    st.markdown(f"_{video.get('script')}_")
    st.markdown("---")

# Video player
video_url = video.get("video")
if video_url:
    st.video(video_url)
else:
    st.error("Video URL not available")

# Additional info
col1, col2 = st.columns(2)
with col1:
    st.caption(f"**Uploaded by:** {video.get('user', 'Unknown')}")
with col2:
    st.caption(f"**Created:** {video.get('created_at', 'Unknown')}")