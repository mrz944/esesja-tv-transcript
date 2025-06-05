import os
import time
from pathlib import Path
from typing import Optional, Dict, Any
import whisper
import torch

from utils import Config, Logger, sanitize_filename, format_duration

class WhisperTranscriber:
    """Transcribe audio files using OpenAI Whisper."""
    
    def __init__(self, config: Config, logger: Logger):
        self.config = config
        self.logger = logger
        self.transcripts_dir = Path(config.get('storage.transcripts_dir'))
        self.transcripts_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Whisper model
        self.model = None
        self.model_name = config.get('transcription.whisper_model', 'base')
        self.language = config.get('transcription.language', 'pl')
        self.device = self._get_device()
        
        self.logger.info(f"Whisper transcriber initialized with model: {self.model_name}")
        self.logger.info(f"Using device: {self.device}")
    
    def _get_device(self) -> str:
        """Determine the best device for Whisper processing."""
        device_config = self.config.get('transcription.device', 'auto')
        
        if device_config == 'auto':
            if torch.cuda.is_available():
                return 'cuda'
            elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
                return 'mps'  # Apple Silicon
            else:
                return 'cpu'
        else:
            return device_config
    
    def _load_model(self):
        """Load Whisper model if not already loaded."""
        if self.model is None:
            self.logger.info(f"Loading Whisper model: {self.model_name}")
            try:
                self.model = whisper.load_model(self.model_name, device=self.device)
                self.logger.success(f"Whisper model loaded successfully")
            except Exception as e:
                self.logger.error(f"Failed to load Whisper model: {e}")
                raise
    
    def transcribe_audio(self, audio_path: str, video_info: Dict[str, Any]) -> Optional[str]:
        """Transcribe audio file and return the transcript file path."""
        audio_file = Path(audio_path)
        if not audio_file.exists():
            self.logger.error(f"Audio file not found: {audio_path}")
            return None
        
        # Create transcript filename
        video_id = video_info.get('id', 'unknown')
        safe_title = sanitize_filename(video_info.get('title', 'untitled'))
        transcript_filename = f"{video_id}_{safe_title}.txt"
        transcript_path = self.transcripts_dir / transcript_filename
        
        # Skip if transcript already exists
        if transcript_path.exists():
            self.logger.info(f"Transcript already exists: {transcript_path}")
            return str(transcript_path)
        
        self.logger.info(f"Transcribing audio: {audio_file.name}")
        self.logger.info(f"Output transcript: {transcript_filename}")
        
        try:
            # Load model if needed
            self._load_model()
            
            # Start transcription
            start_time = time.time()
            
            # Transcribe with Whisper
            result = self.model.transcribe(
                str(audio_file),
                language=self.language,
                task='transcribe',
                verbose=False,
                word_timestamps=False,
                fp16=self.device == 'cuda',  # Use FP16 on CUDA for speed
            )
            
            end_time = time.time()
            transcription_time = end_time - start_time
            
            # Extract transcript text
            transcript_text = result['text'].strip()
            
            if not transcript_text:
                self.logger.warning(f"Empty transcript generated for: {audio_file.name}")
                return None
            
            # Create full transcript with metadata
            full_transcript = self._format_transcript(
                transcript_text, 
                video_info, 
                result, 
                transcription_time
            )
            
            # Save transcript
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(full_transcript)
            
            # Log success
            audio_duration = result.get('duration', 0)
            self.logger.success(
                f"Transcript created: {transcript_filename} "
                f"(Audio: {format_duration(int(audio_duration))}, "
                f"Processing: {format_duration(int(transcription_time))})"
            )
            
            return str(transcript_path)
            
        except Exception as e:
            self.logger.error(f"Transcription failed for {audio_file.name}: {e}")
            return None
    
    def _format_transcript(self, transcript_text: str, video_info: Dict[str, Any], 
                          whisper_result: Dict[str, Any], processing_time: float) -> str:
        """Format transcript with metadata header."""
        
        # Extract metadata
        title = video_info.get('title', 'Unknown Title')
        video_id = video_info.get('id', 'unknown')
        date = video_info.get('date', 'Unknown Date')
        publisher = video_info.get('publisher', 'Unknown Publisher')
        url = video_info.get('url', '')
        
        # Whisper metadata
        detected_language = whisper_result.get('language', 'unknown')
        audio_duration = whisper_result.get('duration', 0)
        
        # Create formatted transcript
        header = f"""# Transkrypcja Video - {title}

## Informacje o nagraniu
- **Tytuł**: {title}
- **ID Video**: {video_id}
- **Data**: {date}
- **Wydawca**: {publisher}
- **URL**: {url}

## Informacje o transkrypcji
- **Model Whisper**: {self.model_name}
- **Wykryty język**: {detected_language}
- **Czas audio**: {format_duration(int(audio_duration))}
- **Czas przetwarzania**: {format_duration(int(processing_time))}
- **Data transkrypcji**: {time.strftime('%Y-%m-%d %H:%M:%S')}

---

## Transkrypcja

{transcript_text}

---

*Transkrypcja wygenerowana automatycznie przy użyciu OpenAI Whisper*
"""
        
        return header
    
    def transcribe_with_timestamps(self, audio_path: str, video_info: Dict[str, Any]) -> Optional[str]:
        """Transcribe audio with word-level timestamps (more detailed)."""
        audio_file = Path(audio_path)
        if not audio_file.exists():
            self.logger.error(f"Audio file not found: {audio_path}")
            return None
        
        # Create transcript filename with timestamps suffix
        video_id = video_info.get('id', 'unknown')
        safe_title = sanitize_filename(video_info.get('title', 'untitled'))
        transcript_filename = f"{video_id}_{safe_title}_timestamps.txt"
        transcript_path = self.transcripts_dir / transcript_filename
        
        # Skip if transcript already exists
        if transcript_path.exists():
            self.logger.info(f"Timestamped transcript already exists: {transcript_path}")
            return str(transcript_path)
        
        self.logger.info(f"Creating timestamped transcript: {audio_file.name}")
        
        try:
            # Load model if needed
            self._load_model()
            
            # Transcribe with word timestamps
            result = self.model.transcribe(
                str(audio_file),
                language=self.language,
                task='transcribe',
                verbose=False,
                word_timestamps=True,
                fp16=self.device == 'cuda',
            )
            
            # Format transcript with timestamps
            timestamped_text = self._format_timestamped_transcript(result)
            
            # Create full transcript with metadata
            full_transcript = self._format_transcript(
                timestamped_text, 
                video_info, 
                result, 
                0  # Processing time not tracked for this method
            )
            
            # Save transcript
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(full_transcript)
            
            self.logger.success(f"Timestamped transcript created: {transcript_filename}")
            return str(transcript_path)
            
        except Exception as e:
            self.logger.error(f"Timestamped transcription failed for {audio_file.name}: {e}")
            return None
    
    def _format_timestamped_transcript(self, whisper_result: Dict[str, Any]) -> str:
        """Format transcript with timestamps."""
        segments = whisper_result.get('segments', [])
        
        if not segments:
            return whisper_result.get('text', '')
        
        formatted_lines = []
        
        for segment in segments:
            start_time = segment.get('start', 0)
            end_time = segment.get('end', 0)
            text = segment.get('text', '').strip()
            
            if text:
                timestamp = f"[{self._format_timestamp(start_time)} -> {self._format_timestamp(end_time)}]"
                formatted_lines.append(f"{timestamp} {text}")
        
        return '\n'.join(formatted_lines)
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to MM:SS or HH:MM:SS format."""
        total_seconds = int(seconds)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded Whisper model."""
        if self.model is None:
            return {
                'model_name': self.model_name,
                'loaded': False,
                'device': self.device,
                'language': self.language
            }
        
        return {
            'model_name': self.model_name,
            'loaded': True,
            'device': self.device,
            'language': self.language,
            'model_size': self._get_model_size()
        }
    
    def _get_model_size(self) -> str:
        """Get approximate model size information."""
        size_info = {
            'tiny': '39 MB',
            'base': '74 MB',
            'small': '244 MB',
            'medium': '769 MB',
            'large': '1550 MB',
            'large-v2': '1550 MB',
            'large-v3': '1550 MB'
        }
        return size_info.get(self.model_name, 'Unknown')
    
    def cleanup(self):
        """Clean up resources."""
        if self.model is not None:
            del self.model
            self.model = None
            
            # Clear CUDA cache if using GPU
            if self.device == 'cuda' and torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self.logger.info("Whisper model resources cleaned up")
