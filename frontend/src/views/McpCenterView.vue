<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { apiRequest } from '../api/client'
import AppIcon from '../components/AppIcon.vue'
import StatusPill from '../components/StatusPill.vue'

const state = ref(null)
const loading = ref(true)
const error = ref('')
let refreshTimer

const server = computed(() => state.value?.server ?? {})
const computeTools = computed(() => state.value?.tools?.filter((tool) => tool.category === '计算工具') ?? [])
const supportTools = computed(() => state.value?.tools?.filter((tool) => tool.category !== '计算工具') ?? [])
const jobs = computed(() => state.value?.jobs ?? [])

const statusLabel = {
  queued: '排队中', running: '运行中', completed: '已完成', blocked: '已阻断',
  failed: '失败', cancelled: '已取消',
}

function statusTone(status) {
  if (status === 'completed') return 'success'
  if (status === 'failed' || status === 'blocked') return 'warning'
  if (status === 'running') return 'brand'
  return 'neutral'
}

async function load() {
  error.value = ''
  try { state.value = await apiRequest('/mcp/') }
  catch (cause) { error.value = cause.message }
  finally { loading.value = false }
}

onMounted(() => {
  load()
  refreshTimer = window.setInterval(load, 10000)
})
onBeforeUnmount(() => window.clearInterval(refreshTimer))
</script>

<template>
  <section class="mcp-page">
    <header class="mcp-hero" :class="{ offline: !server.online }">
      <div class="mcp-hero-copy">
        <span class="eyebrow">MODEL CONTEXT PROTOCOL</span>
        <h1>MCP 工具中心</h1>
        <p>网页负责交互，Django Agent 通过 MCP 调用工业算法；这里展示真实连接、工具契约与任务证据。</p>
        <div class="server-address"><AppIcon name="network" :size="16" /><code>{{ server.endpoint || '尚未配置 MCP 地址' }}</code></div>
      </div>
      <div class="connection-card">
        <span class="connection-light"></span>
        <div><small>processpilot-modeling</small><strong>{{ server.online ? 'MCP ONLINE' : 'MCP OFFLINE' }}</strong><p>{{ server.online ? `${server.tool_count} 个工具已完成握手` : '请通过 npm run dev 启动服务' }}</p></div>
        <button type="button" :disabled="loading" @click="load">{{ loading ? '检查中' : '重新检查' }}</button>
      </div>
    </header>

    <p v-if="error" class="mcp-error"><AppIcon name="alert" :size="17" />{{ error }}</p>

    <div class="mcp-metrics">
      <article><span>连接方式</span><strong>{{ server.transport || '—' }}</strong><small>本机 HTTP，由后端代理调用</small></article>
      <article><span>注册工具</span><strong>{{ state?.tools?.length ?? 0 }}</strong><small>3 个计算工具 + 6 个支撑工具</small></article>
      <article><span>MCP 历史任务</span><strong>{{ jobs.length }}</strong><small>页面展示最近 20 条记录</small></article>
      <article><span>控制边界</span><strong>只建议</strong><small>PLC / DCS 写入：禁止</small></article>
    </div>

    <section class="mcp-panel">
      <div class="panel-title"><div><span>赛题能力映射</span><h2>Agent 实际通过 MCP 调用的三项工业能力</h2></div><StatusPill :tone="server.online ? 'success' : 'warning'">{{ server.online ? '调用链就绪' : '等待服务' }}</StatusPill></div>
      <div class="compute-grid">
        <article v-for="(tool, index) in computeTools" :key="tool.name">
          <b>0{{ index + 3 }}</b><div><span>{{ tool.label }}</span><code>{{ tool.name }}</code><p>{{ tool.description }}</p></div>
          <footer><span>{{ tool.skills.length }} 个 Skill</span><span>{{ tool.quality_gates.length }} 项门禁</span></footer>
        </article>
      </div>
    </section>

    <section class="mcp-flow" aria-label="MCP 调用链">
      <div><strong>Web 前端</strong><small>提交自然语言任务</small></div><AppIcon name="arrow" />
      <div><strong>Django Agent</strong><small>意图识别与 Skill 路由</small></div><AppIcon name="arrow" />
      <div class="active"><strong>MCP Server</strong><small>工具契约与任务隔离</small></div><AppIcon name="arrow" />
      <div><strong>算法 Worker</strong><small>真实数据计算与证据落盘</small></div>
    </section>

    <div class="mcp-columns">
      <section class="mcp-panel">
        <div class="panel-title"><div><span>Supporting Tools</span><h2>任务、证据与知识工具</h2></div></div>
        <div class="support-list">
          <article v-for="tool in supportTools" :key="tool.name"><span><AppIcon :name="tool.read_only ? 'file' : 'shield'" :size="17" /></span><div><strong>{{ tool.label }}</strong><code>{{ tool.name }}</code><p>{{ tool.description }}</p></div><b>{{ tool.read_only ? '只读' : '受控写入' }}</b></article>
        </div>
      </section>

      <section class="mcp-panel">
        <div class="panel-title"><div><span>Recent MCP Jobs</span><h2>最近任务记录</h2></div><StatusPill tone="neutral">{{ jobs.length }} 条</StatusPill></div>
        <div v-if="jobs.length" class="job-list">
          <article v-for="job in jobs" :key="job.job_id"><div><strong>{{ job.tool_name || 'MCP 工具任务' }}</strong><code>{{ job.job_id }}</code></div><StatusPill :tone="statusTone(job.status)">{{ statusLabel[job.status] || job.status }}</StatusPill><p>结果：{{ job.result_ref || '等待生成' }} · 阶段：{{ job.current_stage || '等待执行' }}</p></article>
        </div>
        <div v-else class="empty-jobs"><AppIcon name="clock" :size="26" /><strong>还没有 MCP 任务</strong><p>在 Agent 中枢要求执行动态优选、解耦辨识或闭环寻优后，记录会出现在这里。</p></div>
      </section>
    </div>

    <footer class="safety-note"><AppIcon name="shield" :size="19" /><div><strong>安全边界已固定</strong><p>MCP 仅执行离线建模与证据查询，不提供 PLC/DCS 下发工具；所有计算均受真实数据、测试集隔离、幂等和质量门禁约束。</p></div></footer>
  </section>
</template>

<style scoped>
.mcp-page{display:grid;gap:18px}.mcp-hero{display:flex;justify-content:space-between;gap:28px;padding:30px;border:1px solid #cfe5df;border-radius:20px;background:linear-gradient(135deg,#eefaf6 0%,#f7fbff 55%,#e8f1ff 100%)}.mcp-hero.offline{border-color:#f0d6d1;background:linear-gradient(135deg,#fff7f5,#f7faff)}.eyebrow,.panel-title span{color:#12836a;font-size:10px;font-weight:800;letter-spacing:.15em;text-transform:uppercase}.mcp-hero h1{margin:7px 0 8px;color:#102b4c;font-size:31px}.mcp-hero-copy>p{max-width:720px;color:#5e7188;font-size:13px;line-height:1.65}.server-address{display:flex;align-items:center;gap:8px;margin-top:17px;color:#176b5b}.server-address code{padding:6px 9px;border-radius:8px;background:rgba(255,255,255,.75);font-size:11px}.connection-card{display:grid;grid-template-columns:auto minmax(180px,1fr);gap:2px 11px;align-items:center;min-width:300px;padding:18px;border:1px solid rgba(255,255,255,.9);border-radius:15px;background:rgba(255,255,255,.78);box-shadow:0 12px 30px rgba(32,73,104,.09)}.connection-light{width:11px;height:11px;border-radius:50%;background:#20b987;box-shadow:0 0 0 5px rgba(32,185,135,.13)}.offline .connection-light{background:#e05b4b;box-shadow:0 0 0 5px rgba(224,91,75,.12)}.connection-card small,.connection-card p{display:block;color:#738399;font-size:10px}.connection-card strong{display:block;margin:3px 0;color:#0c775e;font-size:17px}.offline .connection-card strong{color:#b33b31}.connection-card button{grid-column:2;margin-top:9px;padding:8px 11px;border:1px solid #cbd9e6;border-radius:8px;color:#31516f;background:#fff;font-weight:700;cursor:pointer}.mcp-error{display:flex;gap:8px;align-items:center;padding:12px 15px;border-radius:10px;color:#a7352b;background:#fff0ed}.mcp-metrics{display:grid;grid-template-columns:repeat(4,1fr);gap:13px}.mcp-metrics article{padding:17px;border:1px solid #dfe8f1;border-radius:14px;background:#fff}.mcp-metrics span,.mcp-metrics small{display:block;color:#7a899c;font-size:10px}.mcp-metrics strong{display:block;margin:7px 0;color:#173d66;font-size:22px}.mcp-panel{padding:20px;border:1px solid #dfe7ef;border-radius:16px;background:#fff}.panel-title{display:flex;justify-content:space-between;gap:14px;align-items:flex-start;margin-bottom:15px}.panel-title h2{margin-top:5px;color:#183a5f;font-size:16px}.compute-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:13px}.compute-grid>article{display:grid;grid-template-columns:auto 1fr;gap:12px;padding:17px;border:1px solid #dce7f0;border-radius:13px;background:linear-gradient(150deg,#fff,#f7fbff)}.compute-grid>article>b{display:grid;place-items:center;width:34px;height:34px;border-radius:10px;color:#fff;background:#188d73}.compute-grid span,.compute-grid code{display:block}.compute-grid div>span{color:#173c63;font-size:13px;font-weight:800}.compute-grid code,.support-list code,.job-list code{margin-top:5px;color:#597087;font-size:9px;word-break:break-all}.compute-grid p,.support-list p{margin-top:8px;color:#64758a;font-size:11px;line-height:1.55}.compute-grid footer{grid-column:1/-1;display:flex;gap:7px;padding-top:10px;border-top:1px solid #e7edf3}.compute-grid footer span{padding:4px 7px;border-radius:999px;color:#16745f;background:#e8f8f2;font-size:9px}.mcp-flow{display:flex;align-items:center;justify-content:center;gap:12px;padding:17px;border-radius:14px;color:#6c7f93;background:#102d4d}.mcp-flow>div{min-width:155px;padding:11px 14px;border:1px solid #32516f;border-radius:10px;background:#173958}.mcp-flow>div.active{border-color:#36d2a7;box-shadow:0 0 0 2px rgba(54,210,167,.14)}.mcp-flow strong,.mcp-flow small{display:block}.mcp-flow strong{color:#fff;font-size:12px}.mcp-flow small{margin-top:4px;color:#9db2c7;font-size:9px}.mcp-columns{display:grid;grid-template-columns:1.2fr .8fr;gap:14px}.support-list,.job-list{display:grid;gap:8px}.support-list article{display:grid;grid-template-columns:auto 1fr auto;gap:11px;align-items:start;padding:12px;border:1px solid #e5ebf1;border-radius:11px}.support-list article>span{display:grid;place-items:center;width:32px;height:32px;border-radius:9px;color:#26765f;background:#eaf7f2}.support-list strong{color:#284763;font-size:12px}.support-list article>b{padding:4px 7px;border-radius:999px;color:#53697e;background:#eef3f7;font-size:8px}.job-list article{display:grid;grid-template-columns:1fr auto;gap:7px;padding:12px;border:1px solid #e4eaf0;border-radius:10px}.job-list strong{display:block;color:#294864;font-size:11px}.job-list p{grid-column:1/-1;color:#78889a;font-size:9px}.empty-jobs{display:grid;place-items:center;padding:38px 20px;color:#7c8da0;text-align:center}.empty-jobs strong{margin-top:9px;color:#405970}.empty-jobs p{max-width:360px;margin-top:6px;font-size:11px;line-height:1.55}.safety-note{display:flex;gap:11px;padding:16px 18px;border-left:4px solid #24a27f;border-radius:0 12px 12px 0;color:#345d55;background:#edf9f5}.safety-note p{margin-top:4px;font-size:11px;line-height:1.55}@media(max-width:1100px){.mcp-hero{display:grid}.connection-card{min-width:0}.compute-grid,.mcp-metrics{grid-template-columns:repeat(2,1fr)}.mcp-columns{grid-template-columns:1fr}.mcp-flow{flex-wrap:wrap}}@media(max-width:640px){.mcp-metrics,.compute-grid{grid-template-columns:1fr}.mcp-flow{align-items:stretch;flex-direction:column}.mcp-flow>div{min-width:0}.mcp-flow>.app-icon{transform:rotate(90deg)}}
.support-list strong{display:block}
</style>
