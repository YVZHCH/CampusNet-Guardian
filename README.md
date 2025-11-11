# CampusNet-Guardian / 校园网助手

一个基于 python + pyqt5 的校园网自动登录与网络守护程序。

本项目在 up 主 [猪肉四喜丸子](https://space.bilibili.com/363076511)原版基础上进行了以下改进：
- ✅ 使用 **PyQt 自绘通知** 替代系统 Toast，解决兼容性问题  
- ⚙️ 优化 **登录检测逻辑**，区分登录返回与联网状态（同时补充科学网络环境的检测兼容）  
- 🔁 增加 **持续登录守护**，断网后自动重连  
- 💾 支持配置保存与修改  
- 🖥 托盘常驻运行，显示实时状态  

---

## 功能概览
- 自动检测网络连接状态
- 网络断开时自动登录校园网
- 登录信息可通过 GUI 修改并保存到 `config.json`
- 自定义托盘菜单（修改登录信息 / 关于 / 退出）
- 屏幕右下角浮动通知，无系统依赖
- 鼠标悬停托盘图标可实时查看状态
- **⚠️程序没有主界面，运行后直接在托盘放置图标！**

### 运行平台
- Windows 10 / 11（已测试）
- ……
  
---

## 运行方式

### 快速运行（不推荐）

以下方式需要已安装 **Python 环境**，并会在系统环境中安装外部依赖包。  
**不建议小白使用。**  
如确需运行，强烈建议在 **独立虚拟环境** 中进行，以免影响其他 Python 项目。

#### 一、安装依赖
```bash
pip install -r requirements.txt
```

#### 二、尝试运行
```bash
python heartbeat_login_pyqt.py
```
- 首次启动会提示填写用户名、密码和登录服务器 IP  
- 信息会自动保存到 `config.json`，下次启动无需重复填写  

#### 三、打包为独立程序

使用 PyInstaller 打包：

```bash
pip install pyinstaller
pyinstaller -F -w heartbeat_login_pyqt.py
```

打包完成后，生成的文件位于：
```
dist/heartbeat_login_pyqt.exe
```
放置在不会变动/误删的目录，加入自启动
- 首次启动会提示填写用户名、密码和登录服务器 IP  
- 信息会自动保存到 `config.json`，下次启动无需重复填写
- 也可以将项目目录下的 `config.json`复制到程序同目录

---

### 委托打包方式（适合不会配置环境的用户）

如果你无法完成打包，可以将修改好的文件发送给我代打包：

📱 **添加微信：YVZHCH**  
备注：校园网助手打包  
请同时提供你修改后的 `.py` 文件
**免费提供帮助，不过平时较忙可能咕咕**

---

## 可修改部分（必须进行）

**如果下面的内容对你来说有难度，也可以添加联系方式委托修改**

在 `heartbeat_login_pyqt.py` 中，可根据你学校的校园网规则调整以下内容：

### 🔗 登录请求与加密规则

#### 加密规则
```python
def encrypt_data(data):
    ...
```
该函数用于加密用户名、密码、IP 地址。  
如果你的校园网加密规则不同，可在此处修改加密方式。
如果你的校园网没有加密，直接用下面的代码替换：
```python
def encrypt_data(data):
    return data
```

#### 附加修改
```python
modified_username = f',0,{username}'
```
此处是针对部分校园网对用户名先拼接“,0,”再加密的处理方式。
如果你的校园网变化规则不同，可修改“,0,”部分，**不要直接删去此行**

### 🌐 登录 URL
```python
url = (f"https://{login_IP}:802/eportal/portal/login?...")  # 第 630 行附近
```
根据你学校的登录系统调整：
- URL 根据视频教程进行修改
- 注意 URL 内的参数名保持不变，如 `{login_IP}` 等

### 🧾 登录页与成功页识别
```python
not_sign_in_title = '上网登录页'
result_return = '成功'
signed_in_title = '用户信息页'
```
说明：
- `not_sign_in_title`：校园网登录页的标题（未登录状态）
- `signed_in_title`：登录后用户信息页标题（已登录状态）
- `result_return`：登录成功时返回内容关键字（例如 `'dr1004'` 或 `'result:0'`）

---

## 致谢
感谢以下项目与作者的贡献：

- [猪肉四喜丸子](https://space.bilibili.com/363076511) — 原版脚本作者

拷打鸽子精：

- [羽中](https://space.bilibili.com/353357823) — 改进版与维护  
