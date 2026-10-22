# VCA 补货监控

监控商品：Vintage Alhambra 手链 5 花 18K 黄金 虎眼石 VCARD35600，新加坡官网：
https://www.vancleefarpels.com/sg/en/collections/jewelry/alhambra/vcard35600---vintage-alhambra-bracelet-5-motifs.html

## 部署步骤
1. 新建一个 **Public** 仓库（Public 仓库的 Actions 免费不限时长；Private 每 5 分钟跑一次会很快用完免费额度），上传本目录全部文件。
2. 仓库 Settings → Secrets and variables → Actions → New repository secret：
   | 名称 | 内容 |
   |---|---|
   | `BARK_KEY` | Bark App 首页 URL 里 `api.day.app/` 后面那串 key |
   | `GMAIL_USER` | 发件 Gmail 地址 |
   | `GMAIL_APP_PASSWORD` | Google 账号 → 安全 → 两步验证 → 应用专用密码（16 位） |
   | `MAIL_TO` | 收件邮箱（不填则发给 GMAIL_USER） |
   | `BARK_SERVER` | 可选，自建 Bark 服务器地址 |
3. iPhone：设置 → 通知 → Bark → 打开 **“紧急警告/Critical Alerts”**，否则静音时不会响。
4. Actions 页面 → VCA restock monitor → Run workflow，依次选择 `test-email`、`test-bark`，确认手机响铃、收到邮件。
5. 最后手动运行一次 `check`：它会每 2 分钟检查一次，约 5.5 小时后自动接力启动下一次，一直跑下去，不用再管。

## 结果说明
- 绿色 ✅：检查正常（无货或有货且已提醒）
- 红色 ❌ 退出码 1：两个按钮都没看到（可能被反爬拦截或页面改版），在该次运行的 Artifacts 里下载截图查看
- 红色 ❌ 退出码 2：有货但提醒发送失败

有货期间每 10 分钟会再提醒一次，买到后在 Actions 页面点 “Disable workflow” 停止。

## 本地运行
```bash
pip install -r requirements.txt && python -m playwright install chromium
python monitor.py --headed          # 打开浏览器观察
python monitor.py --test-email      # 需先 export GMAIL_USER / GMAIL_APP_PASSWORD
```
按钮文字可在 `monitor.py` 顶部 `IN_STOCK_TEXTS` / `OUT_OF_STOCK_TEXTS` 修改。
