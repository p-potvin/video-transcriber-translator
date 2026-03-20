import sys, types, asyncio

# Mock deep_translator and its exceptions
deep = types.ModuleType("deep_translator")
class FakeGoogleTranslator:
    def __init__(self, source="auto", target="en"):
        self.source = source
        self.target = target
    def translate(self, text):
        # Simple transform to show translation happened
        return f"<{self.source}->{self.target}>{text[::-1]}"
    def get_supported_languages(self, as_dict=False):
        # Provide a minimal supported languages mapping
        return {"en": "english", "es": "spanish"} if as_dict else ["english", "spanish"]
deep.GoogleTranslator = FakeGoogleTranslator
sys.modules["deep_translator"] = deep

# Mock deep_translator.exceptions
deep_ex = types.ModuleType("deep_translator.exceptions")
class LanguageNotSupportedException(Exception):
    pass
deep_ex.LanguageNotSupportedException = LanguageNotSupportedException
sys.modules["deep_translator.exceptions"] = deep_ex

# Mock googletrans
googletrans = types.ModuleType("googletrans")
class FakeDetected:
    def __init__(self, lang):
        self.lang = lang
class FakeDetector:
    def detect(self, text):
        text_l = text.lower()
        if "hola" in text_l or "spanish" in text_l:
            return FakeDetected("es")
        return FakeDetected("en")
googletrans.Translator = FakeDetector
sys.modules["googletrans"] = googletrans

# Now import the project's translation module and run a test
from video_transcriber import translation

texts = ["Hello world", "Hola spanish amigos"]
print("Input texts:", texts)
res = asyncio.run(translation.translate_segments(
    texts,
    target_lang="es",
    translate_api="deep-translator",
    translate_mode="non-target",
    max_chars=10000,
    max_calls=10,
    detector=None
))
print("Translated:", res)
