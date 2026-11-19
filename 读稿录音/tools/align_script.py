# -*- coding: utf-8 -*-
"""读稿录音 → 训练清单（核心：用「稿子已知」把标注错误率降到零）

流程：转码 → 按静音切片 → 逐段识别（用稿子做提示）→ 顺序约束的对齐（允许 1~3 个
      碎片合并成一句）→ 从原音频截取完整时间跨度 → 用「稿子原文」作标注 →
      质检报告 + 需补读清单

用法：
  python align_script.py --audio <录音目录或文件> --script 脚本.txt --out <输出目录>
补录后合并：
  python align_script.py --audio raw/补录 --script out/需补读.txt --out out_补录 --merge-to out/list.txt

关键设计：
  * 标注文本 100% 来自稿子，绝不使用 ASR 结果
  * ASR 只用来判断「这段音频是第几句」
  * 允许她漏读（跳过稿子行）、允许她重读/口误/咳嗽（跳过音频段）
"""
import argparse
import difflib
import io
import os
import re
import subprocess
import sys

GSV = r"D:\gpt-sovits\GPT-SoVITS-v2pro-20250604"
FFMPEG = os.path.join(GSV, "runtime", "ffmpeg.exe")
WHISPER_DIR = os.path.join(GSV, "tools", "asr", "models", "faster-whisper-large-v3")

SPK, LANG = "mother", "ZH"
SR = 32000

ACCEPT_SIM = 0.42        # 文本相似度低于此 → 判为「需补读」
MIN_DUR, MAX_DUR = 0.9, 18.0
MAX_MERGE = 3            # 最多把 3 个碎片合并成一句
MAX_MERGE_DUR = 15.0

CJK = re.compile(r"[^\u4e00-\u9fff]")


def norm(t):
    return CJK.sub("", t or "")


def log(*a):
    print(*a, flush=True)


# ---------------- 音频 ----------------

def to_wav32k(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    subprocess.run([FFMPEG, "-y", "-hide_banner", "-loglevel", "error", "-i", src,
                    "-ac", "1", "-ar", str(SR), "-c:a", "pcm_s16le", dst], check=True)
    return dst


def collect_audio(paths):
    exts = (".wav", ".mp3", ".m4a", ".flac", ".aac", ".ogg", ".wma", ".opus")
    files = []
    for p in paths:
        if os.path.isdir(p):
            for f in sorted(os.listdir(p)):
                q = os.path.join(p, f)
                if os.path.isfile(q) and f.lower().endswith(exts):
                    files.append(q)
        elif os.path.isfile(p):
            files.append(p)
    return files


def slice_all(wavs, workdir):
    """用 GSV 自带 Slicer 切片，记录每段在原始 wav 中的采样点跨度，不做增益。"""
    sys.path.insert(0, GSV)
    sys.path.insert(0, os.path.join(GSV, "tools"))
    from slicer2 import Slicer
    from tools.my_utils import load_audio
    import soundfile as sf

    outdir = os.path.join(workdir, "slices")
    os.makedirs(outdir, exist_ok=True)
    slicer = Slicer(sr=SR, threshold=-38, min_length=1500,
                    min_interval=250, hop_size=10, max_sil_kept=450)
    items = []
    for wav in wavs:
        audio = load_audio(wav, SR)
        stem = os.path.splitext(os.path.basename(wav))[0]
        n = 0
        for chunk, start, end in slicer.slice(audio):
            n += 1
            p = os.path.join(outdir, "%s_s%04d.wav" % (stem, n))
            sf.write(p, chunk, SR)
            items.append({"tmp": p, "src": wav, "start": int(start), "end": int(end)})
        log("  切片 %s → %d 段" % (stem, n))
    return items


def span_stats(src, start, end):
    """从原音频取跨度，返回 (音频数组, 去掉首尾静音后的 start, end)。"""
    import numpy as np
    import soundfile as sf
    x, sr = sf.read(src, dtype="float32", start=start, frames=end - start)
    if x.ndim > 1:
        x = x.mean(1)
    if len(x) == 0:
        return x, start, end
    fl = max(1, int(0.02 * sr))
    nf = len(x) // fl
    if nf > 0:
        fr = x[: nf * fl].reshape(nf, fl)
        db = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
        voiced = np.where(db > -42)[0]
        if len(voiced):
            s = max(0, voiced[0] * fl - int(0.05 * sr))
            e = min(len(x), (voiced[-1] + 1) * fl + int(0.15 * sr))
            x = x[s:e]
            start, end = start + s, start + e
    return x, start, end


def quick_qc(x, sr=SR):
    import numpy as np
    if len(x) == 0:
        return {"dur": 0, "db": -99, "peak": 0, "sil": 1.0, "clip": 0}
    dur = len(x) / sr
    peak = float(np.abs(x).max())
    db = float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-9))
    fl = max(1, int(0.02 * sr))
    nf = len(x) // fl
    sil = 0.0
    if nf > 0:
        fr = x[: nf * fl].reshape(nf, fl)
        fdb = 20 * np.log10(np.sqrt((fr ** 2).mean(1)) + 1e-9)
        sil = float((fdb < -45).mean())
    return {"dur": dur, "db": db, "peak": peak, "sil": sil,
            "clip": float((np.abs(x) > 0.999).mean())}


# ---------------- 识别 ----------------

def transcribe(paths, prompt):
    from faster_whisper import WhisperModel
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ.setdefault("HF_HOME", r"D:\gpt-sovits\hf")
    try:
        model = WhisperModel(WHISPER_DIR, device="cuda", compute_type="float16",
                             local_files_only=True)
        log("  Whisper: cuda")
    except Exception:
        model = WhisperModel(WHISPER_DIR, device="cpu", compute_type="int8",
                             local_files_only=True)
        log("  Whisper: cpu")
    out = []
    for i, p in enumerate(paths, 1):
        try:
            segs, _ = model.transcribe(
                p, language="zh", beam_size=5, initial_prompt=prompt,
                condition_on_previous_text=False, vad_filter=False,
                temperature=[0.0, 0.2, 0.4, 0.6], no_speech_threshold=0.6,
                log_prob_threshold=-1.0)
            txt = "".join(s.text for s in segs).strip()
        except Exception as e:
            log("    识别失败 %s %s" % (os.path.basename(p), e))
            txt = ""
        out.append(txt)
        if i % 20 == 0:
            log("  识别 %d/%d" % (i, len(paths)))
    return out


# ---------------- 对齐 ----------------

def sim_text(a, b):
    a, b = norm(a), norm(b)
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b, autojunk=False).ratio()


def sim_len(dur, text):
    exp = max(0.8, len(norm(text)) / 4.2)      # 中文口语约 4.2 字/秒
    return min(1.0, (2 * min(dur, exp)) / (dur + exp))


def group_score(asr_txt, dur, line):
    return 0.8 * sim_text(asr_txt, line) + 0.2 * sim_len(dur, line)


def align(items, lines):
    """单调全局对齐：一句可吃 1~MAX_MERGE 个相邻碎片。返回 [(i_start, i_end, j, k)]"""
    n, m = len(items), len(lines)
    MATCH, SKIP_S, SKIP_L = 0.30, 0.40, 0.50
    NEG = -1e9
    dp = [[NEG] * (m + 1) for _ in range(n + 1)]
    bk = [[None] * (m + 1) for _ in range(n + 1)]
    dp[0][0] = 0.0
    for i in range(1, n + 1):
        dp[i][0], bk[i][0] = -SKIP_S * i, ("S", 1)
    for j in range(1, m + 1):
        dp[0][j], bk[0][j] = -SKIP_L * j, ("L", 1)

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            best, arg = NEG, None
            d = dp[i][j - 1] - SKIP_L
            if d > best:
                best, arg = d, ("L", 1)
            d = dp[i - 1][j] - SKIP_S
            if d > best:
                best, arg = d, ("S", 1)
            for k in range(1, MAX_MERGE + 1):
                if i - k < 0:
                    break
                grp = items[i - k:i]
                if len({g["src"] for g in grp}) > 1:
                    break
                dur = (grp[-1]["end"] - grp[0]["start"]) / SR
                if dur > MAX_MERGE_DUR:
                    break
                # 合并后不能明显超出这句话该有的长度，否则会把「上一句的重读」吞进来
                exp = max(1.0, len(norm(lines[j - 1])) / 4.2)
                if dur > max(3.0, 1.8 * exp):
                    break
                txt = "".join(g["asr"] for g in grp)
                sc = group_score(txt, dur, lines[j - 1]) - MATCH - 0.02 * (k - 1)
                d = dp[i - k][j - 1] + sc
                if d > best:
                    best, arg = d, ("M", k)
            dp[i][j], bk[i][j] = best, arg

    out, i, j = [], n, m
    while i > 0 or j > 0:
        step, k = bk[i][j]
        if step == "M":
            out.append((i - k, i, j - 1, k))
            i, j = i - k, j - 1
        elif step == "S":
            i -= 1
        else:
            j -= 1
    out.reverse()
    return out


# ---------------- 主流程 ----------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", nargs="+", required=True)
    ap.add_argument("--script", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--merge-to", default=None, help="把结果追加进指定的已有 list.txt（补录用）")
    args = ap.parse_args()

    lines = [l.strip() for l in io.open(args.script, encoding="utf-8") if l.strip()]
    out = os.path.abspath(args.out)
    work = os.path.join(out, "work")
    seg_dir = os.path.join(out, "segments")
    os.makedirs(work, exist_ok=True)
    os.makedirs(seg_dir, exist_ok=True)

    log("[1/5] 转码")
    files = collect_audio(args.audio)
    if not files:
        log("没有找到音频文件"); return
    wavs = [to_wav32k(f, os.path.join(work, "w32",
                                     os.path.splitext(os.path.basename(f))[0] + ".wav"))
            for f in files]

    log("[2/5] 切片")
    items = slice_all(wavs, work)
    log("  共 %d 段" % len(items))

    log("[3/5] 识别（只用于定位，不用于标注）")
    prompt = "".join(lines[:8])[:220]
    for it, t in zip(items, transcribe([it["tmp"] for it in items], prompt)):
        it["asr"] = t

    log("[4/5] 对齐 + 截取")
    groups = align(items, lines)

    recs, hit = [], set()
    for gi, (a, b, j, k) in enumerate(groups):
        grp = items[a:b]
        line = lines[j]
        hit.add(j)
        x, s, e = span_stats(grp[0]["src"], grp[0]["start"], grp[-1]["end"])
        q = quick_qc(x)
        txt = "".join(g["asr"] for g in grp)
        ts = sim_text(txt, line)
        rec = {"j": j, "line": line, "asr": txt, "dur": q["dur"], "ts": ts,
               "wav": x, "sr": SR, "name": None, "gi": gi, "i0": a, "i1": b,
               "k": k, "hard": [], "soft": [], "low": False}
        # 硬伤：音频本身不可用，必须补读
        if q["dur"] < MIN_DUR:
            rec["hard"].append("太短%.2fs" % q["dur"])
        if q["dur"] > MAX_DUR:
            rec["hard"].append("太长%.0fs" % q["dur"])
        if q["db"] < -45:
            rec["hard"].append("音量低%.0fdB" % q["db"])
        if q["clip"] > 0.001:
            rec["hard"].append("爆音")
        if q["sil"] > 0.55:
            rec["hard"].append("静音多%.0f%%" % (q["sil"] * 100))
        # 软伤：只是识别文字对不上，可能是方言导致，位置可信就照用
        if ts < ACCEPT_SIM and not rec["hard"]:
            rec["soft"].append("识别对不上(%.2f)" % ts)
        recs.append(rec)

    # 位置可信度：前后相邻句都是严丝合缝的一对一，则这一句的「文字对不上」只是 ASR 的问题
    for idx, r in enumerate(recs):
        if r["hard"] or not r["soft"]:
            continue
        prev, nxt = recs[idx - 1] if idx > 0 else None, recs[idx + 1] if idx + 1 < len(recs) else None
        tight = False
        if r["k"] == 1 and prev is not None and not prev["hard"] and prev["ts"] >= ACCEPT_SIM:
            tight |= (r["j"] - prev["j"] <= 2) and (r["i0"] - prev["i1"] <= 2)
        if r["k"] == 1 and nxt is not None and not nxt["hard"] and nxt["ts"] >= ACCEPT_SIM:
            tight |= (nxt["j"] - r["j"] <= 2) and (nxt["i0"] - r["i1"] <= 2)
        r["low"] = bool(tight)

    used = [r for r in recs if not r["hard"]]
    need = [r for r in recs if r["hard"]]
    lowc = [r for r in used if r["low"]]

    import soundfile as sf
    rows = []
    for idx, r in enumerate(used, 1):
        name = "rd_%04d.wav" % idx
        p = os.path.join(seg_dir, name)
        sf.write(p, r["wav"], SR)
        r["name"] = name
        rows.append("%s|%s|%s|%s" % (p.replace("\\", "/"), SPK, LANG, r["line"]))

    missed = [{"j": j, "line": l} for j, l in enumerate(lines) if j not in hit]

    log("[5/5] 输出")
    list_path = os.path.abspath(args.merge_to) if args.merge_to else os.path.join(out, "list.txt")
    if args.merge_to and os.path.exists(list_path):
        old = [l.rstrip("\n") for l in io.open(list_path, encoding="utf-8") if l.strip()]
        rows = old + rows
    io.open(list_path, "w", encoding="utf-8").write("\n".join(rows) + "\n")

    todo = [r["line"] for r in need] + [m["line"] for m in missed]
    io.open(os.path.join(out, "需补读.txt"), "w", encoding="utf-8").write(
        "\n".join(todo) + ("\n" if todo else ""))

    tot = sum(r["dur"] for r in used)
    rep = ["# 读稿录音质检报告", "",
           "- 录音文件：%s" % "、".join(os.path.basename(f) for f in files),
           "- 稿子句数：%d" % len(lines),
           "- 切出音段：%d（%d 处碎片被合并成整句）" % (len(items), sum(1 for g in groups if g[3] > 1)),
           "- **已采用：%d 句 / %.2f 分钟**" % (len(used), tot / 60),
           "- 其中低置信（建议抽听）：%d 句" % len(lowc),
           "- 需补读：%d 句（音频不合格 %d + 漏读 %d）" % (len(todo), len(need), len(missed)), ""]
    if used:
        ds = sorted(r["dur"] for r in used)
        rep.append("采用段：中位 %.2fs，最短 %.2fs，最长 %.2fs；平均 %.1f 字/句；平均置信度 %.2f"
                   % (ds[len(ds) // 2], ds[0], ds[-1],
                      sum(len(norm(r["line"])) for r in used) / len(used),
                      sum(r["ts"] for r in used) / len(used)))
        rep.append("")
    if need:
        rep += ["## 需补读（音频本身有问题）", "", "| # | 稿子 | 机器听到 | 问题 |", "|---|---|---|---|"]
        for r in sorted(need, key=lambda x: x["j"]):
            rep.append("| %d | %s | %s | %s |" % (r["j"] + 1, r["line"],
                                                  (r["asr"] or "（空）")[:26], "、".join(r["hard"])))
        rep.append("")
    if lowc:
        rep += ["## 低置信采用（位置对得上，只是方言让识别文字偏了；建议抽听 3~5 条）", ""]
        for r in lowc[:40]:
            rep.append("- 第 %d 句 %.2fs sim=%.2f 「%s」← 机器听到「%s」"
                       % (r["j"] + 1, r["dur"], r["ts"], r["line"], (r["asr"] or "空")[:22]))
        if len(lowc) > 40:
            rep.append("- …另有 %d 条" % (len(lowc) - 40))
        rep.append("")
    if missed:
        rep += ["## 漏读", ""]
        for m in missed:
            rep.append("- 第 %d 句：%s" % (m["j"] + 1, m["line"]))
        rep.append("")
    unmatched = [i for i in range(len(items)) if i not in {a for a, _, _, _ in groups} and
                 i not in {gg for g in groups for gg in range(g[0], g[1])}]
    if unmatched:
        rep += ["## 未匹配音段（重读/口误/噪声，共 %d 段）" % len(unmatched), ""]
        for i in unmatched:
            rep.append("- %s %.1fs 「%s」" % (os.path.basename(items[i]["tmp"]),
                                            (items[i]["end"] - items[i]["start"]) / SR,
                                            (items[i]["asr"] or "（空）")[:30]))
        rep.append("")

    io.open(os.path.join(out, "报告.md"), "w", encoding="utf-8").write("\n".join(rep) + "\n")

    log("")
    log("✅ 采用 %d 句 / %.2f 分钟（低置信 %d）；需补读 %d 句"
        % (len(used), tot / 60, len(lowc), len(todo)))
    log("   清单：%s" % list_path)
    log("   报告：%s" % os.path.join(out, "报告.md"))
    log("   补读：%s" % os.path.join(out, "需补读.txt"))
    if len(todo) == 0:
        log("   （全部对齐成功，可以进训练）")


if __name__ == "__main__":
    main()
