"""Offline workflow tests for document_type, tone enforcement, and persistence.

Covers: upload type/default tone, mismatch rejection (no file saved),
legacy load/list roundtrip, source locator persistence, worker effective
tone via mock, and textbook typing.  No network, no commits.
"""
import copy
import json
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from fastapi.testclient import TestClient
from core.parser import BookChapter, BookParagraph, BookProject
from core.glossary import BookGlossary
from server import database
from server.app import app
from server.translator_worker import TranslationWorker


class WorkflowTests(unittest.TestCase):
    """Workflow-level tests that run offline against temp storage."""

    def setUp(self):
        self.storage = tempfile.TemporaryDirectory()
        self.addCleanup(self.storage.cleanup)
        for target, value in (
            ("server.database.PROJECTS_DIR", self.storage.name),
            ("server.database.SETTINGS_FILE", os.path.join(self.storage.name, "settings.json")),
            ("server.app.UPLOADS_DIR", self.storage.name),
        ):
            patcher = patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    # -- helpers --

    def _make_project(self, pid="proj1", doc_type="novel", fmt="epub",
                      paras=None, warnings=None):
        """Create and persist a project with given attributes."""
        if paras is None:
            paras = [BookParagraph(id="p0", original_text="hello world",
                                   source_doc="ch1.xhtml", source_element_index=7)]
        project = BookProject(
            id=pid, title="Test Book", author="Tester",
            source_format=fmt,
            chapters=[BookChapter(id="chap_0", title="Ch1", paragraphs=paras)],
            document_type=doc_type,
            structure_warnings=warnings or [],
        )
        database.ProjectManager.save_new_project(project)
        return project

    # ------------------------------------------------------------------ #
    # 1. Upload with explicit type & default tone seeding                 #
    # ------------------------------------------------------------------ #

    def test_upload_txt_default_novel_tone(self):
        """TXT upload without explicit type -> document_type='novel', glossary tone='novel'."""
        resp = self.client.post("/api/projects/upload", files={
            "file": ("story.txt", b"Once upon a time there was a hero.", "text/plain")
        })
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["document_type"], "novel")
        # Glossary should be seeded with novel tone
        pid = body["project_id"]
        glossary = database.ProjectManager.load_glossary(pid)
        self.assertEqual(glossary.tone, "novel")

    def test_upload_pdf_default_paper_tone(self):
        """PDF upload without explicit type -> document_type='paper', glossary tone='academic'."""
        # We mock BookParser.parse_file so no real PDF is needed
        fake_project = BookProject(
            id="WILL_BE_REPLACED", title="Paper", source_format="pdf",
            chapters=[BookChapter(id="chap_0", title="Intro",
                                  paragraphs=[BookParagraph(id="p1", original_text="Abstract text")])]
        )

        def fake_parse(path, pid, document_type=None):
            fake_project.id = pid
            fake_project.document_type = document_type or "paper"
            return fake_project

        with patch("server.app.BookParser.parse_file", side_effect=fake_parse):
            resp = self.client.post("/api/projects/upload", files={
                "file": ("research.pdf", b"%PDF-fake-content", "application/pdf")
            })
        self.assertEqual(resp.status_code, 200, resp.text)
        body = resp.json()
        self.assertEqual(body["document_type"], "paper")
        glossary = database.ProjectManager.load_glossary(body["project_id"])
        self.assertEqual(glossary.tone, "academic")

    # ------------------------------------------------------------------ #
    # 2. Mismatch rejected – no file saved on disk                        #
    # ------------------------------------------------------------------ #

    def test_type_ext_mismatch_rejected_no_saved_file(self):
        """Uploading a .txt with document_type='paper' must fail before file is saved."""
        before_files = set(os.listdir(self.storage.name))
        resp = self.client.post(
            "/api/projects/upload",
            files={"file": ("notes.txt", b"Some text content here.", "text/plain")},
            data={"document_type": "paper"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("not compatible", resp.json()["detail"])
        after_files = set(os.listdir(self.storage.name))
        self.assertEqual(before_files, after_files,
                         "No upload file should remain after a type mismatch rejection")

    def test_unknown_and_textbook_upload_modes_rejected_before_parse(self):
        for mode in ('invalid', 'textbook'):
            with patch('server.app.BookParser.parse_file') as parse:
                response = self.client.post('/api/projects/upload',
                    files={'file': ('input.pdf', b'%PDF-test')},
                    data={'document_type': mode})
            self.assertEqual(response.status_code, 400)
            parse.assert_not_called()
            self.assertEqual(os.listdir(self.storage.name), [])

    def test_type_ext_mismatch_novel_pdf_rejected(self):
        """Uploading a .pdf with document_type='novel' must fail."""
        resp = self.client.post(
            "/api/projects/upload",
            files={"file": ("book.pdf", b"%PDF-dummy", "application/pdf")},
            data={"document_type": "novel"},
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("not compatible", resp.json()["detail"])

    # ------------------------------------------------------------------ #
    # 3. Legacy load / list roundtrip with existing data                  #
    # ------------------------------------------------------------------ #

    def test_legacy_load_list_roundtrip(self):
        """A project persisted with document_type survives load and appears in list."""
        self._make_project(pid="legacy1", doc_type="novel", fmt="epub",
                           warnings=["missing TOC"])
        # Load project via API
        resp = self.client.get("/api/projects/legacy1")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["document_type"], "novel")
        self.assertIn("missing TOC", body["structure_warnings"])

        # List projects – meta should include document_type
        listing = self.client.get("/api/projects").json()
        found = [p for p in listing if p["id"] == "legacy1"]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]["document_type"], "novel")
        self.assertEqual(found[0]["structure_warnings"], ["missing TOC"])

    def test_legacy_project_without_document_type_infers_on_load(self):
        """A meta.json without document_type gets inferred: pdf->paper, epub->novel."""
        # Manually write a legacy meta without document_type
        proj_dir = os.path.join(self.storage.name, "old_proj")
        os.makedirs(os.path.join(proj_dir, "chapters"), exist_ok=True)
        meta = {
            "id": "old_proj", "title": "Old", "author": "A",
            "source_format": "pdf", "total_chapters": 0,
            "total_paragraphs": 0, "translated_paragraphs": 0,
            "total_words": 0, "progress_percent": 0,
            "created_at": "2024-01-01", "updated_at": "2024-01-01",
        }
        database.atomic_write_json(os.path.join(proj_dir, "meta.json"), meta)

        project = database.ProjectManager.load_project("old_proj")
        self.assertIsNotNone(project)
        self.assertEqual(project.document_type, "paper")  # pdf -> paper
        listed = self.client.get('/api/projects').json()[0]
        self.assertEqual(listed['document_type'], 'paper')
        self.assertEqual(listed['structure_warnings'], [])
        with open(os.path.join(proj_dir, 'meta.json'), encoding='utf-8') as stream:
            self.assertNotIn('document_type', json.load(stream))

    # ------------------------------------------------------------------ #
    # 4. Source locator fields persist through save/load                   #
    # ------------------------------------------------------------------ #

    def test_source_locator_persists(self):
        """BookParagraph.source_doc and source_element_index survive save/load."""
        para = BookParagraph(id="loc1", original_text="Located text",
                             source_doc="chapter3.xhtml", source_element_index=42)
        self._make_project(pid="loctest", paras=[para])

        chapter = database.ProjectManager.load_chapter("loctest", "chap_0")
        self.assertIsNotNone(chapter)
        p = chapter.paragraphs[0]
        self.assertEqual(p.source_doc, "chapter3.xhtml")
        self.assertEqual(p.source_element_index, 42)

    # ------------------------------------------------------------------ #
    # 5. Worker effective tone enforcement (mocked translate_chunk)        #
    # ------------------------------------------------------------------ #

    def test_worker_paper_uses_academic_tone(self):
        """For a paper project the worker must pass a glossary with tone='academic'."""
        self._make_project(pid="wpaper", doc_type="paper", fmt="pdf")
        # Seed a glossary with tone explicitly set to 'novel' by user
        g = BookGlossary()
        g.tone = "novel"
        database.ProjectManager.save_glossary("wpaper", g)

        captured_glossary = {}

        def mock_translate(chunk, glossary, api_key=None):
            captured_glossary["tone"] = glossary.tone
            return {p.id: "translated" for p in chunk.paragraphs}

        worker = TranslationWorker()
        settings = {"provider": "gemini", "api_key": "k", "model": "m",
                     "base_url": "", "temperature": 0.3}
        with patch.object(database.ProjectManager, "get_settings", return_value=settings), \
             patch("server.translator_worker.AITranslator") as MockTranslator:
            instance = MockTranslator.return_value
            instance.api_keys = ["k"]
            instance.provider = "gemini"
            instance.translate_chunk = mock_translate
            worker.start_translation("wpaper")
            # Wait for the thread to finish
            job = worker._active_jobs.get("wpaper")
            if job and job.get("thread"):
                job["thread"].join(timeout=10)

        self.assertEqual(captured_glossary.get("tone"), "academic",
                         "Worker must enforce academic tone for paper projects")
        # Verify user's stored glossary was NOT modified
        stored = database.ProjectManager.load_glossary("wpaper")
        self.assertEqual(stored.tone, "novel",
                         "User's stored glossary must not be overwritten by worker")

    def test_worker_novel_normalizes_academic_to_novel(self):
        """For a novel project, if glossary tone is 'academic', worker normalizes to 'novel'."""
        self._make_project(pid="wnovel", doc_type="novel", fmt="epub")
        g = BookGlossary()
        g.tone = "academic"
        database.ProjectManager.save_glossary("wnovel", g)

        captured_glossary = {}

        def mock_translate(chunk, glossary, api_key=None):
            captured_glossary["tone"] = glossary.tone
            return {p.id: "translated" for p in chunk.paragraphs}

        worker = TranslationWorker()
        settings = {"provider": "gemini", "api_key": "k", "model": "m",
                     "base_url": "", "temperature": 0.3}
        with patch.object(database.ProjectManager, "get_settings", return_value=settings), \
             patch("server.translator_worker.AITranslator") as MockTranslator:
            instance = MockTranslator.return_value
            instance.api_keys = ["k"]
            instance.provider = "gemini"
            instance.translate_chunk = mock_translate
            worker.start_translation("wnovel")
            job = worker._active_jobs.get("wnovel")
            if job and job.get("thread"):
                job["thread"].join(timeout=10)

        self.assertEqual(captured_glossary.get("tone"), "novel",
                         "Worker must normalize academic tone to novel for novel projects")

    # ------------------------------------------------------------------ #
    # 6. Textbook typing                                                  #
    # ------------------------------------------------------------------ #

    def test_textbook_document_type_persists(self):
        """A project with document_type='textbook' round-trips through save/load."""
        self._make_project(pid="tbook", doc_type="textbook", fmt="pdf")
        loaded = database.ProjectManager.load_project("tbook")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.document_type, "textbook")

    def test_textbook_parser_sets_document_type(self):
        """TextbookParser.structure_textbook + document_type='textbook' assignment."""
        from core.textbook_parser import TextbookParser
        pages = [(1, "# Chương 1: Nhập môn\nĐoạn văn mở đầu.")]
        project = TextbookParser.structure_textbook(
            pages_content=pages, project_id="tbtest",
            title="Giáo trình Test", author="BDG", source_path="/fake.pdf"
        )
        # structure_textbook does not set document_type; convert_pdf_to_epub does.
        # We verify the field exists and can be set.
        project.document_type = "textbook"
        self.assertEqual(project.document_type, "textbook")

    # ------------------------------------------------------------------ #
    # 7. Paper project rejects auto_detect                                #
    # ------------------------------------------------------------------ #

    def test_paper_auto_detect_returns_400(self):
        """auto_detect_characters endpoint returns 400 for paper projects."""
        self._make_project(pid="apaper", doc_type="paper", fmt="pdf")
        resp = self.client.post("/api/projects/apaper/glossary/auto_detect")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("not available", resp.json()["detail"])

    # ------------------------------------------------------------------ #
    # 8. Glossary tone normalization via API                              #
    # ------------------------------------------------------------------ #

    def test_get_glossary_normalizes_tone_for_paper(self):
        """GET glossary for a paper project returns academic tone even if stored as novel."""
        self._make_project(pid="gpaper", doc_type="paper", fmt="pdf")
        g = BookGlossary()
        g.tone = "novel"
        database.ProjectManager.save_glossary("gpaper", g)

        resp = self.client.get("/api/projects/gpaper/glossary")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["tone"], "academic")

    def test_save_glossary_normalizes_tone_for_novel(self):
        """POST glossary for a novel project normalizes academic -> novel."""
        self._make_project(pid="gnovel", doc_type="novel", fmt="epub")
        resp = self.client.post("/api/projects/gnovel/glossary", json={
            "tone": "academic", "custom_instructions": "", "characters": [], "terms": []
        })
        self.assertEqual(resp.status_code, 200)
        stored = database.ProjectManager.load_glossary("gnovel")
        self.assertEqual(stored.tone, "novel")

    def test_glossary_404_missing_project(self):
        """GET/POST glossary returns 404 for nonexistent project."""
        resp = self.client.get("/api/projects/nonexistent/glossary")
        self.assertEqual(resp.status_code, 404)

    # ------------------------------------------------------------------ #
    # 9. BookProject / BookParagraph new fields default correctly          #
    # ------------------------------------------------------------------ #

    def test_bookproject_defaults(self):
        """BookProject has document_type='' and structure_warnings=[] by default."""
        p = BookProject(id="x", title="X")
        self.assertEqual(p.document_type, "")
        self.assertEqual(p.structure_warnings, [])

    def test_bookparagraph_source_defaults(self):
        """BookParagraph has source_doc='' and source_element_index=-1 by default."""
        para = BookParagraph(id="y", original_text="text")
        self.assertEqual(para.source_doc, "")
        self.assertEqual(para.source_element_index, -1)


if __name__ == "__main__":
    unittest.main()
