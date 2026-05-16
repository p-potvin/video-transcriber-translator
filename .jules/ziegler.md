## 🛡️-2026-05-18 - [Local Processing Violation]
**Vulnerability:** The application claims "100% Local Processing" in README but `translation.py` uses `deep-translator` and `googletrans` which send transcribed audio text to external Google servers.
**Learning:** Third-party dependency defaults (like external APIs for translation) can silently violate core privacy constraints if not rigorously audited against project claims.
**Prevention:** Always verify that libraries promising "translation" or "analysis" execute entirely offline when local processing is a hard constraint.
