# 手机地图任务页重构

用户已要求重新调研并重构，并明确要求地图占据操作页面、降低卡片占位。实施选择：固定全幅地图 + 单一可收起任务面板；保留数字人及原播放生命周期。

调研：Apple Maps HIG（https://developer.apple.com/design/human-interface-guidelines/maps）强调熟悉的地图交互与地点卡；Sheets HIG（https://developer.apple.com/design/human-interface-guidelines/sheets）强调一次一个面板；Disneyland Paris 官方 App（https://www.disneylandparis.com/en-usd/mobile-app）使用地图/列表寻找活动；WCAG 2.5.5（https://www.w3.org/WAI/WCAG22/Understanding/target-size-enhanced.html）给出 44px 增强目标尺寸。来源为官方说明；不是竞品实机测试。

落实到本项目：手机地图始终铺满标题下可用空间；景点/路线/图层/园区信息一次只显示一个面板。拖动地图不带动页面；列表滚动限定于面板。天气与演示客流不常驻。点击景点就地显示名称及听讲解入口。查询聊天保留地图。真实定位使用独立按钮，不把失败自动伪装成模拟成功；自动讲解维持现有模拟降级但明确标识。

任务：
- [x] MapView 重构信息架构、搜索与地点卡，独立定位反馈。
- [x] 清除上一轮地图布局覆盖，统一 map-task 容器和独立样式。
- [x] 浏览器验收 320/390/429 手机、844 横屏、768 平板和 1024/1440 桌面；搜索选点、面板互斥、路线显示、权限失败可继续浏览。
- [x] 前端测试及构建；更新地图与交付记录。

验证边界：Chrome 触屏仿真不等于 iOS/微信真机；真实导航与路网数据未接入，路线只标“示意”。不增加付费模型调用。
