# 奢侈品补货监控：通用 Prompt

**用法**：复制下面分隔线之间的全部内容，把【】里的内容换成你自己的，然后发给 Claude Code（claude.ai/code）。
密码和 key **不要**填进 prompt 里，部署时 Claude 会教你把它们直接填到 GitHub 里。

**发之前先做两件事（各 1 分钟）**：
1. 在 https://github.com/new 新建一个空的 **Public** 仓库，比如叫 `restock-monitor`，下面的选项都不要勾。
2. 打开 https://github.com/apps/claude/installations/select_target ，把 Claude GitHub App 授权给这个仓库。

---

帮我做一个奢侈品补货监控，一有货我要马上买。我不懂技术，请一步步教我；能替我做的步骤（写代码、测试、上传到 GitHub）就直接做。

## 我的信息
- 商品链接：【粘贴商品页链接，例如 https://www.vancleefarpels.com/sg/en/collections/jewelry/alhambra/vcard35600---vintage-alhambra-bracelet-5-motifs.html】
- 商品编号：【例如 VCARD35600；不知道就写"请从页面里找"】
- 想监控哪个国家/地区的官网：【例如 新加坡；如果给的链接不是这个地区的，请帮我找到对应链接】
- 有货按钮文字：【例如 ADD TO BAG / 加入购物袋；不确定就写"请用 probe 模式核实"】
- 没货按钮文字：【例如 ORDER BY PHONE / 通过电话订购；不确定就写"请用 probe 模式核实"】
- 收件邮箱：【你的 Gmail 地址】
- 我的 GitHub 仓库：【例如 https://github.com/你的用户名/restock-monitor】（已新建为空的 Public 仓库，并授权了 Claude GitHub App）

## 参考实现
https://github.com/xu-shiling/vca-restock-monitor 是一个已经在真实页面上验证过的版本（监控 Van Cleef & Arpels 新加坡官网）。请以它为基础，只改商品链接、商品编号和按钮规则，不要从头重写。上传到我的仓库时，不要带上它的 PROMPT.md 里的个人信息。

## 判断规则
- 页面 HTML 里有货、没货两个按钮一直同时存在，要判断哪个真正"可见"，不能只搜文字。有货按钮可见就算有货。
- "可见"要严格判断：元素本身和所有父元素都不能是 display:none、visibility:hidden、opacity:0 或带 hidden 属性，尺寸也不能为 0。
- 按钮文字要完全一致，只在商品购买区的按钮里找，不要被页头的购物袋、推荐商品的按钮误导。
  （Van Cleef & Arpels 的购买按钮 class 都含 `vca-pdp-v2-cta-common`；其他品牌请先用 probe 模式找到对应的 class。）
- 页面上必须出现商品编号才继续判断，防止跳转到别的商品或被拦截时误报。
- 页面加载后，购买按钮一般由 JS 后填进去，要轮询等待几秒再下结论。

## 脚本要求（Python + Playwright）
- 退出码：0 = 检查正常（有货且已提醒，或没货）；1 = 两个按钮都看不到或找不到商品编号，并保存整页截图；2 = 有货但提醒发送失败
- 模式：
  - `--test-email`：发测试邮件
  - `--test-bark`：发测试紧急警报
  - `--probe`：列出页面上所有按钮的文字、是否可见和 class，用来核实页面结构
  - `--drill`：打开真实页面，把按钮切换成有货的样子，走一遍完整的报警流程；提醒标题带"【演练，不是真的有货】"
- 有货时做两件事：
  1. Bark 推送：level=critical、call=1、音量 10，静音和睡眠模式下也要响；点通知直接打开商品页
  2. 用 Gmail 应用专用密码通过 SMTP 给我的邮箱发邮件
- 所有密码和 key 从 GitHub Secrets 读取，代码里不能写死：BARK_KEY、GMAIL_USER、GMAIL_APP_PASSWORD、MAIL_TO。读取时自动去掉空格。

## 部署（GitHub Actions）
- 每 5 分钟定时检查一次，也可以手动运行，手动时能选择 check / test-email / test-bark / probe / drill
- 运行失败时把截图上传为 Artifact
- 附一份中文 README

## 请按这个顺序带我完成
1. 把代码上传到我的仓库
2. 教我拿到 Bark key，并在 iPhone 上打开 Bark 的"紧急警告"
3. 教我开两步验证、生成 Gmail 应用专用密码（提醒我不要把密码发在聊天里）
4. 教我在仓库 Settings → Secrets 里填 4 个密钥
5. 带我依次手动运行 test-bark → test-email → probe → check → drill，教我看日志在哪里，根据 probe 的结果修正按钮规则，直到 check 判断正确、drill 能让手机响铃并收到邮件
6. 告诉我买到后怎么停用监控

## 已知的坑
- 有些官网会拦截 GitHub 的服务器（check 报错，截图里是拦截页而不是商品页），这种网站不适合用 GitHub 监控，请如实告诉我。
- 同一个地区官网的不同语言页面（例如 /sg/en/ 和 /sg/zh/）库存相同，只监控一个。
- 提醒我：在旧的运行页面点 "Re-run jobs" 会用旧代码重跑，测试新代码要点 "Run workflow"。

---
