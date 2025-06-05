# esesja.tv Video Scraper and Transcript Generator

A comprehensive Python application that scrapes videos from esesja.tv, downloads them, and generates transcripts using OpenAI Whisper AI.

## Features

- 🎥 **Video Discovery**: Automatically scrapes video listings from esesja.tv
- 📥 **Smart Downloads**: Downloads m3u8 video streams using yt-dlp with fallback support
- 🎙️ **Audio Extraction**: Extracts audio from videos for transcription
- 📝 **AI Transcription**: Generates accurate transcripts using OpenAI Whisper
- 🔄 **Progress Tracking**: Resume interrupted sessions and skip already processed videos
- 🎯 **Flexible Selection**: Interactive video selection with multiple filtering options
- 🧹 **Auto Cleanup**: Configurable deletion of video files after transcription
- 📊 **Detailed Logging**: Comprehensive logging with colored output and file logs
- ⚙️ **Configurable**: YAML-based configuration for easy customization

## Installation

### Prerequisites

- Python 3.8 or higher
- ffmpeg (for video/audio processing)

### Install ffmpeg

**macOS (using Homebrew):**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Windows:**
Download from [https://ffmpeg.org/download.html](https://ffmpeg.org/download.html) and add to PATH.

### Install Python Dependencies

1. Clone or download this project
2. Install required packages:

```bash
pip install -r requirements.txt
```

## Configuration

The application uses `config.yaml` for configuration. Key settings include:

```yaml
scraping:
  base_url: "https://esesja.tv/transmisje_z_obrad/1475/rada-dzielnicy-wlochy.htm"
  delay_between_requests: 2  # Be respectful to the server

video:
  delete_after_transcription: true  # Save disk space
  quality: "best"  # or "480p", "720p", etc.

transcription:
  whisper_model: "base"  # tiny, base, small, medium, large
  language: "pl"  # Polish language
  output_format: "txt"  # Plain text transcripts
```

## Usage

### Interactive Mode (Recommended)

Run the application and select videos interactively:

```bash
python main.py
```

This will:
1. Fetch all available videos from the configured URL
2. Display a numbered list with processing status
3. Allow you to select which videos to process
4. Show progress and statistics

### Selection Options

When prompted, you can use various selection formats:

- **Specific videos**: `1,3,5` (process videos 1, 3, and 5)
- **Range**: `1-10` (process videos 1 through 10)
- **All videos**: `all`
- **Pending only**: `pending` (only unprocessed videos)
- **Recent videos**: `recent:5` (5 most recent videos)
- **Failed videos**: `failed` (retry previously failed videos)

### Command Line Options

```bash
# Process all videos without interaction
python main.py --all

# Process 5 most recent videos
python main.py --recent 5

# Use custom configuration file
python main.py --config my_config.yaml

# Process only pending videos
python main.py --pending

# Retry failed videos
python main.py --failed
```

### Example Session

```
╔══════════════════════════════════════════════════════════════╗
║                    esesja.tv Video Scraper                   ║
║                   and Transcript Generator                   ║
╚══════════════════════════════════════════════════════════════╝

📺 Found 15 videos available for processing:

 1. [2025-04-15] IX Sesja Rady Dzielnicy Włochy - 161 views - ⏳ Pending
 2. [2025-03-20] VIII Sesja Rady Dzielnicy Włochy - 245 views - ✅ Completed
 3. [2025-02-18] VII Sesja Rady Dzielnicy Włochy - 189 views - ⏳ Pending

📊 Processing Statistics:
   • Completed: 1
   • Failed: 0
   • Total processed: 1

🎯 Selection Options:
   • Enter numbers separated by commas (e.g., 1,3,5)
   • Enter range (e.g., 1-10)
   • Enter 'all' for all videos
   • Enter 'pending' for unprocessed videos only
   • Enter 'recent:N' for N most recent videos (e.g., recent:5)
   • Enter 'failed' to retry failed videos
   • Press Enter to exit

🔍 Select videos to process: 1,3
```

## Output

### Transcripts

Transcripts are saved in the `data/transcripts/` directory with the following format:

```
# Transkrypcja Video - IX Sesja Rady Dzielnicy Włochy

## Informacje o nagraniu
- **Tytuł**: IX Sesja Rady Dzielnicy Włochy m.st. Warszawy w dniu 15 kwietnia 2025 r.
- **ID Video**: 67352
- **Data**: 2025-04-15
- **Wydawca**: Rada Dzielnicy Włochy
- **URL**: https://esesja.tv/transmisja/67352/...

## Informacje o transkrypcji
- **Model Whisper**: base
- **Wykryty język**: pl
- **Czas audio**: 02:40:46
- **Czas przetwarzania**: 00:15:23
- **Data transkrypcji**: 2025-06-05 08:30:15

---

## Transkrypcja

[Actual transcript content here...]

---

*Transkrypcja wygenerowana automatycznie przy użyciu OpenAI Whisper*
```

### Progress Tracking

Progress is automatically saved in `data/progress.json`, allowing you to:
- Resume interrupted sessions
- Skip already processed videos
- Retry failed videos
- View processing statistics

### Logs

Detailed logs are saved in the `logs/` directory with timestamps and color-coded console output.

## Project Structure

```
ender_script/
├── config.yaml              # Configuration file
├── main.py                  # Main application entry point
├── scraper.py              # Web scraping logic
├── downloader.py           # Video downloading logic
├── transcriber.py          # Whisper transcription logic
├── utils.py                # Utility functions and classes
├── requirements.txt        # Python dependencies
├── README.md               # This file
├── .gitignore             # Git ignore rules
├── data/                  # Data directory (created automatically)
│   ├── videos/            # Temporary video storage
│   ├── transcripts/       # Generated transcripts
│   └── progress.json      # Progress tracking
└── logs/                  # Log files (created automatically)
```

## Whisper Models

Choose the appropriate Whisper model based on your needs:

| Model  | Size | Speed | Accuracy | Use Case |
|--------|------|-------|----------|----------|
| tiny   | 39MB | Fastest | Basic | Quick testing |
| base   | 74MB | Fast | Good | **Recommended default** |
| small  | 244MB | Medium | Better | Higher accuracy needed |
| medium | 769MB | Slow | Very Good | Professional use |
| large  | 1550MB | Slowest | Best | Maximum accuracy |

## Troubleshooting

### Common Issues

**1. ffmpeg not found**
```
Error: ffmpeg not found. Please install ffmpeg for audio extraction.
```
Solution: Install ffmpeg using your system's package manager.

**2. CUDA out of memory**
```
Error: CUDA out of memory
```
Solution: Use a smaller Whisper model or set `device: "cpu"` in config.yaml.

**3. Video download fails**
```
Error: yt-dlp download error
```
Solution: The application will automatically try ffmpeg as a fallback.

**4. Empty transcript**
```
Warning: Empty transcript generated
```
Solution: Check if the audio contains speech or try a different Whisper model.

### Performance Tips

- Use GPU acceleration if available (CUDA/MPS)
- Choose appropriate Whisper model for your hardware
- Enable video deletion after transcription to save disk space
- Process videos in batches to avoid memory issues

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for educational and research purposes. Please respect the terms of service of esesja.tv and use responsibly.

## Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper) for speech recognition
- [yt-dlp](https://github.com/yt-dlp/yt-dlp) for video downloading
- [BeautifulSoup](https://www.crummy.com/software/BeautifulSoup/) for web scraping
