"""
Turns a topic string into a list of video segments.

Tries the Anthropic API first (real LLM scripting). If no API key/network
is available (true in this sandbox), falls back to a small curated
knowledge base for a few demo topics, and finally to a generic template
so *any* topic still produces a runnable script.
"""
import os
import json
import urllib.request
import urllib.error

PALETTE = [
    ("#0f2027", "#2c5364"),
    ("#1a2980", "#26d0ce"),
    ("#134e5e", "#71b280"),
    ("#2b5876", "#4e4376"),
    ("#0f0c29", "#302b63"),
    ("#000428", "#004e92"),
]

CURATED = {
    "the water cycle": [
        ("The Water Cycle",
         "Water on Earth is constantly moving through a continuous cycle, powered by energy from the sun."),
        ("Evaporation",
         "Heat from the sun warms oceans, lakes, and rivers, turning liquid water into invisible water vapor that rises into the sky."),
        ("Condensation",
         "As water vapor rises and cools, it condenses around tiny particles in the air, forming the clouds we see overhead."),
        ("Precipitation",
         "When clouds become heavy with water, it falls back to Earth as rain, snow, sleet, or hail."),
        ("Collection",
         "That water collects in rivers, lakes, and oceans, or soaks into the ground, ready to begin the cycle all over again."),
        ("The Cycle Continues",
         "And so, the water cycle repeats endlessly, quietly sustaining every form of life on Earth."),
    ],
}


def _try_anthropic(topic: str):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    prompt = (
        f"Write a short 5-6 segment narration script for an explainer video about "
        f'"{topic}". Return ONLY JSON: a list of objects with "title" (2-4 words) '
        f'and "narration" (1-2 sentences, spoken aloud, no markdown).'
    )
    body = json.dumps({
        "model": "claude-sonnet-5",
        "max_tokens": 800,
        "messages": [{"role": "user", "content": prompt}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=body,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=6) as resp:
            data = json.loads(resp.read())
            text = data["content"][0]["text"]
            items = json.loads(text)
            return [(i["title"], i["narration"]) for i in items]
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError, json.JSONDecodeError):
        return None


def _generic_template(topic: str):
    return [
        (topic, f"Let's take a closer look at {topic}."),
        ("Overview", f"{topic} is a subject with several key ideas worth understanding."),
        ("Key Point", f"One of the most interesting things about {topic} is how it connects to everyday life."),
        ("Why It Matters", f"Understanding {topic} helps make sense of the world around us."),
        ("Conclusion", f"That's a quick look at {topic}. Thanks for watching."),
    ]


def generate_script(topic: str):
    """Returns (segments, source) where segments is a list of dicts with
    title/narration/caption/colors, and source names which tier produced it."""
    raw = _try_anthropic(topic)
    source = "anthropic-api"
    if raw is None:
        raw = CURATED.get(topic.strip().lower())
        source = "curated-fallback"
    if raw is None:
        raw = _generic_template(topic)
        source = "generic-template-fallback"

    segments = []
    for i, (title, narration) in enumerate(raw):
        c1, c2 = PALETTE[i % len(PALETTE)]
        segments.append({
            "id": i,
            "title": title,
            "narration": narration,
            "caption": narration,
            "color_top": c1,
            "color_bottom": c2,
        })
    return segments, source
