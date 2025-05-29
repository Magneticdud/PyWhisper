# PyWhisper

![Project icon](icon.png)

A user-friendly Tkinter-based GUI for OpenAI's Whisper speech recognition system. PyWhisper allows you to transcribe audio and video files, with support for large files (over 25MB) by automatically splitting them into smaller chunks.

## Features

- 🎙️ Transcribe audio and video files to text
- 📝 Generate SRT subtitles
- 🚀 Optimizes audio for better transcription quality
- ✂️ Automatically splits large files (>25MB) into smaller chunks
- 🔄 Supports only OpenAI API because my GPU sucks and I can't test local models
- 🎛️ Simple and intuitive graphical interface
- 🏷️ Save transcriptions as text or SRT files

## Prerequisites

- Python 3.8 or higher
- FFmpeg installed and added to system PATH
- (Optional) OpenAI API key for using the API instead of local models

## Installation

1. **Clone the repository** or download the source code

2. **Install the required packages**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables** (optional):
   - Copy `.env.example` to `.env`
   - Add your OpenAI API key to the `.env` file if you want to use the API

## How to Use

1. Launch the application:
   ```bash
   python whisper_gui.py
   ```

2. Click "Browse..." to select an audio or video file

3. (Optional) Select a different Whisper model between all the available models on OpenAI which is...
   - whisper-1
   😂 that's it

4. (Optional) Check "Create SRT subtitles" to generate a subtitle file

5. Click "Transcribe" to start the transcription process

6. Once complete, you can:
   - Copy the text from the output box
   - Click "Save Output" to save the transcription as a text file
   - If SRT was selected, it will be automatically saved with the same name as the input file but with a .srt extension

## File Size Handling

For files larger than 20MB (to stay under Whisper's 25MB limit):

1. The application will automatically split the file into smaller chunks
2. Each chunk will be processed separately
3. The results will be combined into a single output
4. For SRT files, timestamps will be adjusted to maintain synchronization

## Using OpenAI API

My GPU sucks so I use the OpenAI API instead of local models:

1. Get an API key from [OpenAI](https://platform.openai.com/account/api-keys)
2. Add it to your `.env` file:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```
3. The application will automatically use the API if the key is present and if not, it will fail to run

## Troubleshooting

### FFmpeg Not Found
If you see an error about FFmpeg not being found:

- **Windows**: `winget install Gyan.FFmpeg`
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt-get install ffmpeg` (Debian/Ubuntu) or `sudo dnf install ffmpeg` (Fedora)

### Large File Handling
For very large files, the transcription might take a while. The progress bar will show the current status. I tried with a 40 minutes audio and it hung for 10 minutes. Maybe one day I will fix that. For now, you can see the progress in the console.

## License

This project is licensed under the GNU General Public License v3.0. See the [LICENSE](LICENSE) file for the full license text.

## Credits

- [OpenAI Whisper](https://github.com/openai/whisper)
- [FFmpeg](https://ffmpeg.org/)
- [pydub](https://github.com/jiaaro/pydub)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
