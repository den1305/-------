# 景点介绍 · 离线语音导游

输入或说出景点名称，即可获得**中英文图文介绍 + 中英双语语音朗读**。**全程离线**：检索、语音识别（ASR）、语音合成（TTS）均在本地完成，比赛现场无需联网、无需调用任何外部模型。

## 功能

- **文本输入**：输入框输入景点名称。
- **按住说话**：浏览器录音 → 本地离线语音识别（Paraformer）→ 自动查询。
- **本地词典检索**：精确名称 / 别名 → 拼音匹配 → 模糊匹配 → 未收录提示（含相近建议）。
- **中英双语回答**：同一次查询同时给出中文介绍与英文介绍（简介 / 历史沿革 / 主要看点 / 游览信息）。
- **中英双语语音朗读**：中文与英文均可朗读，页面提供「中文语音 / 英文语音」一键切换（默认中文），并支持「重新朗读」。

## 目录结构

```
app.py                  Flask 服务入口（本地网页后端）
requirements.txt        Python 依赖
core/
  retriever.py         本地词典检索（精确/别名/拼音/模糊）
  content.py           词条 → 中英文展示内容 + 朗读稿
  tts.py               离线语音合成封装（VITS，中/英模型自动识别）
  asr.py               离线语音识别封装（sherpa-onnx Paraformer）
data/
  spots.json           景点词典（**只需改这里即可换景点**）
templates/index.html   页面结构
static/app.js          前端交互（查询、录音、播放）
static/style.css       页面样式
models/                离线模型（Git LFS 管理）
  sherpa-onnx-vits-zh-ll/                     TTS 中文模型（中文朗读）
  vits-piper-en_US-amy-medium/                TTS 英文模型（英文朗读）
  sherpa-onnx-paraformer-zh-small-2024-03-09/ ASR 中文识别模型
```

## 环境要求

- **Python 3.10 – 3.12**（sherpa-onnx 官方 wheel 的覆盖范围，请勿使用 3.13/3.14）。
- Windows / macOS / Linux 均可运行；现场演示建议用 Windows。

## 快速开始

```bash
# 1. 创建虚拟环境
python -m venv .venv
# Windows：
.venv\Scripts\activate
# macOS / Linux：
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python app.py

# 4. 浏览器打开
#    http://127.0.0.1:5000
```

> 首次查询某个景点时会懒加载对应模型（约数秒），之后即秒级响应。

### 关于模型文件（Git LFS）

`models/` 下的 `*.onnx` 由 Git LFS 管理。克隆仓库后如果这些文件只有一百多字节，说明拿到的是 LFS 指针，需要拉取真实文件：

```bash
git lfs install
git lfs pull
```

### 端口 / 监听地址

可通过环境变量调整（默认 `127.0.0.1:5000`）：

```bash
set SCENIC_PORT=8000        # Windows
export SCENIC_PORT=8000     # macOS / Linux
python app.py
```

## HTTP 接口

| 方法 | 路径          | 说明 |
| ---- | ------------- | ---- |
| GET  | `/`           | 首页 |
| GET  | `/api/spots`  | 词典内全部景点名称 |
| POST | `/api/intro`  | 入参 `{"name": "故宫"}`，返回中英文展示内容 `zh` / `en` 与朗读稿 `narrate.zh` / `narrate.en` |
| POST | `/api/tts`    | 入参 `{"text": "...", "lang": "en", "speed": 1.0, "sid": 0}`，返回 WAV 音频（`lang` 取 `en` / `zh`） |
| POST | `/api/asr`    | 请求体为 WAV 字节，返回 `{"text": "..."}` |
| GET  | `/api/health` | 词典与各模型状态 |

## 替换景点（现场正式景点）

编辑 `data/spots.json`，按下面的字段结构增删条目即可，无需改动任何代码。
条目的**顶层字段为中文内容**，另有一个可选字段 **`en`** 承载英文内容（结构相同）：

| 字段         | 必填 | 说明 |
| ------------ | ---- | ---- |
| `id`         | 是   | 唯一标识（英文） |
| `name`       | 是   | 景点标准名称 |
| `aliases`    | 否   | 别名 / 俗称 / 口语叫法，用于提高命中率 |
| `category`   | 否   | 类别，如「历史古迹」「自然风光」 |
| `location`   | 否   | 所在地 |
| `open_info`  | 否   | 开放时间 |
| `intro`      | 否   | 简介（屏幕展示） |
| `history`    | 否   | 历史沿革（屏幕展示） |
| `highlights` | 否   | 主要看点（数组，屏幕列表展示） |
| `narrate`    | 否   | **中文朗读稿**；留空则用其他字段自动拼一段连贯话术 |
| `tags`       | 否   | 标签（数组），如「5A」「世界文化遗产」 |
| `en`         | 否   | **英文内容对象**，含同名子字段 `name`/`category`/`location`/`open_info`/`intro`/`history`/`highlights`/`narrate`/`tags`；其中 `narrate` 为**英文朗读稿**，供英文语音朗读使用 |

> 建议为每个景点撰写独立的 `narrate`（中文）与 `en.narrate`（英文）：它们比多个字段拼接更口语、更连贯，更适合朗读。
> `en` 缺失时英文分栏会显示占位符，英文语音也不会自动播放，因此正式景点请补齐 `en` 内容。

## Windows 免安装打包（PyInstaller）

在 Windows 的虚拟环境中执行：

```bat
pip install pyinstaller
pyinstaller --noconfirm --name ScenicGuide ^
  --add-data "templates;templates" ^
  --add-data "static;static" ^
  --add-data "data;data" ^
  --add-data "models;models" ^
  --collect-all sherpa_onnx ^
  app.py
```

- 打包结果在 `dist/ScenicGuide/`，双击其中的 `ScenicGuide.exe` 即可运行（无需安装 Python）。
- 由于内嵌了中英 TTS 与 ASR 三个模型，成品体积约 250 MB 以上，属正常现象；`--noconfirm` 免交互、`--collect-all sherpa_onnx` 用于带上 sherpa-onnx 的动态库与资源。
- macOS / Linux 打包时把 `--add-data` 的 `;` 换成 `:` 即可。

## 说明

- 全部逻辑均在本机运行，请在现场关闭网络后实测一遍，确认语音输入与朗读正常。
- 浏览器需允许麦克风权限；自动播放被拦截时，可点击页面上的「重新朗读」按钮。
