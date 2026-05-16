## 🛡️-05-10 - Secure Model Loading Pattern
**Vulnerability:** Loading AI models based on unchecked user input can lead to arbitrary code execution or path traversal, especially if the engine name is used to construct a module path dynamically.
**Learning:** In the `vault_enhancer/core.py` integration, instead of dynamically importing based on the user-provided string, an explicit conditional `if engine == "whisper"` was used to call specific, hardcoded loader functions (`get_whisper_model()` vs `get_parakeet_model()`).
**Prevention:** Always use explicit allowlists or hardcoded conditional mapping when translating external user inputs (like `--engine whisper`) into internal system executions or module loading.
