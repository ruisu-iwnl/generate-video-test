"""
Automated video generator: give it a topic, get back a raw mp4.

Usage:
    python generate.py "The Water Cycle"

Pipeline (fully local, no network/API key required — see README):
    topic -> script (LLM or offline fallback)
          -> voiceover (offline TTS)
          -> visuals (generated per segment)
          -> per-segment clip (Ken Burns zoom + burned-in captions)
          -> concatenated video
          -> synthesized background music bed
          -> final mixed mp4
"""
import sys
import time
import pathlib
import re

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from lib.script_writer import generate_script
from lib.tts import synthesize
from lib.visuals import render_segment_image
from lib.assemble import build_segment_clip, concat_clips, generate_music_bed, mix_final, ffprobe_duration


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "video"


def main():
    topic = " ".join(sys.argv[1:]).strip() or "The Water Cycle"
    t0 = time.time()

    out_root = pathlib.Path(__file__).parent / "output" / slugify(topic)
    clips_dir = out_root / "clips"
    assets_dir = out_root / "assets"
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"[1/6] Writing script for topic: {topic!r}")
    segments, source = generate_script(topic)
    print(f"      -> {len(segments)} segments (source: {source})")

    clip_paths = []
    for seg in segments:
        idx = seg["id"]
        print(f"[2/6] Segment {idx + 1}/{len(segments)}: {seg['title']!r}")

        wav_path = assets_dir / f"seg_{idx:02d}.wav"
        synthesize(seg["narration"], wav_path)

        img_path = assets_dir / f"seg_{idx:02d}.png"
        render_segment_image(seg, len(segments), img_path)

        clip_path = clips_dir / f"seg_{idx:02d}.mp4"
        build_segment_clip(img_path, wav_path, seg["caption"], clip_path)
        clip_paths.append(clip_path)

    print("[3/6] Concatenating segment clips")
    concat_path = out_root / "concat.mp4"
    concat_clips(clip_paths, concat_path)

    print("[4/6] Generating background music bed")
    total_duration = ffprobe_duration(concat_path)
    music_path = out_root / "music.wav"
    generate_music_bed(total_duration, music_path)

    print("[5/6] Mixing final audio")
    final_path = out_root / f"{slugify(topic)}.mp4"
    mix_final(concat_path, music_path, final_path)

    elapsed = time.time() - t0
    print(f"[6/6] Done in {elapsed:.1f}s -> {final_path}")
    return final_path


if __name__ == "__main__":
    main()
