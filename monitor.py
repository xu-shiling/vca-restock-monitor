#!/usr/bin/env python3
"""Van Cleef & Arpels restock monitor.

Opens the product page with Playwright and decides stock status by which
purchase button is *actually visible* (both buttons always exist in the HTML).

Exit codes:
  0  check succeeded (in stock -> alerts sent, or out of stock)
  1  neither button visible -> screenshot saved for debugging
  2  in stock but at least one alert failed to send

Secrets (environment variables, set via GitHub Secrets):
  BARK_KEY            Bark device key
  BARK_SERVER         optional, default https://api.day.app
  GMAIL_USER          Gmail address used to send
  GMAIL_APP_PASSWORD  16-character Gmail App Password
  MAIL_TO             recipient address (defaults to GMAIL_USER)
"""

import argparse
import datetime as dt
import json
import os
import re
import smtplib
import sys
import urllib.request
from email.message import EmailMessage
from pathlib import Path

from playwright.sync_api import sync_playwright

# Only the Singapore and mainland China boutiques are monitored.
DEFAULT_URLS = [
    "https://www.vancleefarpels.com/sg/en/collections/jewelry/alhambra/"
    "vcard35600---vintage-alhambra-bracelet-5-motifs.html",
    "https://www.vancleefarpels.cn/cn/zh/collections/jewelry/alhambra/"
    "vcard35600---vintage-alhambra-bracelet-5-motifs.html",
]
# Case-insensitive; matched against the button's visible text.
IN_STOCK_TEXTS = ["add to bag", "add to cart", "buy now", "加入购物袋", "立即购买", "立刻购买"]
OUT_OF_STOCK_TEXTS = ["order by phone", "contact an ambassador", "call to order", "电话订购", "致电订购"]

CLICKABLE = "button, a, [role='button'], input[type='submit'], input[type='button']"

# Stricter than Playwright's is_visible(): also rejects opacity:0, `hidden`
# ancestors, zero-size boxes and elements pushed fully off-screen.
TRULY_VISIBLE_JS = """
el => {
  for (let n = el; n && n.nodeType === 1; n = n.parentElement) {
    const s = getComputedStyle(n);
    if (s.display === 'none' || s.visibility === 'hidden' || s.visibility === 'collapse') return false;
    if (parseFloat(s.opacity) === 0) return false;
    if (n.hasAttribute('hidden')) return false;
  }
  const r = el.getBoundingClientRect();
  if (r.width < 2 || r.height < 2) return false;
  const docW = Math.max(document.documentElement.scrollWidth, innerWidth);
  if (r.right <= 0 || r.left >= docW || r.bottom + scrollY <= 0) return false;
  return true;
}
"""


def log(msg):
    print(f"[{dt.datetime.now().isoformat(timespec='seconds')}] {msg}", flush=True)


def env(name, default=None, required=True):
    # Strip pasted whitespace, e.g. "abcd efgh ijkl mnop" app passwords.
    val = "".join((os.environ.get(name) or default or "").split())
    if required and not val:
        raise RuntimeError(f"missing environment variable {name}")
    return val


def visible_buttons(page, texts):
    """Return the texts of visible clickable elements matching any of `texts`."""
    pattern = re.compile("|".join(re.escape(t) for t in texts), re.I)
    found = []
    candidates = page.locator(CLICKABLE).filter(has_text=pattern)
    for i in range(candidates.count()):
        el = candidates.nth(i)
        try:
            if el.is_visible() and el.evaluate(TRULY_VISIBLE_JS):
                found.append(" ".join(el.inner_text().split()))
        except Exception:
            continue  # element detached during re-render
    # <input type=submit value="..."> has no inner text
    for el in page.locator("input[type='submit'], input[type='button']").all():
        try:
            if pattern.search(el.get_attribute("value") or "") and el.is_visible() and el.evaluate(TRULY_VISIBLE_JS):
                found.append(el.get_attribute("value"))
        except Exception:
            continue
    return found


def region(url):
    return "中国" if ".cn/" in url else "新加坡"


def check_stock(url, screenshot_dir, timeout_s, headed=False):
    """Return ('in_stock'|'out_of_stock'|'unknown', detail)."""
    with sync_playwright() as p:
        launch = {"headless": not headed, "args": ["--disable-blink-features=AutomationControlled"]}
        if os.environ.get("CHROMIUM_PATH"):
            launch["executable_path"] = os.environ["CHROMIUM_PATH"]
        browser = p.chromium.launch(**launch)
        ctx = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
            ),
            locale="zh-CN" if region(url) == "中国" else "en-SG",
            timezone_id="Asia/Shanghai" if region(url) == "中国" else "Asia/Singapore",
            viewport={"width": 1366, "height": 900},
        )
        page = ctx.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            # Stock status is filled in by JS after load; poll until one button shows up.
            start = dt.datetime.now()
            while True:
                elapsed = (dt.datetime.now() - start).total_seconds()
                in_stock = visible_buttons(page, IN_STOCK_TEXTS)
                out_stock = visible_buttons(page, OUT_OF_STOCK_TEXTS)
                if in_stock:
                    return "in_stock", f"visible: {in_stock}"
                # Give the page time to swap buttons before trusting "out of stock".
                if out_stock and elapsed >= min(10, timeout_s / 2):
                    return "out_of_stock", f"visible: {out_stock}"
                if elapsed >= timeout_s:
                    break
                page.wait_for_timeout(1000)

            screenshot_dir.mkdir(parents=True, exist_ok=True)
            tag = "cn" if region(url) == "中国" else "sg"
            shot = screenshot_dir / f"unknown_{tag}_{dt.datetime.now():%Y%m%d_%H%M%S}.png"
            page.screenshot(path=str(shot), full_page=True)
            return "unknown", f"no purchase button visible; title={page.title()!r}; screenshot={shot}"
        finally:
            browser.close()


def send_bark(title, body, url):
    server = env("BARK_SERVER", "https://api.day.app", required=False).rstrip("/")
    payload = {
        "device_key": env("BARK_KEY"),
        "title": title,
        "body": body,
        "level": "critical",  # rings through silent mode / Focus / sleep
        "volume": 10,
        "call": "1",          # repeat the ringtone for ~30s
        "sound": "alarm",
        "url": url,           # tap the notification to open the product page
        "group": "VCA",
    }
    req = urllib.request.Request(
        f"{server}/push",
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read().decode())
    if result.get("code") != 200:
        raise RuntimeError(f"Bark error: {result}")


def send_email(subject, body):
    user = env("GMAIL_USER")
    msg = EmailMessage()
    msg["From"] = user
    msg["To"] = env("MAIL_TO", user, required=False)
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(user, env("GMAIL_APP_PASSWORD"))
        smtp.send_message(msg)


def alert_in_stock(url, detail):
    title = f"VCA {region(url)}官网有货了！马上下单"
    body = f"{region(url)}官网 Vintage Alhambra 手链 5 花 虎眼石 (VCARD35600) 已可购买。\n{detail}\n{url}"
    ok = True
    for name, fn in (("Bark", lambda: send_bark(title, body, url)),
                     ("Email", lambda: send_email(title, body))):
        try:
            fn()
            log(f"{name} alert sent")
        except Exception as e:
            ok = False
            log(f"{name} alert FAILED: {e}")
    return ok


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", action="append", dest="urls",
                    help="product page to check; repeatable (default: Singapore + China)")
    ap.add_argument("--test-email", action="store_true", help="send a test email and exit")
    ap.add_argument("--test-bark", action="store_true", help="send a test critical Bark alert and exit")
    ap.add_argument("--timeout", type=float, default=30, help="seconds to wait for a button to appear")
    ap.add_argument("--screenshot-dir", type=Path, default=Path("screenshots"))
    ap.add_argument("--headed", action="store_true", help="show the browser (local debugging)")
    args = ap.parse_args()
    urls = args.urls or os.environ.get("PRODUCT_URL", "").split() or DEFAULT_URLS

    if args.test_email or args.test_bark:
        try:
            if args.test_email:
                send_email("VCA 补货监控 - 测试邮件", "邮件配置正常。\n监控页面:\n" + "\n".join(urls))
                log("test email sent")
            if args.test_bark:
                send_bark("VCA 补货监控 - 测试", "Bark 紧急提醒配置正常", urls[0])
                log("test Bark alert sent")
        except Exception as e:
            log(f"test FAILED: {type(e).__name__}: {e}")
            if isinstance(e, smtplib.SMTPAuthenticationError):
                log("Gmail rejected the login: check GMAIL_USER and GMAIL_APP_PASSWORD (16-char app password, 2-Step Verification on)")
            return 2
        return 0

    code = 0
    for url in urls:
        try:
            status, detail = check_stock(url, args.screenshot_dir, args.timeout, args.headed)
        except Exception as e:  # one site failing must not stop the other
            status, detail = "unknown", f"error: {e}"
        log(f"[{region(url)}] status={status} {detail}")
        if status == "in_stock" and not alert_in_stock(url, detail):
            code = 2
        elif status == "unknown" and code == 0:
            code = 1
    return code


if __name__ == "__main__":
    sys.exit(main())
