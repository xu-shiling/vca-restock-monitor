帮我做一个奢侈品补货监控，一有货我要马上买。我不懂技术，部署时请一步步教我，能替我做的步骤就直接做。

## 监控对象
- 商品：Van Cleef & Arpels Vintage Alhambra 手链，5 花，18K 黄金，虎眼石，编号 VCARD35600，新加坡售价 S$8,100（含税）
- 只监控新加坡官网：https://www.vancleefarpels.com/sg/en/collections/jewelry/alhambra/vcard35600---vintage-alhambra-bracelet-5-motifs.html
  - 中国官网（vancleefarpels.cn）会拦截 GitHub 的服务器（页面显示"请求已被拦截"），不要放进 GitHub 的监控
  - /sg/zh/ 是同一个新加坡店的中文页面，库存相同，不要重复监控
- 收件邮箱：xushiling717@gmail.com

## 页面判断规则（已在真实页面上核实）
- 页面 HTML 里一直同时存在两个按钮，要判断哪个真正"可见"，不能只搜文字：
  - 有货：`ADD TO BAG`（中文页面显示"加入购物袋"）
  - 没货：`ORDER BY PHONE`（中文页面显示"通过电话订购"）
- 购买按钮的 class 都含 `vca-pdp-v2-cta-common`，同一个按钮有多份（电脑版、底部固定栏等）。只在这些元素里找，文字要完全一致，避免把页头的 "MY SHOPPING BAG" 或推荐商品的按钮误判为有货。
- "可见"的判断要严格：元素本身和所有父元素都不能是 display:none、visibility:hidden、opacity:0 或带 hidden 属性，尺寸也不能为 0。
- 页面上必须出现编号 VCARD35600 才继续判断，防止跳转到别的商品或被拦截时误报。
- 页面加载后，购买按钮由 JS 后填进去，要轮询等待几秒再下结论。

## 脚本要求（Python + Playwright）
- 退出码：0 = 检查正常（有货且已提醒，或没货）；1 = 两个按钮都看不到或找不到商品编号，并保存整页截图；2 = 有货但提醒发送失败
- 模式：
  - `--test-email`：发一封测试邮件
  - `--test-bark`：发一条测试紧急警报
  - `--probe`：列出页面上所有按钮的文字、是否可见和 class，用来核实页面结构
  - `--drill`：打开真实页面，把按钮切换成补货后的样子，走一遍完整的报警流程；提醒标题带"【演练，不是真的有货】"
- 有货时做两件事：
  1. Bark 推送：level=critical、call=1、音量 10，静音和睡眠模式下也要响；点通知直接打开商品页
  2. 用 Gmail 应用专用密码通过 SMTP 发邮件
- 所有密码和 key 从环境变量（GitHub Secrets）读取，不能写在代码里：BARK_KEY、GMAIL_USER、GMAIL_APP_PASSWORD、MAIL_TO（BARK_SERVER 可选）。读取时自动去掉空格（应用专用密码常带空格）。

## 部署（GitHub Actions）
- 用 Public 仓库（Actions 免费不限时长）
- 每 5 分钟定时检查一次，也可以手动运行，手动时能选择 check / test-email / test-bark / probe / drill
- 运行失败时把截图上传为 Artifact
- 交付一份中文 README，写清楚怎么填 Secrets、在 iPhone 上打开 Bark 的"紧急警告"、怎么测试，以及买到后怎么停用

## 验收步骤
依次手动运行 test-bark → test-email → probe → check → drill：手机要响、邮件要收到，check 显示没货（ORDER BY PHONE 可见），drill 能触发带"演练"标记的警报和邮件。
