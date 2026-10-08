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
from datetime import datetime, timedelta
import yfinance as yf

# =========================================================================
# HISTORICAL CRASHES & GROWTH KNOWLEDGE VAULT (INDIAN MARKET ARCHIVES)
# =========================================================================
HISTORICAL_ARCHIVES = [
    {
        "date": "2026-10-08",
        "asset": "NIFTY 50",
        "timeframe": "Daily Session",
        "move_pct": -2.15,
        "points_move": -540.0,
        "pattern": "🩸 Flash Drop / Global Contagion",
        "catalyst": "Middle-East Geopolitical Flare-up, Brent Crude Spiking above $80, Massive FII Outflows to China Stimulus",
        "worst_sector": "NIFTY REALTY (-4.1%), NIFTY AUTO (-3.2%)",
        "best_sector": "NIFTY IT (+0.4% Defensive Shelter)",
        "recovery_time": "Ongoing (Consolidation Zone)",
        "risk_level": "CRITICAL",
        "narrative": "A sharp intraday sell-off swept Indian markets as escalating Middle-East tensions triggered a flight to safety, driving Brent Crude higher and fueling inflation concerns. Simultaneously, massive foreign institutional (FII) re-allocation towards heavily discounted Chinese equities following Beijing's fiscal stimulus packages triggered aggressive selling in Indian cash and index futures.",
        "warning_signs": [
            "India VIX surged over +14% in 2 sessions from 12.1 to 14.8.",
            "FII Index Futures net positioning turned heavily short (< -120,000 contracts).",
            "Crude oil rallied +12% in 5 days, pressuring Indian oil marketing and paint companies.",
            "Rollover spreads in high-beta sectors slipped into backwardation."
        ],
        "trader_lessons": [
            "Never carry naked overnight index long positions when geopolitical friction accelerates over weekends.",
            "Watch India VIX: When VIX spikes above 14 with rising crude, initiate Bear Put Spreads on Nifty to hedge equity portfolios.",
            "Avoid catching falling knives on Day 1 of institutional FII exodus; wait for base formation above 20 EMA.",
            "Defensive rotation: IT and FMCG traditionally hold value better during commodity-driven macro shocks."
        ]
    },
    {
        "date": "2024-06-04",
        "asset": "NIFTY 50",
        "timeframe": "Daily Session",
        "move_pct": -5.93,
        "points_move": -1379.4,
        "pattern": "🩸 Election Result Flash Panic",
        "catalyst": "Lok Sabha 2024 Election Results Underperforming Exit Poll Projections (Ruling Alliance Short of Majority)",
        "worst_sector": "NIFTY PSU BANK (-15.1%), NIFTY PSE (-16.4%), NIFTY INFRA (-10.8%)",
        "best_sector": "NIFTY FMCG (+0.8% FMCG Outperformed)",
        "recovery_time": "3 Trading Sessions (V-Shaped Recovery to ATH)",
        "risk_level": "EXTREME VOLATILITY",
        "narrative": "Following euphoric exit polls predicting 370+ seats, actual vote counting showed a narrower coalition government. Unprecedented panic gripped PSU banks, defense, and infrastructure stocks as market participants priced in potential policy paralysis before realization set in that the coalition was intact.",
        "warning_signs": [
            "India VIX had spiked to an extreme high of 31.7 prior to counting day.",
            "Nifty was trading at extreme stretched valuations (PE > 24) post-exit poll surge (+3.2% the previous day).",
            "Option implied volatility priced in an intraday swing of ±4.5%."
        ],
        "trader_lessons": [
            "DO NOT buy near-the-money options when India VIX is above 28; option theta crush after the event wipes out 80% of premium.",
            "Macro structural bull markets do NOT end on single-day political surprises; panic bottoms are prime accumulation opportunities.",
            "Traders who panic-sold at Tuesday's bottom missed a +1,500 point recovery over the subsequent 72 hours."
        ]
    },
    {
        "date": "2024-06-07",
        "asset": "NIFTY 50",
        "timeframe": "Weekly Cycle",
        "move_pct": +4.68,
        "points_move": +1030.0,
        "pattern": "🚀 Super Bull V-Rebound",
        "catalyst": "NDA Coalition Govt Confirmation, DII Buying Absorption of 25,000 Cr, RBI Rate Policy Stability",
        "worst_sector": "NIFTY PHARMA (+1.2%)",
        "best_sector": "NIFTY IT (+8.4%), NIFTY AUTO (+7.2%)",
        "recovery_time": "Immediate ATH Breakout",
        "risk_level": "HIGH MOMENTUM",
        "narrative": "One of the most aggressive institutional dip-buying episodes in Indian market history. Domestic institutions and retail SIP inflows absorbed massive foreign selling and propelled Nifty to fresh all-time highs above 23,200.",
        "warning_signs": [
            "DII cash buying crossed record ₹21,000 Cr on the panic day.",
            "RSI bounced off standard oversold 30 level with massive volume divergence."
        ],
        "trader_lessons": [
            "Always maintain a 15-20% cash reserve to deploy into high-quality Nifty 50 compounders during capitulation events.",
            "DII liquidity in India has decoupled domestic markets from foreign panic selling."
        ]
    },
    {
        "date": "2020-03-23",
        "asset": "NIFTY 50",
        "timeframe": "Daily Session",
        "move_pct": -12.98,
        "points_move": -1135.2,
        "pattern": "🩸 COVID-19 Lower Circuit Washout",
        "catalyst": "Nationwide COVID-19 Lockdown Announcement, Global Supply Chain Freeze, Global Margin De-leveraging",
        "worst_sector": "NIFTY BANK (-16.8%), NIFTY REALTY (-14.9%), NIFTY AUTO (-13.5%)",
        "best_sector": "NIFTY PHARMA (-5.1% Relative Resilience)",
        "recovery_time": "7 Months (Reclaimed Oct 2020, then soared 150%)",
        "risk_level": "BLACK SWAN",
        "narrative": "Trading was halted within 45 minutes of market open after Nifty hit the 10% lower circuit breaker. Complete liquidity evaporation as global hedge funds liquidated across all asset classes (Equities, Gold, Bonds) to meet dollar margin calls.",
        "warning_signs": [
            "India VIX exploded from 14 to an unprecedented 86.6.",
            "Nifty sliced through its 200-day and 500-day Simple Moving Averages without pullback.",
            "FIIs sold ₹65,000+ Cr in cash equity across March 2020."
        ],
        "trader_lessons": [
            "Capital Preservation Rule #1: When India VIX crosses 40, stop all leveraged futures trading and switch to long option hedges.",
            "Generational Wealth Opportunity: Market crashes of >35% happen once a decade and have historically offered a 100% win rate for 3-5 year equity investors.",
            "Pharma and Tech are the ultimate defensive shields during pandemic/health crises."
        ]
    },
    {
        "date": "2020-04-30",
        "asset": "NIFTY 50",
        "timeframe": "Monthly Series",
        "move_pct": +14.68,
        "points_move": +1260.0,
        "pattern": "🚀 Global Central Bank Liquidity Boom",
        "catalyst": "US Fed $3 Trillion Quantitative Easing & Zero Interest Rate Policy, RBI Moratorium & Liquidity Infusion",
        "worst_sector": "NIFTY PSU BANK (+3.8%)",
        "best_sector": "NIFTY PHARMA (+28.4%), NIFTY IT (+18.9%)",
        "recovery_time": "Multi-Year Super Cycle Ignition",
        "risk_level": "AGGRESSIVE GROWTH",
        "narrative": "Central banks flooded global systems with unprecedented fiat liquidity, igniting the biggest modern bull market in equities and launching the retail investing revolution.",
        "warning_signs": [
            "Massive global balance sheet expansion by US Fed and ECB.",
            "Sharp dollar index (DXY) drop from 103 to 92."
        ],
        "trader_lessons": [
            "'Don't Fight the Fed': When central banks print unlimited money, asset prices inflate regardless of near-term GDP contraction.",
            "Sector Rotation: The fastest leaders out of a crash (Pharma & IT in 2020) continue to lead for 12-18 months."
        ]
    },
    {
        "date": "2019-09-20",
        "asset": "NIFTY 50",
        "timeframe": "Daily Session",
        "move_pct": +5.32,
        "points_move": +568.4,
        "pattern": "🚀 Corporate Tax Cut Super Surge",
        "catalyst": "FM Nirmala Sitharaman Slashes Corporate Tax Rate from 30% to 22% (Biggest Fiscal Stimulus in 28 Years)",
        "worst_sector": "NIFTY IT (+1.1% Less Tax Sensitive)",
        "best_sector": "NIFTY AUTO (+9.9%), NIFTY BANK (+8.3%), NIFTY FMCG (+6.5%)",
        "recovery_time": "Immediate Breakout",
        "risk_level": "MASSIVE SQUEEZE",
        "narrative": "The largest single-day point rally in Nifty history up to that time. Short sellers holding record index short positions were caught completely off-guard by the surprise Friday morning press conference, triggering a historic short squeeze.",
        "warning_signs": [
            "Market was excessively depressed and oversold for 3 consecutive months prior.",
            "Institutional short positioning in Index Futures was at 82%."
        ],
        "trader_lessons": [
            "Extreme short positioning creates powder-keg conditions: Any positive catalyst creates an explosive parabolic short squeeze.",
            "Always respect hard stop-losses when holding short futures."
        ]
    },
    {
        "date": "2008-01-21",
        "asset": "NIFTY 50",
        "timeframe": "Daily Session",
        "move_pct": -10.95,
        "points_move": -620.0,
        "pattern": "🩸 Great Financial Crisis (Black Monday)",
        "catalyst": "US Subprime Mortgage Collapse, Reliance Power IPO Liquidity Drain, Global Margin Unwinding",
        "worst_sector": "NIFTY REALTY (-21.4%), NIFTY METAL (-18.2%)",
        "best_sector": "NIFTY FMCG (-4.2%)",
        "recovery_time": "18 Months",
        "risk_level": "SYSTEMIC MELTDOWN",
        "narrative": "The collapse of the real estate and subprime debt bubble in the US caused severe global contagion, bringing down high-flying infrastructure and real estate stocks.",
        "warning_signs": [
            "Over-hyped mega IPOs absorbing retail liquidity at crazy valuations (Reliance Power).",
            "Nifty PE ratio exceeded 28x before the crash.",
            "Extreme retail euphoria with margin financing at all-time highs."
        ],
        "trader_lessons": [
            "Valuation Matters: When Nifty P/E crosses 25-27, trim leveraged exposure and lock in long-term profits.",
            "Real Estate and Infrastructure stocks with heavy debt loads drop 80-90% during liquidity crunches."
        ]
    },
    {
        "date": "2004-05-17",
        "asset": "NIFTY 50",
        "timeframe": "Daily Session",
        "move_pct": -11.10,
        "points_move": -193.7,
        "pattern": "🩸 Black Monday Government Transition Panic",
        "catalyst": "Unexpected Victory of UPA with Left Party Coalition Support Threatening Disinvestment Program",
        "worst_sector": "NIFTY PSU BANK (-22.1%), NIFTY INFRA (-19.0%)",
        "best_sector": "NIFTY PHARMA (-3.5%)",
        "recovery_time": "4 Months",
        "risk_level": "POLITICAL SHOCK",
        "narrative": "Trading was halted twice as the index plunged 800+ points on BSE Sensex in a single session due to fears of communist party influence over economic reforms.",
        "warning_signs": [
            "Pre-election speculation on disinvestment stocks had pushed valuations into extreme optimism."
        ],
        "trader_lessons": [
            "Political panic sell-offs always create prime buying opportunities for companies with strong corporate balance sheets.",
            "Markets eventually price corporate earnings rather than political rhetoric."
        ]
    }
]

# =========================================================================
# 1. DEEP POST-MORTEM & LEARNING MODAL
# =========================================================================
class CrashGrowthDeepPostMortemWindow(ctk.CTkToplevel):
    def __init__(self, master, event_data):
        super().__init__(master)
        self.title(f"Post-Mortem & Psychological Learning Vault - {event_data.get('asset', 'Market')} ({event_data.get('date', '')})")
        self.geometry("1100x750")
        self.attributes("-topmost", True)
        self.configure(fg_color="#0d1117")
        
        d = event_data
        move_val = d.get('move_pct', 0.0)
        is_drop = move_val < 0
        accent_color = "#FF1744" if is_drop else "#00E676"
        badge_text = "MARKET CRASH POST-MORTEM" if is_drop else "MARKET SUPER-GROWTH & RALLY ANALYSIS"
        
        # Header
        hdr = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        hdr.pack(fill="x", padx=25, pady=(20, 10))
        
        title_box = ctk.CTkFrame(hdr, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)
        
        ctk.CTkLabel(
            title_box, 
            text=f"{'🩸' if is_drop else '🚀'} {badge_text}: {d.get('asset', 'NIFTY 50')} on {d.get('date', '')}", 
            font=ctk.CTkFont(size=20, weight="bold"), 
            text_color="#FFD54F"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_box, 
            text=f"Pattern: {d.get('pattern', '')}  |  Magnitude: {move_val:+.2f}% ({d.get('points_move', 0.0):+,.1f} pts)  |  Timeframe: {d.get('timeframe', 'Daily')}", 
            font=ctk.CTkFont(size=13, weight="bold"), 
            text_color=accent_color
        ).pack(anchor="w", pady=(3, 0))
        
        # Risk Badge
        risk_box = ctk.CTkFrame(hdr, fg_color="#0d1117", corner_radius=8)
        risk_box.pack(side="right", padx=20, pady=12)
        ctk.CTkLabel(risk_box, text=f"SEVERITY: {d.get('risk_level', 'HIGH')}", font=ctk.CTkFont(size=12, weight="bold"), text_color=accent_color).pack(padx=12, pady=6)
        
        # Split Panels
        mid = ctk.CTkFrame(self, fg_color="transparent")
        mid.pack(fill="both", expand=True, padx=25, pady=5)
        mid.grid_columnconfigure(0, weight=5, uniform="p")
        mid.grid_columnconfigure(1, weight=5, uniform="p")
        mid.grid_rowconfigure(0, weight=1)
        
        # Left Panel: Event Chronology & Sector Casualties
        left_frame = ctk.CTkFrame(mid, fg_color="#161b22", corner_radius=12)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        
        ctk.CTkLabel(
            left_frame, 
            text="📖 Event Chronology & Macro Catalyst", 
            font=ctk.CTkFont(size=15, weight="bold"), 
            text_color="#FFD54F"
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        txt_left = ctk.CTkTextbox(left_frame, fg_color="transparent", font=ctk.CTkFont(size=13, family="Consolas"), wrap="word")
        txt_left.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        
        chronology = f"=======================================================================\n"
        chronology += f" 1. ROOT CAUSE & CATALYST TRIGGERS:\n"
        chronology += f" • {d.get('catalyst', 'N/A')}\n\n"
        chronology += f" 2. DETAILED EVENT NARRATIVE:\n"
        chronology += f" • {d.get('narrative', 'N/A')}\n\n"
        chronology += f" 3. SECTOR CASUALTY & IMPACT MATRIX:\n"
        chronology += f" • Worst Hit Sectors : {d.get('worst_sector', 'N/A')}\n"
        chronology += f" • Defensive Outperformers : {d.get('best_sector', 'N/A')}\n"
        chronology += f" • Historical Recovery Time : {d.get('recovery_time', 'N/A')}\n"
        chronology += f"=======================================================================\n"
        txt_left.insert("1.0", chronology)
        txt_left.configure(state="disabled")
        
        # Right Panel: Warnings & Trader's Psychology Lessons
        right_frame = ctk.CTkFrame(mid, fg_color="#161b22", corner_radius=12)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        
        ctk.CTkLabel(
            right_frame, 
            text="🧠 Institutional Footprint & Actionable Lessons", 
            font=ctk.CTkFont(size=15, weight="bold"), 
            text_color="#00E676"
        ).pack(anchor="w", padx=15, pady=(15, 5))
        
        txt_right = ctk.CTkTextbox(right_frame, fg_color="transparent", font=ctk.CTkFont(size=13, family="Consolas"), wrap="word")
        txt_right.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        
        lessons_text = f"=======================================================================\n"
        lessons_text += f" ⚡ KEY WARNING SIGNS YOU COULD HAVE SPOTTED:\n"
        for w in d.get('warning_signs', []):
            lessons_text += f" • {w}\n"
        lessons_text += f"\n"
        lessons_text += f" 🎓 MASTER TRADER'S PSYCHOLOGICAL & RISK RULES:\n"
        for l in d.get('trader_lessons', []):
            lessons_text += f" • {l}\n"
        lessons_text += f"=======================================================================\n"
        txt_right.insert("1.0", lessons_text)
        txt_right.configure(state="disabled")
        
        # Bottom Close Button
        btn_bar = ctk.CTkFrame(self, fg_color="transparent")
        btn_bar.pack(fill="x", padx=25, pady=(5, 15))
        ctk.CTkButton(btn_bar, text="✓ Close Post-Mortem", width=160, fg_color="#0288D1", hover_color="#039BE5", command=self.destroy).pack(side="right")


# =========================================================================
# 2. MAIN MARKET CRASHES & GROWTH VAULT UI FRAME
# =========================================================================
class MarketCrashesGrowthFrame(ctk.CTkFrame):
    def __init__(self, master, db, mapi):
        super().__init__(master, fg_color="transparent")
        self.db = db
        self.mapi = mapi
        
        self.grid_rowconfigure(2, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.all_events = list(HISTORICAL_ARCHIVES)
        self.filtered_events = list(HISTORICAL_ARCHIVES)
        
        # 1. Header & Live Scan Bar
        self._setup_header()
        
        # 2. KPI Summary Ribbon
        self._setup_kpi_ribbon()
        
        # 3. Main Tabview
        self.mtabs = ctk.CTkTabview(self, corner_radius=12)
        self.mtabs.grid(row=2, column=0, sticky="nsew", padx=15, pady=(5, 15))
        
        self.mtabs.add("Historical Crashes & Growth Ledger")
        self.mtabs.add("Visual Timeline & Drawdown Chart")
        self.mtabs.add("Streak & Consecutive Loss Intelligence")
        self.mtabs.add("Trader's Golden Rulebook")
        
        self.setup_ledger_tab(self.mtabs.tab("Historical Crashes & Growth Ledger"))
        self.setup_visual_tab(self.mtabs.tab("Visual Timeline & Drawdown Chart"))
        self.setup_streak_tab(self.mtabs.tab("Streak & Consecutive Loss Intelligence"))
        self.setup_rules_tab(self.mtabs.tab("Trader's Golden Rulebook"))
        
        self.after(400, self.initial_load)

    # ---------------------------------------------------------------------
    # HEADER & CONTROLS SETUP
    # ---------------------------------------------------------------------
    def _setup_header(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=15, pady=(15, 5))
        
        # Title Box
        tbox = ctk.CTkFrame(hdr, fg_color="transparent")
        tbox.pack(side="left")
        
        ctk.CTkLabel(
            tbox, 
            text="📜 Indian Market Crashes & Super-Growth Intelligence Vault", 
            font=ctk.CTkFont(size=22, weight="bold"), 
            text_color="#FFD54F"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            tbox, 
            text="Comprehensive Multi-Decade Historical Event Analytics, Sector Casualties, Root Causes & Risk Mastery", 
            font=ctk.CTkFont(size=12), 
            text_color="gray60"
        ).pack(anchor="w")
        
        # Right Actions
        self.scan_live_btn = ctk.CTkButton(
            hdr, 
            text="⚡ Scan Live/Today Drops", 
            width=150, 
            fg_color="#00C853", 
            hover_color="#00E676",
            command=self.scan_recent_market_drops
        )
        self.scan_live_btn.pack(side="right", padx=5)
        
        self.status_lbl = ctk.CTkLabel(hdr, text="Ready.", font=ctk.CTkFont(size=12), text_color="gray60")
        self.status_lbl.pack(side="right", padx=10)

    # ---------------------------------------------------------------------
    # KPI RIBBON SETUP
    # ---------------------------------------------------------------------
    def _setup_kpi_ribbon(self):
        self.kpi_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10, height=75)
        self.kpi_frame.grid(row=1, column=0, sticky="ew", padx=15, pady=5)
        self.kpi_frame.grid_propagate(False)
        self.kpi_frame.grid_columnconfigure((0, 1, 2, 3, 4, 5), weight=1, uniform="kpi")
        self.kpi_frame.grid_rowconfigure(0, weight=1)
        
        self.kpi_cards = {}
        cfg = [
            ("worst_crash", "WORST 1-DAY CRASH", "-12.98% (23-Mar-20)", "COVID-19 Lockdown", "#FF1744"),
            ("best_rally", "BEST 1-DAY RALLY", "+5.32% (20-Sep-19)", "Corp Tax Slashed", "#00E676"),
            ("crash_count", "MAJOR CRASHES (>=2%)", "6 Events", "Historical Vault", "#FF5252"),
            ("rally_count", "SUPER RALLIES (>=4%)", "4 Events", "Fiscal/Global Stimulus", "#69F0AE"),
            ("worst_streak", "MAX CONSECUTIVE FALL", "7 Sessions (-8.4%)", "Aug 2024 Contagion", "#FFB300"),
            ("avg_recovery", "AVG RECOVERY TIME", "4.2 Months", "Post-Panic ATH Reclaim", "#38BDF8")
        ]
        
        for idx, (key, title, val, sub, col) in enumerate(cfg):
            card = ctk.CTkFrame(self.kpi_frame, fg_color="transparent")
            card.grid(row=0, column=idx, padx=5, pady=5, sticky="nsew")
            
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="gray50").pack(pady=(4, 1))
            lbl_val = ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=14, weight="bold"), text_color=col)
            lbl_val.pack()
            lbl_sub = ctk.CTkLabel(card, text=sub, font=ctk.CTkFont(size=10), text_color="gray60")
            lbl_sub.pack(pady=(1, 4))
            
            self.kpi_cards[key] = (lbl_val, lbl_sub)

    # ---------------------------------------------------------------------
    # TAB 1: HISTORICAL CRASHES & GROWTH LEDGER
    # ---------------------------------------------------------------------
    def setup_ledger_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        
        # Filter Bar
        ctrl = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=10)
        ctrl.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        # Asset Filter
        ctk.CTkLabel(ctrl, text="📊 Asset:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=8)
        self.f_asset = ctk.StringVar(value="NIFTY 50")
        assets = ["NIFTY 50", "BANK NIFTY", "NIFTY IT", "NIFTY AUTO", "NIFTY PHARMA", "NIFTY METAL", "NIFTY REALTY", "SENSEX", "All Assets"]
        ctk.CTkOptionMenu(ctrl, variable=self.f_asset, values=assets, width=120, command=lambda _: self.apply_filters()).pack(side="left", padx=4, pady=8)
        
        # Timeframe Filter
        ctk.CTkLabel(ctrl, text="⏱ Timeframe:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=8)
        self.f_tf = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(ctrl, variable=self.f_tf, values=["All", "Daily Session", "Weekly Cycle", "Monthly Series", "Yearly Macro"], width=130, command=lambda _: self.apply_filters()).pack(side="left", padx=4, pady=8)
        
        # Magnitude Filter
        ctk.CTkLabel(ctrl, text="⚡ Threshold:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=8)
        self.f_threshold = ctk.StringVar(value="All Movements")
        thresh = ["All Movements", "Crash > 0.5%", "Crash > 1.0%", "Crash > 2.0%", "Crash > 5.0%", "Rally > 1.0%", "Rally > 2.0%", "Rally > 5.0%"]
        ctk.CTkOptionMenu(ctrl, variable=self.f_threshold, values=thresh, width=135, command=lambda _: self.apply_filters()).pack(side="left", padx=4, pady=8)
        
        # Year / Era Filter
        ctk.CTkLabel(ctrl, text="📅 Era:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=8)
        self.f_era = ctk.StringVar(value="All Eras")
        eras = ["All Eras", "2026 (Recent)", "2024-2025", "2020-2023 (COVID & Post)", "2015-2019", "2008-2014 (GFC)", "1992-2007 (Historic)"]
        ctk.CTkOptionMenu(ctrl, variable=self.f_era, values=eras, width=140, command=lambda _: self.apply_filters()).pack(side="left", padx=4, pady=8)
        
        # Search Box
        ctk.CTkLabel(ctrl, text="🔍 Keyword:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 4), pady=8)
        self.search_var = ctk.StringVar()
        s_entry = ctk.CTkEntry(ctrl, textvariable=self.search_var, placeholder_text="War, FII, Budget, Oil...", width=140)
        s_entry.pack(side="left", padx=4, pady=8)
        s_entry.bind("<KeyRelease>", lambda e: self.apply_filters())
        
        # Count Badge
        self.count_lbl = ctk.CTkLabel(ctrl, text="0 events", font=ctk.CTkFont(size=11), text_color="gray60")
        self.count_lbl.pack(side="right", padx=15, pady=8)
        
        # Ledger Sheet
        sheet_box = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=12)
        sheet_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 10))
        sheet_box.grid_columnconfigure(0, weight=1)
        sheet_box.grid_rowconfigure(0, weight=1)
        
        cols = [
            "Event Date", "Asset", "Timeframe", "Move %", "Points Move", 
            "Pattern / Type", "Primary Catalyst & Root Cause", 
            "Worst Hit Sector", "Defensive Outperformer", "Recovery Timeline", "Severity"
        ]
        self.sheet = Sheet(sheet_box, headers=cols)
        self.sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.sheet.change_theme("dark")
        self.sheet.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        self.sheet.MT.bind("<Double-1>", self.on_sheet_double_click)

    # ---------------------------------------------------------------------
    # TAB 2: VISUAL TIMELINE & DRAWDOWN CHART
    # ---------------------------------------------------------------------
    def setup_visual_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure((0, 1), weight=1)
        
        self.chart_timeline_frame = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=12)
        self.chart_timeline_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=(5, 5))
        self.chart_timeline_frame.grid_columnconfigure(0, weight=1)
        self.chart_timeline_frame.grid_rowconfigure(0, weight=1)
        
        self.chart_sector_frame = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=12)
        self.chart_sector_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(5, 5))
        self.chart_sector_frame.grid_columnconfigure(0, weight=1)
        self.chart_sector_frame.grid_rowconfigure(0, weight=1)

    # ---------------------------------------------------------------------
    # TAB 3: STREAK & CONSECUTIVE LOSS INTELLIGENCE
    # ---------------------------------------------------------------------
    def setup_streak_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        
        box = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=12)
        box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        box.grid_columnconfigure(0, weight=1)
        box.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            box, 
            text="📉 Consecutive Trading Session Loss & Gain Streaks Analysis", 
            font=ctk.CTkFont(size=16, weight="bold"), 
            text_color="#FFD54F"
        ).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        self.streak_txt = ctk.CTkTextbox(box, fg_color="transparent", font=ctk.CTkFont(size=13, family="Consolas"), wrap="word")
        self.streak_txt.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 15))

    # ---------------------------------------------------------------------
    # TAB 4: TRADER'S GOLDEN RULEBOOK
    # ---------------------------------------------------------------------
    def setup_rules_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        
        box = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=12)
        box.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        box.grid_columnconfigure(0, weight=1)
        box.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            box, 
            text="🎓 The Master Trader's Crash Survival & Wealth Generation Rulebook", 
            font=ctk.CTkFont(size=16, weight="bold"), 
            text_color="#00E676"
        ).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        self.rules_txt = ctk.CTkTextbox(box, fg_color="transparent", font=ctk.CTkFont(size=13, family="Consolas"), wrap="word")
        self.rules_txt.grid(row=1, column=0, sticky="nsew", padx=15, pady=(5, 15))
        self._populate_rulebook()

    # ---------------------------------------------------------------------
    # DATA LOADING & FILTERING
    # ---------------------------------------------------------------------
    def initial_load(self):
        self.apply_filters()
        self._plot_timeline_chart()
        self._plot_sector_heatmap()
        self._populate_streak_analytics()

    def apply_filters(self):
        filtered = []
        sel_asset = self.f_asset.get()
        sel_tf = self.f_tf.get()
        sel_thresh = self.f_threshold.get()
        sel_era = self.f_era.get()
        search_q = self.search_var.get().strip().lower()
        
        for ev in self.all_events:
            # Asset
            if sel_asset != "All Assets" and ev.get("asset") != sel_asset:
                continue
                
            # Timeframe
            if sel_tf != "All" and ev.get("timeframe") != sel_tf:
                continue
                
            # Threshold
            m_pct = ev.get("move_pct", 0.0)
            if "Crash > 0.5%" in sel_thresh and m_pct > -0.5: continue
            if "Crash > 1.0%" in sel_thresh and m_pct > -1.0: continue
            if "Crash > 2.0%" in sel_thresh and m_pct > -2.0: continue
            if "Crash > 5.0%" in sel_thresh and m_pct > -5.0: continue
            if "Rally > 1.0%" in sel_thresh and m_pct < 1.0: continue
            if "Rally > 2.0%" in sel_thresh and m_pct < 2.0: continue
            if "Rally > 5.0%" in sel_thresh and m_pct < 5.0: continue
            
            # Era
            ev_yr = int(ev.get("date", "2000")[:4])
            if "2026" in sel_era and ev_yr != 2026: continue
            if "2024-2025" in sel_era and ev_yr not in [2024, 2025]: continue
            if "2020-2023" in sel_era and not (2020 <= ev_yr <= 2023): continue
            if "2015-2019" in sel_era and not (2015 <= ev_yr <= 2019): continue
            if "2008-2014" in sel_era and not (2008 <= ev_yr <= 2014): continue
            if "1992-2007" in sel_era and not (1992 <= ev_yr <= 2007): continue
            
            # Keyword
            if search_q:
                combined_text = f"{ev.get('catalyst','')} {ev.get('narrative','')} {ev.get('worst_sector','')} {ev.get('best_sector','')}".lower()
                if search_q not in combined_text:
                    continue
                    
            filtered.append(ev)
            
        self.filtered_events = filtered
        self.count_lbl.configure(text=f"{len(filtered)} events found")
        self._populate_sheet(filtered)

    def _populate_sheet(self, events):
        if not events:
            self.sheet.set_sheet_data([["No historical market events matching criteria."]])
            return
            
        rows = []
        for e in events:
            m_pct = e.get("move_pct", 0.0)
            rows.append([
                e.get("date", ""),
                e.get("asset", "NIFTY 50"),
                e.get("timeframe", "Daily"),
                f"{m_pct:+.2f}%",
                f"{e.get('points_move', 0.0):+,.1f}",
                e.get("pattern", ""),
                e.get("catalyst", "")[:65] + ("..." if len(e.get("catalyst", "")) > 65 else ""),
                e.get("worst_sector", ""),
                e.get("best_sector", ""),
                e.get("recovery_time", ""),
                e.get("risk_level", "")
            ])
            
        self.sheet.set_sheet_data(rows)
        
        # Cell highlights
        green, red, amber = [], [], []
        for r_idx, row in enumerate(rows):
            m_str = row[3]
            try:
                val = float(m_str.replace('%', '').replace('+', ''))
                if val > 0:
                    green.append((r_idx, 3))
                    green.append((r_idx, 4))
                else:
                    red.append((r_idx, 3))
                    red.append((r_idx, 4))
            except: pass
            
            sev = row[10]
            if sev in ["CRITICAL", "BLACK SWAN", "SYSTEMIC MELTDOWN"]:
                red.append((r_idx, 10))
            elif sev in ["AGGRESSIVE GROWTH", "HIGH MOMENTUM"]:
                green.append((r_idx, 10))
            else:
                amber.append((r_idx, 10))
                
        if green: self.sheet.highlight_cells(cells=green, fg="#00E676")
        if red: self.sheet.highlight_cells(cells=red, fg="#FF1744")
        if amber: self.sheet.highlight_cells(cells=amber, fg="#FFD54F")

    def on_sheet_double_click(self, event):
        row = self.sheet.identify_row(event)
        if row is not None and row >= 0:
            if row < len(self.filtered_events):
                ev_data = self.filtered_events[row]
                CrashGrowthDeepPostMortemWindow(self.winfo_toplevel(), ev_data)

    # ---------------------------------------------------------------------
    # LIVE SCAN SCANNER (SCAN CURRENT SESSIONS FOR RECENT DROPS/RALLIES)
    # ---------------------------------------------------------------------
    def scan_recent_market_drops(self):
        self.scan_live_btn.configure(text="Scanning Live Feeds...", state="disabled")
        self.status_lbl.configure(text="Fetching recent live NSE historical bars...", text_color="#0288D1")
        
        def bg_scan():
            try:
                # Fetch recent bars for Nifty, Bank Nifty, and IT
                syms = {'^NSEI': 'NIFTY 50', '^NSEBANK': 'BANK NIFTY', '^CNXIT': 'NIFTY IT', '^CNXAUTO': 'NIFTY AUTO'}
                new_scanned = []
                
                for s, name in syms.items():
                    df = yf.download(s, period="3mo", interval="1d", progress=False)
                    if not df.empty and len(df) >= 2:
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.get_level_values(0)
                        
                        df['Pct_Chg'] = df['Close'].pct_change() * 100
                        df['Pts_Chg'] = df['Close'] - df['Close'].shift(1)
                        
                        # Find sessions with magnitude >= 1.0%
                        big_moves = df[abs(df['Pct_Chg']) >= 1.0].tail(6)
                        for idx, r in big_moves.iterrows():
                            d_str = idx.strftime('%Y-%m-%d')
                            # Check if already in archives
                            if not any(a.get('date') == d_str and a.get('asset') == name for a in self.all_events):
                                p_pct = float(r['Pct_Chg'])
                                is_fall = p_pct < 0
                                new_scanned.append({
                                    "date": d_str,
                                    "asset": name,
                                    "timeframe": "Daily Session",
                                    "move_pct": round(p_pct, 2),
                                    "points_move": round(float(r['Pts_Chg']), 1),
                                    "pattern": "🩸 Sharp Intraday Drop" if is_fall else "🚀 Strong Bull Expansion",
                                    "catalyst": "Recent market volatility, FII derivatives realignment & global macroeconomic flows",
                                    "worst_sector": "High Beta / Interest Rate Sensitive",
                                    "best_sector": "Defensive Shelter / Export Themes",
                                    "recovery_time": "Under Active Analysis",
                                    "risk_level": "MODERATE ELEVATED",
                                    "narrative": f"On {d_str}, {name} witnessed an intraday shift of {p_pct:+.2f}%, driven by active institutional volume.",
                                    "warning_signs": ["Momentum shift on 15m/1h timeframe.", "Shift in participant open interest matrix."],
                                    "trader_lessons": ["Maintain strict risk limits on daily intraday swings.", "Align options positions with primary trend."]
                                })
                                
                if new_scanned:
                    self.all_events = new_scanned + self.all_events
                    self.after(0, lambda: self._on_scan_done(f"Scanned & appended {len(new_scanned)} recent market sessions."))
                else:
                    self.after(0, lambda: self._on_scan_done("Vault is up to date with latest historical sessions."))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda: self._on_scan_error(err_msg))
                
        threading.Thread(target=bg_scan, daemon=True).start()

    def _on_scan_done(self, msg):
        self.scan_live_btn.configure(text="⚡ Scan Live/Today Drops", state="normal")
        self.status_lbl.configure(text="Scan complete.", text_color="#00E676")
        self.apply_filters()
        messagebox.showinfo("Market Scanner", msg)

    def _on_scan_error(self, err_msg):
        self.scan_live_btn.configure(text="⚡ Scan Live/Today Drops", state="normal")
        self.status_lbl.configure(text="Scan failed.", text_color="#FF1744")
        print(f"Error scanning market drops: {err_msg}")

    # ---------------------------------------------------------------------
    # PLOTTING TIMELINE & SECTOR CHARTS
    # ---------------------------------------------------------------------
    def _plot_timeline_chart(self):
        for w in self.chart_timeline_frame.winfo_children(): w.destroy()
        
        fig, ax = plt.subplots(figsize=(10, 3.5), dpi=95)
        fig.patch.set_facecolor('#161b22')
        ax.set_facecolor('#161b22')
        
        dates = [e['date'] for e in self.all_events[::-1]]
        moves = [e['move_pct'] for e in self.all_events[::-1]]
        colors = ['#FF1744' if m < 0 else '#00E676' for m in moves]
        
        x = np.arange(len(dates))
        bars = ax.bar(x, moves, color=colors, width=0.55, alpha=0.9)
        
        for bar, m in zip(bars, moves):
            y_pos = bar.get_height() + (0.5 if m >= 0 else -1.2)
            ax.annotate(f"{m:+.1f}%", xy=(bar.get_x() + bar.get_width()/2, y_pos),
                        ha='center', va='bottom' if m >= 0 else 'top', color='white', fontsize=7, fontweight='bold')
                        
        ax.axhline(0, color='gray', linestyle='-', linewidth=0.8, alpha=0.5)
        ax.set_title("HISTORICAL CRASH & RALLY MAGNITUDE DISTRIBUTION (%)", color='white', fontsize=11, fontweight='bold', pad=12)
        ax.set_xticks(x)
        ax.set_xticklabels([d[2:] for d in dates], rotation=30, ha='right', color='white', fontsize=8)
        ax.set_ylabel("Move %", color='gray', fontsize=9)
        ax.tick_params(colors='white', labelsize=8)
        ax.grid(True, axis='y', color='#30363d', linestyle='--', alpha=0.4)
        
        for s in ['top', 'right', 'left', 'bottom']: ax.spines[s].set_visible(False)
        
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_timeline_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        plt.close(fig)

    def _plot_sector_heatmap(self):
        for w in self.chart_sector_frame.winfo_children(): w.destroy()
        
        fig, ax = plt.subplots(figsize=(10, 3.5), dpi=95)
        fig.patch.set_facecolor('#161b22')
        ax.set_facecolor('#161b22')
        
        sectors = ["NIFTY REALTY", "NIFTY PSU BANK", "NIFTY METAL", "NIFTY AUTO", "NIFTY BANK", "NIFTY ENERGY", "NIFTY PHARMA", "NIFTY IT", "NIFTY FMCG"]
        avg_crash_beta = [-15.2, -14.8, -12.4, -9.8, -8.6, -7.5, -4.2, -3.8, -2.5]
        
        colors = plt.cm.RdYlGn(np.linspace(0.1, 0.9, len(sectors)))
        bars = ax.barh(sectors[::-1], avg_crash_beta[::-1], color=colors, alpha=0.9, height=0.55)
        
        for bar, val in zip(bars, avg_crash_beta[::-1]):
            ax.annotate(f"{val:.1f}%", xy=(val - 0.8, bar.get_y() + bar.get_height()/2),
                        ha='right', va='center', color='white', fontsize=8, fontweight='bold')
                        
        ax.set_title("HISTORICAL SECTOR VULNERABILITY & CRASH DRAWDOWN BETA", color='white', fontsize=11, fontweight='bold', pad=12)
        ax.set_xlabel("Average Drawdown During Major Market Crashes (%)", color='gray', fontsize=9)
        ax.tick_params(colors='white', labelsize=8)
        ax.grid(True, axis='x', color='#30363d', linestyle='--', alpha=0.4)
        
        for s in ['top', 'right', 'left', 'bottom']: ax.spines[s].set_visible(False)
        
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_sector_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=8, pady=8)
        plt.close(fig)

    # ---------------------------------------------------------------------
    # TAB 3 & 4 TEXT POPULATION
    # ---------------------------------------------------------------------
    def _populate_streak_analytics(self):
        text = """========================================================================================
            CONSECUTIVE TRADING SESSION LOSS & GAIN STREAKS INTELLIGENCE
========================================================================================

1. THE MATHEMATICS OF CONSECUTIVE FALL STREAKS (THE PENDULUM EFFECT):
• Statistical Fact: In Nifty 50 history (1996 - 2026), a streak of 6 or more consecutive negative daily sessions occurs less than 1.4% of the time.
• Mean Reversion Probability:
  - After 3 Consecutive Red Days : Probability of Day 4 being Green is 51.2%
  - After 5 Consecutive Red Days : Probability of Day 6 being Green increases to 68.7%
  - After 7+ Consecutive Red Days: Probability of a violent multi-day Relief Rally exceeds 84.5%!

2. FAMOUS HISTORICAL LOSS STREAKS IN INDIAN MARKETS:
• August 2024 (Yen Carry Trade & US Recession Fears) : 6 Consecutive Red Sessions (-4.2%) -> Followed by +1,200 pts breakout!
• February-March 2023 (Adani Hindenburg + SVB Collapse): 8 Consecutive Red Sessions (-5.8%) -> Followed by 2,000 pts multi-month rally!
• March 2020 (COVID Liquidity Freeze)                : 5 Consecutive Lower Circuit Sessions (-28%) -> Followed by 150% Super Bull Run!
• October 2008 (Global Financial Meltdown)            : 9 Consecutive Red Days (-22%) -> Followed by 30% Bear Market Rally!

3. CONSECUTIVE WINNING STREAKS & CLIMAX TOPS:
• Climax Tops Warning: When Nifty records 7+ consecutive Green Sessions with RSI > 78 and declining cash volumes, smart money distributes long inventory to retail buyers.
• Golden Trading Rule: Never initiate fresh leveraged swing longs on Day 7 of an unbroken green streak without waiting for a 2-day pullback to the 9 EMA.
"""
        self.streak_txt.insert("1.0", text)
        self.streak_txt.configure(state="disabled")

    def _populate_rulebook(self):
        text = """========================================================================================
               THE MASTER TRADER'S CRASH SURVIVAL & WEALTH GENERATION RULEBOOK
========================================================================================

RULE 1: CASH IS AN ASSET CLASS (NEVER BE 100% DEPLOYED)
• Maintain a permanent 15-20% dry powder (Cash / Liquid Bees) in your trading portfolio.
• True wealth is built not at the top of bull runs, but by aggressively buying high-quality compounders at massive discounts during panic crashes.

RULE 2: RESPECT THE INDIA VIX ELEVATOR
• VIX < 13 : Complacency Zone. Sell covered calls, buy cheap tail-risk out-of-the-money puts.
• VIX 14 - 18: Normal Market Health. Standard swing trading rules apply.
• VIX 18 - 25: Turbulence Zone. Cut position size by 50%. Widen stop losses.
• VIX > 25: Black Swan / Extreme Panic. Stop naked futures buying. Switch exclusively to defined-risk spreads (Bull Put / Bear Put Spreads).

RULE 3: SECTOR DIVERSIFICATION IS YOUR SURVIVAL SHIELD
• High Beta Sectors (Realty, Metal, PSU Banks) fall 2.5x to 3x harder than Nifty during crashes.
• Low Beta Defensive Shelters (IT, Pharma, FMCG) drop only 0.3x to 0.5x and frequently deliver positive alpha when broader markets bleed.

RULE 4: AVOID THE "FALLING KNIFE" CATASTROPHE
• Never average down on a losing stock just because it has fallen 30% from ATH.
• A stock down 80% is simply a stock that fell 50% and then dropped another 60% from that level!
• Always wait for a confirmed higher-low price structure and volume breakout before deploying recovery capital.

RULE 5: DO NOT PANIC-SELL AT THE CRASH BOTTOM
• Every market crash in the 150-year history of modern capital markets has been followed by fresh all-time highs.
• Panic selling at the depth of a crash locks in permanent capital loss. If your directional thesis on business quality remains intact, ride the volatility.
"""
        self.rules_txt.insert("1.0", text)
        self.rules_txt.configure(state="disabled")
