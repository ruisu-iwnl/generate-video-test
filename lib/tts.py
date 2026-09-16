"""Text-to-speech with two tiers:
1. edge-tts: free, keyless neural voice via Microsoft's online TTS service.
   Natural-sounding, but needs network.
2. Windows SAPI (System.Speech) via PowerShell: fully offline fallback,
   more robotic, but always works with zero dependencies.
"""
import asyncio
import subprocess
import pathlib

NEURAL_VOICE = "en-US-GuyNeural"
SAPI_VOICE = "Microsoft Zira Desktop"

SAPI_PS_TEMPLATE = """
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice('{voice}')
$s.Rate = -1
$s.SetOutputToWaveFile('{wav_path}')
$s.Speak([IO.File]::ReadAllText('{txt_path}'))
$s.Dispose()
"""


def _synthesize_edge(text: str, out_wav: pathlib.Path):
    import edge_tts  # optional dependency; only needed for this tier

    tmp_mp3 = out_wav.with_suffix(".mp3")

    async def _gen():
        communicate = edge_tts.Communicate(text, NEURAL_VOICE)
        await communicate.save(str(tmp_mp3))

    asyncio.run(_gen())

    result = subprocess.run(
        ["ffmpeg", "-y", "-i", str(tmp_mp3), str(out_wav)],
        capture_output=True, text=True,
    )
    tmp_mp3.unlink(missing_ok=True)
    if result.returncode != 0 or not out_wav.exists():
        raise RuntimeError(f"edge-tts->wav conversion failed: {result.stderr}")
    return out_wav


def _synthesize_sapi(text: str, out_wav: pathlib.Path):
    txt_path = out_wav.with_suffix(".txt")
    txt_path.write_text(text, encoding="utf-8")

    ps_script = SAPI_PS_TEMPLATE.format(
        voice=SAPI_VOICE,
        wav_path=str(out_wav).replace("\\", "\\\\"),
        txt_path=str(txt_path).replace("\\", "\\\\"),
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not out_wav.exists():
        raise RuntimeError(f"SAPI TTS failed for {out_wav}: {result.stderr}")
    return out_wav


def synthesize(text: str, out_wav: pathlib.Path):
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    try:
        return _synthesize_edge(text, out_wav)
    except Exception:
        return _synthesize_sapi(text, out_wav)
