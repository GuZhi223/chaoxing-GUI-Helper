# XuexiTong-GUI-Helper 2.0

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![Python: 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![Flet: 0.84.0](https://img.shields.io/badge/Flet-0.84.0-blue.svg)](https://flet.dev/)

**XuexiTong-GUI-Helper** 是一个面向学习通/超星任务自动化流程的图形化启动器。

2.0 版本已经从旧版 `customtkinter` 界面重构为 **Flet + MVVM + EventBus** 架构，重点提升了深色界面质感、账号配置体验、运行监控和日志可读性。旧版 Tkinter 实现将保留在 `tkinter-legacy` 分支。

本项目基于开源核心项目 [Samueli924/chaoxing](https://github.com/Samueli924/chaoxing) 的命令行能力进行图形化封装，方便用户通过界面完成账号配置、任务启动、停止与状态查看。

> 简易运行方式：
> 如果你不想折腾 Python 环境，请在右侧 **Releases** 中下载打包好的 2.0 GUI 压缩包。注意：Release 只包含本项目的图形界面，不包含底层命令行程序。

---

## 功能特性

### 账号管理
- **添加 / 编辑 / 删除 / 复制账号**：完整的账号生命周期管理，支持备注名、手机号、密码字段。
- **批量操作**：勾选多个账号后可批量启动、批量停止、批量删除，一键管理多账号。
- **课程列表获取**：在账号弹窗中登录并拉取课程列表，支持多选课程并自动回填，减少手动填写错误。
- **账号配置持久化**：历史账号自动保存，重启应用后恢复。

### 任务执行
- **一键启动 / 停止**：每个账号卡片可独立启动、停止底层任务。
- **高级参数调节**：每个账号支持独立的倍速、并发 jobs、题库开关、自动提交等配置。
- **实时进度监控**：卡片内环形进度条实时反映视频播放进度，显示当前课程、视频名和运行时长。
- **状态可视化**：待启动 / 运行中 / 已完成 / 失败 / 已停止，每种状态独立配色与图标。

### 运行日志
- **多账号日志聚合**：所有账号的日志统一汇总，支持按账号筛选。
- **运行统计面板**：实时展示本次会话的任务数、视频完成数、任务完成率。
- **题库指标追踪**：统计从题库 API 获取答案数与实际提交数，计算答题命中率，帮助评估题库质量。
- **日志导出**：支持将当前筛选的日志导出为文件。

### 全局设置
- **题库提供商配置**：支持 6 种题库模式 —— 言溪题库、Like 回调、自定义 Adapter、AI (OpenAI 兼容)、SiliconFlow、禁用。选择不同模式自动展示对应的字段。
- **代理设置**：支持 HTTP 代理配置。
- **全局参数持久化**：所有设置保存在本地配置文件，重启后自动恢复。

### 历史配置
- **模糊搜索**：快速检索已保存的历史账号配置。
- **导入 / 导出**：支持将配置导出为文件，或从文件导入，可选合并或覆盖模式。

### 界面体验
- **现代深色主题**：基于 Flet/Flutter 渲染，统一的深色设计语言，卡片阴影、圆角与动画协同。
- **全局通知**：顶部横幅通知组件，支持成功 / 错误 / 警告 / 信息四种类型。
- **流畅动画**：页面切换、卡片入场、按钮悬停、侧边栏导航均有平滑动画过渡。
- **响应式布局**：侧边栏 + 内容区域，自适应窗口尺寸。

### 进程管理
- **安全退出**：关闭窗口时拦截退出事件，提示用户确认；异步执行进程清理，关闭对话框即时响应。
- **强制结束**：通过 `taskkill`（Windows）或 `kill`（Linux/macOS）确保底层子进程彻底终止。

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

本项目是 GUI 启动器，不内置、不分发任何底层命令行程序。请用户自行准备来源与授权均合规的兼容命令行程序。

可参考的上游下载入口：

- [Samueli924/chaoxing Releases](https://github.com/Samueli924/chaoxing/releases/latest)

默认情况下，程序会调用：

```bash
./chaoxing.exe
```

因此请将你自行准备的兼容命令行程序命名为 `chaoxing.exe`，并放在项目根目录，也就是与 `app/`、`core/`、`views/` 同级的位置。使用 Release 中的打包版时，请将该程序放在 GUI 主程序同级目录。

### 5. 启动界面

```bash
python app/main.py
```

---

## 目录结构

```text
app/                程序入口
core/               事件定义与事件总线
models/             账号配置与全局配置模型
services/           配置读写、日志解析、任务进程调度
viewmodels/         账号状态管理与页面数据绑定
views/
  ├── shell.py              侧边栏 + 内容区容器，全局通知集成
  ├── pages/
  │   ├── account_page.py   账号运行主页面，批量操作工具栏
  │   ├── history_page.py   历史配置页面，模糊搜索与导入导出
  │   ├── logs_page.py      运行日志页面，统计面板与日志筛选
  │   └── settings_page.py  全局设置页面，题库多模式配置
  ├── components/
  │   ├── account_card.py   账号卡片组件，进度环与状态胶囊
  │   ├── account_dialog.py 账号添加/编辑弹窗，课程获取与多选
  │   ├── loading.py        加载遮罩与加载动画组件
  │   └── notification.py   全局横幅通知组件
  └── theme/
      ├── colors.py         统一色板定义
      └── animations.py     动画常量与曲线
```

运行时产生的账号配置、cookies、日志和临时 ini 文件不会进入 Git 仓库。

---

## 技术栈

| 层级 | 技术 |
|------|------|
| UI 框架 | Flet 0.84.0（Flutter 渲染） |
| 架构模式 | MVVM + EventBus 发布/订阅 |
| 进程管理 | subprocess + taskkill/kill |
| 配置持久化 | configparser（INI 格式） |
| 日志解析 | 正则匹配 + ANSI 转义清理 |
| Python 版本 | 3.13+ |

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
3. 本项目 Release 仅发布 GUI 本体，不包含、也不授权分发任何第三方或二次修改的命令行二进制程序。
4. 用户在下载、安装、配置和使用本项目时，需要自行承担相关风险，包括但不限于账号异常、平台检测等后果。
5. 请尊重教育公平，合理使用技术工具。

---

## 反馈与贡献

如果你遇到 Bug，或者对界面、交互、日志解析有更好的想法，欢迎提交 Issue 或 Pull Request。
