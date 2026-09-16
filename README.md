# Automated Video Generator (Manos Corp trial task)

Give it a topic, get back a raw mp4.

```
python generate.py "The Water Cycle"
```

Output lands at `output/<topic_slug>/<topic_slug>.mp4`. Demo run included at
`output/the_water_cycle/the_water_cycle.mp4` (51s, 1920x1080, h264/aac).

## How it works

Topic string goes through a six-stage local pipeline, no manual steps in between:

1. **Script** (`lib/script_writer.py`) — topic -> list of `{title, narration}`
   segments. Tries the Anthropic API first (real LLM writing); if no
   `ANTHROPIC_API_KEY`/network is available it falls back to a small curated
   script for a couple of demo topics, then to a generic topic-substitution
   template so *any* string still produces a runnable video. This sandbox
   had no internet access, so the demo run used the curated fallback.
2. **Voiceover** (`lib/tts.py`) — each segment's narration is synthesized to a
   WAV file via Windows SAPI (`System.Speech.Synthesis`), invoked through
   PowerShell. Fully offline, real speech audio (not silence/beeps).
3. **Visuals** (`lib/visuals.py`) — a 1920x1080 background image per segment:
   procedural vertical gradient (Pillow) + the segment title rendered in
   Arial Bold, wrapped and centered.
4. **Per-segment clip** (`lib/assemble.py: build_segment_clip`) — ffmpeg
   `zoompan` turns the static image into a slow Ken Burns zoom timed to the
   voiceover's actual duration (via `ffprobe`), and `drawtext` burns the
   caption (wrapped narration text) onto the bottom of the frame.
5. **Concat** — all segment clips are joined via ffmpeg's concat demuxer.
6. **Music bed** — a simple ambient pad is *synthesized*, not sourced, from
   three sine oscillators (a triad) via ffmpeg's `lavfi` sine source, faded
   in/out and mixed under the voice track at low volume with `amix`.

Everything after step 1 runs with zero external dependencies — no stock
footage API, no paid TTS, no GPU. That was a constraint of this sandbox
(no internet, no API keys provisioned), not a design goal.

## Tools / AI used

- **Claude (this coding session)** — wrote the pipeline, and is the
  fallback "AI" behind the demo script content.
- **ffmpeg** (full build, local) — all video/audio generation and muxing:
  `zoompan`, `drawtext`, `concat`, `lavfi` sine synthesis, `amix`.
- **Windows SAPI** (`System.Speech`) via PowerShell — offline TTS.
- **Pillow** — procedural background image generation.
- Python 3.12 as the orchestrator (`generate.py` + `lib/`).

No Playwright, yt-dlp, or Postgres in this build — the task didn't need a
browser, downloader, or database, so I didn't reach for them.

## What I'd change with more time / real API access

- Swap the fallback/curated script tiers for a live Anthropic API call as
  the *only* path (it's already wired in `script_writer.py`, just needs
  `ANTHROPIC_API_KEY` and network).
- Replace the generated gradient backgrounds with real stock footage/images
  (Pexels/Pixabay API) or AI-generated imagery per segment, keeed to the
  narration content.
- Use a neural TTS (ElevenLabs/OpenAI) for more natural voice + word-level
  timestamps, so captions can be word-synced instead of per-segment.
- Replace the synthesized sine-wave pad with a licensed/generated music
  track matched to topic mood, and add loudness normalization.
- Parallelize per-segment clip rendering (currently sequential) — trivial
  win once segment count grows.
