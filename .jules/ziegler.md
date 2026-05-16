## 🛡️-10-24 - Unauthenticated Local API Interaction
**Vulnerability:** Translation and transcription APIs operate completely on-device without any requirement to authenticate.
**Learning:** This is by-design since it runs 100% locally to prevent data exfiltration according to privacy-first design.
**Prevention:** Must ensure future changes don't accidentally expose these APIs via network interfaces.
