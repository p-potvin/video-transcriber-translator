import asyncio
import time
from functools import lru_cache

class UnsupportedLanguageError(RuntimeError):
    pass

@lru_cache(maxsize=None)
def get_supported_language_codes(translate_api="local"):
    if translate_api not in {"local", "argos"}:
        raise ValueError(f"Unsupported translate API: {translate_api}")
    try:
        import argostranslate.package

        argostranslate.package.update_package_index()
        packages = argostranslate.package.get_available_packages()
        codes = set()
        for package in packages:
            codes.add(package.from_code)
            codes.add(package.to_code)
        return {code.strip().lower() for code in codes}
    except Exception:
        return set()

def is_supported_language_code(lang_code, translate_api="local", allow_auto=False):
    normalized_lang = str(lang_code or "").strip().lower()
    if not normalized_lang:
        return False
    if allow_auto and normalized_lang == "auto":
        return True
    try:
        supported = get_supported_language_codes(translate_api)
        return normalized_lang in supported
    except Exception:
        return True

def _get_argos_translator(source_lang, target_lang):
    import argostranslate.package
    import argostranslate.translate

    source_lang = "en" if source_lang == "auto" or not source_lang else source_lang

    if source_lang.lower() == target_lang.lower():
        class PassthroughTranslator:
            def translate(self, text):
                return text
        return PassthroughTranslator()

    # Try to find installed translation
    installed_languages = argostranslate.translate.get_installed_languages()
    source_lang_obj = next((lang for lang in installed_languages if lang.code == source_lang), None)
    target_lang_obj = next((lang for lang in installed_languages if lang.code == target_lang), None)

    if source_lang_obj and target_lang_obj:
        translation = source_lang_obj.get_translation(target_lang_obj)
        if translation:
            return translation

    # If not installed, try to download and install
    argostranslate.package.update_package_index()
    available_packages = argostranslate.package.get_available_packages()
    package_to_install = next(
        (pkg for pkg in available_packages if pkg.from_code == source_lang and pkg.to_code == target_lang),
        None
    )

    if package_to_install:
        print(f"Downloading translation package: {source_lang} -> {target_lang}...")
        argostranslate.package.install_from_path(package_to_install.download())

        installed_languages = argostranslate.translate.get_installed_languages()
        source_lang_obj = next((lang for lang in installed_languages if lang.code == source_lang), None)
        target_lang_obj = next((lang for lang in installed_languages if lang.code == target_lang), None)

        if source_lang_obj and target_lang_obj:
            translation = source_lang_obj.get_translation(target_lang_obj)
            if translation:
                return translation

    raise RuntimeError(f"Could not find or install translation package for {source_lang} -> {target_lang}")

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

    if translate_api not in {"local", "argos"}:
        raise ValueError(f"Unsupported translate API: {translate_api}")

    try:
        import argostranslate.package
        import argostranslate.translate
    except ImportError as exc:
        raise ImportError("Missing argostranslate. Install with: pip install argostranslate") from exc

    translated_texts = []
    calls = 0
    translators_cache = {}
    translated_texts = [s if is_list_of_strings else s.text for s in segments]

    indices_to_translate = []

    if translate_mode == "non-target":
        for i, segment in enumerate(segments):
            text = segment if is_list_of_strings else segment.text
            if not text.strip():
                continue
            if is_list_of_strings:
                indices_to_translate.append(i)
                continue
            current_lang = getattr(segment, "language", None) or "en"
            if current_lang.lower() != target_lang.lower():
                indices_to_translate.append(i)

        if not indices_to_translate:
            return translated_texts

        for idx in indices_to_translate:
            if calls >= max_calls:
                raise RuntimeError("Translation request limit reached.")

            text = translated_texts[idx]
            segment = segments[idx] if not is_list_of_strings else None
            source_lang = getattr(segment, "language", "en") if segment else "en"
            cache_key = f"{source_lang}_{target_lang}"
            if cache_key not in translators_cache:
                translators_cache[cache_key] = _get_argos_translator(source_lang, target_lang)

            try:
                translated_texts[idx] = translators_cache[cache_key].translate(text)
                calls += 1
            except Exception as exc:
                raise ValueError(
                    f"Error while translating segment {idx} with text '{text}': {exc}"
                ) from exc

        print(f"Local translation completed with {calls} calls.")
        return translated_texts

    if translate_mode != "all":
        raise ValueError(f"Unsupported translate mode: {translate_mode}")

    from tqdm import tqdm

    input_texts = [s if is_list_of_strings else s.text for s in segments]
    for i, text in enumerate(
        tqdm(input_texts, desc=f"Translating to {target_lang}", unit="segment", colour="blue")
    ):
        if calls >= max_calls:
            raise RuntimeError("Translation request limit reached.")
        if not text.strip():
            continue

        segment = segments[i] if not is_list_of_strings else None
        source_lang = getattr(segment, "language", "en") if segment else "en"
        cache_key = f"{source_lang}_{target_lang}"
        if cache_key not in translators_cache:
            translators_cache[cache_key] = _get_argos_translator(source_lang, target_lang)

        try:
            translated_texts[i] = translators_cache[cache_key].translate(text)
            calls += 1
        except Exception as exc:
            raise ValueError(
                f"Error while translating segment {i} with text '{text}': {exc}"
            ) from exc

    print(f"Local translation completed with {calls} calls.")
    return translated_texts
