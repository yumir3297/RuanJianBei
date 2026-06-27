# 数字导游增强功能实施方案

> 目标：提升游客游玩体验 + 展示数字人技术创新
> 预计工期：7-9 天
> 创建时间：2026-06-18

## 📊 6大创新方向

### 1️⃣ 个性化分级讲解
**目标**：让每个游客都能听懂 - 儿童/成人/专家三级模式

**技术实现**：
```python
# backend/app/schemas/visitor.py
class ExplanationLevel(str, Enum):
    CHILD = "child"      # 5-12岁：讲故事、打比方、慢语速
    ADULT = "adult"      # 成人：简明扼要、标准语速
    EXPERT = "expert"    # 深度：历史考据、建筑细节、专业术语

# backend/app/services/llm/prompt_builder.py
def build_system_prompt(level: ExplanationLevel, topic: str) -> str:
    base_prompts = {
        "child": """你是一位亲切的儿童导游。
- 用"很久很久以前..."、"你知道吗"等开头
- 多用比喻：把88米比作"30层楼那么高"
- 避免专业术语，用"金色的大佛像"而不是"青铜立像"
- 讲故事而不是背资料""",
        
        "adult": """你是专业景区导游。
- 简明扼要，3-5句话概括要点
- 提供关键数据（高度、年代、面积）
- 平衡知识性和趣味性""",
        
        "expert": """你是文化历史学者。
- 引用文献和考古资料
- 说明建筑工艺、艺术风格流派
- 对比分析（如"与龙门石窟造像风格对比"）
- 提供深度背景知识"""
    }
    return base_prompts[level]
```

**前端集成**：
```vue
<!-- frontend/src/components/ExplanationLevelSelector.vue -->
<template>
  <div class="level-selector">
    <h4>选择讲解深度</h4>
    <el-radio-group v-model="selectedLevel" @change="handleChange">
      <el-radio-button label="child">
        <el-icon><TrophyBase /></el-icon>
        儿童模式
      </el-radio-button>
      <el-radio-button label="adult">
        <el-icon><User /></el-icon>
        标准模式
      </el-radio-button>
      <el-radio-button label="expert">
        <el-icon><Reading /></el-icon>
        专业模式
      </el-radio-button>
    </el-radio-group>
  </div>
</template>
```

**数字人联动**：
- child模式 → 活泼表情、夸张手势、语速0.8x
- expert模式 → 严肃表情、学者形象、语速1.0x

---

### 2️⃣ 智能路线规划助手
**目标**：解决"第一次来不知道怎么玩"的痛点

**数据模型**：
```python
# backend/app/models/route_template.py
class RouteTemplate(Base):
    __tablename__ = "route_templates"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(100))  # "3小时历史文化精华游"
    duration_minutes: Mapped[int]  # 180
    difficulty: Mapped[str]  # easy/medium/hard
    tags: Mapped[str]  # "history,culture,photography"
    waypoints: Mapped[str]  # JSON: [{"poi": "灵山大佛", "duration": 60, "priority": 5}]
    description: Mapped[str]
    
class POI(Base):
    """景点元数据"""
    __tablename__ = "pois"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str]  # "灵山大佛"
    category: Mapped[str]  # "history" / "nature" / "architecture"
    avg_duration: Mapped[int]  # 平均游览时间（分钟）
    priority: Mapped[int]  # 1-5星推荐度
    best_photo_time: Mapped[str]  # "下午4-5点顺光"
    tips: Mapped[str]  # JSON: ["内部可登顶", "需排队30分钟"]
```

**推荐算法**：
```python
# backend/app/services/route/recommender.py
def recommend_route(
    time_budget: int,  # 分钟
    interests: List[str],  # ["history", "culture"]
    mobility: str = "normal"  # easy/normal/hard
) -> RouteTemplate:
    """
    智能推荐算法：
    1. 过滤：duration <= time_budget
    2. 匹配：tags包含interests
    3. 排序：优先级 * 兴趣匹配度
    4. 返回最佳路线
    """
    candidates = session.query(RouteTemplate).filter(
        RouteTemplate.duration_minutes <= time_budget,
        RouteTemplate.difficulty == mobility
    ).all()
    
    # 计算兴趣匹配分数
    for route in candidates:
        route_tags = set(route.tags.split(","))
        route.score = len(route_tags & set(interests)) / len(interests)
    
    return max(candidates, key=lambda r: r.score)
```

**交互式规划对话**：
```python
# backend/app/api/route.py
@router.post("/plan-interactive")
async def plan_route_interactive(request: RoutePlanRequest):
    """
    交互式路线规划：
    Q1: 您有多少时间？ → time_budget
    Q2: 更喜欢什么类型？ → interests
    Q3: 体力如何？ → mobility
    返回：推荐路线 + 数字人解说
    """
    route = recommend_route(
        time_budget=request.time_budget,
        interests=request.interests,
        mobility=request.mobility
    )
    
    # 数字人话术生成
    avatar_script = f"""
    好的！我为您规划了一条{route.duration_minutes//60}小时{route.name}：
    
    {generate_waypoint_list(route.waypoints)}
    
    预计步行距离：{calculate_distance(route)}公里
    
    需要我详细讲解每个景点吗？😊
    """
    
    return {
        "route": route,
        "avatar_message": avatar_script,
        "emotion": "happy"
    }
```

---

### 3️⃣ 交互式深度讲解
**目标**：可打断、分支选择、按需深入

**对话树结构**：
```python
# backend/app/services/explanation/dialogue_tree.py
class ExplanationNode:
    topic: str  # "灵山大佛高度"
    brief: str  # "88米，世界最高青铜立佛"
    deep_dives: List[Dict[str, str]]  # 深度分支
    
example_tree = ExplanationNode(
    topic="灵山大佛",
    brief="灵山大佛高88米，是世界最高的青铜立佛，建于1997年。",
    deep_dives=[
        {"label": "为什么是88米？", "content": "88在佛教中..."},
        {"label": "建造技术难点", "content": "采用分段浇铸..."},
        {"label": "与其他大佛对比", "content": "比乐山大佛高17米..."}
    ]
)
```

**前端交互**：
```vue
<!-- 深度讲解分支选择 -->
<div v-if="deepDiveOptions.length" class="deep-dive-panel">
  <p>{{ currentExplanation }}</p>
  <div class="branch-options">
    <span>您想了解：</span>
    <el-button 
      v-for="option in deepDiveOptions" 
      :key="option.label"
      size="small"
      @click="selectDeepDive(option)"
    >
      {{ option.label }}
    </el-button>
  </div>
</div>
```

---

### 4️⃣ 场景自适应切换
**目标**：历史类问题严肃、服务类问题友好

**问题分类**：
```python
# backend/app/services/classification/question_classifier.py
class QuestionCategory(str, Enum):
    HISTORY = "history"      # 历史文化类
    NATURE = "nature"        # 自然风光类
    SERVICE = "service"      # 服务咨询类（厕所、餐厅）
    ROUTE = "route"          # 路线导航类

def classify_question(query: str) -> QuestionCategory:
    """基于关键词/语义分类"""
    if any(kw in query for kw in ["历史", "建造", "年代", "故事"]):
        return QuestionCategory.HISTORY
    elif any(kw in query for kw in ["厕所", "餐厅", "出口", "票价"]):
        return QuestionCategory.SERVICE
    # ... 也可以用LLM分类
```

**数字人风格切换**：
```python
AVATAR_PERSONAS = {
    "history": {
        "tone": "庄重、学者式",
        "greeting": "让我为您讲述这段历史...",
        "emotion_base": "speaking",
        "speech_rate": 0.9
    },
    "nature": {
        "tone": "活泼、赞美式",
        "greeting": "这里的风景真美！",
        "emotion_base": "happy",
        "speech_rate": 1.1
    },
    "service": {
        "tone": "友好、高效",
        "greeting": "我来帮您查询...",
        "emotion_base": "speaking",
        "speech_rate": 1.0
    }
}

# SSE流中增加
{
  "event": "avatar",
  "data": {
    "emotion": "speaking",
    "persona": "history",  # ← 新增字段
    "speech_rate": 0.9
  }
}
```

---

### 5️⃣ 多模态感知与响应
**目标**：图像识别后拟人化响应

**当前能力**：
- ✅ 图像识别（Qwen Vision API）
- ✅ 语音输入（ASR）

**增强方向**：

**A. 拟人化图像响应**
```python
# backend/app/api/vision.py
@router.post("/analyze-with-context")
async def analyze_image_with_context(file: UploadFile):
    # 原有识别
    vision_result = await vision_service.analyze(image_data)
    
    # 新增：生成拟人化响应
    if vision_result.confidence > 0.8:
        avatar_message = f"我看到了{vision_result.main_attraction}！💡"
        emotion = "happy"
    else:
        avatar_message = "让我仔细看看这是哪里..."
        emotion = "thinking"
    
    # 主动推送温馨提示
    poi_meta = get_poi_metadata(vision_result.main_attraction)
    tips = f"""
    温馨提示：
    - 最佳拍照点在{poi_meta.best_photo_spot}
    - {poi_meta.upcoming_event or "暂无特殊活动"}
    - {poi_meta.tips[0] if poi_meta.tips else ""}
    """
    
    return {
        "vision_result": vision_result,
        "avatar_response": {
            "message": avatar_message + tips,
            "emotion": emotion
        }
    }
```

**B. 语音情感同步（选做）**
```python
# 从语音中提取情感特征
def analyze_voice_emotion(audio_blob: bytes) -> str:
    """
    使用声学特征判断情绪：
    - 音量大、语速快 → excited/urgent
    - 音调低、停顿多 → sad/tired
    """
    # 可以集成第三方情感识别API
    # 或简单实现：音量阈值判断
    return emotion

# 数字人响应调整
if voice_emotion == "urgent":
    avatar.speech_rate = 1.2  # 加快语速
    response_style = "简洁快速"
```

---

### 6️⃣ 知识置信度驱动的情感表达
**目标**：数字人表达对答案的"自信程度"

**置信度计算**：
```python
# backend/app/services/qa/confidence.py
def calculate_confidence(qa_result: QAResult) -> ConfidenceMetadata:
    """
    计算答案置信度并映射情感
    """
    if qa_result.source == "faq" and qa_result.match_score > 0.9:
        return ConfidenceMetadata(
            level="high",
            score=qa_result.match_score,
            emotion="happy",
            message_prefix="我很确定："
        )
    
    elif qa_result.source == "llm":
        evidence_count = len(qa_result.evidence)
        if evidence_count >= 3:
            return ConfidenceMetadata(
                level="medium",
                score=0.75,
                emotion="speaking",
                message_prefix="根据官方资料，"
            )
        else:
            return ConfidenceMetadata(
                level="low",
                score=0.5,
                emotion="thinking",
                message_prefix="让我想想...（证据较少）"
            )
    
    elif qa_result.is_blind_spot:
        return ConfidenceMetadata(
            level="none",
            score=0.0,
            emotion="apology",
            message_prefix="抱歉，这个问题超出了我的知识范围。"
        )
```

**SSE流扩展**：
```python
# 在answer事件中增加置信度元数据
{
  "event": "answer",
  "data": {
    "text": "灵山大佛高88米...",
    "confidence": {
      "level": "high",
      "score": 0.92,
      "evidence_count": 5
    }
  }
}

# avatar事件中反映置信度
{
  "event": "avatar",
  "data": {
    "emotion": "happy",  # 由confidence.level决定
    "intensity": 0.92,   # 表情强度
    "gesture": "thumbs_up"  # 高置信度时竖大拇指
  }
}
```

---

## 🗓️ 实施时间线

### Phase 1: 后端基础（3天）
- [ ] Day 1-2: RouteTemplate模型 + 推荐算法 + ExplanationLevel配置
- [ ] Day 2-3: SSE协议扩展（confidence/avatar_context） + 置信度计算

### Phase 2: 前端交互（3天）
- [ ] Day 4: 讲解模式选择器 + 路线规划对话界面
- [ ] Day 5: Vision增强（拟人化响应）+ 深度讲解UI
- [ ] Day 6: 整合所有前端组件到ChatView

### Phase 3: 数字人联动（2天）
- [ ] Day 7: 场景自适应 + 置信度驱动情感
- [ ] Day 8: 状态切换优化 + 全流程测试

### Phase 4: 优化与演示（1天）
- [ ] Day 9: 性能优化 + 准备演示场景 + 技术文档

---

## 📂 文件结构规划

```
backend/
├── app/
│   ├── models/
│   │   ├── route_template.py  # 新增
│   │   └── poi.py             # 新增
│   ├── services/
│   │   ├── route/
│   │   │   ├── recommender.py # 新增
│   │   │   └── planner.py     # 新增
│   │   ├── explanation/
│   │   │   ├── dialogue_tree.py  # 新增
│   │   │   └── level_adapter.py  # 新增
│   │   └── qa/
│   │       └── confidence.py  # 扩展
│   ├── schemas/
│   │   ├── route.py          # 新增
│   │   └── visitor.py        # 扩展
│   └── api/
│       └── route.py          # 新增

frontend/src/
├── components/
│   ├── ExplanationLevelSelector.vue  # 新增
│   ├── RoutePlanDialog.vue          # 新增
│   └── DeepDivePanel.vue            # 新增
├── composables/
│   └── useAvatar.js                 # 扩展（置信度映射）
└── views/tourist/
    └── ChatView.vue                 # 集成新功能
```

---

## 🎯 评审要点准备

### 技术创新点总结
1. **知识图谱驱动的情感智能** - 不是预设动画，而是实时计算置信度
2. **场景自适应人设切换** - 历史学者 vs 服务助手
3. **交互式深度讲解** - 分支对话树，游客主导深度
4. **智能路线规划** - 多维度推荐算法（时间/兴趣/体力）
5. **多模态拟人化** - 图像识别后"我看到了..."而非冷冰冰JSON

### 用户体验提升数据（模拟）
- 讲解满意度：68% → 89% (+31%)
- 路线使用率：91%的游客使用智能规划
- 深度交互率：二次提问率提升292%
- 平均停留时间：45min → 78min (+73%)

### 答辩话术模板
```
评委：这个数字人是你们自己做的吗？

回答：我们使用了成熟的渲染SDK（Live2D/Three.js），
这是业界标准做法。我们的创新在于：

1. 将数字人与知识图谱深度绑定 - 根据答案置信度
   自动切换表情，传递"确定性"/"真诚性"

2. 场景自适应人设系统 - 历史问题用学者语气，
   服务问题用助手语气，而不是机械播报

3. 流式感知的渐进式呈现 - 优化冷启动体验，
   首个token到达即进入speaking状态（2.6s），
   而非等待全部生成（30s）

这些创新让数字人从"会说话的动画"升级为
"有情感、能共情的智能导游"。
```

---

## ⚠️ 风险与应对

### 风险1：开发时间不足
**应对**：按优先级实施，Phase 1-2必做，Phase 3选做

### 风险2：Live2D模型资源缺乏
**应对**：
- 方案A：使用官方免费示例模型（Haru等）
- 方案B：降级为2D静态图片+表情切换

### 风险3：LLM输出不稳定影响置信度
**应对**：在prompt中强制要求返回confidence字段

---

## 📚 参考资源

- Live2D Cubism SDK: https://www.live2d.com/en/download/cubism-sdk/
- 阿里云TTS API: https://help.aliyun.com/document_detail/84435.html
- Element Plus: https://element-plus.org/
- DeepSeek API: https://platform.deepseek.com/docs

---

**下一步行动**：从 Task 1 开始实施 - 扩展RouteTemplate模型
