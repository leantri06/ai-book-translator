/**
 * AI Book Translator Pro - Frontend Application Controller
 * Handles real-time polling updates, dual-view studio, inline editing, glossary & export.
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
        this.readerFont = 'font-serif';
        this.readerDisplayMode = 'vi-only';
        this.uploadType = 'paper';
        this.isUploading = false;
        this._projectSwitchToken = 0;
        this._chapterSwitchToken = 0;
        this._loadedCharacters = [];
        this._modalStack = [];      // focus-restore stack
        this._inertStates = new Map();

        this.initElements();
        this.bindEvents();
        this.setUploadType(this.uploadType);
        this.init();
    }

    initElements() {
        // Header
        this.projectSelect = document.getElementById('projectSelect');
        this.btnNewBook = document.getElementById('btnNewBook');
        this.btnDeleteProject = document.getElementById('btnDeleteProject');
        this.projectTitleDisplay = document.getElementById('projectTitleDisplay');
        this.globalPercentDisplay = document.getElementById('globalPercentDisplay');
        this.globalProgressBar = document.getElementById('globalProgressBar');
        this.btnStartTranslate = document.getElementById('btnStartTranslate');
        this.btnPauseTranslate = document.getElementById('btnPauseTranslate');
        this.btnExportModal = document.getElementById('btnExportModal');
        this.btnSettingsModal = document.getElementById('btnSettingsModal');
        this.btnUploadPaper = document.getElementById('btnUploadPaper');
        this.btnUploadNovel = document.getElementById('btnUploadNovel');

        // globalProgressBox ARIA
        const gpb = document.getElementById('globalProgressBox');
        if (gpb) {
            gpb.setAttribute('role', 'progressbar');
            gpb.setAttribute('aria-valuemin', '0');
            gpb.setAttribute('aria-valuemax', '100');
            gpb.setAttribute('aria-valuenow', '0');
            gpb.setAttribute('aria-label', 'Tiến độ dịch sách');
        }

        // Sidebar Left
        this.chapterCountBadge = document.getElementById('chapterCountBadge');
        this.chapterSearchInput = document.getElementById('chapterSearchInput');
        this.chaptersList = document.getElementById('chaptersList');

        // New chapter drawer elements (expected in HTML)
        this.sidebarChapters = document.getElementById('sidebarChapters');
        this.btnToggleChapters = document.getElementById('btnToggleChapters');
        this.btnCloseChapters = document.getElementById('btnCloseChapters');
        this.panelBackdrop = document.getElementById('panelBackdrop');

        // Center Views
        this.tabStudio = document.getElementById('tabStudio');
        this.tabReader = document.getElementById('tabReader');
        this.activeChapterTitle = document.getElementById('activeChapterTitle');
        this.btnTranslateCurrentChapter = document.getElementById('btnTranslateCurrentChapter');
        this.btnRetranslateCurrentChapter = document.getElementById('btnRetranslateCurrentChapter');
        this.btnToggleRightSidebar = document.getElementById('btnToggleRightSidebar');
        this.studioView = document.getElementById('studioView');
        this.readerView = document.getElementById('readerView');
        this.studioParagraphs = document.getElementById('studioParagraphs');
        this.readerBody = document.getElementById('readerBody');

        // Set initial font class on readerBody
        if (this.readerBody) {
            this.readerBody.className = 'reader-body font-serif';
        }

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
        this.groupCharacterSettings = document.getElementById('groupCharacterSettings');

        // sidebarRight initially collapsed
        if (this.sidebarRight) {
            this.sidebarRight.classList.add('collapsed');
        }
        // ARIA for toggle button
        if (this.btnToggleRightSidebar) {
            this.btnToggleRightSidebar.setAttribute('aria-expanded', 'false');
        }

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
        this.btnUploadModePaper = document.getElementById('btnUploadModePaper');
        this.btnUploadModeNovel = document.getElementById('btnUploadModeNovel');
        this.uploadModalTitle = document.getElementById('uploadModalTitle');
        this.uploadDropzoneHeading = document.getElementById('uploadDropzoneHeading');
        this.uploadAcceptHint = document.getElementById('uploadAcceptHint');
        this.uploadProgressTrack = document.getElementById('uploadProgressTrack');
        this.structureWarningsPanel = document.getElementById('structureWarningsPanel');
        this.structureWarningsList = document.getElementById('structureWarningsList');

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

        // Delete Modal
        this.deleteConfirmModal = document.getElementById('deleteConfirmModal');
        this.btnCloseDeleteModal = document.getElementById('btnCloseDeleteModal');
        this.btnCancelDelete = document.getElementById('btnCancelDelete');
        this.btnConfirmDeleteAction = document.getElementById('btnConfirmDeleteAction');
        this.deleteProjectTitleDisplay = document.getElementById('deleteProjectTitleDisplay');

        // Textbook Modal Elements
        this.btnTextbookModal = document.getElementById('btnTextbookModal');
        this.textbookModal = document.getElementById('textbookModal');
        this.btnCloseTextbookModal = document.getElementById('btnCloseTextbookModal');
        this.btnCancelTextbook = document.getElementById('btnCancelTextbook');
        this.btnStartConvertTextbook = document.getElementById('btnStartConvertTextbook');
        this.textbookExistingSelect = document.getElementById('textbookExistingSelect');
        this.textbookFileInput = document.getElementById('textbookFileInput');
        this.textbookSelectedFilename = document.getElementById('textbookSelectedFilename');
        this.textbookProgressContainer = document.getElementById('textbookProgressContainer');
        this.textbookStatusTitle = document.getElementById('textbookStatusTitle');
        this.textbookPercentDisplay = document.getElementById('textbookPercentDisplay');
        this.textbookProgressBar = document.getElementById('textbookProgressBar');
        this.textbookMessageDisplay = document.getElementById('textbookMessageDisplay');
        this.textbookSuccessBox = document.getElementById('textbookSuccessBox');
        this.textbookSuccessTitle = document.getElementById('textbookSuccessTitle');
        this.textbookSuccessMeta = document.getElementById('textbookSuccessMeta');
        this.btnDownloadTextbookEpub = document.getElementById('btnDownloadTextbookEpub');
        this.btnOpenTextbookReader = document.getElementById('btnOpenTextbookReader');
        this.textbookActionFooter = document.getElementById('textbookActionFooter');

        // textbookProgressContainer ARIA
        if (this.textbookProgressContainer) {
            this.textbookProgressContainer.setAttribute('role', 'progressbar');
            this.textbookProgressContainer.setAttribute('aria-valuemin', '0');
            this.textbookProgressContainer.setAttribute('aria-valuemax', '100');
            this.textbookProgressContainer.setAttribute('aria-valuenow', '0');
            this.textbookProgressContainer.setAttribute('aria-label', 'Tiến độ chuyển đổi giáo trình');
        }

        // Apply role=dialog + aria-modal to all modal cards
        this._initModalARIA();
    }

    _initModalARIA() {
        const pairs = [
            [this.uploadModal,        'uploadModalHeading'],
            [this.settingsModal,      'settingsModalHeading'],
            [this.exportModal,        'exportModalHeading'],
            [this.deleteConfirmModal, 'deleteModalHeading'],
            [this.textbookModal,      'textbookModalHeading'],
        ];
        pairs.forEach(([modal, hid]) => {
            if (!modal) return;
            const card = modal.querySelector('.modal-card');
            if (!card) return;
            card.setAttribute('role', 'dialog');
            card.setAttribute('aria-modal', 'true');
            card.setAttribute('tabindex', '-1');
            const heading = card.querySelector('.modal-header h2, .modal-header h3');
            if (heading) {
                if (!heading.id) heading.id = hid;
                card.setAttribute('aria-labelledby', heading.id);
            }
        });
    }

    bindEvents() {
        // Project selection & explicit upload mode buttons
        this.projectSelect.addEventListener('change', (e) => this.selectProject(e.target.value));
        if (this.btnUploadPaper) {
            this.btnUploadPaper.addEventListener('click', () => this.openUploadModal('paper'));
        }
        if (this.btnUploadNovel) {
            this.btnUploadNovel.addEventListener('click', () => this.openUploadModal('novel'));
        }
        this.btnNewBook.addEventListener('click', () => this.openUploadModal());
        if (this.btnUploadModePaper) {
            this.btnUploadModePaper.addEventListener('click', () => this.setUploadType('paper'));
        }
        if (this.btnUploadModeNovel) {
            this.btnUploadModeNovel.addEventListener('click', () => this.setUploadType('novel'));
        }
        const btnBrowseFile = document.getElementById('btnBrowseFile');
        if (btnBrowseFile) {
            btnBrowseFile.addEventListener('click', () => {
                if (!this.isUploading && this.bookFileInput) {
                    this.bookFileInput.click();
                }
            });
        }
        if (this.btnDeleteProject) {
            this.btnDeleteProject.addEventListener('click', (e) => {
                e.preventDefault();
                this.confirmDeleteProject();
            });
        }
        if (this.btnCloseDeleteModal) {
            this.btnCloseDeleteModal.addEventListener('click', () => this.hideModal(this.deleteConfirmModal));
        }
        if (this.btnCancelDelete) {
            this.btnCancelDelete.addEventListener('click', () => this.hideModal(this.deleteConfirmModal));
        }
        if (this.btnConfirmDeleteAction) {
            this.btnConfirmDeleteAction.addEventListener('click', () => this.executeDeleteProject());
        }

        // Textbook Modal Events
        if (this.btnTextbookModal) {
            this.btnTextbookModal.addEventListener('click', () => {
                this.resetTextbookModal();
                this.showModal(this.textbookModal);
            });
        }
        if (this.btnCloseTextbookModal) {
            this.btnCloseTextbookModal.addEventListener('click', () => this.hideModal(this.textbookModal));
        }
        if (this.btnCancelTextbook) {
            this.btnCancelTextbook.addEventListener('click', () => this.hideModal(this.textbookModal));
        }
        if (this.textbookFileInput) {
            this.textbookFileInput.addEventListener('change', (e) => {
                if (e.target.files && e.target.files[0]) {
                    this.textbookSelectedFilename.textContent = `Đã chọn: ${e.target.files[0].name}`;
                    if (this.textbookExistingSelect) this.textbookExistingSelect.value = '';
                }
            });
        }
        if (this.textbookExistingSelect) {
            this.textbookExistingSelect.addEventListener('change', (e) => {
                if (e.target.value) {
                    this.textbookSelectedFilename.textContent = `Đã chọn: ${e.target.value}`;
                    if (this.textbookFileInput) this.textbookFileInput.value = '';
                }
            });
        }
        if (this.btnStartConvertTextbook) {
            this.btnStartConvertTextbook.addEventListener('click', () => this.startTextbookConversion());
        }

        // Translation control buttons
        this.btnStartTranslate.addEventListener('click', () => this.startTranslation());
        this.btnPauseTranslate.addEventListener('click', () => this.pauseTranslation());
        this.btnTranslateCurrentChapter.addEventListener('click', () => {
            if (this.currentChapterId) {
                this.startTranslation(this.currentChapterId);
            }
        });
        if (this.btnRetranslateCurrentChapter) {
            this.btnRetranslateCurrentChapter.addEventListener('click', () => {
                if (!this.currentChapterId) {
                    alert('Vui lòng chọn một chương trước khi dịch lại.');
                    return;
                }
                const chapTitle = this.currentChapter ? this.currentChapter.title : 'chương này';
                if (confirm(`Bạn có chắc muốn xóa bản dịch cũ và dịch lại từ đầu "${chapTitle}" bằng mô hình AI hiện tại không?`)) {
                    this.startTranslation(this.currentChapterId, true);
                }
            });
        }

        // Search chapters
        this.chapterSearchInput.addEventListener('input', (e) => this.filterChapters(e.target.value));

        // View tabs — ARIA selected state
        this.tabStudio.addEventListener('click', () => this.switchView('studio'));
        this.tabReader.addEventListener('click', () => this.switchView('reader'));

        // Right sidebar toggle — ARIA expanded
        this.btnToggleRightSidebar.addEventListener('click', () => {
            const collapsed = this.sidebarRight.classList.toggle('collapsed');
            this.btnToggleRightSidebar.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
            this._updateBackdrop();
        });
        this.btnCloseRightSidebar.addEventListener('click', () => {
            this.sidebarRight.classList.add('collapsed');
            this.btnToggleRightSidebar.setAttribute('aria-expanded', 'false');
            this._updateBackdrop();
        });

        // Chapter drawer (left sidebar — new IDs)
        if (this.btnToggleChapters) {
            this.btnToggleChapters.addEventListener('click', () => {
                const open = this.sidebarChapters.classList.toggle('open');
                this.btnToggleChapters.setAttribute('aria-expanded', open ? 'true' : 'false');
                this._updateBackdrop();
            });
        }
        if (this.btnCloseChapters) {
            this.btnCloseChapters.addEventListener('click', () => this._closeChapterDrawer());
        }

        window.addEventListener('resize', () => this._updateBackdrop());

        // Backdrop
        if (this.panelBackdrop) {
            this.panelBackdrop.addEventListener('click', () => {
                this._closeChapterDrawer();
                this.sidebarRight.classList.add('collapsed');
                this.btnToggleRightSidebar.setAttribute('aria-expanded', 'false');
                this._updateBackdrop();
            });
        }

        // Escape: close topmost modal, then drawers
        document.addEventListener('keydown', (e) => {
            if (e.key !== 'Escape') return;
            if (this._modalStack.length > 0) {
                const top = this._modalStack[this._modalStack.length - 1];
                this.hideModal(top);
                return;
            }
            if (this.sidebarChapters && this.sidebarChapters.classList.contains('open')) {
                this._closeChapterDrawer();
                return;
            }
            if (this.sidebarRight && !this.sidebarRight.classList.contains('collapsed')) {
                this.sidebarRight.classList.add('collapsed');
                this.btnToggleRightSidebar.setAttribute('aria-expanded', 'false');
                this._updateBackdrop();
            }
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
                this.fontToggles.forEach(b => {
                    b.classList.remove('active');
                    b.setAttribute('aria-pressed', 'false');
                });
                btn.classList.add('active');
                btn.setAttribute('aria-pressed', 'true');
                // Map data-font to CSS class: merriweather/serif -> font-serif, sans -> font-sans
                const df = btn.dataset.font;
                this.readerFont = (df === 'merriweather' || df === 'serif') ? 'font-serif' : 'font-sans';
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
        if (this.settingsApiKey) {
            this.settingsApiKey.addEventListener('input', () => this.updateApiKeyCounter());
        }
        const btnCheckQuota = document.getElementById('btnCheckQuota');
        if (btnCheckQuota) {
            btnCheckQuota.addEventListener('click', () => this.checkQuota());
        }
        this.btnSaveSettings.addEventListener('click', () => this.saveSettings());

        // File Upload Dropzone (drag/drop preserved)
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
            if (this.isUploading) return;
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

    // --- Drawer helpers ---

    _closeChapterDrawer() {
        if (this.sidebarChapters) this.sidebarChapters.classList.remove('open');
        if (this.btnToggleChapters) this.btnToggleChapters.setAttribute('aria-expanded', 'false');
        this._updateBackdrop();
    }

    _updateBackdrop() {
        if (!this.panelBackdrop) return;
        const w = window.innerWidth;
        const chapOpen = this.sidebarChapters && this.sidebarChapters.classList.contains('open');
        const rightOpen = this.sidebarRight && !this.sidebarRight.classList.contains('collapsed');
        const show = (w <= 900 && chapOpen) || (w <= 1200 && rightOpen);
        this.panelBackdrop.classList.toggle('hidden', !show);
    }

    // --- LOGS ---

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

    // --- SSE / STATUS POLLING ---

    startStatusPolling(projectId) {
        if (this.pollTimer) clearInterval(this.pollTimer);
        this.lastPollTimestamp = 0;

        const pollFunc = async () => {
            if (this.currentProjectId !== projectId) return;
            const switchToken = this._projectSwitchToken;
            try {
                const res = await fetch(`/api/projects/${projectId}/status?since=${this.lastPollTimestamp}`);
                if (!res.ok) return;
                const data = await res.json();
                if (this.currentProjectId !== projectId || switchToken !== this._projectSwitchToken) return;
                this.lastPollTimestamp = data.timestamp || (Date.now() / 1000);

                // 1. Update running status
                this.updateTranslatingStatus(data.is_running);
                if (data.status_text) {
                    this.statusText.textContent = data.status_text;
                    this.footerCurrentChunk.textContent = data.status_text;
                }

                // 2. Add new logs
                if (data.logs && data.logs.length > 0) {
                    for (const l of data.logs) this.appendLog(l.level || 'info', l.text);
                }

                // 3. Update overall progress
                if (data.overall_progress !== undefined && data.overall_progress > 0) {
                    this.updateGlobalProgress(data.overall_progress);
                }

                // 4. Update chapter progress badge & fill bar
                if (data.chapter_id && data.chapter_progress !== undefined) {
                    const chapBadge = document.getElementById(`chap_badge_${data.chapter_id}`);
                    if (chapBadge) {
                        chapBadge.textContent = `${data.chapter_progress}%`;
                        chapBadge.className = data.chapter_progress >= 100 ? 'chapter-badge badge-done' : 'chapter-badge badge-progress';
                    }
                    const miniFill = document.getElementById(`chap_fill_${data.chapter_id}`);
                    if (miniFill) miniFill.style.width = `${data.chapter_progress}%`;
                }

                // 5. Update paragraph editors — class flash, no inline color
                if (data.updated_paragraphs && data.updated_paragraphs.length > 0) {
                    for (const p of data.updated_paragraphs) {
                        if (this.currentChapterId === p.chapter_id) {
                            const pEl = document.getElementById(`para_${p.id}`);
                            if (pEl) {
                                const editor = pEl.querySelector('.para-vi-editor');
                                const chip = pEl.querySelector('.para-status-chip');
                                if (editor && editor.innerText !== p.text) {
                                    editor.innerText = p.text;
                                    editor.classList.add('editor-updated');
                                    setTimeout(() => editor.classList.remove('editor-updated'), 800);
                                }
                                if (chip) {
                                    chip.className = 'para-status-chip chip-done';
                                    chip.textContent = 'Đã dịch';
                                }
                            }
                        }
                    }
                }
            } catch (err) {
                // Ignore transient network errors during polling
            }
        };

        pollFunc();
        this.pollTimer = setInterval(pollFunc, 1500);
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

    confirmDeleteProject() {
        const projId = this.currentProjectId || (this.projectSelect ? this.projectSelect.value : null);
        if (!projId) {
            alert('Vui lòng chọn một sách hoặc bài báo trong danh sách để xóa.');
            return;
        }
        const projTitle = this.currentProject?.title ||
            (this.projectSelect && this.projectSelect.selectedIndex >= 0
                ? this.projectSelect.options[this.projectSelect.selectedIndex].text
                : 'Dự án đã chọn');

        if (this.deleteProjectTitleDisplay) this.deleteProjectTitleDisplay.textContent = projTitle;
        if (this.deleteConfirmModal) {
            this.showModal(this.deleteConfirmModal);
        } else {
            if (confirm(`Bạn có chắc chắn muốn xóa bài báo / sách:\n"${projTitle}"?\n\nToàn bộ dữ liệu sẽ bị xóa vĩnh viễn.`)) {
                this.executeDeleteProject();
            }
        }
    }

    deleteCurrentProject() { this.confirmDeleteProject(); }

    async executeDeleteProject() {
        const projId = this.currentProjectId || (this.projectSelect ? this.projectSelect.value : null);
        if (!projId) return;

        const projTitle = this.currentProject?.title || 'dự án';
        const confirmBtn = this.btnConfirmDeleteAction || document.getElementById('btnConfirmDeleteAction');
        const origBtnText = confirmBtn ? confirmBtn.textContent : '';

        if (confirmBtn) {
            confirmBtn.disabled = true;
            confirmBtn.textContent = 'Đang xóa...';
        }

        try {
            if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }

            const res = await fetch(`/api/projects/${projId}`, { method: 'DELETE' });
            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                throw new Error(errData.detail || 'Không thể xóa dự án');
            }

            this.appendLog('info', `Đã xóa thành công bài báo/sách: "${projTitle}".`);
            if (this.deleteConfirmModal) this.hideModal(this.deleteConfirmModal);

            // Reset current state
            this.currentProjectId = null;
            this.currentProject = null;
            this.currentChapterId = null;
            this.currentChapter = null;
            delete document.body.dataset.doctype;
            this.renderStructureWarnings([]);
            this.projectTitleDisplay.textContent = 'Chưa chọn sách';
            this.updateGlobalProgress(0);
            this.chapterCountBadge.textContent = '0';
            this.chaptersList.innerHTML = '<div class="empty-placeholder">Chưa chọn sách</div>';
            this.studioParagraphs.innerHTML = '<div class="empty-placeholder">Chọn một chương để xem và chỉnh sửa bản dịch song ngữ</div>';
            this.readerBody.innerHTML = '<div class="empty-placeholder">Nội dung chương sẽ hiển thị tại đây khi được chọn.</div>';

            await this.loadProjects();
        } catch (e) {
            alert(`Lỗi khi xóa: ${e.message}`);
            this.appendLog('error', `Lỗi xóa dự án: ${e.message}`);
        } finally {
            if (confirmBtn) {
                confirmBtn.disabled = false;
                confirmBtn.textContent = origBtnText || 'Xóa vĩnh viễn';
            }
        }
    }

    openUploadModal(mode = null) {
        if (this.isUploading) {
            this.showModal(this.uploadModal);
            return;
        }
        if (mode) {
            this.setUploadType(mode);
        } else {
            this.setUploadType(this.uploadType || 'novel');
        }
        if (this.uploadProgressContainer) {
            this.uploadProgressContainer.classList.add('hidden');
        }
        this.showModal(this.uploadModal);
    }

    setUploadType(mode) {
        if (this.isUploading) return;
        this.uploadType = mode === 'paper' ? 'paper' : 'novel';
        this.uploadModal.dataset.uploadType = this.uploadType;
        const isPaper = this.uploadType === 'paper';

        if (this.btnUploadModePaper) {
            this.btnUploadModePaper.classList.toggle('active', isPaper);
            this.btnUploadModePaper.setAttribute('aria-pressed', isPaper ? 'true' : 'false');
        }
        if (this.btnUploadModeNovel) {
            this.btnUploadModeNovel.classList.toggle('active', !isPaper);
            this.btnUploadModeNovel.setAttribute('aria-pressed', !isPaper ? 'true' : 'false');
        }
        if (this.bookFileInput) {
            this.bookFileInput.accept = isPaper ? '.pdf' : '.epub,.docx,.txt,.md';
        }
        if (this.uploadModalTitle) {
            this.uploadModalTitle.textContent = isPaper ? 'Tải bài báo (Paper PDF)' : 'Tải sách điện tử (Novel eBook)';
        }
        if (this.uploadDropzoneHeading) {
            this.uploadDropzoneHeading.textContent = isPaper
                ? 'Kéo thả file PDF bài báo vào đây'
                : 'Kéo thả file sách (EPUB, DOCX, TXT, MD) vào đây';
        }
        if (this.uploadAcceptHint) {
            this.uploadAcceptHint.textContent = isPaper
                ? 'Chỉ chấp nhận file PDF · Tối đa 100 MiB'
                : 'EPUB, DOCX, TXT hoặc MD · Tối đa 100 MiB';
        }
    }

    _setUploadControlsLocked(locked) {
        if (this.btnUploadModePaper) this.btnUploadModePaper.disabled = locked;
        if (this.btnUploadModeNovel) this.btnUploadModeNovel.disabled = locked;
        if (this.bookFileInput) this.bookFileInput.disabled = locked;
        const browseBtn = document.getElementById('btnBrowseFile');
        if (browseBtn) browseBtn.disabled = locked;
    }

    normalizeDocType(proj) {
        if (!proj) return 'novel';
        const dt = (proj.document_type || '').toLowerCase().trim();
        if (dt === 'paper' || dt === 'novel' || dt === 'textbook') return dt;
        const name = (proj.original_filename || proj.filename || proj.title || '').toLowerCase();
        if (proj.source_format === 'pdf' || proj.format === 'pdf' || name.endsWith('.pdf')) {
            return 'paper';
        }
        return 'novel';
    }

    updateDocTypeUI(docType) {
        const isPaper = docType === 'paper';
        const isNovel = docType === 'novel';
        const label = isPaper ? 'Mục' : 'Chương';
        this.tabReader.textContent = isPaper ? 'Đọc paper' : 'Đọc sách';
        this.btnExportModal.textContent = isPaper ? 'Xuất paper' : 'Xuất sách';
        this.btnStartTranslate.title = isPaper ? 'Dịch toàn bộ paper' : 'Dịch toàn bộ sách';
        this.chaptersList.setAttribute('aria-label', `Danh sách ${label.toLowerCase()}`);
        document.querySelector('label[for="chapterSearchInput"]').textContent = `Tìm ${label.toLowerCase()}`;
        this.customInstructions.placeholder = isPaper
            ? 'Ví dụ: Giữ nguyên ký hiệu toán học; thống nhất thuật ngữ chuyên ngành.'
            : 'Ví dụ: Giữ nguyên tên riêng; xưng hô giữa hai nhân vật là tôi – cậu.';

        const chapLabelEl = document.querySelector('.current-chap-label');
        if (chapLabelEl) chapLabelEl.textContent = label;

        if (this.chapterSearchInput) {
            this.chapterSearchInput.placeholder = `Tìm ${label.toLowerCase()}…`;
        }
        if (this.btnTranslateCurrentChapter) {
            this.btnTranslateCurrentChapter.textContent = `Dịch ${label.toLowerCase()}`;
        }
        if (this.btnRetranslateCurrentChapter) {
            this.btnRetranslateCurrentChapter.textContent = isPaper ? 'Dịch lại mục' : 'Dịch lại';
        }
        if (!this.currentChapterId && this.activeChapterTitle) {
            this.activeChapterTitle.textContent = `Chọn một ${label.toLowerCase()} để bắt đầu`;
        }

        const acadOpt = this.toneSelect ? this.toneSelect.querySelector('option[value="academic"]') : null;
        if (this.toneSelect) {
            if (isPaper) {
                if (acadOpt) { acadOpt.hidden = false; acadOpt.disabled = false; }
                this.toneSelect.value = 'academic';
                this.toneSelect.disabled = true;
            } else if (isNovel) {
                if (acadOpt) { acadOpt.hidden = true; acadOpt.disabled = true; }
                this.toneSelect.disabled = false;
                if (this.toneSelect.value === 'academic') {
                    this.toneSelect.value = 'novel';
                }
            } else {
                if (acadOpt) { acadOpt.hidden = false; acadOpt.disabled = false; }
                this.toneSelect.disabled = false;
            }
        }

        if (this.groupCharacterSettings) {
            this.groupCharacterSettings.classList.toggle('hidden', isPaper);
        }
    }

    renderStructureWarnings(warnings) {
        if (!this.structureWarningsPanel || !this.structureWarningsList) return;
        this.structureWarningsList.textContent = '';
        const list = Array.isArray(warnings) ? warnings.filter(Boolean) : [];
        if (list.length === 0) {
            this.structureWarningsPanel.classList.add('hidden');
            return;
        }
        for (const item of list) {
            const li = document.createElement('li');
            li.className = 'structure-warning-item';
            li.textContent = typeof item === 'string' ? item : (item.message || item.text || JSON.stringify(item));
            this.structureWarningsList.appendChild(li);
        }
        this.structureWarningsPanel.classList.remove('hidden');
    }

    async loadProjects(preferredProjectId = null) {
        try {
            const res = await fetch('/api/projects');
            const projects = await res.json();

            this.projectSelect.innerHTML = '';
            if (projects.length === 0) {
                this.projectSelect.innerHTML = '<option value="">-- Chưa có tài liệu nào, hãy tải lên --</option>';
                this.openUploadModal('novel');
                return;
            }

            for (const p of projects) {
                const opt = document.createElement('option');
                opt.value = p.id;
                const docType = this.normalizeDocType(p);
                const prefix = docType === 'paper' ? '[Paper]' : (docType === 'textbook' ? '[Textbook]' : '[Novel]');
                opt.textContent = `${prefix} ${p.title} (${p.progress_percent}%)`;
                this.projectSelect.appendChild(opt);
            }

            const targetId = (preferredProjectId && projects.some(p => p.id === preferredProjectId))
                ? preferredProjectId
                : (this.currentProjectId && projects.some(p => p.id === this.currentProjectId)
                    ? this.currentProjectId
                    : projects[0].id);

            await this.selectProject(targetId);
        } catch (e) {
            this.appendLog('error', `Lỗi tải danh sách dự án: ${e.message}`);
        }
    }

    async selectProject(projectId) {
        if (!projectId) return;
        if (this.pollTimer) { clearInterval(this.pollTimer); this.pollTimer = null; }
        this._chapterSwitchToken += 1;
        this.currentProject = null;
        this._loadedCharacters = [];
        this.renderCharacters([]);
        this.renderTerms([]);
        this.customInstructions.value = '';
        this.btnSaveGlossary.disabled = true;
        this.chaptersList.textContent = '';
        this.currentProjectId = projectId;
        this.projectSelect.value = projectId;

        // Clear old chapter content immediately even if new project has no chapters
        this.currentChapterId = null;
        this.currentChapter = null;
        if (this.activeChapterTitle) {
            this.activeChapterTitle.textContent = 'Chọn một mục để bắt đầu';
        }
        if (this.studioParagraphs) {
            this.studioParagraphs.innerHTML = '<div class="empty-placeholder">Chọn một mục để xem và chỉnh sửa bản dịch song ngữ</div>';
        }
        if (this.readerBody) {
            this.readerBody.innerHTML = '<div class="empty-placeholder">Nội dung mục sẽ hiển thị tại đây khi được chọn.</div>';
        }
        this.renderStructureWarnings([]);

        // Guard tokens against stale responses
        this._projectSwitchToken = (this._projectSwitchToken || 0) + 1;
        const switchToken = this._projectSwitchToken;

        await this.loadProjectDetails(projectId, true, switchToken);
        await this.loadGlossary(projectId, switchToken);
        if (switchToken === this._projectSwitchToken && this.currentProjectId === projectId) {
            this.startStatusPolling(projectId);
        }
    }

    async loadProjectDetails(projectId, autoSelectFirstChapter = true, switchToken = null) {
        try {
            const res = await fetch(`/api/projects/${projectId}`);
            if (!res.ok) throw new Error('Không thể tải thông tin sách');
            const data = await res.json();

            // Guard against stale response
            if (switchToken !== null && switchToken !== this._projectSwitchToken) return;
            if (this.currentProjectId !== projectId) return;

            this.currentProject = data;
            const docType = this.normalizeDocType(data);
            document.body.dataset.doctype = docType;
            this.updateDocTypeUI(docType);

            this.projectTitleDisplay.textContent = data.title;
            this.updateGlobalProgress(data.progress_percent);
            this.chapterCountBadge.textContent = data.total_chapters;
            this.updateTranslatingStatus(data.is_translating);

            this.renderStructureWarnings(data.structure_warnings || []);
            this.renderChaptersList(data.chapters);

            if (autoSelectFirstChapter && data.chapters && data.chapters.length > 0) {
                this.selectChapter(data.chapters[0].id);
            }
        } catch (e) {
            if (switchToken === null || switchToken === this._projectSwitchToken) {
                this.appendLog('error', e.message);
            }
        }
    }

    updateGlobalProgress(percent) {
        const p = Math.min(100, Math.max(0, percent || 0));
        this.globalPercentDisplay.textContent = `${p}%`;
        this.globalProgressBar.style.width = `${p}%`;
        const gpb = document.getElementById('globalProgressBox');
        if (gpb) gpb.setAttribute('aria-valuenow', String(p));
    }

    renderChaptersList(chapters) {
        this.chaptersList.innerHTML = '';
        if (!chapters || chapters.length === 0) {
            this.chaptersList.innerHTML = '<div class="empty-placeholder">Sách không có chương nào.</div>';
            return;
        }

        for (const chap of chapters) {
            // <button type="button"> for keyboard operability
            const item = document.createElement('button');
            item.type = 'button';
            item.className = `chapter-item ${chap.id === this.currentChapterId ? 'active' : ''}`;
            item.id = `chap_item_${chap.id}`;
            item.addEventListener('click', () => {
                this.selectChapter(chap.id);
                // Close chapter drawer on narrow screens after selection
                if (window.innerWidth <= 900) this._closeChapterDrawer();
            });

            let badgeClass = 'badge-pending';
            if (chap.progress_percent >= 100) badgeClass = 'badge-done';
            else if (chap.progress_percent > 0) badgeClass = 'badge-progress';

            item.innerHTML = `
                <div class="chapter-title-row">
                    <span class="chapter-title" title="${this.escapeHtml(chap.title)}">${this.escapeHtml(chap.title)}</span>
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
            item.style.display = title.includes(q) ? '' : 'none';
        });
    }

    // --- CHAPTER DETAIL & DUAL-VIEW ---

    async selectChapter(chapterId) {
        this.currentChapterId = chapterId;
        const projId = this.currentProjectId;

        const allItems = this.chaptersList.querySelectorAll('.chapter-item');
        allItems.forEach(i => { i.classList.remove('active'); i.removeAttribute('aria-current'); });
        const activeItem = document.getElementById(`chap_item_${chapterId}`);
        if (activeItem) { activeItem.classList.add('active'); activeItem.setAttribute('aria-current', 'page'); }

        this._chapterSwitchToken = (this._chapterSwitchToken || 0) + 1;
        const chapToken = this._chapterSwitchToken;

        try {
            const res = await fetch(`/api/projects/${projId}/chapters/${chapterId}`);
            if (!res.ok) throw new Error('Không thể tải chi tiết chương');
            const data = await res.json();

            if (chapToken !== this._chapterSwitchToken || this.currentProjectId !== projId) return;

            this.currentChapter = data;
            this.activeChapterTitle.textContent = data.title;
            this.renderStudioView();
            this.renderReaderView();
        } catch (e) {
            if (chapToken === this._chapterSwitchToken && this.currentProjectId === projId) {
                this.appendLog('error', e.message);
            }
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

            // Image paragraph — no inline styles; use classes studio-image / image-caption / image-preserved
            if (p.tag === 'img' || p.image_path) {
                const imgFilename = p.image_path ? p.image_path.split(/[\\\/]/).pop() : '';
                const imgSrc = imgFilename ? `/api/projects/${this.currentProjectId}/images/${imgFilename}` : '';
                row.className = 'para-row para-row-image';

                const enDiv = document.createElement('div');
                enDiv.className = 'para-en';

                if (imgSrc) {
                    const img = document.createElement('img');
                    img.src = imgSrc;
                    img.alt = p.original_text || '';
                    img.className = 'studio-image';
                    enDiv.appendChild(img);
                }
                const capDiv = document.createElement('div');
                capDiv.className = 'image-caption';
                capDiv.textContent = p.original_text;
                enDiv.appendChild(capDiv);

                const viDiv = document.createElement('div');
                viDiv.className = 'para-vi-wrapper';
                const preservedDiv = document.createElement('div');
                preservedDiv.className = 'image-preserved';
                preservedDiv.textContent = '[Hình anh / So do duoc giu nguyen ban goc]';
                viDiv.appendChild(preservedDiv);

                row.appendChild(enDiv);
                row.appendChild(viDiv);
                frag.appendChild(row);
                continue;
            }

            let chipClass = 'chip-pending';
            let chipText = 'Đang chờ';
            if (p.status === 'done') { chipClass = 'chip-done'; chipText = 'Đã dịch'; }
            else if (p.status === 'edited') { chipClass = 'chip-edited'; chipText = 'Đã sửa tay'; }

            const enDiv = document.createElement('div');
            enDiv.className = 'para-en';
            enDiv.textContent = p.original_text;

            const viWrapper = document.createElement('div');
            viWrapper.className = 'para-vi-wrapper';

            const editor = document.createElement('div');
            editor.className = 'para-vi-editor';
            editor.setAttribute('contenteditable', 'true');
            editor.setAttribute('spellcheck', 'false');
            editor.setAttribute('role', 'textbox');
            editor.setAttribute('aria-label', 'Bản dịch tiếng Việt có thể chỉnh sửa');
            editor.setAttribute('aria-multiline', 'true');
            editor.setAttribute('data-para-id', p.id);
            editor.setAttribute('data-placeholder', 'Đoạn văn bản tiếng Việt…');
            editor.textContent = p.translated_text || '';

            const metaDiv = document.createElement('div');
            metaDiv.className = 'para-meta';
            const chip = document.createElement('span');
            chip.className = `para-status-chip ${chipClass}`;
            chip.textContent = chipText;
            metaDiv.appendChild(chip);

            viWrapper.appendChild(editor);
            viWrapper.appendChild(metaDiv);
            row.appendChild(enDiv);
            row.appendChild(viWrapper);

            // Auto-save on blur (upstream save error preserved)
            editor.addEventListener('blur', (e) => {
                const newText = e.target.innerText.trim();
                if (newText !== (p.translated_text || '')) {
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
            if (!res.ok) {
                const error = await res.json();
                throw new Error(error.detail || 'Không thể lưu bản dịch');
            }
            const chip = rowEl.querySelector('.para-status-chip');
            chip.className = 'para-status-chip chip-edited';
            chip.textContent = 'Đã sửa tay';
            this.appendLog('info', `Đã lưu đoạn văn chỉnh sửa (${paraId})`);
        } catch (e) {
            this.appendLog('error', `Lỗi lưu đoạn văn: ${e.message}`);
        }
    }

    renderReaderView() {
        this.readerBody.innerHTML = '';
        const isPaper = this.currentProject && this.normalizeDocType(this.currentProject) === 'paper';
        if (!this.currentChapter || !this.currentChapter.paragraphs.length) {
            const noContent = document.createElement('p');
            noContent.className = 'reader-notice';
            noContent.textContent = isPaper ? 'Không có nội dung mục để hiển thị.' : 'Không có nội dung để hiển thị.';
            this.readerBody.appendChild(noContent);
            return;
        }

        const chapTitle = (this.currentChapter.title || '').trim();
        const chapTitleLower = chapTitle.toLowerCase();
        const isPreamble = ['phần mở đầu / tiêu đề', 'title', 'header'].includes(chapTitleLower);

        const firstPara = this.currentChapter.paragraphs && this.currentChapter.paragraphs[0];
        const headingTags = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'];
        const firstParaIsHeadingAndMatches = firstPara &&
            firstPara.tag &&
            headingTags.includes(firstPara.tag.toLowerCase()) &&
            (firstPara.original_text || '').trim().toLowerCase() === chapTitleLower;

        if (!isPreamble && !firstParaIsHeadingAndMatches && chapTitle) {
            const titleH2 = document.createElement('h2');
            titleH2.textContent = this.currentChapter.title;
            this.readerBody.appendChild(titleH2);
        }

        const translatedCount = this.currentChapter.paragraphs.filter(
            p => p.translated_text && p.translated_text.trim()
        ).length;
        const isNotTranslated = translatedCount === 0;

        if (isNotTranslated && this.readerDisplayMode !== 'en-only') {
            const alertBox = document.createElement('div');
            alertBox.className = 'notice reader-notice';

            const titleDiv = document.createElement('div');
            titleDiv.className = 'notice-title';
            titleDiv.textContent = 'Chương này chưa được dịch sang tiếng Việt.';
            alertBox.appendChild(titleDiv);

            const descDiv = document.createElement('div');
            descDiv.textContent = 'Chương này chưa có bản dịch tiếng Việt. Bạn có thể xem bản gốc hoặc bắt đầu dịch bằng nút bên dưới.';
            alertBox.appendChild(descDiv);

            const actionsDiv = document.createElement('div');
            actionsDiv.className = 'notice-actions';
            const translateBtn = document.createElement('button');
            translateBtn.type = 'button';
            translateBtn.className = 'btn btn-primary';
            translateBtn.textContent = `Dịch chương này (${this.currentChapter.paragraphs.length} đoạn)`;
            translateBtn.addEventListener('click', () => this.startTranslation(this.currentChapter.id));
            actionsDiv.appendChild(translateBtn);
            alertBox.appendChild(actionsDiv);
            this.readerBody.appendChild(alertBox);
        }

        const isCaption = (p) => {
            if (!p) return false;
            if (p.tag === 'caption') return true;
            const pat = /^(?:Figure|Fig\.?|Hình|Table|Bảng)\s*[\d\.\-]+[:\.\-–]/i;
            return pat.test((p.original_text || '').trim()) || pat.test((p.translated_text || '').trim());
        };

        const splitCaption = (text) => {
            const m = (text || '').trim().match(
                /^(Figure\s*[\d\.\-]+[:\.\-–]|Fig\.?\s*[\d\.\-]+[:\.\-–]|Hình\s*[\d\.\-]+[:\.\-–]|Table\s*[\d\.\-]+[:\.\-–]|Bảng\s*[\d\.\-]+[:\.\-–])\s*(.*)$/i
            );
            if (m) return { label: m[1].trim(), content: m[2].trim() };
            return { label: '', content: text };
        };

        const makeCaptionEl = (enCap, viCap, extraClass) => {
            const capDiv = document.createElement('div');
            capDiv.className = extraClass ? `image-caption ${extraClass}` : 'image-caption';

            if (this.readerDisplayMode === 'bilingual') {
                const enObj = splitCaption(enCap);
                const viObj = splitCaption(viCap);
                const pair = document.createElement('div');
                pair.className = 'caption-pair';

                const enRow = document.createElement('div');
                enRow.className = 'caption-en';
                enRow.innerHTML = `<span class="cap-badge en">EN</span> <strong>${this.escapeHtml(enObj.label)}</strong> ${this.escapeHtml(enObj.content)}`;

                const viRow = document.createElement('div');
                viRow.className = 'caption-vi';
                viRow.innerHTML = `<span class="cap-badge vi">VI</span> <strong>${this.escapeHtml(viObj.label)}</strong> ${this.escapeHtml(viObj.content)}`;

                pair.appendChild(enRow);
                pair.appendChild(viRow);
                capDiv.appendChild(pair);
            } else {
                const targetCap = this.readerDisplayMode === 'en-only' ? enCap : viCap;
                const obj = splitCaption(targetCap);
                capDiv.innerHTML = `<strong>${this.escapeHtml(obj.label)}</strong> ${this.escapeHtml(obj.content)}`;
            }
            return capDiv;
        };

        const paras = this.currentChapter.paragraphs;
        let pIdx = 0;

        while (pIdx < paras.length) {
            const p = paras[pIdx];

            // Image — use classes reader-image, image-caption
            if (p.tag === 'img' || p.image_path) {
                const imgFilename = p.image_path ? p.image_path.split(/[\\\/]/).pop() : '';
                const imgSrc = imgFilename ? `/api/projects/${this.currentProjectId}/images/${imgFilename}` : '';
                const nextP = pIdx + 1 < paras.length ? paras[pIdx + 1] : null;
                const captionPara = isCaption(nextP) ? nextP : null;

                if (imgSrc) {
                    const isTable = captionPara
                        ? (/^(?:Table|Bảng)\b/i.test(captionPara.original_text) ||
                           /^(?:Table|Bảng)\b/i.test(captionPara.translated_text) ||
                           p.id.includes('tab'))
                        : false;

                    const card = document.createElement('div');
                    card.className = isTable ? 'academic-table-block' : 'academic-figure';

                    const wrapper = document.createElement('div');
                    wrapper.className = isTable ? 'table-image-wrapper' : 'figure-image-wrapper';
                    const img = document.createElement('img');
                    img.src = imgSrc;
                    img.alt = p.original_text || '';
                    img.className = 'reader-image';
                    wrapper.appendChild(img);

                    if (captionPara) {
                        const enCap = (captionPara.original_text || '').trim();
                        const viCap = (captionPara.translated_text || '').trim() || enCap;
                        const capEl = makeCaptionEl(enCap, viCap, isTable ? 'table-caption' : 'figure-caption');
                        if (isTable) { card.appendChild(capEl); card.appendChild(wrapper); }
                        else { card.appendChild(wrapper); card.appendChild(capEl); }
                    } else {
                        card.appendChild(wrapper);
                    }

                    this.readerBody.appendChild(card);
                    pIdx += captionPara ? 2 : 1;
                    continue;
                }
            }

            // Standalone caption
            if (isCaption(p)) {
                const enCap = (p.original_text || '').trim();
                const viCap = (p.translated_text || '').trim() || enCap;
                const capEl = makeCaptionEl(enCap, viCap, 'table-caption');
                this.readerBody.appendChild(capEl);
                pIdx += 1;
                continue;
            }

            // Footnotes (*, †, ‡)
            const firstChar = (p.original_text || '').trim()[0];
            const isFootnote = firstChar === '*' || firstChar === '∗' || firstChar === '†' || firstChar === '‡';
            if (isFootnote) {
                const fnDiv = document.createElement('div');
                fnDiv.className = 'academic-footnote';
                const hasVi = p.translated_text && p.translated_text.trim();
                if (this.readerDisplayMode === 'bilingual') {
                    const enSpan = document.createElement('div');
                    enSpan.className = 'fn-en';
                    enSpan.textContent = p.original_text;
                    const viSpan = document.createElement('div');
                    viSpan.className = 'fn-vi';
                    viSpan.textContent = p.translated_text || '';
                    fnDiv.appendChild(enSpan);
                    fnDiv.appendChild(viSpan);
                } else if (this.readerDisplayMode === 'en-only') {
                    fnDiv.textContent = p.original_text;
                } else {
                    fnDiv.textContent = hasVi ? p.translated_text : p.original_text;
                }
                this.readerBody.appendChild(fnDiv);
                pIdx += 1;
                continue;
            }

            const hasVi = p.translated_text && p.translated_text.trim();
            const isHeading = p.tag && ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].includes(p.tag.toLowerCase());

            if (this.readerDisplayMode === 'bilingual') {
                const pair = document.createElement('div');
                pair.className = isHeading ? 'reader-bilingual-pair reader-heading-pair' : 'reader-bilingual-pair';

                const enDiv = document.createElement('div');
                enDiv.className = isHeading ? 'reader-bilingual-en heading-en' : 'reader-bilingual-en';
                enDiv.textContent = p.original_text;

                const viDiv = document.createElement('div');
                viDiv.className = isHeading ? 'reader-bilingual-vi heading-vi' : 'reader-bilingual-vi';
                if (hasVi) {
                    viDiv.textContent = p.translated_text;
                } else {
                    const em = document.createElement('em');
                    em.className = 'not-translated';
                    em.textContent = '[Đoạn này chưa dịch]';
                    viDiv.appendChild(em);
                }

                pair.appendChild(enDiv);
                pair.appendChild(viDiv);
                this.readerBody.appendChild(pair);
            } else if (this.readerDisplayMode === 'en-only') {
                const pEl = document.createElement(isHeading ? p.tag : 'p');
                pEl.textContent = p.original_text;
                this.readerBody.appendChild(pEl);
            } else {
                // vi-only
                const pEl = document.createElement(isHeading ? p.tag : 'p');
                if (hasVi) {
                    pEl.textContent = p.translated_text;
                } else {
                    const em = document.createElement('em');
                    em.className = 'not-translated';
                    em.textContent = `[Chưa dịch: "${p.original_text.substring(0, 80)}…"]`;
                    pEl.appendChild(em);
                }
                this.readerBody.appendChild(pEl);
            }

            pIdx += 1;
        }
    }

    switchView(viewName) {
        this.activeView = viewName;
        if (viewName === 'studio') {
            this.tabStudio.classList.add('active');
            this.tabReader.classList.remove('active');
            this.tabStudio.setAttribute('aria-selected', 'true');
            this.tabReader.setAttribute('aria-selected', 'false');
            this.studioView.classList.remove('hidden');
            this.readerView.classList.add('hidden');
        } else {
            this.tabReader.classList.add('active');
            this.tabStudio.classList.remove('active');
            this.tabReader.setAttribute('aria-selected', 'true');
            this.tabStudio.setAttribute('aria-selected', 'false');
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
        // this.readerFont is already 'font-serif' or 'font-sans'
        this.readerBody.className = `reader-body ${this.readerFont}`;
    }

    // --- TRANSLATION CONTROLS ---

    async startTranslation(chapterId = null, force = false) {
        if (!this.currentProjectId) {
            alert('Vui lòng chọn một cuốn sách trước khi dịch.');
            return;
        }

        const params = [];
        if (chapterId) params.push(`chapter_id=${encodeURIComponent(chapterId)}`);
        if (force) params.push('force=true');
        const url = `/api/projects/${this.currentProjectId}/translate/start${params.length ? '?' + params.join('&') : ''}`;

        this.updateTranslatingStatus(true);
        const chapTitle = this.currentChapter ? this.currentChapter.title : (chapterId || '');
        if (force) {
            this.appendLog('info', `[Dịch lại] Đang xóa bản dịch cũ và dịch lại từ đầu: ${chapTitle}...`);
            this.statusText.textContent = `Đang dịch lại từ đầu: ${chapTitle}...`;
            if (this.currentChapterId === chapterId) {
                const editors = this.studioParagraphs.querySelectorAll('.para-vi-editor');
                editors.forEach(ed => { ed.innerText = ''; });
                const chips = this.studioParagraphs.querySelectorAll('.para-status-chip');
                chips.forEach(ch => { ch.className = 'para-status-chip chip-pending'; ch.textContent = 'Chờ dịch'; });
            }
        } else {
            this.appendLog('info', chapterId
                ? `[Khởi động] Đang chuẩn bị dịch chương: ${chapTitle}...`
                : 'Đang chuẩn bị dịch toàn bộ sách...');
            this.statusText.textContent = 'Đang khởi động phiên dịch...';
        }

        this.startStatusPolling(this.currentProjectId);

        try {
            const res = await fetch(url, { method: 'POST' });
            const data = await res.json();
            this.appendLog(data.status === 'ok' ? 'success' : 'info', data.message);
        } catch (e) {
            this.appendLog('error', `Lỗi bắt đầu dịch: ${e.message}`);
            this.updateTranslatingStatus(false);
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

    async loadGlossary(projectId, switchToken = null) {
        try {
            const res = await fetch(`/api/projects/${projectId}/glossary`);
            if (!res.ok) throw new Error('Không thể tải bảng thuật ngữ');
            const data = await res.json();

            if (switchToken !== null && switchToken !== this._projectSwitchToken) return;
            if (this.currentProjectId !== projectId) return;

            const docType = this.normalizeDocType(this.currentProject);
            if (docType === 'paper') {
                this.toneSelect.value = 'academic';
            } else if (docType === 'novel') {
                this.toneSelect.value = (data.tone === 'academic') ? 'novel' : (data.tone || 'novel');
            } else {
                this.toneSelect.value = data.tone || 'novel';
            }

            this.customInstructions.value = data.custom_instructions || '';
            this._loadedCharacters = data.characters || [];
            this.renderCharacters(this._loadedCharacters);
            this.renderTerms(data.terms || []);
            this.btnSaveGlossary.disabled = false;
        } catch (e) {
            if (switchToken === null || switchToken === this._projectSwitchToken) {
                this.appendLog('error', `Lỗi tải bảng thuật ngữ: ${e.message}`);
            }
        }
    }

    renderCharacters(characters) {
        this.characterList.innerHTML = '';
        for (const c of characters) this.characterList.appendChild(this.createCharacterCardElement(c));
    }

    createCharacterCardElement(charData = {}) {
        const card = document.createElement('div');
        card.className = 'char-card';
        const roleText = charData.role
            ? (charData.notes ? `${charData.role} - ${charData.notes}` : charData.role)
            : (charData.notes || '');

        const row1 = document.createElement('div');
        row1.className = 'char-card-row';
        const nameInput = document.createElement('input');
        nameInput.type = 'text';
        nameInput.className = 'styled-input input-sm char-input-name';
        nameInput.placeholder = 'Tên nhân vật';
        nameInput.value = charData.name || '';
        const delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.className = 'btn-del-item';
        delBtn.title = 'Xóa nhân vật';
        delBtn.textContent = '×';
        delBtn.setAttribute('aria-label', delBtn.title);
        delBtn.addEventListener('click', () => card.remove());
        row1.appendChild(nameInput);
        row1.appendChild(delBtn);

        const row2 = document.createElement('div');
        row2.className = 'char-card-row';
        const pronounInput = document.createElement('input');
        pronounInput.type = 'text';
        pronounInput.className = 'styled-input input-sm char-input-pronoun';
        pronounInput.placeholder = 'Xưng hô: tôi - cậu / anh - em';
        pronounInput.value = charData.first_person ? `${charData.first_person} - ${charData.second_person}` : '';
        row2.appendChild(pronounInput);

        const row3 = document.createElement('div');
        row3.className = 'char-card-row';
        const roleInput = document.createElement('input');
        roleInput.type = 'text';
        roleInput.className = 'styled-input input-sm char-input-role';
        roleInput.placeholder = 'Vai trò & ghi chú xưng hô';
        roleInput.title = roleText;
        roleInput.value = roleText;
        row3.appendChild(roleInput);

        card.appendChild(row1);
        card.appendChild(row2);
        card.appendChild(row3);
        return card;
    }

    addCharacterCard() {
        const card = this.createCharacterCardElement({ name: '', first_person: 'tôi', second_person: 'cậu' });
        this.characterList.appendChild(card);
        card.querySelector('.char-input-name').focus();
    }

    renderTerms(terms) {
        this.termsList.innerHTML = '';
        for (const t of terms) this.termsList.appendChild(this.createTermCardElement(t));
    }

    createTermCardElement(termData = {}) {
        const card = document.createElement('div');
        card.className = 'term-card';

        const row = document.createElement('div');
        row.className = 'char-card-row';

        const srcInput = document.createElement('input');
        srcInput.type = 'text';
        srcInput.className = 'styled-input input-sm term-input-src';
        srcInput.placeholder = 'Từ gốc (EN)';
        srcInput.value = termData.source_term || '';
        srcInput.style.width = '45%';

        const arrow = document.createElement('span');
        arrow.textContent = '->';

        const tgtInput = document.createElement('input');
        tgtInput.type = 'text';
        tgtInput.className = 'styled-input input-sm term-input-tgt';
        tgtInput.placeholder = 'Bản dịch (VI)';
        tgtInput.value = termData.target_term || '';
        tgtInput.style.width = '45%';

        const delBtn = document.createElement('button');
        delBtn.type = 'button';
        delBtn.className = 'btn-del-item';
        delBtn.title = 'Xóa thuật ngữ';
        delBtn.textContent = '×';
        delBtn.setAttribute('aria-label', delBtn.title);
        delBtn.addEventListener('click', () => card.remove());

        row.appendChild(srcInput);
        row.appendChild(arrow);
        row.appendChild(tgtInput);
        row.appendChild(delBtn);
        card.appendChild(row);
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
        const origText = btn.textContent;
        btn.disabled = true;
        btn.textContent = 'Đang tra cứu AI...';
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
            btn.textContent = origText;
        }
    }

    async saveGlossary() {
        if (!this.currentProjectId || !this.currentProject || this.btnSaveGlossary.disabled) return;

        let characters = [];
        const isPaper = this.currentProject && this.normalizeDocType(this.currentProject) === 'paper';
        if (isPaper) {
            characters = this._loadedCharacters || [];
        } else {
            this.characterList.querySelectorAll('.char-card').forEach(card => {
                const name = card.querySelector('.char-input-name').value.trim();
                const pronounStr = card.querySelector('.char-input-pronoun').value.trim();
                const role = card.querySelector('.char-input-role').value.trim();
                if (name) {
                    const parts = pronounStr.split(/[-–\/]/).map(s => s.trim());
                    characters.push({
                        name, gender: 'unknown', role,
                        first_person: parts[0] || 'tôi',
                        second_person: parts[1] || 'cậu',
                        third_person: name, notes: ''
                    });
                }
            });
            this._loadedCharacters = characters;
        }

        const terms = [];
        this.termsList.querySelectorAll('.term-card').forEach(card => {
            const src = card.querySelector('.term-input-src').value.trim();
            const tgt = card.querySelector('.term-input-tgt').value.trim();
            if (src && tgt) terms.push({ source_term: src, target_term: tgt, category: 'general', description: '' });
        });

        const payload = {
            tone: this.toneSelect.value,
            custom_instructions: this.customInstructions.value.trim(),
            characters, terms
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

        if (this.bookFileInput) {
            this.bookFileInput.value = '';
        }

        if (this.isUploading) return;

        const fileName = (file.name || '').toLowerCase();
        const ext = fileName.includes('.') ? '.' + fileName.split('.').pop() : '';
        const allowedExts = this.uploadType === 'paper' ? ['.pdf'] : ['.epub', '.docx', '.txt', '.md'];

        if (!allowedExts.includes(ext)) {
            const expected = this.uploadType === 'paper' ? 'file PDF (.pdf)' : 'EPUB, DOCX, TXT hoặc MD';
            const msg = `Định dạng không hợp lệ. Chế độ ${this.uploadType === 'paper' ? 'Paper' : 'Novel'} chỉ nhận ${expected}.`;
            this.uploadProgressContainer.classList.remove('hidden');
            if (this.uploadProgressTrack) this.uploadProgressTrack.classList.add('hidden');
            this.uploadStatusText.textContent = msg;
            this.appendLog('error', msg);
            return;
        }

        this.isUploading = true;
        this._setUploadControlsLocked(true);

        this.uploadProgressContainer.classList.remove('hidden');
        if (this.uploadProgressTrack) this.uploadProgressTrack.classList.remove('hidden');
        this.uploadStatusText.textContent = `Đang phân tích tài liệu: ${file.name}...`;

        const formData = new FormData();
        formData.append('file', file);
        formData.append('document_type', this.uploadType);

        try {
            const res = await fetch('/api/projects/upload', { method: 'POST', body: formData });
            if (!res.ok) {
                const err = await res.json().catch(() => ({}));
                throw new Error(err.detail || 'Lỗi tải sách');
            }
            const data = await res.json();
            const isPaper = data.document_type === 'paper';
            const unitName = isPaper ? 'mục' : 'chương';
            const typeName = isPaper ? 'bài báo' : 'sách';
            this.appendLog('success', `Đã nạp thành công ${typeName}: "${data.title}" (${data.chapters_count} ${unitName}, ${data.paragraphs_count} đoạn)`);
            this.hideModal(this.uploadModal);
            this.uploadProgressContainer.classList.add('hidden');
            await this.loadProjects(data.project_id);
        } catch (e) {
            if (this.uploadProgressTrack) this.uploadProgressTrack.classList.add('hidden');
            this.uploadStatusText.textContent = `Thất bại: ${e.message}`;
            this.appendLog('error', `Lỗi tải file: ${e.message}`);
        } finally {
            this.isUploading = false;
            this._setUploadControlsLocked(false);
        }
    }

    // --- SETTINGS & EXPORT ---

    async loadSettings() {
        try {
            const res = await fetch('/api/settings');
            const data = await res.json();
            this.settingsProvider.value = data.provider || 'gemini';
            this.settingsApiKey.value = data.api_key || '';
            this.updateApiKeyCounter();
            const currentModel = data.model || 'gemini-3.5-flash';
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

        const models = {
            gemini: ['gemini-3.5-flash', 'gemini-flash-latest', 'gemini-3.6-flash', 'gemini-3.1-pro-preview'],
            deepseek: ['deepseek-chat', 'deepseek-reasoner'],
            openai: ['gpt-4o-mini', 'gpt-4o'],
            openrouter: ['deepseek/deepseek-chat', 'anthropic/claude-3.5-sonnet', 'google/gemini-2.5-flash'],
            ollama: ['qwen2.5:7b', 'qwen3.5:4b', 'qwen2.5vl:3b'],
            free_fallback: ['free-fallback']
        };
        const baseUrls = {
            deepseek: 'https://api.deepseek.com/v1',
            openrouter: 'https://openrouter.ai/api/v1',
            ollama: 'http://localhost:11434/v1'
        };
        this.groupBaseUrl.classList.toggle('hidden', !baseUrls[provider]);
        this.groupApiKey.classList.toggle('hidden', ['ollama', 'free_fallback'].includes(provider));
        if (baseUrls[provider] && selectedModel === null) {
            this.settingsBaseUrl.value = baseUrls[provider];
        }
        for (const model of models[provider] || []) {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model === 'free-fallback' ? 'Dùng thử không cần API key' : model;
            select.appendChild(option);
        }
        if (provider !== 'free_fallback') {
            const custom = document.createElement('option');
            custom.value = 'custom';
            custom.textContent = 'Nhập tên mô hình khác…';
            select.appendChild(custom);
        }
        if (this.modelHelpText) {
            this.modelHelpText.textContent = provider === 'ollama'
                ? 'Cần cài mô hình tương ứng trong Ollama trước khi sử dụng.'
                : 'Chọn mô hình tương thích với nhà cung cấp và hạn mức của bạn.';
        }

        // Set select value
        const targetModel = selectedModel || select.options[0]?.value || '';
        let found = false;
        for (const opt of select.options) {
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

    updateApiKeyCounter() {
        if (!this.settingsApiKey) return;
        const raw = this.settingsApiKey.value || '';
        const keys = raw.split(/[\n,;]+/).map(k => k.trim()).filter(k => k.length > 0);
        const badge = document.getElementById('keyCountBadge');
        const notice = document.getElementById('multiKeyNotice');
        const countSpan = document.getElementById('multiKeyCount');
        const multSpan = document.getElementById('multiKeyMultiplier');

        if (keys.length > 1) {
            if (badge) { badge.style.display = 'inline-block'; badge.textContent = `${keys.length} key`; }
            if (notice) {
                notice.style.display = 'block';
                if (countSpan) countSpan.textContent = keys.length;
                if (multSpan) multSpan.textContent = keys.length;
            }
        } else if (keys.length === 1) {
            if (badge) { badge.style.display = 'inline-block'; badge.textContent = `1 key`; }
            if (notice) notice.style.display = 'none';
        } else {
            if (badge) badge.style.display = 'none';
            if (notice) notice.style.display = 'none';
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

    async checkQuota() {
        const btn = document.getElementById('btnCheckQuota');
        const spinner = document.getElementById('quotaCheckSpinner');
        const container = document.getElementById('quotaCheckResults');
        const rawApiKey = (this.settingsApiKey.value || '').trim();

        if (!rawApiKey) {
            alert('Vui lòng dán ít nhất 1 API Key vào ô trước khi kiểm tra.');
            return;
        }

        if (btn) btn.disabled = true;
        if (spinner) spinner.style.display = 'inline-block';
        if (container) {
            container.style.display = 'block';
            container.innerHTML = '';
            const loadingDiv = document.createElement('div');
            loadingDiv.className = 'quota-message';
            loadingDiv.textContent = 'Đang kiểm tra hạn mức…';
            container.appendChild(loadingDiv);
        }

        try {
            const res = await fetch('/api/settings/check-quota', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    provider: this.settingsProvider.value,
                    api_key: rawApiKey,
                    base_url: this.settingsBaseUrl.value.trim()
                })
            });

            const data = await res.json();
            if (data.status === 'empty' || !data.keys || data.keys.length === 0) {
                container.innerHTML = '';
                const errDiv = document.createElement('div');
                errDiv.className = 'quota-error';
                errDiv.textContent = data.message || 'Không có key nào để kiểm tra.';
                container.appendChild(errDiv);
                return;
            }

            container.innerHTML = '';

            const header = document.createElement('div');
            header.className = 'quota-header';
            const titleSpan = document.createElement('span');
            titleSpan.textContent = `Kết quả kiểm tra (${data.keys.length} key)`;
            const closeBtn = document.createElement('button');
            closeBtn.type = 'button';
            closeBtn.className = 'quota-close';
            closeBtn.textContent = 'Đóng';
            closeBtn.addEventListener('click', () => { container.style.display = 'none'; });
            header.appendChild(titleSpan);
            header.appendChild(closeBtn);
            container.appendChild(header);

            data.keys.forEach(k => {
                const statusTextMap = {
                    ok: 'Sẵn sàng',
                    daily_limit: 'Hết hạn mức 24h',
                    rpm_wait: 'Chờ lượt yêu cầu',
                    error: 'Lỗi / Không hợp lệ'
                };
                const statusText = statusTextMap[k.status] || k.status || 'Không rõ';

                const keyDiv = document.createElement('div');
                keyDiv.className = 'quota-key';

                const keyHeader = document.createElement('div');
                keyHeader.className = 'quota-key-header';

                const keyLabel = document.createElement('span');
                // escapeHtml for API-returned masked_key
                keyLabel.textContent = `Key #${k.key_index} (${k.masked_key || ''})`;

                const statusSpan = document.createElement('span');
                statusSpan.className = `quota-status quota-status--${k.status || 'ok'}`;
                statusSpan.textContent = statusText;

                keyHeader.appendChild(keyLabel);
                keyHeader.appendChild(statusSpan);

                const summaryDiv = document.createElement('div');
                summaryDiv.className = 'quota-summary';
                summaryDiv.textContent = k.summary || '';

                keyDiv.appendChild(keyHeader);
                keyDiv.appendChild(summaryDiv);

                if (k.models && k.models.length > 0) {
                    const modelsDiv = document.createElement('div');
                    modelsDiv.className = 'quota-models';
                    const mStatusTextMap = { ok: 'Sẵn sàng', daily_limit: 'Hết hạn mức', rpm_wait: 'Chờ lượt', error: 'Lỗi' };
                    k.models.forEach(m => {
                        const modelSpan = document.createElement('span');
                        modelSpan.className = 'quota-model';
                        modelSpan.textContent = `${m.model}: ${mStatusTextMap[m.status] || m.text || ''}`;
                        modelsDiv.appendChild(modelSpan);
                    });
                    keyDiv.appendChild(modelsDiv);
                }

                container.appendChild(keyDiv);
            });
        } catch (e) {
            container.innerHTML = '';
            const errDiv = document.createElement('div');
            errDiv.className = 'quota-error';
            errDiv.textContent = `Lỗi kiểm tra: ${e.message}`;
            container.appendChild(errDiv);
        } finally {
            if (btn) btn.disabled = false;
            if (spinner) spinner.style.display = 'none';
        }
    }

    openSettingsModal() {
        this.updateApiKeyCounter();
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

    // --- TEXTBOOK CONVERSION ---

    resetTextbookModal() {
        if (this.textbookProgressContainer) this.textbookProgressContainer.classList.add('hidden');
        if (this.textbookSuccessBox) this.textbookSuccessBox.classList.add('hidden');
        if (this.textbookActionFooter) this.textbookActionFooter.classList.remove('hidden');
        if (this.textbookProgressBar) this.textbookProgressBar.style.width = '0%';
        if (this.textbookPercentDisplay) this.textbookPercentDisplay.textContent = '0%';
        if (this.textbookProgressContainer) this.textbookProgressContainer.setAttribute('aria-valuenow', '0');
    }

    async startTextbookConversion() {
        const file = this.textbookFileInput && this.textbookFileInput.files ? this.textbookFileInput.files[0] : null;
        const existingFilename = this.textbookExistingSelect ? this.textbookExistingSelect.value : null;

        if (!file && !existingFilename) {
            alert('Vui lòng chọn một file PDF giáo trình.');
            return;
        }

        const formData = new FormData();
        if (file) formData.append('file', file);
        else formData.append('filename', existingFilename);

        this.textbookProgressContainer.classList.remove('hidden');
        this.textbookSuccessBox.classList.add('hidden');
        this.textbookActionFooter.classList.add('hidden');
        this.textbookStatusTitle.textContent = 'Đang khởi động phân tích giáo trình...';
        this.textbookPercentDisplay.textContent = '0%';
        this.textbookProgressBar.style.width = '0%';
        this.textbookMessageDisplay.textContent = 'Đang kết nối đến server...';

        try {
            const resp = await fetch('/api/textbook/convert', { method: 'POST', body: formData });
            const data = await resp.json();
            if (!resp.ok) throw new Error(data.detail || 'Khởi động thất bại');
            this.pollTextbookProgress(data.task_id);
        } catch (err) {
            this.textbookStatusTitle.textContent = 'Lỗi!';
            this.textbookMessageDisplay.textContent = err.message;
            this.textbookActionFooter.classList.remove('hidden');
        }
    }

    pollTextbookProgress(taskId) {
        const timer = setInterval(async () => {
            try {
                const resp = await fetch(`/api/textbook/status/${taskId}`);
                if (!resp.ok) return;
                const status = await resp.json();

                const pct = status.progress || 0;
                this.textbookPercentDisplay.textContent = `${pct}%`;
                this.textbookProgressBar.style.width = `${pct}%`;
                this.textbookMessageDisplay.textContent = status.message || '';
                if (this.textbookProgressContainer) {
                    this.textbookProgressContainer.setAttribute('aria-valuenow', String(pct));
                }

                if (status.status === 'done') {
                    clearInterval(timer);
                    this.textbookProgressContainer.classList.add('hidden');
                    this.textbookSuccessBox.classList.remove('hidden');
                    this.textbookSuccessTitle.textContent = `Chuyển đổi thành công: ${status.title || 'Giáo trình'}`;
                    this.textbookSuccessMeta.textContent = `Tác giả: ${status.author || 'N/A'} | Gồm ${status.chapters_count || 0} chương, ${status.paragraphs_count || 0} đoạn.`;
                    this.btnDownloadTextbookEpub.href = `/api/textbook/export/${taskId}`;

                    if (this.btnOpenTextbookReader && status.project_id) {
                        this.btnOpenTextbookReader.onclick = async () => {
                            this.hideModal(this.textbookModal);
                            await this.loadProjects();
                            await this.selectProject(status.project_id);
                            this.switchView('reader');
                        };
                    }
                    this.loadProjects();
                } else if (status.status === 'error') {
                    clearInterval(timer);
                    this.textbookStatusTitle.textContent = 'Quá trình chuyển đổi gặp lỗi';
                    this.textbookMessageDisplay.textContent = status.message;
                    this.textbookActionFooter.classList.remove('hidden');
                }
            } catch (e) {
                console.error(e);
            }
        }, 1500);
    }

    // --- MODAL UTILS: accessible focus containment, Escape, inert ---

    _syncModalInert() {
        const top = this._modalStack[this._modalStack.length - 1];
        if (!top) {
            this._inertStates.forEach((wasInert, node) => { node.inert = wasInert; });
            this._inertStates.clear();
            return;
        }
        // Dialogs are inside #app; only their siblings may be inert.
        Array.from(document.getElementById('app').children).forEach(node => {
            if (!this._inertStates.has(node)) this._inertStates.set(node, node.inert);
            node.inert = node !== top;
        });
        this._modalStack.forEach((modal, index) => {
            modal.style.zIndex = String(100 + index);
        });
    }

    showModal(el) {
        if (!el || this._modalStack.includes(el)) return;
        el._returnFocus = document.activeElement;
        el.classList.remove('hidden');
        this._modalStack.push(el);
        this._syncModalInert();

        const card = el.querySelector('[role="dialog"]');
        if (card) {
            card.focus();
            el._trapHandler = (evt) => this._trapFocus(evt, el);
            el.addEventListener('keydown', el._trapHandler);
        }
    }

    hideModal(el) {
        if (!el) return;
        const wasTop = this._modalStack[this._modalStack.length - 1] === el;
        el.classList.add('hidden');
        el.style.removeProperty('z-index');
        const idx = this._modalStack.indexOf(el);
        if (idx !== -1) this._modalStack.splice(idx, 1);
        if (el._trapHandler) {
            el.removeEventListener('keydown', el._trapHandler);
            el._trapHandler = null;
        }
        this._syncModalInert();

        if (wasTop) {
            const top = this._modalStack[this._modalStack.length - 1];
            const target = el._returnFocus;
            if (target && target.isConnected && !target.closest('[inert]') && target.getClientRects().length) {
                target.focus();
            } else if (top) {
                top.querySelector('[role="dialog"]')?.focus();
            }
        }
        el._returnFocus = null;
    }

    _trapFocus(evt, modal) {
        if (evt.key !== 'Tab') return;
        const focusable = Array.from(modal.querySelectorAll(
            'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
        )).filter(el => el.offsetParent !== null);

        if (focusable.length === 0) {
            evt.preventDefault();
            modal.querySelector('[role="dialog"]')?.focus();
            return;
        }
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        const active = document.activeElement;
        if (!focusable.includes(active)) {
            evt.preventDefault();
            (evt.shiftKey ? last : first).focus();
        } else if (evt.shiftKey && active === first) {
            evt.preventDefault();
            last.focus();
        } else if (!evt.shiftKey && active === last) {
            evt.preventDefault();
            first.focus();
        }
    }

    escapeHtml(str) {
        if (str === null || str === undefined) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
}

// Instantiate App
let app;
window.addEventListener('DOMContentLoaded', () => {
    app = new BookTranslatorApp();
    window.app = app;
});
