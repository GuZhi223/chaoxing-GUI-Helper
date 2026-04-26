# XuexiTong-GUI-Helper 2.0

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python: 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)

**XuexiTong-GUI-Helper** 是一个面向学习通/超星任务自动化流程的图形化启动器。

2.0 版本已经从旧版 `customtkinter` 界面重构为 **Flet + MVVM + EventBus** 架构，重点提升了深色界面质感、账号配置体验、运行监控和日志可读性。旧版 Tkinter 实现将保留在 `tkinter-legacy` 分支。

本项目基于开源核心项目 [Samueli924/chaoxing](https://github.com/Samueli924/chaoxing) 的命令行能力进行图形化封装，方便用户通过界面完成账号配置、任务启动、停止与状态查看。

> 简易运行方式：
> 如果你不想折腾 Python 环境，请在右侧 **Releases** 中下载打包好的 2.0 版本压缩包，解压后运行即可。

---

## 功能特性

- **现代深色界面**：基于 Flet/Flutter 渲染，提供更流畅的侧边栏、卡片和弹窗体验。
- **账号配置管理**：支持添加、编辑、删除账号配置，并保存历史记录。
- **课程列表获取**：在账号配置弹窗中登录并读取课程列表，减少手动填写错误。
- **一键启动/停止**：每个账号卡片都可以独立启动、停止底层任务。
- **运行监控**：实时展示当前账号正在运行的视频槽位、进度、时间和状态。
- **日志视图**：支持运行监控与底层日志查看，方便排查任务异常。
- **全局设置**：支持题库提供商、Token/Key 等全局参数持久化。
- **进程清理**：关闭窗口时会拦截退出事件，尽量停止仍在运行的底层进程。

---

## 源码安装与运行

### 1. 准备环境

请确保电脑已经安装 **Python 3.13 或更高版本**。

### 2. 克隆仓库

```bash
git clone https://github.com/GuZhi223/chaoxing-GUI-Helper.git
cd chaoxing-GUI-Helper
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 准备底层命令行程序

本项目是 GUI 启动器，不直接内置底层刷课核心。请前往 [Samueli924/chaoxing](https://github.com/Samueli924/chaoxing) 下载或编译命令行程序。

默认情况下，程序会调用：

```bash
./chaoxing.exe
```

因此请将 `chaoxing.exe` 放在项目根目录，也就是与 `app/`、`core/`、`views/` 同级的位置。打包成 exe 后，也建议将底层 `chaoxing.exe` 放在主程序同级目录。

### 5. 启动界面

```bash
python app/main.py
```

---

## 目录结构

```text
app/          程序入口
core/         事件定义与事件总线
models/       账号配置与全局配置模型
services/     配置读写、日志解析、任务进程调度
viewmodels/   账号状态管理与页面数据绑定
views/        Flet UI 页面、组件与主题
```

运行时产生的账号配置、cookies、日志和临时 ini 文件不会进入 Git 仓库。

---

## 分支说明

- `main`：当前 2.0 Flet 重构版。
- `tkinter-legacy`：旧版 customtkinter/Tkinter 实现，仅作历史保留。

---

## 致谢

本项目底层自动化能力来自优秀的开源项目：

- [Samueli924/chaoxing](https://github.com/Samueli924/chaoxing)：超星学习通/超星尔雅/泛雅超星任务点自动化核心。

---

## 免责声明

1. 本项目仅供 Python 自动化、GUI 开发和本地工具封装等技术研究与学习交流。
2. 禁止将本项目用于商业用途、代刷服务或任何违反平台规则的行为。
3. 用户在下载、安装、配置和使用本项目时，需要自行承担相关风险，包括但不限于账号异常、平台检测等后果。
4. 请尊重教育公平，合理使用技术工具。

---

## 反馈与贡献

如果你遇到 Bug，或者对界面、交互、日志解析有更好的想法，欢迎提交 Issue 或 Pull Request。
