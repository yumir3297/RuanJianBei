# 2026-06-22 Three.js 数字人三角色设定稿

## 1. 文档目的

本稿用于为 Three.js 数字人方案提供一套可以直接进入评审和程序化实现的角色设计基础。

适用范围：

1. 游客端数字人展示
2. 管理端数字人预览
3. 后续 Three.js 程序化建模参数设计
4. 后续 AI 概念图生成提示词

本稿不直接修改实现代码，只定义角色设计。

## 2. 设计目标

本项目的数字人不走“写实真人”路线，而走“风格化类 3D 导览员”路线。

设计目标如下：

1. 远看能一眼分出三个人设
2. 近看有文化感、导览感和一定科技感
3. 风格统一，不像来自三个完全不同项目
4. 能被 Three.js 程序化几何快速表达
5. 适合当前项目的胸像式展示窗口

## 3. 总体风格基线

### 3.1 风格关键词

统一风格关键词：

1. 东方文化气质
2. 温和、可信、可亲近
3. 非写实、非卡通幼态
4. 轮廓清楚，便于小窗口展示
5. 材质干净，避免过强塑料感

### 3.2 视觉基线

三角色共享以下视觉基线：

1. 都采用半身到胸像构图
2. 头身比例偏写意，不做夸张二头身
3. 五官简化，但保留明显的眼、鼻、口、眉层次
4. 材质为柔和标准材质，不做皮肤真实毛孔
5. 配色饱和度中低，避免廉价游戏皮肤感

### 3.3 动效基线

三角色共享以下动作原则：

1. 待机时有轻微呼吸和头部微动
2. 说话时口型开合清楚，但幅度不过分夸张
3. 眨眼频率自然，不做高频卖萌
4. 情绪变化主要通过眉眼、嘴角和头部姿态完成

## 4. 三角色总览

| 预设键 | 展示名 | 角色定位 | 视觉关键词 | 推荐音色 |
|---|---|---|---|---|
| `preset:monk` | 明彻法师 | 佛教文化讲解型数字人 | 庄重、安定、慈和 | `male_calm` |
| `preset:hanfu` | 清岚 | 文化叙事型汉服导游 | 雅致、温润、书卷气 | `female_warm` |
| `preset:modern` | 景行 | 现代服务型智能导游 | 亲切、利落、轻科技 | `male_enthusiastic` |

## 5. 角色一：明彻法师

### 5.1 人设定位

角色职责：

1. 负责佛教文化、景区历史、礼佛礼仪类讲解
2. 在游客感知上承担“可信、沉稳、知识深”的角色

人物气质：

1. 平静
2. 慈和
3. 稳定
4. 不疏离

### 5.2 外观设计

脸型与五官：

1. 脸型偏长椭圆
2. 眉形平稳略弯，显沉着
3. 眼睛不宜过大，眼裂偏细长
4. 鼻梁干净简化
5. 嘴型较薄，微笑幅度克制

发型：

1. 主方案为净头
2. 不做夸张头骨高光
3. 可加非常轻的头皮暖色渐变，避免“完全光头模型”过冷

服装：

1. 以赭黄、棕褐、暗金为主
2. 上身采用僧袍与披肩层叠轮廓
3. 领口简洁，肩部轮廓较宽，体现稳定感

配饰：

1. 一串低调念珠
2. 不做过多金属饰件
3. 可在胸前做小型佛珠坠点缀

### 5.3 配色方案

主色：

1. 袍色赭黄 `#A06A2C`
2. 深棕辅色 `#5C3B24`
3. 暖米内衬 `#D8C3A5`

皮肤建议：

1. 温暖中性肤色 `#D9B08C`

点缀色：

1. 暗铜金 `#8C6A3A`

### 5.4 动作与表情风格

待机动作：

1. 呼吸幅度最小
2. 头部左右摆动最轻
3. 眼神移动缓慢

说话动作：

1. 口型开合节奏偏稳
2. 点头频率低
3. 情绪转换不过度

情绪表达：

1. `neutral`：平静讲述
2. `happy`：嘴角轻扬，眼神更柔和
3. `apology`：眉头微收，头部略低

### 5.5 Three.js 实现翻译

适合映射成以下几何与参数：

1. 头部：偏长椭球
2. 发型：无发层
3. 肩部：更宽、更厚、更稳定
4. 服装：披肩式外层几何，领口开口较小
5. 配饰：低面数佛珠环
6. 动作参数：呼吸慢、摆动小、说话动作克制

### 5.6 AI 概念图提示词

正向提示词：

```text
Stylized 3D Buddhist guide for a Chinese scenic cultural tourism app, male, calm and compassionate, shaved head, saffron and brown monk robe, prayer beads, bust portrait, elegant East Asian facial features, soft cinematic lighting, clean simplified geometry, cultural dignity, semi-realistic but not photorealistic, warm and trustworthy, front-facing presentation
```

反向提示词：

```text
photorealistic skin pores, exaggerated anime, childish chibi, sci-fi armor, cyberpunk neon overload, western fantasy priest, muscular bodybuilder, horror, old low-poly game look
```

## 6. 角色二：清岚

### 6.1 人设定位

角色职责：

1. 负责文化叙事、建筑艺术、传统礼仪类内容
2. 在游客感知上承担“优雅、亲和、最有文化氛围”的角色

人物气质：

1. 温润
2. 清雅
3. 有书卷气
4. 不高冷

### 6.2 外观设计

脸型与五官：

1. 脸型偏鹅蛋脸
2. 眉形更柔，弧线顺
3. 眼睛较明亮，但不做二次元放大
4. 嘴角自然上扬
5. 鼻型柔和简洁

发型：

1. 盘发或半盘发
2. 发髻轮廓清晰
3. 一支发簪作为主要辨识点
4. 侧边可保留少量柔和发束

服装：

1. 交领汉服结构
2. 肩颈线条要柔和
3. 袖口和领缘可做轻微层次
4. 上身建议有披帛感或轻搭肩感

配饰：

1. 玉色发簪
2. 细小流苏或耳侧装饰
3. 不堆叠太多首饰，重点保留“轻”

### 6.3 配色方案

主色：

1. 米白 `#E9E0D1`
2. 青绿 `#7DAA92`
3. 墨青 `#4F6B63`

皮肤建议：

1. 柔和暖白肤色 `#E8C4A8`

点缀色：

1. 玉石青 `#A7C7B7`
2. 淡金 `#B9A06A`

### 6.4 动作与表情风格

待机动作：

1. 呼吸更柔和
2. 头部微侧动作略多于法师
3. 眼神移动轻缓

说话动作：

1. 口型线条圆润
2. 点头和目光交流更自然
3. 说话时头颈线更柔软

情绪表达：

1. `neutral`：温和讲述
2. `happy`：笑意更明显，眼尾稍弯
3. `apology`：嘴角回收，头部轻微下倾

### 6.5 Three.js 实现翻译

适合映射成以下几何与参数：

1. 头部：标准椭圆，轮廓柔和
2. 发型：盘发主体 + 发簪 + 两侧轻发束
3. 服装：交领层叠面片 + 柔和肩披
4. 配饰：低面数发簪与流苏点缀
5. 动作参数：待机更柔，眨眼略轻快

### 6.6 AI 概念图提示词

正向提示词：

```text
Stylized 3D Hanfu female cultural guide for a Chinese scenic tourism app, elegant and gentle, soft East Asian facial features, ivory and celadon hanfu, hair bun with jade hairpin, bust portrait, refined scholarly temperament, clean geometry, warm lighting, semi-realistic but not photorealistic, graceful cultural hostess
```

反向提示词：

```text
heavy palace costume, exaggerated cosplay, neon fantasy, sexy fashion model, giant anime eyes, over-detailed jewelry, photorealistic skin pores, western medieval dress
```

## 7. 角色三：景行

### 7.1 人设定位

角色职责：

1. 负责路线推荐、服务说明、游客指引、智能问答感更强的内容
2. 在游客感知上承担“最容易交流、最现代、最像数字助手”的角色

人物气质：

1. 利落
2. 可靠
3. 亲近
4. 有轻微科技感

### 7.2 外观设计

脸型与五官：

1. 脸型略方中带圆
2. 眉形更清晰利落
3. 眼睛更直接、更有精神
4. 鼻梁略挺
5. 嘴角自然上扬，开朗度高于法师

发型：

1. 干净短发
2. 发顶有轻微层次
3. 两侧不宜过厚

服装：

1. 现代导览制服或轻科技夹克
2. 立领或简洁翻领结构
3. 胸前可做徽章或识别牌
4. 肩线比汉服角色更利落

配饰：

1. 极简胸牌
2. 可选单耳微型导览耳麦
3. 少量青绿色光感点缀

### 7.3 配色方案

主色：

1. 深藏青 `#243447`
2. 青绿 `#2F7F79`
3. 亮米白 `#E6E2D3`

皮肤建议：

1. 中性暖肤色 `#D8B091`

点缀色：

1. 亮琥珀 `#E39B43`

### 7.4 动作与表情风格

待机动作：

1. 头部微动最明显
2. 眼神扫视稍快
3. 呼吸和站姿更有活力

说话动作：

1. 口型张合最清楚
2. 头部反馈和点头略多
3. 更有“正在服务”的即时感

情绪表达：

1. `neutral`：友好说明
2. `happy`：微笑更明显，头部更挺
3. `apology`：表情收敛，但仍保持专业

### 7.5 Three.js 实现翻译

适合映射成以下几何与参数：

1. 头部：略偏方圆
2. 发型：短发层次片
3. 服装：现代领口、徽章、胸牌几何
4. 配饰：低面数耳麦或小徽标
5. 动作参数：说话动作最活跃，眨眼节奏最自然

### 7.6 AI 概念图提示词

正向提示词：

```text
Stylized 3D modern scenic guide for a Chinese smart tourism app, male, approachable and energetic, neat short hair, navy and teal modern guide uniform, badge and subtle earpiece, bust portrait, intelligent service vibe, clean simplified geometry, semi-realistic but not photorealistic, warm modern technology aesthetic
```

反向提示词：

```text
full sci-fi robot, cyberpunk overload, military uniform, businessman in suit, childish anime, photorealistic pores, western office worker, superhero costume
```

## 8. 三角色区分矩阵

| 维度 | 明彻法师 | 清岚 | 景行 |
|---|---|---|---|
| 角色感知 | 稳重可信 | 温雅文化 | 亲和现代 |
| 脸型 | 长椭圆 | 鹅蛋脸 | 方圆脸 |
| 发型 | 净头 | 盘发发簪 | 短发 |
| 服装轮廓 | 僧袍披肩 | 交领汉服 | 现代制服 |
| 主色 | 赭黄棕 | 米白青绿 | 藏青青绿 |
| 动作节奏 | 最慢 | 柔和 | 最利落 |
| 说话感觉 | 平稳 | 温润 | 直接 |

## 9. 对 Three.js 程序化建模的直接指导

### 9.1 第一阶段可共用的基础网格

三角色可以共用：

1. 头部基础几何
2. 眼球基础结构
3. 嘴部基础结构
4. 胸像基础骨架

### 9.2 第一阶段需要变化的部件

优先通过以下部件拉开差异：

1. 发型
2. 服装领口
3. 肩部轮廓
4. 胸前配饰
5. 主配色

### 9.3 第一阶段不必追求的细节

为控制实现复杂度，第一阶段不强求：

1. 写实手部
2. 复杂布料模拟
3. 精细耳饰摆动
4. 发丝级建模
5. 高精法线或贴图

## 10. 建议的审阅重点

把本稿交给审阅方时，建议重点看：

1. 三个角色是否足够区分
2. 三个角色是否符合景区文化气质
3. 是否存在角色气质和音色不匹配的问题
4. 是否有需要避免的宗教符号或过度戏剧化表达
5. 是否需要将“景行”改为女性现代导游以形成性别平衡

## 11. 下一步建议

本稿确认后，建议按以下顺序推进：

1. 基于本稿生成三张概念图
2. 将概念图进一步收敛成最终人设版本
3. 把三角色拆成 Three.js 可实现参数表
4. 再进入 `ThreeAvatar` 的正式实现

## 12. 可直接衔接的后续产物

基于本稿，可以继续产出：

1. `三角色 AI 概念图提示词精修版`
2. `Three.js 角色参数表`
3. `管理端角色预览文案`
4. `游客端默认角色策略说明`
