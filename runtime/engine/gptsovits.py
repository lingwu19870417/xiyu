"""声音层（GPT-SoVITS 后端）。

和 tts.py 暴露同一套接口（load / say），app.py 不用关心底下是谁。
实际的模型跑在又一个独立进程里（GPT-SoVITS 的 api_v2.py，端口 9880），
这里只负责发 HTTP 请求拿音频。这样 F5 和 GPT-SoVITS 可以并存、随时切。
"""

import json
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GPTSoVITS:
    def __init__(self, cfg, voice):
        self.cfg = cfg
        self.voice = voice
        self.api = cfg.get("api", "http://127.0.0.1:9880").rstrip("/")
        self.last_error = None

    def _ref_audio(self):
        p = Path(self.voice.get("ref_audio", ""))
        if not p.is_absolute():
            p = (ROOT.parent / p).resolve()
        return p

    def _post(self, payload, timeout):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            self.api + "/tts",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()

    def load(self):
        """确认语音服务在跑。模型由服务自己加载，这里只探活。"""
        try:
            urllib.request.urlopen(self.api + "/docs", timeout=8).read(1)
        except urllib.error.URLError as e:
            raise RuntimeError(
                f"语音服务没启动（{self.api}）。请先运行 "
                f"D:\\gpt-sovits\\GPT-SoVITS-v2pro-20250604\\启动语音服务.bat"
            ) from e
        except Exception:  # noqa: BLE001
            # /docs 未必存在，端口能连上就算活
            pass
        ref = self._ref_audio()
        if not ref.exists():
            raise RuntimeError(f"参考音频不存在：{ref}")
        return True

    def say(self, text, out_wav):
        out_wav = Path(out_wav)
        # 注意：api_v2.py 的请求模型是固定字段，多传字段会被 400 拒掉，
        # 所以这里只发它认识的键。ref_free 由 prompt_text 是否为空间接控制。
        ref_free = bool(self.cfg.get("ref_free", False))
        payload = {
            "text": text,
            "text_lang": self.cfg.get("text_lang", "zh"),
            "ref_audio_path": str(self._ref_audio()),
            "prompt_text": "" if ref_free else self.voice.get("ref_text", ""),
            "prompt_lang": self.cfg.get("text_lang", "zh"),
            "text_split_method": self.cfg.get("split_method", "cut5"),
            "batch_size": 1,
            "speed_factor": float(self.cfg.get("speed_factor", 1.0)),
            "seed": int(self.cfg.get("seed", 42)),
            "parallel_infer": True,
            "repetition_penalty": float(self.cfg.get("repetition_penalty", 1.35)),
            "top_k": int(self.cfg.get("top_k", 15)),
            "top_p": float(self.cfg.get("top_p", 1.0)),
            "temperature": float(self.cfg.get("temperature", 1.0)),
        }
        audio = self._post(payload, timeout=float(self.cfg.get("timeout", 120)))
        if len(audio) < 2000:
            # 服务出错时会返回很短的内容，通常是 JSON 错误信息
            try:
                raise RuntimeError("合成失败：" + audio.decode("utf-8", "ignore")[:200])
            except UnicodeDecodeError:
                raise RuntimeError(f"合成失败，返回 {len(audio)} 字节")
        out_wav.write_bytes(audio)
        if self.cfg.get("trim_tail", True):
            self._trim_silence(out_wav)
        return out_wav

    @staticmethod
    def _trim_silence(path, thresh_db=-42.0, head=0.04, tail=0.18):
        """去掉首尾多余静音。

        GPT-SoVITS 常在句尾拖 0.5~3 秒空白，浏览器里听着像"愣住没说完"。
        这里按峰值相对阈值找首尾有效段，各留一点余量，避免切掉气口。
        """
        import wave

        import numpy as np

        try:
            with wave.open(str(path), "rb") as w:
                sr, ch, sw = w.getframerate(), w.getnchannels(), w.getsampwidth()
                data = w.readframes(w.getnframes())
            if sw != 2 or not data:
                return
            a = np.frombuffer(data, dtype=np.int16)
            if ch > 1:
                a = a.reshape(-1, ch)
            amp = np.abs(a.astype(np.float32))
            if amp.ndim > 1:
                amp = amp.max(axis=1)
            peak = float(amp.max())
            if peak <= 0:
                return
            thr = peak * (10 ** (thresh_db / 20.0))
            idx = np.where(amp > thr)[0]
            if len(idx) < 10:
                return
            start = max(0, idx[0] - int(head * sr))
            end = min(len(amp), idx[-1] + int(tail * sr))
            # 保留不足 60% 就不动，防止把整句误切
            if end - start < 0.6 * len(amp):
                return
            out = a[start:end]
            with wave.open(str(path), "wb") as w:
                w.setnchannels(ch)
                w.setsampwidth(sw)
                w.setframerate(sr)
                w.writeframes(out.tobytes())
        except Exception as e:  # noqa: BLE001
            # 修剪失败不影响出声，保留原始音频
            print(f"[tts] 静音修剪跳过：{e}", flush=True)
