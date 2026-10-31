"""
Web Scraper untuk Linktree Cipta Group Official (https://linktr.ee/ciptagroupofficial)
Mendukung scraping profil utama serta deep-scraping ke seluruh sub-linktree proyek perumahan/komersial.
"""

import argparse
import csv
import json
import os
import re
import sys
import time
from typing import Any, Dict, List, Optional
import requests

DEFAULT_URL = "https://linktr.ee/ciptagroupofficial"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "id,en-US;q=0.9,en;q=0.8",
}


def fetch_linktree_page(url: str, session: Optional[requests.Session] = None) -> Dict[str, Any]:
    """
    Mengambil dan mem-parsing data dari sebuah halaman Linktree melalui __NEXT_DATA__.
    """
    req_session = session or requests.Session()
    
    try:
        response = req_session.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"[!] Gagal mengakses {url}: {e}", file=sys.stderr)
        return {}

    html = response.text
    match = re.search(r'<script\s+id="__NEXT_DATA__"[^>]*>(.*?)</script>', html, re.DOTALL)
    if not match:
        print(f"[!] Tag __NEXT_DATA__ tidak ditemukan pada {url}", file=sys.stderr)
        return {}

    try:
        payload = json.loads(match.group(1))
    except json.JSONDecodeError as e:
        print(f"[!] Gagal decode JSON dari {url}: {e}", file=sys.stderr)
        return {}

    page_props = payload.get("props", {}).get("pageProps", {})
    account = page_props.get("account", {})

    # Ekstraksi tautan media sosial
    raw_socials = account.get("socialLinks", [])
    social_links = [
        {"platform": item.get("type"), "url": item.get("url")}
        for item in raw_socials
        if item.get("url")
    ]

    # Ekstraksi tautan utama
    raw_links = account.get("links", [])
    links = []
    for item in raw_links:
        links.append({
            "id": item.get("id"),
            "title": item.get("title", "").strip(),
            "url": item.get("url", "").strip(),
            "type": item.get("type"),
            "position": item.get("position"),
        })

    return {
        "url": url,
        "username": account.get("username"),
        "page_title": account.get("pageTitle"),
        "description": account.get("description"),
        "avatar_url": account.get("profilePictureUrl"),
        "social_links": social_links,
        "links": links,
    }


def scrape_ciptagroup(
    base_url: str = DEFAULT_URL,
    deep: bool = False,
    delay: float = 1.0,
) -> Dict[str, Any]:
    """
    Melakukan scraping pada profil Cipta Group.
    Jika `deep=True`, akan mengambil link konten (brosur, pricelist, dll.) dari masing-masing proyek.
    """
    session = requests.Session()
    print(f"[*] Mengambil data profil utama dari: {base_url}")
    main_data = fetch_linktree_page(base_url, session=session)

    if not main_data:
        print("[-] Gagal mengambil profil utama.", file=sys.stderr)
        return {}

    print(f"[+] Berhasil mengambil profil: {main_data.get('page_title')} (@{main_data.get('username')})")
    print(f"[+] Ditemukan {len(main_data.get('links', []))} daftar proyek/tautan.")

    if deep:
        print(f"[*] Memulai deep scraping pada sub-linktree setiap proyek (delay: {delay}s)...")
        for i, link in enumerate(main_data.get("links", []), start=1):
            target_url = link.get("url", "")
            title = link.get("title", "")
            
            # Cek apakah target merupakan URL Linktree
            if "linktr.ee" in target_url:
                print(f"  [{i}/{len(main_data['links'])}] Scraping proyek: {title} ({target_url})")
                sub_data = fetch_linktree_page(target_url, session=session)
                link["sub_title"] = sub_data.get("page_title")
                link["sub_links"] = sub_data.get("links", [])
                link["sub_socials"] = sub_data.get("social_links", [])
                time.sleep(delay)
            else:
                link["sub_links"] = []

    return main_data


def export_json(data: Dict[str, Any], filepath: str) -> None:
    """Menyimpan data hasil scraping ke file JSON."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"[✓] Data JSON tersimpan di: {filepath}")


def export_csv(data: Dict[str, Any], filepath: str) -> None:
    """
    Menyimpan data hasil scraping ke file CSV (kompatibel Excel & Spreadsheet).
    """
    rows = []
    has_sublinks = any("sub_links" in l and l["sub_links"] for l in data.get("links", []))

    if has_sublinks:
        fieldnames = [
            "Project_Title",
            "Project_URL",
            "Item_Title",
            "Item_URL",
            "Item_Type",
        ]
        for proj in data.get("links", []):
            proj_title = proj.get("title")
            proj_url = proj.get("url")
            sub_links = proj.get("sub_links", [])
            if sub_links:
                for sub in sub_links:
                    rows.append({
                        "Project_Title": proj_title,
                        "Project_URL": proj_url,
                        "Item_Title": sub.get("title"),
                        "Item_URL": sub.get("url"),
                        "Item_Type": sub.get("type"),
                    })
            else:
                rows.append({
                    "Project_Title": proj_title,
                    "Project_URL": proj_url,
                    "Item_Title": "-",
                    "Item_URL": proj_url,
                    "Item_Type": proj.get("type"),
                })
    else:
        fieldnames = ["No", "Title", "URL", "Type", "Position"]
        for i, l in enumerate(data.get("links", []), start=1):
            rows.append({
                "No": i,
                "Title": l.get("title"),
                "URL": l.get("url"),
                "Type": l.get("type"),
                "Position": l.get("position"),
            })

    with open(filepath, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"[✓] Data CSV tersimpan di: {filepath}")


def export_markdown(data: Dict[str, Any], filepath: str) -> None:
    """Menyimpan ringkasan data hasil scraping ke file Markdown."""
    lines = []
    lines.append(f"# {data.get('page_title')} (@{data.get('username')})")
    lines.append(f"**URL Sumber**: [{data.get('url')}]({data.get('url')})  ")
    if data.get("description"):
        lines.append(f"**Deskripsi**: {data.get('description')}  ")
    if data.get("avatar_url"):
        lines.append(f"**Avatar**: [Lihat Foto Profil]({data.get('avatar_url')})  ")
    lines.append("")

    socials = data.get("social_links", [])
    if socials:
        lines.append("## Media Sosial")
        for s in socials:
            lines.append(f"- **{s.get('platform')}**: [{s.get('url')}]({s.get('url')})")
        lines.append("")

    links = data.get("links", [])
    lines.append(f"## Daftar Proyek & Tautan ({len(links)} item)")
    
    has_sublinks = any("sub_links" in l and l["sub_links"] for l in links)
    if has_sublinks:
        for i, proj in enumerate(links, start=1):
            lines.append(f"\n### {i}. {proj.get('title')}")
            lines.append(f"- **Linktree**: [{proj.get('url')}]({proj.get('url')})")
            sub_links = proj.get("sub_links", [])
            if sub_links:
                lines.append("- **Dokumen & Media Proyek**:")
                for item in sub_links:
                    lines.append(f"  - [{item.get('title')}]({item.get('url')})")
            else:
                lines.append("- *Tidak ada sub-dokumen tambahan.*")
    else:
        for i, l in enumerate(links, start=1):
            lines.append(f"{i}. [{l.get('title')}]({l.get('url')})")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print(f"[✓] Data Markdown tersimpan di: {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Scraper data Linktree Cipta Group Official (dan sub-proyek)."
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_URL,
        help=f"URL Linktree target (default: {DEFAULT_URL})",
    )
    parser.add_argument(
        "--deep",
        "-d",
        action="store_true",
        help="Aktifkan deep scraping untuk mengambil sub-link di setiap proyek (brosur, pricelist, render, dll.)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Jeda waktu (detik) antar request saat deep scraping (default: 1.0)",
    )
    parser.add_argument(
        "--output",
        "-o",
        default="ciptagroup_data",
        help="Prefix nama file output (default: 'ciptagroup_data')",
    )
    parser.add_argument(
        "--format",
        "-f",
        choices=["all", "json", "csv", "md"],
        default="all",
        help="Format file output (all, json, csv, md; default: all)",
    )

    args = parser.parse_args()

    results = scrape_ciptagroup(
        base_url=args.url,
        deep=args.deep,
        delay=args.delay,
    )

    if not results:
        print("[-] Scraping selesai tanpa data.")
        return

    out_prefix = args.output
    fmt = args.format

    if fmt in ("all", "json"):
        export_json(results, f"{out_prefix}.json")
    if fmt in ("all", "csv"):
        export_csv(results, f"{out_prefix}.csv")
    if fmt in ("all", "md"):
        export_markdown(results, f"{out_prefix}.md")

    print("[*] Selesai! Semua data berhasil diproses.")


if __name__ == "__main__":
    main()
