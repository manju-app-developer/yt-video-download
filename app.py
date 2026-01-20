import streamlit as st
import yt_dlp
import os
import time

# Create directories
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Cookie storage
COOKIE_FILE = "cookies.txt"

st.set_page_config(page_title="Pro YT Downloader", page_icon="🎬", layout="centered")

st.title("🎬 Pro YouTube Downloader")
st.markdown("Download **HD Video**, **Shorts**, or **Audio**. If downloads fail, upload your cookies in the sidebar.")

# --- Sidebar: Authentication (The Fix for 403/Forbidden) ---
with st.sidebar:
    st.header("⚙️ Advanced Settings")
    st.info("💡 Getting 'Forbidden' or '404' errors? Upload your cookies.txt file here.")
    
    uploaded_cookies = st.file_uploader("Upload cookies.txt", type=["txt"])
    
    cookie_path = None
    if uploaded_cookies is not None:
        # Save the uploaded cookie file temporarily
        with open(COOKIE_FILE, "wb") as f:
            f.write(uploaded_cookies.getbuffer())
        cookie_path = COOKIE_FILE
        st.success("✅ Cookies loaded! Retrying download should work now.")
    else:
        st.warning("⚠️ No cookies loaded. Cloud servers may get blocked by YouTube.")

# --- Main Interface ---
url = st.text_input("Paste URL (Video or Short):", placeholder="https://www.youtube.com/watch?v=...")

col1, col2 = st.columns(2)
with col1:
    download_type = st.selectbox("Format", ["Video (MP4)", "Audio (MP3)"])
with col2:
    if download_type == "Video (MP4)":
        quality = st.selectbox("Quality", ["Best Available", "1080p", "720p"])
    else:
        st.info("High Quality MP3 (192kbps)")

# --- Core Logic ---
progress_bar = st.progress(0)
status_text = st.empty()

def progress_hook(d):
    if d['status'] == 'downloading':
        try:
            p = d.get('_percent_str', '0%').replace('%', '')
            progress = float(p) / 100
            progress_bar.progress(progress)
            status_text.text(f"⏳ {d.get('_percent_str')} | {d.get('_speed_str')}")
        except:
            pass
    elif d['status'] == 'finished':
        progress_bar.progress(1.0)
        status_text.success("✅ Download complete! Processing...")

def download_video(url, type, quality, cookies=None):
    timestamp = int(time.time())
    
    # Advanced Options to Bypass Blocks
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s_{timestamp}.%(ext)s',
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        # Spoof a real browser user agent
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    # Attach cookies if uploaded
    if cookies:
        ydl_opts['cookiefile'] = cookies

    if type == "Audio (MP3)":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        })
    else:
        if quality == "1080p":
            format_str = 'bestvideo[height<=1080]+bestaudio/best[height<=1080]'
        elif quality == "720p":
            format_str = 'bestvideo[height<=720]+bestaudio/best[height<=720]'
        else:
            format_str = 'bestvideo+bestaudio/best'
        
        ydl_opts.update({'format': format_str, 'merge_output_format': 'mp4'})

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # Handle extension changes (webm -> mp3/mp4)
            base, _ = os.path.splitext(filename)
            final_ext = ".mp3" if type == "Audio (MP3)" else ".mp4"
            final_filename = base + final_ext
            
            return final_filename, info.get('title', 'media')

    except Exception as e:
        # Return the error to display to the user
        return None, str(e)

if st.button("🚀 Download"):
    if url:
        with st.spinner("Connecting to YouTube..."):
            # Check if cookies exist locally
            current_cookie = COOKIE_FILE if os.path.exists(COOKIE_FILE) else None
            
            file_path, result = download_video(url, download_type, quality if download_type == "Video (MP4)" else None, current_cookie)

        if file_path and os.path.exists(file_path):
            st.balloons()
            st.success(f"Ready: {result}")
            with open(file_path, "rb") as f:
                st.download_button("📥 Save File", f, file_name=os.path.basename(file_path))
        else:
            st.error("❌ Download Failed")
            st.error(f"Error Details: {result}")
            if "HTTP Error 403" in str(result) or "Sign in" in str(result):
                st.warning("👉 **Fix:** Please upload your `cookies.txt` in the sidebar to bypass this YouTube restriction.")
    else:
        st.warning("Please paste a link first.")
