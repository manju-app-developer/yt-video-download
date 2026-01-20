import streamlit as st
import yt_dlp
import os
import time

# --- Config ---
st.set_page_config(page_title="Universal YT Downloader", page_icon="🎬")
st.title("🎬 Universal YT Downloader")

# --- Debug Section (Helps you see if cookies are loaded) ---
COOKIES_FILE = "cookies.txt"
if os.path.exists(COOKIES_FILE):
    st.success(f"✅ Found 'cookies.txt' ({os.path.getsize(COOKIES_FILE)} bytes). using authentication.")
else:
    st.warning("⚠️ 'cookies.txt' NOT found in root folder. 403 Errors likely.")

# --- Constants ---
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def download_media(url, format_choice):
    timestamp = int(time.time())
    
    # --- ADVANCED OPTIONS (The Fix) ---
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s_{timestamp}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        # 1. Force IPv4 (Fixes some cloud network issues)
        'source_address': '0.0.0.0', 
        # 2. Use Android Client (Bypasses many Browser 403 blocks)
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'ios'],
            }
        }
    }

    # Add Cookies if file exists
    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE

    # --- Format Logic ---
    if format_choice == "Audio (MP3)":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        # VIDEO: Universal Fallback
        # 'best' is safer than 'bestvideo+bestaudio' when facing 403s
        # It grabs the best single pre-merged file available.
        ydl_opts.update({
            'format': 'best',
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            temp_filename = ydl.prepare_filename(info)
            
            # Extension Handling
            base, ext = os.path.splitext(temp_filename)
            final_filename = base + (".mp3" if format_choice == "Audio (MP3)" else ext)
            
            # Verify file existence
            if not os.path.exists(final_filename):
                 # Fallback search
                 for f in os.listdir(DOWNLOAD_FOLDER):
                    if str(timestamp) in f:
                        final_filename = os.path.join(DOWNLOAD_FOLDER, f)
                        break
            
            return final_filename, info.get('title', 'Media')

    except Exception as e:
        return None, str(e)

# --- UI ---
url = st.text_input("Paste URL:", placeholder="https://youtube.com/...")
fmt = st.selectbox("Format", ["Video (Best Safe)", "Audio (MP3)"])

if st.button("Download", type="primary"):
    if url:
        with st.spinner("Processing..."):
            path, result = download_media(url, fmt)
            
            if path and os.path.exists(path) and os.path.getsize(path) > 0:
                st.success("Success!")
                with open(path, "rb") as f:
                    st.download_button("📥 Save File", f, file_name=os.path.basename(path))
            else:
                st.error("❌ Download Failed")
                st.write(result)
