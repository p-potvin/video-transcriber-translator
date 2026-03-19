import argparse
import os
import subprocess
import time
from faster_whisper import WhisperModel


def format_time(seconds):
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    milliseconds = (seconds - int(seconds)) * 1000
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d},{int(milliseconds):03d}"

async def _translate_segments(
    texts,
    target_lang: str,
    translate_api="deep-translator",
    max_chars=350000,
    max_calls=250,
    translate_mode="all",
    detector=None, # Add detector as an argument
):
    if not texts:
        return []

    total_chars = sum(len(t) for t in texts)
    if total_chars > max_chars:
        raise RuntimeError(
            f"Translation skipped: text length {total_chars} > max_chars {max_chars}. "
            "Use --max-translate-chars to raise this limit or skip translation."
        )

    if translate_api == "deep-translator":
        try:
            from deep_translator import GoogleTranslator
            from googletrans import Translator as GoogleTrans_Detector
        except ImportError as exc:
            raise ImportError(
                "Missing deep-translator or googletrans. Install with: "
                "pip install deep-translator googletrans==4.0.0-rc1"
            ) from exc

        translated_texts = []
        calls = 0
        if detector is None: # Initialize detector only if not provided
            detector = GoogleTrans_Detector()

        if translate_mode == "non-target":
            for text in texts:                
                if calls > max_calls: 
                    raise RuntimeError("Translation request limit reached.")
                if not text.strip():
                    translated_texts.append(text)
                    continue
                
                detected_lang = await detector.detect(text).lang.lower().split("-")[0]
                calls += 1

                if detected_lang == target_lang.lower().split("-")[0]:
                    translated_texts.append(text)
                else:
                    calls += 1
                    if calls > max_calls: 
                        raise RuntimeError("Translation request limit reached.")
                    translated_texts.append(getattr(GoogleTranslator(source=detected_lang, target=target_lang).translate(text), "text", text))
            return translated_texts

        # "all" mode for deep-translator
        for text in texts:
            calls += 1
            if calls > max_calls: raise RuntimeError("Translation request limit reached.")
            if not text.strip():
                translated_texts.append(text)
                continue
            translated_texts.append(getattr(GoogleTranslator(source="auto", target=target_lang).translate(text), "text", text))
        return translated_texts

    else:
        raise ValueError(f"Unsupported translate API: {translate_api}")


def get_media_duration_seconds(input_file):
    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                input_file,
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        return float(result.stdout.strip())
    except Exception:
        return None


def extract_audio_to_wav(input_file, output_wav):
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-i",
            input_file,
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            output_wav,
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def isolate_vocals_with_demucs(input_audio, output_dir, device="cuda"):
    os.makedirs(output_dir, exist_ok=True)
    cmd = ["demucs", "--two-stems=vocals", "-o", output_dir, input_audio]
    if device == "cuda":
        cmd.insert(1, "-d")
        cmd.insert(2, "cuda")
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    vocals_path = None
    for root, _, files in os.walk(output_dir):
        for file in files:
            if file.endswith("vocals.wav"):
                vocals_path = os.path.join(root, file)
                break
        if vocals_path:
            break
    if not vocals_path:
        raise RuntimeError("Voice isolation with Demucs did not produce vocals.wav")
    return vocals_path

def write_srt(output_path, segments, texts):
    with open(output_path, "w", encoding="utf-8") as output_file:
        for segment, text in zip(segments, texts):
            start_time = format_time(segment.start)
            end_time = format_time(segment.end)
            segment_id = segment.id + 1
            line_out = f"{segment_id}\n{start_time} --> {end_time}\n{text.lstrip()}\n\n"
            output_file.write(line_out)


import threading

def transcribe_video(
    input_file,
    output_file=None,
    languages=None,
    skip_original=False,
    translate_api="deep-translator",
    translate_mode="non-target",
    max_translate_chars=350000,
    max_translate_calls=250,
    overwrite=True,
    vad_filter=True,
):
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
    model_size = "medium"
    model = WhisperModel(model_size, device="cuda", compute_type="int8_float16")

    print(f"Transcribing: {input_file} (VAD filter: {vad_filter})")
    start_ts = time.time()
    
    # Transcribe once to get segments and language info
    all_segments, info = model.transcribe(input_file, beam_size=5, task="transcribe", vad_filter=vad_filter)
    all_segments = list(all_segments)
    elapsed_total = time.time() - start_ts
    print(f"Detected language '{info.language}' with probability {info.language_probability:.2f}")
    print(f"Segments generated: {len(all_segments)}")
    print(f"Transcription elapsed: {elapsed_total:.1f}s")
    original_texts = [segment.text for segment in all_segments]

    # --- Step 2: Prepare output file paths and contents ---
    base_path = os.path.splitext(input_file)[0]
    output_base = os.path.splitext(output_file)[0] if output_file else base_path

    outputs_to_generate = {}

    if not skip_original:
        original_srt_path = output_base + ".srt"
        if not overwrite and os.path.exists(original_srt_path):
            print(f"Skipping {original_srt_path} (overwrite is off).")
            # If we skip original, we don't add it to outputs_to_generate.
            # The transcription has already happened at the beginning of the function, so original_texts is available for translation.
        else:
            path = output_base + ".srt"
            outputs_to_generate[path] = original_texts

    if languages:
        for lang_code in languages:
            lang_code = lang_code.strip().lower()
            if not lang_code or lang_code in ("orig", "original", "none"):
                continue

            path = f"{output_base}.{lang_code}.srt"
            
            is_target_lang_same_as_source = (lang_code == info.language) or \
                                            (lang_code.split('-')[0] == info.language.split('-')[0])

            if is_target_lang_same_as_source and translate_mode != "all":
                translated_texts = original_texts
            else:
                print(f"Translating to {lang_code}...")
                translated_texts = _translate_segments(
                    original_texts,
                    target_lang=lang_code,
                    translate_api=translate_api,
                    translate_mode=translate_mode,
                    max_chars=max_translate_chars,
                    max_calls=max_translate_calls,
                    detector=None
                )
            
            outputs_to_generate[path] = translated_texts
    
    # --- Step 3: Write all generated files ---
           
    if not outputs_to_generate:
        print("No new files to generate.")
        return []

    print(f"Writing {len(outputs_to_generate)} SRT file(s)...")
    output_paths = []
    for path, texts_to_write in outputs_to_generate.items():
        write_srt(path, all_segments, texts_to_write)
        output_paths.append(path)
        print(f"Wrote: {path}")
        
    return output_paths


def find_media_files(root_dir, extensions):
    ext_set = {ext.lower() for ext in extensions}
    for dirpath, _, files in os.walk(root_dir):
        for file_name in files:
            ext = os.path.splitext(file_name)[1].lower()
            if ext in ext_set:
                yield os.path.join(dirpath, file_name)


def print_progress(current, total, prefix="", width=30):
    ratio = current / total if total > 0 else 1
    filled = int(width * ratio)
    bar = "#" * filled + "-" * (width - filled)
    print(f"\r{prefix} [{bar}] {current}/{total}\r", end="", flush=True)
    if current >= total:
        print("", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Generate SRT for one video or scan a folder recursively.")
    parser.add_argument("input_file", nargs="?", help="Video/audio file path (if not scanning a folder)")
    parser.add_argument("--scan-dir", help="If set, recursively process all supported media files under this directory")
    parser.add_argument("--output-file", help="Output SRT file (for single file only)")
    parser.add_argument(
        "--languages",
        default="",
        help="Comma-separated target language codes for translation (e.g. en,es,fr). Generates <video>.<lang>.srt.",
    )
    parser.add_argument("--skip-original", action="store_true", help="Do not generate original-language SRT")
    parser.add_argument("--translate-api", default="deep-translator", help="Translator backend (googletrans or deep-translator)")
    parser.add_argument(
        "--translate-mode",
        choices=["all", "non-target"],
        default="non-target",
        help="all: translate all segments; non-target: only translate where detected src != target",
    )
    parser.add_argument("--max-translate-chars", type=int, default=350000, help="Max total chars per video before translation is skipped")
    parser.add_argument("--max-translate-calls", type=int, default=250, help="Max translator calls per video")
    parser.add_argument("--max-duration", type=float, default=3600, help="Max media duration in seconds to process (skip longer files)")
    parser.add_argument("--continue-on-error", action="store_true", help="For scan mode, continue to next file when one fails")
    parser.add_argument("--overwrite", action="store_true", dest="overwrite", default=False, help="Overwrite existing SRT files")
    parser.add_argument("--no-vad-filter", action="store_true", dest="vad_filter", default=False, help="Disable VAD filtering for more accurate timestamps (default is enabled).")
    parser.add_argument("--extensions", default=".mp4,.mkv,.avi,.mov,.flv,.webm,.mp3,.wav,.m4a", help="Comma-separated media extensions for scan mode",
    )

    args = parser.parse_args()
    languages = [lang.strip().lower() for lang in args.languages.split(",") if lang.strip()]

    if args.scan_dir:
        if not os.path.isdir(args.scan_dir):
            raise FileNotFoundError(f"Scan directory does not exist: {args.scan_dir}")

        media_exts = [ext.strip().lower() for ext in args.extensions.split(",") if ext.strip()]
        matched = list(find_media_files(args.scan_dir, media_exts))
        if not matched:
            print(f"No media files found under {args.scan_dir} with extensions {media_exts}")
            return

        print(f"Found {len(matched)} files. Processing recursively...")
        successes = []
        failures = []
        start_time = time.time()
        for idx, path in enumerate(matched, start=1):
            print_progress(idx, len(matched), prefix="Scan progress")
            if args.max_duration is not None:
                duration = get_media_duration_seconds(path)
                if duration is not None and duration > args.max_duration:
                    print(f"\nSkipping (too long > {args.max_duration}s): {path} ({duration:.1f}s)")
                    failures.append((path, f"duration {duration:.1f}s > max {args.max_duration}s"))
                    continue

            try:
                outputs = transcribe_video(
                    path,
                    output_file=None,
                    languages=languages,
                    skip_original=args.skip_original,
                    translate_api=args.translate_api,
                    translate_mode=args.translate_mode,
                    max_translate_chars=args.max_translate_chars,
                    max_translate_calls=args.max_translate_calls,
                    overwrite=args.overwrite,
                    vad_filter=args.vad_filter,
                )
                print(f"\nDone: {path} -> {len(outputs)} output files")
                successes.append(path)
            except Exception as exc:
                print(f"\nFailed for {path}: {exc}")
                failures.append((path, str(exc)))
                if not args.continue_on_error:
                    break

        elapsed = time.time() - start_time
        print("\nScan completed.")
        print(f"Success: {len(successes)} files")
        print(f"Failed: {len(failures)} files")
        if failures:
            for fail_path, reason in failures:
                print(f" - {fail_path}: {reason}")
        print(f"Total time: {elapsed:.1f}s")

    else:        
        transcribe_video(
            args.input_file,
            output_file=args.output_file,
            languages=languages,
            skip_original=args.skip_original,
            translate_api=args.translate_api,
            translate_mode=args.translate_mode,
            max_translate_chars=args.max_translate_chars,
            max_translate_calls=args.max_translate_calls,
            overwrite=args.overwrite,
            vad_filter=args.vad_filter,
        )


if __name__ == "__main__":
    main()
