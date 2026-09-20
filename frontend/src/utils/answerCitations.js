const labels = { basic_data_profile: '数据概况', standardization: '字段标准化', cleaning: '清洗记录', selection: '动态段记录', modeling: '模型结果', optimization: '寻优记录', review: '评审记录', best_selection_receipt: '最佳候选依据', policy_receipt: '参数依据' }

function trustedSource(id, sources, runId) {
  const source = sources.find(item => item?.id === id)
  if (!source) return null
  const [kind, task, ...rest] = id.split(':')
  if (kind === 'run' && (task !== runId || source.run_id !== task || !rest.length)) return null
  if (kind === 'skill' && (source.run_id !== runId || source.skill_run_id !== task || source.skill_id !== rest.join(':'))) return null
  if (kind === 'knowledge' && (source.document_id !== task || source.chunk_id !== rest.join(':'))) return null
  return source
}

// Produce text and allowlisted evidence only. Never interpret model HTML or URLs.
// Code, blockquotes and quoted examples are literal text, including their markers.
export function answerParts(raw = '', sources = [], runId = null, streaming = false) {
  const parts = [], seen = new Set()
  const pushText = text => { if (text) parts.push({ type: 'text', text }) }
  const protectedText = /(```[\s\S]*?(?:```|(?![\s\S]))|`[^`\n]*(?:`|$)|^>[^\n]*|“[^”\n]*”)/gm
  function plain(text) {
    const marker = /\[(run|knowledge|skill):([^\]\n]+)\]/g
    let position = 0
    for (const match of text.matchAll(marker)) {
      pushText(text.slice(position, match.index))
      const id = `${match[1]}:${match[2]}`
      const source = trustedSource(id, sources, runId)
      if (!seen.has(id)) {
        seen.add(id)
        const stage = id.split(':').slice(2).join(':')
        parts.push(source
          ? { type: 'source', id, source, text: `〔${match[1] === 'run' ? labels[stage] || '运行证据' : match[1] === 'knowledge' ? '知识依据' : '技能记录'}〕` }
          : { type: 'unverified', text: streaming ? '〔来源待核验〕' : '〔来源不可核验〕' })
      }
      position = match.index + match[0].length
    }
    let tail = text.slice(position)
    tail = tail.replace(/\[(?:run:[^\]\n]*|knowledge:[^\]\n]*|skill:[^\]\n]*|r|ru|run|k|kn|kno|know|knowl|knowle|knowled|knowledg|knowledge|s|sk|ski|skil|skill|)(?=\n|$)/g, (token, at) => {
      if (streaming && at + token.length === tail.length && token.length <= 512) return ''
      return '〔来源信息不完整〕' + (token.length > 512 ? token.slice(512).replace(/^\S+/, '') : '')
    })
    pushText(tail)
  }
  let offset = 0
  for (const match of raw.matchAll(protectedText)) {
    plain(raw.slice(offset, match.index)); pushText(match[0]); offset = match.index + match[0].length
  }
  plain(raw.slice(offset))
  return parts
}
export function readableAnswer(raw, sources, runId, streaming = false) {
  return answerParts(raw, sources, runId, streaming).map(part => part.text).join('')
}

// Rebuild from unique durable event sequences; replays never append a delta twice.
export function streamedAnswer(events) {
  const unique = new Map()
  for (const event of events) if (event.event_type === 'llm_response_delta') unique.set(event.sequence, event)
  return [...unique.values()].sort((a, b) => a.sequence - b.sequence).map(event => event.metadata?.delta || '').join('')
}
