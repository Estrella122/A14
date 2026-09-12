<script setup>
import { computed, ref } from 'vue'
import AppIcon from './AppIcon.vue'
import StatusPill from './StatusPill.vue'
import { executionStatus } from '../utils/executionStatus'

const props = defineProps({
  catalog: { type: Object, default: null },
  executions: { type: Array, default: () => [] },
  loading: Boolean,
  error: { type: String, default: '' },
})

const query = ref('')
const activeCategory = ref('all')
const executionMap = computed(() => Object.fromEntries(props.executions.map((item) => [item.skill_id, item])))
const visibleSkills = computed(() => {
  const text = query.value.trim().toLowerCase()
  return (props.catalog?.skills ?? []).filter((skill) => {
    const categoryMatch = activeCategory.value === 'all' || skill.category === activeCategory.value
    const textMatch = !text || `${skill.name} ${skill.id} ${skill.description}`.toLowerCase().includes(text)
    return categoryMatch && textMatch
  })
})
const activeCount = computed(() => props.executions.filter((item) => ['success', 'partial'].includes(item.status)).length)
function activityText(item) {
  if (['success', 'partial', 'blocked', 'failed', 'skipped', 'unavailable'].includes(item?.status)) return executionStatus(item.status).label
  return item?.activity === 'executed' ? '旧版记录，未核验' : item?.activity === 'read' ? '读取证据' : item?.activity === 'planned' ? '已规划' : '已调用'
}
function evidenceText(item) {
  return (item?.evidence ?? []).map((entry) => typeof entry === 'string' ? entry : entry?.artifact_type || entry?.source || '结构化证据').join(' · ')
}
</script>

<template>
  <section class="panel skill-center">
    <div class="skill-heading">
      <div>
        <span class="section-kicker">INDUSTRIAL SKILL RUNTIME</span>
        <h2>Agent Skill 能力中心</h2>
        <p>统一注册、按需规划、依赖补齐，并将每次执行绑定到当前流水线证据。</p>
      </div>
      <div class="skill-stats">
        <span><strong>{{ catalog?.total ?? 30 }}</strong> 已注册</span>
        <span><strong>{{ catalog?.expert_topics?.length ?? 0 }}</strong> 专家问题域</span>
        <span><strong>{{ activeCount }}</strong> 本轮调用</span>
        <StatusPill :tone="error ? 'warning' : 'success'" dot>{{ error ? '降级可用' : '运行时就绪' }}</StatusPill>
      </div>
    </div>

    <div v-if="loading" class="skill-state"><AppIcon name="loop" class="spinning" /> 正在加载 Skill 注册表…</div>
    <div v-else-if="error && !catalog" class="skill-state is-error"><AppIcon name="alert" /> {{ error }}</div>
    <template v-else>
      <div class="skill-toolbar">
        <label><AppIcon name="spark" :size="15" /><input v-model="query" placeholder="搜索 30 个工业 Skill" /></label>
        <div class="skill-filters">
          <button type="button" :class="{ active: activeCategory === 'all' }" @click="activeCategory = 'all'">全部</button>
          <button v-for="category in catalog?.categories" :key="category.id" type="button" :class="{ active: activeCategory === category.id }" @click="activeCategory = category.id">{{ category.name }}</button>
        </div>
      </div>

      <div v-if="visibleSkills.length" class="skill-grid">
        <details v-for="skill in visibleSkills" :key="skill.id" class="skill-card" :class="{ selected: ['success', 'partial'].includes(executionMap[skill.id]?.status), blocked: executionMap[skill.id]?.status === 'blocked', failed: executionMap[skill.id]?.status === 'failed' }">
          <summary>
            <span class="skill-index">{{ String((catalog?.skills ?? []).findIndex((item) => item.id === skill.id) + 1).padStart(2, '0') }}</span>
            <span class="skill-copy"><strong>{{ skill.name }}</strong><code>{{ skill.id }}</code></span>
            <span v-if="executionMap[skill.id]" class="skill-hit" :class="`is-${executionStatus(executionMap[skill.id].status).tone}`"><AppIcon :name="executionStatus(executionMap[skill.id].status).icon" :size="13" /> {{ activityText(executionMap[skill.id]) }}</span>
            <span v-else class="skill-ready">READY</span>
          </summary>
          <p>{{ skill.description }}</p>
          <dl>
            <div><dt>依赖</dt><dd>{{ skill.depends_on.join(' → ') || '无' }}</dd></div>
            <div><dt>触发词</dt><dd>{{ skill.triggers.join(' · ') }}</dd></div>
            <div v-if="executionMap[skill.id]"><dt>本轮证据</dt><dd>{{ evidenceText(executionMap[skill.id]) || '无独立证据' }}</dd></div>
            <div v-if="executionMap[skill.id]?.relevance_score"><dt>匹配度</dt><dd>{{ Math.round(executionMap[skill.id].relevance_score * 100) }}%</dd></div>
            <div v-if="executionMap[skill.id]"><dt>耗时</dt><dd>{{ executionMap[skill.id].duration_ms }} ms</dd></div>
          </dl>
        </details>
      </div>
      <div v-else class="skill-state">没有匹配的 Skill。</div>
    </template>
  </section>
</template>

<style scoped>
.skill-center { overflow: hidden; }
.skill-heading { display: flex; align-items: flex-start; justify-content: space-between; gap: 20px; padding: 22px 24px 18px; border-bottom: 1px solid #e2e8f0; background: linear-gradient(120deg, #fff 0%, #f5f9ff 72%, #eef6ff 100%); }
.skill-heading h2 { margin: 4px 0 5px; color: #0f2747; font-size: 20px; }
.skill-heading p { margin: 0; color: #64748b; font-size: 11px; }
.skill-stats { display: flex; align-items: center; gap: 10px; }
.skill-stats > span { min-width: 72px; padding: 8px 11px; border: 1px solid #dbeafe; border-radius: 9px; color: #64748b; background: #fff; font-size: 9px; text-align: center; }
.skill-stats strong { display: block; color: #1d4ed8; font-size: 18px; line-height: 1; }
.skill-toolbar { display: flex; align-items: center; gap: 14px; padding: 14px 24px; border-bottom: 1px solid #edf2f7; }
.skill-toolbar label { display: flex; align-items: center; gap: 7px; width: 230px; padding: 7px 10px; border: 1px solid #d7e1ef; border-radius: 8px; color: #94a3b8; }
.skill-toolbar input { width: 100%; border: 0; outline: 0; color: #334155; background: transparent; font: inherit; font-size: 10px; }
.skill-filters { display: flex; flex-wrap: wrap; gap: 6px; }
.skill-filters button { padding: 6px 9px; border: 1px solid #dbe3ef; border-radius: 7px; color: #64748b; background: #fff; font-size: 9px; cursor: pointer; }
.skill-filters button.active { border-color: #8ab4ff; color: #1d4ed8; background: #eff6ff; }
.skill-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 9px; max-height: 430px; padding: 14px 24px 20px; overflow: auto; }
.skill-card { border: 1px solid #e1e8f2; border-radius: 10px; background: #fff; transition: .18s ease; }
.skill-card:hover { border-color: #aac8fa; transform: translateY(-1px); box-shadow: 0 6px 16px rgba(31, 78, 145, .08); }
.skill-card.selected { border-color: #73a9ff; background: linear-gradient(135deg, #f7fbff, #eef6ff); box-shadow: inset 3px 0 #2f6fed; }
.skill-card.blocked { border-color: #f5c26b; background: #fffbeb; box-shadow: inset 3px 0 #f59e0b; }
.skill-card.failed { border-color: #fecaca; background: #fff7f7; box-shadow: inset 3px 0 #dc2626; }
.skill-card summary { display: flex; align-items: center; gap: 9px; padding: 11px; list-style: none; cursor: pointer; }
.skill-card summary::-webkit-details-marker { display: none; }
.skill-index { display: grid; place-items: center; width: 27px; height: 27px; border-radius: 8px; color: #2563eb; background: #eaf2ff; font-weight: 800; font-size: 9px; }
.skill-copy { min-width: 0; flex: 1; }
.skill-copy strong, .skill-copy code { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.skill-copy strong { color: #1e293b; font-size: 10px; }
.skill-copy code { margin-top: 2px; color: #94a3b8; font-size: 7px; }
.skill-hit, .skill-ready { flex: 0 0 auto; font-size: 7px; font-weight: 800; }
.skill-hit { display: flex; align-items: center; gap: 2px; color: #047857; }
.skill-hit.is-warning { color: #b45309; }
.skill-hit.is-danger { color: #b91c1c; }
.skill-hit.is-neutral { color: #64748b; }
.skill-ready { color: #94a3b8; }
.skill-card > p { margin: 0; padding: 0 12px 9px 47px; color: #64748b; font-size: 9px; line-height: 1.55; }
.skill-card dl { margin: 0 10px 10px; padding: 8px; border-radius: 7px; background: rgba(241, 245, 249, .8); font-size: 8px; }
.skill-card dl div { display: grid; grid-template-columns: 52px 1fr; gap: 6px; margin: 3px 0; }
.skill-card dt { color: #94a3b8; }
.skill-card dd { margin: 0; color: #334155; overflow-wrap: anywhere; }
.skill-state { display: flex; align-items: center; justify-content: center; gap: 8px; min-height: 100px; color: #64748b; font-size: 11px; }
.skill-state.is-error { color: #b45309; }
@media (max-width: 1000px) { .skill-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); } .skill-heading { flex-direction: column; } }
@media (max-width: 680px) { .skill-grid { grid-template-columns: 1fr; } .skill-toolbar { align-items: stretch; flex-direction: column; } .skill-toolbar label { width: auto; } .skill-stats { flex-wrap: wrap; } }
</style>
