# 1000+ 剧照采集（独立任务）

这个任务和 3D 地图分开进行。**目前已采集 0 张**：本环境不允许下载剧集视频（权限检查拦截），网页搜索也拿不到可用的剧照（见 `../blender/evidence/REFERENCE_GAPS.md`）。等用户提供视频文件或截图后，用这里的脚本继续。

## 规则

- 不绕过任何权限、登录、付费墙或人机验证；不下载受保护的视频。
- 只收**真正看过、能打开**的画面。不算：缩略图（短边 < 480 像素）、重复图、打不开的链接、猜出来的帧和时间码。
- 每张图都要能追到来源：用户提供的文件名 + 时间码，或网页的真实链接。
- 剧照本身不进 Git 仓库（版权），只把索引 `frames_index.csv` 提交进来。图片存在仓库外的目录（默认 `~/boonie_frames/`）。

## 目录

| 路径 | 内容 |
|---|---|
| `frames_index.csv` | 索引（每张图一行，见下面的字段） |
| `sources.csv` | 来源清单：用户提供的视频 / 截图包 / 网页，以及处理进度 |
| `extract_frames.py` | 从**用户提供的本地视频**抽帧（ffmpeg 场景切换 + 固定间隔），写进存储目录和索引 |
| `ingest_frames.py` | 导入用户提供的截图目录：过滤缩略图、算哈希去重、写索引 |
| `~/boonie_frames/`（仓库外） | 图片本身，按 `系列/集数/` 分目录 |

两个脚本都可以中断后重跑：已经在索引里的图片（按 sha256）会跳过，视频按 `sources.csv` 里记录的进度继续。

## 索引字段（`frames_index.csv`）

| 字段 | 说明 |
|---|---|
| `frame_id` | `系列缩写-集数-时间码`，例如 `XRLLK-E30-000412.5`；截图没有时间码时用 `-IMG序号` |
| `series` | 系列名（例如 夏日连连看）；季别没核实时写“待核验” |
| `episode` | 集数 |
| `episode_title` | 集名 |
| `timestamp_s` | 视频里的秒数（截图没有就空着，**不要猜**） |
| `source_type` | `user_video` / `user_screenshot` / `web` |
| `source` | 文件名或网页链接 |
| `sha256` | 文件哈希（完全相同的去重） |
| `dhash` | 64 位差值哈希（近似重复去重，汉明距离 ≤ 6 算重复） |
| `width` / `height` | 像素 |
| `scene_tag` | 场景（木屋外 / 木屋内 / 仓库 / 熊洞 / 猴洞 / 松鼠窝 / 湖 / 森林 / 其他） |
| `visible_details` | 人工填写：画面里看到了什么 |
| `evidence_level` | A / B / C / D（同 `../blender/evidence/REFERENCE_INDEX.csv`） |
| `reviewed` | 人工看过填 `yes` |
| `notes` | 备注 |

## 用法

```bash
# 用户提供的视频（本地文件），每 2 秒一张 + 场景切换，存到 ~/boonie_frames/
python3 extract_frames.py --video /path/夏日连连看_30.mp4 --series 夏日连连看 --episode 30 --title 湖底历险记

# 用户提供的截图目录
python3 ingest_frames.py --dir /path/screenshots --series 夏日连连看 --episode 41 --title 生存技能

# 统计
python3 ingest_frames.py --stats
```

`scene_tag`、`visible_details`、`evidence_level` 要人工看图后填写；脚本只填能自动得到的字段。
