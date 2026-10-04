"""Historical prototype: photoreal polish of a sample Blender render with OpenAI GPT Image 2.5 Sunburst via OpenRouter.

Reads the API key from the OPENROUTER_API_KEY environment variable (never stored in this file).
Usage:  python ai_polish.py [input.jpg] [output_prefix]
Fill in the {placeholders} in PROMPT for your scene before running.
"""
import base64, json, os, sys, urllib.request, datetime

MODEL = "openai/gpt-image-2.5-sunburst"
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "renders", "Sample_Render_v5.jpg")
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "renders", "Sample_Render_AI_polish")

PROMPT = """Edit this architectural interior rendering into a photograph indistinguishable from a professional
interiors magazine shoot (shot on a full-frame camera, 24mm tilt-shift lens, natural exposure, true verticals).

KEEP EXACTLY THE SAME - do not move, add, remove or redesign anything:
- camera position, framing, perspective and wide aspect ratio
- all architecture: {architecture, e.g. columns, ceiling, light fixtures, glazing, windows}
- all furniture and their positions: {furniture and objects, with materials}
- the {floor material} floor pattern and its direction
- the {number} people: same positions, poses, clothing colors and skin tones ({one short description per person})
- the {palette} palette and overall lighting direction

IMPROVE ONLY PHOTOGRAPHIC REALISM:
- people: real human skin texture, natural faces, real hair, fabric folds and drape, natural relaxed posture
- materials: {real texture for each main material, e.g. wood grain and pores, stone veining, matte wall finishes}
- light: physically accurate soft daylight, gentle bounce light, soft contact shadows, subtle floor reflections, realistic glow from the fixtures without blooming
- plants: real leaves with translucency
- camera realism: fine natural film grain, slight lens vignetting, accurate white balance

No text overlays, no logos, no watermarks, no brand names on covers."""


def main():
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        sys.exit("OPENROUTER_API_KEY is not set. Set it in your terminal first (see README in chat).")
    with open(SRC, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    body = {
        "model": MODEL,
        "modalities": ["image", "text"],
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]}],
    }
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json",
                 "X-Title": "sample render polish"},
    )
    print(f"Sending {os.path.basename(SRC)} to {MODEL} ... (can take 1-2 minutes)")
    with urllib.request.urlopen(req, timeout=600) as r:
        resp = json.load(r)
    msg = resp["choices"][0]["message"]
    imgs = msg.get("images") or []
    if not imgs:
        print("No image returned. Model said:", (msg.get("content") or "")[:800])
        sys.exit(1)
    stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    for i, im in enumerate(imgs):
        url = im["image_url"]["url"]
        header, data = url.split(",", 1)
        ext = "png" if "png" in header else "jpg"
        path = f"{OUT}_{stamp}_{i+1}.{ext}"
        with open(path, "wb") as f:
            f.write(base64.b64decode(data))
        print("Saved", path)
    usage = resp.get("usage") or {}
    if usage: print("Usage:", usage)


if __name__ == "__main__":
    main()
