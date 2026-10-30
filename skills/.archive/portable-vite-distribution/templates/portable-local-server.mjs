// R-Tessera — self-contained local server (USB / portable build).
// Serves dist/ AND the /api/nodes data API from ONE port. Records stored as
// JSON files in data/nodes/ (inside the project — travels on the USB).
// Requires only Node.js 18+.  Usage:  node server/local-server.mjs
import { createServer } from 'node:http'
import { readFile, writeFile, readdir, unlink, mkdir } from 'node:fs/promises'
import { existsSync, statSync } from 'node:fs'
import { join, dirname, extname, normalize } from 'node:path'
import { fileURLToPath } from 'node:url'
import { buffer } from 'node:stream/consumers'

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, '..')
const DIST = join(ROOT, 'dist')
const NODES_DIR = process.env.RT_DATA_DIR
  ? join(process.env.RT_DATA_DIR, 'nodes')
  : join(ROOT, 'data', 'nodes')
const PORT = Number(process.env.PORT || 4173)
const HOST = process.env.HOST || '0.0.0.0'

await mkdir(NODES_DIR, { recursive: true })

const fileFor = (id) => join(NODES_DIR, `${id}.json`)

async function listNodes() {
  const files = (await readdir(NODES_DIR)).filter((f) => f.endsWith('.json'))
  const out = []
  for (const f of files) {
    try {
      const obj = JSON.parse(await readFile(join(NODES_DIR, f), 'utf8'))
      if (obj && obj.id) out.push(obj)
    } catch { /* skip unreadable */ }
  }
  return out
}

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'text/javascript; charset=utf-8',
  '.mjs': 'text/javascript; charset=utf-8',
  '.css': 'text/css; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.jpg': 'image/jpeg',
  '.gif': 'image/gif',
  '.ico': 'image/x-icon',
  '.glb': 'model/gltf-binary',
  '.gltf': 'model/gltf+json',
  '.woff2': 'font/woff2',
}
const contentType = (p) => MIME[extname(p).toLowerCase()] || 'application/octet-stream'

async function serveStatic(req, res) {
  let urlPath = decodeURIComponent(new URL(req.url, `http://${req.headers.host}`).pathname)
  if (urlPath === '/') urlPath = '/index.html'
  const safe = normalize(join(DIST, urlPath)).replace(/^(\.\.[/\\])+/, '')
  if (!safe.startsWith(DIST)) { res.writeHead(403); return res.end('Forbidden') }
  if (!existsSync(safe) || !statSync(safe).isFile()) {
    const index = join(DIST, 'index.html')
    if (existsSync(index)) {
      res.writeHead(200, { 'Content-Type': 'text/html; charset=utf-8' })
      return res.end(await readFile(index))
    }
    res.writeHead(404); return res.end('Not found')
  }
  res.writeHead(200, { 'Content-Type': contentType(safe) })
  return res.end(await readFile(safe))
}

const server = createServer(async (req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`)
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,PUT,DELETE,OPTIONS')
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type')
  if (req.method === 'OPTIONS') { res.writeHead(204); return res.end() }

  const send = (code, data) => {
    res.writeHead(code, { 'Content-Type': 'application/json' })
    res.end(JSON.stringify(data))
  }

  if (url.pathname === '/api/nodes' || url.pathname.startsWith('/api/nodes/')) {
    try {
      if (req.method === 'GET' && url.pathname === '/api/nodes')
        return send(200, await listNodes())
      const m = url.pathname.match(/^\/api\/nodes\/(.+)$/)
      if (req.method === 'GET' && m) {
        const p = fileFor(decodeURIComponent(m[1]))
        if (!existsSync(p)) return send(404, { error: 'not found' })
        return send(200, JSON.parse(await readFile(p, 'utf8')))
      }
      if (req.method === 'POST' && url.pathname === '/api/nodes') {
        const data = JSON.parse((await buffer(req)).toString('utf8') || '{}')
        if (!data.id || !data.name) return send(400, { error: 'id and name required' })
        const p = fileFor(data.id)
        if (existsSync(p)) return send(409, { error: 'node id already exists' })
        await writeFile(p, JSON.stringify(data, null, 2), 'utf8')
        return send(201, { ok: true, id: data.id })
      }
      if (req.method === 'PUT' && m) {
        const data = JSON.parse((await buffer(req)).toString('utf8') || '{}')
        const p = fileFor(decodeURIComponent(m[1]))
        if (!existsSync(p)) return send(404, { error: 'not found' })
        await writeFile(p, JSON.stringify(data, null, 2), 'utf8')
        return send(200, { ok: true, id: decodeURIComponent(m[1]) })
      }
      if (req.method === 'DELETE' && m) {
        const p = fileFor(decodeURIComponent(m[1]))
        if (!existsSync(p)) return send(404, { error: 'not found' })
        await unlink(p)
        return send(200, { ok: true, id: decodeURIComponent(m[1]) })
      }
      return send(404, { error: 'unknown route' })
    } catch (e) {
      return send(500, { error: String((e && e.message) || e) })
    }
  }
  return serveStatic(req, res)
})

server.listen(PORT, HOST, () => {
  const shown = HOST === '0.0.0.0' ? 'localhost' : HOST
  console.log(`R-Tessera running →  http://${shown}:${PORT}`)
  console.log(`Node records stored →  ${NODES_DIR}`)
})
