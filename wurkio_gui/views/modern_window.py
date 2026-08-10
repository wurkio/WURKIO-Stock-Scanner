from __future__ import annotations

import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk
from typing import Any

from wurkio_scanner import FilterConfig, ScanResult

from ..controller import AppController
from ..themes import available_themes, load_theme


FILTER_FIELDS = (
    ("price_min", "Price - minimum", "float"),
    ("price_max", "Price - maximum", "float"),
    ("rvol_min", "Relative Volume (RVOL)", "float"),
    ("current_volume_min", "Current Volume", "int"),
    ("avg_volume_5d_min", "5D Average Volume", "int"),
    ("avg_volume_20d_min", "20D Average Volume", "int"),
    ("atr_percent_min", "ATR% - minimum", "float"),
    ("atr_percent_max", "ATR% - maximum", "float"),
    ("latest_percent_change_min", "Daily % Change", "float"),
    ("volume_percent_change_min", "Volume Change %", "float"),
    ("float_min", "Float - minimum", "int"),
    ("float_max", "Float - maximum", "int"),
    ("above_vwap", "Price Above VWAP", "bool"),
    ("above_sma_20", "Price Above 20 SMA", "bool"),
    ("above_sma_50", "Price Above 50 SMA", "bool"),
    ("above_sma_200", "Price Above 200 SMA", "bool"),
    ("gap_percent_min", "Gap %", "float"),
    ("premarket_percent_change_min", "Premarket % Change", "float"),
    ("premarket_volume_min", "Premarket Volume", "int"),
    ("market_cap_min", "Market Cap - minimum", "float"),
    ("market_cap_max", "Market Cap - maximum", "float"),
    ("short_float_percent_min", "Short Float % - minimum", "float"),
    ("short_float_percent_max", "Short Float % - maximum", "float"),
    ("week_52_position_min", "52W Position %", "float"),
    ("day_range_position_min", "Day Range Position %", "float"),
    ("dollar_volume_min", "Dollar Volume", "float"),
    ("float_rotation_min", "Float Rotation", "float"),
    ("distance_from_high_percent_min", "Distance From HOD %", "float"),
)

RESULT_COLUMNS = (
    "rank", "symbol", "price", "change", "rvol", "volume",
    "avg20", "atrp", "float", "score",
)


class ModernWindow:
    def __init__(self, root: tk.Tk, controller: AppController) -> None:
        self.root = root
        self.controller = controller
        self.style = ttk.Style(root)
        self.filter_enabled: dict[str, tk.BooleanVar] = {}
        self.filter_values: dict[str, tk.StringVar] = {}
        self.result_lookup: dict[str, ScanResult] = {}
        self.visible_results: list[ScanResult] = []
        self.sort_column = "score"
        self.sort_reverse = True
        self.preset_paths = controller.available_presets()
        self.theme_paths = {
            name: path for name, path in available_themes().items()
            if load_theme(path).get("layout") == "modern"
        }

        try:
            self.user_settings = controller.load_settings()
        except (OSError, ValueError):
            self.user_settings = {}
        root.title("WURKIO Scanner v0.5 - Live Data & Outcome Tracking")
        root.geometry(self.user_settings.get("window_geometry", "1580x940"))
        root.minsize(1280, 760)
        self._build()
        saved_columns = tuple(
            column for column in self.user_settings.get("visible_columns", RESULT_COLUMNS)
            if column in RESULT_COLUMNS
        )
        if saved_columns:
            self.results.configure(displaycolumns=saved_columns)
        saved_preset = self.user_settings.get("last_preset", "WURKIO Default")
        if saved_preset in self.preset_paths:
            self.preset_var.set(saved_preset)
            try:
                controller.load_preset(self.preset_paths[saved_preset])
            except (OSError, ValueError):
                pass
        saved_csv = Path(self.user_settings.get("last_csv", controller.state.input_path))
        if saved_csv.exists():
            controller.set_input(saved_csv)
            self.input_var.set(str(saved_csv))
        self._load_config(controller.state.config)
        theme_name = self.user_settings.get("theme", "Dark 2026")
        theme_name = theme_name if theme_name in self.theme_paths else "Dark 2026"
        self.theme_var.set(theme_name)
        self._set_theme(theme_name)
        root.protocol("WM_DELETE_WINDOW", self._close)
        self.root.after(150, self._scan)

    def _build(self) -> None:
        self.header = ttk.Frame(self.root, padding=(18, 10), style="Header.TFrame")
        self.header.pack(fill="x")
        brand = ttk.Frame(self.header, style="Header.TFrame")
        brand.pack(side="left")
        ttk.Label(brand, text="W", style="Logo.TLabel").pack(side="left", padx=(0, 9))
        brand_text = ttk.Frame(brand, style="Header.TFrame")
        brand_text.pack(side="left")
        ttk.Label(brand_text, text="WURKIO SCANNER 2026", style="Title.TLabel").pack(anchor="w")
        ttk.Label(brand_text, text="TRADE SMART. EXECUTE CLEAN.", style="Kicker.TLabel").pack(anchor="w")

        nav = ttk.Frame(self.header, style="Header.TFrame")
        nav.pack(side="left", padx=70)
        for index, name in enumerate(("SCANNER", "WATCHLIST", "ALERTS", "HISTORY", "MARKET", "JOURNAL", "TOOLS")):
            command = self._show_history if name == "HISTORY" else None
            ttk.Button(nav, text=name, command=command, style="NavActive.TButton" if index == 0 else "Nav.TButton").pack(side="left", padx=2)

        ttk.Label(self.header, text="Theme:").pack(side="right", padx=(12, 5))
        self.theme_var = tk.StringVar(value="Dark 2026")
        theme_box = ttk.Combobox(
            self.header, textvariable=self.theme_var, values=list(self.theme_paths),
            state="readonly", width=18,
        )
        theme_box.pack(side="right")
        theme_box.bind("<<ComboboxSelected>>", lambda _event: self._set_theme(self.theme_var.get()))
        live = ttk.Frame(self.header, padding=(10, 4), style="Market.TFrame")
        live.pack(side="right", padx=12)
        ttk.Label(live, text="● LIVE", style="Live.TLabel").pack(side="left")
        ttk.Label(live, text="  10:32:45 AM ET", style="HeaderMuted.TLabel").pack(side="left")

        ticker = ttk.Frame(self.root, padding=(14, 7), style="Ticker.TFrame")
        ticker.pack(fill="x", padx=8, pady=(0, 7))
        for symbol, price, change, positive in (
            ("SPY", "530.91", "+1.28 (+0.24%)", True),
            ("QQQ", "448.92", "+2.01 (+0.45%)", True),
            ("IWM", "204.78", "+0.71 (+0.35%)", True),
            ("VIX", "12.31", "-0.24 (-1.91%)", False),
        ):
            block = ttk.Frame(ticker, style="Ticker.TFrame")
            block.pack(side="left", padx=(0, 36))
            ttk.Label(block, text=f"{symbol}  {price}  ", style="TickerLabel.TLabel").pack(side="left")
            ttk.Label(block, text=change, style="Positive.TLabel" if positive else "Negative.TLabel").pack(side="left")
        ttk.Label(ticker, text="MARKET BREADTH", style="HeaderMuted.TLabel").pack(side="right", padx=(12, 4))
        ttk.Label(ticker, text="62% ▲", style="Positive.TLabel").pack(side="right")

        main = ttk.Panedwindow(self.root, orient="horizontal")
        main.pack(fill="both", expand=True, padx=8, pady=(0, 7))

        left = ttk.Frame(main, padding=10, style="Panel.TFrame")
        right = ttk.Frame(main, padding=10, style="Panel.TFrame")
        main.add(left, weight=1)
        main.add(right, weight=4)
        self._build_filters(left)
        self._build_results(right)

        status = ttk.Frame(self.root, padding=(12, 5), style="Panel.TFrame")
        status.pack(fill="x")
        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(status, textvariable=self.status_var, style="Status.TLabel").pack(side="left")
        self.match_var = tk.StringVar(value="Results: 0")
        ttk.Label(status, textvariable=self.match_var, style="Status.TLabel").pack(side="right")

    def _build_filters(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="1  FILTERS", style="Section.TLabel").pack(fill="x", pady=(0, 8))
        preset_row = ttk.Frame(parent)
        preset_row.pack(fill="x", pady=(0, 8))
        self.preset_var = tk.StringVar(value="WURKIO Default")
        self.preset_box = ttk.Combobox(
            preset_row, textvariable=self.preset_var, values=list(self.preset_paths),
            state="readonly", width=24,
        )
        self.preset_box.pack(side="left", fill="x", expand=True)
        self.preset_box.bind("<<ComboboxSelected>>", self._preset_selected)

        quick = ttk.Frame(parent, style="Panel.TFrame")
        quick.pack(fill="x", pady=(0, 7))
        for name in ("Momentum", "Low Float", "High Rvol", "Scalper"):
            ttk.Button(quick, text=name, style="Quick.TButton", command=lambda n=name: self._quick_preset(n)).pack(
                side="left", fill="x", expand=True, padx=(0, 2)
            )

        canvas = tk.Canvas(parent, highlightthickness=0, width=315)
        self.filter_canvas = canvas
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=canvas.yview)
        fields = ttk.Frame(canvas)
        fields.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=fields, anchor="nw", width=300)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="top", fill="both", expand=True)
        scrollbar.place(relx=1.0, rely=0.10, relheight=0.64, anchor="ne")

        for key, label, _kind in FILTER_FIELDS:
            row = ttk.Frame(fields, padding=(2, 3))
            row.pack(fill="x")
            enabled = tk.BooleanVar(value=True)
            value = tk.StringVar()
            self.filter_enabled[key] = enabled
            self.filter_values[key] = value
            ttk.Checkbutton(row, variable=enabled, command=lambda k=key: self._toggle_filter(k)).pack(side="left")
            ttk.Label(row, text=label, width=23).pack(side="left")
            entry = ttk.Entry(row, textvariable=value, width=13)
            entry.pack(side="right")
            entry.bind("<Return>", lambda _event: self._scan())

        source = ttk.LabelFrame(parent, text="DATA SOURCE", padding=8)
        source.pack(fill="x", pady=(10, 6))
        self.input_var = tk.StringVar(value=str(self.controller.state.input_path))
        ttk.Label(source, textvariable=self.input_var, style="Muted.TLabel", wraplength=270).pack(fill="x")
        ttk.Button(source, text="Choose CSV...", command=self._choose_csv).pack(fill="x", pady=(6, 0))

        self.scan_button = ttk.Button(parent, text="SCAN NOW", style="Accent.TButton", command=self._scan)
        self.scan_button.pack(fill="x", pady=(7, 4), ipady=6)
        self.save_snapshot_var = tk.BooleanVar(value=self.user_settings.get("save_snapshots", True))
        ttk.Checkbutton(parent, text="Save scan snapshot to history", variable=self.save_snapshot_var).pack(anchor="w", pady=(0, 5))
        ttk.Button(parent, text="SAVE FILTER SET", command=self._save_preset).pack(fill="x", pady=(0, 4))
        ttk.Button(parent, text="RESET TO PRESET", command=self._reload_preset).pack(fill="x")

    def _build_results(self, parent: ttk.Frame) -> None:
        cards = ttk.Frame(parent, style="Panel.TFrame")
        cards.pack(fill="x", pady=(0, 8))
        self.card_vars = {
            "matches": tk.StringVar(value="0"), "top": tk.StringVar(value="--"),
            "rvol": tk.StringVar(value="--"), "change": tk.StringVar(value="--"),
            "volume": tk.StringVar(value="--"),
        }
        for label, key in (("MATCHING STOCKS", "matches"), ("TOP SCORE", "top"),
                           ("AVG RVOL", "rvol"), ("AVG % CHANGE", "change"),
                           ("TOTAL VOLUME", "volume")):
            card = ttk.Frame(cards, padding=(14, 9), style="Card.TFrame")
            card.pack(side="left", fill="x", expand=True, padx=(0, 6))
            ttk.Label(card, text=label, style="CardLabel.TLabel").pack()
            ttk.Label(card, textvariable=self.card_vars[key], style="CardValue.TLabel").pack(pady=(4, 0))

        top = ttk.Frame(parent)
        top.pack(fill="x", pady=(0, 8))
        ttk.Label(top, text="2  SCAN RESULTS", style="Section.TLabel").pack(side="left")
        self.search_var = tk.StringVar()
        search = ttk.Entry(top, textvariable=self.search_var, width=24)
        search.pack(side="left", padx=(20, 5))
        search.insert(0, "")
        search.bind("<KeyRelease>", lambda _event: self._apply_search())
        ttk.Label(top, text="Search ticker", style="Muted.TLabel").pack(side="left")
        self.last_scan_var = tk.StringVar(value="Not scanned yet")
        ttk.Label(top, textvariable=self.last_scan_var, style="Muted.TLabel").pack(side="right")
        ttk.Button(top, text="EXPORT", command=self._export_results).pack(side="right", padx=12)
        ttk.Button(top, text="COLUMNS", command=self._choose_columns).pack(side="right")

        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="both", expand=True)
        self.results = ttk.Treeview(table_frame, columns=RESULT_COLUMNS, show="headings", height=16)
        labels = {
            "rank": "#", "symbol": "TICKER", "price": "PRICE", "change": "% CHANGE",
            "rvol": "RVOL", "volume": "VOLUME", "avg20": "20D AVG VOL",
            "atrp": "ATRP%", "float": "FLOAT", "score": "WURKIO SCORE",
        }
        widths = {"rank": 38, "symbol": 76, "price": 80, "change": 92, "rvol": 65,
                  "volume": 100, "avg20": 105, "atrp": 75, "float": 95, "score": 115}
        for column in RESULT_COLUMNS:
            self.results.heading(column, text=labels[column], command=lambda c=column: self._sort_results(c))
            self.results.column(column, width=widths[column], anchor="center", stretch=column == "score")
        y_scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.results.yview)
        x_scroll = ttk.Scrollbar(table_frame, orient="horizontal", command=self.results.xview)
        self.results.configure(yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
        self.results.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)
        self.results.bind("<<TreeviewSelect>>", self._show_selection)

        bottom = ttk.Frame(parent, style="Panel.TFrame")
        bottom.pack(fill="x", pady=(9, 0))
        chart = ttk.LabelFrame(bottom, text="3  CHART", padding=12)
        chart.pack(side="left", fill="both", expand=True, padx=(0, 7))
        ttk.Label(chart, text="INTRADAY CHART", style="CardLabel.TLabel").pack(anchor="w")
        ttk.Label(chart, text="Coming in v0.2", style="Placeholder.TLabel").pack(expand=True, pady=30)

        detail = ttk.LabelFrame(bottom, text="4  KEY METRICS", padding=12)
        detail.pack(side="left", fill="both", expand=True, padx=(0, 7))
        self.detail_symbol = tk.StringVar(value="Select a result to view its metrics")
        ttk.Label(detail, textvariable=self.detail_symbol, style="DetailTitle.TLabel").grid(row=0, column=0, columnspan=4, sticky="w")
        self.detail_vars = {name: tk.StringVar(value="--") for name in
                            ("score", "price", "change", "rvol", "atrp", "volume", "avg20", "float")}
        pairs = (("WURKIO SCORE", "score"), ("PRICE", "price"), ("CHANGE", "change"),
                 ("RVOL", "rvol"), ("ATRP", "atrp"), ("VOLUME", "volume"),
                 ("20D AVG VOLUME", "avg20"), ("FLOAT", "float"))
        for index, (label, key) in enumerate(pairs):
            row = 1 + index // 2
            col = (index % 2) * 2
            ttk.Label(detail, text=label, style="Muted.TLabel").grid(row=row, column=col, sticky="w", padx=(0, 5), pady=5)
            ttk.Label(detail, textvariable=self.detail_vars[key]).grid(row=row, column=col + 1, sticky="w", padx=(0, 24), pady=5)
        self.pass_reasons = tk.StringVar(value="")
        ttk.Label(detail, textvariable=self.pass_reasons, style="Pass.TLabel", wraplength=370).grid(
            row=5, column=0, columnspan=4, sticky="w", pady=(7, 0)
        )
        self.fail_reasons = tk.StringVar(value="")
        ttk.Label(detail, textvariable=self.fail_reasons, style="Fail.TLabel", wraplength=370).grid(
            row=6, column=0, columnspan=4, sticky="w", pady=(4, 0)
        )
        self.breakdown_var = tk.StringVar(value="")
        ttk.Label(detail, textvariable=self.breakdown_var, style="Breakdown.TLabel", wraplength=420).grid(
            row=7, column=0, columnspan=4, sticky="w", pady=(7, 0)
        )

        level2 = ttk.LabelFrame(bottom, text="5  LEVEL II", padding=12)
        level2.pack(side="left", fill="both", expand=True, padx=(0, 7))
        ttk.Label(level2, text="LIVE ORDER BOOK", style="CardLabel.TLabel").pack(anchor="w")
        ttk.Label(level2, text="Requires live market data", style="Placeholder.TLabel").pack(expand=True, pady=30)

        info = ttk.LabelFrame(bottom, text="6  MARKET CONTEXT", padding=12)
        info.pack(side="left", fill="both", expand=True)
        context_fields = (
            ("VWAP", "vwap"), ("Gap", "gap"), ("20/50/200 SMA", "smas"),
            ("Premarket", "premarket"), ("Dollar Volume", "dollar_volume"),
            ("Float Rotation", "rotation"), ("From HOD", "hod"),
            ("Day / 52W Position", "positions"), ("Market Cap", "market_cap"),
            ("Short Float", "short_float"),
        )
        self.info_vars = {key: tk.StringVar(value="--") for _label, key in context_fields}
        for row, (label, key) in enumerate(context_fields):
            ttk.Label(info, text=label, style="Muted.TLabel").grid(row=row, column=0, sticky="w", pady=2)
            ttk.Label(info, textvariable=self.info_vars[key]).grid(row=row, column=1, sticky="w", padx=(8, 0), pady=2)

    def _toggle_filter(self, key: str) -> None:
        if not self.filter_enabled[key].get():
            self.status_var.set(f"{key} disabled; it will not restrict results")

    def _preset_selected(self, _event: object = None) -> None:
        try:
            config = self.controller.load_preset(self.preset_paths[self.preset_var.get()])
            self._load_config(config)
            self.status_var.set(f"Loaded preset: {self.preset_var.get()}")
        except Exception as exc:
            messagebox.showerror("Preset error", str(exc), parent=self.root)

    def _quick_preset(self, name: str) -> None:
        if name not in self.preset_paths:
            messagebox.showerror("Preset unavailable", f"Could not find the {name} preset.", parent=self.root)
            return
        self.preset_var.set(name)
        self._preset_selected()
        self._scan()

    def _reload_preset(self) -> None:
        self._preset_selected()

    def _save_preset(self) -> None:
        try:
            self.controller.update_config(self._read_config())
            name = simpledialog.askstring("Save filter set", "Preset name:", parent=self.root)
            if name is None:
                return
            try:
                path = self.controller.save_preset(name)
            except FileExistsError:
                replace = messagebox.askyesno(
                    "Replace preset?", f"A preset named '{name}' already exists. Replace it?", parent=self.root
                )
                if not replace:
                    return
                path = self.controller.save_preset(name, overwrite=True)
            self.preset_paths = self.controller.available_presets()
            self.preset_box.configure(values=list(self.preset_paths))
            self.preset_var.set(path.stem.replace("_", " ").title())
            self.status_var.set(f"Saved preset: {path.name}")
            messagebox.showinfo("Preset saved", f"Saved to {path}", parent=self.root)
        except Exception as exc:
            messagebox.showerror("Unable to save preset", str(exc), parent=self.root)

    def _load_config(self, config: FilterConfig) -> None:
        for key, value in self.controller.config_values().items():
            self.filter_enabled[key].set(value is not None)
            self.filter_values[key].set("" if value is None else str(value))

    def _read_config(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        kinds = {key: kind for key, _label, kind in FILTER_FIELDS}
        for key, enabled in self.filter_enabled.items():
            if not enabled.get():
                values[key] = None
                continue
            raw = self.filter_values[key].get().strip().replace(",", "")
            if not raw:
                raise ValueError(f"{key} is enabled but has no value")
            if kinds[key] == "int":
                values[key] = int(raw)
            elif kinds[key] == "bool":
                normalized = raw.lower()
                if normalized not in ("true", "yes", "1", "false", "no", "0"):
                    raise ValueError(f"{key} must be Yes/No or True/False")
                values[key] = normalized in ("true", "yes", "1")
            else:
                values[key] = float(raw)
        return values

    def _choose_csv(self) -> None:
        path = filedialog.askopenfilename(
            parent=self.root, title="Select market snapshot",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if path:
            self.controller.set_input(path)
            self.input_var.set(path)
            self.status_var.set(f"Selected {Path(path).name}")

    def _scan(self) -> None:
        try:
            self.scan_button.configure(state="disabled")
            self.status_var.set("Scanning...")
            self.root.update_idletasks()
            self.controller.update_config(self._read_config())
            results = self.controller.scan(self.save_snapshot_var.get(), self.preset_var.get())
            self._display_results(results)
            now = datetime.now().strftime("%I:%M:%S %p")
            self.last_scan_var.set(f"Last scan: {now}")
            self.match_var.set(f"Results: {len(results)}")
            diagnostics = self.controller.state.diagnostics
            if results:
                self.status_var.set(
                    f"Scan complete  |  {diagnostics.rows_processed:,} stocks processed  |  "
                    f"{diagnostics.matches:,} matches  |  {diagnostics.duration_seconds * 1000:.1f} ms"
                    + (f"  |  Snapshot #{self.controller.state.last_run_id}" if self.save_snapshot_var.get() else "")
                )
            else:
                self.status_var.set(
                    f"No matches  |  {diagnostics.rows_processed:,} stocks processed in "
                    f"{diagnostics.duration_seconds * 1000:.1f} ms"
                )
        except Exception as exc:
            self.status_var.set("Scan failed")
            messagebox.showerror("Unable to scan", str(exc), parent=self.root)
        finally:
            self.scan_button.configure(state="normal")

    def _export_results(self) -> None:
        if not self.controller.state.results:
            messagebox.showinfo("Nothing to export", "Run a scan with at least one match first.", parent=self.root)
            return
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        path = filedialog.asksaveasfilename(
            parent=self.root, title="Export scan results", initialdir="exports",
            initialfile=f"WURKIO_Scan_{timestamp}.csv", defaultextension=".csv",
            filetypes=(("CSV file", "*.csv"), ("JSON file", "*.json")),
        )
        if not path:
            return
        format_name = "json" if Path(path).suffix.lower() == ".json" else "csv"
        try:
            destination = self.controller.export_results(path, format_name, self.preset_var.get())
            self.status_var.set(f"Exported {len(self.controller.state.results)} results to {destination.name}")
            messagebox.showinfo("Export complete", f"Saved to {destination}", parent=self.root)
        except Exception as exc:
            messagebox.showerror("Unable to export", str(exc), parent=self.root)

    def _show_history(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("WURKIO Scan History")
        dialog.geometry("760x440")
        dialog.transient(self.root)
        ttk.Label(dialog, text="SCAN HISTORY & OUTCOME PROGRESS", style="Section.TLabel").pack(anchor="w", padx=14, pady=12)
        columns = ("id", "timestamp", "preset", "matches", "outcomes")
        tree = ttk.Treeview(dialog, columns=columns, show="headings")
        headings = ("RUN", "TIMESTAMP", "PRESET", "MATCHES", "OUTCOMES")
        widths = (60, 210, 180, 80, 110)
        for column, heading, width in zip(columns, headings, widths):
            tree.heading(column, text=heading)
            tree.column(column, width=width, anchor="center")
        for run_id, timestamp, preset, matches, complete, total in self.controller.recent_scan_runs():
            tree.insert("", "end", values=(run_id, timestamp, preset, matches, f"{complete or 0} / {total or 0}"))
        tree.pack(fill="both", expand=True, padx=14, pady=(0, 8))
        ttk.Label(
            dialog,
            text="Outcome jobs remain pending until a real market-data provider is configured. Simulated data is used only by automated tests.",
            style="Muted.TLabel", wraplength=700,
        ).pack(anchor="w", padx=14, pady=(0, 12))

    def _display_results(self, results: list[ScanResult]) -> None:
        self.visible_results = list(results)
        self._render_results(self.visible_results)
        self.card_vars["matches"].set(str(len(results)))
        if results:
            self.card_vars["top"].set(f"{results[0].score} / 100")
            self.card_vars["rvol"].set(f"{sum(r.stock.rvol for r in results) / len(results):.2f}")
            self.card_vars["change"].set(f"{sum(r.stock.latest_percent_change for r in results) / len(results):+.2f}%")
            self.card_vars["volume"].set(self._compact(sum(r.stock.current_volume for r in results)))
        else:
            for key in ("top", "rvol", "change", "volume"):
                self.card_vars[key].set("--")

    def _render_results(self, results: list[ScanResult]) -> None:
        self.results.delete(*self.results.get_children())
        self.result_lookup.clear()
        for rank, result in enumerate(results, start=1):
            s = result.stock
            tag = "positive" if s.latest_percent_change >= 0 else "negative"
            item = self.results.insert("", "end", tags=(tag,), values=(
                rank, s.symbol, f"${s.price:.2f}", f"{s.latest_percent_change:+.2f}%",
                f"{s.rvol:.2f}", self._compact(s.current_volume), self._compact(s.avg_volume_20d),
                f"{s.atr_percent:.2f}%", self._compact(s.float_shares), result.score,
            ))
            self.result_lookup[item] = result
        children = self.results.get_children()
        if children:
            self.results.selection_set(children[0])
            self.results.focus(children[0])
            self._show_selection()
        else:
            self.detail_symbol.set("No stocks match the current search or filters")
            self.pass_reasons.set("")
            self.fail_reasons.set("")
            self.breakdown_var.set("")

    def _apply_search(self) -> None:
        query = self.search_var.get().strip().upper()
        matches = [result for result in self.visible_results if query in result.stock.symbol.upper()]
        self._render_results(matches)
        self.match_var.set(f"Showing: {len(matches)} of {len(self.visible_results)}")

    def _sort_results(self, column: str) -> None:
        if self.sort_column == column:
            self.sort_reverse = not self.sort_reverse
        else:
            self.sort_column = column
            self.sort_reverse = column not in ("rank", "symbol")
        original_rank = {id(result): rank for rank, result in enumerate(self.visible_results)}
        getters = {
            "rank": lambda r: original_rank[id(r)], "symbol": lambda r: r.stock.symbol,
            "price": lambda r: r.stock.price, "change": lambda r: r.stock.latest_percent_change,
            "rvol": lambda r: r.stock.rvol, "volume": lambda r: r.stock.current_volume,
            "avg20": lambda r: r.stock.avg_volume_20d, "atrp": lambda r: r.stock.atr_percent,
            "float": lambda r: r.stock.float_shares, "score": lambda r: r.score,
        }
        self.visible_results.sort(key=getters[column], reverse=self.sort_reverse)
        self._apply_search()

    def _choose_columns(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("Visible result columns")
        dialog.transient(self.root)
        dialog.grab_set()
        selected = set(self.results.cget("displaycolumns"))
        if "#all" in selected:
            selected = set(RESULT_COLUMNS)
        variables: dict[str, tk.BooleanVar] = {}
        for row, column in enumerate(RESULT_COLUMNS):
            variable = tk.BooleanVar(value=column in selected)
            variables[column] = variable
            ttk.Checkbutton(dialog, text=column.replace("avg20", "20D Avg Volume").replace("atrp", "ATRP%").replace("_", " ").title(), variable=variable).grid(
                row=row, column=0, sticky="w", padx=18, pady=4
            )

        def apply() -> None:
            columns = tuple(column for column in RESULT_COLUMNS if variables[column].get())
            if not columns:
                messagebox.showerror("Columns", "At least one column must remain visible.", parent=dialog)
                return
            self.results.configure(displaycolumns=columns)
            dialog.destroy()

        ttk.Button(dialog, text="APPLY", style="Accent.TButton", command=apply).grid(row=len(RESULT_COLUMNS), column=0, sticky="ew", padx=18, pady=12)

    def _show_selection(self, _event: object = None) -> None:
        selected = self.results.selection()
        if not selected:
            return
        result = self.result_lookup[selected[0]]
        s = result.stock
        self.detail_symbol.set(s.symbol)
        values = {
            "score": f"{result.score} / 100", "price": f"${s.price:.2f}",
            "change": f"{s.latest_percent_change:+.2f}%", "rvol": f"{s.rvol:.2f}",
            "atrp": f"{s.atr_percent:.2f}%", "volume": self._compact(s.current_volume),
            "avg20": self._compact(s.avg_volume_20d), "float": self._compact(s.float_shares),
        }
        for key, value in values.items():
            self.detail_vars[key].set(value)
        self.info_vars["vwap"].set(self._context_vwap(s))
        self.info_vars["gap"].set(self._optional_percent(s.gap_percent))
        self.info_vars["smas"].set(" / ".join(self._yes_no(value) for value in (s.above_sma_20, s.above_sma_50, s.above_sma_200)))
        self.info_vars["premarket"].set(f"{self._optional_percent(s.premarket_percent_change)} | {self._compact(s.premarket_volume) if s.premarket_volume is not None else 'N/A'}")
        self.info_vars["dollar_volume"].set(f"${self._compact(round(s.dollar_volume))}")
        self.info_vars["rotation"].set("N/A" if s.float_rotation is None else f"{s.float_rotation:.2f}x")
        self.info_vars["hod"].set(self._optional_percent(s.distance_from_high_percent))
        self.info_vars["positions"].set(f"{self._optional_percent(s.day_range_position)} / {self._optional_percent(s.week_52_position)}")
        self.info_vars["market_cap"].set("N/A" if s.market_cap is None else f"${self._compact(round(s.market_cap))}")
        self.info_vars["short_float"].set(self._optional_percent(s.short_float_percent))
        passed = [item for item in result.evaluations if item.passed]
        failed = [item for item in result.evaluations if not item.passed]
        self.pass_reasons.set("PASSED  " + "   ".join(f"✓ {item.name} {item.requirement}" for item in passed))
        self.fail_reasons.set(
            "FAILED SCORE TARGETS  " + "   ".join(f"✕ {item.name} {item.requirement}" for item in failed)
            if failed else "FAILED SCORE TARGETS  None"
        )
        self.breakdown_var.set("   ".join(
            f"{item.category}: {item.earned}/{item.available}" for item in result.score_breakdown
        ))

    def _close(self) -> None:
        try:
            self.controller.save_settings({
                "theme": self.theme_var.get(),
                "last_preset": self.preset_var.get(),
                "last_csv": str(self.controller.state.input_path),
                "window_geometry": self.root.geometry(),
                "visible_columns": list(self.results.cget("displaycolumns")),
                "save_snapshots": self.save_snapshot_var.get(),
            })
        finally:
            self.root.destroy()

    def _set_theme(self, display_name: str) -> None:
        theme = load_theme(self.theme_paths[display_name])
        self.root.configure(bg=theme["window"])
        self.style.theme_use("clam")
        self.style.configure(".", background=theme["window"], foreground=theme["text"], fieldbackground=theme["input"], bordercolor=theme["border"], font=("Segoe UI", 10))
        self.style.configure("TFrame", background=theme["window"])
        self.style.configure("Header.TFrame", background=theme["window"])
        self.style.configure("Panel.TFrame", background=theme["panel"])
        self.style.configure("Ticker.TFrame", background=theme["panel_alt"])
        self.style.configure("Market.TFrame", background=theme["panel_alt"])
        self.style.configure("Card.TFrame", background=theme["panel_alt"], relief="solid", borderwidth=1)
        self.style.configure("TLabel", background=theme["window"], foreground=theme["text"])
        self.style.configure("Title.TLabel", background=theme["window"], font=("Segoe UI", 16, "bold"), foreground=theme["text"])
        self.style.configure("Logo.TLabel", background=theme["window"], font=("Segoe UI", 24, "bold"), foreground=theme["accent"])
        self.style.configure("Kicker.TLabel", background=theme["window"], font=("Segoe UI", 8), foreground=theme["muted"])
        self.style.configure("HeaderMuted.TLabel", background=theme["panel_alt"], foreground=theme["muted"])
        self.style.configure("TickerLabel.TLabel", background=theme["panel_alt"], font=("Segoe UI", 9, "bold"), foreground=theme["text"])
        self.style.configure("Positive.TLabel", background=theme["panel_alt"], foreground=theme["positive"], font=("Segoe UI", 9, "bold"))
        self.style.configure("Negative.TLabel", background=theme["panel_alt"], foreground=theme["negative"], font=("Segoe UI", 9, "bold"))
        self.style.configure("Live.TLabel", background=theme["panel_alt"], foreground=theme["positive"], font=("Segoe UI", 9, "bold"))
        self.style.configure("Section.TLabel", font=("Segoe UI", 11, "bold"), foreground=theme["accent"])
        self.style.configure("DetailTitle.TLabel", font=("Segoe UI", 16, "bold"), foreground=theme["text"])
        self.style.configure("CardLabel.TLabel", background=theme["panel_alt"], foreground=theme["muted"], font=("Segoe UI", 8, "bold"))
        self.style.configure("CardValue.TLabel", background=theme["panel_alt"], foreground=theme["accent"], font=("Segoe UI", 18, "bold"))
        self.style.configure("Placeholder.TLabel", foreground=theme["muted"], font=("Segoe UI", 11, "italic"))
        self.style.configure("Pass.TLabel", foreground=theme["positive"], font=("Segoe UI", 9))
        self.style.configure("Fail.TLabel", foreground=theme["negative"], font=("Segoe UI", 9))
        self.style.configure("Breakdown.TLabel", foreground=theme["text"], font=("Segoe UI", 9, "bold"))
        self.style.configure("Muted.TLabel", foreground=theme["muted"])
        self.style.configure("Status.TLabel", background=theme["panel"], foreground=theme["muted"])
        self.style.configure("TEntry", fieldbackground=theme["input"], foreground=theme["text"], insertcolor=theme["text"])
        self.style.configure("TCombobox", fieldbackground=theme["input"], foreground=theme["text"])
        self.style.configure("Treeview", background=theme["panel"], fieldbackground=theme["panel"], foreground=theme["text"], rowheight=27)
        self.style.configure("Treeview.Heading", background=theme["panel_alt"], foreground=theme["text"], font=("Segoe UI", 9, "bold"))
        self.style.map("Treeview", background=[("selected", theme["selection"])], foreground=[("selected", theme["text"])])
        self.style.configure("Accent.TButton", background=theme["accent"], foreground=theme["window"], font=("Segoe UI", 11, "bold"))
        self.style.map("Accent.TButton", background=[("active", theme["positive"])])
        self.style.configure("TLabelframe", background=theme["panel"], foreground=theme["text"])
        self.style.configure("TLabelframe.Label", background=theme["panel"], foreground=theme["muted"])
        self.style.configure("Nav.TButton", background=theme["window"], foreground=theme["muted"], borderwidth=0, padding=(10, 7), font=("Segoe UI", 9))
        self.style.configure("NavActive.TButton", background=theme["panel_alt"], foreground=theme["accent"], borderwidth=0, padding=(10, 7), font=("Segoe UI", 9, "bold"))
        self.style.configure("Quick.TButton", padding=(4, 4), font=("Segoe UI", 8))
        self.results.tag_configure("positive", foreground=theme["positive"])
        self.results.tag_configure("negative", foreground=theme["negative"])
        self.filter_canvas.configure(background=theme["panel"])
        self.controller.state.theme_name = Path(self.theme_paths[display_name]).stem
        self.status_var.set(f"Theme: {display_name}")

    @staticmethod
    def _compact(value: int) -> str:
        if value >= 1_000_000_000:
            return f"{value / 1_000_000_000:.2f}B"
        if value >= 1_000_000:
            return f"{value / 1_000_000:.2f}M"
        if value >= 1_000:
            return f"{value / 1_000:.0f}K"
        return str(value)

    @staticmethod
    def _yes_no(value: bool | None) -> str:
        return "N/A" if value is None else ("Yes" if value else "No")

    @staticmethod
    def _optional_percent(value: float | None) -> str:
        return "N/A" if value is None else f"{value:+.2f}%"

    @classmethod
    def _context_vwap(cls, stock) -> str:
        if stock.vwap is None:
            return "N/A"
        return f"{cls._yes_no(stock.above_vwap)} ({cls._optional_percent(stock.distance_from_vwap_percent)})"
