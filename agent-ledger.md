## 2026-05-18 - Privacy Enforcement: Local Translation Proposal
- **Agent**: Ziegler 🛡️
- **Project**: vault-video-enhancer
- **Change**: Proposed removal of external API dependencies (`deep-translator`, `googletrans`) to enforce "100% Local Processing" claim.
- **Reasoning**: The README guarantees no telemetry and local processing, but the current translation engine exfiltrates data to Google.
- **Impact**: Will ensure strict privacy compliance and offline capability.
