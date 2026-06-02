const fs = require('fs');
const path = require('path');
const http = require('http');
const { chromium } = require('playwright');
const dir = 'D:/ziliao/dev/diagrams';
const mermaidDist = 'C:/Users/mej/AppData/Local/Temp/mermaid-renderer/node_modules/mermaid/dist';
const files = fs.readdirSync(dir).filter(f => /^diagram_\d+\.mmd$/.test(f)).sort();
let currentCode = '';
function sendFile(res, file, type='text/javascript; charset=utf-8') {
  if (!fs.existsSync(file)) { res.writeHead(404); res.end('not found ' + file); return; }
  res.writeHead(200, {'Content-Type': type}); fs.createReadStream(file).pipe(res);
}
const server = http.createServer((req, res) => {
  const url = decodeURIComponent(req.url.split('?')[0]);
  if (url.startsWith('/mermaid/')) {
    const rel = url.slice('/mermaid/'.length);
    const file = path.normalize(path.join(mermaidDist, rel));
    if (!file.startsWith(path.normalize(mermaidDist))) { res.writeHead(403); res.end('forbidden'); return; }
    const type = file.endsWith('.css') ? 'text/css' : 'text/javascript; charset=utf-8';
    sendFile(res, file, type); return;
  }
  if (url === '/' || url === '/render') {
    const html = `<!doctype html><html><head><meta charset="utf-8"><style>
      body{ margin:0; padding:36px; background:white; font-family: SimSun, 'Microsoft YaHei', 'Times New Roman', serif; }
      #wrap{ display:inline-block; background:white; }
      svg{ background:white; font-family: SimSun, 'Microsoft YaHei', 'Times New Roman', serif !important; }
      .node rect,.node polygon,.node circle,.node ellipse{ fill:#fff !important; stroke:#111 !important; stroke-width:1.2px !important; }
      .edgePath .path{ stroke:#111 !important; stroke-width:1.2px !important; }
      .edgeLabel{ background:#fff !important; color:#111 !important; }
      .cluster rect{ fill:#fff !important; stroke:#111 !important; stroke-width:1.2px !important; }
      text{ fill:#111 !important; font-size:16px !important; }
    </style></head><body><div id="wrap"><div id="diagram"></div></div><script type="module">
      import mermaid from '/mermaid/mermaid.esm.min.mjs';
      mermaid.initialize({ startOnLoad:false, securityLevel:'loose', theme:'base', themeVariables:{ fontFamily:"SimSun, Microsoft YaHei, Times New Roman, serif", primaryColor:'#fff', primaryTextColor:'#111', primaryBorderColor:'#111', lineColor:'#111', secondaryColor:'#fff', tertiaryColor:'#fff', edgeLabelBackground:'#fff' }, flowchart:{ curve:'linear', nodeSpacing:50, rankSpacing:60, padding:20 } });
      const code = ${JSON.stringify(currentCode)};
      try {
        const { svg } = await mermaid.render('mmd_' + Math.random().toString(36).slice(2), code);
        document.getElementById('diagram').innerHTML = svg;
        window.__done = true;
      } catch (e) {
        document.body.innerHTML = '<pre style="color:red">' + e.stack + '</pre>';
        window.__error = e.message;
      }
    </script></body></html>`;
    res.writeHead(200, {'Content-Type': 'text/html; charset=utf-8'}); res.end(html); return;
  }
  res.writeHead(404); res.end('not found ' + url);
});
function listen(port){ return new Promise(resolve => server.listen(port, '127.0.0.1', () => resolve(port))); }
(async () => {
  const port = await listen(8765);
  const browser = await chromium.launch({ headless: true, executablePath: 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', args: ['--no-sandbox'] });
  const page = await browser.newPage({ viewport: { width: 2600, height: 1900 }, deviceScaleFactor: 4 });
  page.on('pageerror', e => console.error('pageerror', e.message));
  page.on('requestfailed', r => console.error('requestfailed', r.url(), r.failure()?.errorText));
  for (const file of files) {
    currentCode = fs.readFileSync(path.join(dir, file), 'utf8');
    await page.goto(`http://127.0.0.1:${port}/render?f=${encodeURIComponent(file)}`, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction('window.__done || window.__error', null, { timeout: 60000 });
    const err = await page.evaluate('window.__error');
    if (err) throw new Error(file + ': ' + err);
    const el = await page.$('#wrap');
    const out = path.join(dir, file.replace('.mmd','.png'));
    await el.screenshot({ path: out, omitBackground: false });
    console.log('rendered', out);
  }
  await browser.close(); server.close();
})();
