/* Offline browser regression checks. Uses installed Chrome/Edge, no npm packages. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const http = require('node:http');
const { spawn } = require('node:child_process');

const browserPath = process.env.TEST_BROWSER || [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',
].find(p => fs.existsSync(p));
if (!browserPath) throw new Error('Set TEST_BROWSER to an installed Chrome/Edge executable.');

const profiles = [
    { id: 'novel', title: 'Story', document_type: 'novel', source_format: 'epub' },
    { id: 'paper', title: 'Study', document_type: 'paper', source_format: 'pdf' },
    { id: 'empty', title: 'Empty', document_type: 'novel', source_format: 'txt' },
    { id: 'textbook', title: 'Textbook', document_type: 'textbook', source_format: 'pdf' },
].map(p => ({ ...p, progress_percent: 0, total_chapters: p.id === 'empty' ? 0 : 1,
    chapters: p.id === 'empty' ? [] : [{ id: 'chap_0', title: 'Introduction', progress_percent: 0 }],
    structure_warnings: p.id === 'paper' ? ['Check structure <script>bad()</script>'] : [] }));
const uploads = [];
const saves = [];
const character = { name: 'Preserved', gender: 'unknown', role: 'Role', notes: 'Original note', first_person: 'I', second_person: 'you', third_person: 'they' };
const server = http.createServer(async (req, res) => {
    const url = new URL(req.url, 'http://localhost');
    let body = '';
    for await (const chunk of req) body += chunk.toString();
    const json = data => { res.setHeader('Content-Type', 'application/json'); res.end(JSON.stringify(data)); };
    if (url.pathname === '/') {
        res.setHeader('Content-Type', 'text/html; charset=utf-8');
        return res.end(fs.readFileSync(path.join(__dirname, 'web/index.html')));
    }
    if (url.pathname === '/static/app.js' || url.pathname === '/static/app.css') {
        res.setHeader('Content-Type', url.pathname.endsWith('.js') ? 'text/javascript' : 'text/css');
        return res.end(fs.readFileSync(path.join(__dirname, 'web', path.basename(url.pathname))));
    }
    if (url.pathname === '/api/settings') return json({ provider: 'free_fallback', model: 'free-fallback' });
    if (url.pathname === '/api/projects') return json(profiles);
    if (url.pathname === '/api/projects/upload') {
        uploads.push(body);
        if (body.includes('filename="broken.pdf"')) {
            res.statusCode = 400;
            return json({ detail: 'Unreadable PDF' });
        }
        return json({ project_id: 'paper', title: 'Study', document_type: 'paper', chapters_count: 1, paragraphs_count: 2 });
    }
    const match = url.pathname.match(/^\/api\/projects\/([^/]+)(.*)$/);
    if (match) {
        const project = profiles.find(p => p.id === match[1]);
        if (match[2] === '') return json(project);
        if (match[2] === '/glossary') {
            if (req.method === 'POST') { saves.push(JSON.parse(body)); return json({ message: 'Saved' }); }
            return json({ tone: project.id === 'paper' ? 'academic' : 'novel', characters: [character], terms: [], custom_instructions: 'Keep terminology.' });
        }
        if (match[2] === '/chapters/chap_0') return json({ id: 'chap_0', title: 'Introduction', paragraphs: [
            { id: 'p0', original_text: 'Introduction', translated_text: 'Giới thiệu', tag: 'h2', status: 'done' },
            { id: 'p1', original_text: 'Details', translated_text: 'Chi tiết', tag: 'h5', status: 'done' },
        ] });
        if (match[2] === '/status') return json({ is_running: false, logs: [], timestamp: 1 });
    }
    res.statusCode = 404; res.end();
});

(async () => {
    const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'translator-browser-'));
    let browser;
    let socket;
    try {
        await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
        const origin = `http://127.0.0.1:${server.address().port}`;
        browser = spawn(browserPath, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--disable-background-networking', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { stdio: ['ignore', 'ignore', 'pipe'] });
        const endpoint = await new Promise((resolve, reject) => {
            let output = '';
            const timeout = setTimeout(() => reject(new Error('Browser startup timed out')), 20000);
            browser.once('error', reject);
            browser.stderr.on('data', chunk => {
                output += chunk.toString();
                const m = output.match(/DevTools listening on (ws:\/\/[^\s]+)/);
                if (m) { clearTimeout(timeout); resolve(m[1]); }
            });
        });
        const debuggerOrigin = endpoint.replace(/^ws:/, 'http:').split('/devtools/')[0];
        const targets = await (await fetch(debuggerOrigin + '/json/list')).json();
        socket = new WebSocket(targets.find(t => t.type === 'page').webSocketDebuggerUrl);
        await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
        let nextId = 0;
        const pending = new Map();
        socket.onmessage = event => {
            const response = JSON.parse(event.data);
            if (pending.has(response.id)) {
                const { resolve, reject } = pending.get(response.id);
                pending.delete(response.id);
                response.error ? reject(new Error(JSON.stringify(response.error))) : resolve(response.result);
            }
        };
        const send = (method, params = {}) => new Promise((resolve, reject) => {
            const id = ++nextId;
            pending.set(id, { resolve, reject });
            socket.send(JSON.stringify({ id, method, params }));
        });
        const evaluate = async expression => {
            const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
            if (result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
            return result.result.value;
        };
        const wait = predicate => evaluate(`(async () => { const end=Date.now()+10000; while(!(${predicate})) { if(Date.now()>end) throw new Error('Condition timed out'); await new Promise(r=>setTimeout(r,25)); } return true; })()`);
        await send('Page.navigate', { url: origin });
        await wait("typeof app !== 'undefined' && app && app.currentProject?.id === 'novel' && app.currentChapter && !app.btnSaveGlossary.disabled");
        assert.deepEqual(await evaluate('[document.body.dataset.doctype, app.toneSelect.disabled, app.groupCharacterSettings.classList.contains("hidden")]'), ['novel', false, false]);
        assert.equal(await evaluate('app.toneSelect.querySelector("option[value=academic]").disabled'), true);
        console.log('PASS Novel tone and character controls');

        await evaluate('app.selectProject("paper")');
        await wait('app.currentChapter !== null');
        assert.deepEqual(await evaluate('[document.body.dataset.doctype, app.toneSelect.value, app.toneSelect.disabled, app.groupCharacterSettings.classList.contains("hidden")]'), ['paper', 'academic', true, true]);
        assert.equal(await evaluate('app.termsList.closest(".setting-group").classList.contains("hidden")'), false);
        assert.equal(await evaluate('app.structureWarningsList.textContent'), 'Check structure <script>bad()</script>');
        assert.equal(await evaluate('app.structureWarningsList.querySelectorAll("script").length'), 0);
        await evaluate('app.saveGlossary()');
        assert.deepEqual(saves.at(-1).characters, [character]);
        console.log('PASS Paper tone, safe warnings and preserved hidden characters');
        assert.equal(await evaluate('app.readerBody.querySelectorAll("h2").length'), 1);
        assert.equal(await evaluate('app.readerBody.querySelector("h5").textContent'), 'Chi tiết');
        console.log('PASS Reader heading deduplication and hierarchy');

        await evaluate('app.openUploadModal("novel")');
        assert.deepEqual(await evaluate('[app.uploadType, app.bookFileInput.accept, document.body.dataset.doctype]'), ['novel', '.epub,.docx,.txt,.md', 'paper']);
        await evaluate('app.handleFileUpload(new File(["test"],"wrong.pdf"))');
        assert.equal(uploads.length, 0);
        assert.equal(await evaluate('app.uploadProgressTrack.classList.contains("hidden")'), true);
        await evaluate('app.setUploadType("paper"); app.handleFileUpload(new File(["test"],"valid.PDF"))');
        await wait('!app.isUploading');
        assert.equal(uploads.length, 1);
        assert.match(uploads[0], /name="document_type"\r\n\r\npaper/);
        assert.equal(await evaluate('app.btnUploadModeNovel.disabled'), false);
        console.log('PASS Explicit upload mode, extension rejection and control restoration');
        await evaluate('app.openUploadModal("paper"); app.handleFileUpload(new File(["test"],"broken.pdf"))');
        assert.equal(await evaluate('app.isUploading'), false);
        assert.equal(await evaluate('app.uploadProgressTrack.classList.contains("hidden")'), true);
        assert.equal(await evaluate('app.btnUploadModeNovel.disabled'), false);
        assert.match(await evaluate('app.uploadStatusText.textContent'), /Unreadable PDF/);
        await evaluate('app.hideModal(app.uploadModal)');
        console.log('PASS Failed upload stops spinner and permits retry');
        await evaluate('app.selectProject("empty")');
        assert.equal(await evaluate('app.currentChapter'), null);
        assert.equal(await evaluate('app.readerBody.querySelectorAll("h2").length'), 0);
        await evaluate('app.selectProject("textbook")');
        assert.equal(await evaluate('document.body.dataset.doctype'), 'textbook');
        assert.equal(await evaluate('app.normalizeDocType({source_format:"pdf"})'), 'paper');
        console.log('PASS Empty projects, textbook separation and legacy inference');

        await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
        assert.equal(await evaluate('document.documentElement.scrollWidth <= window.innerWidth'), true);
        await evaluate('app.openUploadModal("paper")');
        assert.equal(await evaluate('document.querySelector(".app-header").inert'), true);
        await evaluate('app.hideModal(app.uploadModal)');
        assert.equal(await evaluate('document.querySelector(".app-header").inert'), false);
        console.log('PASS Mobile page width and modal inert restoration');
    } finally {
        if (socket) socket.close();
        if (browser) {
            await new Promise(resolve => { browser.once('exit', resolve); browser.kill(); if (browser.exitCode !== null) resolve(); });
        }
        server.close();
        fs.rmSync(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 });
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
