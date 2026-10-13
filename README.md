# mem0

A focused extraction of Hermes memory/session primitives for reuse.

Files included:
- memory_store.py: MemoryStore implementation (file-backed, batch semantics)
- memory_provider.py: MemoryProvider ABC + context helpers
- memory_tool.py: small invocation wrapper exemplifying the tool path
- utils.py: atomic write helper
- constants.py: app home helper (configurable)
- threat_patterns.py: simple threat-scan stub
- example_provider/__init__.py: example provider scaffold

This repo is intended as a starting point for integration — adapt the
helpers (app home, threat scanning, and locking) to your environment.
