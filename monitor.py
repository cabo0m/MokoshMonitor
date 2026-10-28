import json
import queue
import sqlite3
import threading
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
import tkinter as tk
from tkinter import ttk

ROOT = Path(__file__).resolve().parent
DB = ROOT / "monitor.db"
CONFIG = ROOT / "config.json"
DEFAULTS = {"store_url": "https://mokosh.pl", "interval_seconds": 300,
            "telegram_bot_token": "", "telegram_chat_id": ""}


def load_config():
    if not CONFIG.exists():
        CONFIG.write_text(json.dumps(DEFAULTS, indent=2), encoding="utf-8")
    return {**DEFAULTS, **json.loads(CONFIG.read_text(encoding="utf-8"))}


def product_url(link, base):
    url = urljoin(base, link)
    p = urlparse(url)
    if p.netloc.lower() != urlparse(base).netloc.lower():
        return None
    path = p.path.rstrip("/")
    if not path.startswith("/products/") or path.count("/") != 2:
        return None
    return urlunparse((p.scheme, p.netloc, path, "", "", ""))


def json_catalog(session, base):
    found = {}
    for page in range(1, 51):
        response = session.get(base + "/products.json",
                               params={"limit": 250, "page": page}, timeout=20)
        if response.status_code in (401, 403, 404):
            return None
        response.raise_for_status()
        try:
            products = response.json()["products"]
            if not isinstance(products, list):
                return None
        except (ValueError, KeyError, TypeError):
            return None
        for product in products:
            if product.get("handle") and product.get("title"):
                url = product_url("/products/" + product["handle"], base)
                if url:
                    found[url] = str(product["title"])
        if len(products) < 250:
            return found
    raise RuntimeError("Limit stron API, katalog może być niekompletny")


def html_catalog(session, base):
    found = {}
    signatures = set()
    for page in range(1, 51):
        response = session.get(base + "/collections/all",
                               params={"page": page}, timeout=20)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        main = soup.select_one("main") or soup.select_one("#MainContent")
        if main is None:
            raise RuntimeError("Nie znaleziono głównej sekcji sklepu")
        current = {}
        for link in main.select('a[href*="/products/"]'):
            url = product_url(link.get("href", ""), base)
            if not url:
                continue
            img = link.find("img")
            name = link.get_text(" ", strip=True) or (img.get("alt", "") if img else "")
            if name:
                current.setdefault(url, name[:250])
        if not current:
            if page == 1:
                raise RuntimeError("Brak produktów w HTML")
            return found
        signature = tuple(sorted(current))
        if signature in signatures:
            return found
        signatures.add(signature)
        found.update(current)
        links = main.select('a[href*="page="]')
        if not any("page=" + str(page + 1) in a.get("href", "") for a in links):
            return found
    raise RuntimeError("Limit stron HTML, katalog może być niekompletny")


def fetch_catalog(config, session=None):
    base = config["store_url"].rstrip("/")
    if urlparse(base).scheme != "https" or not urlparse(base).netloc:
        raise ValueError("Adres musi zaczynać się od https://")
    own = session is None
    s = session or requests.Session()
    s.headers.update({"User-Agent": "MokoshMonitor/1.0"})
    try:
        result = json_catalog(s, base)
        if not result:
            result = html_catalog(s, base)
        if not result:
            raise RuntimeError("Nie udało się pobrać katalogu")
        return result
    finally:
        if own:
            s.close()


def connect_db():
    conn = sqlite3.connect(DB)
    conn.execute("CREATE TABLE IF NOT EXISTS products (url TEXT PRIMARY KEY, name TEXT NOT NULL, first_seen TEXT NOT NULL)")
    conn.execute("CREATE TABLE IF NOT EXISTS checks (id INTEGER PRIMARY KEY, checked_at TEXT, count INTEGER, new_count INTEGER, status TEXT, error TEXT)")
    conn.commit()
    return conn


def save_catalog(conn, catalog):
    existing = {row[0] for row in conn.execute("SELECT url FROM products")}
    first_run = not existing
    added = [(url, name) for url, name in catalog.items() if url not in existing]
    now = datetime.now().isoformat(timespec="seconds")
    with conn:
        conn.executemany("INSERT OR IGNORE INTO products VALUES (?,?,?)",
                         [(url, name, now) for url, name in added])
        conn.execute("INSERT INTO checks(checked_at,count,new_count,status,error) VALUES (?,?,?,?,?)",
                     (now, len(catalog), 0 if first_run else len(added), "OK", None))
    return ([] if first_run else added), first_run


def telegram(config, name, url):
    token = config.get("telegram_bot_token", "").strip()
    chat = config.get("telegram_chat_id", "").strip()
    if not (token and chat):
        return False
    response = requests.post(
        "https://api.telegram.org/bot" + token + "/sendMessage",
        json={"chat_id": chat, "text": "Nowy produkt Mokosh:\n" + name + "\n" + url},
        timeout=15)
    response.raise_for_status()
    return True


class App:
    def __init__(self, root):
        self.root = root
        self.config = load_config()
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.worker = None
        root.title("Mokosh Monitor | MorenaTech")
        root.geometry("900x550")
        title = ttk.Frame(root, padding=12)
        title.pack(fill="x")
        ttk.Label(title, text="Mokosh Monitor", font=("Segoe UI", 17, "bold")).pack(side="left")
        self.status = tk.StringVar(value="Zatrzymany")
        ttk.Label(title, textvariable=self.status).pack(side="right")
        controls = ttk.Frame(root, padding=8)
        controls.pack(fill="x")
        for name, callback in [("Start", self.start), ("Stop", self.stop),
                               ("Sprawdź teraz", lambda: self.launch(True)),
                               ("Test alertu", self.test_alert),
                               ("Symuluj nowy produkt", self.simulate_product)]:
            ttk.Button(controls, text=name, command=callback).pack(side="left", padx=4)
        ttk.Label(root, text="Produkty (dwuklik otwiera sklep)", padding=8).pack(anchor="w")
        self.table = ttk.Treeview(root, columns=("date", "name", "url"), show="headings")
        for column, label, width in [("date", "Wykryto", 150), ("name", "Produkt", 300),
                                     ("url", "Adres", 400)]:
            self.table.heading(column, text=label)
            self.table.column(column, width=width)
        self.table.pack(expand=True, fill="both", padx=12)
        self.table.bind("<Double-1>", self.open_item)
        ttk.Label(root, text="Dziennik", padding=8).pack(anchor="w")
        self.logbox = tk.Text(root, height=8, state="disabled")
        self.logbox.pack(fill="x", padx=12, pady=8)
        self.refresh()
        root.after(150, self.pump)
        root.protocol("WM_DELETE_WINDOW", self.close)

    def log(self, message):
        self.logbox.configure(state="normal")
        self.logbox.insert("end", datetime.now().strftime("%H:%M:%S") + " " + message + "\n")
        self.logbox.see("end")
        self.logbox.configure(state="disabled")

    def refresh(self):
        for item in self.table.get_children():
            self.table.delete(item)
        with connect_db() as conn:
            for url, name, dt in conn.execute(
                    "SELECT url,name,first_seen FROM products ORDER BY first_seen DESC LIMIT 3000"):
                self.table.insert("", "end", values=(dt, name, url))

    def check(self):
        try:
            catalog = fetch_catalog(self.config)
            with connect_db() as conn:
                added, first = save_catalog(conn, catalog)
            self.events.put(("checked", (len(catalog), added, first)))
            for url, name in added:
                try:
                    telegram(self.config, name, url)
                except requests.RequestException as error:
                    self.events.put(("log", "Telegram: " + str(error)))
        except Exception as error:
            with connect_db() as conn:
                conn.execute("INSERT INTO checks(checked_at,status,error) VALUES (?,?,?)",
                             (datetime.now().isoformat(timespec="seconds"), "ERROR", str(error)[:1000]))
                conn.commit()
            self.events.put(("error", str(error)))

    def loop(self, once):
        while not self.stop_event.is_set():
            self.check()
            if once or self.stop_event.wait(max(30, int(self.config["interval_seconds"]))):
                break
        self.events.put(("finished", None))

    def launch(self, once=False):
        if self.worker and self.worker.is_alive():
            self.log("Kontrola już trwa")
            return
        self.config = load_config()
        self.stop_event.clear()
        self.status.set("Kontrola..." if once else "Monitoring aktywny")
        self.worker = threading.Thread(target=self.loop, args=(once,), daemon=True)
        self.worker.start()

    def start(self):
        self.launch()

    def stop(self):
        self.stop_event.set()
        self.status.set("Zatrzymywanie...")

    def simulate_product(self):
        """Offline demo: show a fictional new product without modifying SQLite."""
        stamp = datetime.now().isoformat(timespec="seconds")
        name = "[DEMO] Nowy kosmetyk testowy"
        url = "https://mokosh.pl/collections/all"
        self.table.insert("", 0, values=(stamp, name, url))
        self.log("SYMULACJA: wykryto nowy produkt: " + name)
        self.log("SYMULACJA: link: " + url + " (przykładowy, bez prawdziwego produktu)")
        self.status.set("Symulacja zakończona")

    def test_alert(self):
        self.log("TEST: produkt testowy (nie jest zapisywany w bazie)")
        def send():
            try:
                if telegram(self.config, "PRODUKT TESTOWY", "https://mokosh.pl/collections/all"):
                    self.events.put(("log", "Wysłano test Telegram"))
            except requests.RequestException as error:
                self.events.put(("error", str(error)))
        threading.Thread(target=send, daemon=True).start()

    def open_item(self, _event):
        item = self.table.focus()
        if item:
            webbrowser.open(self.table.item(item)["values"][2])

    def pump(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "checked":
                    count, added, first = value
                    self.log("Stan początkowy: " + str(count) if first else
                             "Sprawdzono: " + str(count) + ", nowe: " + str(len(added)))
                    for url, name in added:
                        self.log("NOWY: " + name + " | " + url)
                    self.refresh()
                elif kind in ("error", "log"):
                    self.log(("BŁĄD: " if kind == "error" else "") + value)
                elif kind == "finished":
                    self.status.set("Zatrzymany")
        except queue.Empty:
            pass
        self.root.after(150, self.pump)

    def close(self):
        self.stop_event.set()
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    App(window)
    window.mainloop()
