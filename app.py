import streamlit as st
import yt_dlp
import os
import time

st.set_page_config(page_title="Universal YT Downloader", page_icon="🎬")
st.title("🎬 Universal YT Downloader")

# --- Debug: Check for Cookies ---
if os.path.exists("cookies.txt"):
    st.success("✅ Cookies.txt found and loaded.")
else:
    st.warning("⚠️ No cookies.txt found. 403 Errors are possible on Cloud.")

DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

def download_media(url, format_choice):
    timestamp = int(time.time())
    
    # --- CONFIGURATION TO FIX 403 & FORMAT ERRORS ---
    ydl_opts = {
        'outtmpl': f'{DOWNLOAD_FOLDER}/%(title)s_{timestamp}.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        # Fix 1: Use iOS Client (Better for MP4s than Android)
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'web_creator'],
            }
        }
    }

    # Load Cookies
    if os.path.exists("cookies.txt"):
        ydl_opts['cookiefile'] = "cookies.txt"

    # --- FORMAT LOGIC ---
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
        # Fix 2: The "Magic" Format String for Shorts/Videos
        # "bv*+ba/b" means: Try best video + best audio. 
        # If that fails (Format Not Available), just give me the single best file (b).
        ydl_opts.update({
            'format': 'bv*+ba/b',
            'merge_output_format': 'mp4' 
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            fname = ydl.prepare_filename(info)
            base, ext = os.path.splitext(fname)
            
            final_name = base + (".mp3" if format_choice == "Audio (MP3)" else ".mp4")
            
            # Post-download check: sometimes the file stays as .webm or .mkv if merge failed
            # We look for ANY file that starts with the base name
            if not os.path.exists(final_name):
                 dir_files = os.listdir(DOWNLOAD_FOLDER)
                 for f in dir_files:
                     if base in os.path.join(DOWNLOAD_FOLDER, f) or str(timestamp) in f:
                         final_name = os.path.join(DOWNLOAD_FOLDER, f)
                         break
            
            return final_name, info.get('title', 'Media')

    except Exception as e:
        return None, str(e)

# --- UI ---
url = st.text_input("Paste URL:", placeholder="https://youtube.com/...")
fmt = st.selectbox("Format", ["Video", "Audio (MP3)"])

if st.button("Download"):
    if url:
        with st.spinner("Processing..."):
            path, result = download_media(url, fmt)
            
            if path and os.path.exists(path):
                st.success("Done!")
                with open(path, "rb") as f:
                    st.download_button("📥 Save File", f, file_name=os.path.basename(path))
            else:
                st.error("Error:")
                st.code(result)
