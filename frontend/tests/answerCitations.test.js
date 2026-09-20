import test from 'node:test'
import assert from 'node:assert/strict'
import { answerParts, readableAnswer, streamedAnswer } from '../src/utils/answerCitations.js'
const run = 'original_run'
const sources = [{ id:`run:${run}:cleaning`,run_id:run, facts:{period:3600}}, {id:'knowledge:doc:chunk', document_id:'doc',chunk_id:'chunk'}, {id:'skill:exec:clean',run_id:run,skill_run_id:'exec',skill_id:'clean'}]
test('allowlisted run, knowledge and skill use readable labels with original source objects',()=>{
 const parts=answerParts(sources.map(s=>`[${s.id}]`).join(' '),sources,run)
 assert.deepEqual(parts.filter(p=>p.type==='source').map(p=>p.text),['〔清洗记录〕','〔知识依据〕','〔技能记录〕'])
 assert.equal(parts[0].source,sources[0])
})
test('switching run cannot rebind a message or trust an unregistered citation',()=>{
 assert.equal(answerParts(`[run:${run}:cleaning]`,sources,'other')[0].type,'unverified')
 assert.equal(answerParts('[run:forged:cleaning]',sources,run)[0].type,'unverified')
 assert.equal(readableAnswer(`[run:${run}:cleaning]`,[],run),'〔来源不可核验〕')
})
test('duplicates deduplicate labels without modifying raw text',()=>{
 const raw=`one [run:${run}:cleaning] two [run:${run}:cleaning]`
 assert.equal(answerParts(raw,sources,run).filter(p=>p.type==='source').length,1)
 assert.ok(raw.includes('original_run'))
})
test('every streamed prefix hides partial internal ids; interruption is explicit',()=>{
 const marker=`[run:${run}:cleaning]`
 for(let i=1;i<marker.length;i++) assert.ok(!readableAnswer('text '+marker.slice(0,i),sources,run,true).includes('original'))
 assert.equal(readableAnswer('[run:original',sources,run,false),'〔来源信息不完整〕')
 assert.equal(readableAnswer(marker,sources,run,false),'〔清洗记录〕')
})
test('buffer has a boundary and preserves following prose',()=>{
 const result=readableAnswer('[run:'+ 'x'.repeat(540)+' 后续正文',sources,run,true)
 assert.ok(result.includes('后续正文'));assert.ok(result.includes('来源信息不完整'))
})
test('normal brackets, quoted examples and code are literal',()=>{
 for (const raw of ['[1,2] [普通内容]', '`[run:example:cleaning]`', '```txt\n[run:example:cleaning]\n```', '> [run:example:cleaning]', '“[run:example:cleaning]”']) assert.equal(readableAnswer(raw,sources,run),raw)
})
test('hostile urls and html never become executable source routes',()=>{
 const raw='<img src=x onerror=alert(1)> [run:javascript:evil] [knowledge:file://:etc]'
 const parts=answerParts(raw,sources,run)
 assert.ok(parts.every(p=>p.type!=='source'));assert.ok(parts[0].text.startsWith('<img'))
})
test('persisted messages retain their own sources and readable copy',()=>{
 const saved=JSON.parse(JSON.stringify({text:`result [run:${run}:cleaning]`,runId:run,answerSources:sources}))
 assert.equal(readableAnswer(saved.text,saved.answerSources,saved.runId),'result 〔清洗记录〕')
})
test('replayed delta sequences do not duplicate output; final replacement parses independently',()=>{
 const a={sequence:1,event_type:'llm_response_delta',metadata:{delta:'hello [ru'}},b={sequence:2,event_type:'llm_response_delta',metadata:{delta:`n:${run}:cleaning]`}}
 assert.equal(readableAnswer(streamedAnswer([a,b,a,b]),sources,run),'hello 〔清洗记录〕')
 assert.equal(readableAnswer('校验回退后的回答',sources,run),'校验回退后的回答')
})
