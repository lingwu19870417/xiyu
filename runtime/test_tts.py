"""离线验证音色：不启动网页，直接合成一段话。

按 persona/config.json 里 tts.engine 自动选择引擎：
  f5-tts      → 本地零样本，首次会下载约 1.3GB 权重
  gpt-sovits  → 需要先启动 9880 语音服务

用法：
  runtime\\.venv\\Scripts\\python.exe test_tts.py "哎，回来了。坐，坐。饭吃了吗？"
  runtime\\.venv\\Scripts\\python.exe test_tts.py "你爸，走了些年了。" out.wav
"""

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from engine.gptsovits import GPTSoVITS  # noqa: E402
from engine.persona import Persona  # noqa: E402
from engine.tts import TTS  # noqa: E402

text = sys.argv[1] if len(sys.argv) > 1 else "哎，回来了。坐，坐。饭吃了吗？"
name = sys.argv[2] if len(sys.argv) > 2 else "test.wav"

cfg = json.loads((ROOT / "persona" / "config.json").read_text(encoding="utf-8"))
persona = Persona(ROOT / "persona")

engine = cfg["tts"].get("engine", "f5-tts")
if engine == "gpt-sovits":
    tts = GPTSoVITS(cfg["tts"], persona.voice())
else:
    tts = TTS({**cfg["tts"], **cfg["tts"].get("f5", {})}, persona.voice())

out = ROOT / "audio" / name
out.parent.mkdir(exist_ok=True)

print(f"[1/2] 加载模型（引擎 {engine}，首次可能需下载权重）…", flush=True)
t0 = time.time()
tts.load()
print(f"      完成，{time.time() - t0:.1f}s", flush=True)

t1 = time.time()
print(f"[2/2] 合成：{text}", flush=True)
tts.say(text, out)
print(f"      完成，{time.time() - t1:.1f}s -> {out}", flush=True)
print(f"      音频时长 {out.stat().st_size / 1024:.0f} KB")
