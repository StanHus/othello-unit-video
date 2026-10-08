#!/usr/bin/env node
// Minimal static server WITH HTTP Range support, for running the player locally.
// Python's http.server answers Range requests with the whole file, so <video> and <audio> seeking resets to 0
// under it. Usage: node tools/player/serve.js [port] [root]   (defaults: 8780 and the current directory)
const http = require('http'), fs = require('fs'), path = require('path');
const root = path.resolve(process.argv[3] || '.');
const port = Number(process.argv[2] || 8780);
const types = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript', '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
  '.mp4': 'video/mp4', '.webm': 'video/webm', '.vtt': 'text/vtt; charset=utf-8',
  '.m4a': 'audio/mp4', '.mp3': 'audio/mpeg', '.wav': 'audio/wav', '.md': 'text/markdown; charset=utf-8' };
http.createServer((req, res) => {
  let p;
  try { p = decodeURIComponent(new URL(req.url, 'http://x').pathname); } catch (e) { res.writeHead(400); return res.end('bad request'); }
  if (p.endsWith('/')) p += 'index.html';
  const file = path.join(root, p);
  if ((file !== root && !file.startsWith(root + path.sep)) || !fs.existsSync(file) || fs.statSync(file).isDirectory()) { res.writeHead(404); return res.end('not found'); }
  const size = fs.statSync(file).size, type = types[path.extname(file).toLowerCase()] || 'application/octet-stream';
  const m = /^bytes=(\d*)-(\d*)$/.exec(req.headers.range || '');
  if (m && (m[1] || m[2])) {
    const s = m[1] ? Number(m[1]) : Math.max(0, size - Number(m[2])), e = m[1] && m[2] ? Math.min(Number(m[2]), size - 1) : size - 1;
    if (s >= size || s > e) { res.writeHead(416, { 'Content-Range': `bytes */${size}` }); return res.end(); }
    res.writeHead(206, { 'Content-Type': type, 'Accept-Ranges': 'bytes', 'Content-Range': `bytes ${s}-${e}/${size}`, 'Content-Length': e - s + 1 });
    return fs.createReadStream(file, { start: s, end: e }).pipe(res);
  }
  res.writeHead(200, { 'Content-Type': type, 'Accept-Ranges': 'bytes', 'Content-Length': size }); fs.createReadStream(file).pipe(res);
}).listen(port, '127.0.0.1', () => console.log(`serving ${root} on http://127.0.0.1:${port}/`));
