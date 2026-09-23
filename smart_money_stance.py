import os
import sys
import tkinter as tk
import customtkinter as ctk
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tksheet import Sheet
import threading
from datetime import datetime

# Add workspace directory to path
sys.path.append(r"C:\users\navin\StockMarketFnO")
from db_utils import DatabaseHelper

db = DatabaseHelper()

# 1. Stance Justification Popup Modal (1D, 3D, 5D all clear justifications)
class StanceJustificationWindow(ctk.CTkToplevel):
    def __init__(self, master, csi_score, justification_text):
        super().__init__(master)
        self.title("All Clear Directional Justification")
        self.geometry("750x550")
        self.attributes("-topmost", True)
        self.configure(fg_color="#0d1117")
        
        bias_color = "#00E676" if csi_score > 30 else "#FF1744" if csi_score < -30 else "#FFB300"
        bias_text = "STRONG BULLISH" if csi_score > 30 else "STRONG BEARISH" if csi_score < -30 else "NEUTRAL / RANGEBOUND"
        
        ctk.CTkLabel(
            self, 
            text="PRO DIRECTIONAL JUSTIFICATION", 
            font=ctk.CTkFont(size=20, weight="bold"), 
            text_color="#FFD54F"
        ).pack(pady=(20, 5))
        
        bias_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        bias_frame.pack(fill="x", padx=30, pady=10)
        
        ctk.CTkLabel(
            bias_frame, 
            text=f"Market Bias: {bias_text}", 
            font=ctk.CTkFont(size=16, weight="bold"), 
            text_color=bias_color
        ).pack(pady=5)
        
        ctk.CTkLabel(
            bias_frame, 
            text=f"Combined Stance Index (CSI): {csi_score:.1f}%", 
            font=ctk.CTkFont(size=12, slant="italic"), 
            text_color="gray60"
        ).pack(pady=2)
        
        text_container = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        text_container.pack(fill="both", expand=True, padx=30, pady=(10, 20))
        
        txt = ctk.CTkTextbox(
            text_container, 
            fg_color="transparent", 
            font=ctk.CTkFont(size=13, family="Consolas"),
            wrap="word"
        )
        txt.pack(fill="both", expand=True, padx=15, pady=15)
        txt.insert("1.0", justification_text)
        txt.configure(state="disabled")


# 2. Enhanced Index-Specific Drilldown Modal (Expiries split & participant plans)
class IndexStanceDrilldownWindow(ctk.CTkToplevel):
    def __init__(self, master, index_name, master_df):
        super().__init__(master)
        self.title(f"FII, Prop & Retail Index Intelligence - {index_name}")
        self.geometry("1000x680")
        self.attributes("-topmost", True)
        self.configure(fg_color="#0d1117")
        
        self.index_name = index_name.upper()
        self.master_df = master_df
        
        ctk.CTkLabel(
            self, 
            text=f"Index F&O Structure & Rollover: {self.index_name}", 
            font=ctk.CTkFont(size=20, weight="bold"), 
            text_color="#FFD54F"
        ).pack(pady=(20, 5))
        
        # 1. Row of 1D, 3D, 5D Momentum shifts for FII, Prop, and Retail
        self.kpi_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        self.kpi_frame.pack(fill="x", padx=30, pady=5)
        self.kpi_frame.grid_columnconfigure((0, 1, 2), weight=1, uniform="kpi_sub")
        
        self._calculate_and_draw_mom_kpis()
        
        # 2. Expiries Table (Near, Next, Far Month)
        self.expiry_label = ctk.CTkLabel(
            self, 
            text=" Expiry month positioning (Near, Next & Far Month)", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            text_color="#FFD54F"
        )
        self.expiry_label.pack(anchor="w", padx=35, pady=(10, 2))
        
        self.exp_sheet_container = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=12)
        self.exp_sheet_container.pack(fill="x", padx=30, pady=5, height=130)
        self.exp_sheet_container.pack_propagate(False)
        
        cols = ["Expiry Cycle", "Expiry Date", "Close Price", "Spread (Roll Cost)", "Open Interest", "Traded Contracts"]
        self.exp_sheet = Sheet(
            self.exp_sheet_container,
            headers=cols,
            height=110
        )
        self.exp_sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.exp_sheet.change_theme("dark")
        self.exp_sheet.pack(fill="both", expand=True, padx=10, pady=10)
        
        # 3. Advisory Panel (Desks Plan & Secrets)
        self.adv_label = ctk.CTkLabel(
            self, 
            text=" Institutional Intent & Stance Reason", 
            font=ctk.CTkFont(size=14, weight="bold"), 
            text_color="#FFD54F"
        )
        self.adv_label.pack(anchor="w", padx=35, pady=(10, 2))
        
        self.adv_container = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=12)
        self.adv_container.pack(fill="both", expand=True, padx=30, pady=(5, 20))
        
        self.adv_txt = ctk.CTkTextbox(
            self.adv_container, 
            fg_color="transparent", 
            font=ctk.CTkFont(size=13, family="Consolas"),
            wrap="word"
        )
        self.adv_txt.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.load_expiry_and_plans()
        
    def _calculate_and_draw_mom_kpis(self):
        if self.master_df.empty or len(self.master_df) < 5:
            return
            
        latest = self.master_df.iloc[-1]
        prev_1d = self.master_df.iloc[-2]
        prev_3d = self.master_df.iloc[-4]
        prev_5d = self.master_df.iloc[-6]
        
        fii_1d = int(latest['FII_Index_Fut'] - prev_1d['FII_Index_Fut'])
        fii_3d = int(latest['FII_Index_Fut'] - prev_3d['FII_Index_Fut'])
        fii_5d = int(latest['FII_Index_Fut'] - prev_5d['FII_Index_Fut'])
        
        prop_1d = int(latest['Prop_Index_Fut'] - prev_1d['Prop_Index_Fut'])
        prop_3d = int(latest['Prop_Index_Fut'] - prev_3d['Prop_Index_Fut'])
        prop_5d = int(latest['Prop_Index_Fut'] - prev_5d['Prop_Index_Fut'])
        
        ret_1d = int(latest['Retail_Index_Fut'] - prev_1d['Retail_Index_Fut'])
        ret_3d = int(latest['Retail_Index_Fut'] - prev_3d['Retail_Index_Fut'])
        ret_5d = int(latest['Retail_Index_Fut'] - prev_5d['Retail_Index_Fut'])
        
        # 1-Day Card
        card_1d = ctk.CTkFrame(self.kpi_frame, fg_color="transparent")
        card_1d.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(card_1d, text="1-DAY MOMENTUM SHIFT", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray50").pack()
        fii_txt = f"FII: {fii_1d:+,}"
        prop_txt = f"PROP: {prop_1d:+,}"
        ret_txt = f"RETAIL: {ret_1d:+,}"
        ctk.CTkLabel(card_1d, text=f"{fii_txt}\n{prop_txt}\n{ret_txt}", font=ctk.CTkFont(size=12, family="Consolas"), text_color="#E0E0E0").pack(pady=5)
        
        # 3-Day Card
        card_3d = ctk.CTkFrame(self.kpi_frame, fg_color="transparent")
        card_3d.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(card_3d, text="3-DAY TREND ACCUMULATION", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray50").pack()
        fii_txt3 = f"FII: {fii_3d:+,}"
        prop_txt3 = f"PROP: {prop_3d:+,}"
        ret_txt3 = f"RETAIL: {ret_3d:+,}"
        ctk.CTkLabel(card_3d, text=f"{fii_txt3}\n{prop_txt3}\n{ret_txt3}", font=ctk.CTkFont(size=12, family="Consolas"), text_color="#E0E0E0").pack(pady=5)
        
        # 5-Day Card
        card_5d = ctk.CTkFrame(self.kpi_frame, fg_color="transparent")
        card_5d.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(card_5d, text="5-DAY MACRO DIRECTION", font=ctk.CTkFont(size=10, weight="bold"), text_color="gray50").pack()
        fii_txt5 = f"FII: {fii_5d:+,}"
        prop_txt5 = f"PROP: {prop_5d:+,}"
        ret_txt5 = f"RETAIL: {ret_5d:+,}"
        ctk.CTkLabel(card_5d, text=f"{fii_txt5}\n{prop_txt5}\n{ret_txt5}", font=ctk.CTkFont(size=12, family="Consolas"), text_color="#E0E0E0").pack(pady=5)

    def load_expiry_and_plans(self):
        try:
            q = f"""
            SELECT EXPIRY_DATE, CLOSE_PRIC, OI_NO_CON, TRD_NO_CON
            FROM dbo.vw_Futures_FnO_Analysis
            WHERE SnapShotDate = (SELECT MAX(SnapShotDate) FROM dbo.vw_Futures_FnO_Analysis)
              AND SYMBOL = '{self.index_name}'
              AND INSTRUMENTTYPE = 'FUTIDX'
            ORDER BY EXPIRY_DATE ASC
            """
            with db.get_connection() as conn:
                df = pd.read_sql(q, conn)
                
            if df.empty:
                self.exp_sheet.set_sheet_data([["No expiry records found in database."]])
                self.adv_txt.insert("1.0", "Unable to load participant plans (missing expiry structure).")
                self.adv_txt.configure(state="disabled")
                return
                
            cycles = ["Near Month", "Next Month", "Far Month"]
            sheet_rows = []
            
            near_price = df.iloc[0]['CLOSE_PRIC'] if len(df) > 0 else 0
            if pd.isna(near_price):
                near_price = 0.0
            
            for idx in range(min(3, len(df))):
                r = df.iloc[idx]
                expiry_dt = str(r['EXPIRY_DATE'])[:10]
                price = r['CLOSE_PRIC']
                
                if pd.isna(price) or price is None:
                    price_text = "--"
                    spread_text = "--"
                else:
                    price_val = float(price)
                    price_text = f"{price_val:.2f}"
                    if near_price > 0 and idx > 0:
                        spread = price_val - near_price
                        spread_text = f"{spread:+.2f}"
                    elif idx > 0:
                        spread_text = "--"
                    else:
                        spread_text = "0.00 (BASE)"
                
                sheet_rows.append([
                    cycles[idx],
                    expiry_dt,
                    price_text,
                    spread_text,
                    f"{int(r['OI_NO_CON'] or 0):,}",
                    f"{int(r['TRD_NO_CON'] or 0):,}"
                ])
                
            self.exp_sheet.set_sheet_data(sheet_rows)
            
            green, red = [], []
            for r_idx in range(1, len(sheet_rows)):
                spread_str = sheet_rows[r_idx][3]
                if spread_str == "--":
                    continue
                spread_val = float(spread_str.replace('+', ''))
                if spread_val > 0: green.append((r_idx, 3))
                else: red.append((r_idx, 3))
            if green: self.exp_sheet.highlight_cells(cells=green, fg="#00E676")
            if red: self.exp_sheet.highlight_cells(cells=red, fg="#FF1744")
            
            self._generate_advisory_text(sheet_rows)
            
        except Exception as e:
            self.exp_sheet.set_sheet_data([[f"Error: {e}"]])
            
    def _generate_advisory_text(self, exp_rows):
        spread_status = "NORMAL CONTANGO (Bullish)"
        spread_reason = "Next month contracts are trading at a premium, indicating institutions are rolling over longs and paying carry costs."
        
        if len(exp_rows) > 1 and exp_rows[1][3] != "--":
            next_spread = float(exp_rows[1][3].replace('+', ''))
            if next_spread < 0:
                spread_status = "BACKWARDATION (Bearish )"
                spread_reason = "Next month contracts are trading at a discount. Shows massive panic or short build-ups being rolled over by FIIs."
                
        adv = ""
        adv += f"========================================================================================\n"
        adv += f"            PARTICIPANTS PLAN AND INTENT ANALYSIS - {self.index_name}                 \n"
        adv += f"========================================================================================\n\n"
        
        adv += f"1 ROLLOVER COST & CARRY SPREAD: {spread_status}\n"
        adv += f"| Analysis: {spread_reason}\n\n"
        
        adv += "2 FII PLAN (Macro Hedging & Trend Builders):\n"
        adv += "| FIIs hold the bulk of Next and Far month contracts to build long-term hedging blocks.\n"
        adv += f"| They rolls their positions based on the carry spread. If spread is negative (Backwardation), FIIs are locking in shorts.\n"
        if "Bearish" in spread_status:
            adv += "| FII INTENT: Heavily short biased. They are rolling over short contracts, expecting the market to break lower next month.\n\n"
        else:
            adv += "| FII INTENT: Long biased. Rolling over long positions, willing to pay carry premium, expecting index stability or growth.\n\n"
            
        adv += "3 PROP DESK PLAN (Near-Month Scalping & Range Locking):\n"
        adv += "| Prop desks are almost exclusively active in the Near Month contracts where liquidity is maximum.\n"
        adv += "| Their focus is high-speed futures scalping and writing call/put options to trap retail.\n"
        adv += "| PROP INTENT: Today's Prop Desk stance is focused on capturing near-month option premiums. They will defend structural index supports to force decay.\n\n"
        
        adv += "4 RETAIL PLAN (Near-Month Speculators - Trapped Risk):\n"
        adv += "| Retail (Client) is concentrated 95%+ in Near Month naked options and futures contracts.\n"
        adv += "| They rarely roll over far month hedges, exposing them to massive volatility and premium decay traps of FIIs & Prop desks.\n"
        adv += "| RETAIL ACTION: To protect capital, do NOT trade Far Month options (illiquid). Align your Near-Month futures trades directly with the FII carry trend."
        
        self.adv_txt.insert("1.0", adv)
        self.adv_txt.configure(state="disabled")


# 3. Chart Double-Click Deep Insight Modal (Slope & Crossover analysis)
class DivergenceInsightWindow(ctk.CTkToplevel):
    def __init__(self, master, asset_type, timeframe, df):
        super().__init__(master)
        self.title(f"Divergence Deep Insight - {asset_type} ({timeframe})")
        self.geometry("750x550")
        self.attributes("-topmost", True)
        self.configure(fg_color="#0d1117")
        
        ctk.CTkLabel(
            self, 
            text=f"Divergence Insight: {asset_type} ({timeframe})", 
            font=ctk.CTkFont(size=20, weight="bold"), 
            text_color="#FFD54F"
        ).pack(pady=(20, 10))
        
        text_container = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        text_container.pack(fill="both", expand=True, padx=30, pady=(10, 20))
        
        txt = ctk.CTkTextbox(
            text_container, 
            fg_color="transparent", 
            font=ctk.CTkFont(size=13, family="Consolas"),
            wrap="word"
        )
        txt.pack(fill="both", expand=True, padx=15, pady=15)
        
        self._analyze_deep_insight(txt, asset_type, timeframe, df)
        txt.configure(state="disabled")
        
    def _analyze_deep_insight(self, txt, asset_type, timeframe, df):
        try:
            if df.empty or len(df) < 5:
                txt.insert("1.0", "Insufficient data history to generate insights.")
                return
                
            n_days = 15
            if timeframe == "3D": n_days = 3
            elif timeframe == "5D": n_days = 5
            elif timeframe == "15D": n_days = 15
            elif timeframe == "30D": n_days = 30
            
            sub_df = df.tail(n_days)
            
            # Asset type fields
            smart_col = "Smart_Index_Fut" if asset_type == "Index" else "Smart_Stock_Fut"
            retail_col = "Retail_Index_Fut" if asset_type == "Index" else "Retail_Stock_Fut"
            
            smart_start = sub_df.iloc[0][smart_col]
            smart_end = sub_df.iloc[-1][smart_col]
            retail_start = sub_df.iloc[0][retail_col]
            retail_end = sub_df.iloc[-1][retail_col]
            
            smart_slope = (smart_end - smart_start) / len(sub_df)
            retail_slope = (retail_end - retail_start) / len(sub_df)
            
            div_start = smart_start - retail_start
            div_end = smart_end - retail_end
            div_shift = div_end - div_start
            
            phase = "CONVERGING / CONSOLIDATION"
            phase_detail = "Smart Money and Retail net contracts are converging. This indicates rangebound conditions or an impending trend crossover."
            if (smart_slope > 0 and retail_slope < 0) or (smart_slope < 0 and retail_slope > 0):
                phase = "WIDENING DIVERGENCE (Accumulation/Distribution)"
                phase_detail = "Smart Money and Retail positions are moving in diametrically opposite directions. This shows extreme institutional build-ups (smart money accumulating/distributing while retail acts as the counterparty)."
                
            out = ""
            out += f"========================================================================================\n"
            out += f"                  {asset_type.upper()} DIVERGENCE DEEP INSIGHT ({timeframe})           \n"
            out += f"========================================================================================\n\n"
            
            out += f" MATHEMETICAL METRICS OVER {n_days} DAYS:\n"
            out += f"| Smart Money Position Slope: {smart_slope:+.2f} contracts/day\n"
            out += f"| Retail Position Slope: {retail_slope:+.2f} contracts/day\n"
            out += f"| Divergence Gap Shift: {div_shift:+,} contracts\n\n"
            
            out += f" TREND PHASE DETECTION: {phase}\n"
            out += f"| Details: {phase_detail}\n\n"
            
            out += " TRADING INSIGHTS FOR RETAIL:\n"
            if smart_slope > 0 and retail_slope < 0:
                out += "| Smart Money is building aggressive longs while Retail is shorting.\n"
                out += "| This setup usually ends in a sharp bullish breakout (Short Squeeze). Do NOT short Nifty/stocks experiencing this.\n"
            elif smart_slope < 0 and retail_slope > 0:
                out += "| Smart Money is building aggressive shorts while Retail is buying longs.\n"
                out += "| This indicates heavy institutional distribution (smart money selling to retail buyers). Expect a major dump. Avoid holding naked long swings.\n"
            else:
                out += "| Positions are balanced or moving together. There is no active trap. Trade key support/resistance levels using price action.\n"
                
            txt.insert("1.0", out)
            
        except Exception as e:
            txt.insert("1.0", f"Error generating insight: {e}")


# 4. Stock Stance Drilldown Popup Modal with Dual-Axis Chart
class StockStanceDrilldownWindow(ctk.CTkToplevel):
    def __init__(self, master, symbol, setup_name, p_chg, oi_chg):
        super().__init__(master)
        self.title(f"Stock F&O Intelligence - {symbol}")
        self.geometry("950x650")
        self.attributes("-topmost", True)
        self.configure(fg_color="#0d1117")
        
        self.symbol = symbol.upper()
        self.setup_name = setup_name
        self.p_chg = p_chg
        self.oi_chg = oi_chg
        
        ctk.CTkLabel(
            self, 
            text=f"F&O Stock Intelligence: {self.symbol}", 
            font=ctk.CTkFont(size=20, weight="bold"), 
            text_color="#FFD54F"
        ).pack(pady=(20, 5))
        
        adv_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=10)
        adv_frame.pack(fill="x", padx=30, pady=5)
        
        setup_color = "#00E676" if "Buildup" in setup_name and "Long" in setup_name else "#FF1744" if "Short Buildup" in setup_name else "#FFB300"
        
        ctk.CTkLabel(
            adv_frame,
            text=f"Current Setup: {setup_name}  |  Price: {p_chg:+.2f}%  |  OI: {oi_chg:+.2f}%",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=setup_color
        ).pack(pady=8)
        
        mid_container = ctk.CTkFrame(self, fg_color="transparent")
        mid_container.pack(fill="both", expand=True, padx=30, pady=10)
        mid_container.grid_columnconfigure(0, weight=6, uniform="mid")
        mid_container.grid_columnconfigure(1, weight=4, uniform="mid")
        mid_container.grid_rowconfigure(0, weight=1)
        
        self.chart_container = ctk.CTkFrame(mid_container, fg_color="#161b22", corner_radius=12)
        self.chart_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.chart_container.grid_columnconfigure(0, weight=1)
        self.chart_container.grid_rowconfigure(0, weight=1)
        
        self.text_container = ctk.CTkFrame(mid_container, fg_color="#161b22", corner_radius=12)
        self.text_container.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.text_container.grid_columnconfigure(0, weight=1)
        self.text_container.grid_rowconfigure(0, weight=1)
        
        self.details_txt = ctk.CTkTextbox(
            self.text_container,
            fg_color="transparent",
            font=ctk.CTkFont(size=13, family="Consolas"),
            wrap="word"
        )
        self.details_txt.pack(fill="both", expand=True, padx=15, pady=15)
        
        self.bottom_sheet_frame = ctk.CTkFrame(self, fg_color="#161b22", corner_radius=12, height=180)
        self.bottom_sheet_frame.pack(fill="x", padx=30, pady=(10, 20))
        self.bottom_sheet_frame.pack_propagate(False)
        self.bottom_sheet_frame.grid_columnconfigure(0, weight=1)
        self.bottom_sheet_frame.grid_rowconfigure(0, weight=1)
        
        cols = ["Date", "Close Price", "Total OI (Contracts)", "OI Change", "Traded Contracts", "Volume (Cr)"]
        self.sheet = Sheet(
            self.bottom_sheet_frame,
            headers=cols,
            height=150
        )
        self.sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.sheet.change_theme("dark")
        self.sheet.pack(fill="both", expand=True, padx=10, pady=10)
        
        self.load_stock_history()
        
    def load_stock_history(self):
        try:
            q = f"""
            SELECT SnapShotDate, CLOSE_PRIC, OI_NO_CON, TRD_NO_CON, TRADED_VAL
            FROM dbo.vw_Futures_FnO_Analysis
            WHERE SYMBOL = '{self.symbol}' AND INSTRUMENTTYPE = 'FUTSTK'
            ORDER BY SnapShotDate ASC
            """
            with db.get_connection() as conn:
                df = pd.read_sql(q, conn)
                
            if df.empty:
                self.details_txt.insert("1.0", "No historical data found in vw_Futures_FnO_Analysis.")
                self.details_txt.configure(state="disabled")
                return
                
            idx_max = df.groupby('SnapShotDate')['TRD_NO_CON'].idxmax()
            df_near = df.loc[idx_max].copy()
            
            df_sum = df.groupby('SnapShotDate')[['OI_NO_CON', 'TRD_NO_CON', 'TRADED_VAL']].sum().reset_index()
            history = pd.merge(df_near[['SnapShotDate', 'CLOSE_PRIC']], df_sum, on='SnapShotDate').sort_values(by='SnapShotDate')
            
            sheet_rows = []
            for idx in range(len(history)):
                row = history.iloc[idx]
                oi_chg = 0
                if idx > 0:
                    prev_oi = history.iloc[idx-1]['OI_NO_CON']
                    oi_chg = ((row['OI_NO_CON'] - prev_oi) / prev_oi) * 100 if prev_oi else 0.0
                    
                sheet_rows.append([
                    str(row['SnapShotDate'])[:10],
                    f"{row['CLOSE_PRIC']:.2f}",
                    f"{int(row['OI_NO_CON']):,}",
                    f"{oi_chg:+.2f}%" if idx > 0 else "--",
                    f"{int(row['TRD_NO_CON']):,}",
                    f"{(row['TRADED_VAL'] or 0)/10000000:,.2f}"
                ])
                
            self.sheet.set_sheet_data(sheet_rows[::-1])
            self._render_dual_axis_chart(history)
            self._generate_advisory_text(history)
            
        except Exception as e:
            self.details_txt.insert("1.0", f"Error rendering stock history: {e}")
            self.details_txt.configure(state="disabled")
            
    def _render_dual_axis_chart(self, history):
        fig, ax1 = plt.subplots(figsize=(5, 3.5), dpi=100)
        fig.patch.set_facecolor('#161b22')
        ax1.set_facecolor('#161b22')
        
        dates = pd.to_datetime(history['SnapShotDate']).dt.strftime('%m-%d').tolist()[-15:]
        prices = history['CLOSE_PRIC'].tolist()[-15:]
        oi_thousands = (history['OI_NO_CON'] / 1000).tolist()[-15:]
        
        color_price = '#00E676'
        ax1.set_xlabel('Date', color='gray')
        ax1.set_ylabel('Price', color=color_price)
        ax1.plot(dates, prices, color=color_price, marker='o', linewidth=2, label='Price')
        ax1.tick_params(axis='y', labelcolor=color_price)
        ax1.tick_params(colors='gray', labelsize=8)
        
        ax2 = ax1.twinx()
        color_oi = '#FFB300'
        ax2.set_ylabel('OI (Thousands)', color=color_oi)
        ax2.plot(dates, oi_thousands, color=color_oi, marker='x', linewidth=2, linestyle='--', label='Open Interest')
        ax2.tick_params(axis='y', labelcolor=color_oi)
        
        ax1.set_title(f"{self.symbol} Price vs Open Interest Correlation", color='white', fontsize=11, fontweight='bold')
        ax1.grid(True, color='gray', linestyle=':', alpha=0.3)
        
        for ax in [ax1, ax2]:
            for spine in ['top', 'right', 'left', 'bottom']:
                ax.spines[spine].set_visible(False)
                
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        plt.close(fig)
        
    def _generate_advisory_text(self, history):
        adv = ""
        adv += f"* F&O SIGNAL DETAILS:\n"
        adv += f"| Setup: {self.setup_name}\n"
        adv += f"| Price Momentum: {self.p_chg:+.2f}%\n"
        adv += f"| Institutional OI Shift: {self.oi_chg:+.2f}%\n\n"
        
        adv += f" SETUP EXPLANATION:\n"
        if "Long Buildup" in self.setup_name:
            adv += f"| FII & Prop desks are actively buying stock futures (Price is UP, OI is UP).\n"
            adv += f"| This indicates a strong bullish bias. Large players are building long inventory for further upside.\n\n"
            adv += f" ACTIONABLE STANCE:\n"
            adv += f"| Retail Traders: BUY Calls or Go Long in Futures.\n"
            adv += f"| Support Level: Look for minor pullbacks to buy.\n"
        elif "Short Buildup" in self.setup_name:
            adv += f"| FII & Prop desks are building fresh short positions (Price is DOWN, OI is UP).\n"
            adv += f"| This is highly bearish. Smart money is aggressive on the sell side.\n\n"
            adv += f" ACTIONABLE STANCE:\n"
            adv += f"| Retail Traders: BUY Puts or Go Short in Futures.\n"
            adv += f"| Stop Loss: Place stops above the recent high.\n"
        elif "Short Covering" in self.setup_name:
            adv += f"| Sellers are covering their short positions (Price is UP, OI is DOWN).\n"
            adv += f"| This creates upward momentum, but it is driven by short-covering rather than fresh buying.\n\n"
            adv += f" ACTIONABLE STANCE:\n"
            adv += f"| Retail Traders: Ride the short covering but keep tight trailing stops.\n"
        else:
            adv += f"| Buyers are unwinding their long positions (Price is DOWN, OI is DOWN).\n"
            adv += f"| Shows exhaustion of upward trend as longs are booking profits.\n\n"
            adv += f" ACTIONABLE STANCE:\n"
            adv += f"| Retail Traders: Exit existing longs or stay neutral."
            
        self.details_txt.insert("1.0", adv)
        self.details_txt.configure(state="disabled")


# Main Smart Money Stance UI Frame
class SmartMoneyStanceFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=15)
        
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.current_justification = ""
        self.current_csi = 0.0
        self.current_traps_text = ""
        self.master_df = pd.DataFrame()
        
        # Divergence Chart Toggles
        self.chart_asset = "Index"
        self.chart_timeframe = "15D"
        
        # 1. Header Frame
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=25, pady=(20, 10))
        
        ctk.CTkLabel(
            hdr, 
            text="Smart Money Stance & Directional Intelligence", 
            font=ctk.CTkFont(size=24, weight="bold"), 
            text_color="#FFD54F"
        ).pack(side="left")
        
        self.refresh_btn = ctk.CTkButton(
            hdr, 
            text=" Refresh Analysis", 
            width=130, 
            fg_color="#0288D1", 
            hover_color="#039BE5",
            command=self.load_and_analyze
        )
        self.refresh_btn.pack(side="right", padx=5)
        
        self.ingest_btn = ctk.CTkButton(
            hdr, 
            text=" Import Local Files", 
            width=140, 
            fg_color="#00C853", 
            hover_color="#00E676",
            command=self.run_local_ingestion
        )
        self.ingest_btn.pack(side="right", padx=5)
        
        self.status_lbl = ctk.CTkLabel(
            hdr, 
            text="Ready.", 
            font=ctk.CTkFont(size=12), 
            text_color="gray60"
        )
        self.status_lbl.pack(side="right", padx=10)
        
        # 2. All Clear Direction Banner (Row 1)
        self.all_clear_card = ctk.CTkFrame(self, fg_color="#1a2230", border_width=1, border_color="#30363d", corner_radius=10, height=75)
        self.all_clear_card.grid(row=1, column=0, sticky="ew", padx=25, pady=(5, 10))
        self.all_clear_card.grid_propagate(False)
        self.all_clear_card.grid_columnconfigure(0, weight=1)
        self.all_clear_card.grid_rowconfigure(0, weight=1)
        
        self.all_clear_lbl = ctk.CTkLabel(
            self.all_clear_card, 
            text="ALL CLEAR BIAS: ANALYZING MARKET STANCE...", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#FFB300"
        )
        self.all_clear_lbl.grid(row=0, column=0, sticky="nsew")
        
        self.all_clear_card.bind("<Double-1>", self.on_all_clear_double_click)
        self.all_clear_lbl.bind("<Double-1>", self.on_all_clear_double_click)
        
        # 3. Middle Panels: Index Specifics & Divergence Chart (Row 2)
        mid_frame = ctk.CTkFrame(self, fg_color="transparent")
        mid_frame.grid(row=2, column=0, sticky="nsew", padx=25, pady=5)
        mid_frame.grid_columnconfigure(0, weight=6, uniform="mid")
        mid_frame.grid_columnconfigure(1, weight=4, uniform="mid")
        mid_frame.grid_rowconfigure(0, weight=1)
        
        # Left Panel: Index-Specific Grid with FII/Prop/Retail split
        self.index_container = ctk.CTkFrame(mid_frame, fg_color="#161b22", corner_radius=12)
        self.index_container.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        self.index_container.grid_columnconfigure(0, weight=1)
        self.index_container.grid_rowconfigure(1, weight=1)
        
        ctk.CTkLabel(
            self.index_container, 
            text="[SCAN] FII, Prop & Retail Position Matrix (Double-click Row for Details)", 
            font=ctk.CTkFont(size=15, weight="bold"), 
            text_color="#FFD54F"
        ).grid(row=0, column=0, padx=15, pady=(15, 5), sticky="w")
        
        idx_cols = ["Asset / Participant", "FII Net", "Prop Net", "Retail Net", "FII Opt Net", "Prop Opt Net", "Retail Opt Net", "Direction"]
        self.index_sheet = Sheet(
            self.index_container,
            headers=idx_cols,
            height=250
        )
        self.index_sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.index_sheet.change_theme("dark")
        self.index_sheet.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))
        self.index_sheet.MT.bind("<Double-1>", self.on_index_double_click)
        
        # Right Panel: Divergence Chart Wrapper
        self.chart_wrapper = ctk.CTkFrame(mid_frame, fg_color="#161b22", corner_radius=12)
        self.chart_wrapper.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        self.chart_wrapper.grid_rowconfigure(1, weight=1)
        self.chart_wrapper.grid_columnconfigure(0, weight=1)
        
        # Chart Controls Header (Toggles)
        ctrl_frame = ctk.CTkFrame(self.chart_wrapper, fg_color="transparent")
        ctrl_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 0))
        
        self.asset_btn = ctk.CTkSegmentedButton(
            ctrl_frame, 
            values=["Index", "Stocks"], 
            width=100,
            command=self.on_asset_toggle
        )
        self.asset_btn.set("Index")
        self.asset_btn.pack(side="left")
        
        self.tf_btn = ctk.CTkSegmentedButton(
            ctrl_frame, 
            values=["3D", "5D", "15D", "30D"], 
            width=140,
            command=self.on_timeframe_toggle
        )
        self.tf_btn.set("15D")
        self.tf_btn.pack(side="right")
        
        self.chart_container = ctk.CTkFrame(self.chart_wrapper, fg_color="transparent")
        self.chart_container.grid(row=1, column=0, sticky="nsew")
        self.chart_container.grid_columnconfigure(0, weight=1)
        self.chart_container.grid_rowconfigure(0, weight=1)
        
        # 4. Bottom Tab View Container (Row 3)
        self.bottom_tabs = ctk.CTkTabview(self, corner_radius=12, height=220)
        self.bottom_tabs.grid(row=3, column=0, sticky="ew", padx=25, pady=(15, 20))
        
        self.bottom_tabs.add("Smart Money Stock Focus")
        self.bottom_tabs.add("Trap Radar & Secrets")
        self.bottom_tabs.add("Raw Positioning History")
        
        # Tab 1: Smart Money Stock Focus Sheet
        tab_stock = self.bottom_tabs.tab("Smart Money Stock Focus")
        tab_stock.grid_columnconfigure(0, weight=1)
        tab_stock.grid_rowconfigure(0, weight=1)
        
        stk_cols = ["Symbol", "Price", "Price Chg %", "OI Chg %", "Setup", "Stance Advice", "Volume (Cr)"]
        self.stock_sheet = Sheet(
            tab_stock,
            headers=stk_cols,
            height=160
        )
        self.stock_sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.stock_sheet.change_theme("dark")
        self.stock_sheet.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.stock_sheet.MT.bind("<Double-1>", self.on_stock_double_click)
        
        # Tab 2: Trap Radar & Secrets Tab
        tab_traps = self.bottom_tabs.tab("Trap Radar & Secrets")
        tab_traps.grid_columnconfigure(0, weight=1)
        tab_traps.grid_rowconfigure(0, weight=1)
        
        self.traps_txt = ctk.CTkTextbox(
            tab_traps,
            fg_color="transparent",
            font=ctk.CTkFont(size=13, family="Consolas"),
            wrap="word"
        )
        self.traps_txt.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Tab 3: Raw Positioning History Sheet
        tab_raw = self.bottom_tabs.tab("Raw Positioning History")
        tab_raw.grid_columnconfigure(0, weight=1)
        tab_raw.grid_rowconfigure(0, weight=1)
        
        raw_cols = ["Date", "Smart Index Fut Net", "Retail Index Fut Net", "Smart Index Opt Net", "Retail Index Opt Net", "Smart Stock Fut Net", "Combined Bias Score"]
        self.sheet = Sheet(
            tab_raw, 
            headers=raw_cols,
            height=160
        )
        self.sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark":
            self.sheet.change_theme("dark")
        self.sheet.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        self.load_and_analyze()
        
    def run_local_ingestion(self):
        self.ingest_btn.configure(text="Ingesting Files...", state="disabled")
        self.status_lbl.configure(text="Processing folder files...", text_color="gray60")
        
        sys.path.append(r"C:\users\navin\StockMarketFnO")
        from import_fno_files import run_import
        
        def bg_run():
            try:
                run_import()
                self.after(0, self.on_ingestion_complete)
            except Exception as e:
                self.after(0, lambda: self._on_error(f"Ingestion failed: {e}"))
                
        threading.Thread(target=bg_run, daemon=True).start()
        
    def on_ingestion_complete(self):
        self.ingest_btn.configure(text=" Import Local Files", state="normal")
        self.status_lbl.configure(text="Ingestion complete. Analyzing...", text_color="#00E676")
        self.load_and_analyze()
        
    def on_asset_toggle(self, val):
        self.chart_asset = val
        self._draw_chart(self.master_df)
        
    def on_timeframe_toggle(self, val):
        self.chart_timeframe = val
        self._draw_chart(self.master_df)
        
    def load_and_analyze(self):
        self.refresh_btn.configure(text="Analyzing...", state="disabled")
        self.status_lbl.configure(text="Fetching data...", text_color="gray60")
        threading.Thread(target=self._bg_analysis, daemon=True).start()
        
    def _bg_analysis(self):
        try:
            q = """
            SELECT SnapshotDate, ClientType, InstrumentType, OI_Long, OI_Short, Vol_Long, Vol_Short
            FROM dbo.NSE_Participant_Positions
            ORDER BY SnapshotDate ASC, ClientType, InstrumentType
            """
            
            q_index_stats = """
            SELECT SnapshotDate, Product, Buy_Contracts, Buy_Value_Cr, Sell_Contracts, Sell_Value_Cr, OI_Contracts, OI_Value_Cr
            FROM dbo.NSE_FII_Derivatives_Stats
            WHERE SnapshotDate = (SELECT MAX(SnapshotDate) FROM dbo.NSE_FII_Derivatives_Stats)
            """
            
            q_stock_setups = """
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
            
            with db.get_connection() as conn:
                df = pd.read_sql(q, conn)
                df_idx = pd.read_sql(q_index_stats, conn)
                df_stk = pd.read_sql(q_stock_setups, conn)
                
            if df.empty:
                self.after(0, lambda: self._on_error("No positions found. Run Import Local Files first."))
                return
                
            df['SnapshotDate'] = pd.to_datetime(df['SnapshotDate'])
            df_filtered = df[df['ClientType'].isin(['FII', 'Pro', 'Client'])].copy()
            df_filtered['Net_OI'] = df_filtered['OI_Long'].fillna(0) - df_filtered['OI_Short'].fillna(0)
            
            pivoted = df_filtered.pivot_table(
                index='SnapshotDate', 
                columns=['ClientType', 'InstrumentType'], 
                values='Net_OI', 
                aggfunc='sum'
            ).fillna(0)
            
            dates = pivoted.index
            metrics_list = []
            
            for date in dates:
                row = pivoted.loc[date]
                
                fii_idx_fut = row.get(('FII', 'Future Index'), 0)
                fii_call = row.get(('FII', 'Option Index Call'), 0)
                fii_put = row.get(('FII', 'Option Index Put'), 0)
                fii_stock_fut = row.get(('FII', 'Future Stock'), 0)
                
                pro_idx_fut = row.get(('Pro', 'Future Index'), 0)
                pro_call = row.get(('Pro', 'Option Index Call'), 0)
                pro_put = row.get(('Pro', 'Option Index Put'), 0)
                pro_stock_fut = row.get(('Pro', 'Future Stock'), 0)
                
                cli_idx_fut = row.get(('Client', 'Future Index'), 0)
                cli_call = row.get(('Client', 'Option Index Call'), 0)
                cli_put = row.get(('Client', 'Option Index Put'), 0)
                cli_stock_fut = row.get(('Client', 'Future Stock'), 0)
                
                smart_idx_fut = fii_idx_fut + pro_idx_fut
                retail_idx_fut = cli_idx_fut
                smart_idx_opt = (fii_call - fii_put) + (pro_call - pro_put)
                retail_idx_opt = cli_call - cli_put
                smart_stock_fut = fii_stock_fut + pro_stock_fut
                retail_stock_fut = cli_stock_fut
                
                metrics_list.append({
                    'Date': date.strftime('%Y-%m-%d'),
                    'Smart_Index_Fut': smart_idx_fut,
                    'Retail_Index_Fut': retail_idx_fut,
                    'Smart_Index_Opt': smart_idx_opt,
                    'Retail_Index_Opt': retail_idx_opt,
                    'Smart_Stock_Fut': smart_stock_fut,
                    'Retail_Stock_Fut': retail_stock_fut,
                    'FII_Index_Fut': fii_idx_fut,
                    'FII_Index_Opt': fii_call - fii_put,
                    'Prop_Index_Fut': pro_idx_fut,
                    'Prop_Index_Opt': pro_call - pro_put
                })
                
            res_df = pd.DataFrame(metrics_list)
            
            # Calculate CSI Score
            res_df['CSI'] = 0.0
            for idx in range(len(res_df)):
                if idx < 5:
                    continue
                fut_1d = res_df.loc[idx, 'Smart_Index_Fut'] - res_df.loc[idx-1, 'Smart_Index_Fut']
                fut_3d = res_df.loc[idx, 'Smart_Index_Fut'] - res_df.loc[idx-3, 'Smart_Index_Fut']
                fut_5d = res_df.loc[idx, 'Smart_Index_Fut'] - res_df.loc[idx-5, 'Smart_Index_Fut']
                
                opt_1d = res_df.loc[idx, 'Smart_Index_Opt'] - res_df.loc[idx-1, 'Smart_Index_Opt']
                opt_3d = res_df.loc[idx, 'Smart_Index_Opt'] - res_df.loc[idx-3, 'Smart_Index_Opt']
                opt_5d = res_df.loc[idx, 'Smart_Index_Opt'] - res_df.loc[idx-5, 'Smart_Index_Opt']
                
                fut_score = (1 if fut_1d > 0 else -1) + (0.5 if fut_3d > 0 else -0.5) + (0.5 if fut_5d > 0 else -0.5)
                opt_score = (1 if opt_1d > 0 else -1) + (0.5 if opt_3d > 0 else -0.5) + (0.5 if opt_5d > 0 else -0.5)
                
                csi = ((fut_score + opt_score) / 4.0) * 100.0
                res_df.loc[idx, 'CSI'] = csi
                
            # Process Stock setups
            stock_data_list = []
            if not df_stk.empty:
                df_stk = df_stk.sort_values(by=['SYMBOL', 'SnapShotDate'])
                
                idx_max = df_stk.groupby(['SYMBOL', 'SnapShotDate'])['TRD_NO_CON'].idxmax()
                df_near = df_stk.loc[idx_max].copy()
                
                df_oi_sum = df_stk.groupby(['SYMBOL', 'SnapShotDate'])['OI_NO_CON'].sum().reset_index()
                df_merged = pd.merge(df_near[['SYMBOL', 'SnapShotDate', 'CLOSE_PRIC', 'TRADED_VAL']], df_oi_sum, on=['SYMBOL', 'SnapShotDate'])
                df_merged = df_merged.sort_values(by=['SYMBOL', 'SnapShotDate'])
                
                for symbol, g in df_merged.groupby('SYMBOL'):
                    if len(g) < 2:
                        continue
                    prev_row = g.iloc[0]
                    curr_row = g.iloc[1]
                    
                    p_prev = prev_row['CLOSE_PRIC']
                    p_curr = curr_row['CLOSE_PRIC']
                    oi_prev = prev_row['OI_NO_CON']
                    oi_curr = curr_row['OI_NO_CON']
                    
                    p_chg = ((p_curr - p_prev) / p_prev) * 100 if p_prev else 0
                    oi_chg = ((oi_curr - oi_prev) / oi_prev) * 100 if oi_prev else 0
                    
                    if p_chg > 0 and oi_chg > 0:
                        setup = "Long Buildup (Bullish )"
                        stance = "BUY"
                    elif p_chg < 0 and oi_chg > 0:
                        setup = "Short Buildup (Bearish [SELL])"
                        stance = "SELL"
                    elif p_chg > 0 and oi_chg < 0:
                        setup = "Short Covering (Shorts Exiting )"
                        stance = "BUY"
                    else:
                        setup = "Long Unwinding (Longs Exiting )"
                        stance = "SELL"
                        
                    stock_data_list.append({
                        'SYMBOL': symbol,
                        'Price': p_curr,
                        'Price_Chg': p_chg,
                        'OI_Chg': oi_chg,
                        'Setup': setup,
                        'Stance': stance,
                        'Vol_Cr': (curr_row['TRADED_VAL'] or 0) / 10000000
                    })
                    
            try:
                if self.winfo_exists():
                    self.after(0, lambda: self._on_analysis_complete(res_df, df_idx, stock_data_list))
            except Exception:
                pass
            
        except Exception as e:
            try:
                if self.winfo_exists():
                    self.after(0, lambda: self._on_error(str(e)))
            except Exception:
                pass
            
    def _on_analysis_complete(self, df, df_idx, stock_data_list):
        self.master_df = df
        self.refresh_btn.configure(text=" Refresh Analysis", state="normal")
        self.status_lbl.configure(text="Analysis complete.", text_color="#00E676")
        
        # Populate Raw Sheet
        sheet_data = []
        for idx, r in df.iloc[::-1].iterrows():
            sheet_data.append([
                r['Date'],
                f"{int(r['Smart_Index_Fut']):,}",
                f"{int(r['Retail_Index_Fut']):,}",
                f"{int(r['Smart_Index_Opt']):,}",
                f"{int(r['Retail_Index_Opt']):,}",
                f"{int(r['Smart_Stock_Fut']):,}",
                f"{r['CSI']:.1f}%"
            ])
        self.sheet.set_sheet_data(sheet_data)
        
        green, red = [], []
        for row_idx, row in enumerate(sheet_data):
            csi_val = float(row[6].replace('%', ''))
            if csi_val > 0: green.append((row_idx, 6))
            elif csi_val < 0: red.append((row_idx, 6))
        if green: self.sheet.highlight_cells(cells=green, fg="#00E676")
        if red: self.sheet.highlight_cells(cells=red, fg="#FF1744")
            
        # Populate FII, Prop, Retail Matrix
        self._populate_index_sheet(df_idx, df)
        
        # Populate Stock Sheet
        self._populate_stock_sheet(stock_data_list)
        
        # Draw Chart
        self._draw_chart(df)
        
        # Generate All-Clear Banner, Stance Advisory & Traps Text
        self._generate_advisory_and_kpis(df)
        
    def _populate_index_sheet(self, df_idx, df):
        if df.empty:
            return
            
        latest = df.iloc[-1]
        rows = []
        
        indices = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]
        for name in indices:
            prod_fut = f"{name} FUTURES"
            prod_opt = f"{name} OPTIONS"
            
            fut_row = df_idx[df_idx['Product'] == prod_fut]
            opt_row = df_idx[df_idx['Product'] == prod_opt]
            
            fut_net = (fut_row.iloc[0]['Buy_Contracts'] or 0) - (fut_row.iloc[0]['Sell_Contracts'] or 0) if not fut_row.empty else 0
            opt_net = (opt_row.iloc[0]['Buy_Contracts'] or 0) - (opt_row.iloc[0]['Sell_Contracts'] or 0) if not opt_row.empty else 0
            
            direction = "Neutral "
            if fut_net > 0 and opt_net > 0: direction = "Bullish "
            elif fut_net < 0 and opt_net < 0: direction = "Bearish "
            elif fut_net > 0: direction = "Long-Covering "
            elif fut_net < 0: direction = "Short-Covering "
            
            rows.append([
                f"{name} (FII Only)",
                f"{fut_net:+,}",
                "--", "--",
                f"{opt_net:+,}",
                "--", "--",
                direction
            ])
            
        fii_fut = int(latest['FII_Index_Fut'])
        fii_opt = int(latest['FII_Index_Opt'])
        rows.append([
            "OVERALL FII (All)",
            f"{fii_fut:+,}", "--", "--",
            f"{fii_opt:+,}", "--", "--",
            "Bullish " if fii_fut > 0 and fii_opt > 0 else "Bearish " if fii_fut < 0 and fii_opt < 0 else "Mixed "
        ])
        
        prop_fut = int(latest['Prop_Index_Fut'])
        prop_opt = int(latest['Prop_Index_Opt'])
        rows.append([
            "OVERALL PROP DESK (All)",
            "--", f"{prop_fut:+,}", "--",
            "--", f"{prop_opt:+,}", "--",
            "Bullish " if prop_fut > 0 and prop_opt > 0 else "Bearish " if prop_fut < 0 and prop_opt < 0 else "Mixed "
        ])
        
        retail_fut = int(latest['Retail_Index_Fut'])
        retail_opt = int(latest['Retail_Index_Opt'])
        rows.append([
            "OVERALL RETAIL (All)",
            "--", "--", f"{retail_fut:+,}",
            "--", "--", f"{retail_opt:+,}",
            "Bullish " if retail_fut > 0 and retail_opt > 0 else "Bearish " if retail_fut < 0 and retail_opt < 0 else "Mixed "
        ])
        
        self.index_sheet.set_sheet_data(rows)
        
        green, red = [], []
        for r_idx, row in enumerate(rows):
            if row[1] != "--":
                val = int(row[1].replace('+', '').replace(',', ''))
                if val > 0: green.append((r_idx, 1))
                else: red.append((r_idx, 1))
            if row[4] != "--":
                val = int(row[4].replace('+', '').replace(',', ''))
                if val > 0: green.append((r_idx, 4))
                else: red.append((r_idx, 4))
                
            if row[2] != "--":
                val = int(row[2].replace('+', '').replace(',', ''))
                if val > 0: green.append((r_idx, 2))
                else: red.append((r_idx, 2))
            if row[5] != "--":
                val = int(row[5].replace('+', '').replace(',', ''))
                if val > 0: green.append((r_idx, 5))
                else: red.append((r_idx, 5))
                
            if row[3] != "--":
                val = int(row[3].replace('+', '').replace(',', ''))
                if val > 0: green.append((r_idx, 3))
                else: red.append((r_idx, 3))
            if row[6] != "--":
                val = int(row[6].replace('+', '').replace(',', ''))
                if val > 0: green.append((r_idx, 6))
                else: red.append((r_idx, 6))
                
            if "Bullish" in row[7] or "" in row[7]: green.append((r_idx, 7))
            elif "Bearish" in row[7] or "" in row[7]: red.append((r_idx, 7))
            
        if green: self.index_sheet.highlight_cells(cells=green, fg="#00E676")
        if red: self.index_sheet.highlight_cells(cells=red, fg="#FF1744")

    def _populate_stock_sheet(self, stock_list):
        if not stock_list:
            self.stock_sheet.set_sheet_data([["No stock F&O analysis data available."]])
            return
            
        sorted_stk = sorted(stock_list, key=lambda x: abs(x['OI_Chg']), reverse=True)
        
        rows = []
        for s in sorted_stk:
            rows.append([
                s['SYMBOL'],
                f"{s['Price']:.2f}",
                f"{s['Price_Chg']:+.2f}%",
                f"{s['OI_Chg']:+.2f}%",
                s['Setup'],
                s['Stance'],
                f"{s['Vol_Cr']:.2f}"
            ])
            
        self.stock_sheet.set_sheet_data(rows)
        
        green, red, yellow, orange = [], [], [], []
        for r_idx, row in enumerate(rows):
            p_chg = float(row[2].replace('%', ''))
            oi_chg = float(row[3].replace('%', ''))
            
            if p_chg > 0 and oi_chg > 0:
                green.append((r_idx, 4))
                green.append((r_idx, 5))
            elif p_chg < 0 and oi_chg > 0:
                red.append((r_idx, 4))
                red.append((r_idx, 5))
            elif p_chg > 0 and oi_chg < 0:
                yellow.append((r_idx, 4))
                yellow.append((r_idx, 5))
            else:
                orange.append((r_idx, 4))
                orange.append((r_idx, 5))
                
        if green: self.stock_sheet.highlight_cells(cells=green, fg="#00E676")
        if red: self.stock_sheet.highlight_cells(cells=red, fg="#FF1744")
        if yellow: self.stock_sheet.highlight_cells(cells=yellow, fg="#FFD54F")
        if orange: self.stock_sheet.highlight_cells(cells=orange, fg="#FF8A65")

    def _draw_chart(self, df):
        if df.empty:
            return
            
        for widget in self.chart_container.winfo_children():
            widget.destroy()
            
        fig, ax = plt.subplots(figsize=(6, 3.6), dpi=100)
        fig.patch.set_facecolor('#161b22')
        ax.set_facecolor('#161b22')
        
        # Get timeframe count
        n_days = 15
        if self.chart_timeframe == "3D": n_days = 3
        elif self.chart_timeframe == "5D": n_days = 5
        elif self.chart_timeframe == "15D": n_days = 15
        elif self.chart_timeframe == "30D": n_days = 30
        
        sub_df = df.tail(n_days)
        dates_to_plot = pd.to_datetime(sub_df['Date']).dt.strftime('%m-%d').tolist()
        
        # Get asset type fields
        if self.chart_asset == "Index":
            smart_fut = (sub_df['Smart_Index_Fut'] / 1000).tolist()
            retail_fut = (sub_df['Retail_Index_Fut'] / 1000).tolist()
            title = f"{n_days}-Day Index Futures Divergence"
        else:
            smart_fut = (sub_df['Smart_Stock_Fut'] / 1000).tolist()
            retail_fut = (sub_df['Retail_Stock_Fut'] / 1000).tolist()
            title = f"{n_days}-Day Stock Futures Divergence"
            
        ax.plot(dates_to_plot, smart_fut, color='#00E676', marker='o', linewidth=2, label='Smart Money (FII+Prop)')
        ax.plot(dates_to_plot, retail_fut, color='#FF1744', marker='x', linewidth=2, linestyle='--', label='Retail (Client)')
        
        ax.set_title(title, color='white', fontsize=11, fontweight='bold')
        ax.set_ylabel("Net Contracts (Thousands)", color='gray', fontsize=9)
        ax.tick_params(colors='gray', labelsize=8)
        ax.grid(True, color='gray', linestyle=':', alpha=0.3)
        ax.legend(facecolor='#161b22', edgecolor='none', labelcolor='white')
        
        for spine in ['top', 'right', 'left', 'bottom']:
            ax.spines[spine].set_visible(False)
            
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        
        # Bind double-click on chart canvas
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill="both", expand=True, padx=5, pady=5)
        canvas_widget.bind("<Double-1>", self.on_chart_double_click)
        plt.close(fig)
        
    def _generate_advisory_and_kpis(self, df):
        if len(df) < 6:
            return
            
        latest = df.iloc[-1]
        prev_1d = df.iloc[-2]
        prev_3d = df.iloc[-4]
        prev_5d = df.iloc[-6]
        
        csi_1d = latest['CSI']
        self.current_csi = csi_1d
        
        bias_color = "#00E676" if csi_1d > 30 else "#FF1744" if csi_1d < -30 else "#FFB300"
        bias_text = "STRONG BULLISH " if csi_1d > 30 else "STRONG BEARISH " if csi_1d < -30 else "NEUTRAL / RANGEBOUND "
        
        self.all_clear_lbl.configure(
            text=f"ALL CLEAR BIAS: {bias_text}  (Double-click for Detailed Justification)",
            text_color=bias_color
        )
        
        div_latest = latest['Smart_Index_Fut'] - latest['Retail_Index_Fut']
        div_1d = div_latest - (prev_1d['Smart_Index_Fut'] - prev_1d['Retail_Index_Fut'])
        div_3d = div_latest - (prev_3d['Smart_Index_Fut'] - prev_3d['Retail_Index_Fut'])
        div_5d = div_latest - (prev_5d['Smart_Index_Fut'] - prev_5d['Retail_Index_Fut'])
        
        fii_fut = int(latest['FII_Index_Fut'])
        fii_opt = int(latest['FII_Index_Opt'])
        prop_fut = int(latest['Prop_Index_Fut'])
        prop_opt = int(latest['Prop_Index_Opt'])
        retail_fut = int(latest['Retail_Index_Fut'])
        retail_opt = int(latest['Retail_Index_Opt'])
        
        justification = ""
        justification += "* DIVERGENCE SCORECARD:\n"
        justification += f"| 1-Day Divergence Shift: {div_1d:+,} contracts\n"
        justification += f"| 3-Day Divergence Shift: {div_3d:+,} contracts\n"
        justification += f"| 5-Day Divergence Shift: {div_5d:+,} contracts\n\n"
        
        justification += " INSTITUTIONAL SEPARATE STANCE:\n"
        justification += f"| FII Index Futures Net: {fii_fut:+,} contracts\n"
        justification += f"| Prop Desk Futures Net: {prop_fut:+,} contracts\n"
        justification += f"| Retail Index Futures Net: {retail_fut:+,} contracts\n\n"
        
        justification += " ANALYSIS JUSTIFICATION:\n"
        if csi_1d > 30:
            justification += "FII & Prop desks are building massive longs, while Retail (Client) is caught short. Statistically, retail gets squeezed.\n"
            justification += "This creates an asymmetric bullish trigger. Support is strong at recent breakout swing lows.\n"
        elif csi_1d < -30:
            justification += "FII & Prop are shorting index futures heavily. Retail is loading call options expecting a bounce.\n"
            justification += "This is a classic bull trap. The market will decay retail options and slide lower to flush out retail longs.\n"
        else:
            justification += "CSI scores show balanced distribution. Market is rangebound. Avoid directional index bets.\n"
            
        self.current_justification = justification
        
        traps = ""
        traps += "========================================================================================\n"
        traps += "                     DESK SECRETS & INSTITUTIONAL TRAP RADAR                          \n"
        traps += "========================================================================================\n\n"
        
        traps += " DIVERGENCE INDEX SUMMARY:\n"
        traps += f"| 1D Divergence: {div_1d:+,} contracts | 3D: {div_3d:+,} | 5D: {div_5d:+,}\n"
        if div_1d < -30000:
            traps += f"| WARNING: Retail is buying aggressively while FII/Prop is dumping. Institutional trap detected!\n\n"
        elif div_1d > 30000:
            traps += f"| WARNING: FII/Prop are accumulating heavily while Retail is selling. Retail is trapped on the short side!\n\n"
        else:
            traps += "| Divergence index is inside a normal range. No immediate macro trap detected.\n\n"
            
        traps += " THE PROP DESK SECRET:\n"
        traps += "| Prop desks are highly active option writers. They usually target retail option buyers by locking the market inside a tight range on expiry days.\n"
        traps += f"| Today's Prop Desk Options Net: {prop_opt:+,} contracts.\n"
        if abs(prop_opt) > 200000 and retail_opt > 0:
            traps += "| TRAP ALERT: Prop Desks written massive options against retail buyers. Avoid buying naked index options. Premium decay will be severe.\n\n"
        else:
            traps += "| Prop desk options positioning is moderate. Normal premium decay rules apply.\n\n"
            
        traps += " THE FII DESK SECRET:\n"
        traps += "| FIIs drive the medium-term macro trend using Index Futures. They rarely take short-term speculative bets. Keep your positioning aligned with them.\n"
        traps += f"| Today's FII Index Futures Net: {fii_fut:+,} contracts.\n"
        if fii_fut < -100000:
            traps += "| FII overall index futures are heavily short. Do NOT hold naked overnight long positions. Protect your cash portfolio.\n\n"
        elif fii_fut > 100000:
            traps += "| FII overall index futures are heavily long. Buy pullbacks. Do NOT short the market.\n\n"
        else:
            traps += "| FII futures position is neutral. Trade intraday setups.\n\n"
            
        traps += " RETAIL STANCE STRATEGY:\n"
        if fii_fut < 0 and prop_fut < 0 and retail_fut > 0:
            traps += " [STATUS: trap active - retail trapped long]\n"
            traps += "| Advice: Retail is heavily long Nifty futures while smart money is short. Stop loss execution will slide price. Exit long positions immediately. Trade Sell on Rallies."
        elif fii_fut > 0 and prop_fut > 0 and retail_fut < 0:
            traps += " [STATUS: trap active - retail trapped short]\n"
            traps += "| Advice: Retail is short while smart money is long. A massive short squeeze is highly probable. Avoid shorting. Buy Nifty calls on pullbacks."
        else:
            traps += "[OK] [STATUS: no active trap]\n"
            traps += "| Advice: Align your trades with stock-specific Long Buildup setups listed in the Smart Money Stock Focus tab."
            
        self.current_traps_text = traps
        self.traps_txt.configure(state="normal")
        self.traps_txt.delete("1.0", "end")
        self.traps_txt.insert("1.0", traps)
        self.traps_txt.configure(state="disabled")

    def on_all_clear_double_click(self, event):
        StanceJustificationWindow(self.winfo_toplevel(), self.current_csi, self.current_justification)
        
    def on_index_double_click(self, event):
        row = self.index_sheet.identify_row(event)
        if row is not None and row >= 0:
            sheet_data = self.index_sheet.get_sheet_data()
            index_raw = sheet_data[row][0]
            index_name = index_raw.split()[0]
            if index_name in ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY"]:
                IndexStanceDrilldownWindow(self.winfo_toplevel(), index_name, self.master_df)

    def on_stock_double_click(self, event):
        row = self.stock_sheet.identify_row(event)
        if row is not None and row >= 0:
            sheet_data = self.stock_sheet.get_sheet_data()
            symbol = sheet_data[row][0]
            p_chg = float(sheet_data[row][2].replace('%', ''))
            oi_chg = float(sheet_data[row][3].replace('%', ''))
            setup = sheet_data[row][4]
            StockStanceDrilldownWindow(self.winfo_toplevel(), symbol, setup, p_chg, oi_chg)

    def on_chart_double_click(self, event):
        DivergenceInsightWindow(self.winfo_toplevel(), self.chart_asset, self.chart_timeframe, self.master_df)

    def _on_error(self, err_msg):
        self.refresh_btn.configure(text=" Refresh Analysis", state="normal")
        self.status_lbl.configure(text="Failed.", text_color="#FF1744")
        self.all_clear_lbl.configure(text=f"ERROR: {err_msg}", text_color="#FF1744")
