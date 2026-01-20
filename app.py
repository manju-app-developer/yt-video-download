import streamlit as st
import yt_dlp
import os
import time

# --- Page Setup ---
st.set_page_config(page_title="Universal YT Downloader", page_icon="🎬")
st.title("🎬 Universal YT Downloader")
st.markdown("Automated for **HD Video (MP4)**, **Shorts**, and **Audio (MP3)**.")

# --- Constants ---
DOWNLOAD_FOLDER = "downloads"
COOKIES_FILE = "cookies.txt"  # Looks for this file in the same folder

# Create download folder if it doesn't exist
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# --- Download Logic ---
def download_media(url, format_choice):
    # Unique timestamp to prevent filename conflicts
    timestamp = int(time.time())
    
    # Base Options
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s_{timestamp}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        # Spoof User Agent to look like a standard Windows Chrome browser
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    }

    # 1. Automatic Cookie Detection
    # Since you uploaded cookies.txt with the code, we just check if it's there.
    if os.path.exists(COOKIES_FILE):
        ydl_opts['cookiefile'] = COOKIES_FILE
    else:
        st.warning("⚠️ 'cookies.txt' not found in folder. YouTube may block this download.")

    # 2. Format Selection (The Fix for your Error)
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
        # 'bestvideo+bestaudio/best' is the "Safe" command.
        # It tries to merge HD streams first. If that fails (Error: format not available),
        # it falls back to '/best' which downloads the single best file available (works on Shorts).
        ydl_opts.update({
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4', # Forces the final container to be MP4
        })

    # 3. Execution
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get Video Info
            info = ydl.extract_info(url, download=True)
            
            # Get the filename yt-dlp created
            temp_filename = ydl.prepare_filename(info)
            
            # 4. Handle Final Filename Extension
            # yt-dlp might generate .webm or .mkv initially. 
            # We need to find the final file that FFmpeg converted.
            base, _ = os.path.splitext(temp_filename)
            
            if format_choice == "Audio (MP3)":
                final_filename = base + ".mp3"
            else:
                final_filename = base + ".mp4"
            
            # Double check: If the merged file works, it's there.
            # If fallback happened, it might still be the original extension (unlikely with merge_output_format, but safe to check)
            if not os.path.exists(final_filename):
                # If exact mp4 not found, look for the file that DOES exist with that timestamp
                for f in os.listdir(DOWNLOAD_FOLDER):
                    if str(timestamp) in f:
                        final_filename = os.path.join(DOWNLOAD_FOLDER, f)
                        break

            return final_filename, info.get('title', 'Media')

    except Exception as e:
        return None, str(e)

# --- User Interface ---
url = st.text_input("Paste URL:", placeholder="https://youtube.com/...")
format_select = st.selectbox("Select Format", ["Video (Best Quality)", "Audio (MP3)"])

if st.button("Download Now", type="primary"):
    if not url:
        st.warning("Please paste a URL first.")
    else:
        with st.spinner("Processing... (HD videos take longer to merge)"):
            path, result = download_media(url, format_select)
            
            if path and os.path.exists(path):
                st.success("Download Complete!")
                
                # Extract filename for the button label
                file_name = os.path.basename(path)
                mime_type = "audio/mpeg" if format_select == "Audio (MP3)" else "video/mp4"
                
                with open(path, "rb") as f:
                    st.download_button(
                        label="📥 Save to Device",
                        data=f,
                        file_name=file_name,
                        mime=mime_type
                    )
            else:
                st.error("❌ Download Failed")
                st.code(result) # Display the error for debugging
