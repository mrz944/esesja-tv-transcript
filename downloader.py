import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import yt_dlp
from tqdm import tqdm

from utils import Config, Logger, sanitize_filename, format_file_size
from scraper import VideoInfo

class VideoDownloader:
    """Download videos from m3u8 streams using yt-dlp."""
    
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        self.videos_dir = Path(config.get('storage.videos_dir'))
        self.videos_dir.mkdir(parents=True, exist_ok=True)
    
    def download_video(self, video_info: VideoInfo, stream_url: str) -> Optional[str]:
        """Download video from stream URL and return the local file path."""
        if not stream_url:
            self.logger.error(f"No stream URL provided for video: {video_info.title}")
            return None
        
        # Create safe filename
        safe_title = sanitize_filename(video_info.title)
        filename = f"{video_info.id}_{safe_title}.mp4"
        output_path = self.videos_dir / filename
        
        # Skip if file already exists
        if output_path.exists():
            self.logger.info(f"Video already exists: {output_path}")
            return str(output_path)
        
        self.logger.info(f"Downloading video: {video_info.title}")
        self.logger.info(f"Stream URL: {stream_url}")
        self.logger.info(f"Output path: {output_path}")
        
        # Configure yt-dlp options
        ydl_opts = {
            'outtmpl': str(output_path),
            'format': self._get_format_selector(),
            'writesubtitles': False,
            'writeautomaticsub': False,
            'ignoreerrors': False,
            'no_warnings': False,
            'extractaudio': False,
            'audioformat': 'mp3',
            'embed_subs': False,
            'writeinfojson': False,
            'writethumbnail': False,
            'socket_timeout': self.config.get('video.download_timeout', 3600),
            'retries': self.config.get('video.max_retries', 3),
            'fragment_retries': self.config.get('video.max_retries', 3),
            'skip_unavailable_fragments': True,
            'keep_fragments': False,
            'noprogress': False,
            'progress_hooks': [self._progress_hook],
        }
        
        # Add headers if needed
        if 'esesja.tv' in stream_url:
            ydl_opts['http_headers'] = {
                'User-Agent': self.config.get('scraping.user_agent'),
                'Referer': video_info.url,
            }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Download the video
                ydl.download([stream_url])
                
                # Check if file was created
                if output_path.exists():
                    file_size = output_path.stat().st_size
                    self.logger.success(f"Downloaded video: {filename} ({format_file_size(file_size)})")
                    return str(output_path)
                else:
                    self.logger.error(f"Download completed but file not found: {output_path}")
                    return None
                    
        except yt_dlp.DownloadError as e:
            self.logger.error(f"yt-dlp download error: {e}")
            # Try alternative download method
            return self._fallback_download(stream_url, output_path, video_info)
            
        except Exception as e:
            self.logger.error(f"Unexpected error during download: {e}")
            return None
    
    def _get_format_selector(self) -> str:
        """Get format selector based on configuration."""
        quality = self.config.get('video.quality', 'best')
        
        if quality == 'best':
            return 'best[ext=mp4]/best'
        elif quality == 'worst':
            return 'worst[ext=mp4]/worst'
        else:
            # Specific quality like '480p', '720p'
            height = quality.replace('p', '')
            return f'best[height<={height}][ext=mp4]/best[height<={height}]/best[ext=mp4]/best'
    
    def _progress_hook(self, d):
        """Progress hook for yt-dlp downloads."""
        if d['status'] == 'downloading':
            if 'total_bytes' in d and d['total_bytes']:
                percent = (d['downloaded_bytes'] / d['total_bytes']) * 100
                speed = d.get('speed', 0)
                speed_str = f"{format_file_size(int(speed))}/s" if speed else "Unknown"
                
                # Update progress (simplified for logging)
                if hasattr(self, '_last_percent'):
                    if percent - self._last_percent >= 5:  # Log every 5%
                        self.logger.info(f"Download progress: {percent:.1f}% - Speed: {speed_str}")
                        self._last_percent = percent
                else:
                    self._last_percent = percent
                    
        elif d['status'] == 'finished':
            self.logger.info(f"Download finished: {d['filename']}")
            
        elif d['status'] == 'error':
            self.logger.error(f"Download error: {d.get('error', 'Unknown error')}")
    
    def _fallback_download(self, stream_url: str, output_path: Path, video_info: VideoInfo) -> Optional[str]:
        """Fallback download method using ffmpeg directly."""
        self.logger.info("Attempting fallback download with ffmpeg...")
        
        try:
            # Use ffmpeg to download m3u8 stream
            cmd = [
                'ffmpeg',
                '-i', stream_url,
                '-c', 'copy',
                '-bsf:a', 'aac_adtstoasc',
                '-y',  # Overwrite output file
                str(output_path)
            ]
            
            # Add headers if needed
            if 'esesja.tv' in stream_url:
                cmd.extend([
                    '-headers', f'User-Agent: {self.config.get("scraping.user_agent")}',
                    '-headers', f'Referer: {video_info.url}'
                ])
            
            self.logger.info(f"Running ffmpeg command: {' '.join(cmd)}")
            
            # Run ffmpeg with progress
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Monitor progress
            while True:
                output = process.stderr.readline()
                if output == '' and process.poll() is not None:
                    break
                if output and 'time=' in output:
                    # Extract time information for progress
                    time_match = output.split('time=')[1].split()[0] if 'time=' in output else ''
                    if time_match:
                        self.logger.debug(f"ffmpeg progress: {time_match}")
            
            # Wait for completion
            return_code = process.poll()
            
            if return_code == 0 and output_path.exists():
                file_size = output_path.stat().st_size
                self.logger.success(f"Fallback download successful: {output_path.name} ({format_file_size(file_size)})")
                return str(output_path)
            else:
                stderr_output = process.stderr.read() if process.stderr else "No error output"
                self.logger.error(f"ffmpeg failed with return code {return_code}: {stderr_output}")
                return None
                
        except FileNotFoundError:
            self.logger.error("ffmpeg not found. Please install ffmpeg for fallback downloads.")
            return None
        except Exception as e:
            self.logger.error(f"Fallback download failed: {e}")
            return None
    
    def extract_audio(self, video_path: str) -> Optional[str]:
        """Extract audio from video file for transcription."""
        video_file = Path(video_path)
        if not video_file.exists():
            self.logger.error(f"Video file not found: {video_path}")
            return None
        
        # Create audio file path
        audio_path = video_file.with_suffix('.wav')
        
        # Skip if audio already exists
        if audio_path.exists():
            self.logger.info(f"Audio file already exists: {audio_path}")
            return str(audio_path)
        
        self.logger.info(f"Extracting audio from: {video_file.name}")
        
        try:
            # Use ffmpeg to extract audio
            cmd = [
                'ffmpeg',
                '-i', str(video_file),
                '-vn',  # No video
                '-acodec', 'pcm_s16le',  # PCM 16-bit little-endian
                '-ar', '16000',  # 16kHz sample rate (good for Whisper)
                '-ac', '1',  # Mono
                '-y',  # Overwrite output file
                str(audio_path)
            ]
            
            self.logger.debug(f"Running audio extraction: {' '.join(cmd)}")
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.config.get('video.download_timeout', 3600)
            )
            
            if result.returncode == 0 and audio_path.exists():
                file_size = audio_path.stat().st_size
                self.logger.success(f"Audio extracted: {audio_path.name} ({format_file_size(file_size)})")
                return str(audio_path)
            else:
                self.logger.error(f"Audio extraction failed: {result.stderr}")
                return None
                
        except subprocess.TimeoutExpired:
            self.logger.error("Audio extraction timed out")
            return None
        except FileNotFoundError:
            self.logger.error("ffmpeg not found. Please install ffmpeg for audio extraction.")
            return None
        except Exception as e:
            self.logger.error(f"Audio extraction failed: {e}")
            return None
    
    def cleanup_video(self, video_path: str) -> bool:
        """Delete video file if configured to do so."""
        if not self.config.get('video.delete_after_transcription', True):
            return True
        
        try:
            video_file = Path(video_path)
            if video_file.exists():
                video_file.unlink()
                self.logger.info(f"Deleted video file: {video_file.name}")
            
            # Also delete audio file if it exists
            audio_file = video_file.with_suffix('.wav')
            if audio_file.exists():
                audio_file.unlink()
                self.logger.info(f"Deleted audio file: {audio_file.name}")
            
            return True
        except Exception as e:
            self.logger.warning(f"Failed to delete video file {video_path}: {e}")
            return False
    
    def get_video_info(self, stream_url: str) -> Dict[str, Any]:
        """Get video information without downloading."""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(stream_url, download=False)
                return {
                    'title': info.get('title', ''),
                    'duration': info.get('duration', 0),
                    'filesize': info.get('filesize', 0),
                    'format': info.get('format', ''),
                    'ext': info.get('ext', ''),
                }
        except Exception as e:
            self.logger.debug(f"Failed to extract video info: {e}")
            return {}
