# Colab Voice-Clone Notebook — Builder Pattern & Key Snippets

Validated 2026-08-22 on aarch64 Ubuntu VM + Colab T4. Full working example: `github.com/Amz34/voice-clone-assistant` → `Voice_Clone_Assistant.ipynb`.

## Why build the notebook from a Python script
Hand-writing .ipynb JSON is error-prone. Use a builder script that defines cells as Python strings and dumps nbformat dict:

```python
def md(text): return {"cell_type": "markdown", "metadata": {}, "source": text.splitlines(keepends=True)}
def code(text): return {"cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": text.splitlines(keepends=True)}

cells = []
cells.append(code("""# Step 1: Install
!pip install -q TTS==0.22.0 faster-whisper soundfile librosa numpy"""))
# ...
nb = {"nbformat": 4, "nbformat_minor": 0,
      "metadata": {"colab": {"provenance": [], "name": "X.ipynb", "toc_visible": True},
                   "kernelspec": {"name": "python3", "display_name": "Python 3"},
                   "language_info": {"name": "python"}, "accelerator": "GPU"},
      "cells": cells}
json.dump(nb, open("X.ipynb", "w"), indent=1, ensure_ascii=False)
```

## CRITICAL pitfall — triple-quote collision
Cell source lives inside the builder's `"""..."""`. Anything with `"""` inside a cell (docstrings!) terminates the outer string → SyntaxError at a confusing line. Fixes:
- Inside cells use `# comments` instead of docstrings
- For JS/other templates inside cells use `'''...'''` (single-quote triple), not `"""`
- Symptom: `SyntaxError: invalid syntax. Perhaps you forgot a comma?` pointing at a line far from the real culprit — check for `"""` inside cell strings first

## Load XTTS-v2
```python
import torch
from TTS.api import TTS
device = "cuda" if torch.cuda.is_available() else "cpu"
tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)
# languages: en, hi, ar, ... (17+; Kashmiri NOT included)
```

## Clean the uploaded voice sample
```python
y, sr = librosa.load(path, sr=22050)
y, _ = librosa.effects.trim(y, top_db=25)   # trim silence
sf.write("voice_sample.wav", y, 22050)
```

## Clone test across languages
```python
tests = {"English": "Hello! ...", "Hindi": "नमस्ते! ...", "Urdu": "السلام علیکم! ...", "Arabic": "السلام عليكم! ..."}
for name, text in tests.items():
    lang = "en" if name == "English" else "hi" if name in ("Hindi","Urdu") else "ar"
    tts.tts_to_file(text=text, speaker_wav="voice_sample.wav", language=lang, file_path=f"clips/test_{name}.wav")
```

## Personality dict (speed + system prompt per mode)
```python
PERSONALITIES = {
    "Kashish": {"speed": 1.0, "system": "Tum ek warm, charming aur engaging voice assistant ho. ... Concise raho (max 3-4 sentences)."},
    "Hasmukh": {"speed": 1.1, "system": "Tum ek cheerful, humorous aur energetic voice assistant ho. ..."},
    "Mozzaz":  {"speed": 0.95, "system": "Tum ek dignified, professional aur formal voice assistant ho. ..."},
}
def deepseek(text, personality="Hasmukh"):
    cfg = PERSONALITIES[personality]
    msgs = [{"role": "system", "content": f"{cfg['system']} User language me jawab do."}, {"role": "user", "content": text}]
    r = requests.post("https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json={"model": "deepseek-chat", "messages": msgs, "max_tokens": 200})
    return r.json()["choices"][0]["message"]["content"].strip()
```

## Colab mic recording (JS eval)
```python
from google.colab import output
JS = '''
  (async () => {
    const stream = await navigator.mediaDevices.getUserMedia({audio: true});
    const rec = new MediaRecorder(stream);
    const chunks = [];
    rec.ondataavailable = e => chunks.push(e.data);
    rec.onstop = () => {
      const blob = new Blob(chunks, {type: 'audio/webm'});
      const reader = new FileReader();
      reader.onloadend = () => window._audioB64 = reader.result.split(',')[1];
      reader.readAsDataURL(blob);
    };
    rec.start();
    await new Promise(r => setTimeout(r, SECONDS*1000));
    rec.stop();
  })()
'''.replace("SECONDS", str(seconds))
output.eval_js(JS)
# then decode b64 → mic.webm → !ffmpeg -y -i mic.webm -ar 16000 -ac 1 mic.wav
```
Note: `'''` not `"""` inside the cell (collision rule above). Requires Runtime → Settings → Hardware acceleration (mic permission).

## Colab user-data secrets (no hardcoded keys)
```python
from google.colab import userdata
API_KEY = userdata.get("DEEPSEEK_API_KEY")   # left key icon → Add new secret
```

## Verify notebook after building
```bash
python3 -c "
import json; nb = json.load(open('X.ipynb'))
print(len(nb['cells']), 'cells')
for c in nb['cells']: print(c['cell_type'], c['source'][0][:50])"
```

## Repo → Colab one-click
```bash
git init && git add -A && git commit -qm "msg"
gh repo create Amz34/<repo> --public --source . --push
# Link: https://colab.research.google.com/github/Amz34/<repo>/blob/main/<NB>.ipynb
```
