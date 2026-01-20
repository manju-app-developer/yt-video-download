import streamlit as st
import yt_dlp
import os
import time
import shutil

# --- Config & Mobile Layout ---
st.set_page_config(page_title="YT Downloader", page_icon="⬇️", layout="centered")

# CSS to hide default Streamlit branding for a cleaner "App" feel
hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

# --- Setup Directories ---
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

st.title("⬇️ Mobile YT Downloader")

# --- input ---
url = st.text_input("", placeholder="Paste Link (Video/Shorts)")

# --- Mobile Friendly Controls ---
# We use columns to put buttons side-by-side on mobile
col1, col2 = st.columns(2)
with col1:
    fmt = st.radio("Format", ["Video (MP4)", "Audio (MP3)"], label_visibility="collapsed")
with col2:
    if fmt == "Video (MP4)":
        qual = st.selectbox("Quality", ["Best", "1080p", "720p"], label_visibility="collapsed")
    else:
        st.write("🎵 MP3 Audio")

# --- Logic ---
def get_cookies_path():
    # 1. Look for pre-loaded cookies (Best for Mobile Users)
    if os.path.exists("cookies.txt"):
        return "cookies.txt"
    # 2. Look for secrets (Advanced Streamlit Cloud method)
    #    You can store cookies content in st.secrets and write to file here
    return None

def download(link, format_type, quality_setting):
    timestamp = int(time.time())
    cookies = get_cookies_path()
    
    opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s_{timestamp}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        # Mobile User Agent to blend in
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
    }

    if cookies:
        opts['cookiefile'] = cookies

    if format_type == "Audio (MP3)":
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3'}]
    else:
        # Simplified quality logic for mobile stability
        if quality_setting == "1080p":
            opts['format'] = 'bestvideo[height<=1080]+bestaudio/best'
        elif quality_setting == "720p":
            opts['format'] = 'bestvideo[height<=720]+bestaudio/best'
        else:
            opts['format'] = 'bestvideo+bestaudio/best'
        opts['merge_output_format'] = 'mp4'

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(link, download=True)
            fname = ydl.prepare_filename(info)
            base, _ = os.path.splitext(fname)
            final = base + (".mp3" if format_type == "Audio (MP3)" else ".mp4")
            return final, info.get('title', 'Media')
    except Exception as e:
        return None, str(e)

# --- Button ---
# "use_container_width=True" makes the button full width on mobile
if st.button("Download Now", use_container_width=True):
    if not url:
        st.toast("⚠️ Paste a link first!")
    else:
        with st.status("Downloading...", expanded=True) as status:
            st.write("☁️ Connecting to server...")
            path, result = download(url, fmt, qual if fmt == "Video (MP4)" else None)
            
            if path and os.path.exists(path):
                status.update(label="✅ Ready!", state="complete", expanded=False)
                
                with open(path, "rb") as f:
                    st.download_button(
                        label="💾 Save to Device",
                        data=f,
                        file_name=os.path.basename(path),
                        mime="audio/mpeg" if fmt == "Audio (MP3)" else "video/mp4",
                        use_container_width=True
                    )
            else:
                status.update(label="❌ Failed", state="error")
                st.error(f"Error: {result}")
                if "403" in str(result) or "Sign in" in str(result):
                    st.error("Server cookies expired. Please update 'cookies.txt' in the repo.")
