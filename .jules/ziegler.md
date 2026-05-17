## 🛡️-10-24 - Unauthenticated Local API Interaction
**Vulnerability:** Translation and transcription APIs operate completely on-device without any requirement to authenticate.
**Learning:** This is by-design since it runs 100% locally to prevent data exfiltration according to privacy-first design.
**Prevention:** Must ensure future changes don't accidentally expose these APIs via network interfaces.
## 🛡️-2026-05-18 - [Local Processing Violation]
**Vulnerability:** The application claims "100% Local Processing" in README but `translation.py` uses `deep-translator` and `googletrans` which send transcribed audio text to external Google servers.
**Learning:** Third-party dependency defaults (like external APIs for translation) can silently violate core privacy constraints if not rigorously audited against project claims.
**Prevention:** Always verify that libraries promising "translation" or "analysis" execute entirely offline when local processing is a hard constraint.
