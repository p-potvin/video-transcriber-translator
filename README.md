# faster-whisper-generate-srt-subtitles
Generate subtitles (SRT) from an audio/video file. It uses the `faster-whisper` library, which is much faster than OpenAI's original Whisper implementation.

It can also translate the generated subtitles into other languages.

The model `large-v2` has the best quality, while `medium` is a good compromise between quality and speed.

Read more about faster-whisper: https://github.com/guillaumekln/faster-whisper

## Usage

```bash
python generate-srt.py input.mp4
```

Translate to English (uses faster-whisper built-in translation):

```bash
python generate-srt.py input.mp4 --translate-to en
```

Translate to another language (e.g. Spanish):

```bash
python generate-srt.py input.mp4 --translate-to es
```

## Installation

Install the required dependencies using the provided requirements file:

```bash
pip install -r requirements.txt
```

> ⚠️ `googletrans` needs an internet connection to work (it uses Google Translate's web API).

