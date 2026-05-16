## 🛡️-05-10 - Stack Trace Leakage in GUI Worker
**Vulnerability:** The `vault_gui.py` TranscriptionWorker catches generic exceptions and emits the full stack trace (`traceback.format_exc()`) to the UI, exposing internal application state.
**Learning:** This existed because GUI error dialogs often try to be helpful by dumping the full error, but this violates the principle of secure error messages.
**Prevention:** Implement secure error messages that log the stack trace internally but only return a sanitized error message to the UI or client.
