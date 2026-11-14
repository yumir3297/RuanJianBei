# 集成调研记录

记录实际访问的资料和对当前代码的影响；以下阅读不等于实现或验收。

## 2026-11-13：确认请求重试

- [RFC 9110 §9.2.2](https://www.rfc-editor.org/rfc/rfc9110.html#section-9.2.2)，本次联网取得并阅读对应原文：幂等方法的多次相同请求在服务端的预期效果与单次相同；PUT、DELETE 和安全方法属于该规范定义的幂等方法，非幂等方法不能仅凭请求重试就假定安全。项目的确认操作是 POST，使用应用层幂等键和请求内容校验；隔离测试核对相同键的重放不再新增行程版本。RFC 本身不规定本项目幂等键的实现，也不证明并发或跨数据库行为。

## 2026-11-12：共享状态和离线缓存

- [Pinia State 官方文档](https://pinia.vuejs.org/core-concepts/state.html)，2026-11-12 访问。状态在 `state()` 中定义，初始字段应显式声明，option store 的 `$reset()` 从初始状态重建。对本项目：合并时先列出状态归属和生命周期，避免运行中随意增加状态或把音频引擎对象当作跨页面持久数据。统一共享视图仍需要通过受控 action、请求版本和后端权威规则来设计，这些是本项目方案，不是 Pinia 文档本身的规定。
- [MDN：Using Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers)，2026-11-12 访问。Service Worker 要求安全上下文、同源路径及明确作用域；已有页面默认不会立刻受新注册 worker 控制，更新还有等待和激活阶段。对本项目：离线陪游纳入游客端构建时，验证 localhost 环境、作用域、首次安装后的控制与缓存更新，不能仅以注册成功证明断网可用。具体代码尚未接入。

后续按功能继续补充，优先官方文档，并记录适用版本、取舍和实际结果。

## 2026-11-13：读取已发布版本

- [SQLAlchemy ORM 查询选项](https://docs.sqlalchemy.org/en/20/orm/queryguide/api.html#populate-existing)，2026-11-13 本次联网访问：`populate_existing` 可刷新身份映射中已有对象。项目的 K01 可见性检查直接查询数据库中的条目 ID 和发布版本标量，避免仅依赖已加载的 ORM 对象；数据库事务隔离及并发提交仍需单独验证，不能据此声称所有并发场景均已解决。
- [Element Plus Select](https://element-plus.org/en-US/component/select.html)，2026-11-13 本次联网访问，确认文档包含 `filterable` 和 `loading` 选项。试验面板使用可搜索选择器和加载状态；候选是否可绑定仍由本项目的发布状态校验负责。
- [Playwright Locators](https://playwright.dev/docs/locators)，2026-11-13 本次联网访问：文档介绍按角色定位和自动等待。管理端浏览器复测使用角色定位和显式状态等待；脚本只访问固定本机地址并要求隔离数据确认。
- [Pinia State](https://pinia.vuejs.org/core-concepts/state.html)，2026-11-13 再次联网访问，确认状态重置与显式初始状态的说明。共享定位使用运行时 store 和明确清除动作；地图隐藏时丢弃定位是本项目的生命周期设计，未依赖持久化插件。
- [MDN Geolocation.clearWatch](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/clearWatch)，2026-11-13 本次联网访问：`clearWatch` 使用 `watchPosition` 返回的标识停止监听。本项目额外用 generation 拒绝已排队或来自旧监听的回调，这是应用层防护，不能代替真机验证。
- [MDN AudioScheduledSourceNode ended](https://developer.mozilla.org/en-US/docs/Web/API/AudioScheduledSourceNode/ended_event)，2026-11-13 再次联网访问：自然结束和 `stop()` 都可能产生 ended；共享播放记录继续依赖播放器会话及停止 generation，不能仅凭 ended 判定完整收听。浏览器/硬件实际表现仍需验证。
- [Vue computed 属性](https://vuejs.org/guide/essentials/computed.html)，2026-11-13 本次联网访问：computed 跟踪响应式依赖。情境讲解请求从行程进度、当前景点及目录派生，行程状态变化会重新计算；已加载目录是否仍为最新需单独校验，不能由 computed 保证。
- [MDN AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)，2026-11-13 再次联网访问：可中止受 signal 控制的请求。当前目录复核采用结果 generation 和输入快照检查；旧请求可能仍完成，但不能据此发送讲解。后续可加入请求取消以节省资源，不能用取消替代结果校验。
- [MDN Using Service Workers](https://developer.mozilla.org/en-US/docs/Web/API/Service_Worker_API/Using_Service_Workers)，2026-11-13 再次联网访问：新 worker 的安装、等待和激活是不同阶段。离线升级测试分别核对旧页面响应、新缓存激活和断网读取；瞬时 worker 状态不可单独证明旧页面体验。
- [MDN ServiceWorkerRegistration.update](https://developer.mozilla.org/en-US/docs/Web/API/ServiceWorkerRegistration/update)，2026-11-13 本次联网访问，核对更新检查与安装流程；失败测试显式触发更新并观察新 worker 失败后旧包的实际离线读取，不把更新调用返回视为安装成功。
- [pypdf 文本提取](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)，2026-11-13 本次联网访问：文档说明图片中的文字需要 OCR，pypdf 本身不是 OCR 引擎。当前 PDF 导入对无可提取文本页要求人工核查；不能借此证明有文本层的页面识别准确。
- [FastAPI 文件上传](https://fastapi.tiangolo.com/tutorial/request-files/)，2026-11-13 本次联网访问：文档介绍 `UploadFile` 和 spooled file；现有导入沿用上传限额与持久任务链，本次未变更文件存储或上传接口。
- [python-docx 快速入门](https://python-docx.readthedocs.io/en/latest/user/quickstart.html)，2026-11-13 本次联网访问：文档介绍 Word 文档及表格操作。项目按正文块遍历并限制复杂结构；正文以外内容和 OCR 不在本次能力内。
- [Playwright 输入操作](https://playwright.dev/docs/input)，2026-11-13 本次联网访问：文档介绍 `setInputFiles`。本次在隔离演示服务中使用它操作管理端真实文件上传控件，再核对任务和草稿状态。
- [Playwright Assertions](https://playwright.dev/docs/test-assertions)，2026-11-13 本次联网访问，核对自动等待断言思路；本次浏览器脚本以等待页面状态和核验 API 结果确认候选取消与保存的不同效果。
- [OCRmyPDF Cookbook](https://ocrmypdf.readthedocs.io/en/latest/cookbook.html)，2026-11-13 本次联网访问：文档描述 `--skip-text` 对已有文本页的处理；本地 OCR 使用该选项，并重新逐页检查输出。该选项不保证识别准确，也不能替代人工校对。
- [OCRmyPDF Languages](https://ocrmypdf.readthedocs.io/en/latest/languages.html)，2026-11-13 本次联网访问：语言选择与识别引擎及其语言资源有关。本机 AppleOCR 使用 `chi_sim` 对合成中文样例通过；不推广为真实文档准确率结论。
- [FastAPI FileResponse](https://fastapi.tiangolo.com/advanced/custom-response/)，2026-11-13 本次联网访问，核对文件响应与文件名参数；来源下载另由项目验证管理员身份、当前修订和存储路径，避免把响应类型当作权限校验。
- [openpyxl 教程](https://openpyxl.readthedocs.io/en/stable/tutorial.html)，2026-11-13 本次联网访问：文档区分 `data_only` 对公式和缓存值的读取。当前导入使用公式形式并拒绝公式单元格，要求人工确认确定值；不把可能缺失或过期的缓存结果当作已核实事实。
- [Pydantic Models](https://docs.pydantic.dev/latest/concepts/models/)，2026-11-13 本次联网访问：模型用于解析和验证结构，但字段合规不证明内容真实。来源字段暴露与人工审核是独立要求，不能把 AI 输出通过 schema 视为事实核验。
- [HTTPX Timeouts](https://www.python-httpx.org/advanced/timeouts/)，2026-11-13 本次联网访问：HTTPX 支持请求超时配置。理解预览同时复用项目的总超时和并发限制；超时返回失败，不将部分输出当作候选。

## 2026-11-12：共享动作与取消

- [Pinia Actions 官方文档](https://pinia.vuejs.org/core-concepts/actions.html)，2026-11-12 访问：action 是 store 的业务逻辑入口，支持同步或异步操作。当前实现将游客端安全暂停状态放在独立 Pinia store，通过 action 接收 CASS 控制器状态；并不据此认定其他导览状态已统一。
- [MDN：AbortController](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)，2026-11-12 访问：可通过 signal 请求中止 fetch 和响应体处理；取消请求不替代对已经返回或无法取消的结果进行版本校验。当前 CASS 保留 AbortController 与 generation 双重隔离，后续仍须验证其他调用链。

## 2026-11-12：播放完成与训练中断

- [MDN：AudioScheduledSourceNode ended 事件](https://developer.mozilla.org/en-US/docs/Web/API/AudioScheduledSourceNode/ended_event)，2026-11-12 访问：音频自然结束或调用 stop 后都可能触发 ended。当前播放器结合自身 stop generation 区分被停止的旧会话，只有当前会话自然结束才报告完成；真实设备和媒体异常仍需验证。
- [MDN：SpeechSynthesisUtterance end 事件](https://developer.mozilla.org/en-US/docs/Web/API/SpeechSynthesisUtterance/end_event)，2026-11-12 访问：end 表示该 utterance 已结束；语音失败还有不同事件。当前浏览器朗读是可能被截短的降级方式，不能当作完整讲解已听。
- [PyTorch：Saving and Loading Models](https://docs.pytorch.org/tutorials/beginner/saving_loading_models.html)，2026-11-12 访问：恢复训练通常需要保存模型和优化器等训练状态。当前 GuideMatch 训练脚本仅在训练阶段结束写模型权重，不具备中断续训；数据、配置及早停/调度和随机状态也需结合实际训练流程设计并验证，不能只加载推理权重就声称完整续训。
- [Alembic：Working with Branches](https://alembic.sqlalchemy.org/en/latest/branches.html)，2026-11-12 访问：多个迁移 head 需要明确合并节点和升级路径。GuideLoop 迁移与现有集成历史分支不同，后续须保留真实历史并验证空库与既有库升级，不能只改文件头使检查通过。
- [FastAPI：Dependencies with yield and StreamingResponse](https://fastapi.tiangolo.com/advanced/advanced-dependencies/)，2026-11-12 访问：官方文档说明 0.118.0 以前 `yield` 依赖会在发送流式响应前运行退出代码。本项目固定 FastAPI 0.116.1；本地追踪确认数据库依赖先关闭、流中操作又重新打开会话。现有聊天流在生成器 finally 显式关闭会话并释放容量，测试覆盖完整和提前关闭；仍需真实服务和部署回归。
