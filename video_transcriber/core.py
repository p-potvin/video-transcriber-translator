from typing import Tuple
import os
import tempfile
import time
import shutil
from tqdm import tqdm
from halo import Halo
from contextlib import contextmanager
from video_transcriber import utils
from video_transcriber import translation
from video_transcriber import media

_WHISPER_MODEL = None

@contextmanager
def temporary_directory(prefix = "transcriber_"):
    temp_dir = tempfile.mkdtemp(prefix = prefix)
    try:
        yield temp_dir
    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to clean up temp directory {temp_dir}: {e}")

@Halo(text='Loading Whisper Model...', color='blue', spinner='star')
def get_whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        from faster_whisper import WhisperModel
        _WHISPER_MODEL = WhisperModel("large-v3-turbo", device = "cuda", compute_type = "float16")
    return _WHISPER_MODEL

@Halo(text='Isolating vocals...', color='red', spinner='dots12')
def get_isolated_vocals(input_file, temp_dir):    
    try:
        isolated_audio_file = media.isolate_vocals_with_demucs(
            input_file,
            temp_dir,
            device = "cuda"
        )

        return isolated_audio_file
    except Exception as e:
        print(f"Warning: Vocal isolation failed: {e}. Falling back to original audio.")
        return input_file

def transcribe_video(
    input_file,
    output_file = None,
    languages = None,
    skip_original = False,
    skip_vocal_isolation = False,
    translate_api = "deep-translator",
    translate_mode = "non-target",
    max_translate_chars = 350000,
    max_translate_calls = 500,
    overwrite = False,
    source_language = ["en"]
):
    start_total = time.time()
    # Validate input file
    if not os.path.isfile(input_file):
        if os.path.isdir(input_file):
            raise ValueError(f"Input path is a directory, not a file: {input_file}")
        else:
            raise FileNotFoundError(f"Input file does not exist: {input_file}")
  
    # Check if all requested output files already exist when overwrite is disabled
    if not overwrite and media.srt_files_exist(input_file, output_file, languages, skip_original):
        return []

    # --- Vocal Isolation, Segmentation, Normalization and Transcription ---
    model = get_whisper_model()
    all_segments = list()
    original_texts = []
    outputs_to_generate = {}
    
    # Tuned VAD parameters for more stable speech segments.
    # min_silence_duration_ms: higher value (1000ms+) prevents cutting during natural phrasing pauses.
    # speech_pad_ms: reduced to 250ms for cleaner cuts without trailing silence.
    vad_parameters = dict(
        min_silence_duration_ms = 1000,
        speech_pad_ms = 250,
        min_speech_duration_ms = 300
    )

    print(f"--- Step 1: Isolating Vocals (Demucs) ---")
    with temporary_directory() as temp_dir:
        if skip_vocal_isolation:
            print("Skipping vocal isolation as requested.")
            transcription_file = input_file
        else:
            transcription_file = get_isolated_vocals(input_file, temp_dir = temp_dir)

        print(f"--- Step 2: Transcribing Isolated Vocals (Silero VAD) ---")
        #with Halo(text="Transcribing with Whisper, using Silero VAD...", color="green", spinner="dots"):
        print(transcription_file)
        segments_generator, info = model.transcribe(
            transcription_file, 
            beam_size = 5, 
            task = "transcribe", 
            vad_filter = True, 
            vad_parameters = vad_parameters,
            multilingual = True,
            condition_on_previous_text = False,
            word_timestamps = True
        )

        all_segments = list(segments_generator)

    if all_segments:
        print(f"First segment starts at: {all_segments[0].start:.2f}s and ends at {all_segments[0].end:.2f}s.")

    # Remove global language assignment to allow per-segment language detection in translation.py
    # for segment in all_segments:
    #     if not hasattr(segment, 'language'):
    #         segment.language = info.language
    
    original_texts = [segment.text for segment in all_segments]

    print(f"Segments generated: {len(original_texts)}. Total duration: {info.duration:.2f}s.")
    
    base_path = os.path.splitext(input_file)[0]
    output_base = os.path.splitext(output_file)[0] if output_file else base_path

    srt_path = output_base + ".srt"
    outputs_to_generate[srt_path] = original_texts

    # Translate if user provided target languages
    print(f"--- Step 3: Translating the transcribed vocals (Deep Translator) ---")
    with Halo(text="Translating segments...", color="magenta", spinner="dots"):
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

        output_paths = []
        for path, texts_to_write in outputs_to_generate.items():
            utils.write_srt(path, all_segments, texts_to_write)
            output_paths.append(path)
        
    print(f"\n--- Processing Finished ---")
    print(f"\nTotal time elapsed: {time.time() - start_total:.2f}s")
    return output_paths
