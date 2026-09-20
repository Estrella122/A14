<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { answerParts, readableAnswer } from '../utils/answerCitations'
const props = defineProps({ text: { type: String, default: '' }, sources: { type: Array, default: () => [] }, runId: { type: String, default: null }, streaming: Boolean })
const parts = computed(() => answerParts(props.text, props.sources, props.runId, props.streaming))
const selected = ref(null)
const dialog = ref(null)
watch(selected, async value => { if (value) { await nextTick(); dialog.value?.focus() } })
watch(() => [props.text, props.runId], () => { selected.value = null })
const facts = computed(() => JSON.stringify(selected.value?.source?.facts ?? selected.value?.source?.relevant_excerpt ?? selected.value?.source?.artifacts ?? selected.value?.source?.provenance ?? '历史未保存事实摘要；仅可核对以下来源信息。', null, 2))
async function copy() { await navigator.clipboard.writeText(readableAnswer(props.text, props.sources, props.runId, props.streaming)) }
</script>
<template>
  <div class="citation-answer">
    <p class="citation-prose"><template v-for="(part, index) in parts" :key="index"><button v-if="part.type === 'source'" type="button" class="evidence-label" @click="selected = part">{{ part.text }}</button><span v-else :class="{ 'unverified-source': part.type === 'unverified' }">{{ part.text }}</span></template><i v-if="streaming" class="streaming-cursor"></i></p>
    <button v-if="text && !streaming" class="copy-answer" type="button" @click="copy">复制可读正文</button>
    <Teleport to="body"><div v-if="selected" class="evidence-overlay" @click.self="selected = null">
    <section ref="dialog" class="evidence-details" role="dialog" aria-modal="true" aria-label="来源详情" tabindex="-1" @keydown.esc="selected = null">
      <div class="evidence-heading"><strong>{{ selected.text }} · 来源详情</strong><button type="button" @click="selected = null">关闭来源详情</button></div>
      <dl><dt>来源类型</dt><dd>{{ selected.source.source_type || selected.id.split(':')[0] }}</dd><dt>所属数据</dt><dd>{{ selected.source.original_name || selected.source.title || '来源未记录数据名称' }}</dd><dt>原消息任务</dt><dd>{{ selected.source.run_id || '知识资料（不绑定数值任务）' }}</dd><dt>阶段 / 定位</dt><dd>{{ selected.source.stage || selected.source.json_pointer || selected.source.skill_id || selected.source.chunk_id }}</dd></dl>
      <strong>已保存的事实或产物</strong><pre>{{ facts }}</pre><details><summary>完整追溯标识</summary><code>{{ selected.id }}</code><p>{{ selected.source.json_pointer }}</p></details>
      <p>只展示本消息保存的证据，不触发训练或寻优。</p>
    </section></div></Teleport>
  </div>
</template>
<style scoped>
.citation-answer{min-width:0;max-width:100%}.citation-answer .citation-prose{font-size:14px;white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.85}.evidence-label{display:inline-block;white-space:nowrap;color:#246a53;background:#edf6f0;border:1px solid #c6dccd;border-radius:5px;margin:0 3px;padding:1px 5px;cursor:pointer;font:inherit;font-size:12px}.unverified-source{color:#846537;font-size:12px}.copy-answer{border:0;background:none;color:#66766d;font-size:11px;cursor:pointer}.evidence-overlay{position:fixed;inset:0;z-index:1000;background:#13261d66;display:flex;align-items:center;justify-content:center;padding:24px}.evidence-details{width:720px;max-height:85vh;overflow:auto;border:1px solid #c6dccd;background:#f8fbf9;padding:16px;border-radius:10px;margin:12px 0;max-width:100%;overflow-wrap:anywhere}.evidence-heading{display:flex;justify-content:space-between;gap:12px}.evidence-heading button{white-space:nowrap;cursor:pointer}dt{font-size:12px;color:#66766d}dd{margin:3px 0 10px}pre{max-height:300px;overflow:auto;white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px}code{overflow-wrap:anywhere}
</style>
