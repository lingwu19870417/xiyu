# -*- coding: utf-8 -*-
"""读稿录音 → 训练（GPT-SoVITS v2Pro，一键）

前提：先跑 align_script.py 得到 list.txt（标注已 100% 正确）

用法：
  python train_reading.py --list <输出目录>/list.txt --exp xiyu_rd --epochs 8
  python train_reading.py --list ... --exp xiyu_rd --prepare-only   # 只做预处理，先查标注
"""
import argparse
import glob
import io
import json
import os
import shutil
import subprocess
import sys
import time

GSV = r"D:\gpt-sovits\GPT-SoVITS-v2pro-20250604"
PY = os.path.join(GSV, "runtime", "python.exe")
LOGS = r"D:\gpt-sovits\logs"
PM = "GPT_SoVITS/pretrained_models"
BERT = PM + "/chinese-roberta-wwm-ext-large"
HUBERT = PM + "/chinese-hubert-base"
SV_CKPT = PM + "/sv/pretrained_eres2netv2w24s4ep4.ckpt"
S2G = PM + "/v2Pro/s2Gv2Pro.pth"
S2D = PM + "/v2Pro/s2Dv2Pro.pth"
S2CONF = "GPT_SoVITS/configs/s2v2Pro.json"
S1CKPT = PM + "/s1v3.ckpt"


def log(*a):
    print("[%s]" % time.strftime("%H:%M:%S"), *a, flush=True)


def run(script, env_extra, tag, logfile):
    env = os.environ.copy()
    env.update(env_extra)
    env.setdefault("PYTHONIOENCODING", "utf-8")
    log("▶", tag)
    with io.open(logfile, "a", encoding="utf-8", errors="replace") as f:
        f.write("\n\n===== %s %s =====\n" % (time.strftime("%F %T"), tag))
        f.flush()
        p = subprocess.run([PY, script], cwd=GSV, env=env, stdout=f, stderr=subprocess.STDOUT)
    if p.returncode != 0:
        tail = "".join(io.open(logfile, encoding="utf-8", errors="replace").readlines()[-25:])
        log("✗ 失败：", tag, "\n", tail)
        sys.exit(1)
    log("✓", tag)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--list", required=True)
    ap.add_argument("--exp", default="xiyu_rd")
    ap.add_argument("--epochs", type=int, default=8)
    ap.add_argument("--batch", type=int, default=4)
    ap.add_argument("--save-every", type=int, default=2)
    ap.add_argument("--prepare-only", action="store_true")
    args = ap.parse_args()

    list_path = os.path.abspath(args.list)
    rows = [l.strip() for l in io.open(list_path, encoding="utf-8") if l.strip()]
    if len(rows) < 20:
        log("样本太少（%d 条），先补录" % len(rows)); return
    wavs = [r.split("|")[0] for r in rows]
    wav_dir = os.path.dirname(wavs[0])
    total = 0.0
    import soundfile as sf
    for w in wavs:
        total += sf.info(w).duration
    log("样本 %d 句 / %.2f 分钟 / %s" % (len(rows), total / 60, wav_dir))

    exp = args.exp
    opt = os.path.join(LOGS, exp)
    os.makedirs(opt, exist_ok=True)
    lg = os.path.join(opt, "train.log")

    base = {"inp_text": list_path, "inp_wav_dir": wav_dir, "exp_name": exp,
            "i_part": "0", "all_parts": "1", "opt_dir": opt,
            "is_half": "True", "version": "v2Pro"}

    # 1. 文本 → 音素
    run("GPT_SoVITS/prepare_datasets/1-get-text.py",
        dict(base, bert_pretrained_dir=BERT), "1/6 文本→音素", lg)
    # 2. hubert 特征 + 32k wav
    run("GPT_SoVITS/prepare_datasets/2-get-hubert-wav32k.py",
        dict(base, cnhubert_base_dir=HUBERT), "2/6 hubert 特征", lg)
    # 3. 说话人向量（v2Pro 必需）
    run("GPT_SoVITS/prepare_datasets/2-get-sv.py",
        dict(base, sv_path=SV_CKPT), "3/6 说话人向量", lg)
    # 4. 语义 token
    run("GPT_SoVITS/prepare_datasets/3-get-semantic.py",
        dict(base, pretrained_s2G=S2G, s2config_path=S2CONF), "4/6 语义 token", lg)

    for src, dst in (("2-name2text-0.txt", "2-name2text.txt"),
                     ("6-name2semantic-0.tsv", "6-name2semantic.tsv")):
        a, b = os.path.join(opt, src), os.path.join(opt, dst)
        if os.path.exists(a):
            shutil.copyfile(a, b)
    for need in ("2-name2text.txt", "6-name2semantic.tsv"):
        if not os.path.exists(os.path.join(opt, need)):
            log("✗ 缺少", need, "—— 看日志", lg); return
    n_ok = sum(1 for _ in io.open(os.path.join(opt, "2-name2text.txt"), encoding="utf-8"))
    log("预处理完成：%d 条带标注样本" % n_ok)

    if args.prepare_only:
        log("--prepare-only：到此为止"); return

    # 5. SoVITS（声学）
    s2_log_dir = os.path.join(opt, "logs_s2_v2Pro")
    if os.path.isdir(s2_log_dir):
        bak = s2_log_dir + "_bak_" + time.strftime("%m%d_%H%M%S")
        shutil.move(s2_log_dir, bak)
        log("旧的 logs_s2_v2Pro 已挪走（否则会自动 resume 到旧轮次）：", os.path.basename(bak))
    os.makedirs(s2_log_dir, exist_ok=True)

    cfg2 = json.load(io.open(os.path.join(GSV, "tmp_s2_8.json"), encoding="utf-8"))
    cfg2["train"]["epochs"] = args.epochs
    cfg2["train"]["batch_size"] = args.batch
    cfg2["train"]["save_every_epoch"] = args.save_every
    cfg2["train"]["pretrained_s2G"] = S2G
    cfg2["train"]["pretrained_s2D"] = S2D
    cfg2["data"]["exp_dir"] = opt
    cfg2["s2_ckpt_dir"] = opt
    cfg2["save_weight_dir"] = "SoVITS_weights_v2Pro"
    cfg2["name"] = exp
    p2 = os.path.join(GSV, "tmp_s2_%s.json" % exp)
    json.dump(cfg2, io.open(p2, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    log("▶ 5/6 SoVITS %d 轮（几分钟到几十分钟）" % args.epochs)
    with io.open(lg, "a", encoding="utf-8") as f:
        subprocess.run([PY, "GPT_SoVITS/s2_train.py", "-c", p2],
                       cwd=GSV, stdout=f, stderr=subprocess.STDOUT, check=True)

    # 6. GPT（韵律）
    cfg1 = io.open(os.path.join(GSV, "tmp_s1_8.yaml"), encoding="utf-8").read()
    cfg1 = cfg1.replace("D:/gpt-sovits/logs/xiyu/logs_s1_v2Pro8",
                        os.path.join(opt, "logs_s1_v2Pro").replace("\\", "/"))
    cfg1 = cfg1.replace("exp_name: xiyu8", "exp_name: %s" % exp)
    cfg1 = cfg1.replace("epochs: 8", "epochs: %d" % args.epochs)
    cfg1 = cfg1.replace("save_every_n_epoch: 2", "save_every_n_epoch: %d" % args.save_every)
    cfg1 = cfg1.replace("D:/gpt-sovits/logs/xiyu/2-name2text.txt",
                        os.path.join(opt, "2-name2text.txt").replace("\\", "/"))
    cfg1 = cfg1.replace("D:/gpt-sovits/logs/xiyu/6-name2semantic.tsv",
                        os.path.join(opt, "6-name2semantic.tsv").replace("\\", "/"))
    cfg1 = cfg1.replace("batch_size: 4", "batch_size: %d" % args.batch)
    p1 = os.path.join(GSV, "tmp_s1_%s.yaml" % exp)
    io.open(p1, "w", encoding="utf-8").write(cfg1)
    log("▶ 6/6 GPT %d 轮" % args.epochs)
    with io.open(lg, "a", encoding="utf-8") as f:
        subprocess.run([PY, "GPT_SoVITS/s1_train.py", "-c", p1],
                       cwd=GSV, stdout=f, stderr=subprocess.STDOUT, check=True)

    sov = sorted(glob.glob(os.path.join(GSV, "SoVITS_weights_v2Pro", "%s_e*.pth" % exp)))
    gpt = sorted(glob.glob(os.path.join(GSV, "GPT_weights_v2Pro", "%s-e*.ckpt" % exp)))
    log("")
    log("✅ 训练完成")
    for p in sov:
        log("   SoVITS:", os.path.basename(p))
    for p in gpt:
        log("   GPT   :", os.path.basename(p))
    log("日志：", lg)


if __name__ == "__main__":
    main()
