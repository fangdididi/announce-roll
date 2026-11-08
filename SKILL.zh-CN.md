---
name: announce-roll
description: >-
  把页面上每个可交互控件整理成一份「播报名册」：角色、朗读名、名称来源、地标与标题，
  并标成 CLEAR / WEAK / MUTE / CLASH / MASK。再把用户意图解析成
  UNIQUE / AMBIGUOUS / MISSING，让智能体按唯一名称点击，而不是猜像素
  或脆弱的 CSS 选择器。适用于智能体要操作页面、把界面做成可被点名驱动，
  或一排重复的「编辑」按钮、纯图标控件总点错的时候。
---

# announce-roll

页面看起来做完了，按名字却可能没法开：两行都叫「编辑」；垃圾桶图标什么也没说；按钮上写着「保存更改」，朗读出来却是「删除账户」。读屏软件、语音输入，以及按「角色 + 名称」选控件的智能体，听到的是同一本目录——目录里有无名、重名或名实不符时，大家都会走错。

**announce-roll** 读取你已经拥有的 HTML（保存下来的页面、组件夹具，或智能体刚写好的标记），编出这份目录。它不会打开真实浏览器、不会截图，也不会替你改网站。它只回答：这个页面会播报什么、哪些名字撞车、某个意图能不能精确落到一个控件上。

## 何时使用

- 智能体需要点击、填写或跟随页面上的某处，并且应该用 **角色 + 朗读名** 来寻址，而不是 CSS 路径或截图像素
- 你在审查或编写界面，希望每个预定动作都有 **恰好一个** 朗读名
- 行内「编辑」、图标工具条、卡片菜单等重复动作总把智能体带到错误控件
- 可见文案和程序化名称已经各说各话

不要用它去爬你没有权利查看的网站、绕过机器人检测、驱动他人的已登录会话，或去审查视觉设计、颜色对比、交互状态覆盖——那些是另一回事。

## 核心想法

1. **名册**：每个可交互控件占一行，包含角色、朗读名、名称来源、附近的标题与地标，以及一个等级。
2. **等级**描述的是名册质量，不是发货/暂缓门禁：
   - `CLEAR` — 名称唯一，来源可靠（内容、关联 label、`alt`，或仍然包含可见词的覆盖）
   - `WEAK` — 名称只来自 `title`、`placeholder`，或浏览器隐式回退（例如 “Submit”）
   - `MUTE` — 没有可播报的名称
   - `CLASH` — 另一个控件有相同的角色和规范化名称
   - `MASK` — `aria-label` / `aria-labelledby` 盖住了可见词，且这些词没有出现在朗读名里
3. **意图**（可选）：人会说出的短语（「加入购物车」「编辑茶叶」）。每条解析为 `UNIQUE`、`AMBIGUOUS` 或 `MISSING`。
4. **整份名册的状态**：`READY`（无需修理）、`SOFT`（只有弱名称）或 `REPAIR`（无名、重名、名实不符，或意图失败）。

辅助脚本按实用顺序取名：先解析 labelled-by 引用，再看 `aria-label`，然后是原生 label / `alt` / `value`，再是元素内容，再是 `title` / `placeholder`，最后是少数输入框的隐式名称。它会跳过带 `hidden` 的节点、`type="hidden"` 的输入，以及处在 `aria-hidden="true"` 之下的内容。这是名册生成器，不是完整的浏览器无障碍引擎。

## 步骤

1. 把你有权检查的页面或组件存成 HTML。一份夹具优于带有他人隐私数据的生产环境整页转储。
2. 列出智能体或用户必须完成的动作，写入 `templates/intents.json`，格式为 `{id, phrase, role}`。`role` 可用来过滤（`button`、`link`、`textbox`、`searchbox` 等）。
3. 运行辅助脚本：

   ```bash
   python3 scripts/announceroll.py lint path/to/page.html
   python3 scripts/announceroll.py roll path/to/page.html
   python3 scripts/announceroll.py resolve path/to/page.html path/to/intents.json
   python3 scripts/announceroll.py demo
   ```

4. 从上到下读名册。每个 `MUTE` 补上可见文字或如实的朗读名；每个 `CLASH` 把对象写进名字（「编辑茶叶」，而不是「编辑」）；每个 `MASK` 要么去掉覆盖，要么让可见词出现在朗读名里。
5. 重新 `resolve`，直到每条意图都是 `UNIQUE`，整页状态为 `READY`，或你接受的 `SOFT`。
6. 智能体之后操作真实页面时，应按名册里的角色和名称点击。若名称仍是 `AMBIGUOUS`，不要取第一个匹配，也不要按兄弟序号点；回到第 4 步。

### 退出码

| 退出码 | 状态 | 含义 |
| --- | --- | --- |
| `0` | `READY` 或 `SOFT` | 名册可用；弱名称已被记录 |
| `2` | `REPAIR` | 存在无名、重名、名实不符，或意图不唯一 |
| `3` | — | 文件或意图 JSON 无法读取 |

## 示例

**两行操作都叫「编辑」。** 名册将两者标为 `CLASH`。意图 `{phrase: "Edit", role: "button"}` 为 `AMBIGUOUS`。修法：改成「编辑茶叶」和「编辑蜂蜜」，可借用旁边的标题或列表文字。

**只有图标的工具条按钮。** 名册标为 `MUTE`。修法：加上可见文字，或写明动作的 `aria-label`（「搜索」「关闭」「分享」），不要写成「图标」或「button2」。

**可见「保存更改」，朗读「删除账户」。** 名册标为 `MASK`。以「保存更改」为意图会得到 `MISSING`，因为按名称寻址的智能体根本听不到这几个字。修法：朗读名改回「保存更改」，或改可见文案，让两边一致。

**带 `<label for="q">搜索商品</label>` 的搜索框。** 名册标为 `CLEAR`，来源是 `label`。智能体应填写 `searchbox`「搜索商品」，而不是 `#q`。

参见 `examples/shelf-clear.html`、`examples/shelf-clash.html`、`examples/shelf-mute.html` 和 `examples/shelf-mask.html`。

## 提示

- 优先用可见文字当名称。覆盖只留给真正没有文字的控件（纯图标、图片）。
- 真正要紧的是「同一角色下唯一」。`button`「保存」和 `link`「保存」不算互相冲突，但意图如果省略角色，仍可能对不上。
- `placeholder` 和 `title` 能让控件离开 `MUTE`，但它们容易消失或漏翻译——把 `WEAK` 当成还没标完。
- 附近的标题应写进名册，修理时就可以借用「账单」或「茶叶」，而不必另造一套词。
- 脚本看不到 CSS 的 `display:none`，也看不到 JavaScript 跑完之后才出现的名字。若线上页面在客户端里生成控件，请保存渲染后的 DOM（或组件渲染后的夹具）再编名册。
- 不要为了编名册把密钥、会话令牌或他人的个人数据贴进夹具。

## 辅助脚本

`scripts/announceroll.py` 是只用标准库的 Python 3 脚本，提供 `lint`、`roll`、`resolve` 和 `demo`。需要给其他工具机器可读数据时加上 `--json`。修改取名规则后请运行 `python3 -m unittest discover -s tests -v`。
