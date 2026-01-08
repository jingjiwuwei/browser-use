# 定时截图监控系统

## 功能概述

这个工具实现了一个定时截图监控系统，可以自动对网站的各个板块进行周期性截图，并保存截图及相关元信息。

## 主要特性

1. **用户登录支持**：支持需要账号、密码和验证码登录的网站，等待用户手动完成首次登录
2. **智能板块识别**：使用 AI 自动识别页面中的图表和仪表板板块
3. **定时截图**：可配置时间间隔，周期性执行截图任务
4. **元数据记录**：自动记录每个截图的时间戳、板块名称、文件路径和 URL

## 安装要求

```bash
# 安装 browser-use
uv add browser-use

# 或使用 pip
pip install browser-use

# 安装浏览器（如果尚未安装）
uvx browser-use install
```

## 环境配置

在项目根目录创建 `.env` 文件，配置 LLM API 密钥：

```bash
# 使用 Browser Use Cloud（推荐）
BROWSER_USE_API_KEY=your-api-key-here

# 或使用 OpenAI
OPENAI_API_KEY=your-openai-key

# 或使用其他 LLM 提供商
# ANTHROPIC_API_KEY=your-anthropic-key
# GOOGLE_API_KEY=your-google-key
```

您可以从以下地址获取 API 密钥：
- Browser Use Cloud: https://cloud.browser-use.com/new-api-key （新用户赠送 $10 额度）
- OpenAI: https://platform.openai.com/api-keys

## 使用方法

### 基本使用

```bash
python examples/use-cases/scheduled_screenshot_monitor.py \
    --url "https://your-website.com/dashboard" \
    --interval 300
```

### 完整参数说明

```bash
python examples/use-cases/scheduled_screenshot_monitor.py \
    --url "https://your-website.com/dashboard"  # 必需：要监控的网站 URL
    --interval 300                               # 可选：截图间隔（秒），默认 300 秒（5 分钟）
    --screenshot-dir "screenshots"               # 可选：截图保存目录，默认 "screenshots"
    --metadata-file "metadata.json"              # 可选：元数据文件名，默认 "screenshot_metadata.json"
```

### 使用流程

1. **启动程序**：运行上述命令
2. **手动登录**：程序会打开浏览器窗口，您需要：
   - 输入账号和密码
   - 完成验证码验证（如有）
   - 等待完全登录成功
3. **确认登录**：登录完成后，在终端按 Enter 键继续
4. **自动监控**：程序将：
   - 自动识别页面中的图表板块
   - 开始定时截图循环
   - 每个周期自动保存截图和元数据
5. **停止监控**：按 Ctrl+C 停止程序

## 输出文件

### 截图文件

截图文件保存在指定的目录中（默认为 `screenshots/`），文件命名格式为：

```
板块名称_时间戳.png
```

示例：
```
Sales-Chart_20260108_120000.png
Revenue-Graph_20260108_120000.png
Performance-Dashboard_20260108_120000.png
```

### 元数据文件

元数据保存在 JSON 文件中（默认为 `screenshot_metadata.json`），包含每个截图的详细信息：

```json
[
  {
    "timestamp": "2026-01-08T12:00:00.123456",
    "block_name": "Sales-Chart",
    "screenshot_path": "screenshots/Sales-Chart_20260108_120000.png",
    "url": "https://your-website.com/dashboard"
  },
  {
    "timestamp": "2026-01-08T12:00:00.234567",
    "block_name": "Revenue-Graph",
    "screenshot_path": "screenshots/Revenue-Graph_20260108_120000.png",
    "url": "https://your-website.com/dashboard"
  }
]
```

## 使用示例

### 示例 1：监控每 5 分钟截图一次

```bash
python examples/use-cases/scheduled_screenshot_monitor.py \
    --url "https://dashboard.example.com" \
    --interval 300
```

### 示例 2：监控每 1 小时截图一次

```bash
python examples/use-cases/scheduled_screenshot_monitor.py \
    --url "https://analytics.example.com" \
    --interval 3600
```

### 示例 3：自定义保存位置

```bash
python examples/use-cases/scheduled_screenshot_monitor.py \
    --url "https://metrics.example.com" \
    --interval 600 \
    --screenshot-dir "my_screenshots" \
    --metadata-file "my_metadata.json"
```

## 工作原理

1. **登录等待阶段**：
   - 程序以非无头模式启动浏览器（headless=False）
   - 用户可以看到并操作浏览器窗口
   - 完成登录后按 Enter 继续

2. **板块识别阶段**：
   - 使用 AI Agent 分析页面 DOM 结构
   - 自动识别图表、图形、仪表板等可视化元素
   - 为每个板块生成名称和 CSS 选择器

3. **定时截图阶段**：
   - 按配置的时间间隔循环执行
   - 每次循环刷新页面获取最新数据
   - 对每个识别的板块分别截图
   - 保存截图文件和元数据

## 注意事项

1. **浏览器保持运行**：监控期间浏览器窗口会一直打开，请勿关闭
2. **网络连接**：确保网络连接稳定，避免登录会话过期
3. **磁盘空间**：定期清理旧的截图文件，避免占用过多磁盘空间
4. **会话超时**：某些网站可能会在一段时间后自动登出，需要重新启动程序
5. **验证码处理**：仅在首次登录时需要处理验证码，之后会复用登录会话

## 高级配置

### 修改 LLM 模型

如果想使用不同的 LLM 模型，可以修改代码中的这一行：

```python
# 在 scheduled_screenshot_monitor.py 中
llm=ChatBrowserUse(),  # 默认使用 Browser Use 的 LLM

# 改为其他模型，例如：
from browser_use import ChatOpenAI
llm=ChatOpenAI(model='gpt-4.1-mini'),
```

### 自定义板块选择器

如果自动识别的板块不准确，可以在代码中手动指定：

```python
# 在 identify_chart_blocks() 方法的 fallback 部分修改
blocks_found = [
    ScreenshotBlock(name='自定义板块1', selector='#chart1'),
    ScreenshotBlock(name='自定义板块2', selector='.dashboard-widget'),
    ScreenshotBlock(name='自定义板块3', selector='[data-chart-id="revenue"]'),
]
```

## 故障排除

### 问题：浏览器无法启动

**解决方案**：
```bash
# 重新安装浏览器
uvx browser-use install
```

### 问题：无法识别图表板块

**解决方案**：
1. 检查页面是否完全加载
2. 尝试手动指定 CSS 选择器（参见"自定义板块选择器"）
3. 增加页面加载等待时间

### 问题：截图失败

**解决方案**：
1. 确认 CSS 选择器是否正确
2. 检查元素是否在可视区域内
3. 尝试先滚动到元素位置再截图

### 问题：API 密钥错误

**解决方案**：
1. 检查 `.env` 文件是否存在且配置正确
2. 确认 API 密钥是否有效
3. 检查 API 额度是否用尽

## 技术支持

- Browser Use 文档：https://docs.browser-use.com
- GitHub 仓库：https://github.com/browser-use/browser-use
- Discord 社区：https://link.browser-use.com/discord

## 许可证

本示例代码遵循 MIT 许可证。
