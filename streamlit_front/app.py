# --------------------------------------------------------------
# QuipVid – Movie Quote Video Library
# --------------------------------------------------------------
import streamlit as st
import requests
import random
from typing import List, Dict

# ----------------------------------------------------------------------
# Helper functions
# ----------------------------------------------------------------------
def fetch_videos(api_url: str) -> List[Dict]:
    """
    Retrieve the list of videos from the API.
    Returns an empty list on failure and shows an error message.
    """
    try:
        resp = requests.get(api_url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        # API returns {'videos': [...], 'total': ..., 'page': ...}
        # Extract just the videos list
        if isinstance(data, dict) and 'videos' in data:
            return data['videos']
        elif isinstance(data, list):
            return data
        else:
            st.error(f"Unexpected API response format")
            return []
            
    except requests.RequestException as exc:
        st.error(f"❗ Unable to load videos: {exc}")
        return []


def sort_by_views(videos: List[Dict]) -> List[Dict]:
    """Return videos sorted descending by the `views` field."""
    return sorted(videos, key=lambda v: v.get("views", 0), reverse=True)


def random_subset(videos: List[Dict], n: int = 8) -> List[Dict]:
    """Return *n* random videos (or all if fewer)."""
    if len(videos) == 0:
        return []
    return random.sample(videos, min(n, len(videos)))


def filter_by_title(videos: List[Dict], query: str) -> List[Dict]:
    """Case‑insensitive filter on the `title` field."""
    if not query:
        return videos
    q = query.lower()
    return [v for v in videos if q in v.get("title", "").lower()]


# ----------------------------------------------------------------------
# Page configuration
# ----------------------------------------------------------------------
st.set_page_config(page_title="QuipVid", layout="wide")

# ----------------------------------------------------------------------
# Hero section + search bar
# ----------------------------------------------------------------------
col1, col2 = st.columns([3, 1], gap="large")
with col1:
    st.title("Find Your Favorite Movie References")
    st.markdown("**Send It To Your Friends Or Even Your Mom!**")
with col2:
    search_query = st.text_input("🔍 Search titles", "", placeholder="Type a movie quote…")

# ----------------------------------------------------------------------
# Load data
# ----------------------------------------------------------------------
API_URL = "http://localhost:8002"
all_videos = fetch_videos(f"{API_URL}/videos")

# Apply search filter
filtered_videos = filter_by_title(all_videos, search_query)

# ----------------------------------------------------------------------
# Section helpers
# ----------------------------------------------------------------------
def get_popular(videos: List[Dict], n: int = 12) -> List[Dict]:
    return sort_by_views(videos)[:n]

def get_featured(videos: List[Dict], n: int = 12) -> List[Dict]:
    return random_subset(videos, n)

def get_all(videos: List[Dict]) -> List[Dict]:
    return videos

# ----------------------------------------------------------------------
# Render section using Streamlit columns (4 per row) with pagination
# ----------------------------------------------------------------------
def render_section(title: str, videos: List[Dict], videos_per_page: int = 12) -> None:
    if not videos:
        st.info(f"No videos to show for **{title}**.")
        return

    st.subheader(title)
    
    # Create unique key for this section's pagination
    section_key = title.lower().replace(" ", "_")
    
    # Calculate total pages
    total_pages = (len(videos) + videos_per_page - 1) // videos_per_page
    
    # Initialize session state for this section if not exists
    if f"page_{section_key}" not in st.session_state:
        st.session_state[f"page_{section_key}"] = 0
    
    # Get current page
    current_page = st.session_state[f"page_{section_key}"]
    
    # Calculate start and end indices
    start_idx = current_page * videos_per_page
    end_idx = min(start_idx + videos_per_page, len(videos))
    current_videos = videos[start_idx:end_idx]

    for i in range(0, len(current_videos), 4):
        cols = st.columns(4)
        for j, col in enumerate(cols):
            if i + j < len(current_videos):
                video = current_videos[i + j]
                with col:
                    # Display poster image as a link to watch page
                    video_id = video.get("id", "")
                    watch_url = f"/watch?v={video_id}"
                    st.markdown(
                        f'<a href="{watch_url}">'
                        f'<img src="{video.get("poster", "")}" style="width:100%; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.15); cursor: pointer;" alt="{video.get("title", "")}"/>'
                        f'</a>',
                        unsafe_allow_html=True
                    )
                    # Title, script, and views
                    st.markdown(f"**{video.get('title', 'Untitled')}**")
                    script = video.get('script', '')
                    if script:
                        display_script = script if len(script) <= 60 else script[:57] + "..."
                        st.caption(f"_{display_script}_")
                    st.caption(f"{video.get('views', 0):,} views")

    
    # Display videos in rows of 4
    
    # for i in range(0, len(current_videos), 4):
    #     cols = st.columns(4)
    #     for j, col in enumerate(cols):
    #         if i + j < len(current_videos):
    #             video = current_videos[i + j]
    #             with col:
    #                 # Display poster image as a link
    #                 st.markdown(
    #                     f'<a href="{video.get("url", "#")}" target="_blank">'
    #                     f'<img src="{video.get("poster", "")}" style="width:100%; border-radius: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.15);" alt="{video.get("title", "")}"/>'
    #                     f'</a>',
    #                     unsafe_allow_html=True
    #                 )
    #                 # Title and views
    #                 st.markdown(f"**{video.get('title', 'Untitled')}**")
    #                 st.caption(f"{video.get('views', 0):,} views")
    
    # Pagination controls
    if total_pages > 1:
        col1, col2, col3 = st.columns([1, 2, 1])
        
        with col1:
            if st.button("← Previous", key=f"prev_{section_key}", disabled=current_page == 0):
                st.session_state[f"page_{section_key}"] = current_page - 1
                st.rerun()
        
        with col2:
            st.markdown(f"<center>Page {current_page + 1} of {total_pages}</center>", unsafe_allow_html=True)
        
        with col3:
            if st.button("Next →", key=f"next_{section_key}", disabled=current_page >= total_pages - 1):
                st.session_state[f"page_{section_key}"] = current_page + 1
                st.rerun()
    
    st.markdown("")  # Add spacing between sections

# ----------------------------------------------------------------------
# Build the three sections
# ----------------------------------------------------------------------
if filtered_videos:
    render_section("POPULAR", get_popular(filtered_videos))
    render_section("EVERCHANGING FEATURED", get_featured(filtered_videos))
    render_section("MOVIE TITLE", get_all(filtered_videos))
else:
    st.warning("No videos found. Make sure your API is running at http://localhost:8002/videos")

# ----------------------------------------------------------------------
# Footer
# ----------------------------------------------------------------------
st.markdown("---")
st.caption("© 2025 QuipVid – All movie quotes are used under fair‑use policy.")