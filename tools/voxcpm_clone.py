# -*- coding: utf-8 -*-
"""VoxCPM2 命令行克隆工具。

用法（在 VoxCPM2 的 venv 里跑）：

    env\\Scripts\\python.exe tools\\voxcpm_clone.py ^
        --ref-wav D:\\path\\ref.wav --ref-text "参考音频的逐字文本" ^
        --text "要合成的话" --out out.wav

可选：
    --style "陕西话，年纪大的女声，语气亲切自然"   加在文本前的风格指令
    --cfg 2.0 --steps 10                          生成质量与速度权衡

注意：
    1. --ref-text 必须与 --ref-wav 逐字对应，错一个字音色就会漂。
    2. 参考音频必须从原始录音里连续截取（6~9 秒），不要拼接切片。
    3. 本脚本的 generate() 没有 seed 参数，别加。
"""
import argparse
import os
import sys
import time


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--vox-root", default=os.environ.get("VOXCPM_ROOT", r"D:\voxcpm"),
                    help="VoxCPM2 安装目录（含 pretrained_models/VoxCPM2）")
    ap.add_argument("--model-dir", default=None, help="模型目录，默认 <vox-root>/pretrained_models/VoxCPM2")
    ap.add_argument("--ref-wav", required=True)
    ap.add_argument("--ref-text", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--style", default="", help="风格指令，会加在文本前的括号里")
    ap.add_argument("--cfg", type=float, default=2.0)
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    # voxcpm 包按相对路径找配置，必须先切到安装目录
    os.chdir(args.vox_root)
    if args.vox_root not in sys.path:
        sys.path.insert(0, args.vox_root)

    import soundfile as sf
    from voxcpm import VoxCPM

    model_dir = args.model_dir or os.path.join(args.vox_root, "pretrained_models", "VoxCPM2")
    if not os.path.isdir(model_dir):
        sys.exit("模型目录不存在：%s" % model_dir)

    print("加载模型：%s" % model_dir)
    t0 = time.time()
    model = VoxCPM.from_pretrained(model_dir, load_denoiser=False)
    sr = model.tts_model.sample_rate
    print("加载完成 %.1fs，采样率 %d Hz" % (time.time() - t0, sr))

    text = args.text
    if args.style:
        text = "(%s)%s" % (args.style.strip("()"), text)

    t1 = time.time()
    wav = model.generate(
        text=text,
        prompt_wav_path=args.ref_wav,
        prompt_text=args.ref_text,
        reference_wav_path=args.ref_wav,
        cfg_value=args.cfg,
        inference_timesteps=args.steps,
    )
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    sf.write(args.out, wav, sr)
    dur = len(wav) / float(sr)
    cost = time.time() - t1
    print("%.2f 秒音频，耗时 %.1fs（RTF %.2f）→ %s" % (dur, cost, cost / max(dur, 1e-6), args.out))


if __name__ == "__main__":
    main()
