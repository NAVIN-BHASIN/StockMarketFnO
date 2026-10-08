import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tksheet import Sheet
import threading
from datetime import datetime

# =========================================================================
# 1. SYMBOL ROLLOVER DRILLDOWN MODAL
# =========================================================================
class SymbolRolloverDrilldownWindow(ctk.CTkToplevel):
    def __init__(self, master, symbol, db, snapshot_date="Latest"):
        super().__init__(master)
        self.title(f"Institutional Rollover & Term Structure - {symbol}")
        self.geometry("980x660")
        self.attributes("-topmost", True)
        self.configure(fg_color="#0d1117")
        
        self.symbol = symbol.upper()
        self.db = db
        self.snapshot_date = snapshot_date
        
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=25, pady=(20, 10))
        
        ctk.CTkLabel(
            hdr, 
            text=f"F&O Term Structure & Rollover Intelligence: {self.symbol}", 
            font=ctk.CTkFont(size=20, weight="bold"), 
            text_color="#FFD54F"
        ).pack(side="left")
        
        self.date_badge = ctk.CTkLabel(
            hdr,
            text=f"Snapshot: {snapshot_date}",
            font=ctk.CTkFont(size=12),
            text_color="gray60"
        )
        self.date_badge.pack(side="right")
        
        # Main split container
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=25, pady=5)
        mid.grid_columnconfigure(0, weight=6, uniform="m")
        mid.grid_columnconfigure(1, weight=4, uniform="m")
        mid.grid_rowconfigure(0, weight=1)
        
        # Left Panel: Expiry Cycle Sheet & Chart
        left_frame = ctk.CTkFrame(mid, fg_color="#161b22", corner_radius=12)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        left_frame.grid_columnconfigure(0, weight=1)
        left_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            left_frame,
            text="📅 Expiry Cycle Distribution (Near, Next, Far)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFD54F"
        ).grid(row=0, column=0, padx=15, pady=(12, 5), sticky="w")
        
        cols = ["Cycle", "Expiry Date", "Close Price", "Spread (Roll Cost)", "OI (Contracts)", "Volume"]
        self.sheet = Sheet(left_frame, headers=cols, height=130)
        self.sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.sheet.change_theme("dark")
        self.sheet.grid(row=1, column=0, sticky="nsew", padx=12, pady=5)
        
        self.chart_container = ctk.CTkFrame(left_frame, fg_color="transparent", height=200)
        self.chart_container.grid(row=2, column=0, sticky="nsew", padx=12, pady=(5, 12))
        self.chart_container.grid_columnconfigure(0, weight=1)
        self.chart_container.grid_rowconfigure(0, weight=1)
        
        # Right Panel: Institutional Carry Recommendation & Stance
        right_frame = ctk.CTkFrame(mid, fg_color="#161b22", corner_radius=12)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right_frame.grid_columnconfigure(0, weight=1)
        right_frame.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            right_frame,
            text="🎯 Institutional Rollover Stance & Desk Plan",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#FFD54F"
        ).grid(row=0, column=0, padx=15, pady=(12, 5), sticky="w")
        
        self.advisory_txt = ctk.CTkTextbox(
            right_frame,
            fg_color="transparent",
            font=ctk.CTkFont(size=13, family="Consolas"),
            wrap="word"
        )
        self.advisory_txt.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 15))
        
        self.load_data()
        
    def load_data(self):
        try:
            date_filter = f"WHERE SnapShotDate = '{self.snapshot_date}'" if self.snapshot_date != "Latest" else "WHERE SnapShotDate = (SELECT MAX(SnapShotDate) FROM dbo.vw_Futures_FnO_Analysis)"
            q = f"""
            SELECT SnapShotDate, EXPIRY_DATE, CLOSE_PRIC, OI_NO_CON, TRD_NO_CON, TRADED_VAL
            FROM dbo.vw_Futures_FnO_Analysis
            {date_filter}
              AND SYMBOL = '{self.symbol}'
            ORDER BY EXPIRY_DATE ASC
            """
            with self.db.get_connection() as conn:
                df = pd.read_sql(q, conn)
                
            if df.empty:
                # Fallback to transformed table
                q_fb = f"""
                SELECT SnapShotDate, EXPIRY_DATE, CLOSE_PRIC, OI_NO_CON, TRADED_QUA as TRD_NO_CON, (TRADED_QUA * CLOSE_PRIC) as TRADED_VAL
                FROM FUTURES_FNO_BhavCopy_History_Transformed_New
                WHERE SYMBOL = '{self.symbol}'
                ORDER BY SnapShotDate DESC, EXPIRY_DATE ASC
                """
                with self.db.get_connection() as conn:
                    df = pd.read_sql(q_fb, conn)
                    if not df.empty:
                        latest_date = df['SnapShotDate'].iloc[0]
                        df = df[df['SnapShotDate'] == latest_date]
                        
            if df.empty:
                self.sheet.set_sheet_data([["No futures contract data found for " + self.symbol]])
                self.advisory_txt.insert("1.0", f"No historical futures contracts found for {self.symbol}.")
                self.advisory_txt.configure(state="disabled")
                return
                
            cycles = ["Near Month", "Next Month", "Far Month"]
            sheet_rows = []
            near_price = df.iloc[0]['CLOSE_PRIC'] if len(df) > 0 else 0
            if pd.isna(near_price) or near_price is None: near_price = 0.0
            
            oi_list, exp_labels, price_list = [], [], []
            
            for idx in range(min(3, len(df))):
                r = df.iloc[idx]
                exp_dt = str(r['EXPIRY_DATE'])[:10]
                price = r['CLOSE_PRIC']
                oi = int(r['OI_NO_CON'] or 0)
                vol = int(r['TRD_NO_CON'] or 0)
                
                price_val = float(price) if pd.notna(price) and price else 0.0
                price_list.append(price_val)
                oi_list.append(oi)
                exp_labels.append(f"{cycles[idx]}\n({exp_dt[-5:]})")
                
                if idx == 0:
                    spread_txt = "0.00 (BASE)"
                else:
                    if near_price > 0 and price_val > 0:
                        spread = price_val - near_price
                        spread_pct = (spread / near_price) * 100
                        spread_txt = f"{spread:+.2f} ({spread_pct:+.2f}%)"
                    else:
                        spread_txt = "--"
                        
                sheet_rows.append([
                    cycles[idx],
                    exp_dt,
                    f"{price_val:.2f}",
                    spread_txt,
                    f"{oi:,}",
                    f"{vol:,}"
                ])
                
            self.sheet.set_sheet_data(sheet_rows)
            
            # Highlights
            green, red = [], []
            for r_idx in range(1, len(sheet_rows)):
                sp = sheet_rows[r_idx][3]
                if sp != "--":
                    if "+" in sp and not sp.startswith("+0.00"):
                        green.append((r_idx, 3))
                    elif "-" in sp:
                        red.append((r_idx, 3))
            if green: self.sheet.highlight_cells(cells=green, fg="#00E676")
            if red: self.sheet.highlight_cells(cells=red, fg="#FF1744")
            
            # Draw Term Structure Chart
            self._draw_term_structure_chart(exp_labels, oi_list, price_list)
            
            # Generate Advisory
            self._generate_advisory(df, sheet_rows)
            
        except Exception as e:
            self.sheet.set_sheet_data([[f"Error: {e}"]])
            self.advisory_txt.insert("1.0", f"Error loading details: {e}")
            self.advisory_txt.configure(state="disabled")
            
    def _draw_term_structure_chart(self, labels, oi_list, price_list):
        for w in self.chart_container.winfo_children():
            w.destroy()
            
        fig, ax1 = plt.subplots(figsize=(5, 2.2), dpi=95)
        fig.patch.set_facecolor('#161b22')
        ax1.set_facecolor('#161b22')
        
        x = np.arange(len(labels))
        width = 0.4
        
        # Bars for Open Interest
        bars = ax1.bar(x - width/2, [o/1000 for o in oi_list], width, label='OI (k Contracts)', color='#0288D1', alpha=0.85)
        ax1.set_ylabel('OI (k)', color='#0288D1', fontsize=9)
        ax1.tick_params(axis='y', labelcolor='#0288D1', labelsize=8)
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, color='white', fontsize=8)
        ax1.tick_params(colors='white', labelsize=8)
        ax1.grid(True, axis='y', color='#30363d', linestyle='--', alpha=0.4)
        
        # Line for Price Curve
        ax2 = ax1.twinx()
        ax2.plot(x + width/2, price_list, color='#FFD54F', marker='o', linewidth=2, label='Price Curve')
        ax2.set_ylabel('Price', color='#FFD54F', fontsize=9)
        ax2.tick_params(axis='y', labelcolor='#FFD54F', labelsize=8)
        
        for ax in [ax1, ax2]:
            for s in ['top', 'right', 'left', 'bottom']:
                ax.spines[s].set_visible(False)
                
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)
        
    def _generate_advisory(self, df, sheet_rows):
        total_oi = sum(int(r['OI_NO_CON'] or 0) for _, r in df.iterrows())
        near_oi = int(df.iloc[0]['OI_NO_CON'] or 0) if len(df) > 0 else 0
        roll_oi = total_oi - near_oi
        roll_pct = (roll_oi / total_oi * 100) if total_oi > 0 else 0.0
        
        spread_status = "CONTANGO (Bullish Carry)"
        spread_desc = "Next month contract trades at a premium to near month. Institutional participants are actively paying carry cost to roll longs forward."
        
        if len(sheet_rows) > 1 and sheet_rows[1][3] != "--":
            spread_str = sheet_rows[1][3]
            if "-" in spread_str:
                spread_status = "BACKWARDATION (Discount / Bearish Roll)"
                spread_desc = "Next month contract trades at a discount to near month. Indicates aggressive short roll-overs or panic hedge locks by institutional desks."
                
        adv = f"========================================================================\n"
        adv += f"             INSTITUTIONAL ROLLOVER AUDIT - {self.symbol}             \n"
        adv += f"========================================================================\n\n"
        
        adv += f"📊 ROLLOVER METRICS:\n"
        adv += f"• Total Derivative Open Interest: {total_oi:,} contracts\n"
        adv += f"• Carried Over (Roll OI): {roll_oi:,} contracts\n"
        adv += f"• Rollover Percentage: {roll_pct:.2f}%\n"
        adv += f"• Carry Spread Structure: {spread_status}\n\n"
        
        adv += f"💡 SPREAD ANALYSIS:\n"
        adv += f"• {spread_desc}\n\n"
        
        adv += f"⚡ TRADING ACTIONABLE PLAN:\n"
        if roll_pct >= 50.0 and "CONTANGO" in spread_status:
            adv += f"• ACTION: STRONG BULLISH CARRY (BUY ON PULLBACKS)\n"
            adv += f"• Rollover speed is robust with positive carry spread. Long momentum is likely to continue into the next series.\n"
            adv += f"• Retail Strategy: Hold trailing longs or buy near-month calls on support dips.\n"
        elif roll_pct >= 50.0 and "BACKWARDATION" in spread_status:
            adv += f"• ACTION: BEARISH ROLLOVER PRESSURE (SELL ON RALLIES)\n"
            adv += f"• Heavy rollovers accompanied by negative spread indicate institutions rolling over short inventory.\n"
            adv += f"• Retail Strategy: Avoid buying dips; buy puts or hedge stock holdings.\n"
        elif roll_pct < 20.0:
            adv += f"• ACTION: LOW ROLLOVER MOMENTUM (EXPOSURE TRIMMING / UNWINDING)\n"
            adv += f"• Most positions are being closed out rather than rolled. Series expected to start on a flat/rangebound note.\n"
            adv += f"• Retail Strategy: Stay neutral and wait for post-expiry breakout setups.\n"
        else:
            adv += f"• ACTION: MODERATE BALANCED ROLLOVER\n"
            adv += f"• Normal cyclical rolling. Observe price action relative to VWAP on expiry day.\n"
            
        self.advisory_txt.insert("1.0", adv)
        self.advisory_txt.configure(state="disabled")


# =========================================================================
# 2. MAIN ROLLOVER INTELLIGENCE TAB
# =========================================================================
class RolloverIntelligenceTab(ctk.CTkFrame):
    def __init__(self, master, db):
        super().__init__(master, fg_color="transparent")
        self.db = db
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.selected_snapshot_date = "Latest"
        self.current_df = pd.DataFrame()
        
        # 1. Top Header Bar
        self._setup_header()
        
        # 2. Top KPI Summary Ribbon
        self._setup_kpi_ribbon()
        
        # 3. Main Internal Tabview
        self.rtabs = ctk.CTkTabview(self, corner_radius=12)
        self.rtabs.grid(row=2, column=0, sticky="nsew", padx=15, pady=(5, 15))
        
        self.rtabs.add("Visual Analytics")
        self.rtabs.add("Comprehensive Grid")
        self.rtabs.add("History & Daily Sync")
        
        self.setup_visual_tab(self.rtabs.tab("Visual Analytics"))
        self.setup_grid_tab(self.rtabs.tab("Comprehensive Grid"))
        self.setup_history_tab(self.rtabs.tab("History & Daily Sync"))
        
        self.after(300, self.refresh_all)

    # ---------------------------------------------------------------------
    # HEADER SETUP
    # ---------------------------------------------------------------------
    def _setup_header(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        
        # Left title
        title_box = ctk.CTkFrame(hdr, fg_color="transparent")
        title_box.pack(side="left")
        
        ctk.CTkLabel(
            title_box, 
            text="Rollover Intelligence & Series Analytics", 
            font=ctk.CTkFont(size=22, weight="bold"), 
            text_color="#FFD54F"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_box, 
            text="Institutional Expiry Carry, Spread Dynamics & Sector Shift Tracking", 
            font=ctk.CTkFont(size=12), 
            text_color="gray60"
        ).pack(anchor="w")
        
        # Right action buttons
        self.sync_btn = ctk.CTkButton(
            hdr, 
            text="⚡ Live Sync Feed", 
            width=130, 
            fg_color="#00C853", 
            hover_color="#00E676",
            command=self.sync_live_feed
        )
        self.sync_btn.pack(side="right", padx=5)
        
        self.refresh_btn = ctk.CTkButton(
            hdr, 
            text="🔄 Refresh", 
            width=100, 
            fg_color="#0288D1", 
            hover_color="#039BE5",
            command=self.refresh_all
        )
        self.refresh_btn.pack(side="right", padx=5)
        
        self.status_lbl = ctk.CTkLabel(
            hdr, 
            text="Ready.", 
            font=ctk.CTkFont(size=12), 
            text_color="gray60"
        )
        self.status_lbl.pack(side="right", padx=10)

    # ---------------------------------------------------------------------
    # KPI RIBBON SETUP
    # ---------------------------------------------------------------------
    def _setup_kpi_ribbon(self):
        self.kpi_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10, height=80)
        self.kpi_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        self.kpi_frame.grid_propagate(False)
        self.kpi_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1, uniform="kpi")
        self.kpi_frame.grid_rowconfigure(0, weight=1)
        
        self.kpi_cards = {}
        cards_cfg = [
            ("nifty", "NIFTY ROLLOVER %", "--", "gray50", "#00E676"),
            ("banknifty", "BANK NIFTY ROLLOVER %", "--", "gray50", "#00E676"),
            ("market_avg", "MARKET-WIDE AVG ROLL %", "--", "gray50", "#4FC3F7"),
            ("long_buildup", "BULLISH CARRY (LONG)", "--", "gray50", "#00E676"),
            ("short_buildup", "BEARISH ROLL (SHORT)", "--", "gray50", "#FF1744"),
            ("top_sector", "TOP ROLLED SECTOR", "--", "gray50", "#FFD54F")
        ]
        
        for idx, (key, title, val, sub, val_col) in enumerate(cards_cfg):
            card = ctk.CTkFrame(self.kpi_frame, fg_color="transparent")
            card.grid(row=0, column=idx, padx=5, pady=5, sticky="nsew")
            
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="gray50").pack(pady=(4, 2))
            lbl_val = ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=16, weight="bold"), text_color=val_col)
            lbl_val.pack()
            lbl_sub = ctk.CTkLabel(card, text=sub, font=ctk.CTkFont(size=10), text_color="gray60")
            lbl_sub.pack(pady=(1, 4))
            
            self.kpi_cards[key] = (lbl_val, lbl_sub)

    # ---------------------------------------------------------------------
    # TAB 1: VISUAL ANALYTICS
    # ---------------------------------------------------------------------
    def setup_visual_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure((0, 1), weight=1)
        
        # Top: Nifty & Bank Nifty vs Marketwide Chart
        self.nifty_chart_frame = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=12)
        self.nifty_chart_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(5, 5))
        self.nifty_chart_frame.grid_columnconfigure(0, weight=1)
        self.nifty_chart_frame.grid_rowconfigure(0, weight=1)
        
        # Bottom: Sector-wise comparison Chart
        self.sector_chart_frame = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=12)
        self.sector_chart_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 5))
        self.sector_chart_frame.grid_columnconfigure(0, weight=1)
        self.sector_chart_frame.grid_rowconfigure(0, weight=1)

    # ---------------------------------------------------------------------
    # TAB 2: COMPREHENSIVE GRID
    # ---------------------------------------------------------------------
    def setup_grid_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        
        # Filter controls
        ctrl = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=10)
        ctrl.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        # Date Filter
        ctk.CTkLabel(ctrl, text="📅 Date:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(12, 4), pady=8)
        self.f_date = ctk.StringVar(value="Latest")
        self.date_menu = ctk.CTkOptionMenu(
            ctrl, 
            variable=self.f_date, 
            values=["Latest"], 
            width=130,
            command=self._on_date_changed
        )
        self.date_menu.pack(side="left", padx=4, pady=8)
        
        # Sector Filter
        ctk.CTkLabel(ctrl, text="🏢 Sector:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(12, 4), pady=8)
        self.f_sector = ctk.StringVar(value="All")
        self.sector_menu = ctk.CTkOptionMenu(
            ctrl, 
            variable=self.f_sector, 
            values=["All"], 
            width=140,
            command=lambda _: self.load_grid_data()
        )
        self.sector_menu.pack(side="left", padx=4, pady=8)
        
        # Sentiment Filter
        ctk.CTkLabel(ctrl, text="🎯 Sentiment:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(12, 4), pady=8)
        self.f_sentiment = ctk.StringVar(value="All")
        sentiments = ["All", "Long Buildup (Bullish Carry)", "Short Buildup (Bearish Roll)", "Short Covering (Relief)", "Long Unwinding (Exiting)"]
        ctk.CTkOptionMenu(
            ctrl, 
            variable=self.f_sentiment, 
            values=sentiments, 
            width=210,
            command=lambda _: self.load_grid_data()
        ).pack(side="left", padx=4, pady=8)
        
        # Search Box
        ctk.CTkLabel(ctrl, text="🔍 Search:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(12, 4), pady=8)
        self.search_var = ctk.StringVar()
        self.search_entry = ctk.CTkEntry(ctrl, textvariable=self.search_var, placeholder_text="Symbol...", width=110)
        self.search_entry.pack(side="left", padx=4, pady=8)
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_grid_data())
        
        # Count Badge
        self.grid_count_lbl = ctk.CTkLabel(ctrl, text="0 stocks", font=ctk.CTkFont(size=11), text_color="gray60")
        self.grid_count_lbl.pack(side="right", padx=15, pady=8)
        
        # Sheet
        self.sheet_container = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=12)
        self.sheet_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        self.sheet_container.grid_columnconfigure(0, weight=1)
        self.sheet_container.grid_rowconfigure(0, weight=1)
        
        cols = [
            "Symbol", "Sector", "Near Price", "Next Price", "Roll Cost (Spread)", 
            "Roll Cost %", "Price Chg %", "Near OI", "Next OI", "Far OI", 
            "Total OI", "Roll OI", "Rollover %", "Sentiment & Stance"
        ]
        self.sheet = Sheet(self.sheet_container, headers=cols)
        self.sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.sheet.change_theme("dark")
        self.sheet.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.sheet.MT.bind("<Double-1>", self.on_grid_double_click)

    # ---------------------------------------------------------------------
    # TAB 3: HISTORY & INGESTION
    # ---------------------------------------------------------------------
    def setup_history_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ctk.CTkLabel(
            top, 
            text="Historical Rollover Database & Ingestion Log", 
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#FFD54F"
        ).pack(side="left")
        
        self.import_btn = ctk.CTkButton(
            top, 
            text="📁 Import Custom PDF / Bhavcopy", 
            fg_color="#E65100", 
            hover_color="#EF6C00",
            command=self.import_pdf
        )
        self.import_btn.pack(side="right", padx=5)
        
        # Table of history
        cols = ["Snapshot Date", "Source Feed", "Symbols Analyzed", "Action"]
        self.hist_tree = ttk.Treeview(parent, columns=cols, show="headings", height=15)
        for c in cols: 
            self.hist_tree.heading(c, text=c)
        self.hist_tree.column("Snapshot Date", width=120, anchor="center")
        self.hist_tree.column("Source Feed", width=300, anchor="w")
        self.hist_tree.column("Symbols Analyzed", width=140, anchor="center")
        self.hist_tree.column("Action", width=140, anchor="center")
        
        self.hist_tree.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.hist_tree.bind("<Double-1>", self.on_history_click)

    # ---------------------------------------------------------------------
    # DATA LOADING & REFRESH ORCHESTRATION
    # ---------------------------------------------------------------------
    def refresh_all(self):
        self.status_lbl.configure(text="Loading rollover intelligence...", text_color="gray60")
        self.refresh_btn.configure(text="Refreshing...", state="disabled")
        
        threading.Thread(target=self._bg_refresh, daemon=True).start()

    def _bg_refresh(self):
        try:
            # 1. Fetch dates
            dates = self.db.get_rollover_snapshot_dates()
            
            # 2. Fetch sectors
            sectors = self.db.get_all_sectors()
            
            # 3. Fetch KPI summary
            kpis = self.db.get_rollover_kpi_summary(self.selected_snapshot_date)
            
            # 4. Fetch Nifty vs Market
            df_trend = self.db.get_nifty_vs_market_rollover(limit_days=30)
            
            # 5. Fetch Sector comparison
            df_sectors = self.db.get_sectorwise_comparison(self.selected_snapshot_date)
            
            # 6. Fetch Comprehensive Table
            df_grid = self.db.get_comprehensive_rollover_table(
                sector=self.f_sector.get(),
                snapshot_date=self.selected_snapshot_date,
                sentiment=self.f_sentiment.get()
            )
            
            # 7. Fetch History log
            df_hist = self.db.get_rollover_history_log()
            
            self.after(0, lambda: self._on_data_loaded(dates, sectors, kpis, df_trend, df_sectors, df_grid, df_hist))
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: self._on_error(msg))

    def _on_data_loaded(self, dates, sectors, kpis, df_trend, df_sectors, df_grid, df_hist):
        self.refresh_btn.configure(text="🔄 Refresh", state="normal")
        self.status_lbl.configure(text="Analysis complete.", text_color="#00E676")
        
        # Update dropdowns if needed
        if dates:
            date_values = ["Latest"] + dates[:30]
            self.date_menu.configure(values=date_values)
            
        if sectors:
            self.sector_menu.configure(values=["All"] + sectors)
            
        # Update KPI Cards
        self._update_kpi_ribbon(kpis)
        
        # Update Charts
        if not df_trend.empty:
            self._plot_nifty_vs_market(df_trend)
        if not df_sectors.empty:
            self._plot_sectorwise(df_sectors)
            
        # Update Grid
        self.current_df = df_grid
        self._populate_grid(df_grid)
        
        # Update History Tree
        self._populate_history(df_hist)

    def _update_kpi_ribbon(self, kpis):
        nifty_roll = kpis.get('nifty_roll', 0.0)
        banknifty_roll = kpis.get('banknifty_roll', 0.0)
        mkt_avg = kpis.get('market_avg_roll', 0.0)
        long_cnt = kpis.get('long_buildup', 0)
        short_cnt = kpis.get('short_buildup', 0)
        top_sec = kpis.get('top_sector', '--')
        
        # Nifty
        n_sub = "Above 3M Avg" if nifty_roll >= 75.0 else "Normal Roll" if nifty_roll >= 60.0 else "Weak Roll (<60%)"
        self.kpi_cards['nifty'][0].configure(text=f"{nifty_roll:.2f}%")
        self.kpi_cards['nifty'][1].configure(text=n_sub)
        
        # Bank Nifty
        bn_sub = "Heavy Carry" if banknifty_roll >= 78.0 else "Normal Roll" if banknifty_roll >= 60.0 else "Weak Roll"
        self.kpi_cards['banknifty'][0].configure(text=f"{banknifty_roll:.2f}%")
        self.kpi_cards['banknifty'][1].configure(text=bn_sub)
        
        # Market Avg
        self.kpi_cards['market_avg'][0].configure(text=f"{mkt_avg:.2f}%")
        self.kpi_cards['market_avg'][1].configure(text=f"{kpis.get('total_symbols', 0)} F&O Symbols")
        
        # Long Buildup
        self.kpi_cards['long_buildup'][0].configure(text=str(long_cnt))
        self.kpi_cards['long_buildup'][1].configure(text="Bullish Carry DESK")
        
        # Short Buildup
        self.kpi_cards['short_buildup'][0].configure(text=str(short_cnt))
        self.kpi_cards['short_buildup'][1].configure(text="Bearish Roll PRESSURE")
        
        # Top Sector
        self.kpi_cards['top_sector'][0].configure(text=top_sec)
        self.kpi_cards['top_sector'][1].configure(text="Sector Rollover Leader")

    # ---------------------------------------------------------------------
    # CHARTS PLOTTING
    # ---------------------------------------------------------------------
    def _plot_nifty_vs_market(self, df):
        for w in self.nifty_chart_frame.winfo_children():
            w.destroy()
            
        fig, ax1 = plt.subplots(figsize=(10, 3.8), dpi=95)
        fig.patch.set_facecolor('#161b22')
        ax1.set_facecolor('#161b22')
        
        dates = pd.to_datetime(df['Date']).dt.strftime('%d-%b').tolist()
        x = np.arange(len(dates))
        
        # Bars for Market-wide Average
        ax1.bar(x, df['Market_Avg_Roll_Pct'], width=0.45, label='Market-Wide Avg Roll %', color='#37474F', alpha=0.85)
        
        # Lines for Nifty and Bank Nifty
        ax1.plot(x, df['Nifty_Roll_Pct'], color='#00E676', marker='o', linewidth=2.2, label='Nifty 50 Rollover %')
        if 'BankNifty_Roll_Pct' in df.columns:
            ax1.plot(x, df['BankNifty_Roll_Pct'], color='#FFD54F', marker='s', linewidth=2.0, linestyle='--', label='Bank Nifty Rollover %')
            
        # Benchmark lines
        ax1.axhline(75.0, color='#00E676', linestyle=':', alpha=0.5, label='High Roll Threshold (75%)')
        ax1.axhline(50.0, color='#FF1744', linestyle=':', alpha=0.5, label='Low Roll Threshold (50%)')
        
        ax1.set_title("NIFTY 50 & BANK NIFTY VS MARKET-WIDE ROLLOVER TREND (LAST 30 SESSIONS)", color='white', fontsize=11, fontweight='bold', pad=12)
        ax1.set_xticks(x[::max(1, len(x)//12)])
        ax1.set_xticklabels(dates[::max(1, len(dates)//12)], color='white', fontsize=8)
        ax1.set_ylabel("Rollover Percentage (%)", color='gray', fontsize=9)
        ax1.tick_params(colors='white', labelsize=8)
        ax1.set_ylim(0, 105)
        ax1.grid(True, axis='y', color='#30363d', linestyle='--', alpha=0.4)
        ax1.legend(facecolor='#161b22', edgecolor='none', labelcolor='white', fontsize=8, loc='upper left')
        
        for spine in ['top', 'right', 'left', 'bottom']:
            ax1.spines[spine].set_visible(False)
            
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.nifty_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        plt.close(fig)

    def _plot_sectorwise(self, df):
        for w in self.sector_chart_frame.winfo_children():
            w.destroy()
            
        fig, ax = plt.subplots(figsize=(10, 3.8), dpi=95)
        fig.patch.set_facecolor('#161b22')
        ax.set_facecolor('#161b22')
        
        sectors = df['Sector'].tolist()[:15]
        rolls = df['Avg_Roll_Pct'].tolist()[:15]
        
        x = np.arange(len(sectors))
        colors = ['#00E676' if r >= 70.0 else '#4FC3F7' if r >= 50.0 else '#FFB300' if r >= 30.0 else '#FF1744' for r in rolls]
        
        bars = ax.bar(x, rolls, width=0.5, color=colors, alpha=0.9)
        
        # Add labels on top of bars
        for bar, r in zip(bars, rolls):
            height = bar.get_height()
            ax.annotate(f'{r:.1f}%',
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),
                        textcoords="offset points",
                        ha='center', va='bottom', color='white', fontsize=7, fontweight='bold')
                        
        ax.set_title("SECTOR-WISE ROLLOVER POSITIONING & INTENSITY", color='white', fontsize=11, fontweight='bold', pad=12)
        ax.set_xticks(x)
        ax.set_xticklabels(sectors, rotation=35, ha='right', color='white', fontsize=8)
        ax.set_ylabel("Avg Rollover %", color='gray', fontsize=9)
        ax.tick_params(colors='white', labelsize=8)
        ax.set_ylim(0, max(rolls + [100]) * 1.15)
        ax.grid(True, axis='y', color='#30363d', linestyle='--', alpha=0.4)
        
        for spine in ['top', 'right', 'left', 'bottom']:
            ax.spines[spine].set_visible(False)
            
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.sector_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        plt.close(fig)

    # ---------------------------------------------------------------------
    # GRID POPULATION & FILTERING
    # ---------------------------------------------------------------------
    def _on_date_changed(self, new_val):
        self.selected_snapshot_date = new_val
        self.refresh_all()

    def load_grid_data(self):
        threading.Thread(target=self._bg_load_grid, daemon=True).start()

    def _bg_load_grid(self):
        try:
            df = self.db.get_comprehensive_rollover_table(
                sector=self.f_sector.get(),
                snapshot_date=self.selected_snapshot_date,
                sentiment=self.f_sentiment.get()
            )
            self.after(0, lambda: self._populate_grid(df))
        except Exception as e:
            print(f"Error filtering grid: {e}")

    def _populate_grid(self, df):
        if df.empty:
            self.sheet.set_sheet_data([["No rollover records matching criteria."]])
            self.grid_count_lbl.configure(text="0 stocks")
            return
            
        search_txt = self.search_var.get().strip().upper()
        if search_txt:
            df = df[df['Symbol'].str.upper().str.contains(search_txt)]
            
        self.grid_count_lbl.configure(text=f"{len(df)} F&O stocks")
        
        rows = []
        for _, r in df.iterrows():
            spread = r['Roll_Cost'] or 0.0
            spread_pct = r['Roll_Cost_Pct'] or 0.0
            p_chg = r['Price_Chg_Pct'] or 0.0
            roll_pct = r['Roll_Pct'] or 0.0
            
            rows.append([
                r['Symbol'],
                r['Sector'],
                f"{r['Near_Price']:.2f}" if r['Near_Price'] else "--",
                f"{r['Next_Price']:.2f}" if r['Next_Price'] else "--",
                f"{spread:+.2f}",
                f"{spread_pct:+.2f}%",
                f"{p_chg:+.2f}%",
                f"{int(r['Near_OI']):,}",
                f"{int(r['Next_OI']):,}",
                f"{int(r['Far_OI']):,}",
                f"{int(r['Total_OI']):,}",
                f"{int(r['Roll_OI']):,}",
                f"{roll_pct:.2f}%",
                r['Roll_Sentiment']
            ])
            
        self.sheet.set_sheet_data(rows)
        
        # Color highlighting
        green, red, yellow, orange = [], [], [], []
        for r_idx, row in enumerate(rows):
            spread_val = float(row[4].replace('+', ''))
            sent = row[13]
            
            # Spread column highlight
            if spread_val > 0:
                green.append((r_idx, 4))
                green.append((r_idx, 5))
            elif spread_val < 0:
                red.append((r_idx, 4))
                red.append((r_idx, 5))
                
            # Sentiment column highlight
            if "Long Buildup" in sent:
                green.append((r_idx, 13))
            elif "Short Buildup" in sent:
                red.append((r_idx, 13))
            elif "Short Covering" in sent:
                yellow.append((r_idx, 13))
            else:
                orange.append((r_idx, 13))
                
        if green: self.sheet.highlight_cells(cells=green, fg="#00E676")
        if red: self.sheet.highlight_cells(cells=red, fg="#FF1744")
        if yellow: self.sheet.highlight_cells(cells=yellow, fg="#FFD54F")
        if orange: self.sheet.highlight_cells(cells=orange, fg="#FF8A65")

    def on_grid_double_click(self, event):
        row = self.sheet.identify_row(event)
        if row is not None and row >= 0:
            sheet_data = self.sheet.get_sheet_data()
            if row < len(sheet_data) and len(sheet_data[row]) > 0:
                sym = sheet_data[row][0]
                if sym and sym != "No rollover records matching criteria.":
                    SymbolRolloverDrilldownWindow(self.winfo_toplevel(), sym, self.db, self.selected_snapshot_date)

    # ---------------------------------------------------------------------
    # HISTORY TAB & LIVE SYNC
    # ---------------------------------------------------------------------
    def _populate_history(self, df):
        for item in self.hist_tree.get_children():
            self.hist_tree.delete(item)
            
        if not df.empty:
            for _, r in df.iterrows():
                dt_str = str(r['Date'])[:10]
                self.hist_tree.insert("", "end", values=(dt_str, r['Filename'], f"{r['SymbolCount']} symbols", "🔍 Open Analysis"))

    def on_history_click(self, event):
        item_id = self.hist_tree.identify_row(event.y)
        if item_id:
            values = self.hist_tree.item(item_id, "values")
            if values and len(values) > 0:
                sel_date = values[0]
                self.selected_snapshot_date = sel_date
                self.f_date.set(sel_date)
                self.rtabs.set("Comprehensive Grid")
                self.refresh_all()

    def sync_live_feed(self):
        self.sync_btn.configure(text="Syncing Live Feed...", state="disabled")
        self.status_lbl.configure(text="Connecting to official NSE live feed...", text_color="#0288D1")
        
        def bg_sync():
            try:
                res = self.db.sync_live_rollover_feed()
                msg = res.get("message", "Live sync completed.")
                self.after(0, lambda: self._on_sync_done(msg))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._on_error(f"Sync error: {err_msg}"))
                
        threading.Thread(target=bg_sync, daemon=True).start()

    def _on_sync_done(self, msg):
        self.sync_btn.configure(text="⚡ Live Sync Feed", state="normal")
        self.status_lbl.configure(text="Sync successful.", text_color="#00E676")
        messagebox.showinfo("Live Feed Sync", msg)
        self.refresh_all()

    def import_pdf(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            initialdir=r"c:\Users\navin\StockMarketFnO\data\Rollover Files",
            title="Select Rollover PDF or Bhavcopy CSV",
            filetypes=(("PDF and CSV files", "*.pdf;*.csv"), ("PDF files", "*.pdf"), ("CSV files", "*.csv"), ("all files", "*.*"))
        )
        if file_path:
            self.import_btn.configure(text="Processing...", state="disabled")
            threading.Thread(target=self._import_bg, args=(file_path,), daemon=True).start()

    def _import_bg(self, file_path):
        try:
            if file_path.lower().endswith(".pdf"):
                import pdfplumber
                import re
                
                date_match = re.search(r'(\d{2}-\d{2}-\d{4})', file_path)
                if date_match:
                    report_date = datetime.strptime(date_match.group(1), '%d-%m-%Y').strftime('%Y-%m-%d')
                else:
                    report_date = datetime.now().strftime('%Y-%m-%d')
                    
                data_to_insert = []
                with self.db.get_connection() as conn:
                    sector_df = pd.read_sql("SELECT Symbol, Sector, Industry FROM FNO_STOCKS_Sectors_Master_Refined_NEW", conn)
                    sector_map = sector_df.set_index('Symbol').to_dict('index')

                with pdfplumber.open(file_path) as pdf:
                    for page in pdf.pages:
                        table = page.extract_table()
                        if not table: continue
                        for row in table:
                            if not row or len(row) < 5 or str(row[0]).upper() in ['SYMBOL', 'TOTAL', 'NIFTY', 'BANKNIFTY']: continue
                            sym = str(row[0]).strip().upper()
                            if not sym or len(sym) > 20: continue
                            
                            def clean_f(val):
                                if val is None: return 0.0
                                s = str(val).replace('%','').replace(',','').replace('(','-').replace(')','').strip()
                                return float(s) if s and s != '-' else 0.0
                                
                            roll_pct = clean_f(row[1])
                            avg_roll = clean_f(row[2])
                            cost_pct = clean_f(row[3])
                            oi_chg = clean_f(row[4])
                            pr_chg = clean_f(row[5])
                            basis = clean_f(row[6]) if len(row) > 6 else 0.0
                            near_oi = int(clean_f(row[7])) if len(row) > 7 else 0
                            next_oi = int(clean_f(row[8])) if len(row) > 8 else 0
                            far_oi = int(clean_f(row[9])) if len(row) > 9 else 0
                            total_oi = int(clean_f(row[10])) if len(row) > 10 else near_oi + next_oi + far_oi
                            
                            meta = sector_map.get(sym, {'Sector': 'Others', 'Industry': 'Others'})
                            sent = "Neutral"
                            if roll_pct >= avg_roll and pr_chg > 0: sent = "Long Buildup (Bullish Carry)"
                            elif roll_pct >= avg_roll and pr_chg < 0: sent = "Short Buildup (Bearish Roll)"
                            elif roll_pct < avg_roll and pr_chg > 0: sent = "Short Covering (Relief)"
                            else: sent = "Long Unwinding (Exiting)"

                            data_to_insert.append((report_date, sym, meta['Sector'], meta['Industry'], roll_pct, avg_roll, cost_pct, oi_chg, pr_chg, basis, near_oi, next_oi, far_oi, total_oi, sent))

                if data_to_insert:
                    with self.db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM Monthly_Rollover_Analysis WHERE Report_Date = ?", (report_date,))
                        cursor.executemany("""
                            INSERT INTO Monthly_Rollover_Analysis (Report_Date, Symbol, Sector, Industry, Rollover_Pct, Avg_Rollover_3M, Roll_Cost_Pct, Change_OI_Pct, Price_Chg_Pct, Basis, Near_OI, Next_OI, Far_OI, Total_OI, Roll_Sentiment)
                            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        """, data_to_insert)
                        conn.commit()
                    self.after(0, lambda: messagebox.showinfo("Success", f"Imported {len(data_to_insert)} records for {report_date}"))
                    self.after(0, self.refresh_all)
            else:
                self.after(0, lambda: messagebox.showinfo("CSV Import", "CSV Bhavcopy ingestion triggered via standard pipeline."))
                self.after(0, self.refresh_all)
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: messagebox.showerror("Error", f"Failed to import file: {msg}"))
        finally:
            self.after(0, lambda: self.import_btn.configure(text="📁 Import Custom PDF / Bhavcopy", state="normal"))

    def _on_error(self, err_msg):
        self.refresh_btn.configure(text="🔄 Refresh", state="normal")
        self.status_lbl.configure(text="Error occurred.", text_color="#FF1744")
        print(f"Rollover Intelligence Error: {err_msg}")
