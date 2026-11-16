# 夕语计划 · GitHub 开源项目调研

> 调研时间：2026-11-15 ｜ 检索维度：纪念类数字人、数字人形象、声音克隆、人格与记忆
> 说明：Star 数为调研时快照；许可证（License）需在选定后逐一核对，商用前务必确认。

---

## 一、核心结论

1. **没有可直接复用的"逝者数字人"完整开源产品。** 相关的垂直仓库全部是个位数 Star 的个人项目或学术实验，代码成熟度不足以支撑产品。
2. **但这个产品的四类"器官"都有顶级开源实现**：形象（口播/实时数字人）、声音（克隆 TTS）、人格（角色卡框架）、记忆（Agent 记忆层）。
3. **真正稀缺的不是技术，而是"人格工程"**：把一个人的一生结构化、写成可信的人格剧本、约束模型不编造——这部分开源社区没有现成答案，也正是你的差异化所在。
4. **建议路径**：以 Linly-Talker 或 CyberVerse 作为架构参考，用成熟单点组件拼装，而不是 fork 某个"同类产品"。

---

## 二、垂直同类项目（纪念 / 数字复活）

> 参考价值 > 使用价值。适合看别人怎么定义产品、怎么组织素材，不适合直接部署。

| 项目 | Star | 技术栈 | 说明 | 可用性判断 |
|---|---|---|---|---|
| [rosesman/Everwith](https://github.com/rosesman/Everwith)（云思园） | 1 | — | 概念最接近：用声音/文字/照片训练数字人格，支持语音通话、聊天、虚拟祭扫 | 代码量小，仅作产品思路参考 |
| [ShahaanK/Relic](https://github.com/ShahaanK/Relic) | 1 | Jupyter | 雪城大学 iSchool 研究项目，专攻 griefbot 的**人格工程与可扩展基础设施** | 学术价值高，工程价值低 |
| [Sanjukta-23/Griefbot](https://github.com/Sanjukta-23/Griefbot) | 0 | Python | 双向语音 + 焦虑安抚的哀伤陪伴机器人 | 原型级 |
| [cwchangggg/AI-Memorial-Generator](https://github.com/cwchangggg/AI-Memorial-Generator) | 1 | Python | 用语音与文字生成纪念短片 | 只覆盖"纪念视频"，非对话 |
| [gaozhongkui/DigitalResurrection](https://github.com/gaozhongkui/DigitalResurrection) | 0 | Kotlin / Swift | 安卓与 iOS 的 App 外壳，两个仓库 | 空壳，无 AI 能力 |

**检索噪音提示**：搜索 "GriefBot" 会大量命中游戏领域的"恶意捣乱机器人"（griefing），说明这个赛道的开源生态尚未形成。

---

## 三、数字人形象（口播视频 / 实时交互）

| 项目 | Star | 语言 | 能力 | 适用场景 |
|---|---|---|---|---|
| [duixcom/Duix-Avatar](https://github.com/duixcom/Duix-Avatar) | 16.3k | C | 离线视频生成 + 数字人克隆，可本地部署 | **照片生成说话视频的首选自建方案** |
| [lipku/LiveTalking](https://github.com/lipku/LiveTalking) | 10.4k | Python | 实时流式数字人，集成 MuseTalk / Wav2Lip / ER-NeRF | 实时对话形象（需 GPU） |
| [duixcom/Duix-Mobile](https://github.com/duixcom/Duix-Mobile) | 8.3k | C++ | 端侧实时数字人，延迟 < 1.5s | 做独立 App 时的移动端方案 |
| [OpenTalker/video-retalking](https://github.com/OpenTalker/video-retalking) | 7.3k | Python | SIGGRAPH Asia 2022，视频口型重配音 | 用老视频做"新说的话" |
| [Kedreamix/Linly-Talker](https://github.com/Kedreamix/Linly-Talker) | 3.5k | Python | **全链路**：ASR + LLM + TTS + SadTalker 口型 | **最佳架构学习样本，MIT 许可** |
| [tencent-ailab/V-Express](https://github.com/tencent-ailab/V-Express) | 2.4k | Python | 腾讯出品，参考图 + 音频 + 关键点序列 | 表情更自然，工程复杂度高 |
| [Lynpoint/CyberVerse](https://github.com/Lynpoint/CyberVerse) | 2.0k | Python | 自托管实时数字人 Agent 平台，含 **persona memory + RAG + WebRTC** | **与本项目形态最接近的全栈参考** |
| [ali-vilab/dreamtalk](https://github.com/ali-vilab/dreamtalk) | 1.8k | Python | 扩散模型驱动的表情化说话头 | 研究向 |
| [met4citizen/TalkingHead](https://github.com/met4citizen/TalkingHead) | 1.7k | JavaScript | 浏览器端 3D 实时口型，纯前端 | **Web 版最轻量方案，无需 GPU** |
| [Henry-23/VideoChat](https://github.com/Henry-23/VideoChat) | 1.3k | Python | 实时交互 + 音色克隆，延迟约 3s | 中文场景可参考 |
| [PunithVT/ai-avatar-system](https://github.com/PunithVT/ai-avatar-system) | 580 | Python | 上传照片 + 克隆声音 + 实时口型，FastAPI + Next.js | 工程结构清晰，MIT |

**技术判断**：若第一版只做"照片微动效 + 声音"，`met4citizen/TalkingHead`（纯前端）即可，零 GPU 成本；若要"照片说话视频"，用 `Duix-Avatar` 自建或直接买云服务；实时 3D 形象建议推迟到第 3 阶段。

---

## 四、声音克隆（TTS）

| 项目 | Star | 特点 | 建议 |
|---|---|---|---|
| [RVC-Boss/GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS) | 65.1k | **1 分钟数据即可微调**，中文社区事实标准，有成熟整合包 | **首选**，适合逝者素材通常很少的现实 |
| [2noise/ChatTTS](https://github.com/2noise/ChatTTS) | 40.0k | 对话口语感极强，韵律自然 | 不擅长克隆特定人，可做"自然度"参考 |
| [myshell-ai/OpenVoice](https://github.com/myshell-ai/OpenVoice) | 38.3k | 即时克隆 + 音色控制 | 快速验证可用 |
| [fishaudio/fish-speech](https://github.com/fishaudio/fish-speech) | 33.7k | SOTA 开源 TTS，多语言 | 效果好，部署偏重 |
| [index-tts/index-tts](https://github.com/index-tts/index-tts) | 25.1k | 工业级零样本克隆，中文强 | **强候选**，零样本无需训练 |
| [QwenAudio/CosyVoice](https://github.com/QwenAudio/CosyVoice) | 24.4k | 阿里出品，多语种，训练+部署全栈 | 企业级首选，生态完善 |
| [abus-aikorea/voice-pro](https://github.com/abus-aikorea/voice-pro) | 13.4k | 带 WebUI 的整合工具，含人声分离 | 素材预处理利器（去背景音乐） |
| [fishaudio/Bert-VITS2](https://github.com/fishaudio/Bert-VITS2) | 8.8k | 经典微调方案 | 备选 |
| [debpalash/VoiceStudio](https://github.com/debpalash/VoiceStudio) | 111.0k | 全本地 ElevenLabs 替代套件，含克隆/配音/转写 | Star 异常高但仓库很新，需评估成熟度 |
| [CorentinJ/Real-Time-Voice-Cloning](https://github.com/CorentinJ/Real-Time-Voice-Cloning) | 60.2k | 经典三阶段方案 | 已过时，不建议生产使用 |

**关键提醒**：声音克隆模型的开源许可证通常附带"不得用于冒充他人"条款；用于逝者时，必须取得近亲属书面授权，并保留授权凭证。

---

## 五、人格与记忆（产品的心脏）

| 项目 | Star | 语言 | 能力 | 用途 |
|---|---|---|---|---|
| [mem0ai/mem0](https://github.com/mem0ai/mem0) | 69.0k | Python | 生产级 Agent 记忆层，自动抽取/更新长期记忆 | **记忆系统直接可用** |
| [SillyTavern/SillyTavern](https://github.com/SillyTavern/SillyTavern) | 35.6k | JavaScript | LLM 角色扮演前端，有**角色卡 + World Info/Lorebook** 机制 | **"人格剧本"的最佳工程范式** |
| [MemoriLabs/Memori](https://github.com/MemoriLabs/Memori) | 17.6k | Python | Agent 原生记忆基础设施，企业向 | mem0 的替代 |
| [memvid/memvid](https://github.com/memvid/memvid) | 17.4k | Rust | 单文件记忆层，替代复杂 RAG | 轻量部署可选 |
| [Open-LLM-VTuber/Open-LLM-VTuber](https://github.com/Open-LLM-VTuber/Open-LLM-VTuber) | 14.7k | Python | 免手语音交互 + 打断 + Live2D 本地运行 | 语音陪伴形态参考 |
| [EverMind-AI/EverOS](https://github.com/EverMind-AI/EverOS) | 13.9k | Python | Markdown 原生的可移植记忆层，自演化 | 适合"记忆可读可审"的伦理需求 |
| [morettt/my-neuro](https://github.com/morettt/my-neuro) | 1.5k | JavaScript | 中文桌面伴侣：长期记忆 + 视觉识别 + 音色克隆 + Live2D，响应约 1s | **中文场景最接近的完整参考实现** |
| [IAAR-Shanghai/Awesome-AI-Memory](https://github.com/IAAR-Shanghai/Awesome-AI-Memory) | 1.3k | Python | AI 记忆知识库，持续更新 | 选型与论文索引 |

**Why SillyTavern matters**：它的 "Character Card + Lorebook" 正是你要的"人格设定 + 人生故事库"的成熟范式——角色卡定义性格与说话方式，Lorebook 按关键词动态注入相关往事。这套机制可低成本移植到自己的产品，比从零设计提示词体系可靠得多。

---

## 五之二、LiveTalking 专项评估（2026-11-15 补充）

**仓库**：lipku/LiveTalking ｜ 10.4k Star / 1.66k Fork / 241 Open Issues ｜ Apache-2.0 ｜ 作者 Hengzhong Li

### 定性
**它是一个"实时数字人推流引擎"，不是"数字人产品"。** 它解决的是"嘴和脸"——把音频变成同步口型并实时推流；它不解决"人格、记忆、故事"，`llm.py` 只是极简对话接口。定位判断错误会导致选型错配。

### 技术事实（据 README）
- 支持模型：ernerf、musetalk、wav2lip、Ultralight-Digital-Human
- 能力：声音克隆、说话打断、全身视频拼接、WebRTC/RTMP/虚拟摄像头输出、待机动作编排、多并发、自定义形象、前端 API（`/human`、`/humanaudio`、`/record`）
- TTS 已插件化对接：EdgeTTS、**GPT-SoVITS**、**CosyVoice**、腾讯云 —— 与本项目声音选型天然契合
- 架构分层清晰：API 层 → 逻辑层（LLM/TTS/特征提取）→ 渲染层（口型推理+贴回原视频）→ 推流层；插件通过 `registry.py` 注册
- 性能：wav2lip256 @ RTX 3060 = 60 FPS；musetalk @ 3080Ti/3090/4090 = 42/45/72 FPS；实时门槛 ≥25 FPS
- 部署：Docker 镜像（AutoDL / UCloud）、Windows 整合包、独立文档站

### 优势
1. **真流式、可打断**——这是陪伴型对话的关键体感，"能被打断"比"画质高"更影响真实感。
2. **Apache-2.0 + 明确商用**——README 自称"已在业内获得广泛商用"，社区与文档成熟度在同类中领先。
3. **TTS 插件化**——接 GPT-SoVITS / CosyVoice 无需改架构，正好复用我们的声音克隆方案。
4. **部署门槛明确**——3060 即可跑 wav2lip256，验证成本低。

### 对本项目的关键限制
1. **需要"驱动视频"而非单张照片**。`/avatar.html` 上传视频生成形象，要求正脸、稳定、有一定时长。逝者素材往往是低清老照片或手持家庭录像，**素材质量会直接击穿效果上限**。
2. **口型模型通病**：侧脸、大幅度表情、牙齿细节易崩；老照片放大后"恐怖谷"明显。这对纪念类产品是高风险——**不像比不做更伤人**。
3. **无记忆、无人格、无 RAG**。多用户会话管理有（sessionid），但长期记忆与知识库需完全自建。
4. **开源版与商用版功能分层**，增强模型（wav2lipls、自适应动作）仅在付费版，需先确认开源版是否满足。
5. **许可存在张力**：README 声明"基于本项目发布在 B站/视频号/抖音的视频需带 LiveTalking 水印"，这与 Apache-2.0 的宽松授权不完全一致。若用于公开传播，建议书面确认。
6. **单人主导项目**（bus factor 风险），241 个未关闭 Issue；作为长期产品底座需评估维护可持续性。
7. **实时 = GPU 成本线性增长**。家庭 1~2 人场景可接受；面向公众商业化时，每路并发都是成本。

### 在本项目中的定位建议
**列为路线 B 的"实时形象层"候选，但不作为第一优先级。**
- 理由：哀伤陪伴产品的核心价值是"说得像、记得住"，而非"看得见"。实时视频带来的恐怖谷风险与 GPU 成本，投入产出比低于先把人格与声音做扎实。
- 更优组合：**日常以文字/语音对话为主**（成本低、无恐怖谷），**特定时刻调用离线视频生成**（Duix-Avatar 类，画质更好、可按需生成一段"他说话"的视频作为仪式感时刻）。

### 低成本验证动作（1~2 小时）
取一段真实的老视频（正脸、30 秒以上）→ 走 `/avatar.html` 生成 avatar → 用 `/human` 驱动说一句家常话 → 观察三点：口型贴合度、面部边缘是否抖动、侧脸/表情是否崩坏。这一步即可判断是否值得投入。

---

## 六、推荐的两条拼装路线

### 路线 A：两周出可用原型（零 GPU、成本最低）

```
前端：Next.js 或直接微信小程序
人格：自研 System Prompt + Lorebook 式故事注入（参考 SillyTavern 结构）
记忆：mem0（托管版）
声音：云服务 TTS（火山/讯飞），先不做克隆
形象：met4citizen/TalkingHead 或纯静态照片
知识库：pgvector / Supabase 向量检索
```
- 优点：无需显卡，部署简单，两周可让家人试用
- 缺点：声音与形象不够"像"

### 路线 B：产品级自建（需 GPU 服务器）

```
形象：Duix-Avatar（离线视频）/ Duix-Mobile（App 端实时）
声音：GPT-SoVITS 微调（素材少时最优）+ voice-pro 做人声分离预处理
人格：SillyTavern 范式自研 + 严格 RAG 约束
记忆：mem0 或 EverOS（Markdown 可读，便于伦理审查）
编排：参考 Linly-Talker（全链路）/ CyberVerse（Agent+RAG+WebRTC）
```
- 优点：可控、可私有化、数据不出境
- 缺点：需 1 张 24G 显存以上 GPU，运维成本上升

---

## 七、必须注意的三个风险

1. **许可证风险**：Star 高不等于可商用。GPT-SoVITS 为 MIT，但部分数字人项目使用非商用许可或含第三方模型限制，选定后须逐一核对 LICENSE 与模型权重条款。
2. **克隆伦理风险**：声音/形象克隆类开源项目普遍在许可中禁止欺骗性使用。用于逝者场景，必须"近亲属授权 + 界面 AI 标识 + 不做公开传播"三件套。
3. **工程落差**：这些项目大多是"能跑通 demo"，离"多用户、可付费、稳定运行"仍有 3~6 个月工程量。不要低估从 demo 到产品的距离。

---

## 八、下一步建议

1. 先 clone 两个仓库跑通：`Linly-Talker`（看全链路架构）、`SillyTavern`（看人格剧本机制）
2. 用你手上的真实素材，在 SillyTavern 里手写第一版"人格卡"，一小时就能判断"像不像"
3. 若判断可行，再决定路线 A 或 B，并把选定的组件写进技术方案
