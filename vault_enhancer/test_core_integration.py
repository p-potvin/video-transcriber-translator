import os
import unittest
from unittest.mock import patch, MagicMock
from vault_enhancer import core
from vault_enhancer.parakeet_wrapper import TranscriptSegment

class TestCoreIntegration(unittest.TestCase):
    @patch("vault_enhancer.media.fix_audio_and_reencode")
    @patch("vault_enhancer.media.extract_wav_for_asr")
    def test_transcribe_video_mocked(self, mock_extract, mock_fix):
        mock_fix.return_value = "dummy_video.mp4"
        mock_extract.return_value = "dummy_video.mp4"

        mock_segments = [TranscriptSegment(1, 0.0, 1.0, "Hello world")]

        mock_transcriber = MagicMock()
        mock_transcriber.transcribe_file.return_value = mock_segments

        input_file = "dummy_video.mp4"
        output_file = "dummy_video.srt"

        # Create a dummy file to pass os.path.isfile check
        with open(input_file, "w") as f:
            f.write("dummy content")

        try:
            with patch("vault_enhancer.core.get_parakeet_model", return_value=mock_transcriber):
                outputs = core.transcribe_video(
                    input_file,
                    output_file=output_file,
                    skip_vocal_isolation=True,
                    overwrite=True,
                    engine="parakeet"
                )

            self.assertEqual(len(outputs), 2)
            self.assertTrue(os.path.exists(output_file))

            with open(output_file, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("Hello world", content)

        finally:
            if os.path.exists(input_file):
                os.remove(input_file)
            if os.path.exists(output_file):
                os.remove(output_file)
            en_file = output_file.replace(".srt", ".en.srt")
            if os.path.exists(en_file):
                os.remove(en_file)

if __name__ == "__main__":
    unittest.main()
