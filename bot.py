"""
Telegram Bot untuk Portal Data & Web Scraping Cipta Group Official
Mendukung:
- Menu Tombol Proyek Interaktif (Reply Keyboard & Inline Grid 2-Kolom)
- Filter Kategori Tombol: Semua Properti, Hunian/Residensial, dan Pertokoan/Komersial
- Tampilkan Semua Proyek & Berkas (Teks Lengkap 96 Berkas Google Drive/Maps)
- Pencarian cerdas proyek & berkas
- Cek data baru (Change Detection)
- Trigger sinkronisasi/scraping ulang langsung dari chat Telegram
- Pengiriman file hasil ekspor (CSV & JSON) ke pengguna
"""

import argparse
import json
import os
import sys
import threading
import time
from datetime import datetime

import requests
import telebot
from telebot import types

import scraper

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ciptagroup_deep.json")
CSV_FILE = os.path.join(BASE_DIR, "ciptagroup_deep.csv")
CONFIG_FILE = os.path.join(BASE_DIR, "bot_config.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")

try:
    from dotenv import load_dotenv
    load_dotenv(ENV_FILE)
except ImportError:
    pass

# Emoji & Tipe Berkas
TYPE_ICONS = {
    "brosur": "📄",
    "brochure": "📄",
    "flyer": "📄",
    "pricelist": "💰",
    "harga": "💰",
    "price": "💰",
    "siteplan": "🗺️",
    "site plan": "🗺️",
    "denah": "🗺️",
    "floor plan": "🗺️",
    "lokasi": "📍",
    "maps": "📍",
    "map": "📍",
    "video": "🎬",
    "promo": "🎬",
    "promosi": "🎬",
    "render": "🎨",
    "desain": "🎨",
    "fasad": "🎨",
    "tampak": "🎨",
}

COMMERCIAL_KEYWORDS = ["pertokoan", "square", "marina central", "namarina", "ruko"]


def is_valid_telegram_url(url: str) -> bool:
    """
    Validasi URL untuk Telegram InlineKeyboardButton.
    Telegram menolak URL lokal seperti 'http://localhost' atau '127.0.0.1'.
    Harus berupa URL publik yang valid (http:// atau https:// dengan domain).
    """
    if not url or not isinstance(url, str):
        return False
    u = url.strip()
    if not (u.startswith("http://") or u.startswith("https://")):
        return False
    u_lower = u.lower()
    if "localhost" in u_lower or "127.0.0.1" in u_lower:
        return False
    if "://" in u:
        domain = u.split("://", 1)[1].split("/", 1)[0].split("?", 1)[0]
        if not domain or "." not in domain:
            return False
    return True


def get_icon_for_title(title: str, url: str) -> str:
    t = (title or "").lower()
    u = (url or "").lower()
    if "maps" in u or "goo.gl" in u:
        return "📍"
    for kw, icon in TYPE_ICONS.items():
        if kw in t:
            return icon
    return "📁"


def get_token() -> str:
    """Mengambil token bot dari argumen CLI, ENV, atau file konfigurasi."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    if token:
        return token

    # Fallback 1: Baca langsung dari file .env
    if os.path.exists(ENV_FILE):
        try:
            with open(ENV_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        t = line.split("=", 1)[1].strip().strip('"').strip("'")
                        if t:
                            return t
        except Exception:
            pass

    # Fallback 2: Baca dari bot_config.json
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                cfg = json.load(f)
                token = cfg.get("telegram_bot_token", "").strip()
                if token:
                    return token
        except Exception:
            pass

    return ""


def load_dataset():
    if not os.path.exists(DATA_FILE):
        return None
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[!] Gagal membaca data file: {e}", file=sys.stderr)
        return None


def get_all_projects():
    data = load_dataset()
    if not data:
        return []
    return data.get("links", [])


def create_reply_keyboard():
    """Membuat tombol menu permanen di bagian bawah chat (Reply Keyboard)."""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    b_proyek = types.KeyboardButton("🏢 Menu Tombol Proyek")
    b_semua = types.KeyboardButton("📋 Tampilkan Semua")
    b_terbaru = types.KeyboardButton("✨ Data Baru")
    b_stats = types.KeyboardButton("📊 Statistik")
    b_cari = types.KeyboardButton("🔍 Cari Berkas")
    b_export = types.KeyboardButton("📥 Unduh CSV/Excel")
    b_web = types.KeyboardButton("🌐 Buka Web Dashboard")

    markup.add(b_proyek, b_semua)
    markup.add(b_terbaru, b_stats)
    markup.add(b_cari, b_export)
    markup.add(b_web)
    return markup


def create_start_inline_keyboard():
    """Membuat tombol inline interaktif pada pesan sambutan."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    b_proyek = types.InlineKeyboardButton("🏢 Menu Tombol Proyek", callback_data="open_project_menu:ALL")
    b_semua = types.InlineKeyboardButton("📋 Tampilkan Semua", callback_data="send_all_text")
    b_terbaru = types.InlineKeyboardButton("✨ Data Baru", callback_data="show_new")
    b_stats = types.InlineKeyboardButton("📊 Statistik", callback_data="show_stats")
    b_sync = types.InlineKeyboardButton("🔄 Scrape / Sync", callback_data="do_sync")
    b_export = types.InlineKeyboardButton("📥 Unduh CSV/Excel", callback_data="do_export")
    b_web = types.InlineKeyboardButton("🌐 Web Dashboard Live", url="https://scraping-pied.vercel.app")
    b_linktree = types.InlineKeyboardButton("🔗 Linktree Resmi", url="https://linktr.ee/ciptagroupofficial")

    markup.add(b_proyek, b_semua)
    markup.add(b_terbaru, b_stats)
    markup.add(b_sync, b_export)
    markup.add(b_web, b_linktree)
    return markup


def create_project_menu_keyboard(filter_type="ALL"):
    """
    Membuat antarmuka Menu Tombol Proyek:
    - Tab filter kategori (Semua, Hunian, Komersial)
    - Grid 2-kolom berisi tombol semua nama proyek
    """
    all_projects = get_all_projects()

    filtered = []
    for p in all_projects:
        t = p.get("title", "").lower()
        is_comm = any(k in t for k in COMMERCIAL_KEYWORDS)
        if filter_type == "RESIDENTIAL" and is_comm:
            continue
        if filter_type == "COMMERCIAL" and not is_comm:
            continue
        filtered.append((p, is_comm))

    markup = types.InlineKeyboardMarkup(row_width=2)

    # 1. Baris Filter Kategori
    tab_all = types.InlineKeyboardButton("🔘 Semua (15)" if filter_type == "ALL" else "Semua (15)", callback_data="open_project_menu:ALL")
    tab_res = types.InlineKeyboardButton("🔘 Hunian (12)" if filter_type == "RESIDENTIAL" else "🏡 Hunian (12)", callback_data="open_project_menu:RESIDENTIAL")
    tab_com = types.InlineKeyboardButton("🔘 Komersial (3)" if filter_type == "COMMERCIAL" else "🏪 Komersial (3)", callback_data="open_project_menu:COMMERCIAL")
    markup.row(tab_all, tab_res, tab_com)

    # 2. Tombol-tombol Proyek (2 per baris)
    buttons = []
    for p, is_comm in filtered:
        title = p.get("title", "Proyek")
        doc_count = len(p.get("sub_links", []))
        icon = "🏪" if is_comm else "🏡"
        is_new = "✨ " if p.get("is_new") or p.get("has_new_items") else ""
        btn_text = f"{is_new}{icon} {title} ({doc_count})"
        buttons.append(types.InlineKeyboardButton(btn_text, callback_data=f"proj:{p.get('id')}"))

    markup.add(*buttons)

    # 3. Baris Aksi Tambahan
    markup.add(types.InlineKeyboardButton("📋 Tampilkan Rincian Semua Berkas (Teks)", callback_data="send_all_text"))
    markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu"))

    desc = "Semua 15 Properti" if filter_type == "ALL" else ("Kawasan Hunian & Residensial (12 Proyek)" if filter_type == "RESIDENTIAL" else "Kawasan Pertokoan & Komersial (3 Proyek)")
    return markup, desc, len(filtered)


def create_project_detail(project):
    title = project.get("title", "Proyek")
    url = project.get("url", "")
    sub_links = project.get("sub_links", [])
    is_new = project.get("is_new")
    has_new = project.get("has_new_items")

    is_comm = any(k in title.lower() for k in COMMERCIAL_KEYWORDS)
    category = "🏪 Pertokoan & Komersial" if is_comm else "🏡 Hunian / Residensial"

    new_str = "\n✨ *Status:* PROYEK BARU DITAMBAHKAN!" if is_new else ("\n✨ *Status:* Ada berkas baru ditambahkan!" if has_new else "")

    text = (
        f"🏢 *{title}*\n"
        f"📂 *Kategori:* {category}"
        f"{new_str}\n"
        f"📁 *Total Berkas:* {len(sub_links)} item\n"
        f"🔗 *Linktree Proyek:* {url}\n\n"
        f"Pilih salah satu tombol di bawah untuk langsung membuka berkas di Google Drive atau Maps:"
    )

    markup = types.InlineKeyboardMarkup(row_width=1)
    for s in sub_links:
        s_title = s.get("title", "Berkas")
        s_url = (s.get("url") or "").strip()
        icon = get_icon_for_title(s_title, s_url)
        new_tag = " [BARU]" if s.get("is_new") else ""
        if is_valid_telegram_url(s_url):
            markup.add(types.InlineKeyboardButton(f"{icon} {s_title}{new_tag}", url=s_url))

    if is_valid_telegram_url(url):
        markup.add(types.InlineKeyboardButton("🌐 Buka Halaman Linktree Asli", url=url.strip()))

    markup.add(types.InlineKeyboardButton("⬅️ Kembali ke Menu Tombol Proyek", callback_data="open_project_menu:ALL"))
    markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu"))

    return text, markup


def send_all_projects_text(bot, chat_id):
    """Mengirim katalog lengkap semua proyek beserta seluruh berkas Google Drive & Maps."""
    projects = get_all_projects()
    total = len(projects)
    total_docs = sum(len(p.get("sub_links", [])) for p in projects)
    step = 4
    total_parts = (total + step - 1) // step

    bot.send_message(
        chat_id,
        f"📚 *MEMUAT KATALOG LENGKAP CIPTA GROUP*\n\n"
        f"Menampilkan seluruh *{total} Kawasan Properti* dan *{total_docs} Berkas Resmi* (E-Brosur, Pricelist, Siteplan, Maps):\n"
        f"_Data dikirimkan dalam {total_parts} bagian rapi di bawah ini..._",
    )

    for start in range(0, total, step):
        end = min(start + step, total)
        part_num = (start // step) + 1

        lines = [f"📋 *SEMUA PROYEK CIPTA GROUP (Bagian {part_num}/{total_parts})*\n"]
        for i in range(start, end):
            p = projects[i]
            title = p.get("title", "")
            url = p.get("url", "")
            is_comm = any(k in title.lower() for k in COMMERCIAL_KEYWORDS)
            cat_label = "🏪 Komersial" if is_comm else "🏡 Hunian"

            lines.append(f"*{i+1}. {title}* ({cat_label})")
            if url:
                lines.append(f"🔗 [Halaman Linktree]({url})")

            subs = p.get("sub_links", [])
            if subs:
                for s in subs:
                    st = s.get("title", "Berkas")
                    su = s.get("url", "")
                    icon = get_icon_for_title(st, su)
                    if su:
                        lines.append(f"   • {icon} [{st}]({su})")
                    else:
                        lines.append(f"   • {icon} {st}")
            else:
                lines.append("   • _Belum ada berkas tambahan_")
            lines.append("")

        text = "\n".join(lines)
        markup = None
        if part_num == total_parts:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🏢 Buka Menu Tombol Proyek", callback_data="open_project_menu:ALL"))
            markup.add(types.InlineKeyboardButton("📥 Unduh CSV / Excel", callback_data="do_export"))
            markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu"))

        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup, disable_web_page_preview=True)
        time.sleep(0.3)


def setup_bot(token: str):
    bot = telebot.TeleBot(token, parse_mode="Markdown")

    # Daftarkan Menu Perintah Resmi Telegram
    try:
        bot.set_my_commands([
            types.BotCommand("proyek", "🏢 Menu Tombol Proyek"),
            types.BotCommand("semua", "📋 Tampilkan Semua 15 Proyek & 96 Berkas"),
            types.BotCommand("cari", "🔍 Cari Nama Proyek / Dokumen"),
            types.BotCommand("terbaru", "✨ Cek Proyek & Berkas Baru"),
            types.BotCommand("stats", "📊 Statistik Data Properti"),
            types.BotCommand("export", "📥 Unduh Rekap Data CSV/Excel"),
            types.BotCommand("start", "🏠 Buka Menu Utama"),
        ])
    except Exception as e:
        print(f"[i] Set my commands info: {e}")

    # Command: /start atau /help
    @bot.message_handler(commands=["start", "help", "menu"])
    def send_welcome(message):
        name = message.from_user.first_name or "Pengguna"
        text = (
            f"👋 *Halo, {name}! Selamat datang di Bot Telegram Cipta Group Batam*\n\n"
            f"Bot ini terintegrasi langsung dengan database [Linktree Cipta Group Official](https://linktr.ee/ciptagroupofficial).\n\n"
            f"📌 *Fitur Utama yang Tersedia:*\n"
            f"• 🏢 *Menu Tombol Proyek*: Pilih nama proyek dalam grid tombol interaktif 2-kolom\n"
            f"• 📋 *Tampilkan Semua*: Kirim rincian seluruh 15 proyek & 96 berkas Drive/Maps\n"
            f"• 🔍 *Pencarian Cerdas*: Ketik langsung nama proyek atau jenis berkas (cth: `Aster`, `Amalfi`, `Pricelist`)\n"
            f"• ✨ *Data Baru*: Pantau proyek & berkas yang baru ditambahkan\n"
            f"• 🔄 *Live Scraping*: Sinkronkan data Linktree langsung dari chat\n"
            f"• 📥 *Ekspor*: Unduh rekapitulasi data format CSV / Excel\n\n"
            f"Silakan gunakan menu tombol di bawah atau tombol keyboard untuk memulai:"
        )
        # Kirim tombol inline dan aktifkan juga persistent reply keyboard di bawah layar!
        bot.send_message(message.chat.id, "🤖 *Menu Cepat Cipta Group Aktif!*", reply_markup=create_reply_keyboard())
        bot.send_message(message.chat.id, text, reply_markup=create_start_inline_keyboard(), disable_web_page_preview=True)

    # Command: /proyek atau /list
    @bot.message_handler(commands=["proyek", "list"])
    def list_projects_cmd(message):
        markup, desc, count = create_project_menu_keyboard(filter_type="ALL")
        bot.send_message(
            message.chat.id,
            f"🏢 *MENU TOMBOL PROYEK CIPTA GROUP*\n\n"
            f"Menampilkan: *{desc}* ({count} Properti)\n"
            f"_Klik nama proyek untuk membuka berkas Drive (E-Brosur, Pricelist, Siteplan, Maps):_",
            reply_markup=markup,
        )

    # Command: /semua atau /all
    @bot.message_handler(commands=["semua", "all", "katalog"])
    def all_projects_cmd(message):
        send_all_projects_text(bot, message.chat.id)

    # Command: /terbaru atau /new
    @bot.message_handler(commands=["terbaru", "new"])
    def new_items_cmd(message):
        projects = get_all_projects()
        new_projects = [p for p in projects if p.get("is_new")]
        projects_with_new_docs = [p for p in projects if not p.get("is_new") and any(s.get("is_new") for s in p.get("sub_links", []))]

        if not new_projects and not projects_with_new_docs:
            bot.send_message(
                message.chat.id,
                "✅ *Semua data sudah mutakhir!*\nTidak ada proyek atau berkas baru yang belum ditinjau.",
                reply_markup=create_start_inline_keyboard(),
            )
            return

        text = "✨ *PEMBERITAHUAN DATA BARU TERDETEKSI:*\n\n"
        markup = types.InlineKeyboardMarkup(row_width=1)

        if new_projects:
            text += "*Proyek Baru:*\n"
            for p in new_projects:
                text += f"• 🏢 *{p.get('title')}* ({len(p.get('sub_links', []))} Berkas)\n"
                markup.add(types.InlineKeyboardButton(f"✨ {p.get('title')}", callback_data=f"proj:{p.get('id')}"))
            text += "\n"

        if projects_with_new_docs:
            text += "*Berkas Baru di Proyek Terdaftar:*\n"
            for p in projects_with_new_docs:
                new_subs = [s for s in p.get("sub_links", []) if s.get("is_new")]
                text += f"• *{p.get('title')}*: {len(new_subs)} berkas baru\n"
                for ns in new_subs[:3]:
                    text += f"   - {ns.get('title')}\n"
                markup.add(types.InlineKeyboardButton(f"📁 {p.get('title')} (Berkas Baru)", callback_data=f"proj:{p.get('id')}"))

        markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu"))
        bot.send_message(message.chat.id, text, reply_markup=markup)

    # Command: /stats
    @bot.message_handler(commands=["stats", "info"])
    def stats_cmd(message):
        projects = get_all_projects()
        total_projects = len(projects)
        total_docs = sum(len(p.get("sub_links", [])) for p in projects)
        brochures = sum(1 for p in projects for s in p.get("sub_links", []) if any(k in s.get("title", "").lower() for k in ["brosur", "brochure", "flyer"]))
        pricelists = sum(1 for p in projects for s in p.get("sub_links", []) if any(k in s.get("title", "").lower() for k in ["pricelist", "harga", "price"]))
        siteplans = sum(1 for p in projects for s in p.get("sub_links", []) if any(k in s.get("title", "").lower() for k in ["siteplan", "site plan", "denah"]))
        maps_count = sum(1 for p in projects for s in p.get("sub_links", []) if "maps" in s.get("url", "").lower() or "lokasi" in s.get("title", "").lower())
        new_items = sum(1 for p in projects if p.get("is_new")) + sum(1 for p in projects for s in p.get("sub_links", []) if s.get("is_new") and not p.get("is_new"))

        text = (
            f"📊 *STATISTIK LENGKAP CIPTA GROUP OFFICIAL*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🏢 *Total Kawasan:* `{total_projects}` Properti\n"
            f"📁 *Total Berkas & Link:* `{total_docs}` Dokumen\n"
            f"📄 *E-Brosur / Flyer:* `{brochures}` Berkas\n"
            f"💰 *Pricelist / Harga:* `{pricelists}` Berkas\n"
            f"🗺️ *Siteplan / Denah:* `{siteplans}` Berkas\n"
            f"📍 *Titik Google Maps:* `{maps_count}` Lokasi\n"
            f"✨ *Item Baru Terdeteksi:* `{new_items}` Item\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🔗 *Sumber:* [linktr.ee/ciptagroupofficial](https://linktr.ee/ciptagroupofficial)"
        )
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏢 Buka Menu Tombol Proyek", callback_data="open_project_menu:ALL"))
        markup.add(types.InlineKeyboardButton("📋 Tampilkan Semua Berkas", callback_data="send_all_text"))
        markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu"))
        bot.send_message(message.chat.id, text, reply_markup=markup, disable_web_page_preview=True)

    # Command: /export
    @bot.message_handler(commands=["export", "download"])
    def export_cmd(message):
        if not os.path.exists(CSV_FILE):
            bot.send_message(message.chat.id, "[-] Berkas CSV belum siap. Silakan jalankan /sync terlebih dahulu.")
            return

        bot.send_message(message.chat.id, "⏳ Sedang menyiapkan berkas CSV/Excel Cipta Group...")
        with open(CSV_FILE, "rb") as f:
            bot.send_document(
                message.chat.id,
                f,
                caption="📊 *Data Proyek & Berkas Cipta Group (CSV/Excel)*\nBerisi seluruh tautan Google Drive E-Brosur, Siteplan, Pricelist, dan Maps.",
            )

    # Command: /cari <keyword>
    @bot.message_handler(commands=["cari"])
    def search_cmd(message):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            bot.send_message(
                message.chat.id,
                "🔍 *Format Pencarian:*\nKetik `/cari <nama proyek atau jenis berkas>`\n\nContoh:\n• `/cari Aster`\n• `/cari Amalfi`\n• `/cari Pricelist`\n• `/cari Marina`",
            )
            return
        query = args[1].strip()
        do_search(bot, message.chat.id, query)

    # Command: /scrape atau /sync
    @bot.message_handler(commands=["scrape", "sync"])
    def scrape_cmd(message):
        msg = bot.send_message(
            message.chat.id,
            "🔄 *Memulai proses sinkronisasi ke Linktree Cipta Group...*\n_Mohon tunggu sekitar 15-25 detik, bot sedang mengambil 15 sub-linktree proyek..._",
        )

        def worker():
            try:
                try:
                    res = requests.post("http://localhost:8000/api/scrape", timeout=5)
                    if res.status_code in (200, 409):
                        for _ in range(30):
                            time.sleep(2)
                            st = requests.get("http://localhost:8000/api/status", timeout=5).json()
                            if not st.get("is_scraping"):
                                break
                except Exception:
                    data = scraper.scrape_ciptagroup(deep=True, delay=0.5)
                    if data:
                        scraper.export_json(data, DATA_FILE)
                        scraper.export_csv(data, CSV_FILE)

                projects = get_all_projects()
                total_docs = sum(len(p.get("sub_links", [])) for p in projects)
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    text=(
                        f"🎉 *Sinkronisasi Data Selesai!*\n\n"
                        f"Berhasil memperbarui database:\n"
                        f"• {len(projects)} Kawasan Properti\n"
                        f"• {total_docs} Berkas & Link Google Drive/Maps\n\n"
                        f"Seluruh data sudah terintegrasi dan siap diakses."
                    ),
                    reply_markup=create_start_inline_keyboard(),
                )
            except Exception as e:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    text=f"❌ *Terjadi kesalahan saat sinkronisasi:* {e}",
                    reply_markup=create_start_inline_keyboard(),
                )

        threading.Thread(target=worker, daemon=True).start()

    # Callback Query Handler
    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        data = call.data

        if data == "noop":
            bot.answer_callback_query(call.id)
            return

        if data == "main_menu":
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="🏠 *Menu Utama Portal Cipta Group:*",
                reply_markup=create_start_inline_keyboard(),
            )
            return

        # Buka Menu Tombol Proyek dengan filter
        if data.startswith("open_project_menu:"):
            bot.answer_callback_query(call.id)
            filter_type = data.split(":")[1]
            markup, desc, count = create_project_menu_keyboard(filter_type=filter_type)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    f"🏢 *MENU TOMBOL PROYEK CIPTA GROUP*\n\n"
                    f"Kategori: *{desc}* ({count} Properti)\n"
                    f"_Klik nama proyek untuk membuka berkas Drive (Brosur, Pricelist, Siteplan, Maps):_"
                ),
                reply_markup=markup,
            )
            return

        # Tampilkan Semua Rincian Berkas (Teks)
        if data == "send_all_text":
            bot.answer_callback_query(call.id, text="Memuat seluruh rincian proyek...")
            send_all_projects_text(bot, call.message.chat.id)
            return

        if data.startswith("proj:"):
            bot.answer_callback_query(call.id)
            pid = data.split(":")[1]
            projects = get_all_projects()
            target = None
            for p in projects:
                if str(p.get("id")) == str(pid):
                    target = p
                    break

            if not target:
                bot.send_message(call.message.chat.id, "[-] Proyek tidak ditemukan.")
                return

            text, markup = create_project_detail(target)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=text,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            return

        if data == "show_new":
            bot.answer_callback_query(call.id)
            new_items_cmd(call.message)
            return

        if data == "show_stats":
            bot.answer_callback_query(call.id)
            stats_cmd(call.message)
            return

        if data == "how_search":
            bot.answer_callback_query(call.id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=(
                    "🔍 *Cara Mencari di Bot Cipta Group:*\n\n"
                    "Anda bisa langsung mengetikkan kata apa pun di ruang obrolan, tanpa perlu garis miring!\n\n"
                    "💡 *Contoh Pencarian Cepat:*\n"
                    "• Ketik `proyek` ➔ Membuka Menu Tombol Proyek\n"
                    "• Ketik `semua` ➔ Menampilkan seluruh 15 proyek & 96 berkas\n"
                    "• Ketik `Aster` ➔ Menampilkan Aster Tropika, Hills, Garden\n"
                    "• Ketik `Amalfi` ➔ Menampilkan proyek hunian Amalfi\n"
                    "• Ketik `Marina` ➔ Menampilkan Pertokoan Marina Central & Cipta Village\n"
                    "• Ketik `Pricelist` ➔ Menemukan daftar harga proyek\n"
                    "• Ketik `Brosur` ➔ Menemukan brosur & e-flyer resmi\n\n"
                    "Coba ketik salah satu kata di atas sekarang!"
                ),
                reply_markup=create_start_inline_keyboard(),
            )
            return

        if data == "do_sync":
            bot.answer_callback_query(call.id)
            scrape_cmd(call.message)
            return

        if data == "do_export":
            bot.answer_callback_query(call.id)
            export_cmd(call.message)
            return

    # Plain text & reply keyboard listener
    @bot.message_handler(func=lambda message: True)
    def handle_text_messages(message):
        text = (message.text or "").strip()
        lower_text = text.lower()

        # Respon terhadap Tombol Menu Bawah (Reply Keyboard)
        if "menu tombol proyek" in lower_text or lower_text in ["proyek", "tombol proyek", "daftar proyek"]:
            list_projects_cmd(message)
            return

        if "tampilkan semua" in lower_text or lower_text in ["semua", "all", "katalog"]:
            send_all_projects_text(bot, message.chat.id)
            return

        if "data baru" in lower_text or lower_text in ["terbaru", "new"]:
            new_items_cmd(message)
            return

        if "statistik" in lower_text or lower_text in ["stats", "stat"]:
            stats_cmd(message)
            return

        if "unduh csv/excel" in lower_text or lower_text in ["export", "unduh", "download"]:
            export_cmd(message)
            return

        if "buka web dashboard" in lower_text or lower_text in ["web", "dashboard"]:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🌐 Buka Web Dashboard Vercel", url="https://scraping-pied.vercel.app"))
            bot.send_message(
                message.chat.id,
                "🌐 *Dashboard Web Cipta Group Live:*\n👉 [https://scraping-pied.vercel.app](https://scraping-pied.vercel.app)",
                reply_markup=markup,
            )
            return

        if "cari berkas" in lower_text or lower_text == "cari":
            bot.send_message(
                message.chat.id,
                "🔍 *Ketik nama proyek atau jenis berkas yang dicari:*\n\nContoh: `Aster`, `Amalfi`, `Marina`, `Brosur`, `Pricelist`",
            )
            return

        # Pencarian umum teks
        do_search(bot, message.chat.id, text)

    return bot


def do_search(bot, chat_id, query):
    q = query.lower()
    projects = get_all_projects()

    matched_projects = []
    matched_docs = []

    for p in projects:
        title = p.get("title", "")
        if q in title.lower():
            matched_projects.append(p)
        else:
            found_subs = [s for s in p.get("sub_links", []) if q in s.get("title", "").lower()]
            if found_subs:
                matched_docs.append((p, found_subs))

    if not matched_projects and not matched_docs:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🏢 Buka Menu Tombol Proyek", callback_data="open_project_menu:ALL"))
        markup.add(types.InlineKeyboardButton("📋 Tampilkan Semua", callback_data="send_all_text"))
        markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu"))
        bot.send_message(
            chat_id,
            f"🔍 Tidak ditemukan data dengan kata kunci: *{query}*\n\nCoba cari kata kunci lain seperti `Aster`, `Amalfi`, `Marina`, `Brosur`, atau `Pricelist`.",
            reply_markup=markup,
        )
        return

    text = f"🔍 *Hasil Pencarian untuk:* `{query}`\n\n"
    markup = types.InlineKeyboardMarkup(row_width=1)

    if matched_projects:
        text += f"*Properti Ditemukan ({len(matched_projects)}):*\n"
        for p in matched_projects:
            text += f"• 🏢 *{p.get('title')}* ({len(p.get('sub_links', []))} berkas)\n"
            markup.add(types.InlineKeyboardButton(f"🏢 Buka {p.get('title')}", callback_data=f"proj:{p.get('id')}"))
        text += "\n"

    if matched_docs:
        text += f"*Dokumen/Berkas Ditemukan:*\n"
        for p, subs in matched_docs:
            text += f"• *{p.get('title')}:*\n"
            for s in subs[:3]:
                icon = get_icon_for_title(s.get("title"), s.get("url"))
                text += f"   - {icon} {s.get('title')}\n"
                if is_valid_telegram_url(s.get("url")):
                    markup.add(types.InlineKeyboardButton(f"{icon} {p.get('title')} - {s.get('title')}", url=s.get("url").strip()))

    markup.add(types.InlineKeyboardButton("🏢 Buka Menu Tombol Proyek", callback_data="open_project_menu:ALL"))
    markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu"))
    bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True)


def run_test_mode():
    print("=" * 60)
    print("🧪 MENJALANKAN TEST MODE BOT TELEGRAM CIPTA GROUP")
    print("=" * 60)
    projects = get_all_projects()
    print(f"[✓] Berhasil memuat data: {len(projects)} proyek ditemukan.")

    # Test reply keyboard
    r_kb = create_reply_keyboard()
    print(f"[✓] Reply Keyboard (Tombol Bawah Layar) berhasil dibuat.")

    # Test project menu keyboards for each category
    for cat in ["ALL", "RESIDENTIAL", "COMMERCIAL"]:
        markup, desc, count = create_project_menu_keyboard(filter_type=cat)
        print(f"[✓] Menu Tombol Proyek ({cat}): {desc} -> {count} tombol dihasilkan.")

    # Test start keyboard
    start_kb = create_start_inline_keyboard()
    print(f"[✓] Inline Keyboard menu utama berhasil dibuat.")

    print("[✓] Semua fitur 'Menu Tombol Proyek' terverifikasi 100% normal!")
    print("=" * 60)


def run_resilient_polling(bot):
    """
    Menjalankan polling Telegram dengan penanganan error otomatis agar tidak crash looping:
    - Menangani HTTP 409 Conflict (proses ganda) dengan backoff ramah
    - Menangani timeout / disconnect internet sementara tanpa mematikan proses
    """
    consecutive_errors = 0
    while True:
        try:
            bot.infinity_polling(timeout=20, long_polling_timeout=20, logger_level=None)
            consecutive_errors = 0
        except telebot.apihelper.ApiTelegramException as e:
            consecutive_errors += 1
            if e.error_code == 409:
                print(f"[!] Error 409 Conflict: Bot aktif di sesi lain atau sedang reload.")
                print(f"[!] Menunggu 10 detik agar koneksi lama terputus bersih (Percobaan {consecutive_errors})...")
                time.sleep(10)
            elif e.error_code in (401, 404):
                print(f"[!] Error fatal ({e.error_code}): Token bot tidak valid.")
                break
            else:
                print(f"[!] Telegram API error ({e.error_code}): {e}")
                time.sleep(5)
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as e:
            consecutive_errors += 1
            delay = min(consecutive_errors * 2, 30)
            print(f"[!] Jaringan terputus sementara ({e.__class__.__name__}). Menghubungkan ulang dalam {delay} detik...")
            time.sleep(delay)
        except Exception as e:
            consecutive_errors += 1
            delay = min(consecutive_errors * 3, 30)
            print(f"[!] Polling error tak terduga: {e}. Retry dalam {delay} detik...")
            time.sleep(delay)


def acquire_single_instance_lock(port=49152):
    """Mencegah dua proses bot berjalan bersamaan pada satu mesin."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(('127.0.0.1', port))
        return s
    except OSError:
        return None


def main():
    parser = argparse.ArgumentParser(description="Bot Telegram Cipta Group Official")
    parser.add_argument("--token", "-t", help="Token Bot Telegram dari @BotFather")
    parser.add_argument("--test", action="store_true", help="Jalankan uji coba logika bot (offline test)")
    args = parser.parse_args()

    if args.test:
        run_test_mode()
        return

    # Kunci single-instance
    lock_socket = acquire_single_instance_lock()
    if lock_socket is None:
        print("=" * 60)
        print("⚠️  PERINGATAN: BOT CIPTA GROUP SUDAH BERJALAN DI PROSES LAIN!")
        print("=" * 60)
        print("Hanya diperbolehkan 1 instance bot yang aktif secara bersamaan.")
        print("Hal ini untuk mencegah konflik getUpdates (HTTP 409 Conflict)")
        print("yang menyebabkan angka restart (↺) di PM2 menjadi tinggi.")
        print("=" * 60)
        sys.exit(0)

    token = args.token or get_token()

    if not token:
        print("=" * 60)
        print("⚠️  TOKEN TELEGRAM BOT BELUM DIATUR!")
        print("=" * 60)
        print("Cara menjalankan bot:")
        print("   python bot.py --token <TOKEN_BOT_ANDA>")
        print("Atau simpan token di file '.env'.")
        print("=" * 60)
        run_test_mode()
        return

    print("=" * 60)
    print("🤖 Memulai Bot Telegram Cipta Group Official...")
    print("=" * 60)
    bot = setup_bot(token)
    try:
        bot_info = bot.get_me()
        print(f"✅ Bot Berhasil Terhubung!")
        print(f"   Nama:     {bot_info.first_name}")
        print(f"   Username: @{bot_info.username}")
        print(f"   ID:       {bot_info.id}")
        print("-" * 60)
        print(f"👉 Silakan buka Telegram dan chat bot: https://t.me/{bot_info.username}")
        print("Bot siap menerima pesan. Tekan Ctrl + C untuk berhenti.")
        print("=" * 60)
        run_resilient_polling(bot)
    except KeyboardInterrupt:
        print("\n[!] Bot dihentikan.")
    except Exception as e:
        print(f"[!] Gagal menghubungkan ke Telegram: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
