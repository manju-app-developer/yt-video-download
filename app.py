import streamlit as st
import yt_dlp
import os
import time

# Create a 'downloads' directory to store temporary files
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

st.set_page_config(page_title="Advanced YT Downloader", page_icon="🎬")

st.title("🎬 Advanced YouTube Downloader")
st.markdown("Download **HD Videos (MP4)** or extract **Audio (MP3)** seamlessly.")

# --- Session State for UI stability ---
if "url" not in st.session_state:
    st.session_state.url = ""

# --- Input Section ---
url = st.text_input("Paste YouTube URL here:", placeholder="https://www.youtube.com/watch?v=...")

# Options
col1, col2 = st.columns(2)
with col1:
    download_type = st.selectbox("Select Format", ["Video (MP4)", "Audio (MP3)"])
with col2:
    if download_type == "Video (MP4)":
        quality = st.selectbox("Max Resolution", ["Best Available (4K/8K)", "1080p", "720p", "480p"])
    else:
        st.info("Audio will be converted to high-quality MP3 (192kbps).")

# Progress Bar & Status Text container
progress_bar = st.progress(0)
status_text = st.empty()

# --- Helper Functions ---

def progress_hook(d):
    """
    Callback function to update the progress bar.
    yt-dlp calls this periodically during download.
    """
    if d['status'] == 'downloading':
        try:
            p = d.get('_percent_str', '0%').replace('%', '')
            progress = float(p) / 100
            progress_bar.progress(progress)
            status_text.text(f"Downloading: {d.get('_percent_str')} | Speed: {d.get('_speed_str')} | ETA: {d.get('_eta_str')}")
        except:
            pass
    elif d['status'] == 'finished':
        progress_bar.progress(1.0)
        status_text.success("Download Complete! Processing file...")

def download_video(url, download_type, quality=None):
    timestamp = int(time.time())
    
    # Base options
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s_{timestamp}.%(ext)s',
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
    }

    # Format selection logic
    if download_type == "Audio (MP3)":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else: # Video
        if quality == "Best Available (4K/8K)":
            # "bestvideo+bestaudio" ensures we get separate high-quality streams and merge them
            format_str = 'bestvideo+bestaudio/best'
        elif quality == "1080p":
            format_str = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
        elif quality == "720p":
            format_str = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
        else: # 480p
            format_str = 'bestvideo[height<=480]+bestaudio/best[height<=480]'
        
        ydl_opts.update({
            'format': format_str,
            'merge_output_format': 'mp4', # Forces output to be mp4 even if streams are webm
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            
            # Retrieve the filename
            # Note: prepare_filename doesn't always account for post-processing changes (like mp4 -> mp3)
            # So we check the directory for the file with the timestamp we added.
            filename = ydl.prepare_filename(info)
            
            if download_type == "Audio (MP3)":
                # prepare_filename returns .webm or .m4a, but we converted to .mp3
                base, _ = os.path.splitext(filename)
                final_filename = base + ".mp3"
            else:
                # prepare_filename might return .mkv or .webm, but we forced merge to mp4
                base, _ = os.path.splitext(filename)
                final_filename = base + ".mp4"
            
            return final_filename, info.get('title', 'video')

    except Exception as e:
        st.error(f"Error: {str(e)}")
        return None, None

# --- Main Execution ---
if st.button("Start Download"):
    if url:
        with st.spinner("Fetching video info..."):
            file_path, title = download_video(url, download_type, quality if download_type == "Video (MP4)" else None)

        if file_path and os.path.exists(file_path):
            # Display success and download button
            st.success(f"Processed: {title}")
            
            with open(file_path, "rb") as file:
                btn = st.download_button(
                    label="📥 Save to Computer",
                    data=file,
                    file_name=os.path.basename(file_path),
                    mime="audio/mpeg" if download_type == "Audio (MP3)" else "video/mp4"
                )
            
            # Optional: Clean up file after user has had a chance to download (Manual cleanup is safer in Streamlit)
            # os.remove(file_path) 
    else:
        st.warning("Please enter a valid URL.")
