# IPTV M3U 自动收集、测速、筛选、生成工具

这个项目会从 `config.yaml` 配置的公开 M3U/M3U8 地址和本地 M3U 文件收集直播源，异步测试可播放性和速度，按频道去重筛选，然后生成适合 Apple TV 上 APTV / iPlayTV 订阅的 `output/mytv.m3u`。

项目不会写死直播源，所有来源都从 `config.yaml` 读取。请只配置你有权使用的公开或自有源。

## 安装

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 配置

编辑 `config.yaml`：

```yaml
sources:
  urls:
    - https://iptv-org.github.io/iptv/countries/cn.m3u
  files:
    - ./local/example.m3u

network:
  timeout_seconds: 10
  concurrency: 30
  proxy: null

filter:
  keep_per_channel: 2
  channel_keywords: []
```

常用设置：

- `sources.urls`：远程 M3U 播放列表。
- `sources.files`：本地 M3U 文件路径。
- `network.timeout_seconds`：每个源测试超时时间。
- `network.concurrency`：并发测速数量。
- `network.proxy`：代理地址，例如 `http://127.0.0.1:7890`。
- `filter.keep_per_channel`：每个频道最多保留几个最快源，默认 2。
- `filter.channel_keywords`：只测试指定关键词，例如 `["CCTV", "湖南卫视"]`。空数组表示测试全部。

可选文件：

- `channel_aliases.yaml`：手动频道名映射。
- `blacklist.yaml`：屏蔽 URL 或频道关键词。

## 运行

```bash
python main.py
```

生成文件：

- `output/mytv.m3u`
- `output/report.md`
- `output/report.json`

## 在 Apple TV 中订阅

把项目推送到 GitHub，并让 GitHub Actions 生成 `output/mytv.m3u` 后，可以使用 raw URL 订阅：

```text
https://raw.githubusercontent.com/<你的用户名>/<仓库名>/main/output/mytv.m3u
```

在 APTV / iPlayTV 中新增远程 M3U 播放列表，填入上面的 raw URL 即可。

## GitHub Actions

`.github/workflows/update.yml` 会每天自动运行一次，也支持手动运行。它会安装依赖、执行 `main.py`，并把 `output/mytv.m3u`、`output/report.md`、`output/report.json` 自动提交回仓库。

## 说明

测速结果取决于运行机器当时的网络。如果你人在澳洲，建议在本机或澳洲网络环境的服务器上运行，这样筛选出来的源更贴近 Apple TV 实际播放体验。
