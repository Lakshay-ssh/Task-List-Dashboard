const http = require('http');
const fs = require('fs');
const path = require('path');

const root = __dirname;
const types = { '.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css', '.svg': 'image/svg+xml' };

http.createServer((req, res) => {
  const urlPath = decodeURIComponent(req.url.split('?')[0]);
  if (req.method === 'POST' && urlPath === '/save') {
    const name = new URL(req.url, 'http://x').searchParams.get('name') || 'out.html';
    if (!/^[\w.-]+\.html$/.test(name)) { res.writeHead(400); res.end('bad name'); return; }
    let body = [];
    req.on('data', c => body.push(c));
    req.on('end', () => {
      fs.writeFileSync(path.join(root, name), Buffer.concat(body));
      res.writeHead(200); res.end('saved');
    });
    return;
  }
  let file = path.join(root, urlPath === '/' ? 'artifact-exporter.html' : urlPath);
  if (!file.startsWith(root)) { res.writeHead(403); res.end(); return; }
  fs.readFile(file, (err, data) => {
    if (err) { res.writeHead(404); res.end('not found'); return; }
    res.writeHead(200, { 'Content-Type': types[path.extname(file)] || 'application/octet-stream' });
    res.end(data);
  });
}).listen(8901, () => console.log('serving ' + root + ' on http://localhost:8901'));
