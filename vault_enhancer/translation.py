import asyncio
import time
from functools import lru_cache

class UnsupportedLanguageError(RuntimeError):
    pass

@lru_cache(maxsize=None)
def get_supported_language_codes(translate_api="local"):
    import argostranslate.package
    argostranslate.package.update_package_index()
    packages = argostranslate.package.get_available_packages()
    # We just need to know which targets are available from ANY source
    targets = {pkg.to_code.strip().lower() for pkg in packages}
    targets.add("en") # Usually English is supported as target
    return targets

def is_supported_language_code(lang_code, translate_api="local", allow_auto=False):
    normalized_lang = str(lang_code or "").strip().lower()
    if not normalized_lang:
        return False
    if allow_auto and normalized_lang == "auto":
        return True
    try:
        supported = get_supported_language_codes()
        return normalized_lang in supported
    except Exception:
        # If we can't fetch the index, allow it and let it fail later
        return True

async def translate_segments(
    segments,
    target_lang: str,
    translate_api="local",
    max_chars=750000,
    max_calls=1000,
    translate_mode="non-target",
    detector=None,
):
    if not segments:
        return []

    is_list_of_strings = all(isinstance(s, str) for s in segments)
    
    total_chars = sum(len(s if is_list_of_strings else s.text) for s in segments)
    if total_chars > max_chars:
        raise RuntimeError(
            f"Translation skipped: text length {total_chars} > max_chars {max_chars}. "
            "Use --max-translate-chars to raise this limit or skip translation."
        )

    try:
        import argostranslate.package
        import argostranslate.translate
    except ImportError as exc:
        raise ImportError("Missing argostranslate. Install with: pip install argostranslate") from exc

    # Download required language packages
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()

    # We will assume 'en' as source if not provided by segment language
    # Argos requires a specific source->target package to be installed.
    # To keep it simple, we translate segment by segment and check if we have the package.

    translated_texts = []
    calls = 0

    indices_to_translate = []

    for i, s in enumerate(segments):
        text = s if is_list_of_strings else s.text
        if not text.strip():
            continue

        if is_list_of_strings:
            indices_to_translate.append((i, "en")) # Fallback source
        else:
            current_lang = getattr(s, 'language', None) or "en"
            if current_lang.lower() != target_lang.lower() or translate_mode == "all":
                indices_to_translate.append((i, current_lang.lower()))

    if not indices_to_translate:
        return [s if is_list_of_strings else s.text for s in segments]

    translated_texts = [s if is_list_of_strings else s.text for s in segments]

    installed_packages = argostranslate.package.get_installed_packages()
    installed_pairs = {(pkg.from_code, pkg.to_code) for pkg in installed_packages}

    for idx, source_lang in indices_to_translate:
        if calls > max_calls:
            raise RuntimeError("Translation request limit reached.")

        text = translated_texts[idx]

        # Ensure package is installed
        if (source_lang, target_lang) not in installed_pairs:
            package_to_install = next(
                filter(
                    lambda x: x.from_code == source_lang and x.to_code == target_lang, available_packages
                ), None
            )
            if package_to_install:
                print(f"Downloading translation package: {source_lang} -> {target_lang}")
                argostranslate.package.install_from_path(package_to_install.download())
                installed_pairs.add((source_lang, target_lang))
            else:
                # If direct translation is not available, maybe via English?
                # For simplicity, if not available, we skip
                print(f"No translation package available from {source_lang} to {target_lang}. Skipping segment.")
                continue

        try:
            translation = argostranslate.translate.translate(text, source_lang, target_lang)
            translated_texts[idx] = translation
            calls += 1
        except Exception as exc:
            print(f"Error while translating segment {idx} with text '{text}': {exc}")

    print(f"Local translation completed with {calls} calls.")
    return translated_texts
