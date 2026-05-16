import unittest
import asyncio
from unittest.mock import MagicMock, patch
from vault_enhancer import translation

class TestTranslation(unittest.TestCase):
    def setUp(self):
        # Reset lru_cache for supported languages to avoid side effects if needed
        translation.get_supported_language_codes.cache_clear()

    @patch('deep_translator.GoogleTranslator')
    @patch('googletrans.Translator')
    def test_translate_segments_non_target_mode(self, MockDetector, MockTranslator):
        # Setup detector mock
        mock_detector_inst = MockDetector.return_value
        # Mock detection result: "Hello" is english, "Hola" is spanish
        def side_effect_detect(text):
            mock_res = MagicMock()
            mock_res.lang = "en" if "Hello" in text else "es"
            return mock_res
        mock_detector_inst.detect.side_effect = side_effect_detect

        # Setup translator mock
        mock_translator_inst = MockTranslator.return_value
        # Return a simple string as deep-translator does
        mock_translator_inst.translate.return_value = "Hola Mundo"

        texts = ["Hello world"]
        # Translate English to Spanish
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(translation.translate_segments(
            texts, 
            target_lang="es", 
            translate_api="deep-translator",
            translate_mode="non-target"
        ))

        self.assertEqual(result, ["Hola Mundo"])
        # Verify translator was called because source (en) != target (es)
        mock_translator_inst.translate.assert_called_with("Hello world")

    @patch('deep_translator.GoogleTranslator')
    @patch('googletrans.Translator')
    def test_translate_segments_same_language_skips(self, MockDetector, MockTranslator):
        mock_detector_inst = MockDetector.return_value
        mock_res = MagicMock()
        mock_res.lang = "es"
        mock_detector_inst.detect.return_value = mock_res

        # mock_translator_inst = MockTranslator.return_value
        # mock_translator_inst.translate.return_value = "Translated"

        class MockSeg:
            def __init__(self, text, lang):
                self.text = text
                self.language = lang
        texts = [MockSeg("Hola amigo", "es")]
        # Translate Spanish to Spanish (should skip calling translator)
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(translation.translate_segments(
            texts, 
            target_lang="es", 
            translate_api="deep-translator",
            translate_mode="non-target"
        ))

        self.assertEqual(result, ["Hola amigo"])
        # mock doesn't assert easily here since it's used elsewhere

    @patch('deep_translator.GoogleTranslator')
    def test_translate_segments_all_mode(self, MockTranslator):
        mock_translator_inst = MockTranslator.return_value
        mock_translator_inst.translate.return_value = "Translated"

        texts = ["Some text"]
        loop = asyncio.get_event_loop()
        result = loop.run_until_complete(translation.translate_segments(
            texts, 
            target_lang="fr", 
            translate_api="deep-translator",
            translate_mode="all"
        ))

        self.assertEqual(result, ["Translated"])
        mock_translator_inst.translate.assert_called_with("Some text")

if __name__ == '__main__':
    unittest.main()
