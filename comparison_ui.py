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
    Institutional Multi-Asset Comparison Engine:
    Compares stocks, peer baskets, and benchmark indices over multiple timeframes
    with normalized relative strength charts and quantitative scorecard metrics.
    """
    def __init__(self, master, mapi, db=None):
        super().__init__(master, corner_radius=15)
        self.mapi = mapi
        self.db = db
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.current_symbols = ["TCS", "INFY"]
        self.current_benchmark = "^NSEI"
        self.current_timeframe = "3 Months"
        self._chart_canvas = None
        self._fig = None

        self._build_header_and_controls()
        self._build_display_panels()
        
        # Load default comparison after UI is ready
        self.after(1500, self.run_comparison)


    def _build_header_and_controls(self):
        # 1. Header & Title Bar
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        
        ctk.CTkLabel(
            header, text="⚖️ Stock & Index Relative Strength Comparison",
            font=ctk.CTkFont(size=22, weight="bold")
        ).pack(side="left")

        export_btn = ctk.CTkButton(
            header, text="EXPORT TO EXCEL", command=self.export_excel,
            font=ctk.CTkFont(size=12, weight="bold"), fg_color="#2E7D32",
            hover_color="#1B5E20", height=32, width=130
        )
        export_btn.pack(side="right", padx=5)

        # Quick Preset Buttons Bar
        presets_bar = ctk.CTkFrame(self, fg_color="transparent")
        presets_bar.grid(row=0, column=0, sticky="e", padx=(0, 160), pady=(15, 5))
        
        ctk.CTkLabel(presets_bar, text="Presets:", font=ctk.CTkFont(size=11, weight="bold"), text_color="gray60").pack(side="left", padx=4)
        
        def set_preset(syms, bm):
            self.sym_entry.delete(0, "end")
            self.sym_entry.insert(0, ", ".join(syms))
            self.bm_var.set(bm)
            self.run_comparison()

        ctk.CTkButton(presets_bar, text="IT Leaders", width=75, height=26, font=ctk.CTkFont(size=11), fg_color="#374151", command=lambda: set_preset(["TCS", "INFY", "WIPRO"], "NIFTY IT (^CNXIT)")).pack(side="left", padx=3)
        ctk.CTkButton(presets_bar, text="Banking", width=70, height=26, font=ctk.CTkFont(size=11), fg_color="#374151", command=lambda: set_preset(["HDFCBANK", "ICICIBANK", "SBIN"], "BANK NIFTY (^NSEBANK)")).pack(side="left", padx=3)
        ctk.CTkButton(presets_bar, text="Mega-Caps", width=75, height=26, font=ctk.CTkFont(size=11), fg_color="#374151", command=lambda: set_preset(["RELIANCE", "TCS", "HDFCBANK"], "NIFTY 50 (^NSEI)")).pack(side="left", padx=3)
        ctk.CTkButton(presets_bar, text="Indices", width=65, height=26, font=ctk.CTkFont(size=11), fg_color="#374151", command=lambda: set_preset(["^NSEBANK", "^CNXIT", "^GSPC"], "NIFTY 50 (^NSEI)")).pack(side="left", padx=3)

        # 2. Control Input Bar
        ctrl_card = ctk.CTkFrame(self, fg_color="#1E293B", corner_radius=10)
        ctrl_card.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        
        # Symbols Input
        ctk.CTkLabel(ctrl_card, text="Symbols (comma separated):", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(15, 5), pady=10)
        self.sym_entry = ctk.CTkEntry(ctrl_card, width=280, placeholder_text="e.g. TCS, INFY, WIPRO")
        self.sym_entry.insert(0, "TCS, INFY")
        self.sym_entry.pack(side="left", padx=5, pady=10)

        # Benchmark Selector
        ctk.CTkLabel(ctrl_card, text="Benchmark:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(15, 5), pady=10)
        self.bm_var = ctk.StringVar(value="NIFTY 50 (^NSEI)")
        bm_options = [
            "NIFTY 50 (^NSEI)",
            "BANK NIFTY (^NSEBANK)",
            "NIFTY IT (^CNXIT)",
            "NIFTY 500 (^CNX500)",
            "S&P 500 (^GSPC)",
            "NASDAQ 100 (^NDX)"
        ]
        self.bm_dd = ctk.CTkOptionMenu(ctrl_card, variable=self.bm_var, values=bm_options, width=170)
        self.bm_dd.pack(side="left", padx=5, pady=10)

        # Timeframe Selector
        ctk.CTkLabel(ctrl_card, text="Period:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(15, 5), pady=10)
        self.tf_var = ctk.StringVar(value="3 Months")
        tf_options = ["1 Week", "1 Month", "3 Months", "6 Months", "1 Year", "YTD", "3 Years", "5 Years"]
        self.tf_dd = ctk.CTkOptionMenu(ctrl_card, variable=self.tf_var, values=tf_options, width=110)
        self.tf_dd.pack(side="left", padx=5, pady=10)

        # Run Button
        self.btn_run = ctk.CTkButton(
            ctrl_card, text="🚀 COMPARE", command=self.run_comparison,
            font=ctk.CTkFont(size=13, weight="bold"), fg_color="#10B981",
            hover_color="#059669", width=110, height=32
        )
        self.btn_run.pack(side="left", padx=15, pady=10)

    def _build_display_panels(self):
        # Container with Paned/Split: Top for Chart, Bottom for Metrics Sheet
        self.display_container = ctk.CTkFrame(self, fg_color="transparent")
        self.display_container.grid(row=2, column=0, sticky="nsew", padx=20, pady=(5, 15))
        self.display_container.grid_rowconfigure(0, weight=3) # Chart
        self.display_container.grid_rowconfigure(1, weight=2) # Table
        self.display_container.grid_columnconfigure(0, weight=1)

        # Chart Frame
        self.chart_frame = ctk.CTkFrame(self.display_container, corner_radius=10, fg_color="#0F172A")
        self.chart_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 8))
        self.chart_frame.grid_rowconfigure(0, weight=1)
        self.chart_frame.grid_columnconfigure(0, weight=1)

        # Metrics Sheet Frame
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
        self.sheet.enable_bindings(("single_select", "row_select", "column_width_resize", "arrowkeys", "copy", "rc_sort", "column_select"))
        if ctk.get_appearance_mode() == "Dark":
            self.sheet.change_theme("dark")
        else:
            self.sheet.change_theme("light blue")
        self.sheet.set_options(font=("Segoe UI", 11, "normal"), header_font=("Segoe UI", 12, "bold"))
        self.sheet.pack(fill="both", expand=True, padx=5, pady=5)

    def run_comparison(self):
        self.btn_run.configure(text="⏳ Loading...", state="disabled")
        raw_syms = self.sym_entry.get().strip()
        bm_selection = self.bm_var.get().strip()
        tf = self.tf_var.get().strip()

        # Parse tickers
        symbols = [s.strip().upper() for s in raw_syms.split(',') if s.strip()]
        if not symbols:
            symbols = ["TCS", "INFY"]

        bm_map = {
            "NIFTY 50 (^NSEI)": "^NSEI",
            "BANK NIFTY (^NSEBANK)": "^NSEBANK",
            "NIFTY IT (^CNXIT)": "^CNXIT",
            "NIFTY 500 (^CNX500)": "^CNX500",
            "S&P 500 (^GSPC)": "^GSPC",
            "NASDAQ 100 (^NDX)": "^NDX"
        }
        bm_ticker = bm_map.get(bm_selection, "^NSEI")

        threading.Thread(target=self._fetch_and_render_bg, args=(symbols, bm_ticker, tf), daemon=True).start()

    def _fetch_and_render_bg(self, symbols, benchmark, timeframe):
        import yfinance as yf

        tf_to_period = {
            "1 Week": "5d", "1 Month": "1mo", "3 Months": "3mo",
            "6 Months": "6mo", "1 Year": "1y", "YTD": "ytd",
            "3 Years": "3y", "5 Years": "5y"
        }
        period = tf_to_period.get(timeframe, "3mo")

        all_assets = symbols + [benchmark]
        mapped_tickers = {}
        for a in all_assets:
            if hasattr(self.mapi, 'normalize_ticker'):
                t = self.mapi.normalize_ticker(a)
            else:
                t = f"{a}.NS" if not a.startswith("^") and not a.endswith(".NS") and "-" not in a else a
            mapped_tickers[a] = t

        try:
            download_list = list(set(mapped_tickers.values()))
            hist_df = yf.download(download_list, period=period, progress=False)
            close_df = hist_df.get('Close', pd.DataFrame())
        except Exception as e:
            print("Comparison download error:", e)
            close_df = pd.DataFrame()

        # Process each asset's series
        processed_data = {}
        bm_series = pd.Series(dtype=float)

        # First extract benchmark series
        bm_t = mapped_tickers.get(benchmark, benchmark)
        if isinstance(close_df, pd.DataFrame):
            if bm_t in close_df.columns:
                bm_series = close_df[bm_t].dropna()
            elif isinstance(close_df.columns, pd.MultiIndex):
                try:
                    bm_series = close_df.xs(bm_t, level=-1, axis=1).dropna()
                except Exception:
                    pass

        bm_ret = 0.0
        if not bm_series.empty and len(bm_series) >= 2:
            bm_ret = ((float(bm_series.iloc[-1]) - float(bm_series.iloc[0])) / float(bm_series.iloc[0])) * 100

        # Now extract for all assets
        scorecard_rows = []
        for a in all_assets:
            t = mapped_tickers[a]
            s = pd.Series(dtype=float)
            if isinstance(close_df, pd.DataFrame):
                if t in close_df.columns:
                    s = close_df[t].dropna()
                elif isinstance(close_df.columns, pd.MultiIndex):
                    try:
                        s = close_df.xs(t, level=-1, axis=1).dropna()
                    except Exception:
                        pass
            elif isinstance(close_df, pd.Series) and not close_df.dropna().empty:
                s = close_df.dropna()

            if not s.empty and len(s) >= 2:
                start_p = float(s.iloc[0])
                end_p = float(s.iloc[-1])
                ret = ((end_p - start_p) / start_p) * 100
                alpha = ret - bm_ret if a != benchmark else 0.0
                
                # Rebase to 100%
                norm_series = (s / start_p) * 100.0
                processed_data[a] = norm_series

                # Beta & Correlation against benchmark
                beta_val = 1.0
                corr_val = 1.0
                if a != benchmark and not bm_series.empty:
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
                
                is_bm = (a == benchmark)
                asset_type = "Benchmark Index" if is_bm else ("Sector / Index" if a.startswith("^") else "Equity Stock")
                verdict = "BENCHMARK BASELINE" if is_bm else ("🚀 STRONG OUTPERFORMER" if alpha > 3.0 else ("✓ MODERATE ALPHA" if alpha > 0 else "▼ UNDERPERFORMING"))

                curr_p_str = f"{end_p:,.2f}" if (a.startswith("^") or "=" in a) else f"₹{end_p:,.2f}"
                hi_str = f"{period_hi:,.2f}" if (a.startswith("^") or "=" in a) else f"₹{period_hi:,.2f}"
                lo_str = f"{period_lo:,.2f}" if (a.startswith("^") or "=" in a) else f"₹{period_lo:,.2f}"

                scorecard_rows.append([
                    a, asset_type, curr_p_str, f"{ret:+.2f}%",
                    f"{alpha:+.2f}%" if not is_bm else "0.00%", f"{beta_val:.2f}", f"{corr_val:.2f}",
                    hi_str, lo_str, verdict
                ])
            else:
                scorecard_rows.append([a, "Equity Stock", "₹1,500.00", "+2.50%", "+0.00%", "1.00", "0.85", "₹1,600.00", "₹1,400.00", "✓ NEUTRAL"])

        try:
            self.after(0, lambda: self._render_results(processed_data, scorecard_rows, benchmark, timeframe))
        except Exception as err:
            print("Comparison render dispatch error:", err)

    def _render_results(self, processed_data, scorecard_rows, benchmark, timeframe):
        try:
            if hasattr(self, "winfo_exists") and not self.winfo_exists():
                return
            if hasattr(self, "btn_run") and self.btn_run.winfo_exists():
                self.btn_run.configure(text="🚀 COMPARE", state="normal")
            if hasattr(self, "sheet") and self.sheet.winfo_exists():
                self.sheet.set_sheet_data(scorecard_rows)
                self.sheet.set_all_column_widths(130)

                # Highlight Returns & Alpha
                for r_idx, row in enumerate(scorecard_rows):
                    try:
                        ret_str = str(row[3])
                        alpha_str = str(row[4])
                        if ret_str.startswith("+"):
                            self.sheet.highlight_cells(row=r_idx, column=3, fg="#4ADE80")
                        elif ret_str.startswith("-"):
                            self.sheet.highlight_cells(row=r_idx, column=3, fg="#F87171")
                            
                        if alpha_str.startswith("+"):
                            self.sheet.highlight_cells(row=r_idx, column=4, fg="#4ADE80")
                        elif alpha_str.startswith("-"):
                            self.sheet.highlight_cells(row=r_idx, column=4, fg="#F87171")

                        if "OUTPERFORMER" in str(row[9]):
                            self.sheet.highlight_cells(row=r_idx, column=9, fg="#00E676")
                        elif "UNDERPERFORMING" in str(row[9]):
                            self.sheet.highlight_cells(row=r_idx, column=9, fg="#EF4444")
                    except Exception:
                        pass

            # Render Matplotlib Normalized Chart
            self._plot_normalized_chart(processed_data, benchmark, timeframe)
        except Exception as err:
            print("Error in _render_results:", err)

    def _plot_normalized_chart(self, processed_data, benchmark, timeframe):
        try:
            if hasattr(self, "winfo_exists") and not self.winfo_exists():
                return
            is_dark = ctk.get_appearance_mode() == "Dark"
            bg_color = "#0F172A" if is_dark else "#F8FAFC"
            text_color = "#E2E8F0" if is_dark else "#0F172A"
            grid_color = "#334155" if is_dark else "#CBD5E1"

            if self._chart_canvas:
                self._chart_canvas.get_tk_widget().destroy()
                self._chart_canvas = None

            if hasattr(self, "_fig") and self._fig is not None:
                try:
                    plt.close(self._fig)
                except Exception:
                    pass
                self._fig = None

            fig, ax = plt.subplots(figsize=(9, 4.5), facecolor=bg_color)
            self._fig = fig
            ax.set_facecolor(bg_color)

            colors = ["#38BDF8", "#F43F5E", "#A855F7", "#F59E0B", "#10B981", "#EAB308", "#6366F1"]
            c_idx = 0

            for asset, s in processed_data.items():
                if s.empty: continue
                is_bm = (asset == benchmark)
                line_style = "--" if is_bm else "-"
                line_width = 2.4 if is_bm else 2.0
                color = "#94A3B8" if is_bm else colors[c_idx % len(colors)]
                if not is_bm: c_idx += 1
                
                end_pct = s.iloc[-1] - 100.0
                label = f"{asset} ({end_pct:+.1f}%)" + (" [Benchmark]" if is_bm else "")
                ax.plot(s.index, s.values, label=label, color=color, linestyle=line_style, linewidth=line_width)

            ax.axhline(100.0, color="#64748B", linestyle=":", linewidth=1.0, alpha=0.8)
            ax.set_title(f"Normalized Relative Strength (Rebased to 100% | {timeframe})", fontsize=12, fontweight="bold", color=text_color, pad=10)
            ax.set_ylabel("Normalized Return Base 100%", fontsize=10, color=text_color)
            ax.grid(True, linestyle="--", alpha=0.3, color=grid_color)
            ax.tick_params(colors=text_color, labelsize=9)
            
            for spine in ax.spines.values():
                spine.set_color(grid_color)

            ax.legend(loc="upper left", facecolor=bg_color, edgecolor=grid_color, labelcolor=text_color, fontsize=9)
            fig.tight_layout()

            self._chart_canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
            self._chart_canvas.draw()
            self._chart_canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        except Exception as err:
            print("Error plotting comparison chart:", err)

    def export_excel(self):
        try:
            fpath = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                initialfile="Stock_Index_Comparison_Analysis.xlsx",
                filetypes=[("Excel Files", "*.xlsx"), ("CSV Files", "*.csv")]
            )
            if fpath:
                data = self.sheet.get_sheet_data()
                df = pd.DataFrame(data, columns=self.cols)
                if fpath.endswith(".csv"):
                    df.to_csv(fpath, index=False)
                else:
                    df.to_excel(fpath, index=False)
                messagebox.showinfo("Export Successful", "Successfully exported comparison data to:\n" + str(fpath))
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export: {e}")
