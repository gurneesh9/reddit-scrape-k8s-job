#!/usr/bin/env python3

import os
import re
import sys
import requests
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from dataclasses import dataclass
from datetime import datetime

import yt_dlp  # Updated from youtube_dl, which is deprecated
from requests import Session

class TorSessionManager:
    @staticmethod
    def get_tor_session() -> Session:
        """Create a requests session routed through Tor."""
        try:
            session = requests.Session()
            session.proxies = {
                'http': 'socks5h://127.0.0.1:9050',
                'https': 'socks5h://127.0.0.1:9050'
            }
            print(f"[{datetime.now()}] Tor session initialized successfully")
            return session
        except Exception as e:
            print(f"[{datetime.now()}] Failed to create Tor session: {e}")
            raise

@dataclass
class MediaDownloadConfig:
    """Configuration for different media download strategies."""
    extensions: List[str] = None
    domains: List[str] = None
    download_method: str = 'direct'  # 'direct' or 'yt_dlp'

class RedditDownloader:
    def __init__(self, subreddit: str, use_tor: bool = False):
        self.subreddit = subreddit
        self.base_url = f'https://www.reddit.com/r/{subreddit}.json'
        
        # Setup session
        try:
            self.session = TorSessionManager.get_tor_session() if use_tor else requests.Session()
            print(f"[{datetime.now()}] Session initialized {'with Tor' if use_tor else 'without Tor'}")
        except Exception as e:
            print(f"[{datetime.now()}] Failed to create session: {e}")
            self.session = requests.Session()
        
        # Predefined media download configurations
        self.media_configs = [
            MediaDownloadConfig(
                extensions=['.jpg', 'jpeg', '.png', '.gif', '.mp4', '.webm'], 
                download_method='direct'
            ),
            MediaDownloadConfig(
                domains=['gfycat.com', 'v.redd.it', 'youtube.com', 'youtu.be'], 
                download_method='yt_dlp'
            )
        ]

    def fetch_subreddit_data(self, after: Optional[str] = None) -> Dict[str, Any]:
        """Fetch JSON data for the subreddit with optional pagination."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        params = {'after': f't3_{after}'} if after else {}

        try:
            print(f"[{datetime.now()}] Fetching subreddit data{' after ' + after if after else ''}")
            response = self.session.get(
                self.base_url, 
                headers=headers, 
                params=params
            )
            response.raise_for_status()
            post_count = len(response.json().get('data', {}).get('children', []))
            print(f"[{datetime.now()}] Successfully fetched {post_count} posts")
            return response.json()
        except requests.RequestException as e:
            print(f"[{datetime.now()}] Error fetching subreddit data: {e}")
            return {}

    def download_media(self, url: str, download_path: str) -> bool:
        """Download media with various strategies based on URL."""
        parsed_url = urlparse(url)

        # Determine download strategy
        for config in self.media_configs:
            match = (
                (config.extensions and any(url.endswith(ext) for ext in config.extensions)) or
                (config.domains and any(domain in parsed_url.netloc for domain in config.domains))
            )
            
            if match:
                match config.download_method:
                    case 'direct':
                        return self._download_direct(url, download_path)
                    case 'yt_dlp':
                        return self._download_yt_dlp(url, os.path.dirname(download_path))
        
        print(f"[{datetime.now()}] No download method found for {url}")
        return False

    def _download_direct(self, url: str, filepath: str) -> bool:
        """Download media directly via requests."""
        try:
            print(f"[{datetime.now()}] Downloading direct: {url}")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            with open(filepath, 'wb') as file:
                for chunk in response.iter_content(chunk_size=8192):
                    file.write(chunk)
            print(f"[{datetime.now()}] Successfully downloaded: {filepath}")
            return True
        except Exception as e:
            print(f"[{datetime.now()}] Direct download failed for {url}: {e}")
            return False

    def _download_yt_dlp(self, url: str, download_dir: str) -> bool:
        """Download media using yt-dlp."""
        ydl_opts = {
            'outtmpl': os.path.join(download_dir, '%(id)s.%(ext)s'),
            'no_warnings': True,
            'quiet': False
        }
        
        try:
            print(f"[{datetime.now()}] Downloading via YT-DLP: {url}")
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            print(f"[{datetime.now()}] Successfully downloaded: {url}")
            return True
        except Exception as e:
            print(f"[{datetime.now()}] YT-DLP download failed for {url}: {e}")
            return False

    def scrape_subreddit(
        self, 
        output_dir: Optional[str] = None, 
        flair: Optional[str] = None
    ) -> None:
        """Comprehensive subreddit media scraping method."""
        output_dir = output_dir or os.path.join(os.getcwd(), self.subreddit)
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"[{datetime.now()}] Starting scrape of r/{self.subreddit}")
        print(f"[{datetime.now()}] Output directory: {output_dir}")
        if flair:
            print(f"[{datetime.now()}] Filtering posts with flair: {flair}")

        total_downloaded = 0
        after_id = None
        
        try:
            while True:
                data = self.fetch_subreddit_data(after_id)
                if not data or 'data' not in data:
                    print(f"[{datetime.now()}] No more data to fetch")
                    break

                posts = [post['data'] for post in data['data']['children']]
                if not posts:
                    print(f"[{datetime.now()}] No posts in current batch")
                    break

                batch_downloads = 0
                for post in posts:
                    try:
                        url = post.get('url')
                        if url and (not flair or post.get('link_flair_text') == flair):
                            filename = f"{post['id']}_{os.path.basename(urlparse(url).path)}"
                            filepath = os.path.join(output_dir, filename)
                            
                            if self.download_media(url, filepath):
                                batch_downloads += 1
                    except Exception as e:
                        print(f"[{datetime.now()}] Error processing post: {e}")

                total_downloaded += batch_downloads
                print(f"[{datetime.now()}] Downloaded {batch_downloads} files in this batch")

                after_id = posts[-1].get('id')
                if not after_id:
                    break

        except Exception as e:
            print(f"[{datetime.now()}] Unexpected error during scraping: {e}")
        finally:
            print(f"[{datetime.now()}] Scraping complete. Total files downloaded: {total_downloaded}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Reddit Media Downloader')
    parser.add_argument('subreddit', help='Subreddit to scrape')
    parser.add_argument('--flair', help='Optional flair to filter posts')
    parser.add_argument('--tor', action='store_true', help='Use Tor for requests')
    args = parser.parse_args()

    downloader = RedditDownloader(args.subreddit, use_tor=args.tor)
    downloader.scrape_subreddit(flair=args.flair)

if __name__ == '__main__':
    main()
