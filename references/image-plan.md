# Schema 3：逐图完整 Prompt

v3 修复旧流程中最关键的差异：四张图不是同一组五参数的四次改写，而是四个各自完整的语义画面。AI 需要先理解口播，再分别写四条最终交给 Codex `image_gen` 的完整 Prompt。程序只保存、编号、校验和传递这些正文，不把第一张的对象复制到其他图。

## JSON 契约

```json
{
  "schema_version": 3,
  "template_version": "3",
  "speech": "本次完整口播",
  "title": "项目名称",
  "duration_seconds": 6,
  "scene": "供 video_prompt 使用的共用场景摘要",
  "objects": "供 video_prompt 使用的共用对象摘要",
  "action": "供 video_prompt 使用的共用关系摘要",
  "result": "供 video_prompt 使用的共用结果摘要",
  "palette": "本组配色摘要",
  "frames": [
    {"number": 1, "role": "建立场景", "prompt": "完整的第1张图片 Prompt"},
    {"number": 2, "role": "关键对象", "prompt": "完整的第2张图片 Prompt"},
    {"number": 3, "role": "动作关系", "prompt": "完整的第3张图片 Prompt"},
    {"number": 4, "role": "结果冲突", "prompt": "完整的第4张图片 Prompt"}
  ]
}
```

`speech`、`scene`、`objects`、`action`、`result`、`palette` 供原 `video_prompt()` 使用。`frames[n].prompt` 是唯一的生图正文来源，不能存摘要、占位符或共同五参数拼接结果。四个 `role` 和 `number` 必须严格按顺序。

## 每条 Prompt 的旧流程共性

每条正文按本次题材自行组织，但必须保留以下可检查的共性：

- `Use case:`；
- `9:16` 竖屏新闻图生视频参考用途；
- `Premium editorial halftone paper collage`，黑白半调摄影剪贴、卡纸、奶油描边、纸张颗粒和柔和阴影；
- 主要信息位于 `middle core`；顶部是 `news headline` 安全区，只放次要纹理或装饰；
- `no English`、`no logo`、`no watermark`、`no UI`、`no subtitles`、`no 3D`；
- 题材需要时写明中文标签、数量、数字归属、否定关系和主题排除项。

共性只约束媒介、画幅和安全边界，不约束四张图使用同一组物件、同一坐标、同一画板或同一时间状态。每张正文必须明确本图主体、动作/关系、文字规则和排除项；可以没有可读文字，也可以根据口播只保留必要中文标签。

禁止写入：

- `same board`、`fixed composition for all four`、`no major relocation` 等跨图锁定语句；
- 把整句口播复制成字幕段落；
- 将其他图片的数字、标签、结果或物件无条件复制到本图；
- `0–2 秒` 等视频分秒导演指令；这些只属于即梦视频提示词，不能进入生图 Prompt。

## 旧记录兼容

schema 1 的结构化旧记录和 schema 2 的共享五参数记录仍可读取、重渲染和校验，渲染结果不转换、不覆盖；新素材包一律使用 schema 3。`tests/fixtures/v3/golden_old_thread_01a11588.json` 是用户确认线程中四条实际 `imageGeneration.revisedPrompt` 的只读回放证据，不是未来新题材的填空模板。

## 写入和校验顺序

1. AI 先完成四条完整正文和供视频函数使用的六项内容。
2. `prepare_package.py` 先验证四帧，再建立目录并写入全部文件。
3. `load_image_prompts.py` 将文件字节与 `frames[n].prompt` 加一个末尾 LF 的渲染结果逐字比较。
4. 全部通过后才可以同批调用四次 image_gen。
