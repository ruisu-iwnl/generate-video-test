"""Offline text-to-speech via Windows SAPI (System.Speech), driven through PowerShell.
No network or API key required."""
import subprocess
import pathlib

VOICE = "Microsoft Zira Desktop"

PS_TEMPLATE = """
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice('{voice}')
$s.Rate = -1
$s.SetOutputToWaveFile('{wav_path}')
$s.Speak([IO.File]::ReadAllText('{txt_path}'))
$s.Dispose()
"""


def synthesize(text: str, out_wav: pathlib.Path):
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    txt_path = out_wav.with_suffix(".txt")
    txt_path.write_text(text, encoding="utf-8")

    ps_script = PS_TEMPLATE.format(
        voice=VOICE,
        wav_path=str(out_wav).replace("\\", "\\\\"),
        txt_path=str(txt_path).replace("\\", "\\\\"),
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", ps_script],
        capture_output=True, text=True,
    )
    if result.returncode != 0 or not out_wav.exists():
        raise RuntimeError(f"TTS failed for {out_wav}: {result.stderr}")
    return out_wav
