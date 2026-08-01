# YouTube 下载器

拖拽式 YouTube 视频下载工具，绿色版无需安装 Python。把视频链接拖进窗口即可开始下载最高可用画质，也支持通过 Firefox 登录状态下载会员专属视频。

## 功能

- 拖拽 YouTube 链接自动开始下载
- 自动选择 `bestvideo*+bestaudio` 最高画质
- 自动合并为 MKV
- 支持 Firefox 登录状态，可下载会员视频
- 代理可自定义，留空时自动检测常见本地代理端口
- 绿色版自带 yt-dlp、ffmpeg、aria2、Node.js

## 使用

### 绿色版

1. 下载 zip 并解压整个文件夹。
2. 双击 `YouTubeDownloader.exe`。
3. 拖入 YouTube 链接，或粘贴后点击“开始下载”。

### 源码运行

需要 Python 3.11+：

```powershell
pip install -r requirements.txt
python YouTubeDownloader.pyw
```

## 会员视频

- 勾选“使用 Firefox 登录（会员视频）”
- 先在 Firefox 登录有会员权限的 YouTube 账号
- 下载前关闭 Firefox

## 代理

- 默认直连
- 勾选“代理”后可填写自己的代理地址
- 支持 `http://127.0.0.1:7890`、`socks5://127.0.0.1:1080` 等格式
- 留空会自动检测常见本地代理端口

## 打包

```powershell
pip install -r requirements.txt
python -m PyInstaller --noconfirm --clean --onedir --noconsole --name YouTubeDownloader --collect-all yt_dlp --collect-all tkinterdnd2 YouTubeDownloader.pyw
```

打包后把 `ffmpeg.exe`、`aria2c.exe`、`node.exe` 放进 `dist/YouTubeDownloader/` 即可。
