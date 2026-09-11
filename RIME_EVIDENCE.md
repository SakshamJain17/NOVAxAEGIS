# Rime evidence — NOVA × AEGIS

## User and voice necessity

A researcher working hands-busy recalls project context and captures ideas by speaking. Spoken retrieval and redirection are the default desktop voice-session flow. Rime delivers answers and approval explanations throughout the session. Removing speech removes hands-free retrieval and conversational interruption; the remaining text controls are a recovery path and an inspectable interface.

## Selected hard voice problem

Interruption and recovery during speech and memory lookup. Stop scheduled audio and queued synthesis, cancel/fence old model and tool results, and accept the corrected request without treating unheard output as confirmed context.

## Acceptance test defined before live demo

Use a headset and synchronized recordings of microphone input and loopback output. Run ten trials: five while NOVA is speaking and five while a memory lookup is delayed by five seconds. For each trial:

1. Say “Search my memory for voice.”
2. During response audio or the delayed lookup, say “Wait, search for AEGIS instead.”
3. Require old speech to stop within 300 ms of annotated interruption onset in at least nine of ten trials. This is a target, not an achieved measurement.
4. Require zero obsolete answers/audio after the corrected turn, in all ten trials.
5. Require the next spoken answer to answer the corrected request, in all ten trials.
6. Confirm no unapproved memory writes. Verify old pending approvals are invalidated.

Run the normal flow without a delay first. For tool-delay trials, set `NOVA_TEST_TOOL_DELAY_MS=5000` in your environment before `npm start`. This delays every memory tool, including the corrected request; it does not delay input or cancellation. Restore it to zero afterward. Check the active provider badge says Rime live during playback.

## Reproduction commands

```sh
npm ci
npm test
npm run preflight
npm start
```

Use the Connections screen to confirm the Ollama model and catalog tuple. Use a local loopback recorder to capture Rime output separately from the microphone. Annotate the interruption onset from the synchronized microphone track. Export output as 16-bit PCM WAV, then:

```sh
python scripts/measure-interruption.py output.wav --onset 4.25
```

Replace 4.25 with the measured onset, not a button-click timestamp. Inspect the recording and transcript to distinguish an interruption from a natural pause. Store per-trial WAVs, annotations, output JSON, hardware/audio configuration, app commit, and exported audit in `artifacts/` locally. Use synthetic task content; review before explicitly publishing evidence.

## Implemented mechanisms

- Continuous audio capture during playback and tool work, echo cancellation requested.
- Energy VAD detects speech onset; local playback sources are stopped and generation invalidated.
- AbortControllers cancel model, speech, transcription, and delayed-tool work.
- Turn IDs fence callbacks even when a provider does not honor cancellation.
- Rime raw PCM is reassembled across odd byte boundaries, queued in Web Audio, and discarded on interruption.
- Pending approvals are cleared. Exact approved payloads cannot be replayed.
- Full playback completion is acknowledged; interrupted output is marked as potentially unheard.

## Results from this build

Automated checks: run `npm test` for the recorded assertions. These cover application state and mocked provider contracts, not acoustic performance. Build validation details are in VALIDATION.md.

Live Rime synthesis: NOT RUN — no credential supplied.
Live model/speaker/language tuple: documentation-matched defaults, live preflight pending.
Live Qwen + microphone session: NOT RUN — user's local services and audio hardware unavailable.
Acoustic stop time and end-to-end latency: NOT MEASURED.
Full-duplex user acceptance: NOT VERIFIED.
Organizer secret/config preflight: NOT PROVIDED / NOT RUN.
Recorded 4–5 minute demo: NOT RECORDED.

The browser Voice studio fixture is explicitly simulated and reports JavaScript cancellation dispatch, not acoustic stop latency. It is not evidence of a live Rime session.

## Exact configured path

Coda / astra / en; `https://users.rime.ai/v1/rime-tts`; default regional routing; `Accept: audio/L16`; signed 16-bit little-endian mono PCM at 24 kHz; streaming HTTPS in Electron main, IPC to Web Audio. No cached speech. See README for live catalog validation.

## Limitations

Energy VAD may misfire on noise or loudspeaker echo. Headphones are part of the test conditions. Recognition is utterance-based local whisper.cpp, not streaming ASR. The 700 ms endpoint silence and local model inference contribute to latency. No telephony, automatic code-switching, word-aligned partial delivery state, or production full-duplex claim. Provider first-byte timings and UI request-to-scheduled-playback timings exclude parts of the user path and must not be reported as end-to-end response latency.
