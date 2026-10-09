# 四路生图调用

四份完整 Prompt 必须先落盘，并由加载器核对模板输出，才开始任何生图。调用位置采用本 Skill 安装目录；PowerShell 参数使用单引号并转义其中的单引号。

```javascript
const skillDir = "C:/Users/Administrator/.codex/skills/gbro-jimeng-collage-broll-audited";
const quotePS = value => "'" + value.replaceAll("'", "''") + "'";
const loaded = await tools.exec_command({
  cmd: "$env:PYTHONUTF8='1'\npython " + quotePS(skillDir + "/scripts/load_image_prompts.py") +
    " --project " + quotePS(projectDir),
  max_output_tokens: 16000
});
if (loaded.exit_code !== 0) throw new Error("参数或模板输出不一致，先修复并重渲染");
const prompts = JSON.parse(loaded.output);
if (prompts.length !== 4 || prompts.some((item, i) =>
  Number(item.number) !== i + 1 || typeof item.prompt !== "string" || !item.prompt.trim()
)) throw new Error("四份 Prompt 编号或正文不完整");

const requestImage = async prompt => {
  const result = await tools.image_gen__imagegen({ prompt, transparent_background: false });
  if (result?.isError === true) {
    const message = (result.content ?? []).filter(item => item.type === "text")
      .map(item => item.text).join("\n");
    throw new Error(message || "image_gen 返回错误");
  }
  return result;
};
const requests = prompts.map(({ prompt }) => requestImage(prompt));
const results = await Promise.allSettled(requests);
const retryIndexes = results.flatMap((item, i) =>
  item.status === "rejected" &&
  /network|timeout|timed out|ECONNRESET|ETIMEDOUT|网络|超时/i.test(
    String(item.reason?.message ?? item.reason)
  ) ? [i] : []
);
if (retryIndexes.length) {
  const retried = await Promise.allSettled(
    retryIndexes.map(i => requestImage(prompts[i].prompt))
  );
  retried.forEach((item, i) => { results[retryIndexes[i]] = item; });
}
const failed = [];
results.forEach((item, i) => {
  const number = String(i + 1).padStart(2, "0");
  if (item.status === "fulfilled") store("trial_imagegen_result_" + number, item.value);
  else failed.push(number);
});
if (failed.length) throw new Error("仍缺少成功请求：" + failed.join("、"));
```

四次调用使用 plan 中已经保存的四条完整独立 Prompt；不再把共享五参数重复拼进四张图。每条 Prompt 必须已经包含旧流程的风格标记、顶部安全区和逐图排除项。不传 `referenced_image_paths` 或 `num_last_images_to_include`。`results[0]` 对应 01，依此类推，完成先后不改变编号。对错误只按网络或超时补试一次，不补试服务拒绝或内容错误。

工具返回成功后，读取实际图片路径，复制到内部项目的 `03-图片/01-建立场景`、`02-关键对象`、`03-动作关系`、`04-结果冲突`，保留实际扩展名、原始尺寸与字节。不要猜测返回路径，也不要用前一张图作后续参考。

成功请求都保留；四个编号的文件均存在且非空才进入视频提示词阶段。若补试后仍失败，说明缺失编号并停止最终导出。生成后不目视检查、不调用 `view_image`、不制作拼图或视觉 QA，也不根据审美判断重生。
