import { cpSync, mkdirSync, rmSync, readFileSync, writeFileSync, readdirSync, statSync, existsSync } from 'node:fs'
import { join, relative } from 'node:path'

const root = new URL('..', import.meta.url).pathname
const srcDir = join(root, 'src')
const assetsDir = join(root, 'assets')
const docsDir = join(root, 'docs')

rmSync(docsDir, { recursive: true, force: true })
mkdirSync(docsDir, { recursive: true })
cpSync(srcDir, docsDir, { recursive: true })
cpSync(assetsDir, join(docsDir, 'assets'), { recursive: true })

// Ensure SPA-ish 404 fallback for GitHub Pages project site
cpSync(join(docsDir, 'index.html'), join(docsDir, '404.html'))
writeFileSync(join(docsDir, '.nojekyll'), '')

function walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    if (statSync(p).isDirectory()) walk(p)
    else if (name.endsWith('.html')) {
      let t = readFileSync(p, 'utf8')
      const next = t.replaceAll('../../assets/', '../assets/')
      if (next !== t) writeFileSync(p, next)
    }
  }
}
walk(docsDir)

console.log('Built docs/ from src/ + assets/')
