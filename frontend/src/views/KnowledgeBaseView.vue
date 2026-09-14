<script setup>
import { computed, onMounted, ref } from 'vue'
import { getKnowledgeSummary, searchKnowledge, submitRoutingFeedback } from '../api/knowledge'

const props = defineProps({ project: { type: Object, required: true } })
const emit = defineEmits(['notify'])
const summary = ref(null)
const query = ref('')
const loading = ref(false)
const error = ref('')
const result = ref(null)
const activeScene = computed(() => props.project?.scenarioId || '')

async function loadSummary() {
  try { summary.value = await getKnowledgeSummary() } catch (cause) { error.value = cause.message }
}

async function search() {
  if (!query.value.trim()) return
  loading.value = true
  error.value = ''
  try { result.value = await searchKnowledge(query.value.trim(), activeScene.value) }
  catch (cause) { error.value = cause.message }
  finally { loading.value = false }
}

async function feedback(outcome) {
  const predicted = result.value?.skill_suggestions?.map((item) => item.skill_id) ?? []
  try {
    await submitRoutingFeedback({ query: query.value, scene_id: activeScene.value, predicted_skill_ids: predicted, corrected_skill_ids: [], outcome })
    emit('notify', { tone: 'success', title: '路由反馈已记录', message: outcome === 'accepted' ? '本次 Skill 推荐已标记为正确。' : '本次推荐已进入人工复核队列。' })
    await loadSummary()
  } catch (cause) { error.value = cause.message }
}

onMounted(loadSummary)
</script>

<template>
  <section class="knowledge-page">
    <header class="knowledge-hero">
      <div><span class="eyebrow">KNOWLEDGE GOVERNANCE</span><h1>工业知识库</h1><p>把场景、变量与 Skill 边界沉淀为可审核证据，为 Agent 路由提供受控加权。</p></div>
      <span class="mode-badge">结构化词法检索 v1</span>
    </header>

    <p v-if="error" class="error-banner">{{ error }}</p>
    <div class="metric-grid" v-if="summary">
      <article><span>已审核文档</span><strong>{{ summary.documents.approved }}</strong><small>{{ summary.documents.draft }} 份草稿待审核</small></article>
      <article><span>知识实体</span><strong>{{ summary.entities }}</strong><small>{{ summary.chunks }} 个可检索片段</small></article>
      <article><span>Skill 覆盖</span><strong>{{ summary.skill_coverage.covered }}/{{ summary.skill_coverage.total }}</strong><small>{{ summary.skill_coverage.missing.length ? '仍有缺口' : '全部执行契约已覆盖' }}</small></article>
      <article><span>人工反馈</span><strong>{{ summary.feedback.total }}</strong><small>{{ summary.feedback.corrected }} 条纠错记录</small></article>
    </div>

    <div class="scene-grid" v-if="summary">
      <article v-for="scene in summary.scene_coverage" :key="scene.id" :class="{ active: scene.id === activeScene }">
        <span>{{ scene.id === activeScene ? '当前场景' : '正式场景' }}</span><strong>{{ scene.name }}</strong><small>{{ scene.entity_count }} 个已审核实体</small>
      </article>
    </div>

    <section class="search-panel">
      <div><h2>检索与路由验证</h2><p>输入工程问题，查看命中的实体、Skill 规则和来源证据。</p></div>
      <form @submit.prevent="search"><input v-model="query" aria-label="知识库问题" placeholder="例如：提取脱丁烷塔高信噪比动态段" /><button :disabled="loading || !query.trim()">{{ loading ? '检索中…' : '检索' }}</button></form>
    </section>

    <template v-if="result">
      <div class="result-toolbar"><span>场景约束：{{ activeScene }}</span><span>来源：{{ result.provenance.length }} 份</span><div><button @click="feedback('accepted')">推荐正确</button><button class="ghost" @click="feedback('rejected')">需要复核</button></div></div>
      <div class="result-columns">
        <section><h3>推荐 Skill</h3><p v-if="!result.skill_suggestions.length" class="empty">没有高置信度推荐，Agent 将沿用确定性路由。</p><article v-for="item in result.skill_suggestions" :key="item.rule_id"><div><strong>{{ item.skill_id }}</strong><b>{{ Math.round(item.score * 100) }}%</b></div><p>{{ item.rationale }}</p><small>命中：{{ item.matched_terms.join('、') }}</small></article></section>
        <section><h3>知识实体</h3><p v-if="!result.entities.length" class="empty">未命中场景实体。</p><article v-for="item in result.entities" :key="item.entity_id"><div><strong>{{ item.name }}</strong><b>{{ item.entity_type }}</b></div><small>{{ item.scene_id || '通用' }} · 别名 {{ item.matched_alias }}</small></article></section>
        <section><h3>来源片段</h3><p v-if="!result.documents.length" class="empty">未命中文档片段。</p><article v-for="item in result.documents" :key="item.chunk_id"><strong>{{ item.title }}</strong><p>{{ item.excerpt }}</p><small>{{ item.source_type }} · {{ item.document_id }}</small></article></section>
      </div>
    </template>

    <footer class="governance-note"><strong>安全边界</strong><span>只有“已审核”知识会参与路由；知识推荐不能绕过否定意图、数据质量门禁、测试集隔离和投运审批。向量字段已预留，待积累真实问句后再启用 embedding。</span></footer>
  </section>
</template>

<style scoped>
.knowledge-page{display:grid;gap:20px}.knowledge-hero{display:flex;justify-content:space-between;align-items:flex-start;padding:28px;border:1px solid #dce5ef;border-radius:20px;background:linear-gradient(135deg,#f8fbff,#eef8f5)}.eyebrow{font-size:11px;letter-spacing:.16em;color:#16866d;font-weight:800}.knowledge-hero h1{font-size:30px;margin:7px 0}.knowledge-hero p,.search-panel p{margin:0;color:#65758b}.mode-badge{padding:8px 12px;border-radius:999px;background:#dff6ef;color:#08755d;font-size:12px;font-weight:700}.error-banner{padding:12px 16px;background:#fff0f0;color:#b42318;border-radius:10px}.metric-grid,.scene-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:14px}.metric-grid article,.scene-grid article,.result-columns>section{padding:18px;border:1px solid #e1e8f0;border-radius:16px;background:#fff}.metric-grid span,.metric-grid small,.scene-grid span,.scene-grid small{display:block;color:#77869a;font-size:12px}.metric-grid strong{display:block;font-size:28px;margin:7px 0;color:#173b67}.scene-grid{grid-template-columns:repeat(3,1fr)}.scene-grid article.active{border-color:#1da987;box-shadow:0 0 0 2px #d9f6ed}.scene-grid strong{display:block;margin:8px 0}.search-panel{display:grid;grid-template-columns:1fr minmax(420px,1.25fr);align-items:center;gap:24px;padding:22px;border-radius:16px;background:#132f52;color:#fff}.search-panel h2{margin:0 0 6px}.search-panel p{color:#b9c7d9}.search-panel form{display:flex;gap:9px}.search-panel input{flex:1;min-width:0;padding:12px 14px;border:0;border-radius:10px;font:inherit}.search-panel button,.result-toolbar button{border:0;border-radius:9px;padding:10px 16px;background:#20b991;color:white;font-weight:700;cursor:pointer}.result-toolbar{display:flex;align-items:center;gap:18px;padding:0 4px;color:#65758b;font-size:13px}.result-toolbar div{margin-left:auto;display:flex;gap:8px}.result-toolbar button.ghost{background:#edf2f7;color:#41536a}.result-columns{display:grid;grid-template-columns:repeat(3,1fr);gap:14px}.result-columns h3{margin:0 0 14px}.result-columns article{padding:13px 0;border-top:1px solid #edf1f5}.result-columns article div{display:flex;justify-content:space-between;gap:10px}.result-columns b{font-size:11px;color:#10866c}.result-columns p{font-size:13px;color:#52647a;line-height:1.5}.result-columns small,.empty{color:#8795a7;font-size:12px}.governance-note{display:flex;gap:14px;padding:16px 18px;border-left:4px solid #f1aa31;background:#fff9eb;color:#655332;font-size:13px;line-height:1.5}@media(max-width:980px){.metric-grid{grid-template-columns:repeat(2,1fr)}.result-columns{grid-template-columns:1fr}.search-panel{grid-template-columns:1fr}}@media(max-width:640px){.knowledge-hero{display:grid;gap:16px}.metric-grid,.scene-grid{grid-template-columns:1fr}.search-panel form{display:grid}.result-toolbar{align-items:flex-start;flex-wrap:wrap}.result-toolbar div{margin-left:0}.governance-note{display:grid}}
</style>
