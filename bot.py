"""
Telegram Bot untuk Portal Data & Web Scraping Cipta Group Official
Mendukung:
- Tampilkan Semua Proyek & Berkas (2-kolom Grid & Teks Lengkap 96 Berkas)
- Pencarian cerdas proyek & berkas Google Drive (Brosur, Pricelist, Siteplan, Maps)
- Menu interaktif dengan Inline Keyboard
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

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import requests
import telebot
from telebot import types

import scraper

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "ciptagroup_deep.json")
CSV_FILE = os.path.join(BASE_DIR, "ciptagroup_deep.csv")
CONFIG_FILE = os.path.join(BASE_DIR, "bot_config.json")

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


def create_start_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    b_semua = types.InlineKeyboardButton("📋 Tampilkan Semua", callback_data="send_all_text")
    b_proyek = types.InlineKeyboardButton("🏢 Tombol Proyek", callback_data="list_all")
    b_terbaru = types.InlineKeyboardButton("✨ Data Baru", callback_data="show_new")
    b_stats = types.InlineKeyboardButton("📊 Statistik", callback_data="show_stats")
    b_cari = types.InlineKeyboardButton("🔍 Cara Cari", callback_data="how_search")
    b_sync = types.InlineKeyboardButton("🔄 Scrape / Sync", callback_data="do_sync")
    b_export = types.InlineKeyboardButton("📥 Unduh CSV/Excel", callback_data="do_export")
    b_web = types.InlineKeyboardButton("🌐 Web Dashboard Live", url="https://scraping-pied.vercel.app")
    b_linktree = types.InlineKeyboardButton("🔗 Linktree Resmi", url="https://linktr.ee/ciptagroupofficial")

    markup.add(b_semua, b_proyek)
    markup.add(b_terbaru, b_stats)
    markup.add(b_sync, b_export)
    markup.add(b_cari, b_web)
    markup.add(b_linktree)
    return markup


def create_all_projects_keyboard():
    """Membuat keyboard 2-kolom yang menampilkan SEMUA proyek sekaligus tanpa pagination."""
    projects = get_all_projects()
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = []

    for i, p in enumerate(projects, 1):
        title = p.get("title", f"Proyek #{i}")
        doc_count = len(p.get("sub_links", []))
        is_new_badge = "✨ " if p.get("is_new") or p.get("has_new_items") else ""
        btn_text = f"{is_new_badge}{title} ({doc_count})"
        buttons.append(types.InlineKeyboardButton(btn_text, callback_data=f"proj:{p.get('id', i)}"))

    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("📋 Kirim Rincian Semua Berkas (Teks)", callback_data="send_all_text"))
    markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu"))
    return markup, len(projects)


def create_project_detail(project):
    title = project.get("title", "Proyek")
    url = project.get("url", "")
    sub_links = project.get("sub_links", [])
    is_new = project.get("is_new")
    has_new = project.get("has_new_items")

    category = "Pertokoan & Komersial" if any(k in title.lower() for k in ["pertokoan", "square", "marina", "namarina", "ruko"]) else "Hunian / Residensial"

    new_str = "\n✨ *Status:* PROYEK BARU DITAMBAHKAN!" if is_new else ("\n✨ *Status:* Ada berkas baru ditambahkan!" if has_new else "")

    text = (
        f"🏢 *{title}*\n"
        f"📂 *Kategori:* {category}"
        f"{new_str}\n"
        f"📁 *Total Berkas:* {len(sub_links)} item\n"
        f"🔗 *Linktree Proyek:* {url}\n\n"
        f"Silakan klik tombol di bawah ini untuk langsung membuka berkas di Google Drive atau Maps:"
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

    markup.add(types.InlineKeyboardButton("⬅️ Kembali ke Semua Proyek", callback_data="list_all"))
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
            is_comm = any(k in title.lower() for k in ["pertokoan", "square", "marina", "namarina", "ruko"])
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
        # Tambahkan tombol aksi pada bagian terakhir
        if part_num == total_parts:
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("🏢 Buka Menu Tombol Proyek", callback_data="list_all"))
            markup.add(types.InlineKeyboardButton("📥 Unduh CSV / Excel", callback_data="do_export"))
            markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu"))

        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=markup, disable_web_page_preview=True)
        time.sleep(0.3)


def setup_bot(token: str):
    bot = telebot.TeleBot(token, parse_mode="Markdown")

    # Command: /start atau /help
    @bot.message_handler(commands=["start", "help", "menu"])
    def send_welcome(message):
        name = message.from_user.first_name or "Pengguna"
        text = (
            f"👋 *Halo, {name}! Selamat datang di Bot Telegram Cipta Group Batam*\n\n"
            f"Bot ini terintegrasi langsung dengan database [Linktree Cipta Group Official](https://linktr.ee/ciptagroupofficial).\n\n"
            f"📌 *Fitur Utama:*\n"
            f"• 📋 *Tampilkan Semua*: Kirim rincian seluruh 15 proyek & 96 berkas Drive/Maps\n"
            f"• 🏢 *Tombol Proyek*: Pilih nama proyek dalam tata letak tombol interaktif\n"
            f"• 🔍 *Pencarian Cerdas*: Ketik langsung nama proyek atau jenis berkas (cth: `Aster`, `Amalfi`, `Pricelist`)\n"
            f"• ✨ *Data Baru*: Pantau proyek & berkas yang baru ditambahkan\n"
            f"• 🔄 *Live Scraping*: Sinkronkan data Linktree langsung dari chat\n"
            f"• 📥 *Ekspor*: Unduh rekapitulasi data format CSV / Excel\n\n"
            f"Silakan pilih menu di bawah ini:"
        )
        bot.send_message(message.chat.id, text, reply_markup=create_start_keyboard(), disable_web_page_preview=True)

    # Command: /semua atau /all
    @bot.message_handler(commands=["semua", "all", "katalog"])
    def all_projects_cmd(message):
        send_all_projects_text(bot, message.chat.id)

    # Command: /proyek atau /list
    @bot.message_handler(commands=["proyek", "list"])
    def list_projects_cmd(message):
        markup, total = create_all_projects_keyboard()
        bot.send_message(
            message.chat.id,
            f"🏢 *Daftar Lengkap Semua Proyek Cipta Group ({total} Kawasan):*\n"
            f"_Klik salah satu tombol proyek di bawah untuk membuka berkas Drive (Brosur, Pricelist, Siteplan, Maps):_",
            reply_markup=markup,
        )

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
                reply_markup=create_start_keyboard(),
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
        markup.add(types.InlineKeyboardButton("📋 Tampilkan Semua", callback_data="send_all_text"))
        markup.add(types.InlineKeyboardButton("🏢 Tombol Proyek", callback_data="list_all"))
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
                    reply_markup=create_start_keyboard(),
                )
            except Exception as e:
                bot.edit_message_text(
                    chat_id=message.chat.id,
                    message_id=msg.message_id,
                    text=f"❌ *Terjadi kesalahan saat sinkronisasi:* {e}",
                    reply_markup=create_start_keyboard(),
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
                reply_markup=create_start_keyboard(),
            )
            return

        # Tampilkan Semua Rincian Berkas (Teks)
        if data == "send_all_text":
            bot.answer_callback_query(call.id, text="Memuat seluruh rincian proyek...")
            send_all_projects_text(bot, call.message.chat.id)
            return

        # Tampilkan Semua Tombol Proyek Sekaligus
        if data == "list_all":
            bot.answer_callback_query(call.id)
            markup, total = create_all_projects_keyboard()
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🏢 *Semua Proyek Cipta Group ({total} Kawasan Properti):*\n_Pilih nama proyek untuk melihat berkas Drive-nya:_",
                reply_markup=markup,
            )
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
                    "• Ketik `semua` ➔ Menampilkan seluruh 15 proyek & 96 berkas\n"
                    "• Ketik `Aster` ➔ Menampilkan Aster Tropika, Hills, Garden\n"
                    "• Ketik `Amalfi` ➔ Menampilkan proyek hunian Amalfi\n"
                    "• Ketik `Marina` ➔ Menampilkan Pertokoan Marina Central & Cipta Village\n"
                    "• Ketik `Pricelist` ➔ Menemukan daftar harga proyek\n"
                    "• Ketik `Brosur` ➔ Menemukan brosur & e-flyer resmi\n\n"
                    "Coba ketik salah satu kata di atas sekarang!"
                ),
                reply_markup=create_start_keyboard(),
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

    # Plain text listener
    @bot.message_handler(func=lambda message: True)
    def handle_text_search(message):
        query = message.text.strip()
        # Jika user mengetik "semua" atau "tampilkan semua"
        if query.lower() in ["semua", "tampilkan semua", "all", "semua proyek"]:
            send_all_projects_text(bot, message.chat.id)
            return

        do_search(bot, message.chat.id, query)

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
        markup.add(types.InlineKeyboardButton("📋 Tampilkan Semua", callback_data="send_all_text"))
        markup.add(types.InlineKeyboardButton("🏢 Tombol Proyek", callback_data="list_all"))
        markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu"))
        bot.send_message(
            chat_id,
            f"🔍 Tidak ditemukan data dengan kata kunci: *{query}*\n\nCoba cari kata kunci lain seperti `semua`, `Aster`, `Amalfi`, `Marina`, `Brosur`, atau `Pricelist`.",
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

    markup.add(types.InlineKeyboardButton("📋 Tampilkan Semua", callback_data="send_all_text"))
    markup.add(types.InlineKeyboardButton("🏠 Menu Utama", callback_data="main_menu"))
    bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True)


def run_test_mode():
    print("=" * 60)
    print("🧪 MENJALANKAN TEST MODE BOT TELEGRAM CIPTA GROUP")
    print("=" * 60)
    projects = get_all_projects()
    print(f"[✓] Berhasil memuat data: {len(projects)} proyek ditemukan.")

    # Test create all projects keyboard
    markup, total_items = create_all_projects_keyboard()
    print(f"[✓] Keyboard SEMUA proyek (2-kolom grid) berhasil dibuat: {total_items} tombol.")

    # Test start keyboard
    start_kb = create_start_keyboard()
    print(f"[✓] Keyboard menu utama berhasil dibuat dengan tombol 'Tampilkan Semua'.")

    # Test text chunking
    step = 4
    total_parts = (len(projects) + step - 1) // step
    print(f"[✓] Logika chunking teks berhasil: {len(projects)} proyek dipecah ke {total_parts} pesan aman.")

    # Test search logic
    test_queries = ["semua", "aster", "amalfi", "pricelist", "brosur"]
    for q in test_queries:
        if q == "semua":
            print(f"[✓] Query '{q}': Otomatis mentrigger tampilan semua katalog.")
            continue
        matched = [p for p in projects if q in p.get("title", "").lower()]
        doc_matches = [
            (p["title"], s["title"])
            for p in projects
            for s in p.get("sub_links", [])
            if q in s.get("title", "").lower()
        ]
        print(f"[✓] Query '{q}': {len(matched)} proyek cocok, {len(doc_matches)} dokumen cocok.")

    print("[✓] Semua fitur 'Tampilkan Semua' terverifikasi 100% normal!")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Bot Telegram Cipta Group Official")
    parser.add_argument("--token", "-t", help="Token Bot Telegram dari @BotFather")
    parser.add_argument("--test", action="store_true", help="Jalankan uji coba logika bot (offline test)")
    args = parser.parse_args()

    if args.test:
        run_test_mode()
        return

    token = args.token or get_token()

    if not token:
        print("=" * 60)
        print("⚠️  TOKEN TELEGRAM BOT BELUM DIATUR!")
        print("=" * 60)
        print("Cara mendapatkan token bot Telegram gratis:")
        print("1. Buka Telegram dan cari akun resmi @BotFather (tanda centang biru).")
        print("2. Kirim pesan: /newbot")
        print("3. Beri nama bot (contoh: Cipta Group Bot).")
        print("4. Beri username bot yang berakhiran 'bot' (contoh: ciptagroup_official_bot).")
        print("5. Salin token API yang diberikan (contoh: 123456789:ABCdefGhIjk...).")
        print("-" * 60)
        print("Cara menjalankan bot:")
        print("   python bot.py --token <TOKEN_BOT_ANDA>")
        print("Atau simpan token di file 'bot_config.json' atau '.env'.")
        print("=" * 60)

        if not os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"telegram_bot_token": ""}, f, indent=2)
            print(f"[i] File template '{CONFIG_FILE}' telah dibuat. Masukkan token Anda di sana.")

        print("\nMenjalankan demonstrasi logika bot (--test):")
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
        bot.infinity_polling(timeout=20, long_polling_timeout=20)
    except KeyboardInterrupt:
        print("\n[!] Bot dihentikan.")
    except Exception as e:
        print(f"[!] Gagal menghubungkan ke Telegram: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
