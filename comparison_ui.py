import ui_thread_safe
import customtkinter as ctk
import pandas as pd
import numpy as np
import threading
import time
from tksheet import Sheet
import tkinter.messagebox as messagebox
import tkinter.filedialog as filedialog
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates


class StockIndexComparisonFrame(ctk.CTkFrame):
    """
    Institutional Multi-Asset Relative Strength Comparison Engine:
    Compares stocks, sector baskets, and benchmark indices over multiple timeframes
    with dynamic asset addition (+ Sector / + Stock / + Index), removable chips (- / ✕),
    normalized 100% relative strength charts, and quantitative alpha/beta scorecard.
    """
    def __init__(self, master, mapi, db=None):
        super().__init__(master, corner_radius=15)
        self.mapi = mapi
        self.db = db
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Active Comparison Basket
        self.current_symbols = ["TCS", "INFY", "^NSEI"]
        self.current_benchmark = "^NSEI"
        self.current_timeframe = "3 Months"
        self._chart_canvas = None
        self._fig = None
        self._is_loading = False

        # Predefined Sectors and Constituent mapping
        self.sector_map = {
            "IT": ("^CNXIT", ["TCS", "INFY", "WIPRO", "HCLTECH", "TECHM"]),
            "Banking & Finance": ("^NSEBANK", ["HDFCBANK", "ICICIBANK", "SBIN", "AXISBANK", "KOTAKBANK"]),
            "Automobile": ("^CNXAUTO", ["MARUTI", "TATAMOTORS", "M&M", "BAJAJ-AUTO", "EICHERMOT"]),
            "Pharma & Healthcare": ("^CNXPHARMA", ["SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "LUPIN"]),
            "FMCG & Consumption": ("^CNXFMCG", ["ITC", "HINDUNILVR", "NESTLEIND", "BRITANNIA", "TATACONSUM"]),
            "Metals & Mining": ("^CNXMETAL", ["TATASTEEL", "JSWSTEEL", "HINDALCO", "VEDL", "COALINDIA"]),
            "Energy & Oil": ("^CNXENERGY", ["RELIANCE", "NTPC", "POWERGRID", "ONGC", "BPCL"]),
            "Financial Services": ("^CNXFIN", ["BAJFINANCE", "BAJAJFINSV", "CHOLAFIN", "SHRIRAMFIN", "PFC"]),
            "Realty & Infrastructure": ("^CNXINFRA", ["DLF", "GODREJPROP", "LT", "ADANIPORTS", "ULTRACEMCO"]),
        }

        # Predefined Indices
        self.index_options = [
            ("NIFTY 50", "^NSEI"),
            ("BANK NIFTY", "^NSEBANK"),
            ("NIFTY IT", "^CNXIT"),
            ("NIFTY AUTO", "^CNXAUTO"),
            ("NIFTY PHARMA", "^CNXPHARMA"),
            ("NIFTY METAL", "^CNXMETAL"),
            ("NIFTY FMCG", "^CNXFMCG"),
            ("NIFTY 500", "^CNX500"),
            ("S&P 500 (US)", "^GSPC"),
            ("NASDAQ 100 (US)", "^NDX"),
        ]

        self._build_header_and_controls()
        self._build_basket_chips_bar()
        self._build_insights_strip()
        self._build_display_panels()

        self.after(1000, self.run_comparison)

    def _build_header_and_controls(self):
        # 1. Header Bar
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(12, 4))

        t_left = ctk.CTkFrame(header, fg_color="transparent")
        t_left.pack(side="left")

        ctk.CTkLabel(
            t_left, text="⚖️ Stock & Index Relative Strength Comparison",
            font=ctk.CTkFont(size=22, weight="bold"), text_color="#38BDF8"
        ).pack(anchor="w")

        ctk.CTkLabel(
            t_left, text="Cross-Asset Normalized Performance, Alpha vs Benchmark, Beta Volatility & Correlation Analysis",
            font=ctk.CTkFont(size=11), text_color="#94A3B8"
        ).pack(anchor="w")

        btn_box = ctk.CTkFrame(header, fg_color="transparent")
        btn_box.pack(side="right")

        export_btn = ctk.CTkButton(
            btn_box, text="💾 EXPORT TO EXCEL", command=self.export_excel,
            font=ctk.CTkFont(size=12, weight="bold"), fg_color="#1F4E78",
            hover_color="#153655", height=32, width=140
        )
        export_btn.pack(side="right", padx=4)

        # 2. Control Input Bar
        ctrl_card = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=10, border_width=1, border_color="#334155")
        ctrl_card.grid(row=1, column=0, sticky="ew", padx=20, pady=(4, 6))

        c_row1 = ctk.CTkFrame(ctrl_card, fg_color="transparent")
        c_row1.pack(fill="x", padx=12, pady=8)

        # A. Sector Dropdown + Add Button
        sec_box = ctk.CTkFrame(c_row1, fg_color="transparent")
        sec_box.pack(side="left", padx=4)
        ctk.CTkLabel(sec_box, text="SECTOR / BASKET:", font=ctk.CTkFont(size=10, weight="bold"), text_color="#94A3B8").pack(anchor="w")
        
        self.sec_var = ctk.StringVar(value=list(self.sector_map.keys())[0])
        self.sec_dd = ctk.CTkOptionMenu(sec_box, variable=self.sec_var, values=list(self.sector_map.keys()), width=155, height=28)
        self.sec_dd.pack(side="left", pady=2)
        
        self.add_sec_btn = ctk.CTkButton(
            sec_box, text="➕ Sector", width=75, height=28,
            fg_color="#0284C7", hover_color="#0369A1", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_add_sector_clicked
        )
        self.add_sec_btn.pack(side="left", padx=(4, 0), pady=2)

        # B. Stock Selector / Search + Add Button
        stock_box = ctk.CTkFrame(c_row1, fg_color="transparent")
        stock_box.pack(side="left", padx=8)
        ctk.CTkLabel(stock_box, text="STOCK TICKER:", font=ctk.CTkFont(size=10, weight="bold"), text_color="#94A3B8").pack(anchor="w")

        popular_stocks = [
            "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "BHARTIARTL",
            "LT", "ITC", "BAJFINANCE", "MARUTI", "SUNPHARMA", "TATAMOTORS", "DIXON",
            "POLYCAB", "MCX", "DIVISLAB", "PATANJALI", "WIPRO", "HCLTECH"
        ]
        self.stock_var = ctk.StringVar(value="RELIANCE")
        self.stock_dd = ctk.CTkComboBox(stock_box, variable=self.stock_var, values=popular_stocks, width=135, height=28)
        self.stock_dd.pack(side="left", pady=2)

        self.add_stock_btn = ctk.CTkButton(
            stock_box, text="➕ Stock", width=70, height=28,
            fg_color="#0D9488", hover_color="#0F766E", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_add_stock_clicked
        )
        self.add_stock_btn.pack(side="left", padx=(4, 0), pady=2)

        # C. Major Indices Dropdown + Add Button
        idx_box = ctk.CTkFrame(c_row1, fg_color="transparent")
        idx_box.pack(side="left", padx=8)
        ctk.CTkLabel(idx_box, text="MAJOR INDEX:", font=ctk.CTkFont(size=10, weight="bold"), text_color="#94A3B8").pack(anchor="w")

        idx_names = [name for name, _ in self.index_options]
        self.idx_var = ctk.StringVar(value="BANK NIFTY")
        self.idx_dd = ctk.CTkOptionMenu(idx_box, variable=self.idx_var, values=idx_names, width=135, height=28)
        self.idx_dd.pack(side="left", pady=2)

        self.add_idx_btn = ctk.CTkButton(
            idx_box, text="➕ Index", width=70, height=28,
            fg_color="#7C3AED", hover_color="#6D28D9", font=ctk.CTkFont(size=11, weight="bold"),
            command=self._on_add_index_clicked
        )
        self.add_idx_btn.pack(side="left", padx=(4, 0), pady=2)

        # D. Benchmark Selector
        bm_box = ctk.CTkFrame(c_row1, fg_color="transparent")
        bm_box.pack(side="left", padx=8)
        ctk.CTkLabel(bm_box, text="BENCHMARK:", font=ctk.CTkFont(size=10, weight="bold"), text_color="#94A3B8").pack(anchor="w")

        self.bm_var = ctk.StringVar(value="NIFTY 50 (^NSEI)")
        bm_options = [
            "NIFTY 50 (^NSEI)",
            "BANK NIFTY (^NSEBANK)",
            "NIFTY IT (^CNXIT)",
            "NIFTY 500 (^CNX500)",
            "S&P 500 (^GSPC)",
            "NASDAQ 100 (^NDX)"
        ]
        self.bm_dd = ctk.CTkOptionMenu(bm_box, variable=self.bm_var, values=bm_options, width=160, height=28)
        self.bm_dd.pack(pady=2)

        # E. Timeframe Selector
        tf_box = ctk.CTkFrame(c_row1, fg_color="transparent")
        tf_box.pack(side="left", padx=8)
        ctk.CTkLabel(tf_box, text="TIMEFRAME:", font=ctk.CTkFont(size=10, weight="bold"), text_color="#94A3B8").pack(anchor="w")

        self.tf_var = ctk.StringVar(value="3 Months")
        tf_options = ["1 Week", "1 Month", "3 Months", "6 Months", "1 Year", "YTD", "3 Years", "5 Years"]
        self.tf_dd = ctk.CTkOptionMenu(tf_box, variable=self.tf_var, values=tf_options, width=105, height=28)
        self.tf_dd.pack(pady=2)

        # F. Run Button
        run_box = ctk.CTkFrame(c_row1, fg_color="transparent")
        run_box.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(run_box, text="", font=ctk.CTkFont(size=10)).pack()
        self.btn_run = ctk.CTkButton(
            run_box, text="🚀 COMPARE", command=self.run_comparison,
            font=ctk.CTkFont(size=12, weight="bold"), fg_color="#10B981",
            hover_color="#059669", width=110, height=30
        )
        self.btn_run.pack()

    def _build_basket_chips_bar(self):
        # Row for Active Asset Chips and Quick Presets
        basket_card = ctk.CTkFrame(self, fg_color="#0F172A", corner_radius=10, border_width=1, border_color="#334155")
        basket_card.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 6))

        b_row = ctk.CTkFrame(basket_card, fg_color="transparent")
        b_row.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(b_row, text="📌 Comparison Basket:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#38BDF8").pack(side="left", padx=(0, 8))

        # Flow container for active removable chips
        self.chips_frame = ctk.CTkFrame(b_row, fg_color="transparent")
        self.chips_frame.pack(side="left", fill="x", expand=True)

        # Presets & Reset
        p_right = ctk.CTkFrame(b_row, fg_color="transparent")
        p_right.pack(side="right")

        def set_preset(syms, bm):
            self.current_symbols = list(syms)
            self.bm_var.set(bm)
            self._render_basket_chips()
            self.run_comparison()

        ctk.CTkButton(p_right, text="IT Leaders", width=72, height=24, font=ctk.CTkFont(size=10), fg_color="#334155", command=lambda: set_preset(["TCS", "INFY", "WIPRO"], "NIFTY IT (^CNXIT)")).pack(side="left", padx=2)
        ctk.CTkButton(p_right, text="Banking Titans", width=85, height=24, font=ctk.CTkFont(size=10), fg_color="#334155", command=lambda: set_preset(["HDFCBANK", "ICICIBANK", "SBIN"], "BANK NIFTY (^NSEBANK)")).pack(side="left", padx=2)
        ctk.CTkButton(p_right, text="Mega-Caps", width=75, height=24, font=ctk.CTkFont(size=10), fg_color="#334155", command=lambda: set_preset(["RELIANCE", "TCS", "HDFCBANK"], "NIFTY 50 (^NSEI)")).pack(side="left", padx=2)
        ctk.CTkButton(p_right, text="Major Indices", width=80, height=24, font=ctk.CTkFont(size=10), fg_color="#334155", command=lambda: set_preset(["^NSEBANK", "^CNXIT", "^CNXAUTO", "^GSPC"], "NIFTY 50 (^NSEI)")).pack(side="left", padx=2)

        self.clear_btn = ctk.CTkButton(
            p_right, text="🗑️ Clear", width=60, height=24,
            fg_color="#B91C1C", hover_color="#991B1B", font=ctk.CTkFont(size=10, weight="bold"),
            command=self._on_clear_all_clicked
        )
        self.clear_btn.pack(side="left", padx=(6, 0))

        self._render_basket_chips()

    def _render_basket_chips(self):
        for w in self.chips_frame.winfo_children():
            w.destroy()

        if not self.current_symbols:
            ctk.CTkLabel(self.chips_frame, text="(Basket is empty. Select sectors, stocks or indices above)", font=ctk.CTkFont(size=11), text_color="#64748B").pack(side="left")
            return

        for sym in self.current_symbols:
            chip = ctk.CTkFrame(self.chips_frame, fg_color="#1E293B", corner_radius=12, border_width=1, border_color="#475569")
            chip.pack(side="left", padx=3, pady=2)

            icon = "🏛️" if sym.startswith("^") else "📈"
            ctk.CTkLabel(chip, text=f"{icon} {sym}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#E2E8F0").pack(side="left", padx=(8, 4), pady=2)

            del_btn = ctk.CTkButton(
                chip, text="✕", width=18, height=18, corner_radius=9,
                fg_color="#EF4444", hover_color="#DC2626", font=ctk.CTkFont(size=9, weight="bold"),
                command=lambda s=sym: self._remove_symbol(s)
            )
            del_btn.pack(side="left", padx=(0, 5), pady=2)

    def _on_add_sector_clicked(self):
        sec = self.sec_var.get()
        if sec in self.sector_map:
            sec_idx, sec_stocks = self.sector_map[sec]
            added = False
            if sec_idx not in self.current_symbols:
                self.current_symbols.append(sec_idx)
                added = True
            for s in sec_stocks[:2]:
                if s not in self.current_symbols:
                    self.current_symbols.append(s)
                    added = True
            if added:
                self._render_basket_chips()
                self.run_comparison()

    def _on_add_stock_clicked(self):
        s = self.stock_var.get().strip().upper()
        if s:
            s_clean = s.replace('.NS', '').replace('.BO', '')
            if s_clean not in self.current_symbols:
                self.current_symbols.append(s_clean)
                self._render_basket_chips()
                self.run_comparison()

    def _on_add_index_clicked(self):
        selected_name = self.idx_var.get()
        ticker = None
        for name, tk in self.index_options:
            if name == selected_name:
                ticker = tk
                break
        if not ticker:
            ticker = "^NSEI"

        if ticker not in self.current_symbols:
            self.current_symbols.append(ticker)
            self._render_basket_chips()
            self.run_comparison()

    def _remove_symbol(self, sym):
        if sym in self.current_symbols:
            self.current_symbols.remove(sym)
            self._render_basket_chips()
            self.run_comparison()

    def _on_clear_all_clicked(self):
        self.current_symbols = ["^NSEI"]
        self._render_basket_chips()
        self.run_comparison()

    def _build_insights_strip(self):
        self.insights_card = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=10, border_width=1, border_color="#334155")
        self.insights_card.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 6))
        self.insights_card.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.insight_labels = []
        cards_info = [
            ("👑 TOP ALPHA LEADER", "Calculating...", "Leading vs Benchmark", "#4ADE80"),
            ("⚡ MOMENTUM PLAY", "Calculating...", "High Beta / Volatility", "#38BDF8"),
            ("🛡️ DEFENSIVE ANCHOR", "Calculating...", "Lowest Relative Drawdown", "#FBBF24"),
            ("⚠️ LAGGING ASSET", "Calculating...", "Worst Alpha Drag", "#F87171"),
        ]
        for idx, (t, v, sub, clr) in enumerate(cards_info):
            box = ctk.CTkFrame(self.insights_card, fg_color="#0F172A", corner_radius=8, border_width=1, border_color="#334155")
            box.grid(row=0, column=idx, padx=5, pady=6, sticky="nsew")

            ctk.CTkLabel(box, text=t, font=ctk.CTkFont(size=10, weight="bold"), text_color="#94A3B8").pack(anchor="w", padx=10, pady=(6, 2))
            val_lbl = ctk.CTkLabel(box, text=v, font=ctk.CTkFont(size=13, weight="bold"), text_color=clr)
            val_lbl.pack(anchor="w", padx=10, pady=0)
            sub_lbl = ctk.CTkLabel(box, text=sub, font=ctk.CTkFont(size=10), text_color="#64748B")
            sub_lbl.pack(anchor="w", padx=10, pady=(0, 6))

            self.insight_labels.append((val_lbl, sub_lbl))

    def _build_display_panels(self):
        self.display_container = ctk.CTkFrame(self, fg_color="transparent")
        self.display_container.grid(row=4, column=0, sticky="nsew", padx=20, pady=(0, 12))
        self.display_container.grid_rowconfigure(0, weight=3) # Chart
        self.display_container.grid_rowconfigure(1, weight=2) # Table
        self.display_container.grid_columnconfigure(0, weight=1)

        # Chart Frame
        self.chart_frame = ctk.CTkFrame(self.display_container, corner_radius=10, fg_color="#0F172A", border_width=1, border_color="#334155")
        self.chart_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.chart_frame.grid_rowconfigure(0, weight=1)
        self.chart_frame.grid_columnconfigure(0, weight=1)

        # Table Frame
        self.table_frame = ctk.CTkFrame(self.display_container, corner_radius=10)
        self.table_frame.grid(row=1, column=0, sticky="nsew")
        self.table_frame.grid_rowconfigure(0, weight=1)
        self.table_frame.grid_columnconfigure(0, weight=1)

        self.cols = [
            "Symbol / Asset", "Asset Type", "Current LTP", "Period Return %",
            "Alpha vs Benchmark", "Beta (Volatility)", "Correlation",
            "Period High", "Period Low", "Outperformance Verdict"
        ]
        self.sheet = Sheet(self.table_frame, headers=self.cols)
        self.sheet.enable_bindings((
            "single_select", "row_select", "column_width_resize", "arrowkeys", "copy", "rc_sort", "column_select"
        ))
        if ctk.get_appearance_mode() == "Dark":
            self.sheet.change_theme("dark")
        else:
            self.sheet.change_theme("light blue")

        self.sheet.set_options(font=("Segoe UI", 10, "normal"), header_font=("Segoe UI", 11, "bold"))
        self.sheet.pack(fill="both", expand=True, padx=4, pady=4)

    def run_comparison(self):
        if self._is_loading:
            return
        self._is_loading = True
        self.btn_run.configure(text="⏳ Loading...", state="disabled")

        bm_selection = self.bm_var.get().strip()
        tf = self.tf_var.get().strip()

        bm_map = {
            "NIFTY 50 (^NSEI)": "^NSEI",
            "BANK NIFTY (^NSEBANK)": "^NSEBANK",
            "NIFTY IT (^CNXIT)": "^CNXIT",
            "NIFTY 500 (^CNX500)": "^CNX500",
            "S&P 500 (^GSPC)": "^GSPC",
            "NASDAQ 100 (^NDX)": "^NDX"
        }
        bm_ticker = bm_map.get(bm_selection, "^NSEI")

        symbols = [s for s in self.current_symbols if s]
        if not symbols:
            symbols = ["TCS", "INFY"]

        threading.Thread(target=self._fetch_and_render_bg, args=(symbols, bm_ticker, tf), daemon=True).start()

    def _fetch_and_render_bg(self, symbols, benchmark, timeframe):
        import yfinance as yf

        tf_to_period = {
            "1 Week": "5d", "1 Month": "1mo", "3 Months": "3mo",
            "6 Months": "6mo", "1 Year": "1y", "YTD": "ytd",
            "3 Years": "3y", "5 Years": "5y"
        }
        period = tf_to_period.get(timeframe, "3mo")

        # Prepare normalized tickers for yfinance
        all_assets = list(symbols)
        if benchmark not in all_assets:
            all_assets.append(benchmark)

        mapped_tickers = {}
        for a in all_assets:
            if a.startswith("^") or "=" in a:
                mapped_tickers[a] = a
            else:
                mapped_tickers[a] = f"{a}.NS"

        download_list = list(set(mapped_tickers.values()))
        try:
            hist_df = yf.download(download_list, period=period, progress=False)
            close_df = hist_df.get('Close', pd.DataFrame())
        except Exception as e:
            print("Comparison download note:", e)
            close_df = pd.DataFrame()

        def extract_series(cdf, asset_key):
            ytk = mapped_tickers.get(asset_key, asset_key)
            candidates = [ytk, asset_key, f"{asset_key}.NS", f"{asset_key}.BO", asset_key.upper()]
            for c in candidates:
                if c in cdf.columns:
                    s = cdf[c].dropna()
                    if not s.empty:
                        return s
                if isinstance(cdf.columns, pd.MultiIndex):
                    try:
                        s = cdf.xs(c, level=-1, axis=1).dropna()
                        if not s.empty:
                            return s.iloc[:, 0] if isinstance(s, pd.DataFrame) else s
                    except Exception:
                        pass

            # Fallback to local SQL Server database for Indian stocks
            if self.db and not asset_key.startswith("^"):
                try:
                    with self.db.get_connection() as conn:
                        q = f"""
                        SELECT TOP 75 SnapShotDate, CLOSE_PRIC 
                        FROM FUTURES_FNO_BhavCopy_History_Transformed_New 
                        WHERE SYMBOL = '{asset_key}'
                        ORDER BY SnapShotDate DESC
                        """
                        df_s = pd.read_sql(q, conn)
                        if not df_s.empty:
                            df_s = df_s.sort_values('SnapShotDate')
                            idx = pd.to_datetime(df_s['SnapShotDate'])
                            return pd.Series(df_s['CLOSE_PRIC'].astype(float).values, index=idx)
                except Exception:
                    pass

            return pd.Series(dtype=float)

        processed_data = {}
        bm_series = extract_series(close_df, benchmark)
        bm_ret = 0.0
        if not bm_series.empty and len(bm_series) >= 2:
            bm_ret = ((float(bm_series.iloc[-1]) - float(bm_series.iloc[0])) / float(bm_series.iloc[0])) * 100
            processed_data[benchmark] = (bm_series / float(bm_series.iloc[0])) * 100.0

        scorecard_rows = []
        alpha_records = []

        for a in all_assets:
            s = extract_series(close_df, a)
            if not s.empty and len(s) >= 2:
                start_p = float(s.iloc[0])
                end_p = float(s.iloc[-1])
                ret = ((end_p - start_p) / start_p) * 100
                is_bm = (a == benchmark)
                alpha = ret - bm_ret if not is_bm else 0.0

                norm_series = (s / start_p) * 100.0
                processed_data[a] = norm_series

                # Beta & Correlation against benchmark
                beta_val = 1.0
                corr_val = 1.0
                if not is_bm and not bm_series.empty:
                    try:
                        aligned = pd.concat([s.pct_change(), bm_series.pct_change()], axis=1).dropna()
                        if len(aligned) > 5:
                            cov = np.cov(aligned.iloc[:, 0], aligned.iloc[:, 1])[0][1]
                            var = np.var(aligned.iloc[:, 1])
                            beta_val = round(cov / var, 2) if var > 0 else 1.0
                            corr_val = round(aligned.iloc[:, 0].corr(aligned.iloc[:, 1]), 2)
                    except Exception:
                        pass

                period_hi = float(s.max())
                period_lo = float(s.min())

                asset_type = "Benchmark Index" if is_bm else ("Sector Index" if a.startswith("^") else "Equity Stock")
                verdict = "BENCHMARK BASELINE" if is_bm else ("🚀 STRONG ALPHA" if alpha > 2.5 else ("✓ POSITIVE ALPHA" if alpha > 0 else "▼ UNDERPERFORMING"))

                curr_p_str = f"{end_p:,.2f}" if (a.startswith("^") or "=" in a) else f"₹{end_p:,.2f}"
                hi_str = f"{period_hi:,.2f}" if (a.startswith("^") or "=" in a) else f"₹{period_hi:,.2f}"
                lo_str = f"{period_lo:,.2f}" if (a.startswith("^") or "=" in a) else f"₹{period_lo:,.2f}"

                row_vals = [
                    a, asset_type, curr_p_str, f"{ret:+.2f}%",
                    f"{alpha:+.2f}%" if not is_bm else "0.00%", f"{beta_val:.2f}", f"{corr_val:.2f}",
                    hi_str, lo_str, verdict
                ]
                scorecard_rows.append(row_vals)

                if not is_bm:
                    alpha_records.append({'sym': a, 'ret': ret, 'alpha': alpha, 'beta': beta_val})

        try:
            self.after(0, lambda: self._render_results(processed_data, scorecard_rows, alpha_records, benchmark, timeframe))
        except Exception as err:
            print("Comparison render error:", err)

    def _render_results(self, processed_data, scorecard_rows, alpha_records, benchmark, timeframe):
        self._is_loading = False
        self.btn_run.configure(text="🚀 COMPARE", state="normal")

        # 1. Update Insights Strip
        if alpha_records:
            best_alpha = sorted(alpha_records, key=lambda x: x['alpha'], reverse=True)[0]
            worst_alpha = sorted(alpha_records, key=lambda x: x['alpha'])[0]
            highest_beta = sorted(alpha_records, key=lambda x: x['beta'], reverse=True)[0]
            defensive = sorted(alpha_records, key=lambda x: x['beta'])[0]

            self.insight_labels[0][0].configure(text=f"{best_alpha['sym']} ({best_alpha['alpha']:+.2f}% Alpha)")
            self.insight_labels[0][1].configure(text=f"Total Return: {best_alpha['ret']:+.2f}% | Beta: {best_alpha['beta']:.2f}")

            self.insight_labels[1][0].configure(text=f"{highest_beta['sym']} (Beta: {highest_beta['beta']:.2f})")
            self.insight_labels[1][1].configure(text=f"Alpha: {highest_beta['alpha']:+.2f}% | Return: {highest_beta['ret']:+.2f}%")

            self.insight_labels[2][0].configure(text=f"{defensive['sym']} (Beta: {defensive['beta']:.2f})")
            self.insight_labels[2][1].configure(text=f"Alpha: {defensive['alpha']:+.2f}% | Low Drawdown Anchor")

            self.insight_labels[3][0].configure(text=f"{worst_alpha['sym']} ({worst_alpha['alpha']:+.2f}% Alpha)")
            self.insight_labels[3][1].configure(text=f"Total Return: {worst_alpha['ret']:+.2f}% | Underperforming")

        # 2. Update Table
        self.sheet.set_sheet_data(scorecard_rows)
        self.sheet.set_all_column_widths(125)
        self.sheet.column_width(column=0, width=140)
        self.sheet.column_width(column=1, width=130)
        self.sheet.column_width(column=9, width=180)

        for r_idx, r in enumerate(scorecard_rows):
            ret_str = str(r[3])
            alpha_str = str(r[4])
            if "+" in ret_str: self.sheet.highlight_cells(row=r_idx, column=3, fg="#00E676")
            elif "-" in ret_str: self.sheet.highlight_cells(row=r_idx, column=3, fg="#FF5252")

            if "+" in alpha_str and alpha_str != "0.00%": self.sheet.highlight_cells(row=r_idx, column=4, fg="#00E676")
            elif "-" in alpha_str: self.sheet.highlight_cells(row=r_idx, column=4, fg="#FF5252")

        # 3. Render Chart
        for w in self.chart_frame.winfo_children():
            w.destroy()

        fig, ax = plt.subplots(figsize=(10, 4.0), dpi=100)
        fig.patch.set_facecolor("#1E293B")
        ax.set_facecolor("#0F172A")

        palette = ["#38BDF8", "#4ADE80", "#FBBF24", "#F43F5E", "#A855F7", "#FB923C", "#2DD4BF", "#E879F9", "#60A5FA"]
        color_idx = 0

        # Plot Benchmark first
        if benchmark in processed_data:
            bm_s = processed_data[benchmark]
            bm_ret = float(bm_s.iloc[-1]) - 100.0
            ax.plot(bm_s.index, bm_s.values, color="#94A3B8", linewidth=2.0, linestyle="--", label=f"{benchmark} ({bm_ret:+.1f}%) [Benchmark]")

        # Plot other assets
        for sym, s in processed_data.items():
            if sym == benchmark or s.empty:
                continue
            clr = palette[color_idx % len(palette)]
            color_idx += 1
            ret_pct = float(s.iloc[-1]) - 100.0
            ax.plot(s.index, s.values, color=clr, linewidth=2.2, label=f"{sym} ({ret_pct:+.1f}%)")

        ax.axhline(100.0, color="#475569", linestyle=":", linewidth=1.0, alpha=0.7)
        ax.set_title(f"Normalized Relative Strength (Rebased to 100% | {timeframe})", fontsize=12, fontweight="bold", color="#F1F5F9", pad=10)
        ax.set_ylabel("Normalized Return Base 100%", fontsize=10, color="#94A3B8")

        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d" if "Year" in timeframe else "%b-%d"))
        ax.tick_params(colors="#94A3B8", labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#334155")
        ax.grid(True, linestyle=":", alpha=0.3, color="#475569")
        ax.legend(facecolor="#1E293B", edgecolor="#334155", labelcolor="#F1F5F9", fontsize=8, loc="upper left")
        fig.tight_layout()

        self._chart_canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        self._chart_canvas.draw()
        self._chart_canvas.get_tk_widget().pack(fill="both", expand=True)

    def export_excel(self):
        data = self.sheet.get_sheet_data()
        if not data:
            messagebox.showwarning("Warning", "No comparison data to export.")
            return
        df = pd.DataFrame(data, columns=self.cols)
        fn = filedialog.asksaveasfilename(defaultextension=".xlsx", initialfile="Relative_Strength_Comparison.xlsx", title="Export Comparison Data")
        if fn:
            try:
                df.to_excel(fn, index=False)
                messagebox.showinfo("Success", f"Comparison exported successfully to:\n{fn}")
            except Exception as e:
                messagebox.showerror("Error", f"Could not export: {e}")
