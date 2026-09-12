import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse, compileScript, compileTemplate } from '@vue/compiler-sfc'
import { parse as parseJavaScript } from 'acorn'

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..')
const sourceRoot = path.join(root, 'src')
const files = []
const errors = []

function walk(directory) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    const target = path.join(directory, entry.name)
    if (entry.isDirectory()) walk(target)
    else if (/\.(?:js|vue)$/.test(entry.name)) files.push(target)
  }
}

walk(sourceRoot)
for (const file of files) {
  const relative = path.relative(root, file)
  const source = fs.readFileSync(file, 'utf8')
  if (/console\.log\s*\(/.test(source)) errors.push(`${relative}: 禁止提交 console.log`)
  if (/TODO\(mock\)/.test(source)) errors.push(`${relative}: 必须移除或显式标注 mock fallback`)
  try {
    if (file.endsWith('.js')) {
      parseJavaScript(source, { ecmaVersion: 'latest', sourceType: 'module' })
      continue
    }
    const id = Buffer.from(relative).toString('hex').slice(0, 12)
    const parsed = parse(source, { filename: relative })
    if (parsed.errors.length) throw parsed.errors[0]
    if (parsed.descriptor.script || parsed.descriptor.scriptSetup) compileScript(parsed.descriptor, { id })
    if (parsed.descriptor.template) {
      const compiled = compileTemplate({ id, filename: relative, source: parsed.descriptor.template.content })
      if (compiled.errors.length) throw compiled.errors[0]
    }
  } catch (error) {
    errors.push(`${relative}: ${error.message ?? error}`)
  }
}

if (errors.length) {
  process.stderr.write(`${errors.join('\n')}\n`)
  process.exit(1)
}
process.stdout.write(`Lint passed: ${files.length} JavaScript/Vue files checked.\n`)
