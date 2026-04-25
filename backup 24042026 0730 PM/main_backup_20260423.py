import customtkinter as ctk
from tkinter import ttk
import tkinter.messagebox as messagebox
from db_utils import DatabaseHelper
from market_api import MarketAPI
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import matplotlib.dates as mdates
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import threading
import yfinance as yf
from tksheet import Sheet

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

def update_treeview_style(mode):
    style = ttk.Style()
    style.theme_use("default")
    
    # Base Professional Styling
    style.configure("Treeview", font=("Segoe UI", 12), rowheight=35)
    style.configure("Treeview.Heading", font=("Segoe UI", 13, "bold"), padding=5)
    
    # Dynamic Light/Dark
    if mode == "Light":
        style.configure("Treeview", background="#ffffff", foreground="#333333", fieldbackground="#ffffff", borderwidth=1, bordercolor="#cccccc")
        style.map('Treeview', background=[('selected', '#3a7ebf')], foreground=[('selected', 'white')])
        style.configure("Treeview.Heading", background="#f0f0f0", foreground="#111111", relief="flat")
    else:
        style.configure("Treeview", background="#1e1e1e", foreground="white", fieldbackground="#1e1e1e", borderwidth=0)
        style.map('Treeview', background=[('selected', '#1f538d')], foreground=[('selected', 'white')])
        style.configure("Treeview.Heading", background="#2a2d2e", foreground="white", relief="flat")

class SymbolDetailWindow(ctk.CTkToplevel):
    def __init__(self, master, symbol, db, expiry='All', start_date=None, end_date=None):
        super().__init__(master)
        self.title(f"{symbol} - Intelligence & Drilldown")
        self.geometry("1200x800")
        self.db = db
        self.symbol = symbol
        self.expiry = expiry
        self.start_date = start_date
        self.end_date = end_date
        
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        lbl = ctk.CTkLabel(self, text=f"Historical Drilldown & Intelligence: {symbol}", font=ctk.CTkFont(size=22, weight="bold"))
        lbl.grid(row=0, column=0, pady=10)
        
        self.tabs = ctk.CTkTabview(self, corner_radius=10)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        
        self.tabs.add("What-If Analysis & Intelligence")
        self.tabs.add("Historical Data")
        self.tabs.add("Technical Indicators")
        
        # Intelligence Tab
        self.intel_label = ctk.CTkLabel(self.tabs.tab("What-If Analysis & Intelligence"), text="Loading intelligence...", font=ctk.CTkFont(size=16), justify="left")
        self.intel_label.pack(padx=20, pady=20, anchor="w")
        
        # Historical Data Tab
        cols = ("SnapShotDate", "Expiry", "PrevClose", "Open", "High", "Low", "Close", "Gap", "MaxProfitLong", "MaxLossLong", "NetPnL")
        self.tree = ttk.Treeview(self.tabs.tab("Historical Data"), columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=90, anchor="e" if col not in ("SnapShotDate", "Expiry") else "w")
            
        self.tree.pack(fill="both", expand=True, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(self.tabs.tab("Historical Data"), orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        
        # Technical Indicators Tab
        tech_cols = ("SnapShotDate", "Close", "RSI", "MACD", "MACD_Signal", "ATR", "PCR")
        self.tech_tree = ttk.Treeview(self.tabs.tab("Technical Indicators"), columns=tech_cols, show="headings")
        for col in tech_cols:
            self.tech_tree.heading(col, text=col)
            self.tech_tree.column(col, width=100, anchor="e" if col != "SnapShotDate" else "w")
            
        self.tech_tree.pack(fill="both", expand=True, padx=10, pady=10)
        tech_scrollbar = ttk.Scrollbar(self.tabs.tab("Technical Indicators"), orient="vertical", command=self.tech_tree.yview)
        self.tech_tree.configure(yscroll=tech_scrollbar.set)
        tech_scrollbar.pack(side="right", fill="y")
        
        self.after(100, self.load_data)

    def load_data(self):
        df = self.db.get_symbol_historical_drilldown(self.symbol, self.start_date, self.end_date, self.expiry)
        if not df.empty:
            max_profit = df['MaxProfitLong'].max()
            max_loss = df['MaxLossLong'].min()
            
            intel_text = f"💡 What-If Scenario (If traded in selected period):\n\n"
            intel_text += f"▲ Maximum Potential Profit (Long): ₹{max_profit:.2f}\n"
            intel_text += f"   (This assumes entering exactly at Open and exiting at the absolute Peak High.)\n\n"
            intel_text += f"▼ Maximum Potential Loss (Drawdown): ₹{max_loss:.2f}\n"
            intel_text += f"   (This is the worst-case scenario holding from Open to Intraday Low.)\n\n"
            
            fades = df[(df['Gap'] > 0) & (df['CLOSE_PRIC'] < df['OPEN_PRICE'])]
            if not fades.empty:
                intel_text += f"⚠️ Strategy Warning: Gap Up Fade Detected\n"
                intel_text += f"   The stock faded after a Gap Up {len(fades)} time(s) during these dates.\n"
                intel_text += f"   Recommendation: Avoid buying blindly at open after a gap up.\n\n"
                
            huge_drawdowns = df[df['MaxLossLong'] < -5000]
            if not huge_drawdowns.empty:
                intel_text += f"⚠️ High Volatility Warning:\n"
                intel_text += f"   {len(huge_drawdowns)} sessions showed massive intraday drawdowns > ₹5000.\n"
                intel_text += f"   Recommendation: Strictly use Stop Losses; do not average losing positions.\n"
                
            self.intel_label.configure(text=intel_text)
            
            for _, row in df.iterrows():
                self.tree.insert("", "end", values=(
                    row.get('SnapShotDate', ''), row.get('EXPIRY_DATE', ''), row.get('PREVIOUS_S', ''),
                    row.get('OPEN_PRICE', ''), row.get('HIGH_PRICE', ''), row.get('LOW_PRICE', ''),
                    row.get('CLOSE_PRIC', ''), row.get('Gap', ''), row.get('MaxProfitLong', ''),
                    row.get('MaxLossLong', ''), row.get('NetPnL', '')
                ))
        else:
            self.intel_label.configure(text="No historical data found for the selected criteria.")
            
        # Load Technicals
        ml_df = self.db.get_ml_features(self.symbol)
        if ml_df is not None and not ml_df.empty:
            if self.start_date: ml_df = ml_df[ml_df['SnapShotDate'] >= pd.to_datetime(self.start_date)]
            if self.end_date: ml_df = ml_df[ml_df['SnapShotDate'] <= pd.to_datetime(self.end_date)]
            
            ml_df = ml_df.sort_values(by='SnapShotDate', ascending=False)
            
            if not ml_df.empty:
                latest = ml_df.iloc[0]
                close_price = latest['CLOSE_PRIC']
                atr = latest['ATR']
                
                # Additional Metrics
                gap_ups = len(ml_df[ml_df['OPEN_PRICE'] > ml_df['PREVIOUS_S']])
                advances = len(ml_df[ml_df['CLOSE_PRIC'] > ml_df['PREVIOUS_S']])
                declines = len(ml_df[ml_df['CLOSE_PRIC'] < ml_df['PREVIOUS_S']])
                total_days = len(ml_df)
                
                proj_text = f"🎯 AI Projections (Based on latest Volatility/ATR of ₹{atr:.2f}):\n"
                proj_text += f"   ➤ 1-Day Target (Upside): ₹{(close_price + atr):.2f} | 1-Day Target (Downside): ₹{(close_price - atr):.2f}\n"
                proj_text += f"   ➤ 1-Week Target (Upside): ₹{(close_price + (atr * 2.23)):.2f} | 1-Week Target (Downside): ₹{(close_price - (atr * 2.23)):.2f}\n"
                proj_text += f"\n📊 Historical Sentiment ({total_days} Days Analyzed):\n"
                proj_text += f"   ➤ Gap-Up Opens: {gap_ups} days | Advances: {advances} days | Declines: {declines} days\n"
                
                current_intel = self.intel_label.cget("text")
                self.intel_label.configure(text=current_intel + proj_text)

            for _, row in ml_df.iterrows():
                self.tech_tree.insert("", "end", values=(
                    row['SnapShotDate'].strftime('%Y-%m-%d'), 
                    f"{row['CLOSE_PRIC']:.2f}",
                    f"{row['RSI']:.2f}", 
                    f"{row['MACD']:.2f}", 
                    f"{row['MACD_Signal']:.2f}", 
                    f"{row['ATR']:.2f}", 
                    f"{row['PCR']:.2f}"
                ))

class IndexChartWindow(ctk.CTkToplevel):
    def __init__(self, master, index_name, ticker):
        super().__init__(master)
        self.title(f"{index_name} ({ticker}) - Live Price Action")
        self.geometry("800x500")
        
        self.index_name = index_name
        self.ticker = ticker
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        lbl = ctk.CTkLabel(btn_frame, text=f"Loading live chart for {index_name}...", font=ctk.CTkFont(size=18, weight="bold"))
        lbl.pack(side="left")
        self.lbl = lbl
        
        hist_btn = ctk.CTkButton(btn_frame, text="View Historical Data", command=self.open_history)
        hist_btn.pack(side="right")
        
        self.chart_frame = ctk.CTkFrame(self)
        self.chart_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        threading.Thread(target=self.load_chart, daemon=True).start()

    def open_history(self):
        HistoricalIndexWindow(self.winfo_toplevel(), self.index_name, self.ticker)

    def load_chart(self):
        try:
            tk = yf.Ticker(self.ticker)
            hist = tk.history(period="1mo")
            self.after(0, self.draw_chart, hist)
        except Exception as e:
            self.after(0, lambda: self.lbl.configure(text=f"Failed to load chart: {e}"))

    def draw_chart(self, hist):
        self.lbl.configure(text=f"Live Price Action: {self.index_name}")
        if hist.empty:
            self.lbl.configure(text="No data available.")
            return
            
        for widget in self.chart_frame.winfo_children(): widget.destroy()
            
        fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
        
        if ctk.get_appearance_mode() == "Dark":
            fig.patch.set_facecolor('#1a1a1a')
            ax.set_facecolor('#1a1a1a')
            ax.tick_params(colors='white')
            for spine in ax.spines.values(): spine.set_color('#333333')
        else:
            fig.patch.set_facecolor('#ffffff')
            ax.set_facecolor('#ffffff')
            ax.tick_params(colors='black')
            for spine in ax.spines.values(): spine.set_color('#cccccc')
            
        ax.plot(hist.index, hist['Close'], color='#00E676' if hist['Close'].iloc[-1] > hist['Close'].iloc[0] else '#FF1744', linewidth=2)
        ax.fill_between(hist.index, hist['Close'], hist['Close'].min(), alpha=0.1, color='#00E676' if hist['Close'].iloc[-1] > hist['Close'].iloc[0] else '#FF1744')
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

class LiveComponentsWindow(ctk.CTkToplevel):
    def __init__(self, master, mapi, index_name):
        super().__init__(master)
        self.title(f"{index_name} - Live Components Drilldown")
        self.geometry("900x600")
        self.mapi = mapi
        self.index_name = index_name
        
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=10)
        
        lbl = ctk.CTkLabel(btn_frame, text=f"Live Intraday Data: {index_name} Components", font=ctk.CTkFont(size=20, weight="bold"))
        lbl.pack(side="left")
        
        hist_btn = ctk.CTkButton(btn_frame, text="Historical Data", command=self.open_history)
        hist_btn.pack(side="right")
        
        self.status_lbl = ctk.CTkLabel(self, text="Fetching Live Data from Exchange...", font=ctk.CTkFont(size=14))
        self.status_lbl.pack(pady=5)
        
        cols = ["Symbol", "Open", "High", "Low", "Close", "% Change", "Buildup"]
        self.sheet = Sheet(self, headers=[f"{c} ▼▲" for c in cols])
        self.sheet.enable_bindings(("single_select", "row_select", "column_width_resize", "arrowkeys", "copy", "rc_sort", "column_select"))
        if ctk.get_appearance_mode() == "Dark":
            self.sheet.change_theme("dark")
        else:
            self.sheet.change_theme("light blue")
        self.sheet.set_options(font=("Segoe UI", 12, "normal"), header_font=("Segoe UI", 14, "bold"))
        self.sheet.extra_bindings([("column_select", self.on_column_select)])
        self.sheet.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.sort_col = None
        self.sort_rev = False
        
        threading.Thread(target=self.load_data, daemon=True).start()

    def on_column_select(self, event):
        col = event.column
        if self.sort_col == col:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_col = col
            self.sort_rev = False
        self.sheet.sort(column=col, reverse=self.sort_rev)
        
        headers = self.sheet.headers()
        for i, h in enumerate(headers):
            h_base = h.replace(" ▼▲", "").replace(" ▲", "").replace(" ▼", "")
            if i == self.sort_col:
                headers[i] = f"{h_base} {'▲' if not self.sort_rev else '▼'}"
            else:
                headers[i] = f"{h_base} ▼▲"
        self.sheet.headers(headers)

    def open_history(self):
        ticker = self.mapi.indian_indices.get(self.index_name)
        if not ticker: ticker = self.mapi.global_indices.get(self.index_name)
        if ticker:
            HistoricalIndexWindow(self.winfo_toplevel(), self.index_name, ticker)

    def load_data(self):
        df = self.mapi.get_index_components_live(self.index_name)
        self.after(0, self.update_ui, df)

    def update_ui(self, df):
        if df.empty:
            self.status_lbl.configure(text=f"Failed to fetch component data for {self.index_name}")
            return
            
        self.status_lbl.configure(text=f"Live Data Loaded. Total Components Analyzed: {len(df)}")
        data = []
        for _, row in df.iterrows():
            data.append([row['Symbol'], row['Open'], row['High'], row['Low'], row['Close'], f"{row['% Change']}%", row['Buildup']])
            
        self.sheet.set_sheet_data(data)
        
        for r, row in enumerate(data):
            if "Long Buildup" in row[6] or "Short Covering" in row[6]:
                self.sheet.highlight_cells(row=r, column=6, bg=None, fg="#00E676")
            elif "Short Buildup" in row[6] or "Long Unwinding" in row[6]:
                self.sheet.highlight_cells(row=r, column=6, bg=None, fg="#FF1744")
        self.sheet.set_all_column_widths(120)

class HistoricalIndexWindow(ctk.CTkToplevel):
    def __init__(self, master, index_name, ticker):
        super().__init__(master)
        self.title(f"{index_name} Historical Data")
        self.geometry("1000x700")
        
        lbl = ctk.CTkLabel(self, text=f"{index_name} Historical Data", font=ctk.CTkFont(size=24, weight="bold"))
        lbl.pack(pady=10)
        
        self.status = ctk.CTkLabel(self, text="Fetching historical data...", font=ctk.CTkFont(size=14))
        self.status.pack()
        
        cols = ["Date", "Price", "Open", "High", "Low", "Vol.", "Change %"]
        self.sheet = Sheet(self, headers=[f"{c} ▼▲" for c in cols])
        self.sheet.enable_bindings(("single_select", "row_select", "column_width_resize", "arrowkeys", "copy", "rc_sort", "column_select"))
        if ctk.get_appearance_mode() == "Dark":
            self.sheet.change_theme("dark")
        else:
            self.sheet.change_theme("light blue")
        self.sheet.set_options(font=("Segoe UI", 12, "normal"), header_font=("Segoe UI", 14, "bold"))
        self.sheet.extra_bindings([("column_select", self.on_column_select)])
        self.sheet.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.sort_col = None
        self.sort_rev = False
        
        self.intel_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.intel_frame.pack(fill="x", padx=20, pady=10)
        
        self.lbl_highest = ctk.CTkLabel(self.intel_frame, text="Highest: --", font=ctk.CTkFont(weight="bold"))
        self.lbl_highest.pack(side="left", padx=15)
        self.lbl_lowest = ctk.CTkLabel(self.intel_frame, text="Lowest: --", font=ctk.CTkFont(weight="bold"))
        self.lbl_lowest.pack(side="left", padx=15)
        self.lbl_diff = ctk.CTkLabel(self.intel_frame, text="Difference: --", font=ctk.CTkFont(weight="bold"))
        self.lbl_diff.pack(side="left", padx=15)
        self.lbl_avg = ctk.CTkLabel(self.intel_frame, text="Average: --", font=ctk.CTkFont(weight="bold"))
        self.lbl_avg.pack(side="left", padx=15)
        self.lbl_change = ctk.CTkLabel(self.intel_frame, text="Change %: --", font=ctk.CTkFont(weight="bold"))
        self.lbl_change.pack(side="left", padx=15)
        
        threading.Thread(target=self.load_data, args=(ticker,), daemon=True).start()
        
    def on_column_select(self, event):
        col = event.column
        if self.sort_col == col:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_col = col
            self.sort_rev = False
        self.sheet.sort(column=col, reverse=self.sort_rev)
        
        headers = self.sheet.headers()
        for i, h in enumerate(headers):
            h_base = h.replace(" ▼▲", "").replace(" ▲", "").replace(" ▼", "")
            if i == self.sort_col:
                headers[i] = f"{h_base} {'▲' if not self.sort_rev else '▼'}"
            else:
                headers[i] = f"{h_base} ▼▲"
        self.sheet.headers(headers)
        
    def load_data(self, ticker):
        try:
            tk = yf.Ticker(ticker)
            hist = tk.history(period="6mo")
            if hist.empty:
                self.after(0, lambda: self.status.configure(text="No historical data found."))
                return
                
            hist['Prev_Close'] = hist['Close'].shift(1)
            hist['Pct_Change'] = ((hist['Close'] - hist['Prev_Close']) / hist['Prev_Close']) * 100
            
            hist = hist.dropna(subset=['Prev_Close'])
            hist = hist.sort_index(ascending=False)
            self.after(0, self.update_ui, hist)
        except Exception as e:
            self.after(0, lambda: self.status.configure(text=f"Error: {e}"))
            
    def update_ui(self, hist):
        self.status.pack_forget()
        highest = hist['High'].max()
        lowest = hist['Low'].min()
        diff = highest - lowest
        avg = hist['Close'].mean()
        
        start_price = hist['Close'].iloc[-1]
        end_price = hist['Close'].iloc[0]
        total_change = ((end_price - start_price) / start_price) * 100
        
        self.lbl_highest.configure(text=f"Highest: {highest:.2f}")
        self.lbl_lowest.configure(text=f"Lowest: {lowest:.2f}")
        self.lbl_diff.configure(text=f"Difference: {diff:.2f}")
        self.lbl_avg.configure(text=f"Average: {avg:.2f}")
        self.lbl_change.configure(text=f"Change %: {total_change:.2f}%")
        
        data = []
        for date, row in hist.iterrows():
            date_str = date.strftime('%b %d, %Y')
            price = row['Close']
            o = row['Open']
            h = row['High']
            l = row['Low']
            v = row['Volume']
            pct = row['Pct_Change']
            
            pct_str = f"+{pct:.2f}%" if pct > 0 else f"{pct:.2f}%"
            vol_str = f"{v/1000000:.2f}M" if v >= 1000000 else f"{v/1000:.2f}K"
            data.append([date_str, f"{price:.2f}", f"{o:.2f}", f"{h:.2f}", f"{l:.2f}", vol_str, pct_str])
            
        self.sheet.set_sheet_data(data)
        for r, row in enumerate(data):
            if "+" in row[6]:
                self.sheet.highlight_cells(row=r, column=6, bg=None, fg="#00E676")
            else:
                self.sheet.highlight_cells(row=r, column=6, bg=None, fg="#FF1744")
        self.sheet.set_all_column_widths(120)

class GlobalMarketFrame(ctk.CTkFrame):
    def __init__(self, master, mapi):
        super().__init__(master, corner_radius=15)
        self.mapi = mapi
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)
        
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, columnspan=2, pady=20)
        
        ctk.CTkLabel(self.header_frame, text="Global Markets & Macro View", font=ctk.CTkFont(size=28, weight="bold")).pack()
        self.ad_lbl = ctk.CTkLabel(self.header_frame, text="Loading Market Breadth...", font=ctk.CTkFont(size=16))
        self.ad_lbl.pack(pady=5)
        
        self.indices_tabs = ctk.CTkTabview(self, corner_radius=10)
        self.indices_tabs.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=20, pady=10)
        self.indices_tabs.add("Indian Indices")
        self.indices_tabs.add("Global Indices")
        
        self.in_sheet = self.create_sheet(self.indices_tabs.tab("Indian Indices"), ("Index", "Price", "Change", "% Change", "Advances", "Declines", "Trend"), self.on_in_sheet_click)
        self.gl_sheet = self.create_sheet(self.indices_tabs.tab("Global Indices"), ("Index", "Price", "Change", "% Change", "Trend"), self.on_gl_sheet_click)
        
        self.news_frame = ctk.CTkFrame(self, corner_radius=10)
        self.news_frame.grid(row=1, column=1, rowspan=2, sticky="nsew", padx=20, pady=10)
        ctk.CTkLabel(self.news_frame, text="Market News (Global & Indian)", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=15)
        
        self.news_tabs = ctk.CTkTabview(self.news_frame, corner_radius=10)
        self.news_tabs.pack(fill="both", expand=True, padx=10, pady=5)
        self.news_tabs.add("Indian News")
        self.news_tabs.add("Global News")
        self.news_tabs.add("Geopolitics")
        
        self.news_in_frame = ctk.CTkScrollableFrame(self.news_tabs.tab("Indian News"), fg_color="transparent")
        self.news_in_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.news_gl_frame = ctk.CTkScrollableFrame(self.news_tabs.tab("Global News"), fg_color="transparent")
        self.news_gl_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.news_geo_frame = ctk.CTkScrollableFrame(self.news_tabs.tab("Geopolitics"), fg_color="transparent")
        self.news_geo_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ctk.CTkLabel(self.news_in_frame, text="Loading Indian news...", font=ctk.CTkFont(size=14)).pack()
        ctk.CTkLabel(self.news_gl_frame, text="Loading Global news...", font=ctk.CTkFont(size=14)).pack()
        ctk.CTkLabel(self.news_geo_frame, text="Loading Geopolitics news...", font=ctk.CTkFont(size=14)).pack()
        
        self._data_ready = False
        self.load_args = None
        self.after(500, self.start_bg_load)
        self.after(100, self.poll_data)

    def create_sheet(self, parent, cols, click_handler):
        sheet = Sheet(parent, headers=[f"{c} ▼▲" for c in cols])
        sheet.enable_bindings(("single_select", "row_select", "column_width_resize", "arrowkeys", "copy", "rc_sort", "column_select"))
        if ctk.get_appearance_mode() == "Dark":
            sheet.change_theme("dark")
        else:
            sheet.change_theme("light blue")
            
        sheet.set_options(font=("Segoe UI", 12, "normal"), header_font=("Segoe UI", 14, "bold"))
        sheet.MT.bind("<Double-1>", click_handler)
        sheet.extra_bindings([("column_select", lambda e, s=sheet: self.on_column_select(e, s))])
        sheet.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Add custom sorting state tracking attributes
        sheet.sort_col = None
        sheet.sort_rev = False
        return sheet
        
    def on_column_select(self, event, sheet):
        col = event.column
        if sheet.sort_col == col:
            sheet.sort_rev = not sheet.sort_rev
        else:
            sheet.sort_col = col
            sheet.sort_rev = False
        sheet.sort(column=col, reverse=sheet.sort_rev)
        
        headers = sheet.headers()
        for i, h in enumerate(headers):
            h_base = h.replace(" ▼▲", "").replace(" ▲", "").replace(" ▼", "")
            if i == sheet.sort_col:
                headers[i] = f"{h_base} {'▲' if not sheet.sort_rev else '▼'}"
            else:
                headers[i] = f"{h_base} ▼▲"
        sheet.headers(headers)

    def on_in_sheet_click(self, event):
        row = self.in_sheet.identify_row(event)
        if row is not None:
            self.handle_index_click(row, self.in_sheet)
        
    def on_gl_sheet_click(self, event):
        row = self.gl_sheet.identify_row(event)
        if row is not None:
            self.handle_index_click(row, self.gl_sheet)

    def handle_index_click(self, row, sheet):
        try:
            index_name = sheet.get_cell_data(row, 0)
            if hasattr(self.mapi, 'index_baskets') and index_name in self.mapi.index_baskets:
                LiveComponentsWindow(self.winfo_toplevel(), self.mapi, index_name)
            else:
                ticker = None
                for name, t in self.mapi.indian_indices.items():
                    if name == index_name: ticker = t
                for name, t in self.mapi.global_indices.items():
                    if name == index_name: ticker = t
                if ticker:
                    IndexChartWindow(self.winfo_toplevel(), index_name, ticker)
        except Exception as e:
            print(f"Click error: {e}")

    def start_bg_load(self):
        threading.Thread(target=self.load_data, daemon=True).start()
        
    def poll_data(self):
        if self._data_ready and self.load_args:
            self.update_ui(*self.load_args)
            self._data_ready = False
        self.after(100, self.poll_data)

    def load_data(self):
        df_in = self.mapi.get_indian_indices()
        df_gl = self.mapi.get_global_indices()
        adv_dict = self.mapi.get_advances_declines()
        broad_breadth = self.mapi.get_broad_market_breadth()
        news = self.mapi.get_top_news()
        
        self.load_args = (df_in, df_gl, adv_dict, broad_breadth, news)
        self._data_ready = True

    def update_ui(self, df_in, df_gl, adv_dict, broad_breadth, news):
        nse = broad_breadth.get('NSE', {'Adv': 0, 'Dec': 0, 'Total': 0})
        bse = broad_breadth.get('BSE', {'Adv': 0, 'Dec': 0, 'Total': 0})
        
        self.ad_lbl.pack_forget()
        
        if not hasattr(self, 'breadth_frame'):
            self.breadth_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
            self.breadth_frame.pack(pady=5)
            
            self.b_title = ctk.CTkLabel(self.breadth_frame, text="Total Listed Companies Live Breadth | ", font=ctk.CTkFont(size=16))
            self.b_title.pack(side="left")
            
            self.nse_lbl = ctk.CTkLabel(self.breadth_frame, text="NSE: ", font=ctk.CTkFont(size=16))
            self.nse_lbl.pack(side="left")
            
            self.nse_adv = ctk.CTkLabel(self.breadth_frame, text="", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00E676")
            self.nse_adv.pack(side="left", padx=5)
            
            self.nse_dec = ctk.CTkLabel(self.breadth_frame, text="", font=ctk.CTkFont(size=16, weight="bold"), text_color="#FF1744")
            self.nse_dec.pack(side="left", padx=5)
            
            ctk.CTkLabel(self.breadth_frame, text="  |  ", font=ctk.CTkFont(size=16)).pack(side="left")
            
            self.bse_lbl = ctk.CTkLabel(self.breadth_frame, text="BSE: ", font=ctk.CTkFont(size=16))
            self.bse_lbl.pack(side="left")
            
            self.bse_adv = ctk.CTkLabel(self.breadth_frame, text="", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00E676")
            self.bse_adv.pack(side="left", padx=5)
            
            self.bse_dec = ctk.CTkLabel(self.breadth_frame, text="", font=ctk.CTkFont(size=16, weight="bold"), text_color="#FF1744")
            self.bse_dec.pack(side="left", padx=5)

        self.nse_adv.configure(text=f"▲ Advances {nse['Adv']}")
        self.nse_dec.configure(text=f"▼ Declines {nse['Dec']}")
        self.bse_adv.configure(text=f"▲ Advances {bse['Adv']}")
        self.bse_dec.configure(text=f"▼ Declines {bse['Dec']}")
        
        in_data = []
        if not df_in.empty:
            for _, row in df_in.iterrows():
                idx_name = row['Index']
                ad_info = adv_dict.get(idx_name, {'Adv': 0, 'Dec': 0})
                in_data.append([row['Index'], row['Price'], row['Change'], f"{row['% Change']}%", f"{ad_info['Adv']}", f"{ad_info['Dec']}", row['Trend']])
        
        self.in_sheet.set_sheet_data(in_data)
        
        in_green = []
        in_red = []
        for r, row_data in enumerate(in_data):
            in_green.append((r, 4)) # Advances Green
            in_red.append((r, 5)) # Declines Red
            if "Bullish" in row_data[6]:
                in_green.append((r, 6))
            else:
                in_red.append((r, 6))
                
        if in_green: self.in_sheet.highlight_cells(cells=in_green, bg=None, fg="#00E676")
        if in_red: self.in_sheet.highlight_cells(cells=in_red, bg=None, fg="#FF1744")
                
        gl_data = []
        if not df_gl.empty:
            for _, row in df_gl.iterrows():
                gl_data.append([row['Index'], row['Price'], row['Change'], f"{row['% Change']}%", row['Trend']])
                
        self.gl_sheet.set_sheet_data(gl_data)
        
        gl_green = []
        gl_red = []
        for r, row_data in enumerate(gl_data):
            if "Bullish" in row_data[4]:
                gl_green.append((r, 4))
            else:
                gl_red.append((r, 4))
                
        if gl_green: self.gl_sheet.highlight_cells(cells=gl_green, bg=None, fg="#00E676")
        if gl_red: self.gl_sheet.highlight_cells(cells=gl_red, bg=None, fg="#FF1744")
                
        self.in_sheet.set_all_column_widths(120)
        self.gl_sheet.set_all_column_widths(120)
                
        for widget in self.news_in_frame.winfo_children(): widget.destroy()
        for widget in self.news_gl_frame.winfo_children(): widget.destroy()
        for widget in self.news_geo_frame.winfo_children(): widget.destroy()
        
        import webbrowser
        
        def add_news_items(frame, news_list, empty_msg):
            if not news_list:
                ctk.CTkLabel(frame, text=empty_msg, font=ctk.CTkFont(size=14)).pack(pady=10)
                return
            for item in news_list:
                card = ctk.CTkFrame(frame, corner_radius=10)
                card.pack(fill="x", padx=5, pady=5)
                
                title = ctk.CTkLabel(card, text=item['Title'], font=ctk.CTkFont(size=16, weight="bold"), wraplength=500, justify="left")
                title.pack(anchor="w", padx=10, pady=(10, 2))
                
                if item.get('Summary'):
                    summ = ctk.CTkLabel(card, text=item['Summary'][:250] + "...", font=ctk.CTkFont(size=14), wraplength=500, justify="left", text_color="gray60")
                    summ.pack(anchor="w", padx=10, pady=(0, 5))
                
                pub = ctk.CTkLabel(card, text=item['Published'], font=ctk.CTkFont(size=12), text_color="gray50")
                pub.pack(anchor="w", padx=10, pady=(0, 5))
                
                if item.get('Link'):
                    btn = ctk.CTkButton(card, text="Read Full Article", width=120, height=28, command=lambda l=item['Link']: webbrowser.open(l))
                    btn.pack(anchor="e", padx=10, pady=(0, 10))

        if news:
            add_news_items(self.news_in_frame, news.get('Indian', []), "No Indian news available.")
            add_news_items(self.news_gl_frame, news.get('Global', []), "No Global news available.")
            add_news_items(self.news_geo_frame, news.get('Geopolitics', []), "No Geopolitics news available.")

class TopPicksFrame(ctk.CTkFrame):
    def __init__(self, master, mapi):
        super().__init__(master, corner_radius=15)
        self.mapi = mapi
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, pady=20)
        ctk.CTkLabel(header_frame, text="Today's Top 10 Picks (Live AI Scanner)", font=ctk.CTkFont(size=28, weight="bold")).pack(side="left", padx=10)
        ctk.CTkButton(header_frame, text="🔄 Refresh Live", width=120, command=self.start_bg_load).pack(side="left", padx=10)
        
        self.tabs = ctk.CTkTabview(self, corner_radius=10)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=30, pady=10)
        
        self.tabs.add("Indian Market")
        self.tabs.add("Global Market")
        
        self.in_tree = self.create_tree(self.tabs.tab("Indian Market"))
        self.gl_tree = self.create_tree(self.tabs.tab("Global Market"))
        
        self.status_lbl = ctk.CTkLabel(self, text="Scanning markets... this may take 10-15 seconds.", font=ctk.CTkFont(size=14), text_color="#FFB300")
        self.status_lbl.grid(row=2, column=0, pady=10)
        
        self._data_ready = False
        self.df_in = None
        self.df_gl = None
        self.after(500, self.start_bg_load)
        self.after(100, self.poll_data)

    def create_tree(self, parent):
        cols = ("Symbol", "Price", "% Change", "Score", "Justification")
        tree = ttk.Treeview(parent, columns=cols, show="headings")
        for col in cols: tree.heading(col, text=col)
        
        tree.column("Symbol", width=120)
        tree.column("Price", width=100, anchor="e")
        tree.column("% Change", width=100, anchor="e")
        tree.column("Score", width=100, anchor="center")
        tree.column("Justification", width=500)
        
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        return tree

    def start_bg_load(self):
        self.status_lbl.configure(text="Scanning markets... this may take 10-15 seconds.", text_color="#FFB300")
        for item in self.in_tree.get_children(): self.in_tree.delete(item)
        for item in self.gl_tree.get_children(): self.gl_tree.delete(item)
        threading.Thread(target=self.load_data, daemon=True).start()

    def poll_data(self):
        if self._data_ready:
            self.update_ui(self.df_in, self.df_gl)
            self._data_ready = False
        self.after(100, self.poll_data)

    def load_data(self):
        df_in = self.mapi.get_top_picks("Indian")
        df_gl = self.mapi.get_top_picks("Global")
        self.df_in = df_in
        self.df_gl = df_gl
        self._data_ready = True

    def update_ui(self, df_in, df_gl):
        for item in self.in_tree.get_children(): self.in_tree.delete(item)
        if not df_in.empty:
            for _, row in df_in.iterrows():
                self.in_tree.insert("", "end", values=(row['Symbol'], row['Price'], f"{row['% Change']}%", row['Score'], row['Justification']))
                
        for item in self.gl_tree.get_children(): self.gl_tree.delete(item)
        if not df_gl.empty:
            for _, row in df_gl.iterrows():
                self.gl_tree.insert("", "end", values=(row['Symbol'], row['Price'], f"{row['% Change']}%", row['Score'], row['Justification']))
        
        self.status_lbl.configure(text="Scan Complete.", text_color="#00E676")

class FuturesAnalysisFrame(ctk.CTkFrame):
    def __init__(self, master, db, mapi=None):
        super().__init__(master, corner_radius=15)
        self.db = db
        self.mapi = mapi
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.top_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.top_panel.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        
        # Row 0 of top_panel: Header
        ctk.CTkLabel(self.top_panel, text="Futures Strategy & Range Backtest", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, columnspan=7, sticky="w", pady=(0, 10))
        
        # Row 1 of top_panel: Filters Line 1
        ctk.CTkLabel(self.top_panel, text="Sector:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.sector_var = ctk.StringVar(value="All")
        self.sector_dropdown = ctk.CTkComboBox(self.top_panel, variable=self.sector_var, command=self.on_sector_change, width=140)
        self.sector_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="Industry:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.industry_var = ctk.StringVar(value="All")
        self.industry_dropdown = ctk.CTkComboBox(self.top_panel, variable=self.industry_var, command=self.on_filter_change, width=140)
        self.industry_dropdown.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="Symbol:").grid(row=1, column=4, padx=5, pady=5, sticky="e")
        self.symbol_var = ctk.StringVar(value="All")
        self.symbol_dropdown = ctk.CTkComboBox(self.top_panel, variable=self.symbol_var, width=140)
        self.symbol_dropdown.grid(row=1, column=5, padx=5, pady=5, sticky="w")
        
        # Row 2 of top_panel: Filters Line 2
        ctk.CTkLabel(self.top_panel, text="Expiry Date:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.expiry_var = ctk.StringVar(value="All")
        self.expiry_dropdown = ctk.CTkComboBox(self.top_panel, variable=self.expiry_var, width=140)
        self.expiry_dropdown.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="Start Date:").grid(row=2, column=2, padx=5, pady=5, sticky="e")
        self.start_date_var = ctk.StringVar()
        self.start_date_dropdown = ctk.CTkComboBox(self.top_panel, variable=self.start_date_var, width=140)
        self.start_date_dropdown.grid(row=2, column=3, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="End Date:").grid(row=2, column=4, padx=5, pady=5, sticky="e")
        self.end_date_var = ctk.StringVar()
        self.end_date_dropdown = ctk.CTkComboBox(self.top_panel, variable=self.end_date_var, width=140)
        self.end_date_dropdown.grid(row=2, column=5, padx=5, pady=5, sticky="w")
        
        self.search_btn = ctk.CTkButton(self.top_panel, text="Search Analysis", command=self.on_filter_change, width=120)
        self.search_btn.grid(row=2, column=6, padx=15, pady=5, sticky="w")
        
        self.cols = ["Symbol", "Spot", "Expiry", "Sector", "Lot Size", "Gap", "Open", "High", "Low", "Close", "Net PnL", "% Change", "Volume", "Buildup", "PCR"]
        self.sheet = Sheet(self, headers=[f"{c} ▼▲" for c in self.cols])
        self.sheet.enable_bindings(("single_select", "row_select", "column_width_resize", "arrowkeys", "copy", "column_select"))
        if ctk.get_appearance_mode() == "Dark":
            self.sheet.change_theme("dark")
        else:
            self.sheet.change_theme("light")
            
        self.sheet.set_options(font=("Segoe UI", 12, "normal"), header_font=("Segoe UI", 14, "bold"))
        self.sheet.MT.bind("<Double-1>", self.on_row_double_click)
        self.sheet.extra_bindings([("column_select", self.on_column_select)])
        self.sheet.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=20, pady=15)
        
        self.sort_col = 10 # Net PnL
        self.sort_rev = True
        self.current_df = None
        self.after(200, self.load_data)

    def get_default_expiry(self, expiries):
        from datetime import datetime
        today = datetime.now()
        closest_exp = None
        min_diff = None
        for exp in expiries:
            if exp == "All": continue
            try:
                dt = datetime.strptime(exp, '%b-%Y')
                if dt.year == today.year and dt.month == today.month:
                    return exp
                elif dt > today:
                    diff = (dt - today).days
                    if min_diff is None or diff < min_diff:
                        min_diff = diff
                        closest_exp = exp
            except:
                pass
        return closest_exp if closest_exp else (expiries[1] if len(expiries) > 1 else "All")

    def load_data(self):
        sectors = ["All"] + self.db.get_all_sectors()
        self.sector_dropdown.configure(values=sectors)
        
        symbols = ["All"] + self.db.get_symbols()
        self.symbol_dropdown.configure(values=symbols)
        
        expiries = ["All"] + self.db.get_futures_expiries()
        self.expiry_dropdown.configure(values=expiries)
        if len(expiries) > 1:
            self.expiry_var.set(self.get_default_expiry(expiries))
            
        dates = self.db.get_all_snapshot_dates()
        if dates:
            self.start_date_dropdown.configure(values=dates)
            self.end_date_dropdown.configure(values=dates)
            self.start_date_var.set(dates[0])
            self.end_date_var.set(dates[0])
            
        self.on_sector_change("All")

    def on_sector_change(self, choice):
        industries = ["All"] + self.db.get_industries_by_sector(choice)
        self.industry_dropdown.configure(values=industries)
        self.industry_var.set("All")
        self.on_filter_change(None)

    def on_filter_change(self, choice=None):
        df = self.db.get_futures_advanced_analysis(
            sector=self.sector_var.get(), 
            industry=self.industry_var.get(), 
            symbol=self.symbol_var.get(),
            expiry=self.expiry_var.get(),
            start_date=self.start_date_var.get(),
            end_date=self.end_date_var.get()
        )
        self.current_df = df
        self.update_sheet_data()
        
    def on_column_select(self, event):
        col = event.column
        if self.sort_col == col:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_col = col
            self.sort_rev = False
        self.update_sheet_data()
        
    def update_sheet_data(self):
        data = []
        if self.current_df is not None and not self.current_df.empty:
            df = self.current_df.copy()
            symbols = df['SYMBOL'].unique().tolist()
            spot_prices = self.mapi.get_bulk_live_prices(symbols) if self.mapi else {}
            
            # Map column index to dataframe column name
            col_map = {0:'SYMBOL', 2:'EXPIRY_DATE', 3:'Sector', 4:'Lot_Size', 5:'Gap', 6:'Open', 7:'High', 8:'Low', 9:'Close', 10:'Net_PnL', 11:'Pct_Change', 12:'Volume', 13:'Buildup', 14:'PCR'}
            
            if self.sort_col in col_map and col_map[self.sort_col] in df.columns:
                df = df.sort_values(by=col_map[self.sort_col], ascending=not self.sort_rev)
                
            for _, row in df.iterrows():
                sym = row.get('SYMBOL', '')
                spot = spot_prices.get(sym, 'N/A')
                data.append([
                    sym, spot, row.get('EXPIRY_DATE', ''), row.get('Sector', ''), 
                    row.get('Lot_Size', ''), row.get('Gap', ''), row.get('Open', ''), row.get('High', ''), 
                    row.get('Low', ''), row.get('Close', ''), row.get('Net_PnL', ''), 
                    f"{row.get('Pct_Change', 0):.2f}%", row.get('Volume', ''), row.get('Buildup', ''), row.get('PCR', '')
                ])
                
        self.sheet.set_sheet_data(data)
        
        # Update headers with arrows
        headers = []
        for i, c in enumerate(self.cols):
            if i == self.sort_col:
                arrow = " ▲" if not self.sort_rev else " ▼"
                headers.append(f"{c}{arrow}")
            else:
                headers.append(f"{c} ▼▲")
        self.sheet.headers(headers)
        
        green_cells = []
        red_cells = []
        
        for r, row_data in enumerate(data):
            buildup = str(row_data[13])
            if "Long Buildup" in buildup or "Short Covering" in buildup:
                green_cells.append((r, 13))
            elif "Short Buildup" in buildup or "Long Unwinding" in buildup:
                red_cells.append((r, 13))
                
            try:
                pnl = float(row_data[10])
                if pnl > 0: green_cells.append((r, 10))
                elif pnl < 0: red_cells.append((r, 10))
            except: pass
            
        if green_cells: self.sheet.highlight_cells(cells=green_cells, bg=None, fg="#00E676")
        if red_cells: self.sheet.highlight_cells(cells=red_cells, bg=None, fg="#FF1744")
            
        self.sheet.set_all_column_widths(110)

    def on_row_double_click(self, event):
        try:
            row = self.sheet.identify_row(event)
            if row is None: return
            symbol = self.sheet.get_cell_data(row, 0)
            SymbolDetailWindow(self.winfo_toplevel(), symbol, self.db, self.expiry_var.get(), self.start_date_var.get(), self.end_date_var.get())
        except Exception as e:
            pass

class OptionDetailWindow(ctk.CTkToplevel):
    def __init__(self, master, symbol, strike, opt_type, db, expiry='All', start_date=None, end_date=None):
        super().__init__(master)
        self.title(f"{symbol} Options Intelligence Drilldown")
        self.geometry("1150x750")
        self.db = db
        self.symbol = symbol
        self.strike = strike
        self.opt_type = opt_type
        self.expiry = expiry
        self.start_date = start_date
        self.end_date = end_date
        
        lbl = ctk.CTkLabel(self, text=f"Options Intelligence & Backtest: {symbol} {opt_type}", font=ctk.CTkFont(size=20, weight="bold"))
        lbl.pack(pady=10)
        
        self.intel_label = ctk.CTkLabel(self, text="Analyzing Market Data...", font=ctk.CTkFont(size=14), justify="left")
        self.intel_label.pack(padx=20, pady=10, anchor="w")
        
        cols = ("SnapShotDate", "Strike", "Type", "Open", "High", "Low", "Close", "MaxProfitOpp", "Volume", "OI")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100, anchor="e" if col not in ("SnapShotDate", "Type") else "w")
            
        self.tree.pack(fill="both", expand=True, padx=20, pady=10)
        self.after(100, self.load_data)

    def load_data(self):
        # Build query for all strikes for the symbol and opt_type to find Top 3
        query = f"""
        SELECT o.SnapShotDate, o.STRIKE_PRICE, o.OPTION_TYPE, o.OPEN_PRICE, o.HIGH_PRICE, o.LOW_PRICE, o.CLOSE_PRIC, o.TRADED_QUA, o.OI_NO_CON, s.Lot_Size
        FROM Options_FnO_BhavCopy_History_Transformed_New o
        INNER JOIN FNO_STOCKS_Sectors_Master_Refined_NEW s ON o.SYMBOL = s.Symbol
        WHERE o.SYMBOL = '{self.symbol}' AND o.OPTION_TYPE = '{self.opt_type}'
        """
        if self.expiry and self.expiry != 'All':
            query += f" AND CONVERT(varchar, o.EXPIRY_DATE, 23) = '{self.expiry}'"
        if self.start_date: query += f" AND o.SnapShotDate >= '{self.start_date}'"
        if self.end_date: query += f" AND o.SnapShotDate <= '{self.end_date}'"
        
        try:
            with self.db.get_connection() as conn:
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['MaxProfitOpp'] = (df['HIGH_PRICE'] - df['OPEN_PRICE']) * df['Lot_Size']
                    
                    # Group by Strike to find the Top 3 strikes with maximum average profit opportunity
                    strike_agg = df.groupby('STRIKE_PRICE').agg({'MaxProfitOpp': 'max', 'OI_NO_CON': 'last'}).reset_index()
                    top_3 = strike_agg.sort_values('MaxProfitOpp', ascending=False).head(3)
                    
                    intel_text = f"💡 Top 3 Strike Recommendations for Maximum Intraday Profit ({self.opt_type}):\n"
                    for _, row in top_3.iterrows():
                        intel_text += f"   ➤ Strike {row['STRIKE_PRICE']} | Max Profit Potential: ₹{row['MaxProfitOpp']:.2f} | Current OI: {row['OI_NO_CON']}\n"
                    
                    self.intel_label.configure(text=intel_text)
                    
                    # Show data for top 3 strikes ordered by date
                    top_strikes = top_3['STRIKE_PRICE'].tolist()
                    df_filtered = df[df['STRIKE_PRICE'].isin(top_strikes)].sort_values(by=['SnapShotDate', 'STRIKE_PRICE'], ascending=[False, True])
                    
                    for _, row in df_filtered.iterrows():
                        self.tree.insert("", "end", values=(
                            row['SnapShotDate'].strftime('%Y-%m-%d'), row['STRIKE_PRICE'], row['OPTION_TYPE'],
                            row['OPEN_PRICE'], row['HIGH_PRICE'], row['LOW_PRICE'], row['CLOSE_PRIC'], 
                            row['MaxProfitOpp'], row['TRADED_QUA'], row['OI_NO_CON']
                        ))
        except Exception as e:
            pass

class OptionsAnalysisFrame(ctk.CTkFrame):
    def __init__(self, master, db, mapi=None):
        super().__init__(master, corner_radius=15)
        self.db = db
        self.mapi = mapi
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.top_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.top_panel.grid(row=0, column=0, sticky="ew", padx=20, pady=10)
        
        ctk.CTkLabel(self.top_panel, text="Options Chain Matrix & Backtest", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, columnspan=7, sticky="w", pady=(0, 10))
        
        ctk.CTkLabel(self.top_panel, text="Sector:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        self.sector_var = ctk.StringVar(value="All")
        self.sector_dropdown = ctk.CTkComboBox(self.top_panel, variable=self.sector_var, command=self.on_sector_change, width=140)
        self.sector_dropdown.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="Industry:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        self.industry_var = ctk.StringVar(value="All")
        self.industry_dropdown = ctk.CTkComboBox(self.top_panel, variable=self.industry_var, command=self.on_filter_change, width=140)
        self.industry_dropdown.grid(row=1, column=3, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="Symbol:").grid(row=1, column=4, padx=5, pady=5, sticky="e")
        self.symbol_var = ctk.StringVar(value="All")
        self.symbol_dropdown = ctk.CTkComboBox(self.top_panel, variable=self.symbol_var, width=140)
        self.symbol_dropdown.grid(row=1, column=5, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="Expiry Date:").grid(row=2, column=0, padx=5, pady=5, sticky="e")
        self.expiry_var = ctk.StringVar(value="All")
        self.expiry_dropdown = ctk.CTkComboBox(self.top_panel, variable=self.expiry_var, width=140)
        self.expiry_dropdown.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="Start Date:").grid(row=2, column=2, padx=5, pady=5, sticky="e")
        self.start_date_var = ctk.StringVar()
        self.start_date_dropdown = ctk.CTkComboBox(self.top_panel, variable=self.start_date_var, width=140)
        self.start_date_dropdown.grid(row=2, column=3, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(self.top_panel, text="End Date:").grid(row=2, column=4, padx=5, pady=5, sticky="e")
        self.end_date_var = ctk.StringVar()
        self.end_date_dropdown = ctk.CTkComboBox(self.top_panel, variable=self.end_date_var, width=140)
        self.end_date_dropdown.grid(row=2, column=5, padx=5, pady=5, sticky="w")
        
        self.search_btn = ctk.CTkButton(self.top_panel, text="Search Analysis", command=self.on_filter_change, width=120)
        self.search_btn.grid(row=2, column=6, padx=15, pady=5, sticky="w")
        
        self.cols = ["Symbol", "Spot", "Sector", "Expiry", "Strike", "Type", "Close", "High", "Low", "LotSize", "MaxIntradayOpportunity", "Volume", "OI"]
        self.sheet = Sheet(self, headers=[f"{c} ▼▲" for c in self.cols])
        self.sheet.enable_bindings(("single_select", "row_select", "column_width_resize", "arrowkeys", "copy", "column_select"))
        if ctk.get_appearance_mode() == "Dark":
            self.sheet.change_theme("dark")
        else:
            self.sheet.change_theme("light")
            
        self.sheet.set_options(font=("Segoe UI", 12, "normal"), header_font=("Segoe UI", 14, "bold"))
        self.sheet.MT.bind("<Double-1>", self.on_row_double_click)
        self.sheet.extra_bindings([("column_select", self.on_column_select)])
        self.sheet.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=20, pady=15)
        
        self.sort_col = 10 # MaxIntradayOpportunity
        self.sort_rev = True
        self.current_df = None
        self.after(200, self.load_data)

    def get_default_expiry(self, expiries):
        from datetime import datetime
        today = datetime.now()
        closest_exp = None
        min_diff = None
        for exp in expiries:
            if exp == "All": continue
            try:
                dt = datetime.strptime(exp, '%Y-%m-%d')
                if dt.year == today.year and dt.month == today.month:
                    return exp
                elif dt > today:
                    diff = (dt - today).days
                    if min_diff is None or diff < min_diff:
                        min_diff = diff
                        closest_exp = exp
            except:
                pass
        return closest_exp if closest_exp else (expiries[1] if len(expiries) > 1 else "All")

    def load_data(self):
        sectors = ["All"] + self.db.get_all_sectors()
        self.sector_dropdown.configure(values=sectors)
        symbols = ["All"] + self.db.get_symbols()
        self.symbol_dropdown.configure(values=symbols)
        
        expiries = ["All"] + self.db.get_options_expiries()
        self.expiry_dropdown.configure(values=expiries)
        if len(expiries) > 1:
            self.expiry_var.set(self.get_default_expiry(expiries))
            
        dates = self.db.get_all_snapshot_dates()
        if dates:
            self.start_date_dropdown.configure(values=dates)
            self.end_date_dropdown.configure(values=dates)
            self.start_date_var.set(dates[0])
            self.end_date_var.set(dates[0])
            
        self.on_sector_change("All")

    def on_sector_change(self, choice):
        industries = ["All"] + self.db.get_industries_by_sector(choice)
        self.industry_dropdown.configure(values=industries)
        self.industry_var.set("All")
        self.on_filter_change(None)

    def on_filter_change(self, choice=None):
        df = self.db.get_options_advanced_analysis(
            sector=self.sector_var.get(), 
            industry=self.industry_var.get(), 
            symbol=self.symbol_var.get(),
            expiry=self.expiry_var.get(),
            start_date=self.start_date_var.get(),
            end_date=self.end_date_var.get()
        )
        self.current_df = df
        self.update_sheet_data()
        
    def on_column_select(self, event):
        col = event.column
        if self.sort_col == col:
            self.sort_rev = not self.sort_rev
        else:
            self.sort_col = col
            self.sort_rev = False
        self.update_sheet_data()
        
    def update_sheet_data(self):
        data = []
        if self.current_df is not None and not self.current_df.empty:
            df = self.current_df.copy()
            symbols = df['SYMBOL'].unique().tolist()
            spot_prices = self.mapi.get_bulk_live_prices(symbols) if self.mapi else {}
            
            col_map = {0:'SYMBOL', 2:'Sector', 3:'EXPIRY_DATE', 4:'STRIKE_PRICE', 5:'OPTION_TYPE', 6:'CLOSE_PRIC', 7:'HIGH_PRICE', 8:'LOW_PRICE', 9:'Lot_Size', 10:'MaxIntradayOpportunity', 11:'TRADED_QUA', 12:'OI_NO_CON'}
            if self.sort_col in col_map and col_map[self.sort_col] in df.columns:
                df = df.sort_values(by=col_map[self.sort_col], ascending=not self.sort_rev)
                
            for _, row in df.iterrows():
                sym = row.get('SYMBOL', '')
                spot = spot_prices.get(sym, 'N/A')
                data.append([
                    sym, spot, row.get('Sector', ''), row.get('EXPIRY_DATE', ''), row.get('STRIKE_PRICE', ''),
                    row.get('OPTION_TYPE', ''), row.get('CLOSE_PRIC', ''), row.get('HIGH_PRICE', ''),
                    row.get('LOW_PRICE', ''), row.get('Lot_Size', ''), row.get('MaxIntradayOpportunity', ''),
                    row.get('TRADED_QUA', ''), row.get('OI_NO_CON', '')
                ])
                
        self.sheet.set_sheet_data(data)
        
        headers = []
        for i, c in enumerate(self.cols):
            if i == self.sort_col:
                arrow = " ▲" if not self.sort_rev else " ▼"
                headers.append(f"{c}{arrow}")
            else:
                headers.append(f"{c} ▼▲")
        self.sheet.headers(headers)
        
        green_cells = []
        for r, row_data in enumerate(data):
            try:
                opp = float(row_data[10])
                if opp > 0: green_cells.append((r, 10))
            except: pass
            
        if green_cells: self.sheet.highlight_cells(cells=green_cells, bg=None, fg="#00E676")
            
        self.sheet.set_all_column_widths(110)

    def on_row_double_click(self, event):
        try:
            row = self.sheet.identify_row(event)
            if row is None: return
            symbol = self.sheet.get_cell_data(row, 0)
            strike = self.sheet.get_cell_data(row, 4)
            opt_type = self.sheet.get_cell_data(row, 5)
            OptionDetailWindow(self.winfo_toplevel(), symbol, strike, opt_type, self.db, self.expiry_var.get(), self.start_date_var.get(), self.end_date_var.get())
        except Exception as e:
            pass

class Best10TradesPopup(ctk.CTkToplevel):
    def __init__(self, master, db, mapi):
        super().__init__(master)
        self.title("🔥 LIVE BEST 10 FNO TRADES 🔥")
        self.geometry("1200x650")
        self.db = db
        self.mapi = mapi
        
        lbl = ctk.CTkLabel(self, text="HF Core Algorithm: Top 10 Live F&O Conviction Trades", font=ctk.CTkFont(size=26, weight="bold"))
        lbl.pack(pady=15)
        
        self.status = ctk.CTkLabel(self, text="Initializing Data Science Engine...", font=ctk.CTkFont(size=16, slant="italic"))
        self.status.pack(pady=5)
        
        cols = ("Rank", "Symbol", "Signal", "Conviction", "Buildup", "Live Spot", "AI Justification")
        self.tree = ttk.Treeview(self, columns=cols, show="headings")
        self.tree.heading("Rank", text="Rank")
        self.tree.column("Rank", width=50, anchor="center")
        self.tree.heading("Symbol", text="Symbol")
        self.tree.column("Symbol", width=100, anchor="w")
        self.tree.heading("Signal", text="Signal")
        self.tree.column("Signal", width=80, anchor="center")
        self.tree.heading("Conviction", text="Conviction Score")
        self.tree.column("Conviction", width=120, anchor="center")
        self.tree.heading("Buildup", text="Live Buildup")
        self.tree.column("Buildup", width=120, anchor="w")
        self.tree.heading("Live Spot", text="Live Spot")
        self.tree.column("Live Spot", width=90, anchor="e")
        self.tree.heading("AI Justification", text="Algorithmic Justification")
        self.tree.column("AI Justification", width=450, anchor="w")
        
        self.tree.pack(fill="both", expand=True, padx=20, pady=15)
        
        self._scan_ready = False
        self.scan_args = None
        self.after(100, self.poll_scan)
        threading.Thread(target=self.scan_market, daemon=True).start()

    def poll_scan(self):
        if self._scan_ready and self.scan_args:
            self.update_ui(*self.scan_args)
            self._scan_ready = False
        self.after(100, self.poll_scan)

    def scan_market(self):
        self.status.configure(text="Scanning live F&O universe, analyzing open interest, and PCR... Please wait.")
        dates = self.db.get_all_snapshot_dates()
        df = None
        if dates:
            for d in dates[:5]:
                df = self.db.get_futures_advanced_analysis(start_date=d, end_date=d)
                if df is not None and not df.empty:
                    break
        
        if df is None or df.empty:
            self.status.configure(text="Live Fallback Mode: Database empty, scanning core symbols...")
            symbols_all = self.db.get_symbols()
            if not symbols_all:
                symbols_all = ["RELIANCE.NS", "HDFCBANK.NS", "INFY.NS", "TCS.NS", "ICICIBANK.NS", "SBI.NS", "ITC.NS", "LT.NS"]
            spot_prices = self.mapi.get_bulk_live_prices(symbols_all)
            df = pd.DataFrame([{'SYMBOL': s, 'CLOSE_PRIC': spot_prices.get(s, 0), 'Pct_Change': 0, 'Volume': 5000000, 'PCR': 1.0, 'Start_OI': 0, 'End_OI': 0} for s in symbols_all])
        else:
            self.status.configure(text="Fetching live spot prices for complete F&O universe (Real-Time Intelligence)...")
            symbols_all = df['SYMBOL'].unique().tolist()
            spot_prices = self.mapi.get_bulk_live_prices(symbols_all)
        
        trades = []
        for _, row in df.iterrows():
            sym = row.get('SYMBOL', '')
            prev_close = row.get('Prev_Close', row.get('CLOSE_PRIC', 0))
            spot = spot_prices.get(sym, prev_close)
            
            # Recalculate Live % Change
            if prev_close > 0:
                pct = ((spot - prev_close) / prev_close) * 100
            else:
                pct = row.get('Pct_Change', 0)
                
            vol = row.get('Volume', 0)
            pcr = row.get('PCR', 1.0)
            
            # Re-evaluate live buildup
            oi_change = row.get('End_OI', 0) - row.get('Start_OI', 0)
            if pct > 0 and oi_change > 0: buildup = "Long Buildup ▲"
            elif pct < 0 and oi_change > 0: buildup = "Short Buildup ▼"
            elif pct < 0 and oi_change < 0: buildup = "Long Unwinding ▼"
            elif pct > 0 and oi_change < 0: buildup = "Short Covering ▲"
            else: buildup = "Neutral ◼"
            
            score = 0
            signal = "NEUTRAL"
            justification = []
            
            if "Long Buildup" in buildup:
                score += 3
                signal = "LONG ▲"
                justification.append("Strong Price+OI accumulation")
                if pcr < 0.8: 
                    score += 2
                    justification.append(f"Oversold Fear (PCR: {pcr:.2f}) - Contrarian Reversal")
                if pct > 2.0:
                    score += 1
                    justification.append(f"Extreme Momentum (+{pct:.1f}%)")
            elif "Short Buildup" in buildup:
                score += 3
                signal = "SHORT ▼"
                justification.append("Heavy Distribution detected")
                if pcr > 1.3:
                    score += 2
                    justification.append(f"Overbought Greed (PCR: {pcr:.2f}) - Pullback Expected")
                if pct < -2.0:
                    score += 1
                    justification.append(f"Downward Momentum ({pct:.1f}%)")
            elif "Short Covering" in buildup:
                score += 2
                signal = "LONG ▲"
                justification.append("Short Trap Unwinding - Squeeze")
                if pcr < 1.0: score += 1
                if pct > 1.5: score += 1
            
            if vol > 5000000:
                score += 1
                justification.append("Massive Institutional Volume")
            if vol > 10000000:
                score += 1
                justification.append("Ultra High Volume Breakout")
                
            if signal == "NEUTRAL" and abs(pct) > 0.1:
                if pct > 0:
                    signal = "MILD LONG ▲"
                    justification.append(f"Positive drift (+{pct:.1f}%)")
                    score += 1
                else:
                    signal = "MILD SHORT ▼"
                    justification.append(f"Negative drift ({pct:.1f}%)")
                    score += 1
            elif signal == "NEUTRAL":
                justification.append("Range-bound / Consolidating")
            
            trades.append({
                'Symbol': sym, 'Signal': signal, 'Score': score, 
                'Buildup': buildup, 'Vol': vol, 'Pct': pct,
                'Justification': " | ".join(justification),
                'Spot': spot
            })
                
        trades.sort(key=lambda x: (x['Score'], abs(x['Pct']), x['Vol']), reverse=True)
        top_10 = trades[:10]
        
        self.scan_args = (top_10, {t['Symbol']: t['Spot'] for t in top_10})
        self._scan_ready = True

    def update_ui(self, top_10, spot_prices):
        self.status.configure(text=f"Scan Complete! Displaying Top 10 High-Impact Trades. Updated dynamically.", text_color="#00E676")
        
        for i, t in enumerate(top_10, 1):
            spot = spot_prices.get(t['Symbol'], "N/A")
            tag = "even" if i % 2 == 0 else "odd"
            self.tree.insert("", "end", values=(
                f"#{i}", t['Symbol'], t['Signal'], f"{t['Score']}/7", 
                t['Buildup'], spot, t['Justification']
            ), tags=(tag,))
        
        self.tree.tag_configure("even", background="#2b2b2b" if ctk.get_appearance_mode() == "Dark" else "#f0f0f0")
        self.tree.tag_configure("odd", background="#1e1e1e" if ctk.get_appearance_mode() == "Dark" else "#ffffff")

class HedgeFundEngineFrame(ctk.CTkFrame):
    def __init__(self, master, db, mapi):
        super().__init__(master, corner_radius=15)
        self.db = db
        self.mapi = mapi
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure((0, 1), weight=1)
        
        self.top_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.top_panel.grid(row=0, column=0, columnspan=2, sticky="ew", padx=20, pady=15)
        
        ctk.CTkLabel(self.top_panel, text="HF Intelligence Engine", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        self.predict_btn = ctk.CTkButton(self.top_panel, text="Analyze & Predict", command=self.analyze, font=ctk.CTkFont(size=16, weight="bold"), height=40)
        self.predict_btn.pack(side="right", padx=10)
        
        self.top10_btn = ctk.CTkButton(self.top_panel, text="🔥 LIVE BEST 10 TRADES", command=self.show_best_trades, font=ctk.CTkFont(size=16, weight="bold"), height=40, fg_color="#D50000", hover_color="#B71C1C")
        self.top10_btn.pack(side="right", padx=10)
        
        self.symbol_var = ctk.StringVar()
        self.symbol_dropdown = ctk.CTkOptionMenu(self.top_panel, variable=self.symbol_var, font=ctk.CTkFont(size=14))
        self.symbol_dropdown.pack(side="right", padx=10)
        
        self.tabs = ctk.CTkTabview(self, corner_radius=10)
        self.tabs.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=20, pady=10)
        
        self.tabs.add("AI Predictions & Backtesting")
        self.tabs.add("Live Intraday Analysis")
        self.tabs.add("LIVE MUST TRADE")
        self.tabs.add("Proprietary Strategies")
        
        # Setup LIVE MUST TRADE tab
        must_trade_tab = self.tabs.tab("LIVE MUST TRADE")
        ctk.CTkLabel(must_trade_tab, text="High Conviction AI Trade Alerts", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        self.must_trade_status = ctk.CTkLabel(must_trade_tab, text="Click below to scan entire F&O Universe for guaranteed momentum setups...", font=ctk.CTkFont(size=14))
        self.must_trade_status.pack(pady=5)
        self.must_trade_btn = ctk.CTkButton(must_trade_tab, text="Launch Must-Trade Deep Scan", command=self.show_best_trades, fg_color="#00C853", hover_color="#00BFA5")
        self.must_trade_btn.pack(pady=10)
        
        # Setup Proprietary Strategies Tab
        strat_tab = self.tabs.tab("Proprietary Strategies")
        self.setup_strategies_tab(strat_tab)
        
        pred_tab = self.tabs.tab("AI Predictions & Backtesting")
        pred_tab.grid_columnconfigure((0,1), weight=1)
        pred_tab.grid_rowconfigure(1, weight=1)
        
        self.output_frame = ctk.CTkFrame(pred_tab, fg_color="transparent")
        self.output_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=10)
        self.output_frame.grid_columnconfigure((0,1,2), weight=1)
        
        self.box_day = self.create_target_box(self.output_frame, 0, "Intraday (Day)")
        self.box_week = self.create_target_box(self.output_frame, 1, "Swing (Week)")
        self.box_month = self.create_target_box(self.output_frame, 2, "Monthly (Month)")
        
        self.chart_frame = ctk.CTkFrame(pred_tab)
        self.chart_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        
        self.backtest_frame = ctk.CTkFrame(pred_tab, corner_radius=10)
        self.backtest_frame.grid(row=1, column=1, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.backtest_frame, text="Historical Backtesting Stats", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        self.bt_stats_textbox = ctk.CTkTextbox(self.backtest_frame, font=ctk.CTkFont(size=14), wrap="word")
        self.bt_stats_textbox.pack(fill="both", expand=True, padx=15, pady=10)
        self.bt_stats_textbox.insert("end", "Select a symbol and click Analyze to view backtest results.\n")
        
        intra_tab = self.tabs.tab("Live Intraday Analysis")
        intra_tab.grid_columnconfigure((0,1), weight=1)
        
        self.intra_stats_frame = ctk.CTkFrame(intra_tab, corner_radius=10)
        self.intra_stats_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.intra_rec_frame = ctk.CTkFrame(intra_tab, corner_radius=10)
        self.intra_rec_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        
        ctk.CTkLabel(self.intra_stats_frame, text="Current Live Technicals", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        self.live_tech_lbl = ctk.CTkLabel(self.intra_stats_frame, text="Awaiting Analysis...", font=ctk.CTkFont(size=16), justify="left")
        self.live_tech_lbl.pack(padx=15, pady=10, anchor="w")
        
        ctk.CTkLabel(self.intra_rec_frame, text="Intraday Intelligence Engine", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=10)
        self.live_rec_lbl = ctk.CTkLabel(self.intra_rec_frame, text="Awaiting Analysis...", font=ctk.CTkFont(size=16), justify="left")
        self.live_rec_lbl.pack(padx=15, pady=10, anchor="w")
        
        self.after(500, self.init_symbols)

    def setup_strategies_tab(self, parent):
        parent.grid_columnconfigure((0, 1), weight=1)
        parent.grid_rowconfigure(1, weight=1)
        
        control_frame = ctk.CTkFrame(parent, fg_color="transparent")
        control_frame.grid(row=0, column=0, columnspan=2, pady=10)
        
        ctk.CTkLabel(control_frame, text="Select Intelligence Strategy:", font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=10)
        self.strat_type_var = ctk.StringVar(value="Intraday")
        self.strat_type_dropdown = ctk.CTkOptionMenu(control_frame, variable=self.strat_type_var, values=["Intraday", "Swing", "Positional"], command=self.on_strat_type_change)
        self.strat_type_dropdown.pack(side="left", padx=10)
        
        self.strat_name_var = ctk.StringVar()
        self.strat_name_dropdown = ctk.CTkOptionMenu(control_frame, variable=self.strat_name_var)
        self.strat_name_dropdown.pack(side="left", padx=10)
        
        self.run_strat_btn = ctk.CTkButton(control_frame, text="Run Intelligence Engine", command=self.run_strategy, fg_color="#6200EA", hover_color="#3700B3")
        self.run_strat_btn.pack(side="left", padx=10)
        
        self.on_strat_type_change("Intraday")
        
        self.strat_result_frame = ctk.CTkFrame(parent, corner_radius=10)
        self.strat_result_frame.grid(row=1, column=0, columnspan=2, sticky="nsew", padx=10, pady=10)
        
        self.strat_title = ctk.CTkLabel(self.strat_result_frame, text="Strategy Output", font=ctk.CTkFont(size=22, weight="bold"))
        self.strat_title.pack(pady=15)
        
        self.strat_signal = ctk.CTkLabel(self.strat_result_frame, text="--", font=ctk.CTkFont(size=30, weight="bold"))
        self.strat_signal.pack(pady=10)
        
        metrics_frame = ctk.CTkFrame(self.strat_result_frame, fg_color="transparent")
        metrics_frame.pack(pady=10)
        
        self.strat_entry = ctk.CTkLabel(metrics_frame, text="Entry: --", font=ctk.CTkFont(size=18))
        self.strat_entry.grid(row=0, column=0, padx=20)
        self.strat_target = ctk.CTkLabel(metrics_frame, text="Target: --", font=ctk.CTkFont(size=18))
        self.strat_target.grid(row=0, column=1, padx=20)
        self.strat_sl = ctk.CTkLabel(metrics_frame, text="Stop Loss: --", font=ctk.CTkFont(size=18))
        self.strat_sl.grid(row=0, column=2, padx=20)
        
        self.strat_logic = ctk.CTkTextbox(self.strat_result_frame, font=ctk.CTkFont(size=14), height=150, wrap="word")
        self.strat_logic.pack(fill="x", padx=30, pady=20)
        self.strat_logic.insert("end", "Select a strategy and run the engine to see the precise setup.")
        
    def on_strat_type_change(self, choice):
        if choice == "Intraday":
            strats = ["VWAP Mean Reversion", "Momentum Breakout", "Gap & Go", "RSI Divergence"]
        elif choice == "Swing":
            strats = ["Moving Average Crossover", "Bollinger Band Squeeze", "Volume Accumulation"]
        else:
            strats = ["Fundamental Growth", "Value Support", "Macro Trend Following"]
        self.strat_name_dropdown.configure(values=strats)
        self.strat_name_var.set(strats[0])

    def run_strategy(self):
        self.run_strat_btn.configure(text="Analyzing...", state="disabled")
        symbol = self.symbol_var.get()
        threading.Thread(target=self._run_strat_bg, args=(symbol,), daemon=True).start()

    def _run_strat_bg(self, symbol):
        live_data = self.mapi.get_live_stock_data(symbol)
        df = self.db.get_ml_features(symbol)
        self.after(0, self._update_strat_ui, symbol, live_data, df)

    def _update_strat_ui(self, symbol, live_data, df):
        self.run_strat_btn.configure(text="Run Intelligence Engine", state="normal")
        strat_type = self.strat_type_var.get()
        strat_name = self.strat_name_var.get()
        
        if not live_data:
            live_data = {'Close': 100, 'High': 105, 'Low': 95, 'Open': 98, 'Volume': 0, 'RSI': 50, 'MACD': 0, 'MACD_Signal': 0, 'ATR': 5}
            if not df.empty:
                latest = df.iloc[-1]
                live_data = {
                    'Close': latest['CLOSE_PRIC'], 'High': latest['HIGH_PRICE'], 'Low': latest['LOW_PRICE'], 
                    'Open': latest['OPEN_PRICE'], 'Volume': latest['TRADED_QUA'], 'RSI': latest.get('RSI', 50),
                    'MACD': latest.get('MACD', 0), 'MACD_Signal': latest.get('MACD_Signal', 0), 'ATR': latest.get('ATR', 5)
                }
                
        price = live_data['Close']
        atr = live_data['ATR']
        rsi = live_data['RSI']
        macd = live_data['MACD']
        macd_sig = live_data['MACD_Signal']
        vwap = (live_data['High'] + live_data['Low'] + live_data['Close']) / 3
        
        signal = "NEUTRAL"
        color = "#FFA500"
        entry = price
        target = price
        sl = price
        logic = ""
        
        if strat_type == "Intraday":
            if strat_name == "VWAP Mean Reversion":
                if price > vwap + atr:
                    signal = "SELL ▼"
                    color = "#FF1744"
                    entry = price
                    target = vwap
                    sl = price + (atr * 0.5)
                    logic = f"Price (₹{price:.2f}) is overextended above VWAP (₹{vwap:.2f}). Expecting mean reversion back to VWAP."
                elif price < vwap - atr:
                    signal = "BUY ▲"
                    color = "#00E676"
                    entry = price
                    target = vwap
                    sl = price - (atr * 0.5)
                    logic = f"Price (₹{price:.2f}) is overextended below VWAP (₹{vwap:.2f}). Expecting mean reversion bounce to VWAP."
                else:
                    logic = f"Price (₹{price:.2f}) is near VWAP (₹{vwap:.2f}). No clear mean reversion setup currently."
            elif strat_name == "Momentum Breakout":
                if macd > macd_sig and rsi > 60:
                    signal = "BUY ▲"
                    color = "#00E676"
                    entry = price
                    target = price + (atr * 1.5)
                    sl = price - atr
                    logic = f"Strong bullish momentum. MACD is above signal and RSI is {rsi:.1f}. Breakout expected."
                elif macd < macd_sig and rsi < 40:
                    signal = "SELL ▼"
                    color = "#FF1744"
                    entry = price
                    target = price - (atr * 1.5)
                    sl = price + atr
                    logic = f"Strong bearish momentum. MACD is below signal and RSI is {rsi:.1f}. Breakdown expected."
                else:
                    logic = "Momentum is flat or conflicting. Wait for clear breakout/breakdown."
            elif strat_name == "Gap & Go":
                gap = live_data['Open'] - live_data.get('Prev_Close', live_data['Close'])
                if gap > (atr * 0.5) and price > live_data['Open']:
                    signal = "BUY ▲"
                    color = "#00E676"
                    entry = price
                    target = price + atr
                    sl = live_data['Open']
                    logic = "Bullish Gap & Go. Stock gapped up and is holding above open price."
                elif gap < -(atr * 0.5) and price < live_data['Open']:
                    signal = "SELL ▼"
                    color = "#FF1744"
                    entry = price
                    target = price - atr
                    sl = live_data['Open']
                    logic = "Bearish Gap & Go. Stock gapped down and is holding below open price."
                else:
                    logic = "No significant gap or gap has faded. Setup invalid."
            elif strat_name == "RSI Divergence":
                if rsi < 30:
                    signal = "BUY ▲"
                    color = "#00E676"
                    entry = price
                    target = price + (atr * 2)
                    sl = price - (atr * 0.5)
                    logic = f"RSI is extremely oversold ({rsi:.1f}). Look for bullish divergence and reversal."
                elif rsi > 70:
                    signal = "SELL ▼"
                    color = "#FF1744"
                    entry = price
                    target = price - (atr * 2)
                    sl = price + (atr * 0.5)
                    logic = f"RSI is extremely overbought ({rsi:.1f}). Look for bearish divergence and reversal."
                else:
                    logic = f"RSI is neutral ({rsi:.1f}). No divergence detected."
        elif strat_type == "Swing":
            if strat_name == "Moving Average Crossover":
                if macd > 0 and macd > macd_sig:
                    signal = "BUY ▲"
                    color = "#00E676"
                    entry = price
                    target = price + (atr * 3)
                    sl = price - (atr * 1.5)
                    logic = "Bullish MACD crossover in positive territory indicates start of a new uptrend."
                elif macd < 0 and macd < macd_sig:
                    signal = "SELL ▼"
                    color = "#FF1744"
                    entry = price
                    target = price - (atr * 3)
                    sl = price + (atr * 1.5)
                    logic = "Bearish MACD crossover in negative territory indicates start of a new downtrend."
                else:
                    logic = "No clear moving average crossover signal."
            elif strat_name == "Bollinger Band Squeeze":
                signal = "WAIT ◼"
                color = "#FFA500"
                entry = price
                target = price + (atr * 4)
                sl = price - atr
                logic = "Volatility is contracting. Wait for a high-volume breakout from the squeeze to establish a swing position."
            elif strat_name == "Volume Accumulation":
                if rsi > 50 and price > vwap:
                    signal = "BUY ▲"
                    color = "#00E676"
                    entry = price
                    target = price + (atr * 3.5)
                    sl = price - atr
                    logic = "Steady price increase with strong volume accumulation. Uptrend is likely to continue."
                else:
                    logic = "No strong volume accumulation detected."
        elif strat_type == "Positional":
            if rsi > 55 and macd > macd_sig:
                signal = "BUY ▲"
                color = "#00E676"
                entry = price
                target = price + (atr * 8)
                sl = price - (atr * 3)
                logic = "Long-term bullish trend confirmed by multiple indicators. Favorable risk/reward for a positional hold."
            elif rsi < 45 and macd < macd_sig:
                signal = "SELL ▼"
                color = "#FF1744"
                entry = price
                target = price - (atr * 8)
                sl = price + (atr * 3)
                logic = "Long-term bearish trend confirmed. Consider short positions or hedging portfolio."
            else:
                logic = "Market is in a broad range. No clear positional trend established."
                
        self.strat_title.configure(text=f"Strategy: {strat_name} ({strat_type})")
        self.strat_signal.configure(text=signal, text_color=color)
        self.strat_entry.configure(text=f"Entry: ₹{entry:.2f}")
        self.strat_target.configure(text=f"Target: ₹{target:.2f}")
        self.strat_sl.configure(text=f"Stop Loss: ₹{sl:.2f}")
        
        if strat_type == "Intraday":
            duration = "1 to 6 Hours (Strictly close before Market End)"
            approach = "Current Month FUTURES, or ATM/OTM OPTIONS (Call/Put) to catch Gamma momentum."
        elif strat_type == "Swing":
            duration = "3 to 15 Trading Days"
            approach = "Current/Next Month FUTURES, or ITM OPTIONS (Delta 0.60+) to balance Theta decay."
        else:
            duration = "4 Weeks to 3 Months (Positional Hold)"
            approach = "Next Month FUTURES, Deep ITM OPTIONS (Delta 0.80+), or Cash Equity to avoid time decay."
            
        self.strat_logic.delete("1.0", "end")
        rr = abs(target - entry) / abs(entry - sl) if abs(entry - sl) > 0 else 0
        self.strat_logic.insert("end", f"INTELLIGENCE REPORT for {symbol}:\n\n{logic}\n\n"
                                       f"⏱️ Target Duration: {duration}\n"
                                       f"🛠️ Best Execution Instrument: {approach}\n\n"
                                       f"Risk/Reward Ratio: {rr:.1f}")

    def create_target_box(self, parent, col, title):
        frame = ctk.CTkFrame(parent, border_width=1, border_color="#cccccc", corner_radius=10)
        frame.grid(row=0, column=col, padx=15, sticky="nsew")
        ctk.CTkLabel(frame, text=title, font=ctk.CTkFont(size=18, weight="bold")).pack(pady=10)
        
        lbl_signal = ctk.CTkLabel(frame, text="--", font=ctk.CTkFont(size=22, weight="bold"))
        lbl_signal.pack(pady=5)
        lbl_entry = ctk.CTkLabel(frame, text="Entry: --", font=ctk.CTkFont(size=16))
        lbl_entry.pack(pady=3)
        lbl_target = ctk.CTkLabel(frame, text="Target: --", font=ctk.CTkFont(size=16))
        lbl_target.pack(pady=3)
        lbl_sl = ctk.CTkLabel(frame, text="Stop Loss: --", font=ctk.CTkFont(size=16))
        lbl_sl.pack(pady=10)
        
        return {'signal': lbl_signal, 'entry': lbl_entry, 'target': lbl_target, 'sl': lbl_sl}

    def init_symbols(self):
        symbols = self.db.get_symbols()
        if symbols:
            self.symbol_dropdown.configure(values=symbols)
            self.symbol_var.set(symbols[0])
            
        self._analyze_ready = False
        self.analyze_args = None
        self.after(100, self.poll_analyze)

    def poll_analyze(self):
        if self._analyze_ready and self.analyze_args:
            self._update_ui(*self.analyze_args)
            self._analyze_ready = False
        self.after(100, self.poll_analyze)

    def update_box(self, box, signal, color, entry, target, sl):
        box['signal'].configure(text=signal, text_color=color)
        box['entry'].configure(text=f"Best Entry: ₹{entry:.2f}")
        box['target'].configure(text=f"Target: ₹{target:.2f}")
        box['sl'].configure(text=f"Stop Loss: ₹{sl:.2f}")

    def show_best_trades(self):
        Best10TradesPopup(self.winfo_toplevel(), self.db, self.mapi)

    def analyze(self):
        symbol = self.symbol_var.get()
        self.predict_btn.configure(text="Analyzing...", state="disabled")
        threading.Thread(target=self._analyze_bg, args=(symbol,), daemon=True).start()
        
    def _analyze_bg(self, symbol):
        df = self.db.get_ml_features(symbol)
        live_data = self.mapi.get_live_stock_data(symbol)
        bt_stats = self.db.get_backtesting_stats(symbol)
        
        self.analyze_args = (symbol, df, live_data, bt_stats)
        self._analyze_ready = True

    def _update_ui(self, symbol, df, live_data, bt_stats):
        self.predict_btn.configure(text="Analyze & Predict", state="normal")
        if df.empty or len(df) < 20:
            messagebox.showwarning("Not Enough Data", f"Not enough historical data to analyze {symbol}")
            return
            
        latest = df.iloc[-1]
        
        # Merge live data if available
        if live_data:
            current_price = live_data['Close']
            vwap_proxy = (live_data['High'] + live_data['Low'] + live_data['Close']) / 3
            rsi = live_data['RSI']
            macd = live_data['MACD']
            macd_sig = live_data['MACD_Signal']
            atr = live_data['ATR']
            is_live = True
        else:
            current_price = latest['CLOSE_PRIC']
            vwap_proxy = (latest['HIGH_PRICE'] + latest['LOW_PRICE'] + latest['CLOSE_PRIC']) / 3
            rsi = latest['RSI']
            macd = latest['MACD']
            macd_sig = latest['MACD_Signal']
            atr = latest['ATR']
            is_live = False
            
        pcr = latest.get('PCR', 1.0)
        
        # Trend Analysis
        is_macd_bull = macd > macd_sig
        is_rsi_bull = 40 < rsi < 70
        is_rsi_os = rsi <= 30
        is_rsi_ob = rsi >= 70
        
        df['Days'] = df['SnapShotDate'].map(pd.Timestamp.toordinal)
        X = df[['Days', 'TRADED_QUA', 'OI_NO_CON', 'PCR', 'RSI', 'MACD']].values
        y = df['CLOSE_PRIC'].values
        
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        last_date = df['SnapShotDate'].iloc[-1]
        future_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=30)
        recent_X = np.array([[d.toordinal(), latest['TRADED_QUA'], latest['OI_NO_CON'], pcr, rsi, macd] for d in future_dates])
        future_preds = model.predict(recent_X)
        
        pred_day = future_preds[0]
        pred_week = future_preds[6]
        pred_month = future_preds[29]
        
        color_long = "#00E676" if ctk.get_appearance_mode() == "Dark" else "#008000"
        color_short = "#FF1744" if ctk.get_appearance_mode() == "Dark" else "#D50000"
        color_neutral = "#FFA500"
        
        score_day = sum([is_macd_bull, is_rsi_bull, pred_day > current_price, pcr < 1.2])
        if score_day >= 3: 
            day_sig = "LONG ▲"
            self.update_box(self.box_day, day_sig, color_long, vwap_proxy, current_price + atr, vwap_proxy - (0.5*atr))
        elif score_day <= 1: 
            day_sig = "SHORT ▼"
            self.update_box(self.box_day, day_sig, color_short, vwap_proxy, current_price - atr, vwap_proxy + (0.5*atr))
        else: 
            day_sig = "NEUTRAL ◼"
            self.update_box(self.box_day, day_sig, color_neutral, current_price, current_price + atr, current_price - atr)
            
        score_week = sum([is_macd_bull, pred_week > current_price, pcr < 1.0])
        if score_week >= 2: self.update_box(self.box_week, "SWING LONG ▲", color_long, current_price, current_price + (atr*2), current_price - atr)
        elif score_week == 0: self.update_box(self.box_week, "SWING SHORT ▼", color_short, current_price, current_price - (atr*2), current_price + atr)
        else: self.update_box(self.box_week, "NEUTRAL ◼", color_neutral, current_price, current_price + (atr*2), current_price - (atr*2))
            
        score_month = sum([pred_month > current_price, is_macd_bull])
        if score_month >= 2: self.update_box(self.box_month, "MONTHLY LONG ▲", color_long, current_price, current_price + (atr*4), current_price - (atr*1.5))
        elif score_month == 0: self.update_box(self.box_month, "MONTHLY SHORT ▼", color_short, current_price, current_price - (atr*4), current_price + (atr*1.5))
        else: self.update_box(self.box_month, "NEUTRAL ◼", color_neutral, current_price, current_price + (atr*4), current_price - (atr*4))
        
        # Populate Live Intraday Analysis
        tech_text = (
            f"• Spot Price: ₹{current_price:.2f} ({'LIVE' if is_live else 'Historical'})\n"
            f"• VWAP Proxy: ₹{vwap_proxy:.2f}\n"
            f"• RSI (14): {rsi:.2f} {'(Oversold)' if is_rsi_os else '(Overbought)' if is_rsi_ob else '(Neutral)'}\n"
            f"• MACD: {macd:.2f} vs Signal: {macd_sig:.2f} ({'Bullish' if is_macd_bull else 'Bearish'})\n"
            f"• ATR (Volatility): ₹{atr:.2f}\n"
            f"• Option PCR: {pcr}\n"
        )
        self.live_tech_lbl.configure(text=tech_text)
        
        rec_text = (
            f"• Suggested Intraday Bias: {day_sig}\n"
            f"• Confidence Score: {score_day}/4\n\n"
        )
        if score_day >= 3:
            rec_text += "📈 Strong Bullish convergence. Buy dips near VWAP.\n"
        elif score_day <= 1:
            rec_text += "📉 Strong Bearish convergence. Sell rips near VWAP.\n"
        else:
            rec_text += "⚖️ Conflicting indicators. Wait for trend confirmation or scalp range extremes.\n"
            
        if is_rsi_os and score_day >= 2:
            rec_text += "💡 Contrarian Setup: RSI is oversold and momentum is shifting. Reversal possible.\n"
        elif is_rsi_ob and score_day <= 2:
            rec_text += "💡 Contrarian Setup: RSI is overbought. Risk of profit booking.\n"
            
        self.live_rec_lbl.configure(text=rec_text)

        # Build highly detailed Alpha Report
        report = f"==== HEDGE FUND ALPHA REPORT: {symbol} ====\n\n"
        report += f"1. DATA SOURCE: {'▲ LIVE FEED ACCURATE' if is_live else '◼ HISTORICAL SNAPSHOT'} (Price: ₹{current_price:.2f})\n\n"
        
        report += f"2. TECHNICAL SENTIMENT MATRIX:\n"
        report += f"   - RSI (14): {rsi:.2f} "
        if is_rsi_os: report += "(EXTREMELY OVERSOLD - Bounce Imminent)\n"
        elif is_rsi_ob: report += "(EXTREMELY OVERBOUGHT - Reversal Risk)\n"
        else: report += "(Neutral Momentum)\n"
        
        report += f"   - MACD Crossover: {'BULLISH ▲' if is_macd_bull else 'BEARISH ▼'} (MACD: {macd:.2f}, Signal: {macd_sig:.2f})\n"
        report += f"   - Volatility (ATR): ₹{atr:.2f} per day average move.\n\n"
        
        report += f"3. F&O DERIVATIVES INTELLIGENCE:\n"
        report += f"   - Put-Call Ratio (PCR): {pcr:.2f} "
        if pcr < 0.7: report += "(Oversold / Fear - Contrarian Long Setup)\n"
        elif pcr > 1.3: report += "(Overbought / Greed - Contrarian Short Setup)\n"
        else: report += "(Balanced Structure)\n"
        
        report += f"   - F&O Open Interest: {latest['OI_NO_CON']} Contracts\n\n"
        
        report += f"4. MACHINE LEARNING PREDICITIVE TARGETS (RandomForest Ensembles):\n"
        report += f"   - Projected +1 Day: ₹{pred_day:.2f}\n"
        report += f"   - Projected +7 Days: ₹{pred_week:.2f}\n"
        report += f"   - Projected +30 Days: ₹{pred_month:.2f}\n\n"
        
        report += f"5. HISTORICAL BACKTEST SUMMARY:\n"
        if bt_stats:
            fade_prob = bt_stats['gap_up_fade_prob']
            recover_prob = bt_stats['gap_down_recover_prob']
            report += f"   - Gap Up Fade Probability: {fade_prob:.1f}%\n"
            report += f"   - Gap Down Recover Probability: {recover_prob:.1f}%\n"
            report += f"   - Avg Intraday Range: ₹{bt_stats['avg_intraday_range']:.2f}\n\n"
            
            report += "🗓️ Month-wise Intraday Profitability:\n"
            for m in bt_stats['monthly_data']:
                report += f"   ➤ {m['Month']} | Win Rate: {m['Win_Rate']:.1f}% | Avg Gap: {m['Avg_Gap']:.2f}%\n"
        else:
            report += "   - No backtesting data available for this symbol.\n"
            
        self.bt_stats_textbox.delete("1.0", "end")
        self.bt_stats_textbox.insert("end", report)
        
        for widget in self.chart_frame.winfo_children(): widget.destroy()
            
        fig, ax = plt.subplots(figsize=(8, 4), dpi=100)
        
        if ctk.get_appearance_mode() == "Dark":
            fig.patch.set_facecolor('#1a1a1a')
            ax.set_facecolor('#1a1a1a')
            ax.tick_params(colors='white')
            for spine in ax.spines.values(): spine.set_color('#333333')
            ax.legend(facecolor='#1a1a1a', edgecolor='#333333', labelcolor='white')
        else:
            fig.patch.set_facecolor('#ffffff')
            ax.set_facecolor('#ffffff')
            ax.tick_params(colors='black')
            for spine in ax.spines.values(): spine.set_color('#cccccc')
            ax.legend(facecolor='#ffffff', edgecolor='#cccccc', labelcolor='black')
        
        hist_dates = df['SnapShotDate'].tail(60)
        ax.plot(hist_dates, df['CLOSE_PRIC'].tail(60), label='Historical (60d)', color='#1f538d', linewidth=2)
        ax.plot(future_dates, future_preds, label='ML Projection (30d)', color='#FFA500', linestyle='--', linewidth=2)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

class AdvancedBacktestSearchWindow(ctk.CTkToplevel):
    def __init__(self, master, db):
        super().__init__(master)
        self.title("Advanced Backtesting - Date Search (BTST & Intraday)")
        self.geometry("1400x800")
        self.db = db
        
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.top_panel = ctk.CTkFrame(self, fg_color="transparent")
        self.top_panel.grid(row=0, column=0, sticky="ew", padx=20, pady=15)
        
        ctk.CTkLabel(self.top_panel, text="Search BTST / Top Trades by Date", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        
        self.search_btn = ctk.CTkButton(self.top_panel, text="Search", command=self.load_data)
        self.search_btn.pack(side="right", padx=10)
        
        self.date_var = ctk.StringVar()
        self.date_dropdown = ctk.CTkOptionMenu(self.top_panel, variable=self.date_var, width=150)
        self.date_dropdown.pack(side="right", padx=10)
        
        self.tabs = ctk.CTkTabview(self, corner_radius=10)
        self.tabs.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        
        self.tabs.add("Futures BTST")
        self.tabs.add("Options Intraday")
        
        self.fut_tree = self.create_fut_tree(self.tabs.tab("Futures BTST"))
        self.opt_tree = self.create_opt_tree(self.tabs.tab("Options Intraday"))
        
        self.after(200, self.init_dates)
        
    def init_dates(self):
        dates = self.db.get_all_snapshot_dates()
        if dates:
            self.date_dropdown.configure(values=dates)
            self.date_var.set(dates[0])
            self.load_data()
            
    def create_fut_tree(self, parent):
        cols = ("Symbol", "Expiry", "PrevClose", "Open", "High", "Low", "Close", "Gap_Profit", "OpenToHigh_Profit", "OpenToClose_Profit", "HighToClose_Profit", "Max_BTST_Loss")
        tree = ttk.Treeview(parent, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="e" if col not in ("Symbol", "Expiry") else "w")
        tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        return tree
        
    def create_opt_tree(self, parent):
        cols = ("Symbol", "Expiry", "Type", "Strike", "Open", "High", "Low", "Close", "OpenToHigh_Profit", "OpenToClose_Profit", "HighToClose_Profit")
        tree = ttk.Treeview(parent, columns=cols, show="headings")
        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=100, anchor="e" if col not in ("Symbol", "Expiry", "Type") else "w")
        tree.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
        tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        return tree
        
    def load_data(self):
        date = self.date_var.get()
        if not date: return
        
        df_fut = self.db.get_btst_futures(date)
        df_opt = self.db.get_btst_options(date)
        
        for item in self.fut_tree.get_children(): self.fut_tree.delete(item)
        if not df_fut.empty:
            for _, row in df_fut.iterrows():
                self.fut_tree.insert("", "end", values=(
                    row.get('SYMBOL',''), row.get('EXPIRY_DATE',''), row.get('PREVIOUS_S',''),
                    row.get('OPEN_PRICE',''), row.get('HIGH_PRICE',''), row.get('LOW_PRICE',''), row.get('CLOSE_PRIC',''),
                    row.get('Gap_Profit',''), row.get('Open_To_High_Profit',''), row.get('Open_To_Close_Profit',''),
                    row.get('High_To_Close_Profit',''), row.get('Max_BTST_Loss','')
                ))
                
        for item in self.opt_tree.get_children(): self.opt_tree.delete(item)
        if not df_opt.empty:
            for _, row in df_opt.iterrows():
                self.opt_tree.insert("", "end", values=(
                    row.get('SYMBOL',''), row.get('EXPIRY_DATE',''), row.get('OPTION_TYPE',''), row.get('STRIKE_PRICE',''),
                    row.get('OPEN_PRICE',''), row.get('HIGH_PRICE',''), row.get('LOW_PRICE',''), row.get('CLOSE_PRIC',''),
                    row.get('Open_To_High_Profit',''), row.get('Open_To_Close_Profit',''), row.get('High_To_Close_Profit','')
                ))

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.title("Professional Hedge Fund Terminal")
        self.geometry("1600x900") # Increased default size
        
        update_treeview_style(ctk.get_appearance_mode())
        
        self.db = DatabaseHelper()
        self.mapi = MarketAPI()
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.sidebar_frame = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="PRO TERMINAL", font=ctk.CTkFont(size=26, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(30, 20))
        
        btn_font = ctk.CTkFont(size=16)
        
        self.global_btn = ctk.CTkButton(self.sidebar_frame, text="Global Markets", font=btn_font, height=45, command=self.show_global)
        self.global_btn.grid(row=1, column=0, padx=20, pady=10)

        self.picks_btn = ctk.CTkButton(self.sidebar_frame, text="Top 10 Picks", font=btn_font, height=45, command=self.show_picks)
        self.picks_btn.grid(row=2, column=0, padx=20, pady=10)
        
        self.futures_btn = ctk.CTkButton(self.sidebar_frame, text="Futures Analysis", font=btn_font, height=45, command=self.show_futures)
        self.futures_btn.grid(row=3, column=0, padx=20, pady=10)
        
        self.options_btn = ctk.CTkButton(self.sidebar_frame, text="Options Analysis", font=btn_font, height=45, command=self.show_options)
        self.options_btn.grid(row=4, column=0, padx=20, pady=10)
        
        self.predict_btn = ctk.CTkButton(self.sidebar_frame, text="HF Decision Engine", font=btn_font, height=45, command=self.show_prediction, fg_color="#1f538d")
        self.predict_btn.grid(row=5, column=0, padx=20, pady=10)
        
        self.btst_btn = ctk.CTkButton(self.sidebar_frame, text="BTST / Date Search", font=btn_font, height=45, command=self.open_btst_search, fg_color="#00695c")
        self.btst_btn.grid(row=6, column=0, padx=20, pady=10)
        
        self.participants_btn = ctk.CTkButton(self.sidebar_frame, text="Market Participants", font=btn_font, height=45, command=self.show_participants)
        self.participants_btn.grid(row=7, column=0, padx=20, pady=10)
        
        self.journal_btn = ctk.CTkButton(self.sidebar_frame, text="My Trading Journal", font=btn_font, height=45, command=self.show_journal)
        self.journal_btn.grid(row=8, column=0, padx=20, pady=10)
        
        # Theme Switcher
        self.theme_label = ctk.CTkLabel(self.sidebar_frame, text="Theme:", font=ctk.CTkFont(size=14))
        self.theme_label.grid(row=9, column=0, padx=20, pady=(10, 0), sticky="w")
        self.appearance_menu = ctk.CTkOptionMenu(self.sidebar_frame, values=["Dark", "Light", "System"], command=self.change_appearance_mode, font=ctk.CTkFont(size=14))
        self.appearance_menu.grid(row=10, column=0, padx=20, pady=(0, 20), sticky="ew")
        
        self.global_frame = GlobalMarketFrame(self, self.mapi)
        self.picks_frame = TopPicksFrame(self, self.mapi)
        self.futures_frame = FuturesAnalysisFrame(self, self.db, self.mapi)
        self.options_frame = OptionsAnalysisFrame(self, self.db, self.mapi)
        self.predict_frame = HedgeFundEngineFrame(self, self.db, self.mapi)
        self.participants_frame = MarketParticipantsFrame(self)
        self.journal_frame = TradingJournalFrame(self)
        
        self.show_global()

    def change_appearance_mode(self, new_mode: str):
        ctk.set_appearance_mode(new_mode)
        update_treeview_style(new_mode)
        
        from tksheet import Sheet
        
        def update_sheets(widget):
            for child in widget.winfo_children():
                if isinstance(child, Sheet):
                    if new_mode == "Dark":
                        child.change_theme("dark")
                    else:
                        child.change_theme("light blue")
                elif hasattr(child, "winfo_children"):
                    update_sheets(child)
                    
        update_sheets(self)

    def hide_all_frames(self):
        self.global_frame.grid_forget()
        self.picks_frame.grid_forget()
        self.futures_frame.grid_forget()
        self.options_frame.grid_forget()
        self.predict_frame.grid_forget()
        self.participants_frame.grid_forget()
        self.journal_frame.grid_forget()

    def show_global(self):
        self.hide_all_frames()
        self.global_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

    def show_picks(self):
        self.hide_all_frames()
        self.picks_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

    def show_futures(self):
        self.hide_all_frames()
        self.futures_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

    def show_options(self):
        self.hide_all_frames()
        self.options_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

    def show_prediction(self):
        self.hide_all_frames()
        self.predict_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

    def show_participants(self):
        self.hide_all_frames()
        self.participants_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

    def show_journal(self):
        self.hide_all_frames()
        self.journal_frame.grid(row=0, column=1, sticky="nsew", padx=30, pady=30)

    def open_btst_search(self):
        AdvancedBacktestSearchWindow(self, self.db)

class MarketParticipantsFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=15)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(self, text="Market Participants Activity (FII / DII / PROP / RETAIL)", font=ctk.CTkFont(size=24, weight="bold")).grid(row=0, column=0, pady=15)
        
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.tabs.add("Yearly Summary (5 Years)")
        self.tabs.add("Monthly Summary (1 Year)")
        self.tabs.add("Day Wise Summary")
        
        cols = ["Period", "FII Cash (Cr)", "FII FnO (Cr)", "DII Cash (Cr)", "DII FnO (Cr)", "PROP Desk (Cr)", "Retail (Cr)", "Net Trend"]
        self.y_sheet = self._setup_tab(self.tabs.tab("Yearly Summary (5 Years)"), cols)
        self.m_sheet = self._setup_tab(self.tabs.tab("Monthly Summary (1 Year)"), cols)
        
        day_tab = self.tabs.tab("Day Wise Summary")
        top_bar = ctk.CTkFrame(day_tab, fg_color="transparent")
        top_bar.pack(fill="x", pady=5)
        ctk.CTkLabel(top_bar, text="Select Month:").pack(side="left", padx=5)
        self.d_month_var = ctk.StringVar(value="April 2026")
        ctk.CTkOptionMenu(top_bar, variable=self.d_month_var, values=["April 2026", "March 2026", "February 2026"], command=self.load_day_data).pack(side="left", padx=5)
        self.d_sheet = self._setup_tab(day_tab, cols)
        
        self.load_data()

    def apply_colors(self, sheet, data):
        sheet.set_sheet_data(data)
        green = []
        red = []
        for r, row in enumerate(data):
            if "Bullish" in str(row[-1]):
                green.append((r, len(row)-1))
            elif "Bearish" in str(row[-1]):
                red.append((r, len(row)-1))
        if green: sheet.highlight_cells(cells=green, bg=None, fg="#00E676")
        if red: sheet.highlight_cells(cells=red, bg=None, fg="#FF1744")

    def load_data(self):
        y_data = self.master.db.get_market_participants("Year")
        m_data = self.master.db.get_market_participants("Month")
        self.apply_colors(self.y_sheet, y_data)
        self.apply_colors(self.m_sheet, m_data)
        self.load_day_data()
        
    def load_day_data(self, *args):
        d_data = self.master.db.get_market_participants("Day", self.d_month_var.get())
        self.apply_colors(self.d_sheet, d_data)

    def _setup_tab(self, parent, cols):
        sheet = Sheet(parent, headers=cols)
        sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark": sheet.change_theme("dark")
        else: sheet.change_theme("light blue")
        sheet.set_options(font=("Segoe UI", 12, "normal"), header_font=("Segoe UI", 13, "bold"))
        sheet.pack(fill="both", expand=True, padx=10, pady=10)
        return sheet

class TradingJournalFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=15)
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", pady=15, padx=20)
        
        ctk.CTkLabel(top, text="My Trading Journal (IndMoney)", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text="Reload Data", fg_color="#FF8F00", hover_color="#F57C00", command=self.load_data).pack(side="right")
        
        self.tabs = ctk.CTkTabview(self)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.tabs.add("Trade History")
        
        hist = self.tabs.tab("Trade History")
        
        # Filter Frame
        ff = ctk.CTkFrame(hist, fg_color="transparent")
        ff.pack(fill="x", pady=(0, 10))
        
        # Criteria: Entry Date (From Date and To Date), Exit Date (From Date and To Date), Symbol, P/L, Equity or FnO
        
        ctk.CTkLabel(ff, text="From:").pack(side="left", padx=(2, 2))
        self.f_entry_from = ctk.StringVar()
        e_from = ctk.CTkEntry(ff, textvariable=self.f_entry_from, placeholder_text="YYYY-MM-DD", width=85)
        e_from.pack(side="left", padx=2)
        e_from.bind("<KeyRelease>", lambda e: self.apply_filters())
        
        ctk.CTkLabel(ff, text="To:").pack(side="left", padx=(2, 2))
        self.f_entry_to = ctk.StringVar()
        e_to = ctk.CTkEntry(ff, textvariable=self.f_entry_to, placeholder_text="YYYY-MM-DD", width=85)
        e_to.pack(side="left", padx=2)
        e_to.bind("<KeyRelease>", lambda e: self.apply_filters())
        
        self.f_year = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(ff, variable=self.f_year, values=["All", "2023", "2024", "2025", "2026"], width=60, command=lambda _: self.apply_filters()).pack(side="left", padx=2)
        
        self.f_month = ctk.StringVar(value="All")
        months = ["All", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12"]
        ctk.CTkOptionMenu(ff, variable=self.f_month, values=months, width=50, command=lambda _: self.apply_filters()).pack(side="left", padx=2)
        
        self.f_sym = ctk.StringVar()
        sym_entry = ctk.CTkEntry(ff, textvariable=self.f_sym, placeholder_text="Symbol...", width=70)
        sym_entry.pack(side="left", padx=2)
        sym_entry.bind("<KeyRelease>", lambda e: self.apply_filters())
        
        self.f_pl = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(ff, variable=self.f_pl, values=["All", "Profit", "Loss"], width=70, command=lambda _: self.apply_filters()).pack(side="left", padx=2)
        
        self.f_cat = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(ff, variable=self.f_cat, values=["All", "Equity", "FnO"], width=70, command=lambda _: self.apply_filters()).pack(side="left", padx=2)
        
        ctk.CTkButton(ff, text="Search", command=self.apply_filters, width=50).pack(side="left", padx=2)
        ctk.CTkButton(ff, text="Clear", command=self.clear_filters, width=50, fg_color="#555555").pack(side="left", padx=2)
        
        self.headers = ['S.NO', 'Category', 'Purpose', 'Instrument Type', 'Instrument', 'Qty', 'Lot', 'Buy Date', 'Buy Price', 'Buy Amount', 'Sale Date', 'Sale Price', 'Sale Amount', 'Profit Amount', 'Profit %', 'Broker', 'Status', 'RISK 1:2', 'SL (Max)', 'Target', 'Remarks', 'Expected Profit', 'No Of Days Invested', 'P/L', 'ACTION', 'Remarks.1', 'Max Accepted Loss', 'MTF Interest', 'MTF Amount 70%', 'Your Investment Amount 30%']
        self.sheet = Sheet(hist, headers=self.headers)
        self.sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark": self.sheet.change_theme("dark")
        else: self.sheet.change_theme("light blue")
        self.sheet.pack(fill="both", expand=True)
        
        self.full_df = None
        self.load_data()

    def load_data(self):
        try:
            import pandas as pd
            import re
            file_path = r"c:\Users\navin\StockMarketFnO\data\journal\Indmoney Transaction.xlsx"
            xls = pd.ExcelFile(file_path)
            df_eq = pd.read_excel(xls, 'Equity transactions report', skiprows=6)
            df_fno = pd.read_excel(xls, 'FNO transactions report', skiprows=6)
            
            def process_transactions(df, category):
                trades = []
                df['Execution Date'] = pd.to_datetime(df['Execution Date'])
                df = df.sort_values(by='Execution Date')
                inventory = {}
                
                for _, row in df.iterrows():
                    sym = str(row['Scrip Symbol'])
                    ttype = str(row['Type']).strip().upper()
                    qty = float(row['Quantity'])
                    price = float(row['Price'])
                    date = row['Execution Date']
                    
                    if sym not in inventory:
                        inventory[sym] = {'BUY': [], 'SELL': []}
                        
                    opposite_type = 'SELL' if ttype == 'BUY' else 'BUY'
                    
                    while qty > 0 and len(inventory[sym][opposite_type]) > 0:
                        opp_trade = inventory[sym][opposite_type][0]
                        matched_qty = min(qty, opp_trade['qty'])
                        
                        buy_price = price if ttype == 'BUY' else opp_trade['price']
                        buy_date = date if ttype == 'BUY' else opp_trade['date']
                        sell_price = price if ttype == 'SELL' else opp_trade['price']
                        sell_date = date if ttype == 'SELL' else opp_trade['date']
                        
                        buy_amount = matched_qty * buy_price
                        sell_amount = matched_qty * sell_price
                        profit = sell_amount - buy_amount
                        profit_pct = (profit / buy_amount) * 100 if buy_amount > 0 else 0
                        
                        days = (sell_date - buy_date).days if pd.notnull(sell_date) and pd.notnull(buy_date) else 0
                        
                        trade = {
                            'Category': category, 'Purpose': '', 'Instrument Type': 'CASH' if category == 'Equity' else 'FNO',
                            'Instrument': sym, 'Qty': matched_qty, 'Lot': 1,
                            'Buy Date': buy_date, 'Buy Price': buy_price, 'Buy Amount': buy_amount,
                            'Sale Date': sell_date, 'Sale Price': sell_price, 'Sale Amount': sell_amount,
                            'Profit Amount': profit, 'Profit %': profit_pct, 'Broker': 'INDMoney',
                            'Status': 'Closed', 'RISK 1:2': '', 'SL (Max)': '', 'Target': '', 'Remarks': '',
                            'Expected Profit': '', 'No Of Days Invested': days, 'P/L': 'P' if profit >= 0 else 'L',
                            'ACTION': '', 'Remarks.1': '', 'Max Accepted Loss': '', 'MTF Interest': '',
                            'MTF Amount 70%': '', 'Your Investment Amount 30%': ''
                        }
                        trades.append(trade)
                        
                        qty -= matched_qty
                        inventory[sym][opposite_type][0]['qty'] -= matched_qty
                        if inventory[sym][opposite_type][0]['qty'] == 0:
                            inventory[sym][opposite_type].pop(0)
                            
                    if qty > 0:
                        inventory[sym][ttype].append({'qty': qty, 'price': price, 'date': date})
                        
                for sym, queues in inventory.items():
                    for ttype in ['BUY', 'SELL']:
                        for opp_trade in queues[ttype]:
                            buy_price = opp_trade['price'] if ttype == 'BUY' else None
                            buy_date = opp_trade['date'] if ttype == 'BUY' else None
                            sell_price = opp_trade['price'] if ttype == 'SELL' else None
                            sell_date = opp_trade['date'] if ttype == 'SELL' else None
                            buy_amount = opp_trade['qty'] * buy_price if buy_price else None
                            sell_amount = opp_trade['qty'] * sell_price if sell_price else None
                            
                            trade = {
                                'Category': category, 'Purpose': '', 'Instrument Type': 'CASH' if category == 'Equity' else 'FNO',
                                'Instrument': sym, 'Qty': opp_trade['qty'], 'Lot': 1,
                                'Buy Date': buy_date, 'Buy Price': buy_price, 'Buy Amount': buy_amount,
                                'Sale Date': sell_date, 'Sale Price': sell_price, 'Sale Amount': sell_amount,
                                'Profit Amount': None, 'Profit %': None, 'Broker': 'INDMoney',
                                'Status': 'Open', 'RISK 1:2': '', 'SL (Max)': '', 'Target': '', 'Remarks': '',
                                'Expected Profit': '', 'No Of Days Invested': None, 'P/L': '',
                                'ACTION': '', 'Remarks.1': '', 'Max Accepted Loss': '', 'MTF Interest': '',
                                'MTF Amount 70%': '', 'Your Investment Amount 30%': ''
                            }
                            trades.append(trade)
                return trades

            eq_trades = process_transactions(df_eq, "Equity")
            fno_trades = process_transactions(df_fno, "FnO")
            all_trades = eq_trades + fno_trades
            
            result_df = pd.DataFrame(all_trades, columns=self.headers)
            result_df['S.NO'] = range(1, len(result_df) + 1)
            
            self.full_df = result_df
            self.apply_filters()
        except Exception as e:
            self.sheet.set_sheet_data([[f"Error loading data: {e}"] + [""] * (len(self.headers)-1)])
    def clear_filters(self):
        self.f_entry_from.set("")
        self.f_entry_to.set("")
        self.f_year.set("All")
        self.f_month.set("All")
        self.f_sym.set("")
        self.f_pl.set("All")
        self.f_cat.set("All")
        self.apply_filters()

    def apply_filters(self):
        if self.full_df is None or self.full_df.empty:
            return
            
        import pandas as pd
        df = self.full_df.copy()
        
        # Category Filter
        cat = self.f_cat.get()
        if cat != "All":
            df = df[df['Category'].str.contains(cat, case=False, na=False)]
            
        # P/L Filter
        pl = self.f_pl.get()
        if pl == "Profit":
            df = df[pd.to_numeric(df['Profit Amount'], errors='coerce') > 0]
        elif pl == "Loss":
            df = df[pd.to_numeric(df['Profit Amount'], errors='coerce') <= 0]
            
        # Symbol Filter
        sym = self.f_sym.get().strip().upper()
        if sym:
            df = df[df['Instrument'].str.upper().str.contains(sym, na=False)]
            
        # Date Filters
        en_from = self.f_entry_from.get().strip()
        en_to = self.f_entry_to.get().strip()
        
        if en_from or en_to:
            try:
                buy_dt = pd.to_datetime(df['Buy Date'], errors='coerce')
                if en_from: df = df[buy_dt >= pd.to_datetime(en_from)]
                if en_to: df = df[buy_dt <= pd.to_datetime(en_to)]
            except: pass
            
        # Year and Month Filters
        yr = self.f_year.get()
        if yr != "All":
            try:
                df = df[pd.to_datetime(df['Buy Date'], errors='coerce').dt.year == int(yr)]
            except: pass
            
        mo = self.f_month.get()
        if mo != "All":
            try:
                df = df[pd.to_datetime(df['Buy Date'], errors='coerce').dt.strftime('%m') == mo]
            except: pass
            
        self.render_data(df)

    def render_data(self, df):
        if df is None or df.empty:
            self.sheet.set_sheet_data([["No data matched your search criteria..."] + [""] * (len(self.headers)-1)])
            return
            
        import pandas as pd
        import math
        
        # Convert df to list of lists, handle nan
        data = []
        for _, row in df.iterrows():
            row_data = []
            for col in self.headers:
                val = row.get(col, "")
                if pd.isna(val):
                    val = ""
                elif isinstance(val, float) and col in ['Buy Price', 'Buy Amount', 'Sale Price', 'Sale Amount', 'Profit Amount', 'Expected Profit', 'Max Accepted Loss', 'MTF Amount 70%', 'Your Investment Amount 30%', 'MTF Interest']:
                    val = round(val, 2)
                elif isinstance(val, pd.Timestamp):
                    val = val.strftime('%Y-%m-%d')
                row_data.append(str(val))
            data.append(row_data)
            
        self.sheet.set_sheet_data(data)
        
        # Add basic highlighting for Profit Amount (Column index 13)
        green = []
        red = []
        for r, d in enumerate(data):
            try:
                profit = float(d[13])
                if profit > 0:
                    green.append((r, 13))
                elif profit < 0:
                    red.append((r, 13))
            except:
                pass
                
        if green: self.sheet.highlight_cells(cells=green, bg=None, fg="#00E676")
        if red: self.sheet.highlight_cells(cells=red, bg=None, fg="#FF1744")


if __name__ == "__main__":
    app = App()
    app.mainloop()
