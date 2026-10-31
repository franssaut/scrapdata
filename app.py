"""
Web Server & REST API untuk Dashboard Data Cipta Group
Mendukung Change Detection (Pendeteksian Data Baru), Tambah Proyek Manual,
Tambah Dokumen Baru, Riwayat Perubahan (Changelog), dan Sinkronisasi Linktree.
"""

import http.server
import json
import os
import socketserver
import sys
import threading
import time
from datetime import datetime
from urllib.parse import urlparse

import scraper

PORT = 8000
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ciptagroup_deep.json")
CSV_FILE = os.path.join(BASE_DIR, "ciptagroup_deep.csv")
MD_FILE = os.path.join(BASE_DIR, "ciptagroup_deep.md")
DATA_JS_FILE = os.path.join(BASE_DIR, "data.js")
HISTORY_FILE = os.path.join(BASE_DIR, "sync_history.json")

# Status Scraping Global
scraping_state = {
    "is_scraping": False,
    "progress": "Siap",
    "last_scraped": None,
    "new_projects_count": 0,
    "new_documents_count": 0,
    "error": None,
}


def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_history(history_list):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=2)


def record_history_entry(title, entry_type, new_projects, new_documents, items):
    history = load_history()
    entry = {
        "id": f"hist_{int(time.time())}",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "type": entry_type,
        "title": title,
        "new_projects_count": new_projects,
        "new_documents_count": new_documents,
        "items": items,
    }
    history.insert(0, entry)
    # Simpan maksimal 50 riwayat terakhir
    save_history(history[:50])
    return entry


def save_all_formats(data):
    """Menyimpan data ke JSON, CSV, MD, dan data.js secara bersamaan."""
    scraper.export_json(data, DATA_FILE)
    scraper.export_csv(data, CSV_FILE)
    scraper.export_markdown(data, MD_FILE)
    with open(DATA_JS_FILE, "w", encoding="utf-8") as f:
        f.write("window.CIPTAGROUP_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";")


def detect_changes_and_merge(existing_data, fresh_data):
    """
    Membandingkan data hasil scraping baru dengan data lama.
    Menandai 'is_new': True pada proyek baru atau dokumen baru yang belum pernah ada.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    old_projects_map = {}
    if existing_data and "links" in existing_data:
        for p in existing_data["links"]:
            # Identifikasi proyek dengan url atau title lower
            key = p.get("url", "").strip().lower() or p.get("title", "").strip().lower()
            old_projects_map[key] = p

    new_projects_added = []
    new_docs_added = []

    for p in fresh_data.get("links", []):
        pkey = p.get("url", "").strip().lower() or p.get("title", "").strip().lower()
        if pkey not in old_projects_map:
            # Proyek ini benar-benar baru!
            p["is_new"] = True
            p["created_at"] = now_str
            new_projects_added.append(p.get("title", "Proyek Baru"))
            for sub in p.get("sub_links", []):
                sub["is_new"] = True
                sub["created_at"] = now_str
                new_docs_added.append(f"{p.get('title')}: {sub.get('title')}")
        else:
            old_p = old_projects_map[pkey]
            p["is_new"] = old_p.get("is_new", False)
            p["created_at"] = old_p.get("created_at", now_str)

            # Cek sub_links untuk dokumen baru
            old_subs_map = {
                s.get("url", "").strip().lower(): s
                for s in old_p.get("sub_links", [])
            }

            has_new_sub = False
            for sub in p.get("sub_links", []):
                skey = sub.get("url", "").strip().lower()
                if skey not in old_subs_map:
                    sub["is_new"] = True
                    sub["created_at"] = now_str
                    has_new_sub = True
                    new_docs_added.append(f"{p.get('title')}: {sub.get('title')}")
                else:
                    sub["is_new"] = old_subs_map[skey].get("is_new", False)

            if has_new_sub:
                p["has_new_items"] = True

    return fresh_data, new_projects_added, new_docs_added


def run_background_scrape():
    global scraping_state
    try:
        scraping_state["is_scraping"] = True
        scraping_state["progress"] = "Mengambil data Linktree Cipta Group..."
        scraping_state["error"] = None

        existing_data = None
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    existing_data = json.load(f)
            except Exception:
                existing_data = None

        fresh_data = scraper.scrape_ciptagroup(deep=True, delay=0.5)
        if fresh_data:
            scraping_state["progress"] = "Menganalisis perbedaan & data baru..."
            merged_data, new_proj, new_docs = detect_changes_and_merge(existing_data, fresh_data)

            save_all_formats(merged_data)

            scraping_state["new_projects_count"] = len(new_proj)
            scraping_state["new_documents_count"] = len(new_docs)
            scraping_state["last_scraped"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Catat riwayat jika ada item baru
            if new_proj or new_docs:
                details = []
                for np in new_proj:
                    details.append(f"Proyek Baru: {np}")
                for nd in new_docs:
                    details.append(f"Dokumen Baru: {nd}")
                record_history_entry(
                    title="Sinkronisasi Linktree: Ditemukan Data Baru",
                    entry_type="sync_new_data",
                    new_projects=len(new_proj),
                    new_documents=len(new_docs),
                    items=details,
                )
                scraping_state["progress"] = f"Selesai! Ditemukan {len(new_proj)} proyek baru & {len(new_docs)} dokumen baru."
            else:
                record_history_entry(
                    title="Sinkronisasi Linktree: Tidak Ada Perubahan",
                    entry_type="sync_no_change",
                    new_projects=0,
                    new_documents=0,
                    items=["Semua data sudah up-to-date dengan Linktree."],
                )
                scraping_state["progress"] = "Selesai! Tidak ada data baru (sudah mutakhir)."
        else:
            scraping_state["error"] = "Gagal mengambil data dari Linktree."
    except Exception as e:
        scraping_state["error"] = str(e)
    finally:
        scraping_state["is_scraping"] = False


class CiptaGroupHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.end_headers()

    def send_json(self, status_code, payload):
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.end_headers()
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def parse_body_json(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return {}
        raw_body = self.rfile.read(content_length)
        return json.loads(raw_body.decode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)

        # GET /api/data
        if parsed.path == "/api/data":
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.send_json(200, data)
            else:
                self.send_json(404, {"error": "Data belum tersedia"})
            return

        # GET /api/status
        if parsed.path == "/api/status":
            self.send_json(200, scraping_state)
            return

        # GET /api/history
        if parsed.path == "/api/history":
            history = load_history()
            self.send_json(200, history)
            return

        super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)

        # POST /api/scrape -> Memulai sinkronisasi Linktree
        if parsed.path == "/api/scrape":
            if scraping_state["is_scraping"]:
                self.send_json(409, {"status": "busy", "message": "Scraping sedang berlangsung"})
                return

            t = threading.Thread(target=run_background_scrape, daemon=True)
            t.start()
            self.send_json(200, {"status": "started", "message": "Scraping dimulai di latar belakang"})
            return

        # POST /api/project/add -> Tambah proyek baru secara manual
        if parsed.path == "/api/project/add":
            try:
                payload = self.parse_body_json()
                title = payload.get("title", "").strip()
                url = payload.get("url", "").strip()
                sub_links = payload.get("sub_links", [])

                if not title:
                    self.send_json(400, {"error": "Nama proyek wajib diisi"})
                    return

                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Generate new ID
                existing_ids = [p.get("id", 0) for p in data.get("links", []) if isinstance(p.get("id"), int)]
                new_id = max(existing_ids, default=0) + 1
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                formatted_subs = []
                for sub in sub_links:
                    formatted_subs.append({
                        "title": sub.get("title", "").strip(),
                        "url": sub.get("url", "").strip(),
                        "type": sub.get("type", "CLASSIC"),
                        "is_new": True,
                        "created_at": now_str,
                    })

                new_project = {
                    "id": new_id,
                    "title": title,
                    "url": url or f"https://ciptagroup.com/project/{new_id}",
                    "type": "CLASSIC",
                    "position": 0,
                    "is_new": True,
                    "created_at": now_str,
                    "sub_links": formatted_subs,
                }

                # Tambahkan di posisi teratas
                data["links"].insert(0, new_project)
                save_all_formats(data)

                # Catat ke riwayat
                doc_count = len(formatted_subs)
                details = [f"Proyek Baru Ditambahkan Manual: {title}"]
                for s in formatted_subs:
                    details.append(f"Berkas: {s['title']} ({s['url']})")

                record_history_entry(
                    title=f"Proyek Baru Ditambahkan: {title}",
                    entry_type="manual_add_project",
                    new_projects=1,
                    new_documents=doc_count,
                    items=details,
                )

                self.send_json(201, {
                    "success": True,
                    "message": f"Proyek '{title}' berhasil ditambahkan!",
                    "project": new_project,
                })
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # POST /api/project/add-document -> Tambah dokumen baru ke proyek yang sudah ada
        if parsed.path == "/api/project/add-document":
            try:
                payload = self.parse_body_json()
                project_id = payload.get("project_id")
                doc_title = payload.get("title", "").strip()
                doc_url = payload.get("url", "").strip()
                doc_type = payload.get("type", "CLASSIC")

                if not project_id or not doc_title or not doc_url:
                    self.send_json(400, {"error": "Project ID, Judul dokumen, dan URL wajib diisi"})
                    return

                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                target_proj = None
                for p in data.get("links", []):
                    if str(p.get("id")) == str(project_id):
                        target_proj = p
                        break

                if not target_proj:
                    self.send_json(404, {"error": "Proyek tidak ditemukan"})
                    return

                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_sub = {
                    "title": doc_title,
                    "url": doc_url,
                    "type": doc_type,
                    "is_new": True,
                    "created_at": now_str,
                }

                if "sub_links" not in target_proj:
                    target_proj["sub_links"] = []
                target_proj["sub_links"].insert(0, new_sub)
                target_proj["has_new_items"] = True

                save_all_formats(data)

                record_history_entry(
                    title=f"Dokumen Baru Ditambahkan ke {target_proj['title']}",
                    entry_type="manual_add_doc",
                    new_projects=0,
                    new_documents=1,
                    items=[f"{target_proj['title']}: {doc_title} ({doc_url})"],
                )

                self.send_json(200, {
                    "success": True,
                    "message": f"Dokumen '{doc_title}' berhasil ditambahkan ke '{target_proj['title']}'!",
                    "document": new_sub,
                })
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        # POST /api/mark-read -> Menghapus penanda is_new
        if parsed.path == "/api/mark-read":
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)

                for p in data.get("links", []):
                    p["is_new"] = False
                    p["has_new_items"] = False
                    for sub in p.get("sub_links", []):
                        sub["is_new"] = False

                save_all_formats(data)
                self.send_json(200, {"success": True, "message": "Semua data baru telah ditandai sudah dilihat"})
            except Exception as e:
                self.send_json(500, {"error": str(e)})
            return

        self.send_json(404, {"error": "Endpoint tidak ditemukan"})


# Vercel Serverless Entrypoint (WSGI)
def app(environ, start_response):
    path = environ.get("PATH_INFO", "/")
    if path == "/api/data":
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "rb") as f:
                content = f.read()
            start_response("200 OK", [
                ("Content-Type", "application/json; charset=utf-8"),
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Methods", "GET, POST, OPTIONS"),
            ])
            return [content]
    elif path == "/api/status":
        start_response("200 OK", [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Access-Control-Allow-Origin", "*"),
        ])
        return [json.dumps(scraping_state).encode("utf-8")]
    elif path == "/api/history":
        history = load_history()
        start_response("200 OK", [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Access-Control-Allow-Origin", "*"),
        ])
        return [json.dumps(history).encode("utf-8")]

    # Serve static assets
    clean_path = path.lstrip("/").split("?")[0] or "index.html"
    filepath = os.path.join(BASE_DIR, clean_path)
    if not os.path.exists(filepath) or os.path.isdir(filepath):
        filepath = os.path.join(BASE_DIR, "index.html")

    content_type = "text/html; charset=utf-8"
    if filepath.endswith(".js"): content_type = "application/javascript; charset=utf-8"
    elif filepath.endswith(".css"): content_type = "text/css; charset=utf-8"
    elif filepath.endswith(".json"): content_type = "application/json; charset=utf-8"
    elif filepath.endswith(".csv"): content_type = "text/csv; charset=utf-8"

    try:
        with open(filepath, "rb") as f:
            body = f.read()
        start_response("200 OK", [
            ("Content-Type", content_type),
            ("Access-Control-Allow-Origin", "*"),
        ])
        return [body]
    except Exception:
        start_response("404 Not Found", [("Content-Type", "text/plain")])
        return [b"Not Found"]


application = app
handler = app


def find_available_port(start_port=8000, max_attempts=20):
    import socket
    for port in range(start_port, start_port + max_attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    return start_port


def main():
    socketserver.ThreadingTCPServer.allow_reuse_address = True
    port = find_available_port(PORT)
    server_address = ("", port)
    
    with socketserver.ThreadingTCPServer(server_address, CiptaGroupHandler) as httpd:
        print("=" * 60)
        print(f"🚀 Portal Web Cipta Group Berjalan!")
        print(f"👉 Akses Dashboard di browser: http://localhost:{port}")
        print(f"📡 API Data:    http://localhost:{port}/api/data")
        print(f"🔄 API Status:  http://localhost:{port}/api/status")
        print(f"📜 API History: http://localhost:{port}/api/history")
        print("=" * 60)
        print("Tekan Ctrl + C untuk menghentikan server.")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n[!] Server dimatikan.")


if __name__ == "__main__":
    main()
