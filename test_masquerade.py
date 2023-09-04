# -*- coding: utf-8 -*-
# Time       : 2023/9/4 9:40
# Author     : QIN2DIM
# GitHub     : https://github.com/QIN2DIM
# Description: 测试 hysteria2 masquerade
"""
测试 hysteria2 masquerade 是否正常
如何进行：
    0. 填写测试站点 `hy2_domain`
    1. 尝试开启或关闭系统代理
        但以下测试永远直连访问 hy2-domain 和 nginx-quic 站点
    2. 尝试使用或注释启动参数 `--enable-quic`
    3. 尝试使用或注释启动参数 `--origin-to-force-quic-on=[hy_domain]`
    4. 检查你的“网站”是否支持 HTTP/3
        https://http3check.net/
    5. 在 ./masquerade/ 查看运行截图和录制视频
"""
import asyncio
import logging
import sys
from pathlib import Path
from urllib.request import getproxies

from playwright.async_api import async_playwright, Browser, ProxySettings, TimeoutError, Page

logging.basicConfig(
    level=logging.INFO, stream=sys.stdout, format="%(asctime)s - %(levelname)s - %(message)s"
)

# 纪录浏览器运行的截图和录屏数据
record_dir = Path("masquerade")

# 用你服务器的域名替换
hy2_domain = ""

browser_args = [
    # "--enable-quic"  # enable quic 反而会伪装失败
    f"--origin-to-force-quic-on={hy2_domain}:443"
]

headless = False


async def test_browser_quic(browser: Browser):
    quic_h3_domain = "quic.nginx.org"

    context = await browser.new_context(
        record_video_dir=record_dir.joinpath("video Nginx QUIC"),
        proxy=bypass_system_proxy(quic_h3_domain),
    )
    page = await context.new_page()

    await page.goto(f"https://{quic_h3_domain}", wait_until="networkidle")

    async with page.expect_response("https://quic.nginx.org/test") as pkg:
        res = await pkg.value
        if "x-quic" in res.headers:
            logging.info(f"{quic_h3_domain} - Congratulations! You're connected over QUIC.")
        else:
            logging.warning(f"{quic_h3_domain} - You're not using QUIC right now")

    await page.screenshot(type="png", path=record_dir.joinpath(f"{quic_h3_domain}.png"))
    await context.close()


async def test_hy2_masquerade(browser: Browser):
    context = await browser.new_context(
        record_video_dir=record_dir.joinpath(f"video {hy2_domain}"),
        proxy=bypass_system_proxy(hy2_domain),
    )
    page = await context.new_page()

    try:
        await page.goto(f"https://{hy2_domain}", wait_until="networkidle", timeout=10000)
        await page.wait_for_timeout(500)
    except TimeoutError:
        logging.info(f"伪装触发成功，但访问状态未重置 - recur={page.url}")
    except Exception as err:
        logging.error(err)
        logging.info("伪装触发失败")
    else:
        logging.info(f"伪装触发成功 - {page.url=}")
        await deepin_check(page)

    await page.screenshot(type="png", path=record_dir.joinpath(f"{hy2_domain}.png"))
    await context.close()


async def deepin_check(page: Page):
    if not headless:
        logging.info("对测试站点进行任意的人为操作，维持30s")
        await page.wait_for_timeout(3000)


def bypass_system_proxy(bypass_domain: str | None = None) -> ProxySettings | None:
    system_proxy = getproxies()
    browser_proxy = {"bypass": bypass_domain or ""}

    for protocol in ["http", "https"]:
        if system_proxy.get(protocol):
            browser_proxy["server"] = system_proxy[protocol]
            logging.info(f"Enable system proxy - {browser_proxy=}")
            return browser_proxy

    logging.info("Unavailable system proxy, change to direct mode")


async def bytedance():
    if not hy2_domain:
        logging.error(f"填写域名 - {hy2_domain=}")
        return

    logging.info(f"startup - site={hy2_domain} {browser_args=}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False, proxy={"server": "per-context"}, args=browser_args
        )
        # 测试当前浏览器上下文是否支持 QUIC 收发包
        await test_browser_quic(browser)

        # 测试 Hysteria2 服务器是否能正常反代 HTTP/3 流量
        await test_hy2_masquerade(browser)

        logging.info(f"View record - path={record_dir.absolute()}")


if __name__ == "__main__":
    asyncio.run(bytedance())
