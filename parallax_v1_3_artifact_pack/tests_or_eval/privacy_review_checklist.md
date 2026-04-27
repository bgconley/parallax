# Privacy Review Checklist

- Raw notes are not logged.
- Transcripts are not logged.
- Audio retention defaults off.
- Cloud model fallback defaults off.
- Sensitive/private notes are not embedded by default.
- Raw quotes in query answers are opt-in.
- Context capture policy disables optional sensor capture by default.
- OS permission grant does not bypass backend context policy.
- Raw coordinates and radio identifiers are retained only when policy allows it.
- Radio `redacted_display_label` never contains raw SSID, BSSID, MAC, beacon, UWB peer, or cell identifiers.
- Location, radio, place, and context-feature delete scopes invalidate derived retrieval documents, evidence, and feature vectors.
- Export workflow includes source and derived data.
- Delete/redact workflow removes retrieval documents and embeddings.
- Backups have documented retention implications.
- Cross-user isolation tests pass.
