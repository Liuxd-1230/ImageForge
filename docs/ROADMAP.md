# Roadmap

## Phase 0：规格确认

必须确认：

- 目录
- 数据模型
- API
- 中间语义表示
- Provider 边界
- Prompt Pipeline

不要立即铺大量页面。

---

## Phase 1：项目骨架与连接能力

完成：

- Vue + Vite + TypeScript
- Vuetify / MD3 基础主题
- FastAPI
- SQLite
- Provider 配置
- LM Studio 连接
- 模型列表
- load / inference / unload
- ComfyUI 在线检测

验收：

用户能设置 LM Studio 和 ComfyUI，并保存配置。

---

## Phase 2：Prompt Engine 最小闭环

完成：

- 用户自然语言输入
- 语义事实抽取
- entity / statement
- Character Trigger Resolver
- 角色书命中逻辑
- Prompt Writer
- Safe / NSFW
- 最终英文 Prompt
- Prompt 预览

这是最重要阶段。

验收：

`GOLDEN_CASES.md` 中与 Prompt Engine 相关案例通过。

---

## Phase 3：资源库

完成：

- 角色书
- Trigger cache
- 画师库
- 分类
- 收藏
- 规则文件

验收：

用户无需改配置文件即可管理这些资源。

---

## Phase 4：LoRA + ComfyUI 完整生图

完成：

- 扫描 LoRA
- LoRA trigger mapping
- strength
- enable / disable
- Workflow Template
- `/prompt`
- WebSocket progress
- Result image

验收：

从中文自然语言到实际图片形成完整闭环。

---

## Phase 5：历史和体验打磨

完成：

- 历史记录
- 恢复参数
- 复制 Prompt
- 错误处理
- 空状态
- 加载状态
- MD3 UI 打磨
- 响应式

---

## Phase 6：高级能力

按实际需要评估：

- 创意补全模式
- 区域 Prompt
- Attention Couple / Regional Prompt
- 角色参考图
- 高级多人控制
- 更多 Workflow Template

只有实际需要时再做。

---

## Phase 7：实验功能

评估：

- TE_MAN
- 3D Director
- 外部导演台
- Prompt 交换
- 兼容导出

不影响核心产品稳定性。
