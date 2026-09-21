# 🧙‍♂️ The Frontend Grimoire (前端秘籍)

> "写代码不只是为了让机器运行，更是为了让人类（和你未来的自己）阅读。"

欢迎来到 **Data Task Platform** 的前端世界。这不是一份冷冰冰的说明书，而是一本记录了我们**设计哲学、代码魔法和避坑经验**的探险手册。

如果你刚接手这个项目，或者想让 AI 帮你干活，读它就对了。

---

## 🎨 第一章：我们的设计灵魂 (The Soul)

我们抛弃了那种“一看就是后台管理系统”的深色赛博风，转而拥抱 **Light Notion Style**。
关键词：**干净、呼吸感、物理质感**。

### 1. 颜色的艺术
我们不再说“白色”或“灰色”，我们说：
*   **"画布 (Canvas)"**: `bg-background` (纯白)。这是所有内容的基底。
*   **"纸张 (Paper)"**: `bg-background-secondary` (米白)。这是侧边栏和次级区域的颜色，像一张高级信纸。
*   **"墨水 (Ink)"**: `text-text` (深灰)。永远不要用纯黑 (`#000`)，太刺眼了。我们用 Notion 同款深灰，温润如玉。

### 2. 动效的物理学
我们希望界面是“活”的，但不是“吵”的。
*   **3D 按压**: 重要的按钮（如“发布任务”）按下去时，会有真实的下沉感 (`effect="3d"`)。
*   **极光流动**: 登录页的背景不是静止的，它在缓慢流动 (`.gradient-flow`)，像呼吸一样。
*   **新拟态 (Neumorphism)**: 重要的卡片不是贴在屏幕上，而是从屏幕里“凸”出来的 (`.neumorphic`)。

---

## 🧩 第二章：组件魔法书 (Component Spells)

别手写 `div` 和 `className` 了，用我们封装好的魔法组件。

### 1. 那个万能的按钮 (The Button)
> "我要一个让人忍不住想点的按钮。"

```tsx
// ❌ 平平无奇
<button className="bg-blue-500 text-white">Click me</button>

// ✅ 魔法加持：3D 按压 + 光泽感
<Button variant="primary" effect="3d" size="lg">
  立即启动
</Button>
```

### 2. 会呼吸的卡片 (The Card)
> "这个列表太死板了，动起来。"

```tsx
// ✅ 悬浮时会上浮，并且投影加深
<Card hoverEffect className="bg-white/80 backdrop-blur">
  <CardTitle>任务 A</CardTitle>
  ...
</Card>
```

### 3. 统一的标签 (The Tag)
> "为什么这个标签看起来像贴在墙上的，那个像嵌在墙里的？"

我们统一了 Tag 和 Badge 的风格：**半透明背景 + 深色文字 + 极细边框**。
这叫 **Tinted Style**，看起来通透又高级。

---

## 🗣️ 第三章：如何指挥 AI 干活 (The Whisper)

AI 是个好工兵，但它需要精准的指令。别跟它说“好看一点”，它不懂审美。

### 1. 唤醒咒语 (Wake-up Call)
每次开始新任务，先发这段话，让它对齐上下文：

> "嘿，我们要写新页面了。
> 记住：设计风格是 **Light Notion**。
> 核心变量定义在 `src/index.css`。
> 组件库在 `src/components/ui/`。
> 别用 Ant Design，别用深色背景。"

### 2. 精准施法 (Precision Prompting)
试着这样描述需求：

> "帮我写一个 **设置页面**：
> 1.  **布局**：用 `Layout` 组件包裹。
> 2.  **标题**：用 `gradient-text`（渐变字）写上'系统设置'。
> 3.  **容器**：用一个 `Card (variant='neumorphic')` 包裹表单。
> 4.  **按钮**：保存按钮要 `primary` 且带 `ripple`（涟漪）效果。"

---

## 🕳️ 第四章：避坑指南 (The Pitfalls)

这些坑我们已经替你踩过了，别再跳进去了。

### 1. ❌ 别碰 `tailwind.config.js`
我们升级到了 **Tailwind v4**。所有的变量配置都在 `src/index.css` 的 `@theme` 块里。
如果你去改 js 配置文件，什么都不会发生，除了让你怀疑人生。

### 2. ❌ 别用 `px-` 硬编码间距
不要写 `margin-top: 13px` 这种奇怪的数字。
请用 Tailwind 的标准尺度：`mt-2` (8px), `mt-4` (16px)。
**一致的韵律感**比什么都重要。

### 3. ❌ 别让深色模式“回光返照”
我们彻底移除了 Dark Mode 的支持。
如果你发现某个组件背景突然变黑了，检查一下是不是引入了旧的 `antd` 组件，或者手写了 `@media (prefers-color-scheme: dark)`。
如果有，删掉它。

---

## 📜 结语

前端开发不仅仅是堆砌代码，它是在**搭建一个用户愿意停留的空间**。
保持代码的整洁，保持设计的克制，保持对细节的热爱。

愿你的控制台永远没有 Error，愿你的 CSS 永远不塌陷。✨
