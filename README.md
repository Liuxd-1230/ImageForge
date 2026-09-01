# ImageForge — Anima 二次元提示词与生图工作台

面向 **Anima 2.9B** 二次元生图模型的本地优先 Web 创作工作台。

> **核心价值**：把用户已经表达的画面要求（中文自然语言），可靠地转换为适合 Anima 的英文 Prompt，并管理用户角色书（覆盖层）、画师库（@artist 规范）、LoRA 动态权重与 ComfyUI 生图流程。

---

## ✨ 核心特性

- **忠实语义解析**：基于开放式 Statement（`facet` + `effect`），忠实提取人物动作与服装归属，严格禁止 AI 脑补未提及的背景、外貌与表情。
- **角色书覆盖层机制**：
  - 角色书命中：展开用户自定义设定，角色名绝不作为 Anima tag 输出；当前输入要求（如泳装）确定性覆盖角色书默认服装。
  - 未命中：按 Anima 已训练角色处理，使用 Canonical Trigger，不展开原作冗余外貌。
- **Tag 与自然语言分工**：
  - Tag 区表达 Quality、Safety、人数、Character Trigger、@Artist、LoRA Trigger。
  - 英文自然语言表达人物属性归属、动作交互与空间关系，杜绝多人场景退化为 Tag Soup。
- **全控制链创作台**：
  - 本地 LM Studio 与云端 OpenAI 兼容 API 一键切换，支持思考强度（Instruct / Low / Medium / High / Xhigh / Max）调节。
  - 显式 4 档 Safety（Safe / Sensitive / NSFW / Explicit）控制。
  - 画师库浏览器（@artist 规范，快速筛选、收藏与一键选用）。
  - LoRA 创作联动与 0.10 ~ 1.50 实时权重滑块（勾选即时联动 Prompt 与 ComfyUI）。
- **ComfyUI 官方 Anima-2.9B 工作流**：内置针对 Anima-2.9B 优化的 txt2img 生成工作流（Euler + sgm_uniform / beta，CFG 4.5，1024×1536），支持导入自定义工作流 JSON。

---

## 🚀 快速启动

### 方式一：一键启动（推荐）

在项目根目录下直接运行一键启动脚本：

```bash
./start.sh
```

- **前端创作台**：[http://localhost:5173](http://localhost:5173)
- **后端 API 服务**：[http://localhost:8000](http://localhost:8000)
- **Swagger API 文档**：[http://localhost:8000/docs](http://localhost:8000/docs)

### 方式二：手动分步启动

**1. 启动后端**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

**2. 启动前端**
```bash
cd frontend
npm install
npm run dev
```

---

## 🧪 自动化测试

运行针对 `docs/GOLDEN_CASES.md` 的全部 18 个 Golden Cases 验收测试：

```bash
PYTHONPATH=backend backend/.venv/bin/pytest -q backend/tests/test_golden_cases.py
```

---

## 🛠️ 技术栈

- **前端**：Vue 3 + Vite + TypeScript + Pinia + Vuetify 3 (Material Design 3)
- **后端**：Python 3.12 + FastAPI + SQLModel + SQLite + httpx
- **LLM**：LM Studio（本地） / OpenAI Compatible API（云端）
- **生图引擎**：ComfyUI (Anima 2.9B)

---

## 📄 开源许可

MIT License
