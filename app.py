import streamlit as st
import yt_dlp
import os
import time

st.set_page_config(page_title="Universal YT Downloader", page_icon="🎬")
st.title("🎬 Universal YT Downloader")

# --- Constants ---
DOWNLOAD_FOLDER = "downloads"
COOKIES_FILE = "cookies.txt" 

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- Debug Info ---
if os.path.exists(COOKIES_FILE):
    st.success("✅ Cookies loaded. Authenticated.")
else:
    st.warning("⚠️ No cookies.txt found. YouTube might block the download.")

def download_media(url, format_mode):
    timestamp = int(time.time())
    
    # Common options
    base_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s_{timestamp}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        # We REMOVED the 'extractor_args' (client spoofing) because 
        # it was causing the "Format Not Available" error on Shorts.
        # We rely purely on cookies now.
    }

    if os.path.exists(COOKIES_FILE):
        base_opts['cookiefile'] = COOKIES_FILE

    # --- ATTEMPT 1: HIGH QUALITY (HD/Merge) ---
    try:
        st.info("Attempting High Quality Download...")
        
        if format_mode == "Audio":
            # Audio is simple, usually doesn't fail
            opts = base_opts.copy()
            opts.update({
                'format': 'bestaudio/best',
                'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
            })
        else:
            # Video: Try HD Merge first
            opts = base_opts.copy()
            opts.update({
                'format': 'bestvideo+bestaudio', # Try to get 1080p+
                'merge_output_format': 'mp4',
            })

        # Run Download
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fname = ydl.prepare_filename(info)
            return get_final_filename(fname, format_mode, timestamp), info.get('title')

    except Exception as e:
        # --- ATTEMPT 2: STANDARD QUALITY (Fallback) ---
        # If Attempt 1 failed with "Format Not Available", we catch it here.
        st.warning(f"HD failed ({str(e)}). Switching to Standard Mode...")
        
        if format_mode == "Video":
            try:
                opts = base_opts.copy()
                opts.update({
                    'format': 'best', # Just get the single best file (Safest)
                    # Do NOT force merge_output_format here, let it be what it is
                })
                
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    fname = ydl.prepare_filename(info)
                    return get_final_filename(fname, format_mode, timestamp), info.get('title')
            except Exception as e2:
                return None, f"All attempts failed. {str(e2)}"
        
        return None, str(e)

def get_final_filename(original_fname, mode, timestamp):
    """Helper to find the file after FFmpeg might have renamed it"""
    base, ext = os.path.splitext(original_fname)
    
    # Expected final extension
    expected_ext = ".mp3" if mode == "Audio" else ".mp4"
    final_name = base + expected_ext

    # 1. Check if the expected file exists
    if os.path.exists(final_name):
        return final_name
    
    # 2. Check if the original file exists (e.g. if fallback downloaded .webm)
    if os.path.exists(original_fname):
        return original_fname
        
    # 3. Last resort: Look for any file with our timestamp
    # This handles cases where yt-dlp renames things unexpectedly
    for f in os.listdir(DOWNLOAD_FOLDER):
        if str(timestamp) in f:
            return os.path.join(DOWNLOAD_FOLDER, f)
            
    return None

# --- UI ---
url = st.text_input("Paste URL:", placeholder="https://youtube.com/...")
fmt = st.selectbox("Format", ["Video", "Audio"])

if st.button("Download"):
    if url:
        with st.spinner("Processing..."):
            path, title = download_media(url, fmt)
            
            if path and os.path.exists(path):
                st.success("Success!")
                st.caption(f"File: {os.path.basename(path)}")
                
                with open(path, "rb") as f:
                    st.download_button("📥 Save File", f, file_name=os.path.basename(path))
            else:
                st.error("❌ Download Failed")
                st.write(title) # Prints error message
