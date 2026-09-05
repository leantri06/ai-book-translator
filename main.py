"""
AI Book Translator Pro - Main Launcher.
Starts the server and automatically opens the application in your default web browser.
"""
import os
import sys
import time
import webbrowser
import threading
import uvicorn

# Add current directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from server.database import ProjectManager
from core.parser import BookParser
from core.glossary import BookGlossary


def open_browser_delayed(url: str, delay: float = 1.5):
    """Opens browser after server has started."""
    time.sleep(delay)
    print(f"\n=======================================================")
    print(f" [OK] AI Book Translator Pro dang chay tai: {url}")
    print(f" Dang mo trinh duyet web...")
    print(f"=======================================================\n")
    webbrowser.open(url)


def seed_sample_if_empty():
    """If no projects exist yet, automatically imports a sample or checks user's book directory."""
    try:
        projects = ProjectManager.list_projects()
        if not projects:
            # Check user's local novel directory if available
            sample_candidate = r"d:\books\novel\86\86 - Volume 01 [Yen Press][Kobo].epub"
            if os.path.exists(sample_candidate):
                print(f"-> Phat hien sach mau tai {sample_candidate}. Dang khoi tao du an mau...")
                proj = BookParser.parse_file(sample_candidate, "sample_86")
                glossary = BookGlossary()
                glossary.tone = "fantasy"
                # Add key characters
                glossary.add_character("Shin", "male", "Doi truong Spearhead", "toi", "cau", "cau ay", "Lanh lung, tram tinh, xunh ho voi Lena la toi - co")
                glossary.add_character("Lena", "female", "Handler One (Si quan chi huy)", "toi", "anh", "co ay", "Xung ho voi doi la toi - cac ban hoac toi - anh")
                glossary.add_term("Juggernaut", "Coi may chien dau Juggernaut", "weapon", "Xe thiet giap khong nguoi lai danh cho 86")
                glossary.add_term("Legion", "Quan doan Legion", "organization", "De che co may tu dong")
                glossary.add_term("Processors", "Quan nhan xu ly", "general", "Nhung nguoi 86 bi ep cam lai")
                ProjectManager.save_new_project(proj, glossary)
                print(f"-> Khoi tao du an mau '86 - Eighty Six' thanh cong ({proj.total_chapters} chuong)!")
    except Exception as e:
        print(f"Luu y khi khoi tao sach mau: {e}")


import socket
import urllib.request


def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Checks if a port is currently open and in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0


def is_our_server_running(url: str) -> bool:
    """Checks if the existing server on the port is AI Book Translator."""
    try:
        req = urllib.request.Request(f"{url}/api/settings", headers={"User-Agent": "BookTranslatorLauncher"})
        with urllib.request.urlopen(req, timeout=1.0) as resp:
            return resp.status == 200
    except Exception:
        return False


def find_available_port(start_port: int = 8000, max_attempts: int = 20, host: str = "127.0.0.1") -> int:
    """Finds the first available port starting from start_port."""
    for p in range(start_port, start_port + max_attempts):
        if not is_port_in_use(p, host):
            return p
    return start_port


def main():
    host = "127.0.0.1"
    default_port = 8000

    print("\n-------------------------------------------------------")
    print("   AI BOOK TRANSLATOR PRO - V2.0")
    print("   Phan mem dich sach Anh - Viet chuyen nghiep")
    print("-------------------------------------------------------")

    # Check if our server is already running on port 8000
    if is_port_in_use(default_port, host):
        if is_our_server_running(f"http://{host}:{default_port}"):
            app_url = f"http://localhost:{default_port}"
            print(f"\n[!] May chu AI Book Translator da dang chay san tai: {app_url}")
            print(f"-> Dang tu dong mo trinh duyet web...")
            webbrowser.open(app_url)
            print("\nBan co the dong cua so nay hoac giu de xem huong dan.")
            return
        else:
            print(f"Luu y: Cong {default_port} dang bi chiem boi ung dung khac. Dang tim cong thay the...")
            port = find_available_port(default_port + 1, 20, host)
    else:
        port = default_port

    app_url = f"http://localhost:{port}"

    seed_sample_if_empty()

    # Launch browser thread
    threading.Thread(target=open_browser_delayed, args=(app_url, 1.2), daemon=True).start()

    # Run Uvicorn server
    uvicorn.run("server.app:app", host=host, port=port, log_level="info", reload=False)


if __name__ == "__main__":
    main()
