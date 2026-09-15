<script setup>
import AppIcon from '../components/AppIcon.vue'
import StatusPill from '../components/StatusPill.vue'

defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['navigate'])
</script>

<template>
  <main class="portal-view" aria-label="ProcessPilot 入口选择">
    <section class="portal-hero">
      <div class="portal-brand">
        <span class="brand-symbol"><i></i><b></b><em></em></span>
        <div><strong>ProcessPilot</strong><small>APC Modeling Agent</small></div>
      </div>
      <StatusPill tone="success" dot>工程服务已启动</StatusPill>
      <h1>选择工作入口</h1>
      <p>工作人员板块保留完整工程驾驶舱、数据工程、建模交付与编排追踪；用户板块聚焦 Agent 智能中枢，用自然语言上传数据、提问和查看运行反馈。</p>
    </section>

    <section class="portal-choice-grid">
      <button class="portal-choice staff" type="button" @click="emit('navigate', '/overview/')">
        <span class="choice-icon"><AppIcon name="dashboard" :size="30" /></span>
        <span class="choice-copy">
          <small>STAFF WORKSPACE</small>
          <strong>工作人员板块</strong>
          <em>进入完整工程后台，管理项目、数据、三维场景、建模寻优和评审交付。</em>
        </span>
        <span class="choice-meta">
          <b>{{ project.shortName }}</b>
          <i>完整权限</i>
        </span>
        <AppIcon name="arrow" class="choice-arrow" />
      </button>

      <button class="portal-choice user" type="button" @click="emit('navigate', '/user/')">
        <span class="choice-icon"><AppIcon name="spark" :size="30" /></span>
        <span class="choice-copy">
          <small>USER AGENT</small>
          <strong>用户板块</strong>
          <em>仅保留 Agent 智能中枢，适合直接上传 CSV、描述问题并查看执行进度。</em>
        </span>
        <span class="choice-meta">
          <b>Agent 对话</b>
          <i>简洁入口</i>
        </span>
        <AppIcon name="arrow" class="choice-arrow" />
      </button>
    </section>
  </main>
</template>

<style scoped>
.portal-view {
  min-height: 100vh;
  display: grid;
  align-content: center;
  gap: 28px;
  padding: clamp(28px, 5vw, 70px);
  background:
    linear-gradient(120deg, rgba(238, 244, 255, .86), rgba(248, 251, 255, .98)),
    radial-gradient(circle at 78% 20%, rgba(37, 99, 235, .16), transparent 32%);
}

.portal-hero { max-width: 900px; }
.portal-brand { display: inline-flex; gap: 12px; align-items: center; margin-bottom: 26px; }
.portal-brand div strong,
.portal-brand div small { display: block; }
.portal-brand div strong { color: #10233e; font-size: 18px; }
.portal-brand div small { margin-top: 2px; color: #70839f; font-size: 10px; letter-spacing: .12em; text-transform: uppercase; }
.portal-hero h1 { margin-top: 18px; color: #0f1d33; font-size: clamp(34px, 5vw, 58px); line-height: 1.05; letter-spacing: -.045em; }
.portal-hero p { max-width: 780px; margin-top: 16px; color: #5f7088; font-size: 14px; line-height: 1.8; }

.portal-choice-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 18px; max-width: 1180px; }
.portal-choice {
  position: relative;
  display: grid;
  grid-template-columns: 58px minmax(0, 1fr) auto 22px;
  gap: 16px;
  align-items: center;
  min-height: 190px;
  padding: 24px;
  text-align: left;
  border: 1px solid #d6e2f1;
  border-radius: 18px;
  background: rgba(255, 255, 255, .9);
  box-shadow: 0 20px 52px rgba(15, 35, 68, .10);
  cursor: pointer;
  transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease;
}
.portal-choice:hover { transform: translateY(-3px); border-color: #9abcf4; box-shadow: 0 26px 70px rgba(37, 99, 235, .16); }
.choice-icon { display: grid; place-items: center; width: 58px; height: 58px; color: #fff; border-radius: 15px; background: linear-gradient(145deg, #2868e8, #37bdf8); box-shadow: 0 12px 26px rgba(37, 99, 235, .22); }
.portal-choice.user .choice-icon { background: linear-gradient(145deg, #0f766e, #2dd4bf); box-shadow: 0 12px 26px rgba(13, 148, 136, .18); }
.choice-copy small { color: #2563eb; font-size: 10px; font-weight: 800; letter-spacing: .12em; }
.portal-choice.user .choice-copy small { color: #0f766e; }
.choice-copy strong { display: block; margin-top: 7px; color: #111c30; font-size: 26px; letter-spacing: -.03em; }
.choice-copy em { display: block; max-width: 520px; margin-top: 8px; color: #697b92; font-size: 12px; font-style: normal; line-height: 1.65; }
.choice-meta { display: grid; gap: 7px; justify-items: end; color: #5b6b80; font-size: 10px; }
.choice-meta b { color: #284a78; font-size: 11px; }
.choice-meta i { padding: 5px 8px; color: #1d4ed8; font-style: normal; border: 1px solid #c9daf8; border-radius: 999px; background: #f0f5ff; }
.portal-choice.user .choice-meta i { color: #0f766e; border-color: #bdebdc; background: #ecfdf5; }
.choice-arrow { color: #8aa0ba; }

@media (max-width: 860px) {
  .portal-choice-grid { grid-template-columns: minmax(0, 1fr); }
  .portal-choice { grid-template-columns: 52px minmax(0, 1fr) 18px; min-height: 160px; }
  .choice-meta { grid-column: 2 / 3; justify-items: start; }
}

@media (max-width: 560px) {
  .portal-view { padding: 22px 16px; }
  .portal-choice { grid-template-columns: minmax(0, 1fr); }
  .choice-icon { width: 50px; height: 50px; }
  .choice-arrow { display: none; }
}
</style>
