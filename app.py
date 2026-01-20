import streamlit as st
import yt_dlp
import os
import time
import shutil
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# ==========================================
# 0. CONFIG & SETUP
# ==========================================
st.set_page_config(page_title="SOLID YT Downloader", page_icon="🏗️")
st.title("🏗️ SOLID Architecture Downloader")

# Setup Folders
DOWNLOAD_FOLDER = "downloads"
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Define Cookie Path (Looks for file in the same folder as app.py)
COOKIES_FILE = "cookies.txt"

# ==========================================
# 1. INTERFACES (Strategy Pattern)
# ==========================================

class DownloadFormatStrategy(ABC):
    @abstractmethod
    def get_options(self, save_path: str, cookies_path: Optional[str] = None) -> Dict[str, Any]:
        pass

class IMediaDownloader(ABC):
    @abstractmethod
    def download(self, url: str) -> str:
        pass
    @abstractmethod
    def get_info(self, url: str) -> Dict[str, Any]:
        pass

# ==========================================
# 2. CONCRETE STRATEGIES
# ==========================================

class VideoFormatStrategy(DownloadFormatStrategy):
    def get_options(self, save_path: str, cookies_path: Optional[str] = None) -> Dict[str, Any]:
        timestamp = int(time.time())
        # We use absolute path to ensure yt-dlp finds the folder correctly
        abs_save_path = os.path.abspath(save_path)
        filename_tmpl = f'{abs_save_path}/%(title)s_{timestamp}.%(ext)s'
        
        opts = {
            'outtmpl': filename_tmpl,
            'quiet': True,
            'no_warnings': True,
            # FALLBACK STRATEGY: 
            # 1. Try "bestvideo+bestaudio" (HD). 
            # 2. If that fails (Shorts/Format Error), fall back to "/best" (Single File).
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
        }
        
        # Attach cookies if they exist
        if cookies_path and os.path.exists(cookies_path):
            opts['cookiefile'] = os.path.abspath(cookies_path)
            
        return opts

class AudioFormatStrategy(DownloadFormatStrategy):
    def get_options(self, save_path: str, cookies_path: Optional[str] = None) -> Dict[str, Any]:
        timestamp = int(time.time())
        abs_save_path = os.path.abspath(save_path)
        filename_tmpl = f'{abs_save_path}/%(title)s_{timestamp}.%(ext)s'
        
        opts = {
            'outtmpl': filename_tmpl,
            'quiet': True,
            'no_warnings': True,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        
        if cookies_path and os.path.exists(cookies_path):
            opts['cookiefile'] = os.path.abspath(cookies_path)
            
        return opts

# ==========================================
# 3. CORE LOGIC (Dependency Injection)
# ==========================================

class YouTubeDownloader(IMediaDownloader):
    def __init__(self, save_path: str, strategy: DownloadFormatStrategy):
        self._save_path = save_path
        self._strategy = strategy
        # Auto-detect cookies
        self._cookies_path = COOKIES_FILE if os.path.exists(COOKIES_FILE) else None

    def get_info(self, url: str) -> Dict[str, Any]:
        try:
            opts = self._strategy.get_options(self._save_path, self._cookies_path)
            with yt_dlp.YoutubeDL(opts) as ydl:
                # download=False just fetches metadata
                info = ydl.extract_info(url, download=False)
                return {
                    "Title": info.get('title'),
                    "Channel": info.get('uploader'),
                    "Duration": info.get('duration'),
                    "Thumbnail": info.get('thumbnail')
                }
        except Exception as e:
            return {"Error": str(e)}

    def download(self, url: str) -> str:
        opts = self._strategy.get_options(self._save_path, self._cookies_path)
        
        # Verify Node.js presence (Debug check for your specific error)
        if shutil.which("node") is None:
             print("WARNING: Node.js is NOT installed. YouTube extraction may fail.")

        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                temp_filename = ydl.prepare_filename(info)
                
                # Determine expected extension based on strategy
                base, _ = os.path.splitext(temp_filename)
                if isinstance(self._strategy, AudioFormatStrategy):
                    final_path = base + ".mp3"
                else:
                    final_path = base + ".mp4"

                # File finding logic (Robustness)
                if not os.path.exists(final_path):
                    # Fallback: Search folder for any file with this title/timestamp
                    # This handles cases where yt-dlp didn't merge or used a different ext
                    for f in os.listdir(self._save_path):
                        full_p = os.path.join(self._save_path, f)
                        if base in full_p or info['title'][:15] in f:
                             final_path = full_p
                             break
                
                return final_path
        except Exception as e:
            raise e

# ==========================================
# 4. UI LAYER (Streamlit)
# ==========================================

class StreamlitUI:
    def render(self):
        # Cookie Status Indicator
        if os.path.exists(COOKIES_FILE):
            st.success(f"✅ Authenticated (Found {COOKIES_FILE})")
        else:
            st.warning("⚠️ No 'cookies.txt' found. Upload it if downloads fail.")

        # Input
        url = st.text_input("Paste YouTube URL")
        choice = st.radio("Format", ["Video (MP4)", "Audio (MP3)"], horizontal=True)

        if st.button("Start Download", type="primary"):
            if not url:
                st.error("Please enter a URL")
                return

            try:
                # Factory: Select Strategy
                if "Audio" in choice:
                    strategy = AudioFormatStrategy()
                else:
                    strategy = VideoFormatStrategy()

                # Inject Strategy into Downloader
                downloader = YouTubeDownloader(DOWNLOAD_FOLDER, strategy)

                with st.spinner("Processing..."):
                    # 1. Get Info
                    info = downloader.get_info(url)
                    
                    if "Error" in info:
                        st.error("Could not fetch video info.")
                        st.code(info["Error"])
                        if "403" in info["Error"]:
                            st.info("💡 Tip: Try generating a fresh 'cookies.txt' file.")
                    else:
                        # 2. Show Info
                        col1, col2 = st.columns([1,3])
                        with col1:
                            if info.get("Thumbnail"):
                                st.image(info["Thumbnail"])
                        with col2:
                            st.subheader(info.get("Title", "Video"))
                            st.caption(f"Channel: {info.get('Channel')}")

                        # 3. Download
                        file_path = downloader.download(url)
                        
                        if file_path and os.path.exists(file_path):
                            st.success("Download Complete!")
                            with open(file_path, "rb") as f:
                                st.download_button(
                                    label="📥 Save File",
                                    data=f,
                                    file_name=os.path.basename(file_path),
                                    mime="audio/mpeg" if "Audio" in choice else "video/mp4"
                                )
                        else:
                            st.error("File not found after download.")

            except Exception as e:
                st.error(f"Download Failed: {str(e)}")
                # Specific help for the error you are seeing
                if "JavaScript" in str(e) or "runtime" in str(e):
                    st.warning("👉 Solution: Add 'nodejs' to your packages.txt file.")

if __name__ == "__main__":
    app = StreamlitUI()
    app.render()
