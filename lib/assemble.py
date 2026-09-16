"""ffmpeg-based assembly: image+voiceover -> per-segment clip with Ken Burns
zoom and burned-in captions, then concat, generate a synthesized music bed,
and mix it under the voice track. Pure local ffmpeg, no network needed."""
import json
import subprocess
import textwrap
import pathlib

FPS = 30
FONT = "C\\:/Windows/Fonts/arial.ttf"


def _run(cmd):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{result.stderr[-2000:]}")
    return result


def ffprobe_duration(path: pathlib.Path) -> float:
    result = _run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(path),
    ])
    return float(json.loads(result.stdout)["format"]["duration"])


def build_segment_clip(image_path: pathlib.Path, wav_path: pathlib.Path,
                        caption_text: str, out_path: pathlib.Path):
    wav_duration = ffprobe_duration(wav_path)
    duration = wav_duration + 0.6
    frames = max(int(duration * FPS), 2)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    caption_lines = textwrap.wrap(caption_text, width=48)
    caption_txt = out_path.with_suffix(".caption.txt")
    caption_txt.write_text("\n".join(caption_lines), encoding="utf-8")
    caption_txt_ff = str(caption_txt).replace("\\", "/").replace(":", "\\:")

    vf = (
        f"zoompan=z='min(zoom+0.0006,1.15)':d={frames}:s=1920x1080:fps={FPS},"
        f"drawtext=textfile='{caption_txt_ff}':fontfile='{FONT}':fontsize=42:"
        f"fontcolor=white:borderw=3:bordercolor=black:x=(w-text_w)/2:y=h-170:"
        f"line_spacing=8"
    )

    _run([
        "ffmpeg", "-y",
        "-loop", "1", "-i", str(image_path),
        "-i", str(wav_path),
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-ar", "44100",
        str(out_path),
    ])
    return out_path


def concat_clips(clip_paths, out_path: pathlib.Path):
    list_file = out_path.with_suffix(".list.txt")
    lines = []
    for p in clip_paths:
        safe = str(p.resolve()).replace("\\", "/").replace("'", "'\\''")
        lines.append(f"file '{safe}'")
    list_file.write_text("\n".join(lines), encoding="utf-8")

    _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(list_file), "-c", "copy", str(out_path),
    ])
    return out_path


def generate_music_bed(duration: float, out_path: pathlib.Path):
    d = max(duration, 1.0)
    fade_out_start = max(d - 2, 0)
    _run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", f"sine=frequency=220:duration={d}",
        "-f", "lavfi", "-i", f"sine=frequency=277:duration={d}",
        "-f", "lavfi", "-i", f"sine=frequency=330:duration={d}",
        "-filter_complex",
        f"[0][1][2]amix=inputs=3:duration=longest,"
        f"volume=0.10,afade=t=in:d=2,afade=t=out:st={fade_out_start}:d=2",
        "-ar", "44100", str(out_path),
    ])
    return out_path


def mix_final(video_path: pathlib.Path, music_path: pathlib.Path, out_path: pathlib.Path):
    _run([
        "ffmpeg", "-y",
        "-i", str(video_path), "-i", str(music_path),
        "-filter_complex",
        "[0:a]volume=1.0[a0];[1:a]volume=1.0[a1];"
        "[a0][a1]amix=inputs=2:duration=first:dropout_transition=2[aout]",
        "-map", "0:v", "-map", "[aout]",
        "-c:v", "copy", "-c:a", "aac",
        str(out_path),
    ])
    return out_path
