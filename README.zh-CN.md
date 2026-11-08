# announce-roll

**中文** | [English](README.md)

一份面向页面可交互控件的**播报名册**。读取你已经拥有的 HTML，按读屏软件或按名称寻址的智能体会听到的方式列出每个控件，并标出无名、重名，以及把可见词盖住的覆盖。可选的意图列表会解析到唯一控件——或明确告诉你解析失败。

这个技能不会打开浏览器，也不会代替你点击。它在智能体动手操作页面前，先把名册编好。

## 功能

- **朗读名册** — 角色、朗读名、名称来源、地标、附近标题、禁用标记
- **五个等级** — `CLEAR`、`WEAK`、`MUTE`、`CLASH`、`MASK`（不是发货/暂缓门禁）
- **意图解析** — 每个短语变为 `UNIQUE`、`AMBIGUOUS` 或 `MISSING`
- **修理说明** — 有问题的行会建议如何让名称既唯一又如实
- **标准库脚本** — `scripts/announceroll.py`（`lint` / `roll` / `resolve` / `demo`）外加单元测试

## 安装

```bash
git clone https://github.com/fangdididi/announce-roll.git
cd announce-roll
```

### Claude Code / Codex / Cursor 类智能体

- 把仓库放到（或符号链接到）智能体加载技能的目录，**或者**
- 打开该文件夹并说：「先按 SKILL.md（announce-roll）给这个页面编一份名册，再点击任何东西。」

不需要 API 密钥。辅助脚本是只用标准库的 Python 3。

## 用法

```bash
# 解析并计数
python3 scripts/announceroll.py lint examples/shelf-clear.html

# 打印名册
python3 scripts/announceroll.py roll examples/shelf-clear.html
python3 scripts/announceroll.py roll examples/shelf-clash.html
python3 scripts/announceroll.py roll examples/shelf-mute.html
python3 scripts/announceroll.py roll examples/shelf-mask.html

# 解析意图
python3 scripts/announceroll.py resolve examples/shelf-clash.html examples/intents.json

# 内置混合示例
python3 scripts/announceroll.py demo

# 机器可读输出
python3 scripts/announceroll.py --json roll examples/shelf-clear.html

# 测试
python3 -m unittest discover -s tests -v
```

典型流程：

1. 保存你有权检查的页面或组件 HTML。
2. 把必须成立的动作写入意图文件（参见 `templates/intents.json`）。
3. 运行 `roll` / `resolve`，然后给无名、重名或名实不符的控件改名，直到每条意图都是 `UNIQUE`。

## 示例

| 文件 | 你应看到 |
| --- | --- |
| `examples/shelf-clear.html` | `READY` — 名称唯一，包含带 label 的搜索框 |
| `examples/shelf-clash.html` | `REPAIR` — 两个「Edit」按钮 |
| `examples/shelf-mute.html` | `REPAIR` — 没有朗读名的纯图标按钮 |
| `examples/shelf-mask.html` | `REPAIR` — 可见「Save changes」，朗读「Delete account」 |

## 文件结构

```
announce-roll/
├── SKILL.md
├── SKILL.zh-CN.md
├── README.md
├── README.zh-CN.md
├── LICENSE
├── scripts/announceroll.py
├── templates/intents.json
├── examples/
└── tests/test_announceroll.py
```

## 许可证

MIT
