# Heyhy <a href = "https://t.me/+V1rQL8WFTNxiMjRh"><img src="https://img.shields.io/static/v1?style=social&logo=telegram&label=chat&message=studio" ></a>

Heyhy 用于快速部署 [hysteria2 server](https://github.com/apernet/hysteria) 并输出客户端最佳实践配置。只需 15s 即可完成全自动部署，开箱即用！

## What's features

| Supported Configuration         | Status |
| ------------------------------- | ------ |
| Hysteria2 server                | ✅      |
| NekoRay client proxy            | ✅      |
| sing-box `hy2` outbound         | ✅      |
| Clash.Meta `hysteria2` outbound | ✅      |
| Hysteria2 client                | 🚧      |
| via Cloudflare CDN              | ✅      |

## Prerequisites

- Python3.8+
- 在管理员权限下运行
- 提前为你的服务器解析一个域名 A 纪录

## Get started

> 首次安装完毕后，你可以通过别名指令 `heyhy` 调度脚本。

1. **服务部署**

   在交互式引导下完成部署。脚本会在任务结束后打印代理客户端配置。
   ```shell
   python3 <(curl -fsSL https://download.echosec.top/heyhy.py) install
   ```

   也可以直接指定域名参数「一步到胃」：

   ```shell
   python3 <(curl -fsSL https://download.echosec.top/heyhy.py) install -d YOUR_DOMAIN
   ```

   特殊地，如果你打算在无法直连 GitHub 的服务器上部署 hy2 server，可以使用 `--enable-cdn` 参数：

   ```bash
   python3 <(curl -fsSL https://download.echosec.top/heyhy.py) install --enable-cdn -d YOUR_DOMAIN
   ```

2. **移除负载**

   这个指令会移除与 `hysteria2 server` 有关的一切依赖。需要注意的是，你必须指明与 `hysteria2 server` 绑定的域名才能安全卸载证书。

   ```shell
   python3 <(curl -fsSL https://download.echosec.top/heyhy.py) remove -d YOUR_DOMAIN
   ```

## What's next

```bash
# heyhy
usage: 49 [-h] {install,remove,check,status,log,start,stop,restart,update,edit} ...

Hysteria-v2 Scaffold (Python3.8+) T:2025-03-15

positional arguments:
  {install,remove,check,status,log,start,stop,restart,update,edit}
    install             Automatically install and run
    remove              Uninstall services and associated caches
    check               Print client configuration
    status              Check hysteria2 service status
    log                 Check hysteria2 service syslog
    start               Start hysteria2 service
    stop                Stop hysteria2 service
    restart             Restart hysteria2 service
    update              Keep the configuration information unchanged, only update the service
    edit                Edit the server configuration

options:
  -h, --help            show this help message and exit
```

默认情况下会打印所有客户端配置，你可以通过可选的 `output-filter` 过滤指令仅输出 `NekoRay` / `clash-meta` / `sing-box` 的客户端出站配置：

| Client                                                       | Command                                                      |
| ------------------------------------------------------------ | ------------------------------------------------------------ |
| [NekoRay](https://matsuridayo.github.io/n-extra_core/)       | `python3 <(curl -fsSL https://download.echosec.top/heyhy.py) install --neko` |
| [Clash.Meta](https://wiki.metacubex.one/config/proxies/tuic/) | `python3 <(curl -fsSL https://download.echosec.top/heyhy.py) install --clash` |
| [sing-box](https://sing-box.sagernet.org/configuration/outbound/tuic/) | `python3 <(curl -fsSL https://download.echosec.top/heyhy.py) install --singbox` |

你可以配合参数 `-d DOMAIN` 实现「一键输出」的效果，如：

```bash
python3 <(curl -fsSL https://download.echosec.top/heyhy.py) install --singbox -d YOUR_DOMAIN
```

首次安装后，你还可以使用别名缩写 `heyhy` 更新（覆盖）双端配置，如：

```bash
heyhy install --singbox -d YOUR_DOMAIN
```

所有出站配置已在 `install` 指令后生成，`output-filter` 仅影响输出到屏幕的信息，你可以用 `check` 命令去查看它们，如：

```bash
heyhy check
```

或搭配 `output-filter` 使用，效果和上文的一致：

```bash
heyhy check --neko
```
