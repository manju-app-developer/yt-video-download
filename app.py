import streamlit as st
import yt_dlp
import os
import time

# --- Page Configuration ---
st.set_page_config(page_title="Universal YT Downloader", page_icon="🎬")
st.title("🎬 Universal YT Downloader")
st.markdown("Supports **HD Video**, **Shorts**, and **Audio**.")

# --- Setup Directories ---
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- Sidebar: Cookie Uploader (CRITICAL for Cloud) ---
with st.sidebar:
    st.header("🔐 Authentication")
    st.info("If you get 'Forbidden' or 'Sign In' errors, upload your cookies.txt here.")
    uploaded_cookies = st.file_uploader("Upload cookies.txt", type=["txt"])
    
    cookie_path = None
    if uploaded_cookies:
        # Save cookies to a temp file
        cookie_path = os.path.join(DOWNLOAD_FOLDER, "cookies.txt")
        with open(cookie_path, "wb") as f:
            f.write(uploaded_cookies.getbuffer())
        st.success("✅ Cookies loaded")

# --- Helper Function: Progress Hook ---
def progress_hook(d):
    if d['status'] == 'downloading':
        try:
            # print progress to console (optional logging)
            pass 
        except:
            pass

# --- Main Download Logic ---
def download_media(url, format_choice, cookies_file=None):
    timestamp = int(time.time())
    
    # 1. Base Configuration
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s_{timestamp}.%(ext)s',
        'progress_hooks': [progress_hook],
        'quiet': True,
        'no_warnings': True,
        # Spoof a generic browser to avoid basic bot detection
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    # 2. Add Cookies if provided
    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file

    # 3. Format Selection (Error-Proof Logic)
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
        # VIDEO MODE
        # The magic string: "bestvideo+bestaudio/best"
        # This tells it: "Download the best video stream AND best audio stream and merge them."
        # " /best" means "If that fails, just download the single best file available."
        ydl_opts.update({
            'format': 'bestvideo+bestaudio/best', 
            'merge_output_format': 'mp4',  # Ensures final file is MP4
        })

    # 4. Execution
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            
            # 5. Fix Filename Extension Logic
            # yt-dlp might return .webm, but we asked for mp3 or mp4 conversion.
            base, ext = os.path.splitext(filename)
            
            if format_choice == "Audio (MP3)":
                final_filename = base + ".mp3"
            else:
                final_filename = base + ".mp4"
            
            return final_filename, info.get('title', 'Media')

    except Exception as e:
        return None, str(e)

# --- User Interface ---
url = st.text_input("Paste URL:", placeholder="https://youtube.com/...")
format_select = st.selectbox("Select Format", ["Video (Highest Quality)", "Audio (MP3)"])

if st.button("Download", type="primary"):
    if not url:
        st.warning("Please enter a URL first.")
    else:
        with st.spinner("Processing... (This may take a moment for HD)"):
            # Pass the cookie path (if uploaded) to the downloader
            path, result = download_media(url, format_select, cookie_path)
            
            if path and os.path.exists(path):
                st.success("Download Complete!")
                
                # Create the download button
                with open(path, "rb") as f:
                    file_name = os.path.basename(path)
                    mime_type = "audio/mpeg" if format_select == "Audio (MP3)" else "video/mp4"
                    
                    st.download_button(
                        label="📥 Click to Save File",
                        data=f,
                        file_name=file_name,
                        mime=mime_type
                    )
            else:
                st.error("❌ An error occurred.")
                st.code(result) # Show the exact error message
                
                if result and ("403" in result or "Sign in" in result):
                    st.warning("⚠️ **Fix:** This is a YouTube restriction. Please upload your `cookies.txt` in the sidebar.")
