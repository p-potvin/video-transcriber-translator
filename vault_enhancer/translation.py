import asyncio
import time
import random
from functools import lru_cache
import inspect

class UnsupportedLanguageError(RuntimeError):
    pass

@lru_cache(maxsize=None)
def get_supported_language_codes(translate_api="argos"):
    if translate_api == "argos":
        try:
            import argostranslate.package
            import argostranslate.translate

            argostranslate.package.update_package_index()
            available_packages = argostranslate.package.get_available_packages()

            codes = set()
            for pkg in available_packages:
                codes.add(pkg.to_code)
                codes.add(pkg.from_code)

            return {code.lower() for code in codes}
        except Exception:
            return set()
    raise ValueError(f"Unsupported translate API: {translate_api}")

def is_supported_language_code(lang_code, translate_api="argos", allow_auto=False):
    normalized_lang = str(lang_code or "").strip().lower()
    if not normalized_lang:
        return False
    if allow_auto and normalized_lang == "auto":
        return True
    return normalized_lang in get_supported_language_codes(translate_api)

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
    translate_api="argos",
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

    if translate_api == "argos":
        try:
            import argostranslate.package
            import argostranslate.translate
        except ImportError as exc:
            raise ImportError(
                "Missing argostranslate. Install with: pip install argostranslate"
            ) from exc

        translated_texts = []
        calls = 0

        # We'll need a translator per source language. For strings we assume "auto" -> "en"
        translators_cache = {}

        if translate_mode == "non-target":            
            indices_to_translate = []
            
            for i, s in enumerate(segments):
                text = s if is_list_of_strings else s.text
                if not text.strip():
                    continue
                
                if is_list_of_strings:
                    indices_to_translate.append(i)
                else:
                    current_lang = getattr(s, 'language', None) or "en"
                    if current_lang.lower() != target_lang.lower():
                        indices_to_translate.append(i)

            if not indices_to_translate:
                return [s if is_list_of_strings else s.text for s in segments]

            translated_texts = [s if is_list_of_strings else s.text for s in segments]
            
            for idx in indices_to_translate:
                if calls > max_calls: 
                    raise RuntimeError("Translation request limit reached.")
                
                text = translated_texts[idx]
                segment = segments[idx] if not is_list_of_strings else None
                source_lang = getattr(segment, 'language', "en") if segment else "en"

                cache_key = f"{source_lang}_{target_lang}"
                if cache_key not in translators_cache:
                    translators_cache[cache_key] = _get_argos_translator(source_lang, target_lang)
                
                try:                    
                    translator = translators_cache[cache_key]
                    translated_texts[idx] = translator.translate(text)
                    calls += 1
                except Exception as exc:
                    raise ValueError(
                        f"Error while translating segment {idx} with text '{text}': {exc}"
                    ) from exc
            
            print(f"Translation completed with {calls} calls.")
            return translated_texts

        # "all" mode
        from tqdm import tqdm
        input_texts = [s if is_list_of_strings else s.text for s in segments]
        for i, text in enumerate(tqdm(input_texts, desc=f"Translating to {target_lang}", unit="segment", colour="blue")):
            calls += 1
            if calls > max_calls: raise RuntimeError("Translation request limit reached.")
            if not text.strip():
                translated_texts.append(text)
                continue
            
            tqdm.write(f"Translating segment {i}: '{text}'")

            segment = segments[i] if not is_list_of_strings else None
            source_lang = getattr(segment, 'language', "en") if segment else "en"

            cache_key = f"{source_lang}_{target_lang}"
            if cache_key not in translators_cache:
                translators_cache[cache_key] = _get_argos_translator(source_lang, target_lang)

            translator = translators_cache[cache_key]
            result = translator.translate(text)
            translated_texts.append(result)

        return translated_texts

    else:
        raise ValueError(f"Unsupported translate API: {translate_api}")
