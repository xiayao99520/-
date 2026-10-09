---
name: claude-news-collage
description: 把「一段」中文新闻口播自动做成半调纸拼贴 B-roll 素材：按口播原文顺序设计四张独立画面（每张至少一个中文关键标签）→ 写成 schema 3 image-plan（四条完整生图 Prompt + speech/scene/objects/action/result/palette/duration_seconds）→ 四路同批 Codex image_gen → 由原项目 xy-to-make 的 video_prompt() 原样生成 05-即梦视频提示词.txt → 导出四张图片 + 一份提示词的未压缩交付文件夹。全程自动，不请求人工确认，不做生成后的 AI 自查。用户说“collage b-roll”“纸拼贴 b-roll”“半调拼贴”“拼贴风格配画面”“新闻口播拼贴分镜”“即梦拼贴提示词”“claude-news-collage”，或希望把一段口播转成拼贴参考图和即梦提示词时，必须使用此 skill。每次只处理一段口播；不调用任何视频 API。
compatibility: 在 Codex 环境运行（依赖内置 image_gen）。需要 Python >= 3.9；Pillow 仅用于可选的内部四图预览。不需要 GEMINI_API_KEY、ffmpeg 或任何视频 API。
---

# Claude 新闻拼贴分镜

> 由 Claude（Anthropic）制作。即梦视频提示词机制完整迁移自 [xiayao99520/Repository-name-xy-to-make](https://github.com/xiayao99520/Repository-name-xy-to-make)（提交 `52351a7`，MIT）；视觉风格源自 [pyang5166/gbro-collage-broll](https://github.com/pyang5166/gbro-collage-broll)（MIT）。

全程只有四步，一次跑完，不停下确认：

```text
① 写 image-plan.json  →  ② run.py start  →  ③ 同一批发出四个 image_gen  →  ④ run.py finish
```

`<本skill目录>` 指本 SKILL.md 所在目录。Windows PowerShell 中先设 `$env:PYTHONUTF8='1'`。每次只处理一段口播；一次给了多段独立新闻时只做第一段，并告诉用户其余分别调用。

## ① 写 image-plan.json（一次写对）

在任务目录写 `image-plan.json`，格式是原项目 schema 3（详见 [references/image-plan.md](references/image-plan.md)）。直接按下面的骨架填写，第一次就能通过校验：

```json
{
  "schema_version": 3,
  "template_version": "3",
  "speech": "完整口播原文",
  "title": "简短项目名",
  "duration_seconds": 6,
  "scene": "共用场景摘要",
  "objects": "关键对象摘要",
  "action": "动作关系摘要",
  "result": "最终结果摘要",
  "palette": "配色摘要",
  "frames": [
    {"number": 1, "role": "建立场景", "prompt": "…"},
    {"number": 2, "role": "关键对象", "prompt": "…"},
    {"number": 3, "role": "动作关系", "prompt": "…"},
    {"number": 4, "role": "结果冲突", "prompt": "…"}
  ]
}
```

JSON 注意：字符串里的换行写成 `\n`，英文双引号写成 `\"`（中文标签用中文引号 “…”，不用转义），最后一项后面不加逗号。

### 视频参数（原项目规则，原样进入 video_prompt）

- `speech`：完整口播原文。`duration_seconds`：有限正数，原项目默认 5，样例用 5 或 6。
- `scene` / `objects` / `action` / `result`：整组画面共用的场景、关键对象、动作关系、最终结果摘要，分别对应第 1–4 张图。
- `palette`：配色摘要，会接在“色彩使用”之后。
- 都写成单行短语，不在末尾加句号，不写动画指令，不写占位符（`TODO`、`待填写`、`<…>`、`{{…}}` 会被拒绝）。

它们被逐字填进原模板：`约 {duration} 秒…对应口播：{speech}…视觉隐喻：{scene}；关键对象：{objects}；动作关系：{action}；最终结果：{result}。…色彩使用{palette}。`

### 每条 frames.prompt 的骨架

尖括号部分换成本图内容（写完后不能留下尖括号），其余句子保留，原项目要求的固定词都已包含在内：

```text
Use case: ads-marketing.
Asset type: final still frame for a Chinese news explainer, 9:16 vertical image-to-video reference.
This frame illustrates the voiceover words 「<本图对应的口播原文片段>」 (meaning only; never render these words as text).
Create <景别> of <主体、动作和关系> in the middle core. <本图必须让观众看懂的一件事>.
Premium editorial halftone paper collage, flat <底色> paper field filling the whole vertical frame, black-and-white halftone cut-outs, <点色> cardstock accents, cream keylines, subtle paper grain and soft shadows. Background scenery, props and collage layers continue naturally up to the top edge. Keep the <核心主体> in the middle core; a news headline will be overlaid near the top later, so keep faces, key labels and the result out of the top area, but do not leave it as an empty band.
Use only the short Chinese label “<标签>” on <载体>, perfectly legible; <一句话说明在手机上一眼可读、又不喧宾夺主>.
<本图的排除项>, no extra text, no English, no logo, no watermark, no UI, no subtitles, no 3D.
```

填写规则：

- **按口播顺序一一对应**：口播原文按说话顺序切成四段，第 n 张对应第 n 段，四段连起来覆盖整段口播。口播说到什么，这张就画出对应的对象、行为或结果。
- **每张至少一个中文关键标签**，放在本图最该被认出的对象上；标签字号用自己的话按构图描述，在手机上清楚可读即可，不套固定句子或数值。
- **顶部**：画面一直铺到顶边，顶部照常有背景、场景和纸片；只是不要把人脸、关键标签和结果放在那里。不要写“留白”“空出顶部”“safe area with only secondary texture”这类会让顶部变成空白条的说法。
- **四张可以大幅变化**：景别、构图、主体造型、底色、重点都可以不同（如全景 → 特写 → 中景 → 全景）。不要写 `same board`、`fixed composition for all four`、`no major relocation` 等跨图锁定语句。用户给了参考图时，学习其变化逻辑，见 `references/四图变化逻辑.md`。
- 不把整句口播写成字幕，不写 `0–2 秒` 之类的视频分秒指令，四条正文互不相同。

完整示例：`examples/票务平台退票/image-plan.json`。

## ② run.py start

```bash
python <本skill目录>/scripts/run.py start --plan <image-plan.json> --output <内部父目录> [--date YYYY-MM-DD]
```

一次完成：原项目本地开关检查 → 原项目方案校验 + 口播顺序 / 标签检查（问题一次全部列出，未通过时不建任何目录）→ 原 `prepare_package.prepare()` 建包（含原 `load_image_prompts` 逐字核对）。成功时输出 JSON：`{"project": 内部项目目录, "prompts": [{number, path, prompt} × 4]}`。

未通过：按列出的问题一次改好 `image-plan.json`，再运行一次。

## ③ 同一批发出四个 image_gen

用 start 输出的四条 `prompt`，在同一条回复里同时发出四次 `image_gen`（做法同 [references/parallel-generation.md](references/parallel-generation.md)）：

- `transparent_background: false`；不传 `referenced_image_paths` 或 `num_last_images_to_include`；
- 结果按输入顺序对应 01—04；只有网络或超时错误可对失败编号补试一次；
- 不调用 `view_image`，不做视觉 QA，不因审美重做。

仍有编号失败时，如实告诉用户缺哪张并停止，不要用占位图。

## ④ run.py finish

```bash
python <本skill目录>/scripts/run.py finish --project <内部项目目录> --images <图1> <图2> <图3> <图4>
```

一次完成：四张图按编号复制进 `03-图片`（保留原字节与扩展名）→ 用 plan 里的参数调用原 `make_package.make()`（与 `make_package.py --video-only` 相同）写 `05-即梦视频提示词.txt` → 原 `export_delivery()` 原字节导出。输出交付目录路径。加 `--preview` 会在内部项目另写 `四图预览.jpg`（会多花几秒，默认不做）。

交付目录（未压缩，`<内部父目录>/交付/<日期-项目名>/`，重名自动加 `_02`）严格只有：

```text
01-建立场景.png  02-关键对象.png  03-动作关系.png  04-结果冲突.png  05-即梦视频提示词.txt
```

最后告诉用户：交付目录路径、四张图各对应哪段口播、即梦用法（Seedance 2.0 全能参考，按 01→04 上传，粘贴 05 全文，9:16，时长按提示词里的秒数）。视频由用户自己生成，不要声称视频已生成。

## 不可改动的部分

`VENDORED.json` 列出的 58 个文件是原项目提交 `52351a7` 的逐字节副本（`make_package.py` 的 `video_prompt()`、`image_prompts.py` 的 `content_parameters()`、建包 / 校验 / 导出脚本、模板、本地开关、`references/image-plan.md`、原测试）。不得编辑，不得另写生成即梦提示词的代码，不得润色、扩写或重组 `05-即梦视频提示词.txt`。想改提示词内容，只能改 plan 里的视频参数再运行 `run.py finish`。

`run.py` 只是把原函数按原顺序串起来，测试证明它的输出与原命令行流程逐字节相同。需要时也可以分步运行原命令行：`prepare_package.py` → `load_image_prompts.py` → `make_package.py --video-only` → `export_delivery.py`。

## 事后重做某一张

用户看完结果要求重做某张：只改 plan 中该帧 prompt，运行 `render_image_prompts.py --project <内部项目目录>`，单独重生该张，再运行 `run.py finish`（传入新图和其余三张原图），会生成新的编号交付目录。

## 测试

`python -m unittest discover -s <本skill目录>/tests`：原项目全部测试 + 迁移校验 + `run.py` 与原流程逐字节一致。

## 旧版视频脚本

`scripts/legacy/` 保留 gbro-collage-broll 原 Gemini / Veo 脚本，默认不调用；用户明确要求时才用，按量计费，需用户确认。
