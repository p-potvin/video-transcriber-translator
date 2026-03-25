from ast import Tuple
import os
import tempfile
import time
import shutil
from typing import Iterable
from tqdm import tqdm
from contextlib import contextmanager
from faster_whisper import WhisperModel
from video_transcriber import utils
from video_transcriber import translation
from video_transcriber import media
from pydub import AudioSegment
from pydub.silence import split_on_silence

_WHISPER_MODEL = None

@contextmanager
def temporary_directory(prefix="transcriber_"):
    temp_dir = tempfile.mkdtemp(prefix=prefix)
    try:
        yield temp_dir
    finally:
        if os.path.exists(temp_dir):
            try:
                shutil.rmtree(temp_dir)
            except Exception as e:
                print(f"Warning: Failed to clean up temp directory {temp_dir}: {e}")

def get_whisper_model():
    global _WHISPER_MODEL
    if _WHISPER_MODEL is None:
        _WHISPER_MODEL = WhisperModel("medium", device="cuda", compute_type="int8_float16")
    return _WHISPER_MODEL

def transcribe_video(
    input_file,
    output_file=None,
    languages=None,
    skip_original=False,
    translate_api="deep-translator",
    translate_mode="non-target",
    max_translate_chars=350000,
    max_translate_calls=500,
    overwrite=False,
    vad_filter=True,
    vad_threshold=None,
    isolate_vocals=True,
    source_language=None,
):
    start_total = time.time()
    # Validate input file
    if not os.path.isfile(input_file):
        if os.path.isdir(input_file):
            raise ValueError(f"Input path is a directory, not a file: {input_file}")
        else:
            raise FileNotFoundError(f"Input file does not exist: {input_file}")
  
    # Check if all requested output files already exist when overwrite is disabled
    if not overwrite:
        base_path = os.path.splitext(input_file)[0]
        output_base = os.path.splitext(output_file)[0] if output_file else base_path
        
        check_paths = []
        if not skip_original:
            check_paths.append(output_base + ".srt")
        if languages:
            for lang in languages:
                lang_code = lang.strip().lower()
                if lang_code and lang_code not in ("orig", "original", "none"):
                    check_paths.append(f"{output_base}.{lang_code}.srt")
        
        if check_paths and all(os.path.exists(p) for p in check_paths):
            print(f"All requested SRT files already exist, skipping: {input_file}")
            return []

    # --- Step 1: Transcribe ---
    model = get_whisper_model()
    all_segments = list()
    segment_tuples = []  # To hold (segment, info) pairs for all segments across chunks
    original_texts = []  # To hold the original texts in order for translation and output
    
    # Dynamic VAD threshold detection and Audio Isolation
    transcription_file = input_file
    
    if isolate_vocals:
        with temporary_directory(prefix="demucs_") as temp_dir:
            print(f"--- Step 1: Vocal Isolation ---")
            print(f"Isolating vocals with Demucs to remove background noise (GPU acceleration enabled)...")
            start_step = time.time()
            try:               

                # Load audio
                audio = AudioSegment.from_file(transcription_file)

                # Split where silence > 800ms and quieter than -40dBFS
                chunks = split_on_silence(
                    audio,
                    min_silence_len=1000,
                    silence_thresh=-30
                )

                print(f"Audio split into {len(chunks)} chunks based on silence detection.")
                
                start_ts = time.time()

                vad_params = dict(threshold=vad_threshold) if vad_threshold is not None else dict(threshold=0.35)

                # Export chunks (e.g., only if > 1s)
                chunksPath = os.path.join(temp_dir, "chunks")
                os.makedirs(chunksPath, exist_ok=True)
                for i, chunk in enumerate(chunks):
                    if len(chunk) >= 1000: 
                        chunkName = os.path.join(chunksPath, f"chunk{i}.wav")
                        chunk.export(chunkName, format="wav")

                print(f"Audio chunks exported. Starting vocal isolation and transcription for each chunk...")
                
                # Get only the chunk files we just exported (not directories or isolated outputs)
                chunk_files = sorted(
                    [f for f in os.listdir(chunksPath) if f.startswith("chunk") and f.endswith(".wav")], 
                    key=lambda x: int(''.join(filter(str.isdigit, x)) or 0)
                )
                print(f"Found {len(chunk_files)} chunk files to process: {chunk_files}")

                current_time_offset = 0.0
                for file in chunk_files:
                    print(f"Processing chunk: {file}...")
                    chunkName = os.path.join(chunksPath, file)
                    
                    # Isolate vocals for this chunk
                    isolatedChunk = media.isolate_vocals_with_demucs(chunkName, chunksPath, device="cuda")
                    
                    print(f"Vocal isolation completed for {isolatedChunk}. Starting transcription...")
                    # Transcribe the isolated chunk
                    segments_generator, info = model.transcribe(
                        isolatedChunk, 
                        beam_size=5, 
                        task="transcribe", 
                        vad_filter=vad_filter,
                        vad_parameters=vad_params if vad_filter else None,
                        language=None, 
                        condition_on_previous_text=False,
                        word_timestamps=True,
                    )
                    
                    # Consume the generator into a list to allow multiple iterations and check content
                    chunk_segments = list(segments_generator)
                    print(f"Transcription generated {len(chunk_segments)} segments for this chunk.")

                    # Offset the segment timestamps by the current total duration
                    # and collect them into a single list
                    for segment in chunk_segments:
                        # Adjust start/end times relative to the original video
                        # faster-whisper segments are namedtuples, but we need to create objects 
                        # that behave like them for the SRT writer.
                        # We use a simple dictionary-like object or manual attribute assignment 
                        # if the namedtuple _replace is giving issues in this environment.
                        
                        start_time = segment.start + current_time_offset
                        end_time = segment.end + current_time_offset
                        
                        # Use a dictionary or a SimpleNamespace to ensure attributes are accessible via .start/.end
                        from types import SimpleNamespace
                        updated_segment = SimpleNamespace(
                            id = segment.id,
                            start=start_time,
                            end=end_time,
                            text=segment.text,
                            words=segment.words,
                            tokens=segment.tokens,
                            avg_logprob=segment.avg_logprob,
                            no_speech_prob=segment.no_speech_prob
                        )
                        
                        all_segments.append(updated_segment)
                        original_texts.append(updated_segment.text)
                    
                    # Increment offset by the actual length of the chunk from AudioSegment
                    # to keep timings accurate
                    current_chunk_audio = AudioSegment.from_file(chunkName)
                    current_time_offset += len(current_chunk_audio) / 1000.0
                    
                    print(f"Chunk processed. Total segments so far: {len(all_segments)}")

                print(f"Vocal isolation and transcription completed in {time.time() - start_step:.2f}s")
            except Exception as e:
                print(f"Warning: Vocal isolation failed: {e}. Falling back to original audio.")
                transcription_file = input_file

                # Fallback to standard transcription if chunking/isolation failed
                print(f"--- Transcription (Fallback) ---")
                vad_params = dict(threshold=vad_threshold) if vad_threshold is not None else dict(threshold=0.35)
                segments, info = model.transcribe(
                    transcription_file, 
                    beam_size=5, 
                    task="transcribe", 
                    vad_filter=vad_filter,
                    vad_parameters=vad_params if vad_filter else None,
                    language=None, 
                    word_timestamps=True,
                )
                all_segments = list(segments)
                original_texts = [s.text for s in all_segments]

            print(f"--- Finalizing Transcription ---")
            print(f"Segments generated: {len(all_segments)}")
    else:
        print(f"--- Step 2: Transcription (Step 1 Skipped) ---")
        print(f"Transcribing: {input_file} (VAD filter: {vad_filter}, threshold: {vad_threshold})")
        start_ts = time.time()
        
        vad_params = dict(threshold=vad_threshold) if vad_threshold is not None else dict(threshold=0.35)

        # --- Transcribe exactly as is (no translation at this step) ---
        print("Running transcribing exactly as is...")
        all_segments, info = model.transcribe(
            transcription_file, 
            beam_size=5, 
            task="transcribe", 
            vad_filter=vad_filter,
            vad_parameters=vad_params if vad_filter else None,
            language=None, # Auto-detect per segment
            word_timestamps=True,  # Crucial for precise SRT timing
            initial_prompt="I am transcribing as-is clear dialogue, in its original language. There may be many languages spoken and they must remain in their original language.", # Guide the model
            condition_on_previous_text=False, # Prevents repetitive hallucinations
            compression_ratio_threshold=2.4, # standard fallback trigger
            log_prob_threshold=-1.0,         # standard fallback trigger
            no_speech_threshold=0.6          # filter out silence properly
        )
        
        all_segments = list(all_segments)
        elapsed_total = time.time() - start_ts
        print(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")
        print(f"Segments generated: {len(all_segments)}")
        print(f"Transcription completed in {elapsed_total:.2f}s")
        original_texts = [segment.text for segment in all_segments]

    # --- Step 2: Prepare output file paths and contents ---
    base_path = os.path.splitext(input_file)[0]
    output_base = os.path.splitext(output_file)[0] if output_file else base_path

    outputs_to_generate = {}

    if not skip_original:
        original_srt_path = output_base + ".srt"
        if not overwrite and os.path.exists(original_srt_path):
            print(f"Skipping {original_srt_path} (overwrite is off).")
        else:
            path = output_base + ".srt"
            outputs_to_generate[path] = original_texts

    # Translate only if needed
    if languages:
        source_lang = str(getattr(info, "language", "") or "").strip().lower()
        source_lang_supported = translation.is_supported_language_code(source_lang, translate_api=translate_api)
        
        # We need to process the language list from the user properly
        # Default should include 'en' if no languages were provided
        target_languages = languages if isinstance(languages, list) else [l.strip() for l in str(languages).split(",") if l.strip()]
        
        for lang_code in target_languages:
            lang_code = lang_code.strip().lower()
            if not lang_code or lang_code in ("orig", "original", "none"):
                continue

            path = f"{output_base}.{lang_code}.srt"
            
            # --- FIXED LOGIC ---
            # We treat the original text as 'multilingual' (as transcribed).
            # We only generate a translation if we have non-target segments to translate.
            # If the whole video is ALREADY in the target language, we could just copy it,
            # but usually, users want the translation step to handle mixed languages.
            
            print(f"--- Step 3: Translation ({lang_code}) ---")
            print(f"Translating segments not in '{lang_code}' to '{lang_code}'...")
            import asyncio
            trans_start_ts = time.time()
            try:
                # 'non-target' mode in translation module correctly identifies 
                # segments that don't match lang_code and translates only those.
                translated_texts = asyncio.run(translation.translate_segments(
                    original_texts,
                    target_lang=lang_code,
                    translate_api=translate_api,
                    translate_mode=translate_mode,
                    max_chars=max_translate_chars,
                    max_calls=max_translate_calls,
                    detector=None
                ))
                trans_elapsed = time.time() - trans_start_ts
                print(f"Translation to {lang_code} completed in {trans_elapsed:.2f}s")
            except translation.UnsupportedLanguageError as exc:
                print(f"Skipping translation to {lang_code}: {exc}")
                continue
            except Exception as exc:
                print(f"Exception translating to {lang_code}: {exc}")
                continue
            
            outputs_to_generate[path] = translated_texts
    
    # --- Step 3: Write all generated files ---
           
    if not outputs_to_generate:
        print("No new files to generate.")
        return []

    print(f"Writing {len(outputs_to_generate)} SRT file(s)...")
    output_paths = []
    for path, texts_to_write in tqdm(outputs_to_generate.items(), desc="Saving SRTs", unit="file"):
        utils.write_srt(path, all_segments, texts_to_write)
        output_paths.append(path)
        print(f"Wrote: {path}")
        
    print(f"\n--- Processing Finished ---")
    print(f"Total time elapsed: {time.time() - start_total:.2f}s")
    return output_paths
