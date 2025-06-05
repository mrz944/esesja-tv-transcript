import re
import time
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from datetime import datetime
from dateutil import parser as date_parser

from utils import Config, Logger

class VideoInfo:
    """Data class for video information."""
    
    def __init__(self, title: str, url: str, thumbnail: str = "", 
                 publisher: str = "", date: str = "", views: int = 0):
        self.title = title.strip()
        self.url = url
        self.thumbnail = thumbnail
        self.publisher = publisher.strip()
        self.date = date
        self.views = views
        self.id = self._extract_id_from_url(url)
    
    def _extract_id_from_url(self, url: str) -> str:
        """Extract video ID from URL."""
        # Extract ID from URL like /transmisja/67352/...
        match = re.search(r'/transmisja/(\d+)/', url)
        return match.group(1) if match else ""
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'id': self.id,
            'title': self.title,
            'url': self.url,
            'thumbnail': self.thumbnail,
            'publisher': self.publisher,
            'date': self.date,
            'views': self.views
        }
    
    def __str__(self) -> str:
        return f"[{self.date}] {self.title} - {self.views} views"

class EsesjatvScraper:
    """Web scraper for esesja.tv video pages."""
    
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': config.get('scraping.user_agent'),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'pl-PL,pl;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def get_video_list(self) -> List[VideoInfo]:
        """Scrape the main page and extract all video information."""
        base_url = self.config.get('scraping.base_url')
        self.logger.info(f"Fetching video list from: {base_url}")
        
        try:
            response = self._make_request(base_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Find all video containers
            video_containers = soup.find_all('div', class_='transmisja')
            self.logger.info(f"Found {len(video_containers)} video containers")
            
            videos = []
            for container in video_containers:
                try:
                    video_info = self._parse_video_container(container, base_url)
                    if video_info:
                        videos.append(video_info)
                        self.logger.debug(f"Parsed video: {video_info.title}")
                except Exception as e:
                    self.logger.warning(f"Failed to parse video container: {e}")
                    continue
            
            self.logger.success(f"Successfully extracted {len(videos)} videos")
            return videos
            
        except Exception as e:
            self.logger.error(f"Failed to fetch video list: {e}")
            raise
    
    def _parse_video_container(self, container, base_url: str) -> Optional[VideoInfo]:
        """Parse individual video container and extract information."""
        try:
            # Extract link and thumbnail
            link_elem = container.find('a')
            if not link_elem:
                return None
            
            video_url = urljoin(base_url, link_elem.get('href', ''))
            
            # Extract thumbnail
            img_div = container.find('div', class_='img')
            thumbnail = ""
            if img_div:
                style = img_div.get('style', '')
                thumbnail_match = re.search(r'url\(["\']?([^"\']+)["\']?\)', style)
                if thumbnail_match:
                    thumbnail = thumbnail_match.group(1)
            
            # Extract title
            title_elem = container.find('div', class_='title')
            title = ""
            if title_elem:
                title_link = title_elem.find('a')
                if title_link:
                    title = title_link.get_text(strip=True)
            
            # Extract publisher information
            publisher_elem = container.find('div', class_='publisher')
            publisher = ""
            date_str = ""
            views = 0
            
            if publisher_elem:
                # Publisher name
                publisher_link = publisher_elem.find('a')
                if publisher_link:
                    publisher = publisher_link.get_text(strip=True)
                
                # Time and views information
                time_elem = publisher_elem.find('div', class_='time')
                if time_elem:
                    time_text = time_elem.get_text()
                    
                    # Extract date
                    date_match = re.search(r'(\d{1,2}\s+\w+\s+\d{4})', time_text)
                    if date_match:
                        date_str = self._parse_polish_date(date_match.group(1))
                    
                    # Extract views
                    views_match = re.search(r'(\d+)', time_text.split('views')[0] if 'views' in time_text else time_text)
                    if views_match:
                        try:
                            views = int(views_match.group(1))
                        except ValueError:
                            views = 0
            
            if not title or not video_url:
                return None
            
            return VideoInfo(
                title=title,
                url=video_url,
                thumbnail=thumbnail,
                publisher=publisher,
                date=date_str,
                views=views
            )
            
        except Exception as e:
            self.logger.debug(f"Error parsing video container: {e}")
            return None
    
    def _parse_polish_date(self, date_str: str) -> str:
        """Parse Polish date string to ISO format."""
        # Polish month names mapping
        polish_months = {
            'stycznia': 'January', 'lutego': 'February', 'marca': 'March',
            'kwietnia': 'April', 'maja': 'May', 'czerwca': 'June',
            'lipca': 'July', 'sierpnia': 'August', 'września': 'September',
            'października': 'October', 'listopada': 'November', 'grudnia': 'December'
        }
        
        try:
            # Replace Polish month names with English
            english_date = date_str.lower()
            for polish, english in polish_months.items():
                english_date = english_date.replace(polish, english)
            
            # Parse the date
            parsed_date = date_parser.parse(english_date, fuzzy=True)
            return parsed_date.strftime('%Y-%m-%d')
        except:
            return date_str
    
    def get_video_stream_url(self, video_page_url: str) -> Optional[str]:
        """Extract the video stream URL from a video page."""
        self.logger.info(f"Extracting stream URL from: {video_page_url}")
        
        try:
            response = self._make_request(video_page_url)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Look for the video element with videourl attribute
            video_div = soup.find('div', id='video')
            if video_div and video_div.get('videourl'):
                stream_url = video_div.get('videourl')
                self.logger.success(f"Found stream URL: {stream_url}")
                return stream_url
            
            # Alternative: look for video-js element
            video_js = soup.find('video-js')
            if video_js:
                video_elem = video_js.find('video')
                if video_elem and video_elem.get('src'):
                    stream_url = video_elem.get('src')
                    self.logger.success(f"Found stream URL in video element: {stream_url}")
                    return stream_url
            
            # Alternative: search in script tags for stream URLs
            script_tags = soup.find_all('script')
            for script in script_tags:
                if script.string:
                    # Look for m3u8 URLs in JavaScript
                    m3u8_match = re.search(r'["\']([^"\']*\.m3u8[^"\']*)["\']', script.string)
                    if m3u8_match:
                        stream_url = m3u8_match.group(1)
                        self.logger.success(f"Found stream URL in script: {stream_url}")
                        return stream_url
            
            self.logger.warning(f"No stream URL found on page: {video_page_url}")
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to extract stream URL from {video_page_url}: {e}")
            return None
    
    def _make_request(self, url: str) -> requests.Response:
        """Make HTTP request with error handling and rate limiting."""
        delay = self.config.get('scraping.delay_between_requests', 2)
        timeout = self.config.get('scraping.timeout', 30)
        
        # Rate limiting
        time.sleep(delay)
        
        try:
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed for {url}: {e}")
            raise
    
    def close(self):
        """Close the session."""
        self.session.close()
