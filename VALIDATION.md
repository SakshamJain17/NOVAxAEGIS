# Validation record

Build environment: Linux x64, Node.js 24.19.0.

- `npm test`: 16 tests passed; zero failures. Includes policy enforcement, approval replay/expiry/turn binding, cancelled model/tool/audio isolation, PCM byte-boundary handling, pending-playback cancellation, WAV encoding, provider contract fixtures, and browser/desktop core parity.
- JavaScript syntax checks: passed for renderer, voice capture/playback, runtime, and Electron main.
- Static validation: HTML IDs, referenced UI selectors, module imports, and local asset references passed.
- Electron dependency: 44.2.0. Electron builder: 26.15.3.
- `npm run package`: produces a Linux x64 unpacked desktop application. Packaging is not equivalent to a GUI or microphone test.
- `npm run preflight`: exited with the expected explicit missing `RIME_API_KEY` message. No live Rime synthesis, Ollama, or microphone test was possible.
- No browser visual testing, desktop GUI session, signed installers, macOS/Windows package validation, or acoustic measurements were performed.

RIME_EVIDENCE.md defines the live acceptance procedure and explicitly marks unverified claims.
