const http = require('http');
const fs = require('fs');
const path = require('path');
const root = 'd:\\桌面\\软件杯\\lingshan-redesign';
const mime = { '.html': 'text/html; charset=utf-8', '.css': 'text/css; charset=utf-8', '.js': 'application/javascript', '.jpg': 'image/jpeg', '.png': 'image/png', '.svg': 'image/svg+xml', '.json': 'application/json' };

http.createServer((req, res) => {
  let urlPath = decodeURIComponent(req.url.split('?')[0]);
  if (urlPath === '/') urlPath = '/pages/home.html';
  fs.readFile(path.join(root, urlPath), (err, data) => {
    if (err) { res.writeHead(404); res.end('404: ' + urlPath); return; }
    const ext = path.extname(urlPath).toLowerCase();
    res.writeHead(200, { 'Content-Type': mime[ext] || 'application/octet-stream' });
    res.end(data);
  });
}).listen(8899, () => console.log('http://localhost:8899'));
