"""声音层：F5-TTS 零样本克隆。模型权重走 hf-mirror，避免直连 HuggingFace 被拦。"""

import inspect
import os
import re
import subprocess
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HOME", str(ROOT / "models"))

# pydub / librosa 需要 ffmpeg 在 PATH 里，这里把它指到 venv 自带的那份
try:
    import imageio_ffmpeg

    _ff = Path(imageio_ffmpeg.get_ffmpeg_exe()).parent
    if str(_ff) not in os.environ.get("PATH", ""):
        os.environ["PATH"] = str(_ff) + os.pathsep + os.environ.get("PATH", "")
except Exception:  # noqa: BLE001
    pass


class TTS:
    def __init__(self, cfg, voice):
        self.cfg = cfg
        self.voice = voice
        self._model = None
        self._lock = threading.Lock()
        self.last_error = None

    def _ref(self):
        """参考音频路径相对项目根目录（runtime 的上一级）。"""
        p = Path(self.voice["ref_audio"])
        if not p.is_absolute():
            p = (ROOT.parent / p).resolve()
        return p

    def load(self):
        if self._model is not None:
            return self._model
        from f5_tts.api import F5TTS

        kwargs = {"model": self.cfg.get("model", "F5TTS_v1_Base")}
        if self.cfg.get("device"):
            kwargs["device"] = self.cfg["device"]
        try:
            self._model = F5TTS(**kwargs)
        except TypeError:
            self._model = F5TTS()
        return self._model

    def _ffmpeg(self):
        try:
            import imageio_ffmpeg

            return imageio_ffmpeg.get_ffmpeg_exe()
        except Exception:  # noqa: BLE001
            return None

    def _peak_fix(self, wav):
        """把峰值归一到 -2 dB 左右。F5 的原始输出常顶到 0 dB，会刺耳。"""
        if not self.cfg.get("peak_normalize", True):
            return
        ff = self._ffmpeg()
        if not ff:
            return
        target = float(self.cfg.get("peak_target_db", -2.0))
        probe = subprocess.run(
            [ff, "-hide_banner", "-i", str(wav), "-af", "volumedetect", "-f", "null", "-"],
            capture_output=True,
            text=True,
            errors="ignore",
        )
        m = re.search(r"max_volume:\s*(-?\d+(?:\.\d+)?)\s*dB", probe.stderr or "")
        if not m:
            return
        gain = target - float(m.group(1))
        if abs(gain) < 0.4:
            return
        gain = max(-24.0, min(9.0, gain))
        tmp = wav.with_suffix(".fx.wav")
        r = subprocess.run(
            [ff, "-hide_banner", "-loglevel", "error", "-y", "-i", str(wav),
             "-af", f"volume={gain:.2f}dB", "-ar", "24000", "-ac", "1", str(tmp)],
            capture_output=True,
            text=True,
            errors="ignore",
        )
        if r.returncode == 0 and tmp.exists():
            tmp.replace(wav)

    def say(self, text, out_wav):
        out_wav = Path(out_wav)
        ref = self._ref()
        if not ref.exists():
            raise RuntimeError(f"参考音频不存在：{ref}")
        with self._lock:
            m = self.load()
            kwargs = dict(
                ref_file=str(ref),
                ref_text=self.voice["ref_text"],
                gen_text=text,
                file_wave=str(out_wav),
                nfe_step=self.cfg.get("nfe_step", 32),
                cfg_strength=self.cfg.get("cfg_strength", 2.0),
                speed=self.cfg.get("speed", 0.9),
                remove_silence=self.cfg.get("remove_silence", True),
            )
            sig = inspect.signature(m.infer).parameters
            kwargs = {k: v for k, v in kwargs.items() if k in sig}
            m.infer(**kwargs)
        self._peak_fix(out_wav)
        return out_wav
