# Portal Data, Web Dashboard & Bot Telegram Cipta Group Official

Ekosistem terintegrasi untuk menampilkan, mencari, dan mengelola seluruh data proyek properti serta berkas dokumen [Cipta Group Official](https://linktr.ee/ciptagroupofficial) hasil web scraping otomatis, lengkap dengan **Dashboard Web Responsif** dan **Bot Telegram Interaktif**.

---

## 🤖 Bot Telegram Cipta Group (`bot.py`)

Bot Telegram interaktif yang memungkinkan pengguna mengakses seluruh data properti, brosur, pricelist, dan siteplan langsung dari aplikasi Telegram di smartphone maupun komputer.

### 📌 Fitur Unggulan Bot Telegram:
1. **Navigasi Interaktif dengan Tombol (Inline Keyboard)**:
   - Menjelajahi 15 kawasan properti dengan sistem pagination halaman (`◀️ Prev`, `Halaman X/Y`, `Next ▶️`).
   - Membuka berkas **Google Drive (E-Brosur, Pricelist, Siteplan)** dan **Google Maps** langsung dengan tombol tautan cepat.
2. **Pencarian Cerdas Tanpa Garis Miring**:
   - Cukup ketik nama proyek (cth: `Aster`, `Amalfi`, `Marina`, `Bucepark`) atau tipe berkas (cth: `Pricelist`, `Brosur`, `Siteplan`), bot otomatis menampilkan proyek dan berkas yang relevan.
3. **Pemberitahuan Data Baru (`/terbaru`)**:
   - Mendeteksi apakah ada proyek baru atau berkas tambahan baru yang ditambahkan oleh developer.
4. **Live Scraping & Sinkronisasi (`/sync` atau `/scrape`)**:
   - Memicu proses scraping ulang Linktree langsung dari chat Telegram dengan laporan hasil real-time.
5. **Kirim File Langsung (`/export`)**:
   - Mengirim berkas rekapitulasi `ciptagroup_deep.csv` (kompatibel Excel & Spreadsheet) langsung ke chat pengguna.
6. **Statistik Lengkap (`/stats`)**:
   - Rangkuman total hunian, ruko/komersial, jumlah berkas, dan titik lokasi Maps.

### 📋 Daftar Perintah Bot:

| Perintah | Fungsi |
|----------|--------|
| `/start`, `/help` | Menampilkan pesan sambutan & menu tombol utama |
| `/proyek`, `/list` | Melihat daftar seluruh kawasan properti Cipta Group |
| `/cari <keyword>` | Mencari proyek atau dokumen spesifik |
| `/terbaru`, `/new` | Menampilkan proyek & dokumen baru yang terdeteksi |
| `/stats` | Melihat statistik KPI proyek & berkas |
| `/sync`, `/scrape` | Menjalankan scraping ulang Linktree dari Telegram |
| `/export` | Mengunduh berkas data CSV / Excel ke obrolan |

---

## ⚡ Cara Menjalankan Bot Telegram

### 1. Dapatkan Token Bot Gratis dari @BotFather (Hanya 1 Menit)
1. Buka aplikasi **Telegram** di HP atau PC Anda.
2. Cari akun resmi **[@BotFather](https://t.me/BotFather)** (memiliki tanda centang biru).
3. Kirim pesan: `/newbot`
4. Masukkan nama tampilan bot (contoh: `Cipta Group Property Bot`).
5. Masukkan username bot yang berakhiran `bot` (contoh: `ciptagroup_info_bot`).
6. BotFather akan mengirimkan **Token HTTP API** (contoh: `7123456789:ABCdefGhIjk...`).

### 2. Jalankan Bot

#### Cara A: Menggunakan Argumen CLI Langsung
```bash
python bot.py --token 7123456789:ABCdefGhIjk...
```

#### Cara B: Menggunakan File `bot_config.json`
Buka file [`bot_config.json`](file:///c:/Users/user/Music/scraping/bot_config.json) dan masukkan token Anda:
```json
{
  "telegram_bot_token": "7123456789:ABCdefGhIjk..."
}
```
Lalu jalankan:
```bash
python bot.py
```

#### Cara C: Uji Coba Logika Tanpa Token (Test Mode)
```bash
python bot.py --test
```

---

## 🌐 Dashboard Web Live (Production di Vercel)

Website telah berhasil di-deploy secara publik di Vercel:
👉 **[https://scraping-pied.vercel.app](https://scraping-pied.vercel.app)**

Dashboard dapat diakses langsung secara global melalui HP, tablet, maupun komputer.

---

## 💻 Menjalankan Server Lokal (`app.py`)

Selain versi online di Vercel, server lokal juga dapat dijalankan:

```bash
python app.py
```
Akses di browser lokal: 👉 **[http://localhost:8000](http://localhost:8000)**

---

## 📁 Struktur Berkas Lengkap

```
c:\Users\user\Music\scraping\
│
├── bot.py                # Kode sumber Bot Telegram Cipta Group
├── bot_config.json       # Konfigurasi token Bot Telegram
├── .env.example          # Contoh variabel environment
│
├── index.html            # Antarmuka dashboard web utama
├── app.js                # Controller frontend & logika data baru
├── style.css             # Desain styling responsif & animasi pulse
├── data.js               # Data embedded fallback (kompatibel offline)
├── sync_history.json     # Catatan riwayat penambahan & sinkronisasi data
├── app.py                # Server backend REST API lokal & threading
│
├── scraper.py            # Engine web scraper Linktree Cipta Group
├── requirements.txt      # Dependensi (requests, pyTelegramBotAPI, python-dotenv)
├── README.md             # Panduan lengkap
│
├── ciptagroup_deep.json  # Database hasil scraping (JSON)
├── ciptagroup_deep.csv   # Berkas tabel spreadsheet (CSV)
└── ciptagroup_deep.md    # Dokumen ringkasan (Markdown)
```
