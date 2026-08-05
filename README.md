# 📍 Xiaohongshu to Google Maps Discord Bot (小红书 -> Google 地图 AI 标注机器人)

一个智能 Discord Bot。当你向 Discord 频道发送小红书笔记链接时，Bot 会自动使用大语言模型（LLM）分析笔记内容、提取推荐地点信息，并在 Google 地图（Google Maps）上精确检索定位，最后将地点自动标注到预设的 Google 地图账号中！

---

## 🌟 核心功能与特色

1. **🔗 智能链接识别与解析**
   - 自动识别 Discord 消息中的小红书短链（`xhslink.com`）与完整网页链接（`xiaohongshu.com`）。
   - 自动解析重定向、笔记标题、正文文本、作者信息、便签标签及笔记图片。

2. **🧠 LLM 结构化地点提取**
   - 适配 OpenAI (GPT-4o / GPT-4o-mini)、Google Gemini、Anthropic Claude 或任意 OpenAI 兼容 API（如 DeepSeek）。
   - 智能提取：**具体店名/景点**、**所属城市/街区**、**地点分类（Cafe / Restaurant / Sightseeing 等）**、**1-2句精炼推荐摘要**及**最佳 Google 地图搜索关键词**。

3. **🗺️ Google 地图精准定位**
   - 调用 Google Places API / Geocoding API 匹配准确的 Place ID、详细地址、经纬度坐标及 Google Maps 跳转链接。

4. **📌 三种 Google 地图标注策略**
   - **策略一（推荐）：Google Sheets 实时同步 Google My Maps**
     - Bot 通过 Google Sheets API 自动将地点写入表格，已连接该表格的 Google My Maps 图层会**实时自动更新并展现新的地图标记**！
   - **策略二：KML / GeoJSON 地图文件导出**
     - 自动生成并追加 `<Placemark>` 到本地 `.kml` 文件中，随时可以下载并一键导入 Google My Maps。
   - **策略三：Playwright 浏览器自动化**
     - 可选插件：使用保持登录状态的 Playwright 浏览器，自动点击 Google 地图网页上的“保存”->“想去/收藏”列表。

5. **🎨 美观的 Discord 卡片展示**
   - 根据地点分类自动匹配主题颜色（如 Cafe 琥珀金、Restaurant 活力红、Sightseeing 翡翠绿）。
   - 附带小红书原笔记预览图、Google 评分、一键直达按钮（在 Google 地图查看 & 打开原笔记）。

---

## 🛠️ 项目架构

```text
rednote_map/
├── config.py                  # 配置管理 (环境变量加载)
├── main.py                    # 应用入口 (启动 Discord Bot)
├── .env.example               # 环境变量配置模板
├── requirements.txt           # 依赖列表
├── Dockerfile & docker-compose.yml # 部署配置
├── src/
│   ├── bot/                   # Discord Bot client, 指令与 Embed 卡片生成
│   ├── scrapers/              # 小红书短链解析与 HTML 结构提取
│   ├── llm/                   # 大语言模型地点分析器
│   ├── maps/                  # Google Places 地理编码与 3 种标注策略
│   ├── services/              # 端到端处理 Pipeline
│   └── models/                # Pydantic 数据模型
└── tests/                     # 100% 覆盖的单元与集成测试套件
```

---

## 🚀 快速开始

### 1. 克隆项目与安装依赖

```bash
# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置 `.env` 文件

复制 `.env.example` 为 `.env` 并填写配置：

```bash
cp .env.example .env
```

`.env` 核心参数：

```ini
# Discord Bot
DISCORD_BOT_TOKEN=your_discord_bot_token_here
ALLOWED_CHANNEL_IDS=123456789012345678 # 可选，限定生效频道 ID，用逗号分隔

# LLM 配置
LLM_PROVIDER=openai
LLM_API_KEY=your_openai_api_key_here
LLM_MODEL=gpt-4o-mini

# Google Maps API Key
GOOGLE_MAPS_API_KEY=your_google_maps_api_key_here

# 地图标注策略 ('sheets', 'kml', 'playwright', 'none')
PINNER_STRATEGY=sheets
GOOGLE_SHEETS_ID=your_google_sheets_id_here
GOOGLE_SERVICE_ACCOUNT_FILE=credentials.json
```

---

## 📌 如何设置 Google My Maps 自动同步（策略一）

1. **新建 Google Sheet**：在 Google Drive 创建一个空白表格，复制浏览器地址栏中的 Sheet ID（如 `https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit` 中的 `YOUR_SHEET_ID`）。
2. **创建 Service Account 凭据**：
   - 前往 [Google Cloud Console](https://console.cloud.google.com/)。
   - 启用 `Google Sheets API` 和 `Google Drive API`。
   - 创建服务账号（Service Account），下载 JSON 密钥文件并重命名保存为 `credentials.json` 放到项目根目录。
   - 将服务账号的 `client_email` 添加为该 Google Sheet 的“编辑者”权限。
3. **连接 Google My Maps**：
   - 打开 [Google My Maps (我的地图)](https://www.google.com/maps/d/)，新建一份地图。
   - 点击图层下的 **导入 (Import)** -> 选择 **Google 云端硬盘** -> 选择刚才创建的 Google Sheet。
   - 经纬度列选择 `Latitude` / `Longitude`，标题列选择 `Place Name`。
   - **完成！** Bot 每次追加行，Google My Maps 都会自动刷新呈现标记点。

---

## 🤖 Discord 机器人指令

| 指令 | 描述 |
| :--- | :--- |
| **自动监听** | 直接在频道内发送小红书链接或分享文字，Bot 自动触发分析与标注 |
| `/analyze_xhs link:<url>` | 手动提交小红书链接进行分析 |
| `/map_status` | 查看当前 LLM 模型、Google API 状态及标注策略配置 |
| `/export_map` | 下载当前导出的最新 KML 地图文件 |

---

## 🧪 运行单元与集成测试

项目包含完整的 `pytest` 测试套件：

```bash
PYTHONPATH=. pytest -v
```

测试覆盖了：
- 小红书短链与分享文本正则提取
- HTML / SSR State 解析
- LLM 结构化提取与 Fallback
- Google Places API 检索与模拟定位
- KML 生成与 Google Sheets 接口
- Discord Embed 渲染

---

## 🐳 Docker 容器化部署

使用 Docker 轻松部署在服务器上：

```bash
# 构建并后台运行
docker-compose up -d --build
```
