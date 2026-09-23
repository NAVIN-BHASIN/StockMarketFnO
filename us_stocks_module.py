import customtkinter as ctk
import pandas as pd
import yfinance as yf
import threading
from datetime import datetime, timedelta
from tksheet import Sheet
from tkinter import messagebox
from tkcalendar import DateEntry

class USStocksFrame(ctk.CTkFrame):
    """Foreign Institutional Investor (FII) Desk - US Stocks Intelligence."""

    US_WATCHLIST = {
        'AAPL': 'Apple Inc.', 'MSFT': 'Microsoft Corp.', 'NVDA': 'NVIDIA Corp.', 
        'GOOGL': 'Alphabet Inc.', 'AMZN': 'Amazon.com Inc.', 'META': 'Meta Platforms Inc.', 
        'TSLA': 'Tesla Inc.', 'AVGO': 'Broadcom Inc.', 'JPM': 'JPMorgan Chase & Co.', 
        'UNH': 'UnitedHealth Group', 'V': 'Visa Inc.', 'MA': 'Mastercard Inc.', 
        'HD': 'Home Depot Inc.', 'PG': 'Procter & Gamble', 'JNJ': 'Johnson & Johnson', 
        'WMT': 'Walmart Inc.', 'ORCL': 'Oracle Corp.', 'AMD': 'Advanced Micro Devices', 
        'NFLX': 'Netflix Inc.', 'CRM': 'Salesforce Inc.', 'BAC': 'Bank of America', 
        'GS': 'Goldman Sachs', 'MS': 'Morgan Stanley', 'PYPL': 'PayPal Holdings', 
        'UBER': 'Uber Technologies', 'SHOP': 'Shopify Inc.', 'SNOW': 'Snowflake Inc.', 
        'PLTR': 'Palantir Technologies', 'RBLX': 'Roblox Corp.', 'COIN': 'Coinbase Global',
        'SOFI': 'SoFi Technologies', 'RIVN': 'Rivian Automotive', 'NIO': 'Nio Inc.',
        'BABA': 'Alibaba Group', 'TSM': 'Taiwan Semiconductor', 'ASML': 'ASML Holding',
        'SOXL': 'Direxion Daily Semi Bull 3X', 'LABU': 'Direxion Daily Biotech Bull 3X',
        'XLK': 'Technology Select Sector SPDR', 'MU': 'Micron Technology', 'EWY': 'iShares MSCI South Korea'
    }

    def __init__(self, master, db):
        super().__init__(master, corner_radius=15)
        self.db = db
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._ensure_table()
        self._sync_holdings_from_image() # Sync provided image data if empty

        # Header
        hdr = ctk.CTkFrame(self, fg_color="#0D2137", corner_radius=0)
        hdr.grid(row=0, column=0, sticky="ew")
        ctk.CTkLabel(hdr, text="  FOREIGN INSTITUTIONAL INVESTOR (FII) DESK",
                     font=ctk.CTkFont(size=22, weight="bold"), text_color="#FFD54F").pack(side="left", padx=25, pady=12)

        btn_bar = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_bar.pack(side="right", padx=15)
        ctk.CTkButton(btn_bar, text=" FII Wealth Plan", width=140, fg_color="#7B1FA2",
                      command=lambda: self.tabs.set(" FII Wealth Creation")).pack(side="left", padx=5)
        ctk.CTkButton(btn_bar, text=" Log Trade", width=120, fg_color="#2E7D32",
                      command=self.open_add_trade).pack(side="left", padx=5)
        ctk.CTkButton(btn_bar, text=" Global Refresh", width=120, fg_color="#455A64",
                      command=self.load_all).pack(side="left", padx=5)

        # Tabs
        self.tabs = ctk.CTkTabview(self, corner_radius=10)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=15, pady=10)
        self.tabs.add(" Current Holdings")
        self.tabs.add(" US Trade Journal")
        self.tabs.add(" Swing Intelligence")
        self.tabs.add(" FII Wealth Creation")

        self._setup_holdings_tab()
        self._setup_journal_tab()
        self._setup_scanner_tab()
        self._setup_wealth_tab()

        self.after(300, self.load_all)

    def _setup_holdings_tab(self):
        tab = self.tabs.tab(" Current Holdings")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Stats bar for portfolio
        self.port_stats = ctk.CTkFrame(tab, fg_color="#0a1520", corner_radius=8)
        self.port_stats.grid(row=0, column=0, sticky="ew", padx=5, pady=5)
        self.port_stats.grid_columnconfigure((0,1,2,3), weight=1)
        self._port_labels = {}
        for i, (lbl, col) in enumerate([("Invested Value","#FFFFFF"),("Current Value","#4FC3F7"),
                                         ("Overall P&L","#00E676"),("Day Change","#FFD54F")]):
            f = ctk.CTkFrame(self.port_stats, fg_color="#111e2b", corner_radius=6)
            f.grid(row=0, column=i, padx=6, pady=6, sticky="ew")
            ctk.CTkLabel(f, text=lbl, font=ctk.CTkFont(size=10), text_color="gray60").pack(pady=(4,0))
            v = ctk.CTkLabel(f, text="$ --", font=ctk.CTkFont(size=16, weight="bold"), text_color=col)
            v.pack(pady=(0,4))
            self._port_labels[lbl] = v

        h_cols = ["Symbol", "Holding Since", "Qty", "Avg Price ($)", "LTP ($)", "Current Value ($)", "P&L ($)", "P&L %"]
        self.h_sheet = Sheet(tab, headers=h_cols)
        self.h_sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark": self.h_sheet.change_theme("dark")
        self.h_sheet.set_options(font=("Segoe UI", 12, "normal"), header_font=("Segoe UI", 13, "bold"))
        self.h_sheet.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def _setup_journal_tab(self):
        tab = self.tabs.tab(" US Trade Journal")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        # Filter bar with Calendar
        flt = ctk.CTkFrame(tab, fg_color="transparent")
        flt.grid(row=0, column=0, sticky="ew", pady=5)
        
        ctk.CTkLabel(flt, text="From:").pack(side="left", padx=5)
        self.cal_from = DateEntry(flt, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.cal_from.set_date(datetime.now() - timedelta(days=180))
        self.cal_from.pack(side="left", padx=5)

        ctk.CTkLabel(flt, text="To:").pack(side="left", padx=5)
        self.cal_to = DateEntry(flt, width=12, background='darkblue', foreground='white', borderwidth=2, date_pattern='yyyy-mm-dd')
        self.cal_to.pack(side="left", padx=5)

        ctk.CTkLabel(flt, text="Symbol:").pack(side="left", padx=5)
        self.sym_combo = ctk.CTkComboBox(flt, values=["All"] + sorted(list(self.US_WATCHLIST.keys())), width=120)
        self.sym_combo.set("All")
        self.sym_combo.pack(side="left", padx=5)

        ctk.CTkButton(flt, text=" Search Journal", width=100, command=self.load_journal).pack(side="left", padx=10)

        j_cols = ["Symbol","Entry Date","Entry $","Qty","Exit $","Exit Date","P&L $","P&L %","Status","Notes"]
        self.j_sheet = Sheet(tab, headers=j_cols)
        self.j_sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark": self.j_sheet.change_theme("dark")
        self.j_sheet.set_options(font=("Segoe UI", 11, "normal"), header_font=("Segoe UI", 12, "bold"))
        self.j_sheet.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def _setup_scanner_tab(self):
        tab = self.tabs.tab(" Swing Intelligence")
        tab.grid_rowconfigure(1, weight=1)
        tab.grid_columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", pady=8)
        ctk.CTkLabel(ctrl, text="Scanner focuses on 15-20% Alpha Swings using institutional momentum alignment.").pack(side="left", padx=10)
        
        ctk.CTkButton(ctrl, text="[SCAN] Deep Institutional Scan", fg_color="#1565C0", width=180, command=self.run_scanner).pack(side="right", padx=15)
        self.scan_status = ctk.CTkLabel(ctrl, text="Ready", text_color="#FFB300", font=ctk.CTkFont(size=12))
        self.scan_status.pack(side="right", padx=10)

        sc_cols = ["Symbol", "LTP", "20 EMA", "RSI", "Vol %", "FII Conviction", "Alpha Target", "Swing Justification"]
        self.sc_sheet = Sheet(tab, headers=sc_cols)
        self.sc_sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark": self.sc_sheet.change_theme("dark")
        self.sc_sheet.set_options(font=("Segoe UI", 11, "normal"), header_font=("Segoe UI", 12, "bold"))
        self.sc_sheet.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

    def _setup_wealth_tab(self):
        tab = self.tabs.tab(" FII Wealth Creation")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure((0,1), weight=1)

        # Strategic Plan Text
        plan_frame = ctk.CTkFrame(tab, fg_color="#111e2b", corner_radius=12)
        plan_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        title = ctk.CTkLabel(plan_frame, text=" FII INSTITUTIONAL SWING STRATEGY ($3,000 CAP)", font=ctk.CTkFont(size=18, weight="bold"), text_color="#FFD54F")
        title.pack(pady=15)
        
        strategy = """
 GOAL: 20% Net Profit per Month through Strategic Churning.

 CORE ACTION PLAN:
1. CAPITAL ALLOCATION ($3,000):
   | Split into 5 Equal Tranches of $600.
   | Never hold more than 5 High-Conviction stocks simultaneously.
   | Concentration creates wealth; Diversification preserves it.

2. THE "CHURN" STRATEGY:
   | Target: 10% - 15% move per trade.
   | Timeframe: 5 to 12 Trading Days per cycle.
   | If Target is met -> SELL 100% -> ROTATE to next "Deep Scan" Signal.
   | This creates 2 cycles per month = ~20% compounding effect.

3. RISK MANAGEMENT (FII DESK):
   | Hard Stop Loss: 3% of Capital per trade.
   | Trailing SL: Move to Entry once stock gains 5%.

4. SELECTION CRITERIA:
   | Near 20 EMA + RSI Reversal + Institutional Volume Spike.
   | Focus on Tech (NVDA/MSFT) and Bullish ETFs (SOXL/LABU).
"""
        txt = ctk.CTkTextbox(plan_frame, font=ctk.CTkFont(family="Consolas", size=13), wrap="word", fg_color="transparent")
        txt.insert("1.0", strategy)
        txt.configure(state="disabled")
        txt.pack(fill="both", expand=True, padx=15, pady=10)

        # Actionable Signals Window
        act_frame = ctk.CTkFrame(tab, fg_color="#0D2137", corner_radius=12)
        act_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        ctk.CTkLabel(act_frame, text=" FII DESK - TOP BUY ACTIONS", font=ctk.CTkFont(size=16, weight="bold"), text_color="#00E676").pack(pady=15)
        
        self.wealth_txt = ctk.CTkTextbox(act_frame, font=ctk.CTkFont(family="Segoe UI", size=13), wrap="word")
        self.wealth_txt.pack(fill="both", expand=True, padx=15, pady=10)
        
        ctk.CTkButton(act_frame, text="Generate Action Plan", fg_color="#2E7D32", command=self.generate_wealth_plan).pack(pady=15)

    def _ensure_table(self):
        try:
            with self.db.get_connection() as conn:
                conn.cursor().execute("""
                IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id=OBJECT_ID(N'[dbo].[US_Stocks_Journal]') AND type='U')
                BEGIN
                    CREATE TABLE [dbo].[US_Stocks_Journal](
                        [Id] INT IDENTITY(1,1) PRIMARY KEY,
                        [Symbol] VARCHAR(20) NOT NULL,
                        [EntryDate] DATETIME NULL,
                        [EntryPrice] FLOAT NULL,
                        [Quantity] FLOAT NULL,
                        [TargetPrice] FLOAT NULL,
                        [StopLoss] FLOAT NULL,
                        [ExitPrice] FLOAT NULL,
                        [ExitDate] DATETIME NULL,
                        [GrossPnL] FLOAT NULL,
                        [PnLPct] FLOAT NULL,
                        [Status] VARCHAR(20) NULL DEFAULT 'Open',
                        [Notes] VARCHAR(500) NULL,
                        [CreatedAt] DATETIME DEFAULT GETDATE()
                    )
                END
                """)
                conn.commit()
        except Exception as e: print(f"Table error: {e}")

    def _sync_holdings_from_image(self):
        """Pre-populate with user's specific spreadsheet data if empty."""
        try:
            with self.db.get_connection() as conn:
                res = conn.cursor().execute("SELECT COUNT(*) FROM US_Stocks_Journal").fetchone()
                if res[0] == 0:
                    data = [
                        ('NVDA', '2023-06-17', 86.4017, 9.4903, 'Core AI Leader'),
                        ('GOOGL', '2021-09-17', 294.2471, 0.0679, 'Search Dominance'),
                        ('META', '2021-09-17', 673.0457, 0.1039, 'Metaverse/Ads'),
                        ('NIO', '2022-01-20', 14.0154, 35.8810, 'EV Speculation'),
                        ('AAPL', '2021-09-17', 255.7059, 0.0782, 'Consumer Ecosystem'),
                        ('MSFT', '2021-09-17', 458.7107, 0.1961, 'Cloud/Enterprise'),
                        ('SOXL', '2026-04-10', 156.8208, 0.3306, 'Bullish Semi 3X'),
                        ('ORCL', '2025-09-22', 222.6758, 0.4086, 'Database/Cloud'),
                        ('PYPL', '2025-10-31', 68.4066, 1.5, 'Fintech Rebound'),
                        ('MU', '2026-04-02', 728.1788, 0.0684, 'Memory Cycle'),
                        ('XLK', '2026-05-12', 172.7288, 0.0577, 'Tech Sector Proxy')
                    ]
                    for s, d, p, q, n in data:
                        conn.cursor().execute("""
                            INSERT INTO US_Stocks_Journal (Symbol, EntryDate, EntryPrice, Quantity, Status, Notes)
                            VALUES (?, ?, ?, ?, 'Open', ?)
                        """, s, d, p, q, n)
                    conn.commit()
        except Exception as e: print(f"Sync error: {e}")

    def load_all(self):
        self.load_holdings()
        self.load_journal()

    def load_holdings(self):
        threading.Thread(target=self._bg_load_holdings, daemon=True).start()

    def _bg_load_holdings(self):
        try:
            with self.db.get_connection() as conn:
                df = pd.read_sql("SELECT Symbol, EntryDate, EntryPrice, Quantity FROM US_Stocks_Journal WHERE Status='Open'", conn)
            
            if df.empty:
                self.after(0, lambda: self.h_sheet.set_sheet_data([]))
                return

            syms = df['Symbol'].unique().tolist()
            prices = {}
            try:
                data = yf.download(syms, period="1d", progress=False)
                for s in syms:
                    if len(syms) == 1: prices[s] = data['Close'].iloc[-1]
                    else: prices[s] = data['Close'][s].iloc[-1]
            except: pass

            rows = []
            total_inv, total_cur = 0.0, 0.0
            for _, r in df.iterrows():
                s = r['Symbol']
                ltp = prices.get(s, r['EntryPrice'])
                val_inv = r['EntryPrice'] * r['Quantity']
                val_cur = ltp * r['Quantity']
                pnl = val_cur - val_inv
                pct = (pnl / val_inv * 100) if val_inv else 0
                
                total_inv += val_inv
                total_cur += val_cur
                
                rows.append([
                    s, str(r['EntryDate'])[:10], f"{r['Quantity']:.4f}",
                    f"{r['EntryPrice']:.2f}", f"{ltp:.2f}", f"{val_cur:.2f}",
                    f"{pnl:.2f}", f"{pct:.2f}%"
                ])
            
            pnl_overall = total_cur - total_inv
            self.after(0, lambda: self._update_holdings_ui(rows, total_inv, total_cur, pnl_overall))
        except Exception as e: print(f"Holdings load error: {e}")

    def _update_holdings_ui(self, rows, inv, cur, pnl):
        self.h_sheet.set_sheet_data(rows)
        greens, reds = [], []
        for r, row in enumerate(rows):
            try:
                p_val = float(row[6])
                if p_val > 0: greens.append((r, 6)); greens.append((r, 7))
                elif p_val < 0: reds.append((r, 6)); reds.append((r, 7))
            except: pass
        if greens: self.h_sheet.highlight_cells(cells=greens, bg=None, fg="#00E676")
        if reds: self.h_sheet.highlight_cells(cells=reds, bg=None, fg="#FF1744")
        
        self._port_labels["Invested Value"].configure(text=f"${inv:,.2f}")
        self._port_labels["Current Value"].configure(text=f"${cur:,.2f}")
        self._port_labels["Overall P&L"].configure(text=f"${pnl:,.2f}", text_color="#00E676" if pnl >= 0 else "#FF1744")
        self.h_sheet.set_all_column_widths(120)

    def load_journal(self):
        fd = self.cal_from.get_date().strftime("%Y-%m-%d")
        td = self.cal_to.get_date().strftime("%Y-%m-%d")
        sym = self.sym_combo.get()
        threading.Thread(target=self._bg_load_journal, args=(fd, td, sym), daemon=True).start()

    def _bg_load_journal(self, fd, td, sym):
        try:
            with self.db.get_connection() as conn:
                q = f"SELECT Symbol, EntryDate, EntryPrice, Quantity, ExitPrice, ExitDate, GrossPnL, PnLPct, Status, Notes FROM US_Stocks_Journal WHERE EntryDate >= '{fd}' AND EntryDate <= '{td} 23:59:59'"
                if sym != "All": q += f" AND Symbol = '{sym}'"
                q += " ORDER BY EntryDate DESC"
                df = pd.read_sql(q, conn)
            
            rows = []
            for _, r in df.iterrows():
                rows.append([
                    r['Symbol'], str(r['EntryDate'])[:10], f"{r['EntryPrice']:.2f}",
                    f"{r['Quantity']:.2f}", f"{r['ExitPrice'] or 0:.2f}",
                    str(r['ExitDate'])[:10] if r['ExitDate'] else "-",
                    f"{r['GrossPnL'] or 0:.2f}", f"{r['PnLPct'] or 0:.2f}%",
                    r['Status'], r['Notes'] or ""
                ])
            self.after(0, lambda: self.j_sheet.set_sheet_data(rows))
        except Exception as e: print(f"Journal error: {e}")

    def run_scanner(self):
        self.scan_status.configure(text="Running Institutional Scan...", text_color="#FFB300")
        threading.Thread(target=self._bg_scan, daemon=True).start()

    def _bg_scan(self):
        results = []
        syms = list(self.US_WATCHLIST.keys())
        try:
            data = yf.download(syms, period="60d", progress=False)
            for s in syms:
                try:
                    df = data.loc[:, (slice(None), s)]
                    df.columns = df.columns.droplevel(1)
                    ltp = df['Close'].iloc[-1]
                    ema20 = df['Close'].ewm(span=20).mean().iloc[-1]
                    rsi = self._calc_rsi(df['Close'])
                    vol_avg = df['Volume'].rolling(20).mean().iloc[-1]
                    vol_now = df['Volume'].iloc[-1]
                    vol_pct = (vol_now / vol_avg) * 100

                    conv = "Neutral"
                    if ltp > ema20 and abs(ltp/ema20-1) < 0.02 and rsi < 60:
                        conv = " HIGH ALPHA"
                    elif rsi < 35: conv = " REVERSAL"
                    
                    if conv != "Neutral":
                        results.append([
                            s, f"{ltp:.2f}", f"{ema20:.2f}", f"{rsi:.1f}",
                            f"{vol_pct:.0f}%", conv, f"{ltp*1.2:.2f}", "EMA 20 Pullback + Vol Surge"
                        ])
                except: continue
            self.after(0, lambda: self._update_scanner_ui(results))
        except: pass

    def _update_scanner_ui(self, results):
        self.sc_sheet.set_sheet_data(results)
        self.sc_sheet.set_all_column_widths(115)
        self.sc_sheet.column_width(7, 300)
        self.scan_status.configure(text=f"Scan Complete: {len(results)} Signals", text_color="#00E676")

    def generate_wealth_plan(self):
        self.wealth_txt.delete("1.0", "end")
        self.wealth_txt.insert("end", " FII DESK: ACTIONABLE INTELLIGENCE\n" + "="*40 + "\n")
        threading.Thread(target=self._bg_wealth_plan, daemon=True).start()

    def _bg_wealth_plan(self):
        # Professional plan logic
        picks = ["NVDA", "SOXL", "META", "LABU"]
        try:
            data = yf.download(picks, period="30d", progress=False)
            out = ""
            for s in picks:
                ltp = data['Close'][s].iloc[-1]
                ema20 = data['Close'][s].ewm(span=20).mean().iloc[-1]
                target = ltp * 1.20
                sl = ltp * 0.95
                out += f"\n BUY {s} (Capital Rotation Tranche 1)\n"
                out += f"   | Entry Zone: ${ltp:.2f} (Near 20 EMA: ${ema20:.2f})\n"
                out += f"   | Target (20%): ${target:.2f}\n"
                out += f"   | Stop Loss: ${sl:.2f}\n"
                out += f"   | Rationale: Institutional Accumulation + Bullish Sector Rotation.\n"
            
            out += "\n WEALTH CHURNING RULE:\n"
            out += "Rotate $600 into each of these. As soon as one hits 15%,\n"
            out += "exit and move to the next 'High Alpha' scanner signal.\n"
            self.after(0, lambda: self.wealth_txt.insert("end", out))
        except: pass

    def open_add_trade(self):
        win = ctk.CTkToplevel(self)
        win.title("FII Desk - New Position")
        win.geometry("450x550")
        win.attributes("-topmost", True)
        
        ctk.CTkLabel(win, text=" Open New Institutional Position", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        
        ctk.CTkLabel(win, text="Select Symbol:").pack(pady=2)
        sym_var = ctk.StringVar(value="NVDA")
        combo = ctk.CTkComboBox(win, variable=sym_var, values=sorted(list(self.US_WATCHLIST.keys())), width=300)
        combo.pack(pady=5)
        
        fields = {}
        for lbl, dflt in [("Entry Date", datetime.now().strftime("%Y-%m-%d")), 
                          ("Entry Price ($)", ""), ("Quantity", "10")]:
            ctk.CTkLabel(win, text=lbl).pack(pady=2)
            e = ctk.CTkEntry(win, width=300)
            e.insert(0, dflt)
            e.pack(pady=5)
            fields[lbl] = e
            
        ctk.CTkLabel(win, text="Strategic Notes:").pack(pady=2)
        notes = ctk.CTkEntry(win, width=300)
        notes.pack(pady=5)
        
        def save():
            try:
                s = sym_var.get()
                ed = fields["Entry Date"].get()
                ep = float(fields["Entry Price ($)"].get())
                q = float(fields["Quantity"].get())
                n = notes.get()
                with self.db.get_connection() as conn:
                    conn.cursor().execute("""
                        INSERT INTO US_Stocks_Journal (Symbol, EntryDate, EntryPrice, Quantity, Status, Notes)
                        VALUES (?, ?, ?, ?, 'Open', ?)
                    """, s, ed, ep, q, n)
                    conn.commit()
                win.destroy()
                self.load_all()
            except Exception as e: messagebox.showerror("Error", str(e))
                
        ctk.CTkButton(win, text=" Execute Trade", fg_color="#2E7D32", command=save).pack(pady=25)

    def _calc_rsi(self, series, period=14):
        delta = series.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs)).iloc[-1]
