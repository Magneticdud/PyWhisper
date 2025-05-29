import os
import tkinter as tk
from tkinter import ttk, filedialog
from dotenv import load_dotenv
import openai
import tempfile
import subprocess
import math
import time
from pydub import AudioSegment

class WhisperTranscriber:
    CHUNK_SIZE = 20 * 1024 * 1024  # 20MB chunks (Whisper's limit is 25MB)
    API_UPLOAD_URL = "https://api.openai.com/v1/audio/transcriptions"
    
    def __init__(self):
        self.api_key = None
        self.client = None
        
    def check_ffmpeg(self):
        try:
            subprocess.run(['ffmpeg', '-version'], 
                         stdout=subprocess.PIPE, 
                         stderr=subprocess.PIPE)
            return True
        except FileNotFoundError:
            return False
    
    def load_config(self):
        load_dotenv()
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found in .env file")
        openai.api_key = self.api_key
        self.client = openai.OpenAI(api_key=self.api_key)
    
    def optimize_audio(self, input_file):
        """Optimize audio for Whisper by converting to mono 16kHz
        
        Uses Ogg Vorbis format for temporary files as it provides good compression
        and is well-supported by the Whisper API. Ogg Vorbis is also open-source
        and royalty-free.
        """
        try:
            print(f"\n[1/5] Loading audio file: {os.path.basename(input_file)}")
            audio = AudioSegment.from_file(input_file)
            
            print(f"[2/5] Optimizing audio: Converting to mono 16kHz Ogg Vorbis")
            audio = audio.set_channels(1)  # Convert to mono
            audio = audio.set_frame_rate(16000)  # Convert to 16kHz
            
            # Save as Ogg Vorbis with optimized settings for speech
            temp_file = tempfile.NamedTemporaryFile(suffix='.ogg', delete=False)
            output_path = temp_file.name
            
            print(f"[3/5] Exporting optimized audio to temporary file...")
            audio.export(
                output_path,
                format='ogg',
                codec='libvorbis',
                bitrate='32k',  # Good balance of quality and size for speech
                parameters=[
                    '-ar', '16000',  # Sample rate
                    '-ac', '1',      # Mono
                    '-aq', '4'        # Audio quality (4 is good for speech)
                ]
            )
            
            # Get file size in MB
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"✓ Optimized audio created: {file_size_mb:.2f} MB")
            
            return output_path
            
        except Exception as e:
            print(f"✗ Error optimizing audio: {str(e)}")
            raise
    
    def split_audio(self, input_file, chunk_size_mb=20):
        """Split audio into chunks smaller than chunk_size_mb"""
        file_size = os.path.getsize(input_file)
        file_size_mb = file_size / (1024 * 1024)
        
        if file_size <= chunk_size_mb * 1024 * 1024:
            print(f"File size is {file_size_mb:.2f} MB (under {chunk_size_mb}MB), no splitting needed")
            return [input_file]
        
        # Calculate number of chunks needed
        num_chunks = math.ceil(file_size_mb / chunk_size_mb)
        audio = AudioSegment.from_file(input_file)
        chunk_duration = len(audio) / num_chunks
        
        print(f"File size is {file_size_mb:.2f} MB, splitting into {num_chunks} chunks...")
        
        chunks = []
        for i in range(num_chunks):
            start = int(i * chunk_duration)
            end = int((i + 1) * chunk_duration)
            chunk = audio[start:end]
            
            temp_file = tempfile.NamedTemporaryFile(suffix=f'_chunk{i}.ogg', delete=False)
            chunk.export(
                temp_file.name,
                format='ogg',
                codec='libvorbis',
                parameters=['-ar', '16000', '-ac', '1', '-aq', '4']
            )
            chunk_size = os.path.getsize(temp_file.name) / (1024 * 1024)
            print(f"  Chunk {i+1}/{num_chunks}: {chunk_size:.2f} MB")
            chunks.append(temp_file.name)
        
        print(f"✓ Split into {len(chunks)} chunks successfully")
        return chunks
    
    def transcribe(self, audio_file, model_name="whisper-1", create_srt=False, prompt_text=None, language=None):
        """Transcribe audio using OpenAI's Whisper API"""
        try:
            if not self.client:
                raise ValueError("OpenAI client not initialized. Check your API key.")
            
            file_size_mb = os.path.getsize(audio_file) / (1024 * 1024)
            print(f"\n[4/5] Uploading {file_size_mb:.2f} MB to OpenAI...")
            
            with open(audio_file, 'rb') as audio:
                print("  - Waiting for API response...")
                transcript = self.client.audio.transcriptions.create(
                    file=audio,
                    model=model_name,
                    language=language if language != 'auto' else None,
                    prompt=prompt_text if prompt_text and prompt_text.strip() else None,
                    response_format='srt' if create_srt else 'json'
                )
            
            print("✓ Transcription completed successfully")
            
            if create_srt:
                return transcript, transcript
                
            return transcript.text, None
            
        except Exception as e:
            raise Exception(f"Transcription error: {str(e)}")
    
    def _generate_srt(self, segments):
        """Generate SRT format subtitles from segments"""
        srt = []
        for i, segment in enumerate(segments, 1):
            start = self._format_timestamp(segment['start'])
            end = self._format_timestamp(segment['end'])
            text = segment['text'].strip()
            srt.append(f"{i}\n{start} --> {end}\n{text}\n")
        return "\n".join(srt)
    
    def _format_timestamp(self, seconds):
        """Convert seconds to SRT timestamp format"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}".replace('.', ',')


class WhisperGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("PyWhisper")
        self.root.geometry("800x800")
        
        self.transcriber = WhisperTranscriber()
        self.setup_ui()
        self.check_dependencies()
        
    def check_dependencies(self):
        if not self.transcriber.check_ffmpeg():
            print("FFmpeg not found in PATH. Please install FFmpeg and add it to your system PATH.")
            return False
            
        try:
            self.transcriber.load_config()
            print("\n=== PyWhisper Transcription Started ===")
            print(f"Using OpenAI API with model: {self.model_var.get()}")
            return True
        except Exception as e:
            print(f"Failed to load configuration: {str(e)}")
            return False
    
    def setup_ui(self):
        # File selection
        ttk.Label(self.root, text="Audio/Video File:").pack(pady=5)
        
        file_frame = ttk.Frame(self.root)
        file_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.file_path = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.file_path, width=70).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(file_frame, text="Browse...", command=self.browse_file).pack(side=tk.LEFT, padx=5)
        
        # API mode indicator
        api_frame = ttk.Frame(self.root)
        api_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(api_frame, text="Mode: OpenAI API", font=('Arial', 9, 'bold')).pack(side=tk.LEFT)
        
        # Model selection (simplified for API)
        model_frame = ttk.LabelFrame(self.root, text="Model")
        model_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.model_var = tk.StringVar(value="whisper-1")
        ttk.Radiobutton(model_frame, text="Whisper-1 (Latest)", 
                       variable=self.model_var, value="whisper-1").pack(side=tk.LEFT, padx=5)
        
        # Language selection (simplified for API)
        lang_frame = ttk.LabelFrame(self.root, text="Language")
        lang_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.lang_var = tk.StringVar(value="auto")
        
        # Common languages with better formatting
        common_langs = [
            ("Auto-detect", "auto"),
            ("English", "en"),
            ("Italiano", "it"),
            ("Español", "es"),
            ("Français", "fr"),
            ("Deutsch", "de"),
            ("中文", "zh")
        ]
        
        # Create radio buttons in a grid
        row = 0
        col = 0
        for lang_name, lang_code in common_langs:
            rb = ttk.Radiobutton(
                lang_frame,
                text=lang_name,
                variable=self.lang_var,
                value=lang_code
            )
            rb.grid(row=row, column=col, padx=5, pady=2, sticky='w')
            col += 1
            if col > 3:  # 4 columns
                col = 0
                row += 1
        
        # Prompt for context and important names
        ttk.Label(self.root, text="Context Prompt (optional):").pack(pady=(10, 0))
        self.prompt_text = tk.Text(self.root, height=4, wrap=tk.WORD, font=('Arial', 9))
        self.prompt_text.pack(fill=tk.X, padx=10, pady=5)
        ttk.Label(self.root, text="Add important names, technical terms, or context to improve accuracy", 
                 font=('Arial', 8), foreground='gray').pack()
        
        # Options
        self.create_srt = tk.BooleanVar()
        ttk.Checkbutton(self.root, text="Create SRT subtitles", variable=self.create_srt).pack(pady=5)
        
        # Status bar at the bottom
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, padding=(5, 2))
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.status_var = tk.StringVar(value="Ready to transcribe! Click the 'Start Transcribing' button to begin.")
        ttk.Label(status_frame, textvariable=self.status_var, anchor=tk.W).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Progress bar - more visible
        self.progress = ttk.Progressbar(
            self.root, 
            orient=tk.HORIZONTAL, 
            mode='determinate',
            length=100  # Will expand to fill
        )
        self.progress.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 5))
        
        # Output
        ttk.Label(self.root, text="Transcription:").pack()
        self.output_text = tk.Text(self.root, height=15, wrap=tk.WORD)
        self.output_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Buttons frame with a distinct background
        btn_frame = ttk.Frame(self.root, style='Card.TFrame')
        btn_frame.pack(fill=tk.X, padx=10, pady=10, ipadx=5, ipady=5)
        
        # Main action button - larger and more prominent
        style = ttk.Style()
        style.configure('Action.TButton', font=('Arial', 10, 'bold'), padding=10)
        
        # Transcribe button - larger and more visible
        self.transcribe_btn = ttk.Button(
            btn_frame, 
            text="🎤 Start Transcribing", 
            command=self.start_transcription,
            style='Action.TButton',
            width=20
        )
        self.transcribe_btn.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)
        
        # Secondary buttons
        ttk.Button(
            btn_frame, 
            text="🗑️ Clear", 
            command=self.clear_output
        ).pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Button(
            btn_frame, 
            text="💾 Save Output", 
            command=self.save_output
        ).pack(side=tk.LEFT, padx=5, pady=5)
    
    def browse_file(self):
        filetypes = [
            ("Audio/Video files", "*.mp3 *.wav *.m4a *.mp4 *.avi *.mkv"),
            ("All files", "*.*")
        ]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            self.file_path.set(filename)
    
    def update_status(self, message):
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def clear_output(self):
        self.output_text.delete(1.0, tk.END)
    
    def save_output(self):
        text = self.output_text.get(1.0, tk.END).strip()
        if not text:
            print("No transcription to save.")
            return
            
        filetypes = [("Text files", "*.txt"), ("SRT files", "*.srt"), ("All files", "*.*")]
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=filetypes,
            initialfile=os.path.splitext(os.path.basename(self.file_path.get()))[0]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(text)
                print(f"File saved successfully: {filename}")
            except Exception as e:
                print(f"Failed to save file: {str(e)}")
    
    def start_transcription(self):
        if not self.file_path.get() or not os.path.exists(self.file_path.get()):
            print("Please select a valid file.")
            return
            
        start_time = time.time()
        try:
            self.update_status("Starting transcription...")
            self.progress['value'] = 10
            
            # Optimize audio
            print("\n=== Starting Audio Optimization ===")
            audio_file = self.transcriber.optimize_audio(self.file_path.get())
            
            # Split into chunks if needed
            self.update_status("Preparing audio chunks...")
            self.progress['value'] = 30
            print("\n=== Splitting Audio ===")
            chunks = self.transcriber.split_audio(audio_file)
            
            # Transcribe each chunk
            self.update_status("Transcribing... (This may take a while)")
            self.progress['value'] = 50
            
            full_text = []
            srt_parts = []
            
            print("\n=== Starting Transcription ===")
            for i, chunk in enumerate(chunks, 1):
                chunk_start = time.time()
                self.update_status(f"Processing chunk {i} of {len(chunks)}...")
                print(f"\nProcessing chunk {i}/{len(chunks)}")
                
                # Get language, handling the 'auto' case
                lang = self.lang_var.get()
                if lang == 'auto':
                    lang = None
                else:
                    print(f"Language set to: {lang}")
                
                if self.prompt_text.get("1.0", tk.END).strip():
                    print("Using provided prompt for context")
                    
                text, srt = self.transcriber.transcribe(
                    chunk, 
                    self.model_var.get(),
                    self.create_srt.get(),
                    self.prompt_text.get("1.0", tk.END).strip(),
                    lang
                )
                
                chunk_time = time.time() - chunk_start
                print(f"Chunk {i} completed in {chunk_time:.1f} seconds")
                
                full_text.append(text)
                if srt:
                    srt_parts.append(srt)
                
                # Clean up chunk file
                try:
                    os.unlink(chunk)
                except:
                    pass
                
                # Update progress
                self.progress['value'] = 50 + (i / len(chunks)) * 40
            
            # Combine results
            combined_text = "\n\n".join(full_text)
            self.output_text.delete(1.0, tk.END)
            self.output_text.insert(tk.END, combined_text)
            
            if self.create_srt.get() and srt_parts:
                print("\n=== Combining SRT Subtitles ===")
                self.srt_content = self.transcriber.combine_srt(srt_parts)
            
            total_time = time.time() - start_time
            print(f"\n=== Transcription Complete ===")
            print(f"Total processing time: {total_time//60:.0f}m {total_time%60:.0f}s")
            print("You can now save the transcription or copy it to your clipboard.")
            
            self.update_status("Transcription complete!")
            self.progress['value'] = 100
            
        except Exception as e:
            error_msg = f"An error occurred during transcription: {str(e)}"
            print(f"\n✗ ERROR: {error_msg}")
            self.update_status("Error occurred during transcription")
            self.progress['value'] = 0
            
        finally:
            # Clean up
            try:
                if 'audio_file' in locals() and os.path.exists(audio_file):
                    os.unlink(audio_file)
                    print(f"Cleaned up temporary file: {os.path.basename(audio_file)}")
            except Exception as e:
                print(f"Warning: Could not clean up temporary file: {str(e)}")


def main():
    root = tk.Tk()
    app = WhisperGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
