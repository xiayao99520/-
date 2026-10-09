# claude-news-collage · Claude 新闻拼贴分镜

由 Claude（Anthropic）制作的中文新闻短视频 Skill。

- 即梦视频提示词：**完整迁移** [xiayao99520/Repository-name-xy-to-make](https://github.com/xiayao99520/Repository-name-xy-to-make)（提交 `52351a7`）的 `video_prompt()`、schema 3 `image-plan`、`content_parameters()`、建包 / 校验 / 导出脚本与全部测试，文件逐字节相同（见 `VENDORED.json`）。
- 视觉风格：源自 [pyang5166/gbro-collage-broll](https://github.com/pyang5166/gbro-collage-broll) 的 editorial 半调纸拼贴。

## 流程（全自动，四步）

```text
① 按骨架写 image-plan.json（四张按口播顺序的独立画面，每张至少一个中文关键标签）
② python scripts/run.py start  --plan image-plan.json --output <内部父目录>
③ 同一批发出四个 Codex image_gen
④ python scripts/run.py finish --project <内部项目目录> --images 图1 图2 图3 图4
```

`run.py` 只是按原顺序调用原项目函数（校验 → 建包 → 逐字核对 → `make_package --video-only` → 导出），输出与原命令行流程逐字节一致。不请求确认，不做生成后的 AI 自查，不调用视频 API，不打包。

## 交付（未压缩文件夹）

```text
交付/YYYY-MM-DD-主题/
├── 01-建立场景.png
├── 02-关键对象.png
├── 03-动作关系.png
├── 04-结果冲突.png
└── 05-即梦视频提示词.txt   ← 原 video_prompt() 返回值
```

内部项目目录另有 `image-plan.json`、四份生图 Prompt、使用说明、剪映说明和可选的 `四图预览.jpg`。

## 安装与调用（Codex）

文件夹放在 `C:\Users\<你>\.codex\skills\claude-news-collage\`（或 `~/.agents/skills/`），重启 Codex 后：

```text
$claude-news-collage 票务平台也不能再随便拿票品属于特殊商品当借口拒绝退票。
```

## 在即梦中使用

Seedance 2.0 全能参考 → 按 01→04 上传四张图 → 粘贴 `05-即梦视频提示词.txt` 全文 → 9:16、按提示词中的秒数 → 生成 → 导入剪映。

## 目录

```text
claude-news-collage/
├── SKILL.md
├── VENDORED.json                   # 迁移文件的来源提交与 SHA-256
├── scripts/
│   ├── make_package.py             # 原 video_prompt()（逐字节迁移）
│   ├── image_prompts.py            # 原 content_parameters() 等（逐字节迁移）
│   ├── prepare_package.py / load_image_prompts.py / render_image_prompts.py
│   ├── export_delivery.py / access_control.py      # 逐字节迁移
│   ├── run.py                      # 新增：两步快速流程（只调用原函数）
│   ├── check_setup.py              # 新增：环境与本地控制检查
│   ├── check_plan_rules.py         # 新增：口播顺序与中文标签检查（只读）
│   ├── make_preview.py             # 新增：内部四图预览（可选）
│   └── legacy/                     # gbro 原 Gemini / Veo 脚本（兼容保留）
├── templates/  config/             # 逐字节迁移
├── references/
│   ├── image-plan.md  parallel-generation.md       # 逐字节迁移
│   └── 四图变化逻辑.md  变化逻辑参考/
├── examples/票务平台退票/image-plan.json
└── tests/                          # 原项目全部测试 + test_migration.py
```

测试：`python -m unittest discover -s tests`

## 许可

MIT。`LICENSE` 为 gbro-collage-broll 原许可，`LICENSE.xy-to-make` 为 xy-to-make 原许可；本版本由 Claude（Anthropic）制作。
