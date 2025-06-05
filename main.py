#!/usr/bin/env python3
"""
esesja.tv Video Scraper and Transcript Generator

This application scrapes videos from esesja.tv, downloads them, and generates
transcripts using OpenAI Whisper.
"""

import sys
import signal
import argparse
from typing import List, Optional
from pathlib import Path

from utils import Config, Logger, ProgressTracker, print_banner
from scraper import EsesjatvScraper, VideoInfo
from downloader import VideoDownloader
from transcriber import WhisperTranscriber

class EsesjatvProcessor:
    """Main processor for esesja.tv videos."""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = Config(config_path)
        self.logger = Logger("esesja_processor", self.config)
        self.progress_tracker = ProgressTracker(self.config)
        
        # Initialize components
        self.scraper = EsesjatvScraper(self.config, self.logger)
        self.downloader = VideoDownloader(self.config, self.logger)
        self.transcriber = WhisperTranscriber(self.config, self.logger)
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
        self.shutdown_requested = False
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully."""
        self.logger.info("Shutdown signal received. Finishing current operation...")
        self.shutdown_requested = True
    
    def run(self, selected_videos: Optional[List[int]] = None, 
            interactive: bool = True) -> bool:
        """Main processing loop."""
        try:
            print_banner()
            
            # Get list of available videos
            self.logger.info("Fetching video list from esesja.tv...")
            videos = self.scraper.get_video_list()
            
            if not videos:
                self.logger.error("No videos found on the page")
                return False
            
            # Show video selection interface
            if interactive:
                selected_videos = self._show_video_selection(videos)
                if not selected_videos:
                    self.logger.info("No videos selected. Exiting.")
                    return True
            else:
                # Process all videos if not interactive
                selected_videos = list(range(len(videos)))
            
            # Process selected videos
            return self._process_videos(videos, selected_videos)
            
        except KeyboardInterrupt:
            self.logger.info("Process interrupted by user")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            return False
        finally:
            self._cleanup()
    
    def _show_video_selection(self, videos: List[VideoInfo]) -> List[int]:
        """Display video selection interface."""
        print(f"\n📺 Found {len(videos)} videos available for processing:\n")
        
        # Display videos with numbers
        for i, video in enumerate(videos, 1):
            status = "✅ Completed" if self.progress_tracker.is_processed(video.url) else "⏳ Pending"
            print(f"{i:2d}. {video} - {status}")
        
        print(f"\n📊 Processing Statistics:")
        stats = self.progress_tracker.get_stats()
        print(f"   • Completed: {stats['completed']}")
        print(f"   • Failed: {stats['failed']}")
        print(f"   • Total processed: {stats['total']}")
        
        print(f"\n🎯 Selection Options:")
        print(f"   • Enter numbers separated by commas (e.g., 1,3,5)")
        print(f"   • Enter range (e.g., 1-10)")
        print(f"   • Enter 'all' for all videos")
        print(f"   • Enter 'pending' for unprocessed videos only")
        print(f"   • Enter 'recent:N' for N most recent videos (e.g., recent:5)")
        print(f"   • Enter 'failed' to retry failed videos")
        print(f"   • Press Enter to exit")
        
        while True:
            try:
                selection = input(f"\n🔍 Select videos to process: ").strip()
                
                if not selection:
                    return []
                
                return self._parse_selection(selection, videos)
                
            except ValueError as e:
                print(f"❌ Invalid selection: {e}")
                continue
    
    def _parse_selection(self, selection: str, videos: List[VideoInfo]) -> List[int]:
        """Parse user selection string."""
        selection = selection.lower().strip()
        
        if selection == 'all':
            return list(range(len(videos)))
        
        elif selection == 'pending':
            return [i for i, video in enumerate(videos) 
                   if not self.progress_tracker.is_processed(video.url)]
        
        elif selection == 'failed':
            failed_urls = [url for url, data in self.progress_tracker.progress_data['videos'].items()
                          if data.get('status') == 'failed']
            return [i for i, video in enumerate(videos) if video.url in failed_urls]
        
        elif selection.startswith('recent:'):
            try:
                n = int(selection.split(':')[1])
                return list(range(min(n, len(videos))))
            except (ValueError, IndexError):
                raise ValueError("Invalid recent format. Use 'recent:N' where N is a number")
        
        else:
            # Parse comma-separated numbers and ranges
            indices = []
            parts = selection.split(',')
            
            for part in parts:
                part = part.strip()
                
                if '-' in part:
                    # Handle range like "1-5"
                    try:
                        start, end = map(int, part.split('-'))
                        indices.extend(range(start - 1, end))  # Convert to 0-based
                    except ValueError:
                        raise ValueError(f"Invalid range format: {part}")
                else:
                    # Handle single number
                    try:
                        indices.append(int(part) - 1)  # Convert to 0-based
                    except ValueError:
                        raise ValueError(f"Invalid number: {part}")
            
            # Validate indices
            invalid_indices = [i for i in indices if i < 0 or i >= len(videos)]
            if invalid_indices:
                raise ValueError(f"Invalid video numbers: {[i + 1 for i in invalid_indices]}")
            
            return sorted(list(set(indices)))  # Remove duplicates and sort
    
    def _process_videos(self, videos: List[VideoInfo], selected_indices: List[int]) -> bool:
        """Process selected videos."""
        selected_videos = [videos[i] for i in selected_indices]
        
        self.logger.info(f"Processing {len(selected_videos)} selected videos")
        
        success_count = 0
        failed_count = 0
        
        for i, video in enumerate(selected_videos, 1):
            if self.shutdown_requested:
                self.logger.info("Shutdown requested. Stopping processing.")
                break
            
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Processing video {i}/{len(selected_videos)}: {video.title}")
            self.logger.info(f"{'='*60}")
            
            # Skip if already processed
            if self.progress_tracker.is_processed(video.url):
                self.logger.info(f"Video already processed, skipping: {video.title}")
                continue
            
            try:
                success = self._process_single_video(video)
                if success:
                    success_count += 1
                    self.logger.success(f"Successfully processed: {video.title}")
                else:
                    failed_count += 1
                    self.logger.error(f"Failed to process: {video.title}")
                    
            except Exception as e:
                failed_count += 1
                error_msg = f"Unexpected error processing {video.title}: {e}"
                self.logger.error(error_msg)
                self.progress_tracker.mark_failed(video.url, str(e))
        
        # Final summary
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"PROCESSING COMPLETE")
        self.logger.info(f"{'='*60}")
        self.logger.info(f"✅ Successfully processed: {success_count}")
        self.logger.info(f"❌ Failed: {failed_count}")
        self.logger.info(f"📊 Total: {success_count + failed_count}")
        
        return failed_count == 0
    
    def _process_single_video(self, video: VideoInfo) -> bool:
        """Process a single video through the complete pipeline."""
        try:
            # Step 1: Extract stream URL
            self.logger.info("Step 1: Extracting video stream URL...")
            stream_url = self.scraper.get_video_stream_url(video.url)
            if not stream_url:
                raise Exception("Could not extract video stream URL")
            
            # Step 2: Download video
            self.logger.info("Step 2: Downloading video...")
            video_path = self.downloader.download_video(video, stream_url)
            if not video_path:
                raise Exception("Video download failed")
            
            # Step 3: Extract audio
            self.logger.info("Step 3: Extracting audio...")
            audio_path = self.downloader.extract_audio(video_path)
            if not audio_path:
                raise Exception("Audio extraction failed")
            
            # Step 4: Generate transcript
            self.logger.info("Step 4: Generating transcript...")
            transcript_path = self.transcriber.transcribe_audio(audio_path, video.to_dict())
            if not transcript_path:
                raise Exception("Transcript generation failed")
            
            # Step 5: Cleanup
            self.logger.info("Step 5: Cleaning up temporary files...")
            self.downloader.cleanup_video(video_path)
            
            # Mark as completed
            self.progress_tracker.mark_completed(video.url, {
                **video.to_dict(),
                'stream_url': stream_url,
                'transcript_path': transcript_path
            })
            
            return True
            
        except Exception as e:
            self.progress_tracker.mark_failed(video.url, str(e))
            return False
    
    def _cleanup(self):
        """Clean up resources."""
        try:
            self.scraper.close()
            self.transcriber.cleanup()
            self.logger.info("Cleanup completed")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="esesja.tv Video Scraper and Transcript Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                    # Interactive mode
  python main.py --all              # Process all videos
  python main.py --config custom.yaml  # Use custom config
  python main.py --recent 5         # Process 5 most recent videos
        """
    )
    
    parser.add_argument(
        '--config', '-c',
        default='config.yaml',
        help='Configuration file path (default: config.yaml)'
    )
    
    parser.add_argument(
        '--all',
        action='store_true',
        help='Process all videos without interactive selection'
    )
    
    parser.add_argument(
        '--recent',
        type=int,
        metavar='N',
        help='Process N most recent videos'
    )
    
    parser.add_argument(
        '--pending',
        action='store_true',
        help='Process only pending (unprocessed) videos'
    )
    
    parser.add_argument(
        '--failed',
        action='store_true',
        help='Retry failed videos'
    )
    
    args = parser.parse_args()
    
    # Check if config file exists
    if not Path(args.config).exists():
        print(f"❌ Configuration file not found: {args.config}")
        print("Please create a config.yaml file or specify a valid config file with --config")
        return 1
    
    try:
        processor = EsesjatvProcessor(args.config)
        
        # Determine selection mode
        selected_videos = None
        interactive = True
        
        if args.all:
            interactive = False
        elif args.recent:
            selected_videos = list(range(args.recent))
            interactive = False
        elif args.pending or args.failed:
            # These will be handled in the selection logic
            interactive = True
        
        # Run processor
        success = processor.run(selected_videos, interactive)
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n❌ Process interrupted by user")
        return 1
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
