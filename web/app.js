/**
 * AI Book Translator Pro - Frontend Application Controller
 * Handles real-time SSE updates, dual-view studio, inline editing, glossary & export.
 */

class BookTranslatorApp {
    constructor() {
        this.currentProjectId = null;
        this.currentProject = null;
        this.currentChapterId = null;
        this.currentChapter = null;
        this.activeView = 'studio';
        this.isTranslating = false;
        this.eventSource = null;
        this.fontSize = 18;
        this.readerFont = 'merriweather';
        this.readerDisplayMode = 'vi-only';

        this.initElements();
        this.bindEvents();
        this.init();
    }

    initElements() {
        // Header
        this.projectSelect = document.getElementById('projectSelect');
        this.btnNewBook = document.getElementById('btnNewBook');
        this.projectTitleDisplay = document.getElementById('projectTitleDisplay');
        this.globalPercentDisplay = document.getElementById('globalPercentDisplay');
        this.globalProgressBar = document.getElementById('globalProgressBar');
        this.btnStartTranslate = document.getElementById('btnStartTranslate');
        this.btnPauseTranslate = document.getElementById('btnPauseTranslate');
        this.btnExportModal = document.getElementById('btnExportModal');
        this.btnSettingsModal = document.getElementById('btnSettingsModal');

        // Sidebar Left
        this.chapterCountBadge = document.getElementById('chapterCountBadge');
        this.chapterSearchInput = document.getElementById('chapterSearchInput');
        this.chaptersList = document.getElementById('chaptersList');

        // Center Views
        this.tabStudio = document.getElementById('tabStudio');
        this.tabReader = document.getElementById('tabReader');
        this.activeChapterTitle = document.getElementById('activeChapterTitle');
        this.btnTranslateCurrentChapter = document.getElementById('btnTranslateCurrentChapter');
        this.btnToggleRightSidebar = document.getElementById('btnToggleRightSidebar');
        this.studioView = document.getElementById('studioView');
        this.readerView = document.getElementById('readerView');
        this.studioParagraphs = document.getElementById('studioParagraphs');
        this.readerBody = document.getElementById('readerBody');

        // Reader Controls
        this.btnFontDec = document.getElementById('btnFontDec');
        this.btnFontInc = document.getElementById('btnFontInc');
        this.fontSizeDisplay = document.getElementById('fontSizeDisplay');
        this.readerDisplayModeSelect = document.getElementById('readerDisplayMode');
        this.fontToggles = document.querySelectorAll('.btn-font-toggle');

        // Sidebar Right
        this.sidebarRight = document.getElementById('sidebarRight');
        this.btnCloseRightSidebar = document.getElementById('btnCloseRightSidebar');
        this.toneSelect = document.getElementById('toneSelect');
        this.btnAutoDetectChars = document.getElementById('btnAutoDetectChars');
        this.characterList = document.getElementById('characterList');
        this.btnAddCharacter = document.getElementById('btnAddCharacter');
        this.termsList = document.getElementById('termsList');
        this.btnAddTerm = document.getElementById('btnAddTerm');
        this.customInstructions = document.getElementById('customInstructions');
        this.btnSaveGlossary = document.getElementById('btnSaveGlossary');

        // Footer & Console
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        this.footerCurrentChunk = document.getElementById('footerCurrentChunk');
        this.btnToggleLogConsole = document.getElementById('btnToggleLogConsole');
        this.logCounterBadge = document.getElementById('logCounterBadge');
        this.logConsoleDrawer = document.getElementById('logConsoleDrawer');
        this.consoleBody = document.getElementById('consoleBody');
        this.btnClearLog = document.getElementById('btnClearLog');
        this.btnCloseLog = document.getElementById('btnCloseLog');

        // Modals
        this.uploadModal = document.getElementById('uploadModal');
        this.btnCloseUploadModal = document.getElementById('btnCloseUploadModal');
        this.bookDropzone = document.getElementById('bookDropzone');
        this.bookFileInput = document.getElementById('bookFileInput');
        this.uploadProgressContainer = document.getElementById('uploadProgressContainer');
        this.uploadStatusText = document.getElementById('uploadStatusText');

        this.settingsModal = document.getElementById('settingsModal');
        this.btnCloseSettingsModal = document.getElementById('btnCloseSettingsModal');
        this.settingsProvider = document.getElementById('settingsProvider');
        this.settingsApiKey = document.getElementById('settingsApiKey');
        this.settingsModel = document.getElementById('settingsModel');
        this.settingsModelSelect = document.getElementById('settingsModelSelect');
        this.settingsBaseUrl = document.getElementById('settingsBaseUrl');
        this.settingsTemp = document.getElementById('settingsTemp');
        this.tempValueDisplay = document.getElementById('tempValueDisplay');
        this.btnSaveSettings = document.getElementById('btnSaveSettings');
        this.groupBaseUrl = document.getElementById('groupBaseUrl');
        this.groupApiKey = document.getElementById('groupApiKey');
        this.modelHelpText = document.getElementById('modelHelpText');

        this.exportModal = document.getElementById('exportModal');
        this.btnCloseExportModal = document.getElementById('btnCloseExportModal');
    }

    bindEvents() {
        // Project selection
        this.projectSelect.addEventListener('change', (e) => this.selectProject(e.target.value));
        this.btnNewBook.addEventListener('click', () => this.showModal(this.uploadModal));

        // Translation control buttons
        this.btnStartTranslate.addEventListener('click', () => this.startTranslation());
        this.btnPauseTranslate.addEventListener('click', () => this.pauseTranslation());
        this.btnTranslateCurrentChapter.addEventListener('click', () => {
            if (this.currentChapterId) {
                this.startTranslation(this.currentChapterId);
            }
        });

        // Search chapters
        this.chapterSearchInput.addEventListener('input', (e) => this.filterChapters(e.target.value));

        // View tabs
        this.tabStudio.addEventListener('click', () => this.switchView('studio'));
        this.tabReader.addEventListener('click', () => this.switchView('reader'));

        // Right sidebar toggle
        this.btnToggleRightSidebar.addEventListener('click', () => {
            this.sidebarRight.classList.toggle('collapsed');
        });
        this.btnCloseRightSidebar.addEventListener('click', () => {
            this.sidebarRight.classList.add('collapsed');
        });

        // Reader controls
        this.btnFontDec.addEventListener('click', () => this.adjustFontSize(-1));
        this.btnFontInc.addEventListener('click', () => this.adjustFontSize(1));
        this.readerDisplayModeSelect.addEventListener('change', (e) => {
            this.readerDisplayMode = e.target.value;
            this.renderReaderView();
        });
        this.fontToggles.forEach(btn => {
            btn.addEventListener('click', () => {
                this.fontToggles.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                this.readerFont = btn.dataset.font;
                this.updateReaderFontClass();
            });
        });

        // Glossary & Character controls
        this.btnAutoDetectChars.addEventListener('click', () => this.autoDetectCharacters());
        this.btnAddCharacter.addEventListener('click', () => this.addCharacterCard());
        this.btnAddTerm.addEventListener('click', () => this.addTermCard());
        this.btnSaveGlossary.addEventListener('click', () => this.saveGlossary());

        // Console drawer
        this.btnToggleLogConsole.addEventListener('click', () => {
            this.logConsoleDrawer.classList.toggle('hidden');
        });
        this.btnCloseLog.addEventListener('click', () => {
            this.logConsoleDrawer.classList.add('hidden');
        });
        this.btnClearLog.addEventListener('click', () => {
            this.consoleBody.innerHTML = '';
            this.logCounterBadge.textContent = '0';
        });

        // Modals open/close
        this.btnSettingsModal.addEventListener('click', () => this.openSettingsModal());
        this.btnCloseSettingsModal.addEventListener('click', () => this.hideModal(this.settingsModal));
        this.btnExportModal.addEventListener('click', () => this.showModal(this.exportModal));
        this.btnCloseExportModal.addEventListener('click', () => this.hideModal(this.exportModal));
        this.btnCloseUploadModal.addEventListener('click', () => this.hideModal(this.uploadModal));

        // Settings Provider Change
        this.settingsProvider.addEventListener('change', () => this.updateProviderFormVisibility());
        if (this.settingsModelSelect) {
            this.settingsModelSelect.addEventListener('change', (e) => {
                if (e.target.value === 'custom') {
                    this.settingsModel.classList.remove('hidden');
                    this.settingsModel.focus();
                } else {
                    this.settingsModel.classList.add('hidden');
                    this.settingsModel.value = e.target.value;
                }
            });
        }
        this.settingsTemp.addEventListener('input', (e) => {
            this.tempValueDisplay.textContent = e.target.value;
        });
        this.btnSaveSettings.addEventListener('click', () => this.saveSettings());

        // File Upload Dropzone
        this.bookFileInput.addEventListener('change', (e) => {
            if (e.target.files && e.target.files[0]) {
                this.handleFileUpload(e.target.files[0]);
            }
        });

        this.bookDropzone.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.bookDropzone.classList.add('dragover');
        });
        this.bookDropzone.addEventListener('dragleave', () => {
            this.bookDropzone.classList.remove('dragover');
        });
        this.bookDropzone.addEventListener('drop', (e) => {
            e.preventDefault();
            this.bookDropzone.classList.remove('dragover');
            if (e.dataTransfer.files && e.dataTransfer.files[0]) {
                this.handleFileUpload(e.dataTransfer.files[0]);
            }
        });
    }

    async init() {
        this.appendLog('info', 'Đang kết nối hệ thống...');
        await this.loadSettings();
        await this.loadProjects();
    }

    // --- LOGS & SSE ---

    appendLog(level, text) {
        const line = document.createElement('div');
        line.className = `log-line ${level}`;
        const timeStr = new Date().toLocaleTimeString('vi-VN');
        line.textContent = `[${timeStr}] ${text}`;
        this.consoleBody.appendChild(line);
        this.consoleBody.scrollTop = this.consoleBody.scrollHeight;

        const count = parseInt(this.logCounterBadge.textContent || '0') + 1;
        this.logCounterBadge.textContent = count;
    }

    connectSSE(projectId) {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }

        const url = `/api/stream/${projectId}`;
        this.eventSource = new EventSource(url);

        this.eventSource.addEventListener('status_change', (e) => {
            const data = JSON.parse(e.data);
            this.updateTranslatingStatus(data.status === 'running');
            this.statusText.textContent = data.message || (data.status === 'running' ? 'Đang dịch...' : 'Đã dừng');
        });

        this.eventSource.addEventListener('log', (e) => {
            const data = JSON.parse(e.data);
            this.appendLog(data.level || 'info', data.text);
            this.footerCurrentChunk.textContent = data.text;
        });

        this.eventSource.addEventListener('chunk_done', (e) => {
            const data = JSON.parse(e.data);
            this.handleChunkDone(data);
        });

        this.eventSource.addEventListener('chapter_done', (e) => {
            const data = JSON.parse(e.data);
            this.appendLog('success', `Đã dịch xong chương: ${data.title} (Tiến độ: ${data.progress}%)`);
            this.loadProjectDetails(this.currentProjectId, false);
        });

        this.eventSource.addEventListener('complete', (e) => {
            const data = JSON.parse(e.data);
            this.appendLog('success', data.message);
            this.updateTranslatingStatus(false);
            this.statusText.textContent = 'Đã hoàn tất toàn bộ sách!';
            this.loadProjectDetails(this.currentProjectId, false);
        });

        this.eventSource.addEventListener('error', (e) => {
            if (e.data) {
                try {
                    const data = JSON.parse(e.data);
                    this.appendLog('error', data.message);
                } catch (err) {}
            }
        });
    }

    handleChunkDone(data) {
        // Update global progress bar
        this.updateGlobalProgress(data.overall_progress);

        // If currently viewing the updated chapter, update paragraph elements in real time!
        if (this.currentChapterId === data.chapter_id) {
            for (const p of data.updated_paragraphs) {
                const pEl = document.getElementById(`para_${p.id}`);
                if (pEl) {
                    const editor = pEl.querySelector('.para-vi-editor');
                    const chip = pEl.querySelector('.para-status-chip');
                    if (editor && editor.innerText !== p.text) {
                        editor.innerText = p.text;
                        // Flash green animation
                        editor.style.transition = 'background 0.3s ease';
                        editor.style.background = 'rgba(16, 185, 129, 0.2)';
                        setTimeout(() => { editor.style.background = 'transparent'; }, 600);
                    }
                    if (chip) {
                        chip.className = 'para-status-chip chip-done';
                        chip.textContent = 'Đã dịch';
                    }
                    pEl.classList.remove('translating');
                }
            }
        }

        // Update chapter list progress badge
        const chapBadge = document.getElementById(`chap_badge_${data.chapter_id}`);
        if (chapBadge) {
            chapBadge.textContent = `${data.chapter_progress}%`;
            if (data.chapter_progress >= 100) {
                chapBadge.className = 'chapter-badge badge-done';
            } else {
                chapBadge.className = 'chapter-badge badge-progress';
            }
        }

        const miniFill = document.getElementById(`chap_fill_${data.chapter_id}`);
        if (miniFill) {
            miniFill.style.width = `${data.chapter_progress}%`;
        }
    }

    updateTranslatingStatus(running) {
        this.isTranslating = running;
        if (running) {
            this.btnStartTranslate.classList.add('hidden');
            this.btnPauseTranslate.classList.remove('hidden');
            this.statusIndicator.className = 'status-indicator busy';
        } else {
            this.btnStartTranslate.classList.remove('hidden');
            this.btnPauseTranslate.classList.add('hidden');
            this.statusIndicator.className = 'status-indicator online';
        }
    }

    // --- PROJECTS MANAGEMENT ---

    async loadProjects() {
        try {
            const res = await fetch('/api/projects');
            const projects = await res.json();

            this.projectSelect.innerHTML = '';
            if (projects.length === 0) {
                this.projectSelect.innerHTML = '<option value="">-- Chưa có sách nào, hãy tải lên --</option>';
                this.showModal(this.uploadModal);
                return;
            }

            for (const p of projects) {
                const opt = document.createElement('option');
                opt.value = p.id;
                opt.textContent = `${p.title} (${p.progress_percent}%)`;
                this.projectSelect.appendChild(opt);
            }

            // Auto-select first project
            if (projects.length > 0) {
                this.selectProject(projects[0].id);
            }
        } catch (e) {
            this.appendLog('error', `Lỗi tải danh sách dự án: ${e.message}`);
        }
    }

    async selectProject(projectId) {
        if (!projectId) return;
        this.currentProjectId = projectId;
        this.projectSelect.value = projectId;

        await this.loadProjectDetails(projectId, true);
        await this.loadGlossary(projectId);
        this.connectSSE(projectId);
    }

    async loadProjectDetails(projectId, autoSelectFirstChapter = true) {
        try {
            const res = await fetch(`/api/projects/${projectId}`);
            if (!res.ok) throw new Error('Không thể tải thông tin sách');
            const data = await res.json();
            this.currentProject = data;

            // Update UI headers
            this.projectTitleDisplay.textContent = data.title;
            this.updateGlobalProgress(data.progress_percent);
            this.chapterCountBadge.textContent = data.total_chapters;
            this.updateTranslatingStatus(data.is_translating);

            // Render chapter navigation list
            this.renderChaptersList(data.chapters);

            // Select first chapter
            if (autoSelectFirstChapter && data.chapters.length > 0) {
                this.selectChapter(data.chapters[0].id);
            }
        } catch (e) {
            this.appendLog('error', e.message);
        }
    }

    updateGlobalProgress(percent) {
        const p = Math.min(100, Math.max(0, percent || 0));
        this.globalPercentDisplay.textContent = `${p}%`;
        this.globalProgressBar.style.width = `${p}%`;
    }

    renderChaptersList(chapters) {
        this.chaptersList.innerHTML = '';
        if (!chapters || chapters.length === 0) {
            this.chaptersList.innerHTML = '<div class="empty-placeholder">Sách không có chương nào.</div>';
            return;
        }

        for (const chap of chapters) {
            const item = document.createElement('div');
            item.className = `chapter-item ${chap.id === this.currentChapterId ? 'active' : ''}`;
            item.id = `chap_item_${chap.id}`;
            item.onclick = () => this.selectChapter(chap.id);

            let badgeClass = 'badge-pending';
            if (chap.progress_percent >= 100) badgeClass = 'badge-done';
            else if (chap.progress_percent > 0) badgeClass = 'badge-progress';

            item.innerHTML = `
                <div class="chapter-title-row">
                    <span class="chapter-title" title="${chap.title}">${chap.title}</span>
                    <span id="chap_badge_${chap.id}" class="chapter-badge ${badgeClass}">${chap.progress_percent}%</span>
                </div>
                <div class="chapter-mini-bar">
                    <div id="chap_fill_${chap.id}" class="chapter-mini-fill" style="width: ${chap.progress_percent}%"></div>
                </div>
            `;
            this.chaptersList.appendChild(item);
        }
    }

    filterChapters(query) {
        const q = query.toLowerCase().trim();
        const items = this.chaptersList.querySelectorAll('.chapter-item');
        items.forEach(item => {
            const title = item.querySelector('.chapter-title').textContent.toLowerCase();
            item.style.display = title.includes(q) ? 'flex' : 'none';
        });
    }

    // --- CHAPTER DETAIL & DUAL-VIEW ---

    async selectChapter(chapterId) {
        this.currentChapterId = chapterId;

        // Highlight in left sidebar
        const allItems = this.chaptersList.querySelectorAll('.chapter-item');
        allItems.forEach(i => i.classList.remove('active'));
        const activeItem = document.getElementById(`chap_item_${chapterId}`);
        if (activeItem) activeItem.classList.add('active');

        try {
            const res = await fetch(`/api/projects/${this.currentProjectId}/chapters/${chapterId}`);
            if (!res.ok) throw new Error('Không thể tải chi tiết chương');
            const data = await res.json();
            this.currentChapter = data;

            this.activeChapterTitle.textContent = data.title;

            this.renderStudioView();
            this.renderReaderView();
        } catch (e) {
            this.appendLog('error', e.message);
        }
    }

    renderStudioView() {
        this.studioParagraphs.innerHTML = '';
        if (!this.currentChapter || !this.currentChapter.paragraphs.length) {
            this.studioParagraphs.innerHTML = '<div class="empty-placeholder">Chương này chưa có nội dung văn bản.</div>';
            return;
        }

        const frag = document.createDocumentFragment();

        for (const p of this.currentChapter.paragraphs) {
            const row = document.createElement('div');
            row.className = 'para-row';
            row.id = `para_${p.id}`;

            let chipClass = 'chip-pending';
            let chipText = 'Đang chờ';
            if (p.status === 'done') {
                chipClass = 'chip-done';
                chipText = 'Đã dịch';
            } else if (p.status === 'edited') {
                chipClass = 'chip-edited';
                chipText = 'Đã sửa tay';
            }

            row.innerHTML = `
                <div class="para-en">${this.escapeHtml(p.original_text)}</div>
                <div class="para-vi-wrapper">
                    <div class="para-vi-editor" contenteditable="true" spellcheck="false" data-para-id="${p.id}" placeholder="Đoạn văn bản tiếng Việt...">${this.escapeHtml(p.translated_text || '')}</div>
                    <div class="para-meta">
                        <span class="para-status-chip ${chipClass}">${chipText}</span>
                    </div>
                </div>
            `;

            // Inline auto-save when user finishes typing and blurs
            const editor = row.querySelector('.para-vi-editor');
            editor.addEventListener('blur', (e) => {
                const newText = e.target.innerText.trim();
                if (newText !== p.translated_text) {
                    this.saveEditedParagraph(p.id, newText, row);
                }
            });

            frag.appendChild(row);
        }

        this.studioParagraphs.appendChild(frag);
    }

    async saveEditedParagraph(paraId, newText, rowEl) {
        try {
            const res = await fetch(`/api/projects/${this.currentProjectId}/chapters/${this.currentChapterId}/paragraphs/${paraId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ translated_text: newText })
            });
            if (res.ok) {
                const chip = rowEl.querySelector('.para-status-chip');
                chip.className = 'para-status-chip chip-edited';
                chip.textContent = 'Đã sửa tay';
                this.appendLog('info', `Đã lưu đoạn văn chỉnh sửa (${paraId})`);
            }
        } catch (e) {
            this.appendLog('error', `Lỗi lưu đoạn văn: ${e.message}`);
        }
    }

    renderReaderView() {
        this.readerBody.innerHTML = '';
        if (!this.currentChapter || !this.currentChapter.paragraphs.length) {
            this.readerBody.innerHTML = '<p>Không có nội dung để hiển thị.</p>';
            return;
        }

        const titleH2 = document.createElement('h2');
        titleH2.textContent = this.currentChapter.title;
        this.readerBody.appendChild(titleH2);

        for (const p of this.currentChapter.paragraphs) {
            const trans = p.translated_text || p.original_text;

            if (this.readerDisplayMode === 'bilingual') {
                const pair = document.createElement('div');
                pair.className = 'reader-bilingual-pair';
                pair.innerHTML = `
                    <div class="reader-bilingual-en">${this.escapeHtml(p.original_text)}</div>
                    <div class="reader-bilingual-vi">${this.escapeHtml(trans)}</div>
                `;
                this.readerBody.appendChild(pair);
            } else if (this.readerDisplayMode === 'en-only') {
                const pEl = document.createElement('p');
                pEl.textContent = p.original_text;
                this.readerBody.appendChild(pEl);
            } else {
                // vi-only
                const pEl = document.createElement('p');
                pEl.textContent = trans;
                this.readerBody.appendChild(pEl);
            }
        }
    }

    switchView(viewName) {
        this.activeView = viewName;
        if (viewName === 'studio') {
            this.tabStudio.classList.add('active');
            this.tabReader.classList.remove('active');
            this.studioView.classList.remove('hidden');
            this.readerView.classList.add('hidden');
        } else {
            this.tabReader.classList.add('active');
            this.tabStudio.classList.remove('active');
            this.readerView.classList.remove('hidden');
            this.studioView.classList.add('hidden');
            this.renderReaderView();
        }
    }

    adjustFontSize(delta) {
        this.fontSize = Math.min(26, Math.max(14, this.fontSize + delta));
        this.fontSizeDisplay.textContent = `${this.fontSize}px`;
        this.readerBody.style.fontSize = `${this.fontSize}px`;
    }

    updateReaderFontClass() {
        this.readerBody.className = `reader-body font-${this.readerFont}`;
    }

    // --- TRANSLATION CONTROLS ---

    async startTranslation(chapterId = null) {
        if (!this.currentProjectId) return;

        let url = `/api/projects/${this.currentProjectId}/translate/start`;
        if (chapterId) url += `?chapter_id=${chapterId}`;

        try {
            const res = await fetch(url, { method: 'POST' });
            const data = await res.json();
            if (data.status === 'ok') {
                this.updateTranslatingStatus(true);
                this.appendLog('info', 'Đã bắt đầu tác vụ dịch...');
            } else {
                this.appendLog('info', data.message);
            }
        } catch (e) {
            this.appendLog('error', `Lỗi bắt đầu dịch: ${e.message}`);
        }
    }

    async pauseTranslation() {
        if (!this.currentProjectId) return;
        try {
            const res = await fetch(`/api/projects/${this.currentProjectId}/translate/stop`, { method: 'POST' });
            const data = await res.json();
            this.appendLog('info', data.message);
            this.updateTranslatingStatus(false);
        } catch (e) {
            this.appendLog('error', `Lỗi tạm dừng: ${e.message}`);
        }
    }

    // --- GLOSSARY & CHARACTER PRONOUNS ---

    async loadGlossary(projectId) {
        try {
            const res = await fetch(`/api/projects/${projectId}/glossary`);
            const data = await res.json();

            this.toneSelect.value = data.tone || 'novel';
            this.customInstructions.value = data.custom_instructions || '';

            this.renderCharacters(data.characters || []);
            this.renderTerms(data.terms || []);
        } catch (e) {
            this.appendLog('error', `Lỗi tải bảng thuật ngữ: ${e.message}`);
        }
    }

    renderCharacters(characters) {
        this.characterList.innerHTML = '';
        for (const c of characters) {
            this.characterList.appendChild(this.createCharacterCardElement(c));
        }
    }

    createCharacterCardElement(charData = {}) {
        const card = document.createElement('div');
        card.className = 'char-card';
        const roleText = charData.role ? (charData.notes ? `${charData.role} — ${charData.notes}` : charData.role) : (charData.notes || '');
        card.innerHTML = `
            <div class="char-card-row">
                <input type="text" class="styled-input input-sm char-input-name" placeholder="Tên NV" value="${this.escapeHtml(charData.name || '')}">
                <button class="btn-del-item" title="Xóa nhân vật" onclick="this.closest('.char-card').remove()">✕</button>
            </div>
            <div class="char-card-row">
                <input type="text" class="styled-input input-sm char-input-pronoun" placeholder="Xưng hô: tôi - cậu / anh - em" value="${this.escapeHtml(charData.first_person ? `${charData.first_person} - ${charData.second_person}` : '')}">
            </div>
            <div class="char-card-row">
                <input type="text" class="styled-input input-sm char-input-role" placeholder="Vai trò & Ghi chú xưng hô" title="${this.escapeHtml(roleText)}" value="${this.escapeHtml(roleText)}">
            </div>
        `;
        return card;
    }

    addCharacterCard() {
        const card = this.createCharacterCardElement({ name: '', first_person: 'tôi', second_person: 'cậu' });
        this.characterList.appendChild(card);
        card.querySelector('.char-input-name').focus();
    }

    renderTerms(terms) {
        this.termsList.innerHTML = '';
        for (const t of terms) {
            this.termsList.appendChild(this.createTermCardElement(t));
        }
    }

    createTermCardElement(termData = {}) {
        const card = document.createElement('div');
        card.className = 'term-card';
        card.innerHTML = `
            <div class="char-card-row">
                <input type="text" class="styled-input input-sm term-input-src" placeholder="Từ gốc (EN)" value="${this.escapeHtml(termData.source_term || '')}" style="width: 45%;">
                <span>➔</span>
                <input type="text" class="styled-input input-sm term-input-tgt" placeholder="Bản dịch (VI)" value="${this.escapeHtml(termData.target_term || '')}" style="width: 45%;">
                <button class="btn-del-item" title="Xóa thuật ngữ" onclick="this.closest('.term-card').remove()">✕</button>
            </div>
        `;
        return card;
    }

    addTermCard() {
        const card = this.createTermCardElement();
        this.termsList.appendChild(card);
        card.querySelector('.term-input-src').focus();
    }

    async autoDetectCharacters() {
        if (!this.currentProjectId) return;
        const btn = this.btnAutoDetectChars;
        const origText = btn.innerHTML;
        btn.disabled = true;
        btn.innerHTML = '⏳ Đang tra cứu AI...';
        this.appendLog('info', 'Đang dùng AI & tri thức văn học tra cứu toàn diện nhân vật & xưng hô...');
        try {
            const res = await fetch(`/api/projects/${this.currentProjectId}/glossary/auto_detect`, { method: 'POST' });
            const data = await res.json();
            if (data.status === 'ok') {
                const methodStr = data.method === 'ai' ? 'Trí tuệ nhân tạo (AI & Tri thức sách)' : 'Quét lời thoại sách';
                this.appendLog('success', `[${methodStr}] Đã tự động phân tích và thiết lập ${data.detected_count} nhân vật: ${data.names.join(', ')}`);
                await this.loadGlossary(this.currentProjectId);
            }
        } catch (e) {
            this.appendLog('error', `Lỗi phân tích nhân vật: ${e.message}`);
        } finally {
            btn.disabled = false;
            btn.innerHTML = origText;
        }
    }

    async saveGlossary() {
        if (!this.currentProjectId) return;

        // Collect characters
        const characters = [];
        const charCards = this.characterList.querySelectorAll('.char-card');
        charCards.forEach(card => {
            const name = card.querySelector('.char-input-name').value.trim();
            const pronounStr = card.querySelector('.char-input-pronoun').value.trim();
            const role = card.querySelector('.char-input-role').value.trim();

            if (name) {
                const parts = pronounStr.split(/[-–/]/).map(s => s.trim());
                characters.push({
                    name: name,
                    gender: 'unknown',
                    role: role,
                    first_person: parts[0] || 'tôi',
                    second_person: parts[1] || 'cậu',
                    third_person: name,
                    notes: ''
                });
            }
        });

        // Collect terms
        const terms = [];
        const termCards = this.termsList.querySelectorAll('.term-card');
        termCards.forEach(card => {
            const src = card.querySelector('.term-input-src').value.trim();
            const tgt = card.querySelector('.term-input-tgt').value.trim();
            if (src && tgt) {
                terms.push({ source_term: src, target_term: tgt, category: 'general', description: '' });
            }
        });

        const payload = {
            tone: this.toneSelect.value,
            custom_instructions: this.customInstructions.value.trim(),
            characters: characters,
            terms: terms
        };

        try {
            const res = await fetch(`/api/projects/${this.currentProjectId}/glossary`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            this.appendLog('success', data.message);
        } catch (e) {
            this.appendLog('error', `Lỗi lưu thiết lập: ${e.message}`);
        }
    }

    // --- FILE UPLOAD ---

    async handleFileUpload(file) {
        if (!file) return;

        this.uploadProgressContainer.classList.remove('hidden');
        this.uploadStatusText.textContent = `Đang phân tích sách: ${file.name}...`;

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/api/projects/upload', {
                method: 'POST',
                body: formData
            });
            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Lỗi tải sách');
            }

            const data = await res.json();
            this.appendLog('success', `Đã nạp thành công cuốn sách: "${data.title}" (${data.chapters_count} chương, ${data.paragraphs_count} đoạn)`);
            this.hideModal(this.uploadModal);
            this.uploadProgressContainer.classList.add('hidden');

            await this.loadProjects();
            this.selectProject(data.project_id);
        } catch (e) {
            this.uploadStatusText.textContent = `Thất bại: ${e.message}`;
            this.appendLog('error', `Lỗi tải file: ${e.message}`);
        }
    }

    // --- SETTINGS & EXPORT ---

    async loadSettings() {
        try {
            const res = await fetch('/api/settings');
            const data = await res.json();

            this.settingsProvider.value = data.provider || 'gemini';
            this.settingsApiKey.value = data.api_key || '';
            const currentModel = data.model || 'gemini-2.5-flash';
            this.settingsModel.value = currentModel;
            this.settingsBaseUrl.value = data.base_url || '';
            this.settingsTemp.value = data.temperature || 0.3;
            this.tempValueDisplay.textContent = this.settingsTemp.value;

            this.updateProviderFormVisibility(currentModel);
        } catch (e) {
            this.appendLog('error', `Lỗi tải cấu hình: ${e.message}`);
        }
    }

    updateProviderFormVisibility(selectedModel = null) {
        const provider = this.settingsProvider.value;
        const select = this.settingsModelSelect;
        select.innerHTML = '';

        if (provider === 'gemini') {
            this.groupBaseUrl.classList.add('hidden');
            this.groupApiKey.classList.remove('hidden');
            select.innerHTML = `
                <option value="gemini-2.5-flash">gemini-2.5-flash (Khuyên dùng: Tốc độ cực nhanh, văn mượt, miễn phí)</option>
                <option value="gemini-2.5-pro">gemini-2.5-pro (Chuyên sâu văn học, trau chuốt từng câu)</option>
                <option value="gemini-1.5-flash">gemini-1.5-flash (Bản ổn định phổ thông)</option>
                <option value="custom">✏️ Nhập tên mô hình khác...</option>
            `;
            if (this.modelHelpText) {
                this.modelHelpText.innerHTML = '👉 Khuyên dùng: <strong>gemini-2.5-flash</strong> (Miễn phí 100%, dịch nhanh và mượt mà).';
            }
        } else if (provider === 'deepseek') {
            this.groupBaseUrl.classList.remove('hidden');
            this.settingsBaseUrl.value = 'https://api.deepseek.com/v1';
            this.groupApiKey.classList.remove('hidden');
            select.innerHTML = `
                <option value="deepseek-chat">deepseek-chat (DeepSeek-V3: Chi phí cực rẻ, tiếng Việt xuất sắc)</option>
                <option value="deepseek-reasoner">deepseek-reasoner (DeepSeek-R1: Suy luận và dịch ngữ cảnh khó)</option>
                <option value="custom">✏️ Nhập tên mô hình khác...</option>
            `;
            if (this.modelHelpText) {
                this.modelHelpText.innerHTML = '👉 Khuyên dùng: <strong>deepseek-chat</strong> (Rất rẻ, văn phong dịch sang tiếng Việt cực hay).';
            }
        } else if (provider === 'openai') {
            this.groupBaseUrl.classList.add('hidden');
            this.groupApiKey.classList.remove('hidden');
            select.innerHTML = `
                <option value="gpt-4o-mini">gpt-4o-mini (Tiết kiệm chi phí, tốc độ cao)</option>
                <option value="gpt-4o">gpt-4o (Mô hình thông minh nhất của OpenAI)</option>
                <option value="custom">✏️ Nhập tên mô hình khác...</option>
            `;
            if (this.modelHelpText) {
                this.modelHelpText.innerHTML = '👉 Khuyên dùng: <strong>gpt-4o-mini</strong> hoặc <strong>gpt-4o</strong>.';
            }
        } else if (provider === 'openrouter') {
            this.groupBaseUrl.classList.remove('hidden');
            this.settingsBaseUrl.value = 'https://openrouter.ai/api/v1';
            this.groupApiKey.classList.remove('hidden');
            select.innerHTML = `
                <option value="deepseek/deepseek-chat">deepseek/deepseek-chat</option>
                <option value="anthropic/claude-3.5-sonnet">anthropic/claude-3.5-sonnet (Văn chương xuất sắc)</option>
                <option value="google/gemini-2.5-flash">google/gemini-2.5-flash</option>
                <option value="custom">✏️ Nhập tên mô hình khác...</option>
            `;
        } else if (provider === 'ollama') {
            this.groupBaseUrl.classList.remove('hidden');
            this.settingsBaseUrl.value = 'http://localhost:11434/v1';
            this.groupApiKey.classList.add('hidden');
            select.innerHTML = `
                <option value="qwen2.5:latest">qwen2.5:latest (Mô hình mã nguồn mở dịch tốt)</option>
                <option value="llama3:latest">llama3:latest</option>
                <option value="custom">✏️ Nhập tên mô hình khác...</option>
            `;
        } else if (provider === 'free_fallback') {
            this.groupBaseUrl.classList.add('hidden');
            this.groupApiKey.classList.add('hidden');
            select.innerHTML = `
                <option value="free-fallback">Dịch tự động miễn phí (Không cần cấu hình)</option>
            `;
            if (this.modelHelpText) {
                this.modelHelpText.innerHTML = '👉 Chế độ dùng thử: Không cần nhập API key hay tên mô hình.';
            }
        }

        // Set select value
        const targetModel = selectedModel || select.options[0]?.value || '';
        let found = false;
        for (let opt of select.options) {
            if (opt.value === targetModel) {
                select.value = targetModel;
                this.settingsModel.value = targetModel;
                this.settingsModel.classList.add('hidden');
                found = true;
                break;
            }
        }
        if (!found && targetModel && targetModel !== 'custom') {
            select.value = 'custom';
            this.settingsModel.value = targetModel;
            this.settingsModel.classList.remove('hidden');
        }
    }

    async saveSettings() {
        const payload = {
            provider: this.settingsProvider.value,
            api_key: this.settingsApiKey.value.trim(),
            model: this.settingsModel.value.trim(),
            base_url: this.settingsBaseUrl.value.trim(),
            temperature: parseFloat(this.settingsTemp.value)
        };

        try {
            const res = await fetch('/api/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await res.json();
            this.appendLog('success', data.message);
            this.hideModal(this.settingsModal);
        } catch (e) {
            this.appendLog('error', `Lỗi lưu cấu hình: ${e.message}`);
        }
    }

    openSettingsModal() {
        this.showModal(this.settingsModal);
    }

    downloadBook(format) {
        if (!this.currentProjectId) {
            alert('Vui lòng chọn hoặc tải lên một cuốn sách trước.');
            return;
        }
        const url = `/api/projects/${this.currentProjectId}/export/${format}`;
        window.open(url, '_blank');
        this.appendLog('info', `Đang tải xuống định dạng ${format}...`);
        this.hideModal(this.exportModal);
    }

    // --- MODAL UTILS ---
    showModal(el) { el.classList.remove('hidden'); }
    hideModal(el) { el.classList.add('hidden'); }

    escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }
}

// Instantiate App
let app;
window.addEventListener('DOMContentLoaded', () => {
    app = new BookTranslatorApp();
});
