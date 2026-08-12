#!/usr/bin/env python3
"""
The Table IPTV — Config Manager
Local desktop app for editing settings.json, theme.json, content.json,
welcome.json, and artist-links.json on the VPS over SFTP — no more manual
SSH editing.

Every Save automatically downloads a timestamped backup of the CURRENT
remote file into ./backups/ before writing the new version. The Rollback
tab lets you restore any previous backup with one click.

Requires: pip install paramiko
Run:      python table_config_manager.py
"""

import json
import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog

try:
    import paramiko
except ImportError:
    paramiko = None

try:
    from github import Github, GithubException
except ImportError:
    Github = None

BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
os.makedirs(BACKUP_DIR, exist_ok=True)

REMOTE_FILES = {
    "settings.json": "settings.json",
    "theme.json": "theme.json",
    "content.json": "content.json",
    "welcome.json": "welcome.json",
    "artist-links.json": "artist-links.json",
}

FULL_SITE_FILES = [
    "index.html",
    "privacy.html",
    "dmca.html",
    "financials.html",
    "favicon.png",
    "og-image.jpg",
    "wallpaper.jpg",
    "acquisition.pdf",
] + list(REMOTE_FILES.keys())


class SFTPConnection:
    """Wraps a single SFTP session. Connect once, reuse for all reads/writes."""

    def __init__(self):
        self.client = None
        self.sftp = None
        self.remote_dir = "/var/www/html"

    def connect(self, host, port, username, password, key_path, remote_dir):
        if paramiko is None:
            raise RuntimeError("paramiko is not installed. Run: pip install paramiko")
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if key_path:
            self.client.connect(host, port=port, username=username, key_filename=key_path, timeout=10)
        else:
            self.client.connect(host, port=port, username=username, password=password, timeout=10)
        self.sftp = self.client.open_sftp()
        self.remote_dir = remote_dir.rstrip("/")

    def read_json(self, filename):
        remote_path = f"{self.remote_dir}/{filename}"
        with self.sftp.open(remote_path, "r") as f:
            return json.loads(f.read().decode("utf-8"))

    def backup_current(self, filename):
        """Download the CURRENT remote file to backups/ before overwriting it."""
        remote_path = f"{self.remote_dir}/{filename}"
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        local_name = f"{filename.replace('.json', '')}_{timestamp}.json"
        local_path = os.path.join(BACKUP_DIR, local_name)
        try:
            self.sftp.get(remote_path, local_path)
            return local_path
        except FileNotFoundError:
            return None  # remote file doesn't exist yet — nothing to back up

    def write_json(self, filename, data):
        remote_path = f"{self.remote_dir}/{filename}"
        content = json.dumps(data, indent=2, ensure_ascii=False)
        with self.sftp.open(remote_path, "w") as f:
            f.write(content)

    def close(self):
        if self.sftp:
            self.sftp.close()
        if self.client:
            self.client.close()

    def backup_full_site(self, files):
        """Download every file in `files` into one timestamped snapshot folder."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        snapshot_dir = os.path.join(BACKUP_DIR, f"full_site_{timestamp}")
        os.makedirs(snapshot_dir, exist_ok=True)
        got_any = False
        for filename in files:
            remote_path = f"{self.remote_dir}/{filename}"
            local_path = os.path.join(snapshot_dir, filename)
            try:
                self.sftp.get(remote_path, local_path)
                got_any = True
            except FileNotFoundError:
                pass  # that file doesn't exist on the server — skip it, not fatal
        if not got_any:
            os.rmdir(snapshot_dir)
            return None
        return snapshot_dir

    def restore_full_site(self, snapshot_dir):
        """Upload every file found in a snapshot folder back to its live location."""
        restored = []
        for filename in os.listdir(snapshot_dir):
            local_path = os.path.join(snapshot_dir, filename)
            remote_path = f"{self.remote_dir}/{filename}"
            self.sftp.put(local_path, remote_path)
            restored.append(filename)
        return restored


conn = SFTPConnection()


def save_with_backup(filename, data, status_label):
    """Standard save flow used by every tab: backup current, then write new."""
    try:
        backup_path = conn.backup_current(filename)
        conn.write_json(filename, data)
        msg = f"Saved {filename}."
        if backup_path:
            msg += f" Backup: {os.path.basename(backup_path)}"
        status_label.config(text=msg, fg="#2a7a2a")
    except Exception as e:
        status_label.config(text=f"Save FAILED: {e}", fg="#a02020")
        messagebox.showerror("Save failed", str(e))


# ---------------------------------------------------------------------------
# Connection tab
# ---------------------------------------------------------------------------
class ConnectionTab(ttk.Frame):
    def __init__(self, parent, on_connected):
        super().__init__(parent, padding=16)
        self.on_connected = on_connected

        ttk.Label(self, text="VPS Connection", font=("Segoe UI", 12, "bold")).grid(row=0, column=0, columnspan=2, pady=(0, 12), sticky="w")

        self.host = self._field("Host / IP", "144.217.87.246", 1)
        self.port = self._field("Port", "22", 2)
        self.username = self._field("Username", "ubuntu", 3)

        ttk.Label(self, text="Auth method").grid(row=4, column=0, sticky="w", pady=4)
        self.auth_mode = tk.StringVar(value="key")
        auth_frame = ttk.Frame(self)
        auth_frame.grid(row=4, column=1, sticky="w")
        ttk.Radiobutton(auth_frame, text="SSH Key", variable=self.auth_mode, value="key").pack(side="left")
        ttk.Radiobutton(auth_frame, text="Password", variable=self.auth_mode, value="password").pack(side="left", padx=(12, 0))

        self.key_path = self._field("Key file path", "", 5)
        ttk.Button(self, text="Browse...", command=self._browse_key).grid(row=5, column=2, padx=(6, 0))

        self.password = self._field("Password", "", 6, show="*")

        self.remote_dir = self._field("Remote directory", "/var/www/html", 7)

        self.status = tk.Label(self, text="Not connected", fg="#888")
        self.status.grid(row=9, column=0, columnspan=2, pady=(12, 0), sticky="w")

        ttk.Button(self, text="Connect", command=self._connect).grid(row=8, column=0, pady=(16, 0), sticky="w")

    def _field(self, label, default, row, show=None):
        ttk.Label(self, text=label).grid(row=row, column=0, sticky="w", pady=4)
        var = tk.StringVar(value=default)
        entry = ttk.Entry(self, textvariable=var, width=36, show=show or "")
        entry.grid(row=row, column=1, sticky="w", pady=4)
        return var

    def _browse_key(self):
        path = filedialog.askopenfilename(title="Select SSH private key")
        if path:
            self.key_path.set(path)

    def _connect(self):
        try:
            port = int(self.port.get())
            key_path = self.key_path.get().strip() or None
            password = self.password.get() if not key_path else None
            conn.connect(
                host=self.host.get().strip(),
                port=port,
                username=self.username.get().strip(),
                password=password,
                key_path=key_path,
                remote_dir=self.remote_dir.get().strip(),
            )
            self.status.config(text="Connected.", fg="#2a7a2a")
            self.on_connected()
        except Exception as e:
            self.status.config(text=f"Connection failed: {e}", fg="#a02020")
            messagebox.showerror("Connection failed", str(e))


# ---------------------------------------------------------------------------
# Settings tab
# ---------------------------------------------------------------------------
class SettingsTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=16)
        self.data = None
        self.vars = {}

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Load from VPS", command=self.load).pack(side="left")
        ttk.Button(top, text="Save (with backup)", command=self.save).pack(side="left", padx=(8, 0))
        ttk.Button(top, text="Push Channel to Everyone", command=self.push_channel_to_everyone).pack(side="left", padx=(8, 0))
        self.status = tk.Label(top, text="Not loaded", fg="#888")
        self.status.pack(side="left", padx=(16, 0))

        canvas = tk.Canvas(self, borderwidth=0)
        scroll = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)
        self.inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.pack(side="left", fill="both", expand=True, pady=(12, 0))
        scroll.pack(side="right", fill="y", pady=(12, 0))

    def _row(self, parent, label, key, row, is_int=False):
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="w", pady=2, padx=(0, 8))
        var = tk.StringVar()
        ttk.Entry(parent, textvariable=var, width=20).grid(row=row, column=1, sticky="w", pady=2)
        self.vars[key] = (var, is_int)
        return row + 1

    def load(self):
        try:
            self.data = conn.read_json("settings.json")
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            return

        for w in self.inner.winfo_children():
            w.destroy()
        self.vars = {}

        r = 0
        ttk.Label(self.inner, text="Video", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="w", pady=(4, 2)); r += 1
        r = self._row(self.inner, "cacheOffsetSeconds", "video.cacheOffsetSeconds", r, True)
        r = self._row(self.inner, "maxRecent", "video.maxRecent", r, True)
        r = self._row(self.inner, "coldStartMaxAttempts", "video.coldStartMaxAttempts", r, True)
        r = self._row(self.inner, "coldStartIntervalMs", "video.coldStartIntervalMs", r, True)
        r = self._row(self.inner, "channelNumber", "video.channelNumber", r, False)
        r = self._row(self.inner, "streamBaseUrl", "video.streamBaseUrl", r, False)
        r = self._row(self.inner, "idleTimeoutMinutes (NEW — see note below)", "video.idleTimeoutMinutes", r, True)

        ttk.Label(self.inner, text="UI", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="w", pady=(10, 2)); r += 1
        r = self._row(self.inner, "wishlistMax", "ui.wishlistMax", r, True)
        r = self._row(self.inner, "communityTopMax", "ui.communityTopMax", r, True)
        r = self._row(self.inner, "recentlyPlayedMax", "ui.recentlyPlayedMax", r, True)

        ttk.Label(self.inner, text="API", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="w", pady=(10, 2)); r += 1
        r = self._row(self.inner, "base", "api.base", r, False)
        r = self._row(self.inner, "topLimit", "api.topLimit", r, True)
        r = self._row(self.inner, "refreshIntervalMs", "api.refreshIntervalMs", r, True)

        ttk.Label(self.inner, text="EPG", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="w", pady=(10, 2)); r += 1
        r = self._row(self.inner, "url", "epg.url", r, False)
        ttk.Label(self.inner, text="acronyms (comma-separated)").grid(row=r, column=0, sticky="w", pady=2, padx=(0, 8))
        self.acronyms_var = tk.StringVar(value=", ".join(self.data.get("epg", {}).get("acronyms", [])))
        ttk.Entry(self.inner, textvariable=self.acronyms_var, width=50).grid(row=r, column=1, sticky="w", pady=2); r += 1

        for browser in ("chrome", "firefox", "safari"):
            ttk.Label(self.inner, text=f"HLS — {browser}", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="w", pady=(10, 2)); r += 1
            hls = self.data.get("hls", {}).get(browser, {})
            for k, val in hls.items():
                is_int = isinstance(val, (int, float)) and not isinstance(val, bool)
                r = self._row(self.inner, k, f"hls.{browser}.{k}", r, is_int)

        self._populate_from_data()
        self.status.config(text="Loaded.", fg="#2a7a2a")

    def _populate_from_data(self):
        def get_nested(d, path):
            for p in path.split("."):
                if not isinstance(d, dict) or p not in d:
                    return ""
                d = d[p]
            return d

        for key, (var, _) in self.vars.items():
            val = get_nested(self.data, key)
            var.set(str(val) if val != "" else "")

    def _write_form_into_data(self):
        """Reads every form field back into self.data. Shared by both the
        normal Save button and Push Channel to Everyone, so the two never
        drift out of sync with each other."""
        def set_nested(d, path, value):
            parts = path.split(".")
            for p in parts[:-1]:
                d = d.setdefault(p, {})
            d[parts[-1]] = value

        for key, (var, is_int) in self.vars.items():
            raw = var.get().strip()
            if raw == "":
                continue
            try:
                value = int(raw) if is_int else raw
            except ValueError:
                try:
                    value = float(raw)
                except ValueError:
                    value = raw
            set_nested(self.data, key, value)

        acronyms = [a.strip().lower() for a in self.acronyms_var.get().split(",") if a.strip()]
        self.data.setdefault("epg", {})["acronyms"] = acronyms

    def save(self):
        if self.data is None:
            messagebox.showwarning("Nothing loaded", "Load settings.json first.")
            return
        self._write_form_into_data()
        save_with_backup("settings.json", self.data, self.status)

    def push_channel_to_everyone(self):
        """Saves current settings AND bumps forceReloadSignal — every
        connected viewer's browser (already polling settings.json every
        2 minutes) will notice the change and do a full page reload,
        picking up the Channel Number shown above. Not instant — up to a
        2-minute delay per viewer — but the same reliability as a manual
        F5, just triggered remotely."""
        if self.data is None:
            messagebox.showwarning("Nothing loaded", "Load settings.json first.")
            return
        if not messagebox.askyesno(
            "Push channel to everyone",
            "This saves your current settings AND forces every connected "
            "viewer's browser to reload within ~2 minutes, picking up the "
            "Channel Number shown above.\n\nContinue?",
        ):
            return
        import time
        self._write_form_into_data()
        self.data["forceReloadSignal"] = int(time.time())
        save_with_backup("settings.json", self.data, self.status)


# ---------------------------------------------------------------------------
# Theme tab
# ---------------------------------------------------------------------------
class ThemeTab(ttk.Frame):
    COLOR_KEYS = ["--frame-bg", "--knob-color", "--accent-glow", "--text-light", "--page-bg", "--highlight"]
    FONT_KEYS = ["--font-base", "--font-mono", "--font-serif"]
    PLAYER_KEYS = ["border-color", "border-width", "border-radius", "shadow", "screen-border", "screen-radius"]

    def __init__(self, parent):
        super().__init__(parent, padding=16)
        self.data = None

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Load from VPS", command=self.load).pack(side="left")
        ttk.Button(top, text="Save theme edits (with backup)", command=self.save).pack(side="left", padx=(8, 0))
        self.status = tk.Label(top, text="Not loaded", fg="#888")
        self.status.pack(side="left", padx=(16, 0))

        picker_row = ttk.Frame(self)
        picker_row.pack(fill="x", pady=(12, 4))
        ttk.Label(picker_row, text="Active theme (live on site):").pack(side="left")
        self.active_theme = tk.StringVar()
        self.active_dropdown = ttk.Combobox(picker_row, textvariable=self.active_theme, state="readonly", width=24)
        self.active_dropdown.pack(side="left", padx=(6, 0))
        ttk.Button(picker_row, text="Set as active + Save", command=self.set_active).pack(side="left", padx=(8, 0))

        edit_row = ttk.Frame(self)
        edit_row.pack(fill="x", pady=(8, 12))
        ttk.Label(edit_row, text="Edit theme:").pack(side="left")
        self.edit_theme = tk.StringVar()
        self.edit_dropdown = ttk.Combobox(edit_row, textvariable=self.edit_theme, state="readonly", width=24)
        self.edit_dropdown.pack(side="left", padx=(6, 0))
        self.edit_dropdown.bind("<<ComboboxSelected>>", lambda e: self._load_theme_into_form())

        self.form = ttk.Frame(self)
        self.form.pack(fill="both", expand=True)
        self.color_vars = {}
        self.font_vars = {}
        self.player_vars = {}

    def load(self):
        try:
            self.data = conn.read_json("theme.json")
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            return

        names = list(self.data.get("themes", {}).keys())
        self.active_dropdown["values"] = names
        self.edit_dropdown["values"] = names
        self.active_theme.set(self.data.get("theme", names[0] if names else ""))
        if names:
            self.edit_theme.set(names[0])
            self._load_theme_into_form()
        self.status.config(text="Loaded.", fg="#2a7a2a")

    def _load_theme_into_form(self):
        for w in self.form.winfo_children():
            w.destroy()
        theme = self.data["themes"][self.edit_theme.get()]
        r = 0

        ttk.Label(self.form, text="Colors (click swatch to pick)", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, columnspan=3, sticky="w", pady=(4, 4)); r += 1
        self.color_vars = {}
        colors = theme.get("colors", {})
        for key in self.COLOR_KEYS:
            label = key + ("  <- page background / \"wallpaper\"" if key == "--page-bg" else "")
            ttk.Label(self.form, text=label).grid(row=r, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=colors.get(key, "#000000"))
            entry = ttk.Entry(self.form, textvariable=var, width=12)
            entry.grid(row=r, column=1, sticky="w", pady=2)
            swatch = tk.Label(self.form, text="  ", bg=var.get() if var.get().startswith("#") else "#ffffff", width=3, relief="ridge")
            swatch.grid(row=r, column=2, padx=(6, 0))
            def pick(v=var, s=swatch):
                c = colorchooser.askcolor(color=v.get() if v.get().startswith("#") else None)
                if c[1]:
                    v.set(c[1])
                    s.config(bg=c[1])
            swatch.bind("<Button-1>", lambda e, p=pick: p())
            self.color_vars[key] = var
            r += 1

        ttk.Label(self.form, text="Fonts", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="w", pady=(10, 4)); r += 1
        self.font_vars = {}
        fonts = theme.get("fonts", {})
        for key in self.FONT_KEYS:
            ttk.Label(self.form, text=key).grid(row=r, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=fonts.get(key, ""))
            ttk.Entry(self.form, textvariable=var, width=32).grid(row=r, column=1, columnspan=2, sticky="w", pady=2)
            self.font_vars[key] = var
            r += 1

        ttk.Label(self.form, text="Player frame / screen", font=("Segoe UI", 10, "bold")).grid(row=r, column=0, sticky="w", pady=(10, 4)); r += 1
        self.player_vars = {}
        player = theme.get("player", {})
        for key in self.PLAYER_KEYS:
            ttk.Label(self.form, text=key).grid(row=r, column=0, sticky="w", pady=2)
            var = tk.StringVar(value=player.get(key, ""))
            ttk.Entry(self.form, textvariable=var, width=50).grid(row=r, column=1, columnspan=2, sticky="w", pady=2)
            self.player_vars[key] = var
            r += 1

    def _write_form_into_data(self):
        theme = self.data["themes"][self.edit_theme.get()]
        theme["colors"] = {k: v.get() for k, v in self.color_vars.items()}
        theme["fonts"] = {k: v.get() for k, v in self.font_vars.items()}
        theme["player"] = {k: v.get() for k, v in self.player_vars.items()}

    def save(self):
        if self.data is None:
            messagebox.showwarning("Nothing loaded", "Load theme.json first.")
            return
        self._write_form_into_data()
        save_with_backup("theme.json", self.data, self.status)

    def set_active(self):
        if self.data is None:
            messagebox.showwarning("Nothing loaded", "Load theme.json first.")
            return
        self._write_form_into_data()
        self.data["theme"] = self.active_theme.get()
        save_with_backup("theme.json", self.data, self.status)


# ---------------------------------------------------------------------------
# Content tab
# ---------------------------------------------------------------------------
class ContentTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=16)
        self.data = None

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Load from VPS", command=self.load).pack(side="left")
        ttk.Button(top, text="Save (with backup)", command=self.save).pack(side="left", padx=(8, 0))
        self.status = tk.Label(top, text="Not loaded", fg="#888")
        self.status.pack(side="left", padx=(16, 0))

        ttk.Label(self, text="About — Title").pack(anchor="w", pady=(12, 2))
        self.about_title = tk.StringVar()
        ttk.Entry(self, textvariable=self.about_title, width=60).pack(anchor="w")

        ttk.Label(self, text="About — Paragraphs (one per line, HTML allowed)").pack(anchor="w", pady=(10, 2))
        self.about_paragraphs = tk.Text(self, height=8, width=80, wrap="word")
        self.about_paragraphs.pack(anchor="w")

        ttk.Label(self, text="Footer — main text").pack(anchor="w", pady=(10, 2))
        self.footer_text = tk.StringVar()
        ttk.Entry(self, textvariable=self.footer_text, width=60).pack(anchor="w")

        ttk.Label(self, text="Footer — bugs/progress line").pack(anchor="w", pady=(6, 2))
        self.footer_bugs = tk.StringVar()
        ttk.Entry(self, textvariable=self.footer_bugs, width=60).pack(anchor="w")

        ttk.Label(self, text="Footer — launch line").pack(anchor="w", pady=(6, 2))
        self.footer_launch = tk.StringVar()
        ttk.Entry(self, textvariable=self.footer_launch, width=60).pack(anchor="w")

        ttk.Label(self, text="Loading message").pack(anchor="w", pady=(10, 2))
        self.loading_text = tk.StringVar()
        ttk.Entry(self, textvariable=self.loading_text, width=40).pack(anchor="w")

    def load(self):
        try:
            self.data = conn.read_json("content.json")
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            return
        about = self.data.get("about", {})
        footer = self.data.get("footer", {})
        loading = self.data.get("loading", {})

        self.about_title.set(about.get("title", ""))
        self.about_paragraphs.delete("1.0", "end")
        self.about_paragraphs.insert("1.0", "\n".join(about.get("paragraphs", [])))
        self.footer_text.set(footer.get("text", ""))
        self.footer_bugs.set(footer.get("bugs", ""))
        self.footer_launch.set(footer.get("launch", ""))
        self.loading_text.set(loading.get("text", ""))
        self.status.config(text="Loaded.", fg="#2a7a2a")

    def save(self):
        if self.data is None:
            messagebox.showwarning("Nothing loaded", "Load content.json first.")
            return
        paragraphs = [line for line in self.about_paragraphs.get("1.0", "end").split("\n") if line.strip()]
        self.data["about"] = {"title": self.about_title.get(), "paragraphs": paragraphs}
        self.data["footer"] = {"text": self.footer_text.get(), "bugs": self.footer_bugs.get(), "launch": self.footer_launch.get()}
        self.data["loading"] = {"text": self.loading_text.get()}
        save_with_backup("content.json", self.data, self.status)


# ---------------------------------------------------------------------------
# Welcome tab
# ---------------------------------------------------------------------------
class WelcomeTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=16)
        self.data = None

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Load from VPS", command=self.load).pack(side="left")
        ttk.Button(top, text="Save (with backup)", command=self.save).pack(side="left", padx=(8, 0))
        self.status = tk.Label(top, text="Not loaded", fg="#888")
        self.status.pack(side="left", padx=(16, 0))

        ttk.Label(self, text="Welcome prompts — one per line. A random one shows on every page load.").pack(anchor="w", pady=(12, 2))
        self.prompts_box = tk.Text(self, height=15, width=70, wrap="word")
        self.prompts_box.pack(anchor="w")

    def load(self):
        try:
            self.data = conn.read_json("welcome.json")
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            return
        self.prompts_box.delete("1.0", "end")
        self.prompts_box.insert("1.0", "\n".join(self.data.get("prompts", [])))
        self.status.config(text="Loaded.", fg="#2a7a2a")

    def save(self):
        if self.data is None:
            messagebox.showwarning("Nothing loaded", "Load welcome.json first.")
            return
        prompts = [line for line in self.prompts_box.get("1.0", "end").split("\n") if line.strip()]
        self.data["prompts"] = prompts
        save_with_backup("welcome.json", self.data, self.status)


# ---------------------------------------------------------------------------
# Artist Links tab
# ---------------------------------------------------------------------------
class ArtistLinksTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=16)
        self.data = None

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Load from VPS", command=self.load).pack(side="left")
        ttk.Button(top, text="Save (with backup)", command=self.save).pack(side="left", padx=(8, 0))
        self.status = tk.Label(top, text="Not loaded", fg="#888")
        self.status.pack(side="left", padx=(16, 0))

        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, pady=(12, 0))
        self.listbox = tk.Listbox(list_frame, width=70, height=14)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(list_frame, command=self.listbox.yview)
        scroll.pack(side="left", fill="y")
        self.listbox.config(yscrollcommand=scroll.set)
        self.listbox.bind("<<ListboxSelect>>", self._on_select)

        form = ttk.Frame(self)
        form.pack(fill="x", pady=(10, 0))
        ttk.Label(form, text="Artist").grid(row=0, column=0, sticky="w")
        self.artist_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.artist_var, width=30).grid(row=0, column=1, padx=(6, 12))
        ttk.Label(form, text="URL").grid(row=0, column=2, sticky="w")
        self.url_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.url_var, width=40).grid(row=0, column=3, padx=(6, 0))

        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", pady=(8, 0))
        ttk.Button(btn_row, text="Add / Update", command=self._add_or_update).pack(side="left")
        ttk.Button(btn_row, text="Remove selected", command=self._remove).pack(side="left", padx=(8, 0))

    def load(self):
        try:
            self.data = conn.read_json("artist-links.json")
        except Exception as e:
            messagebox.showerror("Load failed", str(e))
            return
        self._refresh_listbox()
        self.status.config(text="Loaded.", fg="#2a7a2a")

    def _refresh_listbox(self):
        self.listbox.delete(0, "end")
        for artist, url in sorted(self.data.items()):
            self.listbox.insert("end", f"{artist}  ->  {url}")

    def _on_select(self, event):
        sel = self.listbox.curselection()
        if not sel:
            return
        artist = sorted(self.data.keys())[sel[0]]
        self.artist_var.set(artist)
        self.url_var.set(self.data[artist])

    def _add_or_update(self):
        artist = self.artist_var.get().strip()
        url = self.url_var.get().strip()
        if not artist or not url:
            messagebox.showwarning("Missing info", "Both artist and URL are required.")
            return
        self.data[artist] = url
        self._refresh_listbox()

    def _remove(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        artist = sorted(self.data.keys())[sel[0]]
        del self.data[artist]
        self._refresh_listbox()

    def save(self):
        if self.data is None:
            messagebox.showwarning("Nothing loaded", "Load artist-links.json first.")
            return
        save_with_backup("artist-links.json", self.data, self.status)


# ---------------------------------------------------------------------------
# Rollback tab
# ---------------------------------------------------------------------------
class QuickLinksTab(ttk.Frame):
    FIXED_LINKS = [
        ("Cloudflare", "https://dash.cloudflare.com"),
        ("OVH Manager", "https://www.ovh.com/manager/"),
        ("Bunny CDN", "https://dash.bunny.net"),
        ("Gmail", "https://mail.google.com"),
    ]
    CUSTOM_SLOTS = 5

    def __init__(self, parent):
        super().__init__(parent, padding=16)
        self.custom_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quick_links.json")
        self.custom_vars = []  # list of (label_var, url_var)

        ttk.Label(self, text="Fixed Links", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        for label, url in self.FIXED_LINKS:
            row = ttk.Frame(self)
            row.pack(fill="x", pady=3)
            ttk.Button(row, text=f"Open {label}", width=20, command=lambda u=url: self._open(u)).pack(side="left")
            tk.Label(row, text=url, fg="#888").pack(side="left", padx=(10, 0))

        ttk.Label(self, text="Custom Links (saved locally, not synced to the VPS)", font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(16, 6))

        for i in range(self.CUSTOM_SLOTS):
            row = ttk.Frame(self)
            row.pack(fill="x", pady=3)
            label_var = tk.StringVar()
            url_var = tk.StringVar()
            ttk.Entry(row, textvariable=label_var, width=18).pack(side="left")
            ttk.Entry(row, textvariable=url_var, width=40).pack(side="left", padx=(6, 6))
            ttk.Button(row, text="Open", command=lambda u=url_var: self._open(u.get())).pack(side="left")
            self.custom_vars.append((label_var, url_var))

        btn_row = ttk.Frame(self)
        btn_row.pack(fill="x", pady=(12, 0))
        ttk.Button(btn_row, text="Save custom links", command=self.save).pack(side="left")
        self.status = tk.Label(btn_row, text="", fg="#888")
        self.status.pack(side="left", padx=(10, 0))

        self.load()

    def _open(self, url):
        if not url:
            return
        import webbrowser
        webbrowser.open(url)

    def load(self):
        if not os.path.exists(self.custom_file):
            return
        try:
            with open(self.custom_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            for i, entry in enumerate(saved.get("links", [])):
                if i >= len(self.custom_vars):
                    break
                self.custom_vars[i][0].set(entry.get("label", ""))
                self.custom_vars[i][1].set(entry.get("url", ""))
        except Exception:
            pass  # corrupt/missing local file — just start blank, non-critical data

    def save(self):
        links = [{"label": lv.get(), "url": uv.get()} for lv, uv in self.custom_vars if lv.get() or uv.get()]
        try:
            with open(self.custom_file, "w", encoding="utf-8") as f:
                json.dump({"links": links}, f, indent=2)
            self.status.config(text="Saved.", fg="#2a7a2a")
        except Exception as e:
            self.status.config(text=f"Save failed: {e}", fg="#a02020")


class RollbackTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent, padding=16)

        ttk.Label(self, text="Full Site Snapshot", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(self, text="index.html + all config files, bundled together — a real time machine for the whole site.", fg="#888").pack(anchor="w", pady=(0, 8))

        snap_top = ttk.Frame(self)
        snap_top.pack(fill="x")
        ttk.Button(snap_top, text="Backup entire site now", command=self.backup_full_site).pack(side="left")
        ttk.Button(snap_top, text="Restore selected snapshot", command=self.restore_full_site).pack(side="left", padx=(8, 0))
        self.full_site_status = tk.Label(snap_top, text="", fg="#888")
        self.full_site_status.pack(side="left", padx=(16, 0))

        self.snapshot_listbox = tk.Listbox(self, width=60, height=6)
        self.snapshot_listbox.pack(fill="x", pady=(8, 0))
        self._refresh_snapshots()

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=16)

        ttk.Label(self, text="GitHub Transparency Push", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(
            self,
            text="Publishes the selected snapshot above to a public GitHub repo, for\n"
                 "anyone to see the real, current source — separate and deliberate from\n"
                 "the VPS backups above, on purpose. Nothing here is saved between\n"
                 "sessions; the token is entered fresh each time, same as VPS login.",
            fg="#888", justify="left",
        ).pack(anchor="w", pady=(0, 8))

        gh_form = ttk.Frame(self)
        gh_form.pack(fill="x")
        ttk.Label(gh_form, text="Personal Access Token").grid(row=0, column=0, sticky="w", pady=3)
        self.gh_token = tk.StringVar()
        ttk.Entry(gh_form, textvariable=self.gh_token, width=44, show="*").grid(row=0, column=1, sticky="w", padx=(6, 0), pady=3)

        ttk.Label(gh_form, text="Repo (owner/name)").grid(row=1, column=0, sticky="w", pady=3)
        self.gh_repo = tk.StringVar()
        ttk.Entry(gh_form, textvariable=self.gh_repo, width=44).grid(row=1, column=1, sticky="w", padx=(6, 0), pady=3)

        ttk.Label(gh_form, text="Branch").grid(row=2, column=0, sticky="w", pady=3)
        self.gh_branch = tk.StringVar(value="main")
        ttk.Entry(gh_form, textvariable=self.gh_branch, width=20).grid(row=2, column=1, sticky="w", padx=(6, 0), pady=3)

        gh_btn_row = ttk.Frame(self)
        gh_btn_row.pack(fill="x", pady=(10, 0))
        ttk.Button(gh_btn_row, text="Push selected snapshot to GitHub", command=self.push_to_github).pack(side="left")
        self.gh_status = tk.Label(gh_btn_row, text="", fg="#888")
        self.gh_status.pack(side="left", padx=(12, 0))

        ttk.Separator(self, orient="horizontal").pack(fill="x", pady=16)

        ttk.Label(self, text="Individual config file backups (auto-created before every save)", font=("Segoe UI", 11, "bold")).pack(anchor="w")
        tk.Label(self, text=f"Folder: {BACKUP_DIR}", fg="#888").pack(anchor="w", pady=(0, 10))

        top = ttk.Frame(self)
        top.pack(fill="x")
        ttk.Button(top, text="Refresh list", command=self.refresh).pack(side="left")
        ttk.Button(top, text="Restore selected to VPS", command=self.restore).pack(side="left", padx=(8, 0))
        self.status = tk.Label(top, text="", fg="#888")
        self.status.pack(side="left", padx=(16, 0))

        self.listbox = tk.Listbox(self, width=60, height=12)
        self.listbox.pack(fill="both", expand=True, pady=(12, 0))
        self.refresh()

    def _refresh_snapshots(self):
        self.snapshot_listbox.delete(0, "end")
        if not os.path.exists(BACKUP_DIR):
            return
        folders = sorted(
            [f for f in os.listdir(BACKUP_DIR) if f.startswith("full_site_") and os.path.isdir(os.path.join(BACKUP_DIR, f))],
            reverse=True,
        )
        for f in folders:
            self.snapshot_listbox.insert("end", f)

    def backup_full_site(self):
        if conn.sftp is None:
            messagebox.showwarning("Not connected", "Connect to the VPS first (Connection tab).")
            return
        try:
            snapshot_dir = conn.backup_full_site(FULL_SITE_FILES)
            if snapshot_dir is None:
                self.full_site_status.config(text="Nothing found to back up.", fg="#a02020")
                return
            self._refresh_snapshots()
            self.full_site_status.config(text=f"Snapshot saved: {os.path.basename(snapshot_dir)}", fg="#2a7a2a")
        except Exception as e:
            self.full_site_status.config(text=f"Backup FAILED: {e}", fg="#a02020")
            messagebox.showerror("Backup failed", str(e))

    def restore_full_site(self):
        sel = self.snapshot_listbox.curselection()
        if not sel:
            messagebox.showwarning("Nothing selected", "Pick a snapshot first.")
            return
        folder_name = self.snapshot_listbox.get(sel[0])
        if not messagebox.askyesno(
            "Confirm FULL SITE restore",
            f"This will overwrite index.html AND every config file on the live VPS with the contents of:\n{folder_name}\n\n"
            "The current live state will be backed up as a fresh snapshot first, as a safety net.",
        ):
            return
        try:
            # Safety net on top of safety net: snapshot current live state before overwriting it
            conn.backup_full_site(FULL_SITE_FILES)
            restored = conn.restore_full_site(os.path.join(BACKUP_DIR, folder_name))
            self._refresh_snapshots()
            self.full_site_status.config(text=f"Restored {len(restored)} files from {folder_name}.", fg="#2a7a2a")
        except Exception as e:
            self.full_site_status.config(text=f"Restore FAILED: {e}", fg="#a02020")
            messagebox.showerror("Restore failed", str(e))

    def push_to_github(self):
        """Publishes the SELECTED local snapshot to a public GitHub repo —
        deliberately manual, deliberately separate from the automatic VPS
        backup flow above, since this one's public the moment it runs."""
        if Github is None:
            messagebox.showerror(
                "Missing dependency",
                "PyGithub is not installed. Run:  pip install PyGithub",
            )
            return

        sel = self.snapshot_listbox.curselection()
        if not sel:
            messagebox.showwarning("Nothing selected", "Pick a snapshot to push first.")
            return
        folder_name = self.snapshot_listbox.get(sel[0])
        snapshot_dir = os.path.join(BACKUP_DIR, folder_name)

        token = self.gh_token.get().strip()
        repo_name = self.gh_repo.get().strip()
        branch = self.gh_branch.get().strip() or "main"
        if not token or not repo_name:
            messagebox.showwarning("Missing info", "Personal Access Token and Repo (owner/name) are both required.")
            return

        if not messagebox.askyesno(
            "Confirm public push",
            f"This will push every file in:\n{folder_name}\n\n"
            f"to the PUBLIC repo {repo_name} (branch: {branch}).\n\n"
            "Anyone can see these files after this. Continue?",
        ):
            return

        try:
            gh = Github(token)
            repo = gh.get_repo(repo_name)
            files = sorted(os.listdir(snapshot_dir))
            pushed, failed = [], []

            for filename in files:
                local_path = os.path.join(snapshot_dir, filename)
                if not os.path.isfile(local_path):
                    continue
                with open(local_path, "r", encoding="utf-8") as f:
                    content = f.read()
                try:
                    # File already exists in the repo — update it
                    existing = repo.get_contents(filename, ref=branch)
                    repo.update_file(filename, f"Update {filename}", content, existing.sha, branch=branch)
                except GithubException as e:
                    if e.status == 404:
                        # Doesn't exist yet — create it
                        repo.create_file(filename, f"Add {filename}", content, branch=branch)
                    else:
                        raise
                pushed.append(filename)

            self.gh_status.config(text=f"Pushed {len(pushed)} files to {repo_name}.", fg="#2a7a2a")
        except Exception as e:
            failed_msg = f"Push FAILED: {e}"
            self.gh_status.config(text=failed_msg, fg="#a02020")
            messagebox.showerror("GitHub push failed", str(e))

    def refresh(self):
        self.listbox.delete(0, "end")
        files = sorted(os.listdir(BACKUP_DIR), reverse=True)
        for f in files:
            self.listbox.insert("end", f)

    def restore(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("Nothing selected", "Pick a backup file first.")
            return
        filename = self.listbox.get(sel[0])
        # backup filenames look like "settings_20260810_143000.json" — recover the real target name
        base = filename.rsplit("_", 2)[0]
        target = base + ".json"
        if target not in REMOTE_FILES:
            messagebox.showerror("Unrecognized file", f"Can't determine which live file '{filename}' belongs to.")
            return
        if not messagebox.askyesno("Confirm restore", f"This will overwrite the LIVE {target} on the VPS with:\n{filename}\n\n(Current live version will also be backed up first.)"):
            return
        try:
            with open(os.path.join(BACKUP_DIR, filename), "r", encoding="utf-8") as f:
                data = json.load(f)
            conn.backup_current(target)  # safety net: back up whatever's live right now too
            conn.write_json(target, data)
            self.status.config(text=f"Restored {target} from {filename}.", fg="#2a7a2a")
        except Exception as e:
            self.status.config(text=f"Restore FAILED: {e}", fg="#a02020")
            messagebox.showerror("Restore failed", str(e))


# ---------------------------------------------------------------------------
# Main app
# ---------------------------------------------------------------------------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("The Table IPTV — Config Manager")
        self.geometry("880x640")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.connection_tab = ConnectionTab(self.notebook, on_connected=self._on_connected)
        self.notebook.add(self.connection_tab, text="Connection")

        self.settings_tab = SettingsTab(self.notebook)
        self.theme_tab = ThemeTab(self.notebook)
        self.content_tab = ContentTab(self.notebook)
        self.welcome_tab = WelcomeTab(self.notebook)
        self.artist_links_tab = ArtistLinksTab(self.notebook)
        self.quick_links_tab = QuickLinksTab(self.notebook)
        self.rollback_tab = RollbackTab(self.notebook)

        self.notebook.add(self.settings_tab, text="Settings")
        self.notebook.add(self.theme_tab, text="Theme")
        self.notebook.add(self.content_tab, text="Content / Footer")
        self.notebook.add(self.welcome_tab, text="Welcome Prompts")
        self.notebook.add(self.artist_links_tab, text="Artist Links")
        self.notebook.add(self.quick_links_tab, text="Quick Links")
        self.notebook.add(self.rollback_tab, text="Backups / Rollback")

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        conn.close()  # clean SSH disconnect, not just relying on process exit
        self.destroy()

    def _on_connected(self):
        messagebox.showinfo("Connected", "Connected to VPS. Use each tab's 'Load from VPS' button to pull the current file.")


if __name__ == "__main__":
    if paramiko is None:
        print("Missing dependency. Run:  pip install paramiko")
    app = App()
    app.mainloop()
