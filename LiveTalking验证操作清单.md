# LiveTalking 形象验证 · 操作清单

> 目的：用一段真实老视频，验证 LiveTalking 能否做出"像他"的说话形象。
> 适用前提：**必须有一块 NVIDIA 显卡**。无显卡则本清单不适用，直接走扣子方案。
> 参数依据：lipku/LiveTalking 官方 `docs/api.md`、`docs/avatar_api.md`（2026-11 版本）

---

## 第 0 步：先自查硬件（5 分钟，决定要不要继续）

打开 Windows 的「任务管理器」→「性能」标签 → 看左侧有没有「GPU」，点开后看右上角显卡型号。

| 自查结果 | 结论 |
|---|---|
| 有 NVIDIA GeForce/RTX 显卡，显存 8GB 以上 | ✅ 可以本地跑，零成本 |
| 有 NVIDIA 显卡但显存 4~6GB | ⚠️ 只能跑 wav2lip 低分辨率，效果打折 |
| 只有 Intel 核显 / AMD 显卡 / Mac | ❌ 跑不了，**停止本流程** |
| 完全没有独显 | ❌ 跑不了，**停止本流程** |

官方给的实测数据（可作为性能参照）：

| 模型 | 显卡 | 帧率 |
|---|---|---|
| wav2lip256 | RTX 3060 | 60 FPS |
| wav2lip256 | RTX 3080Ti | 120 FPS |
| musetalk | RTX 3080Ti / 3090 / 4090 | 42 / 45 / 72 FPS |

实时门槛是 **≥25 FPS**。低于这个数，嘴型会明显滞后。

---

## 第 1 步：把服务跑起来

### 方式 A：Windows 整合包（零基础首选）

1. 下载作者提供的 Windows 整合包（README 里有夸克网盘链接）
2. 解压到一个**路径不含中文和空格**的目录，例如 `D:\livetalking`
3. 双击启动脚本（通常是 `run.bat` 或 `启动.bat`）
4. 看到日志出现监听 `8010` 端口即成功

### 方式 B：手动安装（Ubuntu，略过，零基础不建议）

```bash
git clone https://github.com/lipku/LiveTalking.git
conda create -n livetalking python=3.12
conda activate livetalking
pip install torch==2.9.1 torchvision==0.24.1 torchaudio==2.9.1 --index-url https://download.pytorch.org/whl/cu128
cd LiveTalking && pip install -r requirements.txt
```

### 下载模型

从 README 提供的网盘下载后：

| 文件 | 放到 | 重命名为 |
|---|---|---|
| `wav2lip256.pth` | `models/` | `wav2lip.pth` |
| `wav2lip256_avatar1.tar.gz` | 解压后整个文件夹放入 `data/avatars/` | 保持原名 |

### 启动

```bash
python app.py --transport webrtc --model wav2lip --avatar_id wav2lip256_avatar1
```

> 端口要求：TCP **8010** 开放，UDP **1-65536** 开放。本机使用一般无需改防火墙；若从别的设备访问，需放行。

---

## 第 2 步：用 `/avatar.html` 生成他的形象

### 素材要求（决定成败）

| 要求 | 说明 |
|---|---|
| 正脸 | 脸部朝向镜头，偏转不超过 30 度 |
| 时长 | 30 秒以上，越长越稳 |
| 画面 | 头部基本不动，背景干净，无遮挡（口罩、手、麦克风） |
| 光线 | 均匀，不要一半脸在阴影里 |
| 分辨率 | 720p 以上；老录像 480p 也能跑，但放大后失真明显 |
| 声音 | 有无都可，形象生成只取画面 |

### 操作

**方式 A：网页（推荐）**

1. 浏览器打开 `http://127.0.0.1:8010/avatar.html`
2. 模型选 `wav2lip`
3. 填写 `avatar_id`，用英文小写，例如 `laochen`
4. 上传视频
5. 点「创建任务」，等待进度到 100%
6. 生成结果保存在 `data/avatars/laochen/`，内含 `full_imgs/`、`face_imgs/`、`coords.pkl`

**方式 B：接口调用**

```bash
curl -X POST http://127.0.0.1:8010/api/avatar/task \
  -F "model=wav2lip" \
  -F "avatar_id=laochen" \
  -F "video_file=@D:/素材/老陈_正面30秒.mp4" \
  -F "img_size=256"
```

返回：

```json
{ "code": 0, "msg": "ok", "data": { "task_id": "uuid-..." } }
```

查询进度：

```bash
curl http://127.0.0.1:8010/api/avatar/task/<task_id>
```

`status` 会经历 `pending` → `running` → `completed`；`progress` 为 0~100。

---

## 第 3 步：用 `/human` 驱动他说话

### 关键机制（必须理解，否则调不通）

`/human` 需要一个 `sessionid`，而 **`sessionid` 只在建立 WebRTC 连接时产生**（来自 `POST /offer` 或 `POST /whep` 的响应）。因此：

- **零基础用户**：直接用网页 `http://127.0.0.1:8010/index.html`，点「开始连接」，在文本框输入文字提交。**效果与调用 API 完全一致**，不需要写任何代码。
- **要做集成时**：先建立连接拿 `sessionid`，再调 `/human`。

### 接口形态（供后续集成参考）

```bash
curl -X POST http://127.0.0.1:8010/human \
  -H "Content-Type: application/json" \
  -d '{
        "sessionid": "<从 /offer 或 /whep 响应取得>",
        "text": "丫头，吃饭了没",
        "type": "echo",
        "interrupt": false
      }'
```

参数说明：

| 参数 | 必填 | 说明 |
|---|---|---|
| `sessionid` | 是 | 会话 ID，WebRTC 连接时生成 |
| `text` | 是 | 要他说的话 |
| `type` | 是 | `echo` 直接复读；`chat` 交由 LLM 生成回复 |
| `interrupt` | 否 | `true` 表示打断当前播报 |
| `tts` | 否 | 透传音色/情绪等配置 |

### 其他可用接口

| 接口 | 用途 |
|---|---|
| `POST /interrupt_talk` | 立即清空播报队列（打断） |
| `POST /is_speaking` | 查询当前是否在说话 |
| `POST /record` (`type=start_record` / `end_record`) | 开始/结束录制 |
| `GET /record/{sessionid}` | 下载录制好的 MP4 |

> **这个录制功能对你很有用**：驱动他说一段话，录下来，就是一条可发家庭群的"他说话"视频，比剪映里的通用数字人真实得多。

---

## 第 4 步：看三个指标（判断值不值得继续）

| 指标 | 合格标准 | 不合格的表现 |
|---|---|---|
| 口型贴合 | 字与口型基本同步，误差肉眼不明显 | 声音先到、嘴后动，或反过来 |
| 面部稳定 | 脸部边缘不抖动、不"融化" | 下巴和脖子交界处有波纹、色块跳动 |
| 表情自然 | 眨眼、微表情存在 | 全程一个表情，像贴了张会动的照片 |

**补充观察**：让他说一句带情绪的话（例如"你怎么又不听话"），看眉毛和嘴角有没有变化。**静态照片驱动最大的问题就是"没有情绪"，这一项比口型更能决定家人的接受度。**

---

## 成本现实（重要）

| 场景 | 成本 | 判断 |
|---|---|---|
| 自有 NVIDIA 显卡 | ¥0（仅电费） | 值得试 |
| 无显卡，租 GPU 按小时 | 约 ¥1.5~5/小时，验证一次约 2 小时 | 属于小额支出，与"零预算"原则冲突 |
| 无显卡，买云服务器包月 | 数百元起 | 不建议，与项目目标不匹配 |

---

## 我的建议

1. **先做第 0 步自查。** 没有 NVIDIA 显卡，这条路对你就不成立，不必再研究。
2. **有显卡的话，值得花两小时验一次。** 因为这是唯一能让你亲眼看到"他动起来"的方式，判断价值高于任何文字评估。
3. **验完就停。** 不要顺着往下做集成——那是几个月的工程量。把结论带回扣子方案：形象能不能用、素材够不够、家人看了什么反应。
4. **无论结果如何，先把对话做扎实。** 形象是加分项，人格和记忆才是主体。

---

## 附：老素材的预处理建议

| 问题 | 处理 |
|---|---|
| 录像抖动 | 剪映开防抖，或截取相对静止的 30 秒 |
| 画质低（480p） | 用剪映"超清画质"增强后再喂给模型 |
| 只有照片 | wav2lip 需要视频；可先用剪映把照片做成 30 秒"微动"视频，但效果会明显下降 |
| 有背景音乐 | 用 `voice-pro` 或剪映分离人声，形象生成虽不用声音，但音频驱动时需要 |
| 多人出镜 | 必须裁成单人镜头，否则人脸检测会跳 |
