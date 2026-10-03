"""Offline API and persistence regression tests using isolated storage."""
import json
import os
import tempfile
import threading
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from core.parser import BookChapter, BookParagraph, BookProject
from server import database
from server.app import app
from server.translator_worker import TranslationWorker


class EndpointTests(unittest.TestCase):
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

    def make_project(self):
        project = BookProject(id="sample", title="Sample", chapters=[
            BookChapter(id="chap_0", title="Chapter", paragraphs=[
                BookParagraph(id="para_0", original_text="one two three")
            ])
        ])
        database.ProjectManager.save_new_project(project)
        return project

    def test_settings_and_index(self):
        response = self.client.post("/api/settings", json={
            "provider": "gemini", "api_key": "test-key", "model": "test-model"
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/settings").json()["api_key"], "test-key")
        self.assertEqual(self.client.get("/").status_code, 200)

    def test_word_count_survives_edit(self):
        self.make_project()
        response = self.client.put("/api/projects/sample/chapters/chap_0/paragraphs/para_0",
                                   json={"translated_text": "một hai ba"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/api/projects/sample").json()["total_words"], 3)
        metadata = self.client.get("/api/projects").json()[0]
        self.assertEqual(metadata["total_words"], 3)
        self.assertEqual(metadata["progress_percent"], 100)

    def test_reject_unsafe_paths(self):
        for identifier in ("..", "../outside", r"C:\outside", "bad/name"):
            with self.assertRaises(ValueError):
                database.project_path(identifier)
        with self.assertRaises(ValueError):
            database.project_path("sample", "chapters", "../../settings.json")
        self.assertEqual(self.client.get("/api/projects/bad%5Cname").status_code, 400)

    def test_atomic_write_preserves_previous_data_on_failure(self):
        filename = os.path.join(self.storage.name, "atomic.json")
        database.atomic_write_json(filename, {"value": "original"})
        with patch("server.database.os.replace", side_effect=OSError("failure")):
            with self.assertRaises(OSError):
                database.atomic_write_json(filename, {"value": "new"})
        with open(filename, encoding="utf-8") as stream:
            self.assertEqual(json.load(stream), {"value": "original"})
        self.assertEqual(os.listdir(self.storage.name), ["atomic.json"])

    def test_upload_and_empty_upload(self):
        response = self.client.post("/api/projects/upload", files={
            "file": ("../../book.txt", b"First paragraph.\n\nSecond paragraph.", "text/plain")
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["title"], "book")
        before = set(os.listdir(self.storage.name))
        response = self.client.post("/api/projects/upload", files={"file": ("empty.txt", b"")})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(set(os.listdir(self.storage.name)), before)

    def test_reject_legacy_doc_and_missing_translation(self):
        self.assertEqual(self.client.post("/api/projects/upload", files={
            "file": ("legacy.doc", b"invalid")}).status_code, 400)
        self.assertEqual(self.client.post("/api/projects/missing/translate/start").status_code, 404)

    def test_failed_parse_cleans_upload(self):
        with patch("server.app.BookParser.parse_file", side_effect=ValueError("broken book")):
            response = self.client.post("/api/projects/upload", files={"file": ("broken.epub", b"invalid")})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(os.listdir(self.storage.name), [])

    def test_missing_chapter_does_not_start_worker(self):
        self.make_project()
        with patch("server.app.worker_instance.start_translation") as start:
            response = self.client.post("/api/projects/sample/translate/start?chapter_id=missing")
        self.assertEqual(response.status_code, 404)
        start.assert_not_called()

    def test_stopping_worker_blocks_restart(self):
        worker = TranslationWorker()
        worker._active_jobs["sample"] = {"status": "running", "stop_event": threading.Event()}
        worker.stop_translation("sample")
        self.assertTrue(worker.is_running("sample"))
        self.assertTrue(worker.get_state("sample")["is_running"])
        self.assertFalse(worker.start_translation("sample"))

    def test_busy_project_cannot_be_deleted_or_edited(self):
        self.make_project()
        with patch("server.app.worker_instance.is_running", return_value=True):
            self.assertEqual(self.client.delete("/api/projects/sample").status_code, 409)
            self.assertEqual(self.client.put("/api/projects/sample/chapters/chap_0/paragraphs/para_0",
                                            json={"translated_text": "edit"}).status_code, 409)


if __name__ == "__main__":
    unittest.main()
