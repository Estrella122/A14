<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import AppIcon from './AppIcon.vue'

const props = defineProps({ open: { type: Boolean, default: false }, navItems: { type: Array, default: () => [] } })
const emit = defineEmits(['close', 'select'])
const query = ref('')
const searchInput = ref(null)
const recent = ref([])

// TODO(api): 当前命令通过页面事件复用已有操作；统一动作 API 上线后可在这里增加跨页面任务状态回传。
const actionCommands = [
  { id: 'action-simulate', label: '生成仿真数据', detail: '打开数据资产并生成阶跃测试集', icon: 'spark', path: '/scenario-data/', action: 'generate-simulation' },
  { id: 'action-optimize', label: '运行闭环寻优', detail: '打开寻优引擎并开始计算', icon: 'loop', path: '/closed-loop-optimization/', action: 'run-optimization' },
  { id: 'action-report', label: '导出分析报告', detail: '打开评审交付并下载报告', icon: 'download', path: '/report-export/', action: 'export-report' },
  { id: 'action-save-flow', label: '保存当前流水线', detail: '保存编排器中的节点与连线', icon: 'network', path: '/pipeline-builder/', action: 'save-pipeline' },
]
const commands = computed(() => [
  ...props.navItems.map((item, index) => ({ id: `nav-${item.path}`, label: item.label, detail: `跳转到 ${item.shortLabel || item.label}`, icon: item.icon, path: item.path, shortcut: index < 8 ? `⌃${index + 1}` : '' })),
  ...actionCommands,
])
const results = computed(() => {
  const normalized = query.value.trim().toLowerCase()
  const rows = normalized ? commands.value.filter((item) => `${item.label} ${item.detail}`.toLowerCase().includes(normalized)) : commands.value
  return rows.slice().sort((left, right) => recent.value.indexOf(right.id) - recent.value.indexOf(left.id))
})

function choose(command) {
  recent.value = [command.id, ...recent.value.filter((id) => id !== command.id)].slice(0, 5)
  try { window.localStorage.setItem('processpilot-command-recent', JSON.stringify(recent.value)) } catch { /* optional */ }
  emit('select', command)
}
function handleKey(event) {
  if (event.key === 'Escape') emit('close')
  if (event.key === 'Enter' && results.value[0]) choose(results.value[0])
}
watch(() => props.open, async (value) => {
  if (!value) return
  query.value = ''
  try { recent.value = JSON.parse(window.localStorage.getItem('processpilot-command-recent') || '[]') } catch { recent.value = [] }
  await nextTick()
  searchInput.value?.focus()
})
</script>

<template>
  <Teleport to="body"><Transition name="command-fade"><div v-if="open" class="command-overlay" role="presentation" @mousedown.self="emit('close')"><section class="command-palette" role="dialog" aria-modal="true" aria-label="全局命令面板" @keydown="handleKey"><div class="command-search"><AppIcon name="spark" :size="19" /><input ref="searchInput" v-model="query" type="search" placeholder="搜索页面或输入操作…" /><kbd>ESC</kbd></div><div class="command-meta"><span>{{ query ? '搜索结果' : recent.length ? '最近使用与全部命令' : '全部命令' }}</span><span><kbd>↵</kbd> 执行 · <kbd>⌘K</kbd> 打开</span></div><div class="command-results"><button v-for="command in results" :key="command.id" type="button" @click="choose(command)"><span><AppIcon :name="command.icon" :size="17" /></span><div><strong>{{ command.label }}</strong><small>{{ command.detail }}</small></div><em v-if="recent.includes(command.id)">最近</em><kbd v-if="command.shortcut">{{ command.shortcut }}</kbd><AppIcon name="arrow" :size="14" /></button><p v-if="!results.length">没有匹配的页面或操作。</p></div><footer><span>ProcessPilot Command Center</span><span>快捷键在输入框中自动停用</span></footer></section></div></Transition></Teleport>
</template>

<style scoped>
.command-overlay { position: fixed; z-index: 200; inset: 0; display: grid; place-items: start center; padding-top: min(16vh, 145px); background: rgba(4,14,27,.52); backdrop-filter: blur(5px); }.command-palette { width: min(680px, calc(100vw - 28px)); overflow: hidden; border: 1px solid rgba(126,164,207,.45); border-radius: 14px; background: #fff; box-shadow: 0 28px 80px rgba(4,14,27,.32); }.command-search { display: grid; grid-template-columns: 24px minmax(0,1fr) auto; gap: 9px; align-items: center; padding: 15px 17px; color: #2563eb; border-bottom: 1px solid #e4ebf3; }.command-search input { width: 100%; color: #172033; font-size: 16px; border: 0; outline: 0; background: transparent; }.command-search kbd, .command-meta kbd { padding: 3px 6px; color: #6b7d91; font: 9px monospace; border: 1px solid #d8e0ea; border-bottom-width: 2px; border-radius: 5px; background: #f8fafc; }.command-meta { display: flex; justify-content: space-between; gap: 10px; padding: 10px 17px 7px; color: #8a99aa; font-size: 9px; }.command-results { max-height: 430px; padding: 4px 8px 10px; overflow-y: auto; }.command-results button { display: grid; grid-template-columns: 36px minmax(0,1fr) auto auto 16px; gap: 9px; align-items: center; width: 100%; min-height: 55px; padding: 7px 10px; color: #334155; text-align: left; border: 0; border-radius: 8px; background: transparent; }.command-results button:hover, .command-results button:focus { background: #edf4ff; outline: 0; }.command-results button > span { display: grid; place-items: center; width: 34px; height: 34px; color: #2563eb; border-radius: 8px; background: #e7f0ff; }.command-results strong, .command-results small { display: block; }.command-results strong { font-size: 12px; }.command-results small { margin-top: 3px; color: #7b8b9e; font-size: 9px; }.command-results em { padding: 3px 6px; color: #0f7b5a; font-size: 8px; font-style: normal; border-radius: 10px; background: #e6f7f0; }.command-results kbd { color: #7c8da0; font: 9px monospace; }.command-results > p { padding: 35px; color: #8a99aa; text-align: center; }.command-palette footer { display: flex; justify-content: space-between; padding: 9px 16px; color: #8494a6; font: 8px monospace; border-top: 1px solid #e8edf3; background: #f8fafc; }.command-fade-enter-active,.command-fade-leave-active { transition: 160ms ease; }.command-fade-enter-from,.command-fade-leave-to { opacity: 0; }.command-fade-enter-from .command-palette,.command-fade-leave-to .command-palette { transform: translateY(-10px) scale(.98); }
</style>
