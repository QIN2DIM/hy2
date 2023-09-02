# Heyhy <a href = "https://t.me/+V1rQL8WFTNxiMjRh"><img src="https://img.shields.io/static/v1?style=social&logo=telegram&label=chat&message=studio" ></a>

Heyhy 用于快速部署 [hysteria2 server](https://github.com/apernet/hysteria) 并输出客户端最佳实践配置。只需 15s 即可完成全自动部署，开箱即用！

## Prerequisites

- Python3.7+
- 在管理员权限下运行
- 提前为你的服务器解析一个域名 A 纪录

## Get started

> 首次安装完毕后，你可以通过别名指令 `heyhy` 调度脚本。

1. **一键部署**

   在交互式引导下完成部署。脚本会在任务结束后打印代理客户端配置。
   ```shell
   python3 <(curl -fsSL https://ros.services/heyhy.py) install
   ```

   也可以直接指定域名参数「一步到胃」：

   ```shell
   python3 <(curl -fsSL https://ros.services/heyhy.py) install -d YOUR_DOMAIN
   ```

2. **移除负载**

   这个指令会移除与 `hysteria2 server` 有关的一切依赖。需要注意的是，你必须指明与 `hysteria2 server` 绑定的域名才能安全卸载证书。

   ```shell
   python3 <(curl -fsSL https://ros.services/heyhy.py) remove -d YOUR_DOMAIN
   ```

3. **查看所有指令**

   查看 [项目 WiKi](https://github.com/QIN2DIM/hy2/wiki/Usage) 以获取完整的技术文档🐧

   ```bash
   $heyhy -h
   
   usage: heyhy [-h] {install,remove,check,status,log,start,stop,restart} ...
   
   Hysteria-v2 Scaffold (Python3.7+)
   
   positional arguments:
     {install,remove,check,status,log,start,stop,restart}
       install             Automatically install and run
       remove              Uninstall services and associated caches
       check               Print client configuration
       status              Check hysteria2 service status
       log                 Check hysteria2 service syslog
       start               Start hysteria2 service
       stop                Stop hysteria2 service
       restart             restart hysteria2 service
   
   optional arguments:
     -h, --help            show this help message and exit
   ```

4. **常用操作**

   > 🚧 2023/09/02
   >
   > 以下文档为预留内容，目前仅可以使用类似 NekoRay 的客户端引导 hysteria2 client ；而 sing-box，clash-meta 等项目会将 hy2 打包进工程重新编译分发，可能暂时还不支持 hysteria2 代理出站。

   默认情况下会打印所有客户端配置，你可以通过可选的 `output-filter` 过滤指令仅输出 `NekoRay` / `clash-meta` / `sing-box` 的客户端出站配置：

   | Client                                                       | Command                                                      |
   | ------------------------------------------------------------ | ------------------------------------------------------------ |
   | [NekoRay](https://matsuridayo.github.io/n-extra_core/)       | `python3 <(curl -fsSL https://ros.services/heyhy.py) install --neko` |
   | [Clash.Meta](https://wiki.metacubex.one/config/proxies/tuic/) | `python3 <(curl -fsSL https://ros.services/heyhy.py) install --clash` |
   | [sing-box](https://sing-box.sagernet.org/configuration/outbound/tuic/) | `python3 <(curl -fsSL https://ros.services/heyhy.py) install --singbox` |

   你可以配合参数 `-d DOMAIN` 实现「一键输出」的效果，如：

   ```bash
   python3 <(curl -fsSL https://ros.services/heyhy.py) install --singbox -d YOUR_DOMAIN
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
