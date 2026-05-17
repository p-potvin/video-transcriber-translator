from typing import Tuple
import os
import tempfile
import time
import shutil
from contextlib import contextmanager

# Silence tqdm globally to keep terminal clean
import tqdm
class DummyTqdm:
    def __init__(self, iterable=None, *args, **kwargs):
        self.iterable = iterable
    def __iter__(self):
        return iter(self.iterable) if self.iterable is not None else self
    def __next__(self):
        raise StopIteration
    def update(self, *args, **kwargs): pass
    def close(self): pass
    def write(self, s, *args, **kwargs): print(s)
    def set_description(self, *args, **kwargs): pass
    def set_postfix(self, *args, **kwargs): pass
tqdm.tqdm = DummyTqdm
from vault_enhancer import utils
from vault_enhancer import translation
from vault_enhancer import media

_PARAKEET_MODEL = None

def get_parakeet_model():
    global _PARAKEET_MODEL
    if _PARAKEET_MODEL is None:
        from vault_enhancer.parakeet_wrapper import ParakeetV3Wrapper
        _PARAKEET_MODEL = ParakeetV3Wrapper()
    return _PARAKEET_MODEL

def transcribe_video(
    input_file,
    output_file = None,
    languages = None,
    skip_original = False,
    skip_vocal_isolation = False,
    translate_api = "local",
    translate_mode = "non-target",
    max_translate_chars = 350000,
    max_translate_calls = 500,
    overwrite = False,
    source_language = "en",
    delay_ms = 0,
    max_duration = 7200,
    progress_callback = None
):
    start_total = time.time()
    # Check if all requested output files already exist when overwrite is disabled
    if not overwrite and media.srt_files_exist(input_file, output_file, languages, skip_original):
        print(f"All SRT files already exist for {input_file}, skipping.")
        if progress_callback is not None:
            progress_callback(f"SRT files already exist for {os.path.basename(input_file)}, skipping.", 100)
        return []
    # Early: Check for audio stream using ffprobe
    audio_duration = media.get_audio_duration_seconds(input_file)
    if audio_duration is None or audio_duration == 0.0:
        raise RuntimeError(f"No audio stream detected in file: {input_file}")
    # Validate input file
    if not os.path.isfile(input_file):
        if os.path.isdir(input_file):
            raise ValueError(f"Input path is a directory, not a file: {input_file}")
        else:
            raise FileNotFoundError(f"Input file does not exist: {input_file}")

    all_segments = list()
    original_texts = []
    outputs_to_generate = {}
    # --- Vocal Isolation, Segmentation, Normalization and Transcription ---
    all_segments = list()
    original_texts = []
    outputs_to_generate = {}
    output_paths = []
    
    # Tuned VAD parameters for more stable speech segments.
    # min_silence_duration_ms: higher value (1000ms+) prevents cutting during natural phrasing pauses.
    # speech_pad_ms: reduced to 250ms for cleaner cuts without trailing silence.
    vad_parameters = dict(
        min_silence_duration_ms = 500,
        speech_pad_ms = 100,
        min_speech_duration_ms = 300
    )

    # --- Step 0: Warm-load Models ---
    # Establishing the GPU context early prevents late-initialization CUDA errors 
    # and eliminates weight-swap latency between Demucs and ASR.

    print(f"--- Step 0: Preparing environment ---")
    if progress_callback is not None:
        progress_callback("Preparing environment...", 1)
    time.sleep(0.5)
    if progress_callback is not None:
        progress_callback("Step 0: Loading ML models into VRAM (this may take a minute)...", 2)
    print(f"--- Step 0: Loading AI Models into VRAM ---")
    # Animate progress bar during dead time
    load_start = time.time()
    tick = 0
    while _PARAKEET_MODEL is None:
        # Simulate progress up to 10% while waiting for model to load
        if progress_callback is not None:
            progress_callback(f"Loading ML models... (still preparing, please wait) [{tick}s]", min(10, 2 + tick))
        time.sleep(1)
        tick += 1
    model = get_parakeet_model()
    # Ensure context is fully initialized before starting subprocesses
    try:
        import torch
        if torch.cuda.is_available():
            torch.cuda.synchronize()
    except ImportError:
        pass
    print(f"Models loaded successfully in {time.time() - load_start:.2f}s.")
    if progress_callback is not None:
        progress_callback("Initiating Media Pipeline...", 12)

    if skip_vocal_isolation:
        print("Skipping audio fix as requested.")
        transcription_file = input_file
    else:
        try:
            fixed_file = media.fix_audio_and_reencode(
                input_file, 
                delay_ms=delay_ms, 
                max_duration=max_duration,
                progress_callback=progress_callback
            )
            # Only use the fixed file if it is not a temp .wav
            if fixed_file.endswith('_asr_temp.wav'):
                transcription_file = input_file
            else:
                transcription_file = fixed_file
        except Exception as e:
            print(f"Warning: Audio fix failed: {e}. Falling back to original video.")
            transcription_file = input_file

    print(f"--- Step 2: Transcribing Video (Parakeet) ---")
    # Extract WAV for reliable ASR loading (bypasses torchaudio FFmpeg extension bugs)
    if progress_callback is not None:
        progress_callback("Extracting audio for ASR...", 48)

    asr_wav_file = media.extract_wav_for_asr(transcription_file)
    print(f"Source file for transcription (WAV): {asr_wav_file}")
    
    if progress_callback is not None:
        progress_callback("Step 2: Transcribing Audio...", 50)
        
    all_segments = model.transcribe_file(
        asr_wav_file,
        language=source_language
    )
    
    # Cleanup ASR temp file
    if os.path.exists(asr_wav_file):
        os.remove(asr_wav_file)

    # Already checked above, just reuse
    # audio_duration = media.get_audio_duration_seconds(input_file) or 0.0
    # Use the value from above

    if all_segments:
        print(f"First segment starts at: {all_segments[0].start:.2f}s and ends at {all_segments[0].end:.2f}s.")

    original_texts = [segment.text for segment in all_segments]

    print(f"Segments generated: {len(original_texts)}. Total duration: {audio_duration:.2f}s.")
    
    base_path = os.path.splitext(input_file)[0]
    output_base = os.path.splitext(output_file)[0] if output_file else base_path

    srt_path = output_base + ".srt"
    outputs_to_generate[srt_path] = original_texts
    
    # Generate an explicit .en.srt by default
    en_srt_path = output_base + ".en.srt"
    outputs_to_generate[en_srt_path] = original_texts

    # Translate if user provided target languages
    print(f"--- Step 3: Translating the transcribed vocals (Local ArgosTranslate) ---")
    print("Translating segments...")
    if languages:        
        target_languages = languages if isinstance(languages, list) and len(languages) > 0 else source_language
        
        for lang_code in target_languages:
            lang_code = lang_code.strip().lower()

            if not lang_code or lang_code in ("orig", "original", "none"):
                continue

            srt_lang_path = f"{output_base}.{lang_code}.srt"
            
            import asyncio
            trans_start_ts = time.time()
            try:
                # Use metadata from segments to guide translation
                translated_texts = asyncio.run(translation.translate_segments(
                    all_segments,
                    target_lang = lang_code,
                    translate_api = translate_api,
                    translate_mode = translate_mode,
                    max_chars = max_translate_chars,
                    max_calls = max_translate_calls,
                    detector = None,
                ))
                trans_elapsed = time.time() - trans_start_ts
                print(f"Translation to {lang_code} completed in {trans_elapsed:.2f}s")
            except Exception as exc:
                print(f"Skipping translation to {lang_code}: {exc}")
                continue
            
            outputs_to_generate[srt_lang_path] = translated_texts

        if not outputs_to_generate:
            print("No new files to generate.")
            return []
        
        for path, texts_to_write in outputs_to_generate.items():
            utils.write_srt(path, all_segments, texts_to_write)
            output_paths.append(path)
        
    print(f"\n--- Processing Finished ---")
    print(f"\nTotal time elapsed: {time.time() - start_total:.2f}s")
    return output_paths
