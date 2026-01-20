import streamlit as st
import yt_dlp
import os
import time

# --- Config ---
st.set_page_config(page_title="Universal YT Downloader", page_icon="🎬", layout="centered")

# CSS to make it look like a mobile app
st.markdown("""
<style>
    .stButton>button {width: 100%; border-radius: 20px; height: 3em;}
    .stTextInput>div>div>input {border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

st.title("🎬 Universal Downloader")
st.caption("Works on Video, Shorts & Audio")

# --- Setup ---
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- Logic ---
def get_cookies():
    # Looks for cookies.txt in the same folder
    if os.path.exists("cookies.txt"):
        return "cookies.txt"
    return None

def download(url, type_fmt, quality):
    timestamp = int(time.time())
    cookies = get_cookies()
    
    # Base Options
    opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s_{timestamp}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36',
    }
    
    if cookies:
        opts['cookiefile'] = cookies

    # --- FORMAT LOGIC (The Fix) ---
    if type_fmt == "Audio (MP3)":
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    else:
        # VIDEO LOGIC
        if quality == "Safe Mode (No FFmpeg)":
            # This is the "Safety" option. It downloads a single pre-merged file (usually 720p max)
            # It NEVER requires FFmpeg and rarely fails.
            opts['format'] = 'best'
        else:
            # High Definition Logic
            # We use /best as a fallback if the merge fails
            if quality == "1080p":
                # We allow height up to 1920 to support HD Shorts (which are 1080x1920)
                opts['format'] = 'bestvideo[height<=1920]+bestaudio/best[height<=1920]/best'
            elif quality == "720p":
                opts['format'] = 'bestvideo[height<=1280]+bestaudio/best[height<=1280]/best'
            else:
                # Best Available
                opts['format'] = 'bestvideo+bestaudio/best'
            
            opts['merge_output_format'] = 'mp4'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fname = ydl.prepare_filename(info)
            
            # Handle filename extensions
            base, ext = os.path.splitext(fname)
            
            if type_fmt == "Audio (MP3)":
                final = base + ".mp3"
            elif quality == "Safe Mode (No FFmpeg)":
                final = fname # Keep original extension (often .mp4 or .webm)
            else:
                final = base + ".mp4"
            
            # Check if file actually exists (sometimes yt-dlp naming varies)
            if not os.path.exists(final):
                # Fallback: try finding the file that DOES exist with that base name
                possible_files = [f for f in os.listdir(DOWNLOAD_FOLDER) if f.startswith(info['title'][:10])]
                if possible_files:
                    final = os.path.join(DOWNLOAD_FOLDER, possible_files[0])

            return final, info.get('title', 'Media')

    except Exception as e:
        return None, str(e)

# --- UI ---
url_input = st.text_input("Paste Link:")

# Settings
col1, col2 = st.columns(2)
with col1:
    fmt = st.selectbox("Format", ["Video", "Audio (MP3)"])
with col2:
    if fmt == "Video":
        # Added "Safe Mode" for when HD fails
        qual = st.selectbox("Quality", ["Best Available", "1080p", "720p", "Safe Mode (No FFmpeg)"])
    else:
        st.write("🎵 MP3")

if st.button("🚀 Download"):
    if not url_input:
        st.warning("Please paste a link.")
    else:
        with st.spinner("Processing..."):
            path, result = download(url_input, fmt, qual if fmt == "Video" else None)
            
            if path and os.path.exists(path):
                st.success("Success!")
                with open(path, "rb") as f:
                    st.download_button(
                        "📥 Save File", 
                        f, 
                        file_name=os.path.basename(path),
                        mime="video/mp4" if fmt == "Video" else "audio/mpeg"
                    )
            else:
                st.error("Error detected.")
                st.code(result)
                st.info("💡 Try switching Quality to **'Safe Mode (No FFmpeg)'** if this keeps happening.")
