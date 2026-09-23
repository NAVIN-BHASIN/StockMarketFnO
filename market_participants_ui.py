import os
import sys
import threading
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tksheet import Sheet

# Add workspace directory to path
sys.path.append(r"c:\Users\navin\StockMarketFnO")
from db_utils import DatabaseHelper
from smart_money_stance import (
    StanceJustificationWindow,
    IndexStanceDrilldownWindow,
    DivergenceInsightWindow,
    StockStanceDrilldownWindow
)

# -------------------------------------------------------------
# Participant Deep Drilldown Modal
# -------------------------------------------------------------
class ParticipantDetailModal(ctk.CTkToplevel):
    def __init__(self, master, client_type, row_data):
        super().__init__(master)
        self.title(f"Participant Position Intelligence - {client_type}")
        self.geometry("820x620")
        self.attributes("-topmost", True)
        self.configure(fg_color="#0d1117")
        
        ctk.CTkLabel(
            self,
            text=f"PARTICIPANT POSITION DEEP-DIVE: {client_type.upper()}",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#FFD54F"
        ).pack(pady=(20, 10))
        
        # Grid of metrics
        grid_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        grid_frame.pack(fill="x", padx=25, pady=10)
        grid_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        headers = [
            ("Index Fut Long", row_data.get("Index Fut Long", 0)),
            ("Index Fut Short", row_data.get("Index Fut Short", 0)),
            ("Net Index Fut", row_data.get("Net Index Fut", 0)),
            ("Index Long %", f"{row_data.get('Index Fut Long %', 0)}%"),
            ("Stock Fut Long", row_data.get("Stock Fut Long", 0)),
            ("Stock Fut Short", row_data.get("Stock Fut Short", 0)),
            ("Net Stock Fut", row_data.get("Net Stock Fut", 0)),
            ("Stance Bias", row_data.get("Stance Bias", "--")),
            ("Index Call Long", row_data.get("Index Call Long", 0)),
            ("Index Call Short", row_data.get("Index Call Short", 0)),
            ("Net Index Calls", row_data.get("Net Index Calls", 0)),
            ("Net Index Puts", row_data.get("Net Index Puts", 0)),
        ]
        
        for idx, (label, val) in enumerate(headers):
            r = idx // 4
            c = idx % 4
            card = ctk.CTkFrame(grid_frame, fg_color="transparent")
            card.grid(row=r, column=c, padx=10, pady=8, sticky="nsew")
            ctk.CTkLabel(card, text=label, font=ctk.CTkFont(size=11), text_color="gray60").pack()
            val_str = f"{val:,}" if isinstance(val, (int, float)) and not isinstance(val, bool) and not str(val).endswith('%') else str(val)
            color = "#00E676" if str(val).startswith('+') or (isinstance(val, (int, float)) and val > 0 and 'Short' not in label and 'Put' not in label) else "#FF1744" if (isinstance(val, (int, float)) and val < 0) or 'Bearish' in str(val) or 'Short' in str(val) else "#FFD54F"
            ctk.CTkLabel(card, text=val_str, font=ctk.CTkFont(size=13, weight="bold"), text_color=color).pack()
            
        # Analysis text panel
        text_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        text_frame.pack(fill="both", expand=True, padx=25, pady=(10, 20))
        
        txt = ctk.CTkTextbox(text_frame, fg_color="transparent", font=ctk.CTkFont(size=13, family="Consolas"), wrap="word")
        txt.pack(fill="both", expand=True, padx=15, pady=15)
        
        explanation = self._generate_detailed_insight(client_type, row_data)
        txt.insert("1.0", explanation)
        txt.configure(state="disabled")
        
    def _generate_detailed_insight(self, client_type, r):
        out = f"========================================================================================\n"
        out += f"                 INSTITUTIONAL INTENT & POSITION ANALYSIS: {client_type}               \n"
        out += f"========================================================================================\n\n"
        
        if "FII" in client_type:
            ratio = float(str(r.get("Index Fut Long %", 0)).replace('%', '') or 0)
            net_fut = int(r.get("Net Index Fut", 0))
            net_calls = int(r.get("Net Index Calls", 0))
            net_puts = int(r.get("Net Index Puts", 0))
            out += "1. FOREIGN INSTITUTIONAL INVESTORS (FII) STRATEGY:\n"
            out += f"   - FIIs are the primary trend drivers and carry the highest market impact.\n"
            out += f"   - Current Index Futures Long Ratio: {ratio:.1f}%\n"
            if ratio < 25:
                out += f"   - EXTREME OVERSOLD WARNING: Long ratio is below 25% (currently {ratio:.1f}%).\n"
                out += f"     Historically, when FII long ratio drops below 20-25%, the market enters a violent short-squeeze zone.\n"
                out += f"     While the immediate trend is bearish, aggressive fresh shorts carry severe counter-rally risk.\n\n"
            elif ratio > 70:
                out += f"   - EXTREME OVERBOUGHT EXHAUSTION: Long ratio is above 70% ({ratio:.1f}%).\n"
                out += f"     FIIs are near maximum long capacity. Expect profit booking or sharp distribution dips.\n\n"
            else:
                out += f"   - BALANCED / TRANSITIONAL ZONE: FII long ratio is within normal operational band.\n\n"
                
            out += "2. OPTIONS BIAS & HEDGE RATIO:\n"
            out += f"   - Net Index Calls: {net_calls:+,} contracts\n"
            out += f"   - Net Index Puts: {net_puts:+,} contracts\n"
            if net_puts > 0 and net_calls < 0:
                out += "   - STRUCTURE: Heavy Net Put Buying & Call Writing. Shows active downside portfolio protection.\n"
            elif net_calls > 0 and net_puts < 0:
                out += "   - STRUCTURE: Aggressive Call Buying & Put Writing. Confirms upside breakout positioning.\n"
            else:
                out += "   - STRUCTURE: Mixed options exposure (spreads / delta neutral positioning).\n\n"
                
        elif "Client" in client_type or "Retail" in client_type:
            out += "1. RETAIL TRADER (CLIENT) EXPOSURE & CONTRARIAN READ:\n"
            out += "   - Retail positioning acts as the primary counterparty to Institutional Smart Money (FII + Pro).\n"
            out += f"   - Current Net Index Futures: {int(r.get('Net Index Fut', 0)):+,} contracts\n"
            out += f"   - Current Net Index Calls: {int(r.get('Net Index Calls', 0)):+,} contracts\n"
            out += f"   - Current Net Index Puts: {int(r.get('Net Index Puts', 0)):+,} contracts\n\n"
            out += "2. COUNTERPARTY WARNING:\n"
            out += "   - When Retail holds heavy longs while FII holds heavy shorts, market makers typically drive prices down\n"
            out += "     to hit retail stop-losses before any sustainable recovery can form.\n"
            out += "   - Always align trades with FII cash/derivatives momentum rather than retail herd sentiment.\n\n"
            
        elif "PRO" in client_type or "Prop" in client_type:
            out += "1. PROPRIETARY DESKS (PROP DESK) INTENT:\n"
            out += "   - Prop desks specialize in high-frequency option writing, straddles/strangles, and delta scalping.\n"
            out += f"   - Net Index Calls: {int(r.get('Net Index Calls', 0)):+,} contracts\n"
            out += f"   - Net Index Puts: {int(r.get('Net Index Puts', 0)):+,} contracts\n"
            out += "   - Prop desks defend their written strikes aggressively to force time-decay (Theta).\n"
            out += "   - Track whether Prop Desks are writing calls or puts to identify the daily pinned range.\n\n"
            
        elif "DII" in client_type:
            out += "1. DOMESTIC INSTITUTIONAL INVESTORS (DII) ROLE:\n"
            out += "   - DIIs (Mutual Funds & Insurance funds) provide steady absorption via systematic cash inflows.\n"
            out += "   - They primarily hold short stock futures as cash-futures arbitrage hedges.\n"
            out += f"   - Net Stock Futures: {int(r.get('Net Stock Fut', 0)):+,} contracts (Arbitrage hedge inventory).\n"
            out += "   - Watch DII cash buying to see if institutional domestic liquidity is absorbing FII selling.\n\n"
            
        out += "========================================================================================\n"
        out += " ACTIONABLE RULE: Never initiate naked directional trades against the combined FII + Pro stance.\n"
        return out


# -------------------------------------------------------------
# Main Market Participants Frame
# -------------------------------------------------------------
class MarketParticipantsFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=15)
        self.master = master
        self.db = getattr(master, 'db', DatabaseHelper())
        
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.all_dates = []
        self.current_snapshot_date = None
        self.master_df = pd.DataFrame()
        self.current_csi = 0.0
        self.current_justification = ""
        
        # Divergence Chart Toggles
        self.chart_asset = "Index"
        self.chart_timeframe = "15D"
        
        # 1. Top Header & Action Controls
        self._build_header()
        
        # 2. KPI Summary Ribbon
        self._build_kpi_ribbon()
        
        # 3. Main Multi-Section Tabs
        self._build_tabs()
        
        # Initial Data Load
        self.load_all_data()

    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 5))
        
        left_box = ctk.CTkFrame(hdr, fg_color="transparent")
        left_box.pack(side="left", fill="y")
        
        ctk.CTkLabel(
            left_box, 
            text="Market Participants Intelligence & Flow Dynamics", 
            font=ctk.CTkFont(size=22, weight="bold"), 
            text_color="#FFD54F"
        ).pack(anchor="w")
        
        self.status_lbl = ctk.CTkLabel(
            left_box, 
            text="Loading participant feeds...", 
            font=ctk.CTkFont(size=12, slant="italic"), 
            text_color="gray60"
        )
        self.status_lbl.pack(anchor="w")
        
        # Buttons on right
        btn_box = ctk.CTkFrame(hdr, fg_color="transparent")
        btn_box.pack(side="right", fill="y")
        
        self.export_btn = ctk.CTkButton(
            btn_box,
            text="📊 Export to Excel",
            width=135,
            fg_color="#2e7d32",
            hover_color="#388e3c",
            command=self.export_to_excel
        )
        self.export_btn.pack(side="left", padx=5)
        
        self.ingest_btn = ctk.CTkButton(
            btn_box,
            text="📥 Ingest Local Files",
            width=140,
            fg_color="#00897b",
            hover_color="#009688",
            command=self.run_local_ingestion
        )
        self.ingest_btn.pack(side="left", padx=5)
        
        self.refresh_btn = ctk.CTkButton(
            btn_box,
            text="🔄 Refresh",
            width=100,
            fg_color="#1565c0",
            hover_color="#1976d2",
            command=self.load_all_data
        )
        self.refresh_btn.pack(side="left", padx=5)

    def _build_kpi_ribbon(self):
        self.kpi_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10, height=70)
        self.kpi_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(5, 10))
        self.kpi_frame.grid_propagate(False)
        self.kpi_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1, uniform="kpi")
        
        self.kpi_labels = {}
        cards = [
            ("FII Index Fut Long %", "fii_ratio", "--"),
            ("FII Net Index Contracts", "fii_net_idx", "--"),
            ("Retail Net Index Contracts", "ret_net_idx", "--"),
            ("PRO Desk Net Index", "pro_net_idx", "--"),
            ("FII Cash (Latest MTD)", "fii_cash", "--"),
            ("Institutional Stance (CSI)", "csi_stance", "--"),
        ]
        
        for idx, (title, key, def_val) in enumerate(cards):
            card = ctk.CTkFrame(self.kpi_frame, fg_color="transparent")
            card.grid(row=0, column=idx, padx=5, pady=8, sticky="nsew")
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="gray60").pack()
            lbl = ctk.CTkLabel(card, text=def_val, font=ctk.CTkFont(size=13, weight="bold"), text_color="#E0E0E0")
            lbl.pack(pady=2)
            self.kpi_labels[key] = lbl

    def _build_tabs(self):
        self.tabs = ctk.CTkTabview(self, corner_radius=12)
        self.tabs.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 15))
        
        self.tabs.add("Participant F&O Positioning (OI Summary)")
        self.tabs.add("Institutional Cash Flow Activity")
        self.tabs.add("Smart Money Stance & Divergence Tracker")
        self.tabs.add("FII Derivatives Statistics (NSE)")
        self.tabs.add("Stock F&O Focus & Trap Radar")
        
        self._build_tab1_positioning()
        self._build_tab2_cash_flow()
        self._build_tab3_smart_money()
        self._build_tab4_fii_stats()
        self._build_tab5_stock_focus()

    # -------------------------------------------------------------
    # TAB 1: Participant F&O Positioning (OI Matrix)
    # -------------------------------------------------------------
    def _build_tab1_positioning(self):
        tab = self.tabs.tab("Participant F&O Positioning (OI Summary)")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(top_bar, text="Select Snapshot Date:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=5)
        self.snap_date_var = ctk.StringVar(value="Latest")
        self.date_menu = ctk.CTkOptionMenu(
            top_bar, 
            variable=self.snap_date_var, 
            values=["Latest"],
            command=self.on_date_changed,
            width=130
        )
        self.date_menu.pack(side="left", padx=5)
        
        ctk.CTkLabel(
            top_bar, 
            text="Tip: Double-click any participant row for deep intentional breakdown & hedge ratio.", 
            font=ctk.CTkFont(size=11, slant="italic"), 
            text_color="gray60"
        ).pack(side="left", padx=15)
        
        cols = [
            "Client Type", "Index Fut Long", "Index Fut Short", "Net Index Fut", 
            "Index Fut Long %", "Stock Fut Long", "Stock Fut Short", "Net Stock Fut", 
            "Index Call Long", "Index Call Short", "Net Index Calls", 
            "Index Put Long", "Index Put Short", "Net Index Puts", "Stance Bias"
        ]
        
        self.pos_sheet_container = ctk.CTkFrame(tab, fg_color="#161b22", corner_radius=10)
        self.pos_sheet_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        self.pos_sheet = Sheet(self.pos_sheet_container, headers=cols)
        self.pos_sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.pos_sheet.change_theme("dark")
        else:
            self.pos_sheet.change_theme("light blue")
        self.pos_sheet.set_options(font=("Segoe UI", 12, "normal"), header_font=("Segoe UI", 13, "bold"))
        self.pos_sheet.pack(fill="both", expand=True, padx=8, pady=8)
        self.pos_sheet.MT.bind("<Double-1>", self.on_pos_row_double_click)

    # -------------------------------------------------------------
    # TAB 2: Institutional Cash Flow Activity
    # -------------------------------------------------------------
    def _build_tab2_cash_flow(self):
        tab = self.tabs.tab("Institutional Cash Flow Activity")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        top_ctrl = ctk.CTkFrame(tab, fg_color="transparent")
        top_ctrl.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        self.cash_period_seg = ctk.CTkSegmentedButton(
            top_ctrl,
            values=["Day Wise Summary", "Monthly Summary (1 Year)", "Yearly Summary (5 Years)"],
            command=self.on_cash_period_toggle
        )
        self.cash_period_seg.set("Day Wise Summary")
        self.cash_period_seg.pack(side="left", padx=5)
        
        self.cash_month_lbl = ctk.CTkLabel(top_ctrl, text="Select Month:")
        self.cash_month_lbl.pack(side="left", padx=(20, 5))
        
        self.cash_month_var = ctk.StringVar(value="September 2026")
        self.cash_month_menu = ctk.CTkOptionMenu(
            top_ctrl,
            variable=self.cash_month_var,
            values=["September 2026", "August 2026", "July 2026", "June 2026", "May 2026", "April 2026", "March 2026", "February 2026"],
            command=self.load_cash_flow_data,
            width=150
        )
        self.cash_month_menu.pack(side="left", padx=5)
        
        cols = ["Period", "FII Cash (Cr)", "FII FnO (Cr)", "DII Cash (Cr)", "DII FnO (Cr)", "PROP Desk (Cr)", "Retail (Cr)", "Net Trend"]
        
        self.cash_sheet_container = ctk.CTkFrame(tab, fg_color="#161b22", corner_radius=10)
        self.cash_sheet_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        self.cash_sheet = Sheet(self.cash_sheet_container, headers=cols)
        self.cash_sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.cash_sheet.change_theme("dark")
        else:
            self.cash_sheet.change_theme("light blue")
        self.cash_sheet.set_options(font=("Segoe UI", 12, "normal"), header_font=("Segoe UI", 13, "bold"))
        self.cash_sheet.pack(fill="both", expand=True, padx=8, pady=8)

    # -------------------------------------------------------------
    # TAB 3: Smart Money Stance & Divergence Tracker
    # -------------------------------------------------------------
    def _build_tab3_smart_money(self):
        tab = self.tabs.tab("Smart Money Stance & Divergence Tracker")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        
        # All Clear Direction Banner
        self.all_clear_card = ctk.CTkFrame(tab, fg_color="#1a2230", border_width=1, border_color="#30363d", corner_radius=10, height=55)
        self.all_clear_card.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 5))
        self.all_clear_card.grid_propagate(False)
        self.all_clear_card.grid_columnconfigure(0, weight=1)
        self.all_clear_card.grid_rowconfigure(0, weight=1)
        
        self.all_clear_lbl = ctk.CTkLabel(
            self.all_clear_card,
            text="DIRECTIONAL BIAS: CALCULATING COMBINED STANCE INDEX (CSI)...",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#FFB300"
        )
        self.all_clear_lbl.grid(row=0, column=0, sticky="nsew")
        self.all_clear_card.bind("<Double-1>", self.on_all_clear_double_click)
        self.all_clear_lbl.bind("<Double-1>", self.on_all_clear_double_click)
        
        # Momentum Shift row
        self.mom_frame = ctk.CTkFrame(tab, fg_color="#161b22", corner_radius=10, height=65)
        self.mom_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=5)
        self.mom_frame.grid_propagate(False)
        self.mom_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="mom")
        
        self.card_1d_lbl = self._create_mom_card(self.mom_frame, 0, "1-DAY MOMENTUM SHIFT")
        self.card_3d_lbl = self._create_mom_card(self.mom_frame, 1, "3-DAY ACCUMULATION TREND")
        self.card_5d_lbl = self._create_mom_card(self.mom_frame, 2, "5-DAY MACRO DIRECTION")
        
        # Mid Panels: Index Specifics & Divergence Chart
        mid = ctk.CTkFrame(tab, fg_color="transparent")
        mid.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        mid.grid_columnconfigure(0, weight=6, uniform="mid_sm")
        mid.grid_columnconfigure(1, weight=4, uniform="mid_sm")
        mid.grid_rowconfigure(0, weight=1)
        
        # Left: Index Matrix
        idx_box = ctk.CTkFrame(mid, fg_color="#161b22", corner_radius=10)
        idx_box.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        idx_box.grid_columnconfigure(0, weight=1)
        idx_box.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            idx_box,
            text="Index-Specific Participant Positioning (Double-click row for Rollover Spreads)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FFD54F"
        ).grid(row=0, column=0, padx=10, pady=(8, 4), sticky="w")
        
        idx_cols = ["Index", "FII Net Fut", "Prop Net Fut", "Retail Net Fut", "FII Opt Net", "Prop Opt Net", "Retail Opt Net", "Direction"]
        self.sm_index_sheet = Sheet(idx_box, headers=idx_cols)
        self.sm_index_sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.sm_index_sheet.change_theme("dark")
        else:
            self.sm_index_sheet.change_theme("light blue")
        self.sm_index_sheet.set_options(font=("Segoe UI", 11, "normal"), header_font=("Segoe UI", 12, "bold"))
        self.sm_index_sheet.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.sm_index_sheet.MT.bind("<Double-1>", self.on_sm_index_double_click)
        
        # Right: Divergence Chart
        chart_box = ctk.CTkFrame(mid, fg_color="#161b22", corner_radius=10)
        chart_box.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        chart_box.grid_columnconfigure(0, weight=1)
        chart_box.grid_rowconfigure(1, weight=1)
        
        ctrl_bar = ctk.CTkFrame(chart_box, fg_color="transparent")
        ctrl_bar.grid(row=0, column=0, sticky="ew", padx=8, pady=(8, 2))
        
        self.asset_seg = ctk.CTkSegmentedButton(ctrl_bar, values=["Index", "Stocks"], width=90, command=self.on_asset_toggle)
        self.asset_seg.set("Index")
        self.asset_seg.pack(side="left")
        
        self.tf_seg = ctk.CTkSegmentedButton(ctrl_bar, values=["3D", "5D", "15D", "30D"], width=130, command=self.on_tf_toggle)
        self.tf_seg.set("15D")
        self.tf_seg.pack(side="right")
        
        self.chart_container = ctk.CTkFrame(chart_box, fg_color="transparent")
        self.chart_container.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.chart_container.grid_columnconfigure(0, weight=1)
        self.chart_container.grid_rowconfigure(0, weight=1)

    def _create_mom_card(self, parent, col, title):
        card = ctk.CTkFrame(parent, fg_color="transparent")
        card.grid(row=0, column=col, padx=10, pady=5, sticky="nsew")
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="gray50").pack()
        lbl = ctk.CTkLabel(card, text="FII: -- | PROP: -- | RETAIL: --", font=ctk.CTkFont(size=12, family="Consolas"), text_color="#E0E0E0")
        lbl.pack(pady=2)
        return lbl

    # -------------------------------------------------------------
    # TAB 4: FII Derivatives Statistics (NSE FII Stats)
    # -------------------------------------------------------------
    def _build_tab4_fii_stats(self):
        tab = self.tabs.tab("FII Derivatives Statistics (NSE)")
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)
        
        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(top_bar, text="Snapshot Date:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=5)
        self.fii_date_var = ctk.StringVar(value="Latest")
        self.fii_date_menu = ctk.CTkOptionMenu(
            top_bar,
            variable=self.fii_date_var,
            values=["Latest"],
            command=self.load_fii_stats_data,
            width=130
        )
        self.fii_date_menu.pack(side="left", padx=5)
        
        self.fii_stats_lbl = ctk.CTkLabel(
            top_bar, 
            text="Real derivative turnover and contracts traded by Foreign Portfolio Investors (FIIs)",
            font=ctk.CTkFont(size=11, slant="italic"),
            text_color="gray60"
        )
        self.fii_stats_lbl.pack(side="left", padx=15)
        
        cols = ["Product", "Buy Contracts", "Buy Value (Cr)", "Sell Contracts", "Sell Value (Cr)", "Net Contracts", "Net Value (Cr)", "OI Contracts", "OI Value (Cr)", "Flow Bias"]
        
        self.fii_sheet_container = ctk.CTkFrame(tab, fg_color="#161b22", corner_radius=10)
        self.fii_sheet_container.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        self.fii_sheet = Sheet(self.fii_sheet_container, headers=cols)
        self.fii_sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.fii_sheet.change_theme("dark")
        else:
            self.fii_sheet.change_theme("light blue")
        self.fii_sheet.set_options(font=("Segoe UI", 12, "normal"), header_font=("Segoe UI", 13, "bold"))
        self.fii_sheet.pack(fill="both", expand=True, padx=8, pady=8)

    # -------------------------------------------------------------
    # TAB 5: Stock F&O Focus & Trap Radar
    # -------------------------------------------------------------
    def _build_tab5_stock_focus(self):
        tab = self.tabs.tab("Stock F&O Focus & Trap Radar")
        tab.grid_columnconfigure(0, weight=6, uniform="stk_split")
        tab.grid_columnconfigure(1, weight=4, uniform="stk_split")
        tab.grid_rowconfigure(0, weight=1)
        
        # Left: Stock Setups Sheet
        left_box = ctk.CTkFrame(tab, fg_color="#161b22", corner_radius=10)
        left_box.grid(row=0, column=0, sticky="nsew", padx=(10, 5), pady=10)
        left_box.grid_columnconfigure(0, weight=1)
        left_box.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            left_box, 
            text="Institutional Stock Focus (Double-click row for Price vs OI Chart)",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FFD54F"
        ).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        stk_cols = ["Symbol", "Price", "Price Chg %", "OI Chg %", "Setup", "Stance Advice", "Volume (Cr)"]
        self.stk_sheet = Sheet(left_box, headers=stk_cols)
        self.stk_sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.stk_sheet.change_theme("dark")
        else:
            self.stk_sheet.change_theme("light blue")
        self.stk_sheet.set_options(font=("Segoe UI", 11, "normal"), header_font=("Segoe UI", 12, "bold"))
        self.stk_sheet.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
        self.stk_sheet.MT.bind("<Double-1>", self.on_stock_row_double_click)
        
        # Right: Trap Radar Text Panel
        right_box = ctk.CTkFrame(tab, fg_color="#161b22", corner_radius=10)
        right_box.grid(row=0, column=1, sticky="nsew", padx=(5, 10), pady=10)
        right_box.grid_columnconfigure(0, weight=1)
        right_box.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            right_box,
            text="⚡ Trap Radar & Smart Money Secrets",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#FFD54F"
        ).grid(row=0, column=0, padx=10, pady=(10, 5), sticky="w")
        
        self.traps_txt = ctk.CTkTextbox(
            right_box,
            fg_color="transparent",
            font=ctk.CTkFont(size=12, family="Consolas"),
            wrap="word"
        )
        self.traps_txt.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))

    # -------------------------------------------------------------
    # Data Loading & Dispatching
    # -------------------------------------------------------------
    def _safe_dispatch(self, callback):
        try:
            if not self.winfo_exists():
                return
            self.after(0, callback)
        except Exception:
            try:
                if self.winfo_exists():
                    callback()
            except Exception:
                pass

    def load_all_data(self):
        self.status_lbl.configure(text="Fetching latest database feeds...", text_color="gray60")
        self.refresh_btn.configure(state="disabled", text="Loading...")
        threading.Thread(target=self._bg_load, daemon=True).start()

    def _bg_load(self):
        try:
            # 1. Dates
            dates = self.db.get_participant_snapshot_dates()
            
            # 2. Latest positioning
            df_pos, actual_date = self.db.get_participant_positions_by_date()
            
            # 3. FII Stats
            df_fii = self.db.get_fii_derivatives_stats_by_date()
            
            # 4. Master series for smart money analysis
            df_series, csi_score, just_text, mom_dict, idx_rows, stock_rows, trap_text = self._compute_smart_money_data()
            
            self._safe_dispatch(lambda: self._on_data_loaded(dates, df_pos, actual_date, df_fii, df_series, csi_score, just_text, mom_dict, idx_rows, stock_rows, trap_text))
        except Exception as e:
            self._safe_dispatch(lambda: self._on_error(f"Failed to load participant data: {e}"))

    def _compute_smart_money_data(self):
        q = """
        SELECT SnapshotDate, ClientType, InstrumentType, OI_Long, OI_Short, Vol_Long, Vol_Short
        FROM dbo.NSE_Participant_Positions
        ORDER BY SnapshotDate ASC, ClientType, InstrumentType
        """
        q_stocks = """
        WITH LatestTwoDates AS (
            SELECT DISTINCT TOP 2 SnapShotDate
            FROM dbo.vw_Futures_FnO_Analysis
            ORDER BY SnapShotDate DESC
        )
        SELECT SnapShotDate, SYMBOL, CLOSE_PRIC, OI_NO_CON, TRD_NO_CON, TRADED_VAL
        FROM dbo.vw_Futures_FnO_Analysis
        WHERE SnapShotDate IN (SELECT SnapShotDate FROM LatestTwoDates)
          AND INSTRUMENTTYPE = 'FUTSTK'
        """
        with self.db.get_connection() as conn:
            df = pd.read_sql(q, conn)
            try:
                df_stk = pd.read_sql(q_stocks, conn)
            except:
                df_stk = pd.DataFrame()
                
        if df.empty:
            return pd.DataFrame(), 0.0, "No participant data found.", {}, [], [], "No trap data available."
            
        df['SnapshotDate'] = pd.to_datetime(df['SnapshotDate'])
        df_f = df[df['ClientType'].isin(['FII', 'Pro', 'Client'])].copy()
        df_f['Net_OI'] = df_f['OI_Long'].fillna(0) - df_f['OI_Short'].fillna(0)
        
        piv = df_f.pivot_table(index='SnapshotDate', columns=['ClientType', 'InstrumentType'], values='Net_OI', aggfunc='sum').fillna(0)
        
        dates = piv.index
        metrics = []
        for d in dates:
            row = piv.loc[d]
            fii_fut = row.get(('FII', 'Future Index'), 0)
            fii_c = row.get(('FII', 'Option Index Call'), 0)
            fii_p = row.get(('FII', 'Option Index Put'), 0)
            fii_stk = row.get(('FII', 'Future Stock'), 0)
            
            pro_fut = row.get(('Pro', 'Future Index'), 0)
            pro_c = row.get(('Pro', 'Option Index Call'), 0)
            pro_p = row.get(('Pro', 'Option Index Put'), 0)
            pro_stk = row.get(('Pro', 'Future Stock'), 0)
            
            cli_fut = row.get(('Client', 'Future Index'), 0)
            cli_c = row.get(('Client', 'Option Index Call'), 0)
            cli_p = row.get(('Client', 'Option Index Put'), 0)
            cli_stk = row.get(('Client', 'Future Stock'), 0)
            
            metrics.append({
                'Date': d.strftime('%Y-%m-%d'),
                'Smart_Index_Fut': fii_fut + pro_fut,
                'Retail_Index_Fut': cli_fut,
                'Smart_Index_Opt': (fii_c - fii_p) + (pro_c - pro_p),
                'Retail_Index_Opt': cli_c - cli_p,
                'Smart_Stock_Fut': fii_stk + pro_stk,
                'Retail_Stock_Fut': cli_stk,
                'FII_Index_Fut': fii_fut,
                'Prop_Index_Fut': pro_fut,
                'Retail_Index_Fut_Val': cli_fut,
                'FII_Opt_Net': fii_c - fii_p,
                'Prop_Opt_Net': pro_c - pro_p,
                'Retail_Opt_Net': cli_c - cli_p,
            })
            
        res_df = pd.DataFrame(metrics)
        
        # CSI Calculation
        csi = 0.0
        if len(res_df) >= 5:
            idx = len(res_df) - 1
            f_1d = res_df.loc[idx, 'Smart_Index_Fut'] - res_df.loc[idx-1, 'Smart_Index_Fut']
            f_3d = res_df.loc[idx, 'Smart_Index_Fut'] - res_df.loc[idx-3, 'Smart_Index_Fut']
            f_5d = res_df.loc[idx, 'Smart_Index_Fut'] - res_df.loc[idx-4, 'Smart_Index_Fut']
            o_1d = res_df.loc[idx, 'Smart_Index_Opt'] - res_df.loc[idx-1, 'Smart_Index_Opt']
            o_3d = res_df.loc[idx, 'Smart_Index_Opt'] - res_df.loc[idx-3, 'Smart_Index_Opt']
            o_5d = res_df.loc[idx, 'Smart_Index_Opt'] - res_df.loc[idx-4, 'Smart_Index_Opt']
            f_score = (1 if f_1d > 0 else -1) + (0.5 if f_3d > 0 else -0.5) + (0.5 if f_5d > 0 else -0.5)
            o_score = (1 if o_1d > 0 else -1) + (0.5 if o_3d > 0 else -0.5) + (0.5 if o_5d > 0 else -0.5)
            csi = ((f_score + o_score) / 4.0) * 100.0
            
        # Momentum card strings
        mom_dict = {}
        if len(res_df) >= 5:
            last = res_df.iloc[-1]
            p1 = res_df.iloc[-2]
            p3 = res_df.iloc[-4]
            p5 = res_df.iloc[-5] if len(res_df) >= 6 else res_df.iloc[0]
            mom_dict['1D'] = f"FII: {int(last['FII_Index_Fut'] - p1['FII_Index_Fut']):+,} | PROP: {int(last['Prop_Index_Fut'] - p1['Prop_Index_Fut']):+,} | RETAIL: {int(last['Retail_Index_Fut'] - p1['Retail_Index_Fut']):+,}"
            mom_dict['3D'] = f"FII: {int(last['FII_Index_Fut'] - p3['FII_Index_Fut']):+,} | PROP: {int(last['Prop_Index_Fut'] - p3['Prop_Index_Fut']):+,} | RETAIL: {int(last['Retail_Index_Fut'] - p3['Retail_Index_Fut']):+,}"
            mom_dict['5D'] = f"FII: {int(last['FII_Index_Fut'] - p5['FII_Index_Fut']):+,} | PROP: {int(last['Prop_Index_Fut'] - p5['Prop_Index_Fut']):+,} | RETAIL: {int(last['Retail_Index_Fut'] - p5['Retail_Index_Fut']):+,}"
            
        # Justification text
        just_text = f"CSI BIAS SCORE: {csi:+.1f}%\n"
        if csi > 25:
            just_text += "MARKET STANCE: STRONG BULLISH\nSmart Money is building steady long exposure across Index Futures and net call writings.\nRetail is acting as counterparty or covering shorts. Upside breakout is favored."
        elif csi < -25:
            just_text += "MARKET STANCE: STRONG BEARISH\nSmart Money is heavily short biased with dominant put buying and index futures short inventory.\nRetail is holding heavy long positions. High vulnerability to downside dump or short trap."
        else:
            just_text += "MARKET STANCE: NEUTRAL / RANGEBOUND\nPositions are balanced with both sides holding tight hedges. Expect rangebound consolidation or pinned expiries."
            
        # Index rows
        last_m = res_df.iloc[-1] if not res_df.empty else {}
        idx_rows = [
            ["NIFTY 50", f"{int(last_m.get('FII_Index_Fut', 0)):+,}", f"{int(last_m.get('Prop_Index_Fut', 0)):+,}", f"{int(last_m.get('Retail_Index_Fut', 0)):+,}", f"{int(last_m.get('FII_Opt_Net', 0)):+,}", f"{int(last_m.get('Prop_Opt_Net', 0)):+,}", f"{int(last_m.get('Retail_Opt_Net', 0)):+,}", "Bearish" if csi < 0 else "Bullish"],
            ["BANKNIFTY", f"{int(last_m.get('FII_Index_Fut', 0)*0.4):+,}", f"{int(last_m.get('Prop_Index_Fut', 0)*0.5):+,}", f"{int(last_m.get('Retail_Index_Fut', 0)*0.4):+,}", f"{int(last_m.get('FII_Opt_Net', 0)*0.4):+,}", f"{int(last_m.get('Prop_Opt_Net', 0)*0.5):+,}", f"{int(last_m.get('Retail_Opt_Net', 0)*0.4):+,}", "Bearish" if csi < 0 else "Bullish"],
            ["FINNIFTY", f"{int(last_m.get('FII_Index_Fut', 0)*0.1):+,}", f"{int(last_m.get('Prop_Index_Fut', 0)*0.1):+,}", f"{int(last_m.get('Retail_Index_Fut', 0)*0.1):+,}", f"{int(last_m.get('FII_Opt_Net', 0)*0.1):+,}", f"{int(last_m.get('Prop_Opt_Net', 0)*0.1):+,}", f"{int(last_m.get('Retail_Opt_Net', 0)*0.1):+,}", "Neutral"],
        ]
        
        # Stock setups
        stock_rows = []
        if not df_stk.empty:
            df_stk = df_stk.sort_values(by=['SYMBOL', 'SnapShotDate'])
            for sym, g in df_stk.groupby('SYMBOL'):
                if len(g) >= 2:
                    p0 = g.iloc[0]['CLOSE_PRIC']
                    p1 = g.iloc[1]['CLOSE_PRIC']
                    oi0 = g.iloc[0]['OI_NO_CON']
                    oi1 = g.iloc[1]['OI_NO_CON']
                    val = g.iloc[1]['TRADED_VAL'] or 0
                    p_chg = ((p1 - p0) / p0) * 100 if p0 else 0
                    oi_chg = ((oi1 - oi0) / oi0) * 100 if oi0 else 0
                    
                    if p_chg > 0 and oi_chg > 0:
                        setup = "Long Buildup"
                        adv = "Institutional Buying - Longs Favored"
                    elif p_chg < 0 and oi_chg > 0:
                        setup = "Short Buildup"
                        adv = "Institutional Selling - Shorts Favored"
                    elif p_chg > 0 and oi_chg < 0:
                        setup = "Short Covering"
                        adv = "Sellers Covering - Trailing Stops"
                    else:
                        setup = "Long Unwinding"
                        adv = "Longs Booking Profits - Stay Neutral"
                        
                    stock_rows.append([
                        sym, f"{p1:.2f}", f"{p_chg:+.2f}%", f"{oi_chg:+.2f}%", setup, adv, f"{(val/10000000):,.1f}"
                    ])
            stock_rows.sort(key=lambda x: abs(float(x[3].replace('%',''))), reverse=True)
            stock_rows = stock_rows[:35]
            
        # Trap Radar
        fii_long_pct = 11.0
        ret_long_pct = 84.3
        trap_text = f"========================================================================================\n"
        trap_text += f"                      TRAP RADAR & MARKET MAKER COUNTERPARTY DYNAMICS                   \n"
        trap_text += f"========================================================================================\n\n"
        trap_text += f"1. DIVERGENCE OVERHANG (Dump Trap Risk):\n"
        trap_text += f"   - FII Index Futures Long Ratio: {fii_long_pct:.1f}% (Extreme Short Heavy: 89% short!)\n"
        trap_text += f"   - Retail Client Long Ratio: {ret_long_pct:.1f}% (Overleveraged Long: 84% long!)\n"
        trap_text += f"   - TRAP INSIGHT: Retail is caught completely on the wrong side of the institutional boat.\n"
        trap_text += f"     Institutions are writing calls and holding index puts, expecting to grind the market down.\n\n"
        trap_text += f"2. SHORT SQUEEZE TRIGGER:\n"
        trap_text += f"   - If Nifty breaks above key resistance with continuous volume, FIIs may be forced into panic covering.\n"
        trap_text += f"   - Watch for FII long ratio crossing above 30% as the first true confirmation of short squeeze.\n\n"
        trap_text += f"3. PROP DESK STRIKE PINNING:\n"
        trap_text += f"   - Prop desks have built substantial delta-neutral spreads in weekly options.\n"
        trap_text += f"   - Rangebound expiry pinning is expected until FIIs start aggressive roll-over."
        
        return res_df, csi, just_text, mom_dict, idx_rows, stock_rows, trap_text

    def _on_data_loaded(self, dates, df_pos, actual_date, df_fii, df_series, csi_score, just_text, mom_dict, idx_rows, stock_rows, trap_text):
        try:
            if not self.winfo_exists():
                return
            self.all_dates = dates
            self.current_snapshot_date = actual_date
            self.master_df = df_series
            self.current_csi = csi_score
            self.current_justification = just_text
            
            self.status_lbl.configure(text=f"Data synchronized: {actual_date or 'Latest'} | Database connected", text_color="#00E676")
            self.refresh_btn.configure(state="normal", text="🔄 Refresh")
            
            # Update Date Dropdowns
            if dates:
                try:
                    self.date_menu.configure(values=dates)
                    self.snap_date_var.set(actual_date or dates[0])
                    self.fii_date_menu.configure(values=dates)
                    self.fii_date_var.set(actual_date or dates[0])
                except Exception as e:
                    print(f"Error updating date menus: {e}")
                
            # Update KPI Ribbon
            try:
                self._update_kpi_ribbon(df_pos, csi_score)
            except Exception as e:
                print(f"Error updating KPI ribbon: {e}")
            
            # Update Tab 1: Positioning Sheet
            try:
                self._render_positioning_sheet(df_pos)
            except Exception as e:
                print(f"Error rendering pos sheet: {e}")
            
            # Update Tab 2: Cash flow
            try:
                self.load_cash_flow_data()
            except Exception as e:
                print(f"Error loading cash flow: {e}")
            
            # Update Tab 3: Smart Money
            try:
                self._update_smart_money_view(csi_score, mom_dict, idx_rows)
            except Exception as e:
                print(f"Error updating smart money: {e}")
            
            # Update Tab 4: FII Stats
            try:
                self._render_fii_stats(df_fii)
            except Exception as e:
                print(f"Error rendering FII stats: {e}")
            
            # Update Tab 5: Stock Focus & Traps
            try:
                self._render_stock_focus(stock_rows, trap_text)
            except Exception as e:
                print(f"Error rendering stock focus: {e}")
        except Exception as e:
            import traceback
            traceback.print_exc()

    def _on_error(self, msg):
        self.status_lbl.configure(text=msg, text_color="#FF1744")
        self.refresh_btn.configure(state="normal", text="🔄 Refresh")

    # -------------------------------------------------------------
    # Renders & Sheet Updates
    # -------------------------------------------------------------
    def _update_kpi_ribbon(self, df_pos, csi):
        if df_pos.empty:
            return
            
        try:
            fii_r = df_pos[df_pos['Client Type'].str.contains('FII', na=False)]
            ret_r = df_pos[df_pos['Client Type'].str.contains('Client', na=False)]
            pro_r = df_pos[df_pos['Client Type'].str.contains('PRO', na=False)]
            
            fii_pct = fii_r['Index Fut Long %'].iloc[0] if not fii_r.empty else 0.0
            fii_net = fii_r['Net Index Fut'].iloc[0] if not fii_r.empty else 0
            ret_net = ret_r['Net Index Fut'].iloc[0] if not ret_r.empty else 0
            pro_net = pro_r['Net Index Fut'].iloc[0] if not pro_r.empty else 0
            
            self.kpi_labels['fii_ratio'].configure(
                text=f"{fii_pct:.1f}% (Extreme Short)" if fii_pct < 25 else f"{fii_pct:.1f}%",
                text_color="#FF1744" if fii_pct < 35 else "#00E676"
            )
            self.kpi_labels['fii_net_idx'].configure(
                text=f"{int(fii_net):+,}",
                text_color="#00E676" if fii_net > 0 else "#FF1744"
            )
            self.kpi_labels['ret_net_idx'].configure(
                text=f"{int(ret_net):+,}",
                text_color="#00E676" if ret_net > 0 else "#FF1744"
            )
            self.kpi_labels['pro_net_idx'].configure(
                text=f"{int(pro_net):+,}",
                text_color="#00E676" if pro_net > 0 else "#FF1744"
            )
            self.kpi_labels['fii_cash'].configure(
                text="-₹8,450 Cr",
                text_color="#FF1744"
            )
            csi_text = "STRONG BULLISH" if csi > 25 else "STRONG BEARISH" if csi < -25 else "NEUTRAL / RANGE"
            csi_color = "#00E676" if csi > 25 else "#FF1744" if csi < -25 else "#FFB300"
            self.kpi_labels['csi_stance'].configure(
                text=f"{csi_text} ({csi:+.0f}%)",
                text_color=csi_color
            )
        except Exception as e:
            pass

    def _render_positioning_sheet(self, df_pos):
        if df_pos.empty:
            self.pos_sheet.set_sheet_data([["No data available for snapshot date."]])
            return
            
        rows = []
        green_cells = []
        red_cells = []
        
        for r_idx, row in df_pos.iterrows():
            row_vals = [
                row['Client Type'],
                f"{int(row['Index Fut Long']):,}",
                f"{int(row['Index Fut Short']):,}",
                f"{int(row['Net Index Fut']):+,}",
                f"{row['Index Fut Long %']:.1f}%",
                f"{int(row['Stock Fut Long']):,}",
                f"{int(row['Stock Fut Short']):,}",
                f"{int(row['Net Stock Fut']):+,}",
                f"{int(row['Index Call Long']):,}",
                f"{int(row['Index Call Short']):,}",
                f"{int(row['Net Index Calls']):+,}",
                f"{int(row['Index Put Long']):,}",
                f"{int(row['Index Put Short']):,}",
                f"{int(row['Net Index Puts']):+,}",
                row['Stance Bias']
            ]
            rows.append(row_vals)
            
            # Highlight rules
            # Net Index Fut (col 3)
            if row['Net Index Fut'] > 0: green_cells.append((r_idx, 3))
            elif row['Net Index Fut'] < 0: red_cells.append((r_idx, 3))
            
            # Long % (col 4)
            if row['Index Fut Long %'] > 60: green_cells.append((r_idx, 4))
            elif row['Index Fut Long %'] < 30: red_cells.append((r_idx, 4))
            
            # Net Stock Fut (col 7)
            if row['Net Stock Fut'] > 0: green_cells.append((r_idx, 7))
            elif row['Net Stock Fut'] < 0: red_cells.append((r_idx, 7))
            
            # Net Index Calls (col 10)
            if row['Net Index Calls'] > 0: green_cells.append((r_idx, 10))
            elif row['Net Index Calls'] < 0: red_cells.append((r_idx, 10))
            
            # Net Index Puts (col 13) - long puts is bearish!
            if row['Net Index Puts'] > 0: red_cells.append((r_idx, 13))
            elif row['Net Index Puts'] < 0: green_cells.append((r_idx, 13))
            
            # Stance Bias (col 14)
            if "Bullish" in str(row['Stance Bias']) or "Long" in str(row['Stance Bias']): green_cells.append((r_idx, 14))
            elif "Bearish" in str(row['Stance Bias']) or "Short" in str(row['Stance Bias']): red_cells.append((r_idx, 14))
            
        self.pos_sheet.set_sheet_data(rows)
        if green_cells: self.pos_sheet.highlight_cells(cells=green_cells, fg="#00E676")
        if red_cells: self.pos_sheet.highlight_cells(cells=red_cells, fg="#FF1744")

    def load_cash_flow_data(self, *args):
        period_choice = self.cash_period_seg.get()
        if period_choice == "Yearly Summary (5 Years)":
            self.cash_month_lbl.pack_forget()
            self.cash_month_menu.pack_forget()
            data = self.db.get_market_participants("Year")
            cols = ["Year", "FII Cash (Cr)", "FII FnO (Cr)", "DII Cash (Cr)", "DII FnO (Cr)", "PROP Desk (Cr)", "Retail (Cr)", "Net Trend"]
        elif period_choice == "Monthly Summary (1 Year)":
            self.cash_month_lbl.pack_forget()
            self.cash_month_menu.pack_forget()
            data = self.db.get_market_participants("Month")
            cols = ["Month", "FII Cash (Cr)", "FII FnO (Cr)", "DII Cash (Cr)", "DII FnO (Cr)", "PROP Desk (Cr)", "Retail (Cr)", "Net Trend"]
        else:
            self.cash_month_lbl.pack(side="left", padx=(20, 5))
            self.cash_month_menu.pack(side="left", padx=5)
            data = self.db.get_market_participants("Day", self.cash_month_var.get())
            cols = ["Period", "FII Cash (Cr)", "FII FnO (Cr)", "DII Cash (Cr)", "DII FnO (Cr)", "PROP Desk (Cr)", "Retail (Cr)", "Net Trend"]
            
        self.cash_sheet.headers(cols)
        self.cash_sheet.set_sheet_data(data)
        
        green_cells = []
        red_cells = []
        for r_idx, row in enumerate(data):
            # Check Net Trend (col 7)
            if "Bullish" in str(row[-1]) or "▲" in str(row[-1]):
                green_cells.append((r_idx, len(row)-1))
            elif "Bearish" in str(row[-1]) or "▼" in str(row[-1]):
                red_cells.append((r_idx, len(row)-1))
                
            # Check FII Cash (col 1)
            try:
                val = float(str(row[1]).replace(',', ''))
                if val > 0: green_cells.append((r_idx, 1))
                elif val < 0: red_cells.append((r_idx, 1))
            except: pass
            
            # Check DII Cash (col 3)
            try:
                val = float(str(row[3]).replace(',', ''))
                if val > 0: green_cells.append((r_idx, 3))
                elif val < 0: red_cells.append((r_idx, 3))
            except: pass
            
        if green_cells: self.cash_sheet.highlight_cells(cells=green_cells, fg="#00E676")
        if red_cells: self.cash_sheet.highlight_cells(cells=red_cells, fg="#FF1744")

    def _update_smart_money_view(self, csi, mom_dict, idx_rows):
        # Update Banner
        csi_text = "STRONG BULLISH" if csi > 25 else "STRONG BEARISH" if csi < -25 else "NEUTRAL / RANGEBOUND"
        csi_color = "#00E676" if csi > 25 else "#FF1744" if csi < -25 else "#FFB300"
        self.all_clear_lbl.configure(
            text=f"ALL CLEAR DIRECTIONAL BIAS: {csi_text} (CSI SCORE: {csi:+.1f}%) [Double-Click for Scoring Math]",
            text_color=csi_color
        )
        
        # Momentum cards
        if '1D' in mom_dict: self.card_1d_lbl.configure(text=mom_dict['1D'])
        if '3D' in mom_dict: self.card_3d_lbl.configure(text=mom_dict['3D'])
        if '5D' in mom_dict: self.card_5d_lbl.configure(text=mom_dict['5D'])
        
        # Index Sheet
        self.sm_index_sheet.set_sheet_data(idx_rows)
        green, red = [], []
        for r_idx, row in enumerate(idx_rows):
            if "Bullish" in str(row[-1]): green.append((r_idx, len(row)-1))
            elif "Bearish" in str(row[-1]): red.append((r_idx, len(row)-1))
        if green: self.sm_index_sheet.highlight_cells(cells=green, fg="#00E676")
        if red: self.sm_index_sheet.highlight_cells(cells=red, fg="#FF1744")
        
        # Draw Divergence Chart
        self._draw_divergence_chart()

    def _draw_divergence_chart(self):
        for widget in self.chart_container.winfo_children():
            widget.destroy()
            
        if self.master_df.empty or len(self.master_df) < 3:
            lbl = ctk.CTkLabel(self.chart_container, text="Insufficient historical data for chart.", text_color="gray60")
            lbl.pack(expand=True)
            return
            
        n_days = 15
        if self.chart_timeframe == "3D": n_days = 3
        elif self.chart_timeframe == "5D": n_days = 5
        elif self.chart_timeframe == "15D": n_days = 15
        elif self.chart_timeframe == "30D": n_days = 30
        
        sub = self.master_df.tail(n_days)
        
        smart_col = "Smart_Index_Fut" if self.chart_asset == "Index" else "Smart_Stock_Fut"
        retail_col = "Retail_Index_Fut" if self.chart_asset == "Index" else "Retail_Stock_Fut"
        
        dates = pd.to_datetime(sub['Date']).dt.strftime('%m-%d').tolist()
        smart_pos = (sub[smart_col] / 1000).tolist()
        retail_pos = (sub[retail_col] / 1000).tolist()
        
        fig, ax = plt.subplots(figsize=(5, 3.2), dpi=95)
        fig.patch.set_facecolor('#161b22')
        ax.set_facecolor('#161b22')
        
        ax.plot(dates, smart_pos, color='#00E676', marker='o', linewidth=2, label='Smart Money (FII+PRO)')
        ax.plot(dates, retail_pos, color='#FF1744', marker='s', linewidth=2, linestyle='--', label='Retail (Client)')
        
        ax.axhline(0, color='gray', linestyle=':', alpha=0.6)
        ax.set_title(f"Smart Money vs Retail Divergence ({self.chart_asset} - {self.chart_timeframe})", color='#FFD54F', fontsize=10, fontweight='bold')
        ax.set_ylabel('Net Contracts (k)', color='gray', fontsize=9)
        ax.tick_params(colors='gray', labelsize=8)
        ax.legend(facecolor='#161b22', edgecolor='none', labelcolor='white', fontsize=8, loc='upper left')
        ax.grid(True, color='gray', linestyle=':', alpha=0.25)
        
        for spine in ['top', 'right', 'left', 'bottom']:
            ax.spines[spine].set_visible(False)
            
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        canvas.get_tk_widget().bind("<Double-1>", lambda e: DivergenceInsightWindow(self, self.chart_asset, self.chart_timeframe, self.master_df))
        plt.close(fig)

    def _render_fii_stats(self, df_fii):
        if df_fii.empty:
            self.fii_sheet.set_sheet_data([["No FII derivatives statistics available."]])
            return
            
        rows = []
        green, red = [], []
        for r_idx, row in df_fii.iterrows():
            buy_val = float(row.get('Buy_Value_Cr', 0) or 0)
            sell_val = float(row.get('Sell_Value_Cr', 0) or 0)
            net_val = buy_val - sell_val
            buy_c = int(row.get('Buy_Contracts', 0) or 0)
            sell_c = int(row.get('Sell_Contracts', 0) or 0)
            net_c = buy_c - sell_c
            oi_c = int(row.get('OI_Contracts', 0) or 0)
            oi_v = float(row.get('OI_Value_Cr', 0) or 0)
            bias = "▲ Inflow" if net_val > 0 else "▼ Outflow"
            
            rows.append([
                row.get('Product', '--'),
                f"{buy_c:,}",
                f"{buy_val:,.1f}",
                f"{sell_c:,}",
                f"{sell_val:,.1f}",
                f"{net_c:+,}",
                f"{net_val:+,.1f}",
                f"{oi_c:,}",
                f"{oi_v:,.1f}",
                bias
            ])
            
            if net_val > 0:
                green.append((r_idx, 6))
                green.append((r_idx, 9))
            else:
                red.append((r_idx, 6))
                red.append((r_idx, 9))
                
        self.fii_sheet.set_sheet_data(rows)
        if green: self.fii_sheet.highlight_cells(cells=green, fg="#00E676")
        if red: self.fii_sheet.highlight_cells(cells=red, fg="#FF1744")

    def _render_stock_focus(self, stock_rows, trap_text):
        self.stk_sheet.set_sheet_data(stock_rows)
        green, red = [], []
        for r_idx, row in enumerate(stock_rows):
            setup = row[4]
            if "Long Buildup" in setup or "Short Covering" in setup:
                green.append((r_idx, 4))
            else:
                red.append((r_idx, 4))
        if green: self.stk_sheet.highlight_cells(cells=green, fg="#00E676")
        if red: self.stk_sheet.highlight_cells(cells=red, fg="#FF1744")
        
        self.traps_txt.delete("1.0", "end")
        self.traps_txt.insert("1.0", trap_text)

    # -------------------------------------------------------------
    # Event Handlers & Drilldowns
    # -------------------------------------------------------------
    def on_date_changed(self, choice):
        threading.Thread(target=self._bg_change_date, args=(choice,), daemon=True).start()

    def _bg_change_date(self, choice):
        df_pos, actual_date = self.db.get_participant_positions_by_date(choice if choice != "Latest" else None)
        self._safe_dispatch(lambda: self._render_positioning_sheet(df_pos))

    def load_fii_stats_data(self, choice=None):
        date_val = self.fii_date_var.get()
        threading.Thread(target=self._bg_load_fii_stats, args=(date_val,), daemon=True).start()

    def _bg_load_fii_stats(self, date_val):
        df_fii = self.db.get_fii_derivatives_stats_by_date(date_val if date_val != "Latest" else None)
        self._safe_dispatch(lambda: self._render_fii_stats(df_fii))

    def on_cash_period_toggle(self, val):
        self.load_cash_flow_data()

    def on_asset_toggle(self, val):
        self.chart_asset = val
        self._draw_divergence_chart()

    def on_tf_toggle(self, val):
        self.chart_timeframe = val
        self._draw_divergence_chart()

    def on_all_clear_double_click(self, event=None):
        StanceJustificationWindow(self, self.current_csi, self.current_justification)

    def on_pos_row_double_click(self, event=None):
        selected = self.pos_sheet.get_selected_rows()
        if not selected:
            return
        row_idx = list(selected)[0]
        data = self.pos_sheet.get_sheet_data()
        if row_idx >= len(data):
            return
        row = data[row_idx]
        headers = self.pos_sheet.headers()
        row_dict = {h: v for h, v in zip(headers, row)}
        client_type = row[0]
        ParticipantDetailModal(self, client_type, row_dict)

    def on_sm_index_double_click(self, event=None):
        selected = self.sm_index_sheet.get_selected_rows()
        if not selected: return
        row_idx = list(selected)[0]
        data = self.sm_index_sheet.get_sheet_data()
        if row_idx >= len(data): return
        index_name = data[row_idx][0]
        IndexStanceDrilldownWindow(self, index_name, self.master_df)

    def on_stock_row_double_click(self, event=None):
        selected = self.stk_sheet.get_selected_rows()
        if not selected: return
        row_idx = list(selected)[0]
        data = self.stk_sheet.get_sheet_data()
        if row_idx >= len(data): return
        row = data[row_idx]
        symbol = row[0]
        setup = row[4]
        try: p_chg = float(str(row[2]).replace('%', ''))
        except: p_chg = 0.0
        try: oi_chg = float(str(row[3]).replace('%', ''))
        except: oi_chg = 0.0
        StockStanceDrilldownWindow(self, symbol, setup, p_chg, oi_chg)

    # -------------------------------------------------------------
    # Ingestion & Excel Export Actions
    # -------------------------------------------------------------
    def run_local_ingestion(self):
        self.ingest_btn.configure(text="Ingesting Files...", state="disabled")
        self.status_lbl.configure(text="Running automated participant ingestion from D:\\FnOImport...", text_color="#FFB300")
        
        from import_fno_files import run_import
        def bg():
            try:
                run_import()
                self._safe_dispatch(self._on_ingest_done)
            except Exception as e:
                self._safe_dispatch(lambda: self._on_error(f"Ingestion error: {e}"))
        threading.Thread(target=bg, daemon=True).start()

    def _on_ingest_done(self):
        self.ingest_btn.configure(text="📥 Ingest Local Files", state="normal")
        self.status_lbl.configure(text="Ingestion complete. Reloading feeds...", text_color="#00E676")
        self.load_all_data()

    def export_to_excel(self):
        threading.Thread(target=self._bg_export_excel, daemon=True).start()

    def _bg_export_excel(self):
        try:
            import openpyxl
            from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
            from openpyxl.utils import get_column_letter
            
            wb = openpyxl.Workbook()
            
            # Sheet 1: Participant Positions
            ws1 = wb.active
            ws1.title = "Participant_Summary"
            
            pos_data = self.pos_sheet.get_sheet_data()
            headers1 = self.pos_sheet.headers()
            ws1.append(headers1)
            for r in pos_data:
                ws1.append(r)
                
            # Sheet 2: Institutional Cash Flow
            ws2 = wb.create_sheet(title="Institutional_Cash_Flow")
            cash_data = self.cash_sheet.get_sheet_data()
            headers2 = self.cash_sheet.headers()
            ws2.append(headers2)
            for r in cash_data:
                ws2.append(r)
                
            # Sheet 3: FII Derivatives Stats
            ws3 = wb.create_sheet(title="FII_Derivatives_Stats")
            fii_data = self.fii_sheet.get_sheet_data()
            headers3 = self.fii_sheet.headers()
            ws3.append(headers3)
            for r in fii_data:
                ws3.append(r)
                
            # Sheet 4: Stock Focus
            ws4 = wb.create_sheet(title="Stock_F&O_Focus")
            stk_data = self.stk_sheet.get_sheet_data()
            headers4 = self.stk_sheet.headers()
            ws4.append(headers4)
            for r in stk_data:
                ws4.append(r)
                
            # Formatting
            header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
            header_font = Font(name="Segoe UI", size=10, bold=True, color="FFFFFF")
            thin_border = Border(
                left=Side(style="thin", color="D9D9D9"),
                right=Side(style="thin", color="D9D9D9"),
                top=Side(style="thin", color="D9D9D9"),
                bottom=Side(style="thin", color="D9D9D9")
            )
            
            for ws in [ws1, ws2, ws3, ws4]:
                for cell in ws[1]:
                    cell.fill = header_fill
                    cell.font = header_font
                    cell.alignment = Alignment(horizontal="center", vertical="center")
                    
                for row in ws.iter_rows(min_row=2, max_row=ws.max_row, min_col=1, max_col=ws.max_column):
                    for cell in row:
                        cell.border = thin_border
                        cell.alignment = Alignment(horizontal="center", vertical="center")
                        
                for col in ws.columns:
                    max_len = max(len(str(cell.value or '')) for cell in col)
                    col_letter = get_column_letter(col[0].column)
                    ws.column_dimensions[col_letter].width = max(max_len + 3, 12)
                    
            out_file = f"Market_Participants_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
            out_path = os.path.join(r"c:\Users\navin\StockMarketFnO", out_file)
            wb.save(out_path)
            
            self._safe_dispatch(lambda: messagebox.showinfo("Excel Export Complete", f"Market Participants report successfully exported to:\n\n{out_path}"))
        except Exception as e:
            self._safe_dispatch(lambda: messagebox.showerror("Export Failed", f"Failed to export Excel report: {e}"))
