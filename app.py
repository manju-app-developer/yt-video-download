import streamlit as st
import yt_dlp
import os
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

# ==========================================
# 0. CONFIG & SETUP
# ==========================================
st.set_page_config(page_title="SOLID YT Downloader", page_icon="🏗️")
st.title("🏗️ SOLID Architecture Downloader")
st.markdown("Built using **Strategy** and **Dependency Injection** patterns.")

DOWNLOAD_FOLDER = "downloads"
COOKIES_FILE = "cookies.txt"

if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# ==========================================
# 1. INTERFACES & ABSTRACTIONS (ISP & DIP)
# ==========================================

class DownloadFormatStrategy(ABC):
    """
    Strategy Interface: Defines how to configure the download format.
    """
    @abstractmethod
    def get_options(self, save_path: str, cookies_path: Optional[str] = None) -> Dict[str, Any]:
        pass

class IMediaDownloader(ABC):
    """
    Interface for any media downloader.
    """
    @abstractmethod
    def download(self, url: str) -> str:
        pass

    @abstractmethod
    def get_info(self, url: str) -> Dict[str, Any]:
        pass

# ==========================================
# 2. CONCRETE STRATEGIES (OCP & SRP)
# ==========================================

class VideoFormatStrategy(DownloadFormatStrategy):
    """Configuration specifically for Video."""
    def get_options(self, save_path: str, cookies_path: Optional[str] = None) -> Dict[str, Any]:
        timestamp = int(time.time())
        filename_template = os.path.join(save_path, f'%(title)s_{timestamp}.%(ext)s')
        
        opts = {
            'outtmpl': filename_template,
            # Robust format selection: Try HD merge, fall back to best single file
            'format': 'bestvideo+bestaudio/best',
            'merge_output_format': 'mp4',
            'noplaylist': True,
            'quiet': True,
            # Anti-403 Measures
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        }
        if cookies_path and os.path.exists(cookies_path):
            opts['cookiefile'] = cookies_path
        return opts

class AudioFormatStrategy(DownloadFormatStrategy):
    """Configuration specifically for Audio Extraction."""
    def get_options(self, save_path: str, cookies_path: Optional[str] = None) -> Dict[str, Any]:
        timestamp = int(time.time())
        filename_template = os.path.join(save_path, f'%(title)s_{timestamp}.%(ext)s')
        
        opts = {
            'outtmpl': filename_template,
            'format': 'bestaudio/best',
            'noplaylist': True,
            'quiet': True,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        if cookies_path and os.path.exists(cookies_path):
            opts['cookiefile'] = cookies_path
        return opts

# ==========================================
# 3. CORE LOGIC (LSP & SRP)
# ==========================================

class YouTubeDownloader(IMediaDownloader):
    """
    Concrete implementation.
    """
    def __init__(self, save_path: str, strategy: DownloadFormatStrategy):
        self._save_path = save_path
        self._strategy = strategy
        self._cookies_path = COOKIES_FILE if os.path.exists(COOKIES_FILE) else None

    def get_info(self, url: str) -> Dict[str, Any]:
        try:
            # We use the strategy options even for info to ensure cookies are used
            opts = self._strategy.get_options(self._save_path, self._cookies_path)
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return {
                    "Title": info.get('title'),
                    "Channel": info.get('uploader'),
                    "Duration": f"{info.get('duration')}s",
                    "Thumbnail": info.get('thumbnail')
                }
        except Exception as e:
            return {"Error": str(e)}

    def download(self, url: str) -> str:
        """Returns the path of the downloaded file."""
        ydl_opts = self._strategy.get_options(self._save_path, self._cookies_path)

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                temp_filename = ydl.prepare_filename(info)
                
                # Resolving the final filename (handling extensions)
                base, _ = os.path.splitext(temp_filename)
                
                # Check based on strategy type
                if isinstance(self._strategy, AudioFormatStrategy):
                    final_path = base + ".mp3"
                else:
                    final_path = base + ".mp4"

                # Fallback file finder (if ffmpeg merge changed name)
                if not os.path.exists(final_path):
                    # Look for file with same timestamp in folder
                    for f in os.listdir(self._save_path):
                        if info['title'][:10] in f: # partial match
                             final_path = os.path.join(self._save_path, f)
                             break
                
                return final_path
        except Exception as e:
            raise e

# ==========================================
# 4. STREAMLIT UI (The New Frontend)
# ==========================================

class StreamlitUI:
    """Handles all Streamlit Input/Output operations."""
    
    def render(self):
        # 1. Check for Cookies
        if os.path.exists(COOKIES_FILE):
            st.success("✅ Cookies loaded successfully.")
        else:
            st.warning("⚠️ cookies.txt not found. Upload it if downloads fail.")

        # 2. Input
        url = st.text_input("YouTube URL")
        type_choice = st.radio("Format", ["Video", "Audio"], horizontal=True)

        if st.button("Download", type="primary"):
            if not url:
                st.error("URL cannot be empty.")
                return

            try:
                # 3. Factory Logic / Strategy Selection
                if type_choice == "Audio":
                    strategy = AudioFormatStrategy()
                else:
                    strategy = VideoFormatStrategy()

                # 4. Dependency Injection
                downloader = YouTubeDownloader(save_path=DOWNLOAD_FOLDER, strategy=strategy)

                with st.spinner("Fetching Metadata..."):
                    info = downloader.get_info(url)
                    
                if "Error" in info:
                    st.error(f"Error fetching info: {info['Error']}")
                else:
                    # Display Metadata
                    col1, col2 = st.columns([1, 2])
                    with col1:
                        if "Thumbnail" in info:
                            st.image(info["Thumbnail"])
                    with col2:
                        st.subheader(info["Title"])
                        st.caption(f"Channel: {info['Channel']} | Duration: {info['Duration']}")

                    # Perform Download
                    with st.spinner("Downloading..."):
                        file_path = downloader.download(url)

                    if file_path and os.path.exists(file_path):
                        st.success("Download Complete!")
                        with open(file_path, "rb") as f:
                            st.download_button(
                                label="📥 Save File",
                                data=f,
                                file_name=os.path.basename(file_path),
                                mime="audio/mpeg" if type_choice == "Audio" else "video/mp4"
                            )
            except Exception as e:
                st.error(f"System Error: {str(e)}")

# ==========================================
# 5. MAIN ENTRY POINT
# ==========================================

if __name__ == "__main__":
    app = StreamlitUI()
    app.render()
