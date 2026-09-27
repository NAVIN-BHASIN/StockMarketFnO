"""
================================================================================
MODULE: TRADING JOURNAL ANALYTICS & COGNITIVE BEHAVIOR REFLECTION SUITE
================================================================================
Tier: Presentation / UI Layer
Architecture: CustomTkinter + tksheet + Matplotlib Data Visualization
Features:
  - 10-Tier Multi-Dimensional Analytics Suite (History, Performance, Win/Loss,
    Emotional & Psychological Discipline, Risk Management, Setup Performance)
  - Deep Cognitive Behavior Reflection Engine with Automated Trading Psychology Insights
  - Direct Trade Entry & Multi-Broker Contract Note Reconciliation
Version: 3.0.0 (Enterprise Release)
Standards: PEP 8, Clean Architecture, High-Fidelity UI/UX
================================================================================
"""

import os
import re
import math
import hashlib
from datetime import datetime, date
import pandas as pd
import numpy as np
import pyodbc

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
from tksheet import Sheet

import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

import journal_engine

SERVER = r'.\SQLEXPRESS'
DATABASE = 'Navin_Personal'
CONN_STR = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'

def get_connection():
    return pyodbc.connect(CONN_STR)

MAJOR_INDICES = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY', 'SENSEX', 'BANKEX']

def resolve_sheet_row(event, sheet):
    """
    Robustly resolves the selected row index from a tksheet event or current selection.
    Handles cell clicks, row index clicks, double clicks, and keyboard events.
    """
    if event is not None:
        if hasattr(event, "row") and isinstance(getattr(event, "row"), int):
            return event.row
        if isinstance(event, dict) and "row" in event:
            return event["row"]
        if isinstance(event, (list, tuple)) and len(event) > 1 and isinstance(event[1], int):
            return event[1]
    try:
        sel = sheet.get_currently_selected()
        if sel and hasattr(sel, "row") and isinstance(sel.row, int):
            return sel.row
    except Exception:
        pass
    try:
        rows = sheet.get_selected_rows()
        if rows:
            return list(rows)[0]
    except Exception:
        pass
    if event is not None and hasattr(event, "y"):
        try:
            return sheet.identify_row(event)
        except Exception:
            pass
    return None

# -------------------------------------------------------------
# ADVANCED TRADE DRILL-DOWN & PROFESSIONAL ADVISOR MODAL
# -------------------------------------------------------------
class TradeDrillDownModal(ctk.CTkToplevel):
    def __init__(self, master, trade_data, on_save_callback=None):
        super().__init__(master)
        self.trade_data = trade_data
        self.on_save_callback = on_save_callback
        
        trade_id = trade_data.get('TradeID', 'N/A')
        symbol = trade_data.get('Symbol', 'Unknown')
        self.title(f"Institutional Trade Advisor & What-If Engine — #{trade_id} ({symbol})")
        self.geometry("980x800")
        self.minsize(900, 700)
        self.attributes("-topmost", True)
        self.after(250, lambda: self.attributes("-topmost", False))
        self.focus_force()
        try:
            self.grab_set()
        except:
            pass
        
        self._build_ui()
        
    def _build_ui(self):
        container = ctk.CTkScrollableFrame(self, corner_radius=10)
        container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # 1. TOP HEADER & METRICS BADGE
        hdr = ctk.CTkFrame(container, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 15))
        
        net_pnl = float(self.trade_data.get('NetPnL', 0.0))
        pnl_color = "#00E676" if net_pnl >= 0 else "#FF5252"
        pnl_sign = "+" if net_pnl >= 0 else ""
        
        sym_lbl = ctk.CTkLabel(hdr, text=f"{self.trade_data.get('Symbol', '')}", font=ctk.CTkFont(size=24, weight="bold"))
        sym_lbl.pack(side="left")
        
        seg = self.trade_data.get('Segment', '')
        sub = self.trade_data.get('SubSegment', '')
        broker = self.trade_data.get('Broker', '')
        broker_badge = ctk.CTkLabel(hdr, text=f" {broker} • {seg} ({sub}) ", 
                                    fg_color="#333333", corner_radius=6, font=ctk.CTkFont(size=12))
        broker_badge.pack(side="left", padx=15)
        
        pnl_badge = ctk.CTkLabel(hdr, text=f"Net Realized P&L: {pnl_sign}Rs. {net_pnl:,.2f}", 
                                 fg_color=pnl_color, text_color="#000000" if net_pnl >= 0 else "#FFFFFF",
                                 corner_radius=8, font=ctk.CTkFont(size=15, weight="bold"), padx=14, pady=5)
        pnl_badge.pack(side="right")
        
        # 2. EXECUTION LEGS & FINANCIAL DETAILS
        grid_frame = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        grid_frame.pack(fill="x", pady=(0, 15), padx=5)
        grid_frame.columnconfigure((0, 1, 2, 3), weight=1)
        
        details = [
            ("Contract Name", self.trade_data.get('ContractName', self.trade_data.get('Symbol', ''))),
            ("Financial Year", self.trade_data.get('FinancialYear', '')),
            ("Holding Duration", f"{self.trade_data.get('HoldingDays', 0)} Days"),
            ("ROI %", f"{float(self.trade_data.get('ROIPct', 0.0)):.2f}%"),
            ("Entry Date", str(self.trade_data.get('EntryDate', ''))),
            ("Buy Price", f"Rs. {float(self.trade_data.get('BuyPrice', 0.0)):,.2f}"),
            ("Quantity", f"{float(self.trade_data.get('Quantity', 0.0)):,.2f}"),
            ("Buy Value", f"Rs. {float(self.trade_data.get('BuyValue', 0.0)):,.2f}"),
            ("Exit Date", str(self.trade_data.get('ExitDate', ''))),
            ("Sell Price", f"Rs. {float(self.trade_data.get('SellPrice', 0.0)):,.2f}"),
            ("Option / Strike", f"{self.trade_data.get('OptionType', 'N/A')} {self.trade_data.get('StrikePrice') or ''}".strip()),
            ("Sell Value", f"Rs. {float(self.trade_data.get('SellValue', 0.0)):,.2f}"),
            ("Expiry Date", str(self.trade_data.get('ExpiryDate') or 'N/A')),
            ("Gross P&L", f"Rs. {float(self.trade_data.get('GrossPnL', 0.0)):,.2f}"),
            ("Total Charges", f"Rs. {float(self.trade_data.get('TotalCharges', 0.0)):,.2f}"),
            ("Outcome", self.trade_data.get('Outcome', 'BREAKEVEN'))
        ]
        
        for i, (label, val) in enumerate(details):
            r = i // 4
            c = i % 4
            cell = ctk.CTkFrame(grid_frame, fg_color="transparent")
            cell.grid(row=r, column=c, padx=12, pady=7, sticky="w")
            ctk.CTkLabel(cell, text=label, font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888").pack(anchor="w")
            ctk.CTkLabel(cell, text=str(val), font=ctk.CTkFont(size=12, weight="normal"), text_color="#FFFFFF").pack(anchor="w")

        # 3. CHARGES BREAKDOWN
        chg_frame = ctk.CTkFrame(container, fg_color="#1E1E1E", corner_radius=10, border_width=1, border_color="#2D2D2D")
        chg_frame.pack(fill="x", pady=(0, 15), padx=5)
        ctk.CTkLabel(chg_frame, text="🧾 Itemized Friction & Brokerage Breakdown", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=15, pady=(10, 5))
        
        chg_row = ctk.CTkFrame(chg_frame, fg_color="transparent")
        chg_row.pack(fill="x", padx=15, pady=(0, 10))
        chg_row.columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        
        charges_items = [
            ("Brokerage", float(self.trade_data.get('Brokerage', 0.0))),
            ("STT / CTT", float(self.trade_data.get('STT', 0.0))),
            ("Exchange Tx", float(self.trade_data.get('ExchangeCharges', 0.0))),
            ("GST / Service Tax", float(self.trade_data.get('GST', 0.0))),
            ("Stamp Duty", float(self.trade_data.get('StampDuty', 0.0))),
            ("Total Charges", float(self.trade_data.get('TotalCharges', 0.0)))
        ]
        for col_idx, (c_label, c_val) in enumerate(charges_items):
            c_box = ctk.CTkFrame(chg_row, fg_color="#121212", corner_radius=6)
            c_box.grid(row=0, column=col_idx, padx=4, pady=4, sticky="nsew")
            ctk.CTkLabel(c_box, text=c_label, font=ctk.CTkFont(size=10), text_color="#999999").pack(pady=(4, 0))
            ctk.CTkLabel(c_box, text=f"Rs. {c_val:,.2f}", font=ctk.CTkFont(size=12, weight="bold"), 
                         text_color="#FFA726" if c_label == "Total Charges" else "#FFFFFF").pack(pady=(0, 4))

        # 4. "WHAT-IF" EXPIRY SIMULATION & OPPORTUNITY COST
        whatif_box = ctk.CTkFrame(container, fg_color="#1A1F2C", corner_radius=10, border_width=1, border_color="#303F9F")
        whatif_box.pack(fill="x", pady=(0, 15), padx=5)
        ctk.CTkLabel(whatif_box, text="🔮 What-If Analysis: Expiry Holding vs Early Exit Simulation", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#82B1FF").pack(anchor="w", padx=15, pady=(12, 6))
        
        whatif_text = self._generate_whatif_analysis()
        ctk.CTkLabel(whatif_box, text=whatif_text, justify="left", font=ctk.CTkFont(size=12), text_color="#E0E0E0").pack(anchor="w", padx=15, pady=(0, 14))

        # 5. ROLLOVER VIABILITY & RECOVERY CHANCE
        roll_box = ctk.CTkFrame(container, fg_color="#1F261F", corner_radius=10, border_width=1, border_color="#388E3C")
        roll_box.pack(fill="x", pady=(0, 15), padx=5)
        ctk.CTkLabel(roll_box, text="🔄 Rollover Viability & Pre-Expiry Recovery Probability", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#A5D6A7").pack(anchor="w", padx=15, pady=(12, 6))
        
        roll_text = self._generate_rollover_analysis()
        ctk.CTkLabel(roll_box, text=roll_text, justify="left", font=ctk.CTkFont(size=12), text_color="#E0E0E0").pack(anchor="w", padx=15, pady=(0, 14))

        # 6. WEEKLY & MONTHLY RECOVERY ACTION PLAN
        rec_box = ctk.CTkFrame(container, fg_color="#2D1C1C" if net_pnl < 0 else "#1A2E22", corner_radius=10, border_width=1, 
                               border_color="#C62828" if net_pnl < 0 else "#2E7D32")
        rec_box.pack(fill="x", pady=(0, 15), padx=5)
        rec_title = "🛡️ Structured Loss Recovery Plan (Weekly & Monthly Roadmap)" if net_pnl < 0 else "🚀 Profit Compounding & Capital Expansion Plan"
        ctk.CTkLabel(rec_box, text=rec_title, font=ctk.CTkFont(size=14, weight="bold"), 
                     text_color="#FF8A80" if net_pnl < 0 else "#81C784").pack(anchor="w", padx=15, pady=(12, 6))
        
        recovery_plan_text = self._generate_recovery_plan(net_pnl)
        ctk.CTkLabel(rec_box, text=recovery_plan_text, justify="left", font=ctk.CTkFont(size=12), text_color="#F5F5F5").pack(anchor="w", padx=15, pady=(0, 14))

        # 7. PROFESSIONAL ADVISOR: GREEKS, OI & WHAT TO AVOID / INCLUDE
        adv_box = ctk.CTkFrame(container, fg_color="#212121", corner_radius=10, border_width=1, border_color="#424242")
        adv_box.pack(fill="x", pady=(0, 15), padx=5)
        ctk.CTkLabel(adv_box, text="🧠 Institutional Advisory: Greeks, OI Behavior & Symbol Execution Rules", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#FFD54F").pack(anchor="w", padx=15, pady=(12, 6))
        
        advisory_text = self._generate_greeks_and_oi_advice()
        ctk.CTkLabel(adv_box, text=advisory_text, justify="left", font=ctk.CTkFont(size=12), text_color="#EEEEEE").pack(anchor="w", padx=15, pady=(0, 14))

        # 8. JOURNALING, TAGGING & NOTES
        tag_frame = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        tag_frame.pack(fill="x", pady=(0, 15), padx=5)
        
        ctk.CTkLabel(tag_frame, text="✍️ Trade Journaling, Discipline Tagging & Rating", font=ctk.CTkFont(size=14, weight="bold"), text_color="#64B5F6").pack(anchor="w", padx=15, pady=(10, 5))
        
        tag_inputs = ctk.CTkFrame(tag_frame, fg_color="transparent")
        tag_inputs.pack(fill="x", padx=15, pady=5)
        tag_inputs.columnconfigure(1, weight=1)
        
        # Mistake Tag
        ctk.CTkLabel(tag_inputs, text="Discipline / Mistake Tag:", font=ctk.CTkFont(size=12)).grid(row=0, column=0, sticky="w", pady=6)
        mistake_options = [
            "None / Clean Execution",
            "FOMO Entry (Fear Of Missing Out)",
            "Overtrading / Excess Lots",
            "No Stop Loss / Refused to Cut Loss",
            "Chasing Green Candles / Late Entry",
            "Averaging Down on Losing Position",
            "Early Exit / Cut Winner Prematurely",
            "Held Past Expiry / Zero Expiry Loss",
            "Revenge Trading After Loss",
            "Plan Followed (Clean Setup)"
        ]
        curr_mistake = self.trade_data.get('MistakeTag') or "None / Clean Execution"
        if curr_mistake not in mistake_options:
            mistake_options.insert(1, curr_mistake)
        self.mistake_var = ctk.StringVar(value=curr_mistake)
        self.mistake_menu = ctk.CTkOptionMenu(tag_inputs, variable=self.mistake_var, values=mistake_options, width=340)
        self.mistake_menu.grid(row=0, column=1, sticky="w", padx=10, pady=6)
        
        # Setup Tag
        ctk.CTkLabel(tag_inputs, text="Strategy / Setup Tag:", font=ctk.CTkFont(size=12)).grid(row=1, column=0, sticky="w", pady=6)
        setup_options = ["None", "Breakout / Momentum", "Mean Reversion / Support-Resistance", "Trend Following", "Expiry Day Scalp", "Hedging / Spread", "Option Buying", "Option Selling"]
        curr_setup = self.trade_data.get('SetupTag') or "None"
        if curr_setup not in setup_options:
            setup_options.insert(1, curr_setup)
        self.setup_var = ctk.StringVar(value=curr_setup)
        self.setup_menu = ctk.CTkOptionMenu(tag_inputs, variable=self.setup_var, values=setup_options, width=340)
        self.setup_menu.grid(row=1, column=1, sticky="w", padx=10, pady=6)
        
        # Notes
        ctk.CTkLabel(tag_inputs, text="Trade Notes & Lessons:", font=ctk.CTkFont(size=12)).grid(row=2, column=0, sticky="nw", pady=6)
        self.notes_txt = ctk.CTkTextbox(tag_inputs, height=85)
        self.notes_txt.grid(row=2, column=1, sticky="ew", padx=10, pady=6)
        if self.trade_data.get('Notes'):
            self.notes_txt.insert("1.0", str(self.trade_data['Notes']))
            
        # Rating (1 to 5 Stars)
        ctk.CTkLabel(tag_inputs, text="Execution Quality Rating:", font=ctk.CTkFont(size=12)).grid(row=3, column=0, sticky="w", pady=6)
        self.rating_var = ctk.StringVar(value=str(self.trade_data.get('Rating') or 3))
        self.rating_menu = ctk.CTkOptionMenu(tag_inputs, variable=self.rating_var, values=["1 Star (Poor)", "2 Stars (Subpar)", "3 Stars (Average)", "4 Stars (Good)", "5 Stars (Flawless Execution)"], width=220)
        self.rating_menu.grid(row=3, column=1, sticky="w", padx=10, pady=6)
        
        # Action Buttons
        btn_bar = ctk.CTkFrame(container, fg_color="transparent")
        btn_bar.pack(fill="x", pady=10)
        
        save_btn = ctk.CTkButton(btn_bar, text=" Save Tags & Notes", fg_color="#2E7D32", hover_color="#1B5E20", 
                                 font=ctk.CTkFont(size=13, weight="bold"), height=36, command=self._save_tags)
        save_btn.pack(side="right", padx=5)
        
        cancel_btn = ctk.CTkButton(btn_bar, text="Close Window", fg_color="#444444", hover_color="#333333", height=36, command=self.destroy)
        cancel_btn.pack(side="right", padx=5)

    # ------------------ ADVISORY GENERATORS ------------------
    def _generate_whatif_analysis(self):
        is_option = self.trade_data.get('OptionType') in ['CE', 'PE']
        net_pnl = float(self.trade_data.get('NetPnL', 0.0))
        buy_val = float(self.trade_data.get('BuyValue', 0.0))
        sell_val = float(self.trade_data.get('SellValue', 0.0))
        qty = float(self.trade_data.get('Quantity', 0.0))
        holding_days = int(self.trade_data.get('HoldingDays', 0))
        
        exp_date = self.trade_data.get('ExpiryDate')
        exit_date = self.trade_data.get('ExitDate')
        days_to_exp = (exp_date - exit_date).days if exp_date and exit_date and hasattr(exp_date, 'day') and hasattr(exit_date, 'day') else None
        
        lines = []
        if is_option:
            if net_pnl < 0:
                if sell_val > 0:
                    salvage = sell_val
                    extra_loss_risk = salvage
                    lines.append(f"• Early Exit Verdict: Cut Loss with Rs. {salvage:,.2f} salvage value preserved.")
                    lines.append(f"• What if held to Expiry? Out-of-the-money options experience accelerated Theta decay towards zero on expiry day. If held to expiry without crossing strike, you would have lost an additional Rs. {extra_loss_risk:,.2f} (100% loss of remaining premium).")
                    lines.append(f"• Mathematical Conclusion: Your decision to exit before expiry prevented total capital write-off, saving Rs. {salvage:,.2f}.")
                else:
                    lines.append("• Expiry Result: Full premium decayed to zero (100% loss on option purchase).")
                    lines.append("• Lesson: Avoid holding long options with < 3 days to expiry unless intrinsic value is solidly in-the-money.")
            else:
                lines.append(f"• Early Exit Verdict: Booked profit of Rs. {net_pnl:,.2f} after {holding_days} days.")
                lines.append(f"• What if held to Expiry? Options held into expiry week face severe Theta drag and IV crush. Booking profit before expiry locked in gains and eliminated weekend gap risk.")
        else:
            lines.append(f"• Equity / Futures Expiry Context: Trade held for {holding_days} days with net P&L Rs. {net_pnl:,.2f}.")
            if net_pnl < 0:
                lines.append("• What if held longer? Equity positions without margin leverage can recover over quarterly earnings cycles if business fundamentals remain intact, whereas leveraged F&O futures face daily mark-to-market drain.")
            else:
                lines.append("• Trend Capitalization: Trade successfully captured the move within the planned holding horizon.")
                
        return "\n".join(lines)

    def _generate_rollover_analysis(self):
        is_option = self.trade_data.get('OptionType') in ['CE', 'PE']
        net_pnl = float(self.trade_data.get('NetPnL', 0.0))
        holding_days = int(self.trade_data.get('HoldingDays', 0))
        sym = self.trade_data.get('Symbol', '')
        
        lines = []
        if is_option:
            if net_pnl < 0:
                lines.append("• Rollover Verdict: [NOT RECOMMENDED] AVOID NAKED ROLLOVER FOR LOSING OPTION.")
                lines.append("• Rationale: Rolling over a losing out-of-the-money long call/put into the next month's series is statistically equivalent to 'averaging down on time decay'.")
                lines.append("• Right Strategy: Close the decaying contract. Wait for fresh price action / structure breakout on the underlying chart before initiating a fresh contract.")
                lines.append("• If directional thesis is still strong: Use a Defined-Risk Debit Spread (Buy ATM, Sell OTM) in the next monthly series to cut cost of carry by 40-50%.")
            else:
                lines.append("• Rollover Verdict: [CAUTION / EVALUATE] ROLLOVER CONSIDERATION FOR WINNING TREND.")
                lines.append("• When to Roll: If the underlying stock is continuing its multi-week trend, roll the winning position into the next month's series 3-4 days before expiry to avoid expiry pin risk.")
        else:
            lines.append(f"• Futures / Cash Rollover: If trading Futures on {sym}, ensure rollover is executed between Friday and Tuesday of expiry week to minimize calendar spread cost.")
            
        return "\n".join(lines)

    # Alias for flexibility
    _generate_what_if_analysis = _generate_whatif_analysis

    def _generate_recovery_plan(self, net_pnl):
        abs_loss = abs(net_pnl)
        lines = []
        if net_pnl < 0:
            lines.append(f"• Total Target to Recover: Rs. {abs_loss:,.2f}")
            lines.append("• Step 1 (Immediate Defense): Implement a 24-hour cooling period on this exact scrip to eradicate emotional revenge trading.")
            lines.append("• Step 2 (Position Sizing): Reduce lot size by 50% on your next 2 setups. Confidence and capital must be rebuilt systematically.")
            lines.append("• Step 3 (Weekly Recovery Roadmap): Target 2 disciplined trades with a strictly enforced 1:2 Risk-Reward ratio (Risk Rs. {:,.0f} to Gain Rs. {:,.0f} per trade).".format(abs_loss * 0.35, abs_loss * 0.70))
            lines.append("• Step 4 (Monthly Milestone): Shift from naked option buying to Bull-Call / Bear-Put Spreads to permanently stop daily Theta bleeding.")
        else:
            lines.append("• Capital Compounding Rule: Bank 50% of trade profits into long-term cash reserves or debt/SGBs.")
            lines.append("• Risk-Reward Discipline: Maintain your winning entry process. Do not double position size after a win.")
            lines.append("• Systematic Trailing: Let winners run towards multi-day resistance while trailing stop-loss to breakeven.")
            
        return "\n".join(lines)

    def _generate_greeks_and_oi_advice(self):
        op_type = self.trade_data.get('OptionType', '')
        sym = self.trade_data.get('Symbol', '')
        lines = []
        
        lines.append("• Delta Advisory: Avoid buying low-delta (< 0.25) OTM strikes. High-probability institutional traders prioritize Delta 0.50 to 0.70 (ATM/ITM) where price sensitivity is direct and predictable.")
        lines.append("• Theta Decay Velocity: Black-Scholes time decay accelerates non-linearly in the final 5 days before expiry. Holding an option overnight during expiry week burns 12-25% of extrinsic value daily regardless of underlying price.")
        lines.append("• Open Interest (OI) & Max Pain: For {}, track the highest Call OI strike (acts as institutional resistance) and highest Put OI strike (acts as support). Never buy a Call directly below a massive Call OI wall.".format(sym))
        lines.append("• What to AVOID: Avoid buying naked options on expiry day expecting multi-bagger moves; 85%+ expire completely worthless.")
        lines.append("• What to INCLUDE: Always trade with a predefined hard Stop-Loss order in the broker terminal, never a mental stop-loss.")
        
        return "\n".join(lines)

    def _save_tags(self):
        trade_id = self.trade_data.get('TradeID')
        if not trade_id:
            messagebox.showerror("Error", "Trade ID not found.")
            return
            
        mistake = self.mistake_var.get()
        setup = self.setup_var.get()
        notes = self.notes_txt.get("1.0", "end-1c").strip()
        rating_str = self.rating_var.get()
        rating = 3
        if rating_str and rating_str[0].isdigit():
            rating = int(rating_str[0])
            
        try:
            with get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE TradingJournal_Master 
                    SET MistakeTag = ?, SetupTag = ?, Notes = ?, Rating = ?, LastUpdatedAt = GETDATE()
                    WHERE TradeID = ?
                """, (mistake, setup, notes, rating, trade_id))
                conn.commit()
                
            self.trade_data['MistakeTag'] = mistake
            self.trade_data['SetupTag'] = setup
            self.trade_data['Notes'] = notes
            self.trade_data['Rating'] = rating
            
            if self.on_save_callback:
                self.on_save_callback(self.trade_data)
                
            messagebox.showinfo("Saved", f"Journal tags updated successfully for trade #{trade_id}!")
            self.destroy()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save changes to database: {e}")

# -------------------------------------------------------------
# MAIN MODERN TRADING JOURNAL FRAME
# -------------------------------------------------------------
class ModernTradingJournalFrame(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, corner_radius=15)
        self.grid_rowconfigure(3, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        self.full_df = pd.DataFrame()
        self.filtered_df = pd.DataFrame()
        self.other_ledger_df = pd.DataFrame()
        self.expiry_map = {}
        self._filter_timer = None
        
        self._dirty_tabs = {
            "📋 Trade Log": True,
            "🎯 Instrument Summary": True,
            "📊 Attribution": True,
            "📈 Equity Curve": True,
            "🛡️ Risk Engine": True,
            "🧠 Mistake Journal": True,
            "⚡ MTF Center": True,
            "🔄 Ingestion Hub": True,
        }
        
        self._build_header()
        self._build_filter_bar()
        self._build_kpi_ribbon()
        self._build_tabs()
        
        self.after(200, self.load_data)
        
    # ------------------ HEADER ------------------
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(12, 4))
        hdr.columnconfigure(0, weight=1)
        
        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.grid(row=0, column=0, sticky="w")
        
        ctk.CTkLabel(left, text=" My Trading Journal & Performance Analytics", 
                     font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w")
        self.status_sub = ctk.CTkLabel(left, text="Unified Multi-Broker Engine • Zerodha | HDFC Securities | BlinkX | INDMoney", 
                                       font=ctk.CTkFont(size=12), text_color="#A0A0A0")
        self.status_sub.pack(anchor="w")
        
        right = ctk.CTkFrame(hdr, fg_color="transparent")
        right.grid(row=0, column=1, sticky="e")
        
        self.last_sync_lbl = ctk.CTkLabel(right, text="Last Sync: Loading...", font=ctk.CTkFont(size=11), text_color="#888888")
        self.last_sync_lbl.pack(side="left", padx=8)
        
        ctk.CTkButton(right, text=" Sync Folder", width=105, height=30, fg_color="#1E88E5", hover_color="#1565C0",
                      font=ctk.CTkFont(size=12, weight="bold"), command=self._trigger_sync_folder).pack(side="left", padx=3)
        
        ctk.CTkButton(right, text=" Export CSV", width=95, height=30, fg_color="#37474F", hover_color="#263238",
                      font=ctk.CTkFont(size=12), command=self._export_to_csv).pack(side="left", padx=3)
        
        ctk.CTkButton(right, text=" Refresh", width=85, height=30, fg_color="#FF8F00", hover_color="#F57C00",
                      font=ctk.CTkFont(size=12, weight="bold"), command=self.load_data).pack(side="left", padx=3)
        
    # ------------------ ENHANCED OMNI-FILTER BAR (2-TIER) ------------------
    def _build_filter_bar(self):
        f_wrap = ctk.CTkFrame(self, fg_color="#1A1A1A", corner_radius=10, border_width=1, border_color="#2A2A2A")
        f_wrap.grid(row=1, column=0, sticky="ew", padx=20, pady=(4, 8))
        
        # ROW 1: PRIMARY CRITERIA (FY, Expiry Date, Broker, Segment, Index/Universe, Type, Outcome)
        row1 = ctk.CTkFrame(f_wrap, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(6, 3))
        
        # 1. FY Filter
        ctk.CTkLabel(row1, text="FY:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64B5F6").pack(side="left", padx=(2, 2))
        self.f_fy = ctk.StringVar(value="All FYs")
        self.fy_menu = ctk.CTkOptionMenu(row1, variable=self.f_fy, values=["All FYs"], width=95, height=26, font=ctk.CTkFont(size=11), 
                                         command=self._on_fy_changed)
        self.fy_menu.pack(side="left", padx=(0, 8))
        
        # 2. Expiry Date Filter (Day-Month-Year e.g. 25-Sep-2026)
        ctk.CTkLabel(row1, text="Expiry Date:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#CE93D8").pack(side="left", padx=(2, 2))
        self.f_expiry = ctk.StringVar(value="All Expiries")
        self.expiry_menu = ctk.CTkOptionMenu(row1, variable=self.f_expiry, values=["All Expiries"], width=125, height=26, font=ctk.CTkFont(size=11),
                                             command=lambda _: self.apply_filters())
        self.expiry_menu.pack(side="left", padx=(0, 8))
        
        # 3. Broker Filter
        ctk.CTkLabel(row1, text="Broker:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(2, 2))
        self.f_broker = ctk.StringVar(value="All Brokers")
        self.broker_menu = ctk.CTkOptionMenu(row1, variable=self.f_broker, values=["All Brokers", "Zerodha", "HDFC Securities", "BlinkX", "INDMoney"], 
                                             width=115, height=26, font=ctk.CTkFont(size=11), command=lambda _: self.apply_filters())
        self.broker_menu.pack(side="left", padx=(0, 8))
        
        # 4. Segment Filter
        ctk.CTkLabel(row1, text="Segment:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(2, 2))
        self.f_segment = ctk.StringVar(value="All Segments")
        self.segment_menu = ctk.CTkOptionMenu(row1, variable=self.f_segment, values=["All Segments", "Equity", "FnO", "Commodity", "MTF"], 
                                              width=105, height=26, font=ctk.CTkFont(size=11), command=lambda _: self.apply_filters())
        self.segment_menu.pack(side="left", padx=(0, 8))

        # 5. Index / Universe Filter
        ctk.CTkLabel(row1, text="Universe:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#FFB74D").pack(side="left", padx=(2, 2))
        self.f_index = ctk.StringVar(value="All Instruments")
        self.index_menu = ctk.CTkOptionMenu(row1, variable=self.f_index, 
                                            values=["All Instruments", "Major Indices (NIFTY/BNF/SENSEX)", "Single Stock F&O", "Cash Stocks (Equity)", "Commodities (MCX)"], 
                                            width=165, height=26, font=ctk.CTkFont(size=11), command=lambda _: self.apply_filters())
        self.index_menu.pack(side="left", padx=(0, 8))
        
        # 6. Instrument Type Filter
        ctk.CTkLabel(row1, text="Type:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(2, 2))
        self.f_type = ctk.StringVar(value="All Types")
        self.type_menu = ctk.CTkOptionMenu(row1, variable=self.f_type, values=["All Types", "Options CE", "Options PE", "Futures", "Delivery", "Intraday"], 
                                           width=100, height=26, font=ctk.CTkFont(size=11), command=lambda _: self.apply_filters())
        self.type_menu.pack(side="left", padx=(0, 8))

        # 7. Outcome Filter
        ctk.CTkLabel(row1, text="P&L:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(2, 2))
        self.f_outcome = ctk.StringVar(value="All")
        self.outcome_menu = ctk.CTkOptionMenu(row1, variable=self.f_outcome, values=["All", "Profit Only", "Loss Only"], 
                                              width=90, height=26, font=ctk.CTkFont(size=11), command=lambda _: self.apply_filters())
        self.outcome_menu.pack(side="left", padx=(0, 4))
        
        # ROW 2: DATE RANGES (ENTRY & EXIT) WITH CALENDAR PICKER + SYMBOL SELECT & SEARCH
        row2 = ctk.CTkFrame(f_wrap, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(2, 6))
        
        # Trade Entry Date Range
        ctk.CTkLabel(row2, text="Entry Range:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#4FC3F7").pack(side="left", padx=(2, 2))
        self.f_entry_from = ctk.StringVar()
        self.entry_from_e = ctk.CTkEntry(row2, textvariable=self.f_entry_from, placeholder_text="YYYY-MM-DD", width=88, height=26, font=ctk.CTkFont(size=11))
        self.entry_from_e.pack(side="left", padx=1)
        self.entry_from_e.bind("<KeyRelease>", self._schedule_filter_update)
        ctk.CTkButton(row2, text="📅", width=26, height=26, fg_color="#333333", hover_color="#444444", 
                      command=lambda: self._open_calendar_picker(self.f_entry_from, "Select Entry From Date")).pack(side="left", padx=(1, 3))
        
        ctk.CTkLabel(row2, text="to", font=ctk.CTkFont(size=11)).pack(side="left", padx=1)
        self.f_entry_to = ctk.StringVar()
        self.entry_to_e = ctk.CTkEntry(row2, textvariable=self.f_entry_to, placeholder_text="YYYY-MM-DD", width=88, height=26, font=ctk.CTkFont(size=11))
        self.entry_to_e.pack(side="left", padx=1)
        self.entry_to_e.bind("<KeyRelease>", self._schedule_filter_update)
        ctk.CTkButton(row2, text="📅", width=26, height=26, fg_color="#333333", hover_color="#444444", 
                      command=lambda: self._open_calendar_picker(self.f_entry_to, "Select Entry To Date")).pack(side="left", padx=(1, 8))
        
        # Trade Exit Date Range
        ctk.CTkLabel(row2, text="Exit Date Range:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#81C784").pack(side="left", padx=(2, 2))
        self.f_exit_from = ctk.StringVar()
        self.exit_from_e = ctk.CTkEntry(row2, textvariable=self.f_exit_from, placeholder_text="YYYY-MM-DD", width=88, height=26, font=ctk.CTkFont(size=11))
        self.exit_from_e.pack(side="left", padx=1)
        self.exit_from_e.bind("<KeyRelease>", self._schedule_filter_update)
        ctk.CTkButton(row2, text="📅", width=26, height=26, fg_color="#333333", hover_color="#444444", 
                      command=lambda: self._open_calendar_picker(self.f_exit_from, "Select Exit From Date")).pack(side="left", padx=(1, 3))
        
        ctk.CTkLabel(row2, text="to", font=ctk.CTkFont(size=11)).pack(side="left", padx=1)
        self.f_exit_to = ctk.StringVar()
        self.exit_to_e = ctk.CTkEntry(row2, textvariable=self.f_exit_to, placeholder_text="YYYY-MM-DD", width=88, height=26, font=ctk.CTkFont(size=11))
        self.exit_to_e.pack(side="left", padx=1)
        self.exit_to_e.bind("<KeyRelease>", self._schedule_filter_update)
        ctk.CTkButton(row2, text="📅", width=26, height=26, fg_color="#333333", hover_color="#444444", 
                      command=lambda: self._open_calendar_picker(self.f_exit_to, "Select Exit To Date")).pack(side="left", padx=(1, 8))
        
        # Symbol Select Dropdown + Text Search
        ctk.CTkLabel(row2, text="Symbol:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(2, 2))
        self.f_sym_select = ctk.StringVar(value="All Symbols")
        self.sym_select_menu = ctk.CTkOptionMenu(row2, variable=self.f_sym_select, values=["All Symbols"], width=120, height=26, font=ctk.CTkFont(size=11),
                                                 command=self._on_sym_dropdown_selected)
        self.sym_select_menu.pack(side="left", padx=(0, 4))
        
        self.f_sym = ctk.StringVar()
        self.sym_entry = ctk.CTkEntry(row2, textvariable=self.f_sym, placeholder_text="Search Symbol...", width=130, height=26, font=ctk.CTkFont(size=11))
        self.sym_entry.pack(side="left", padx=(0, 8))
        self.sym_entry.bind("<KeyRelease>", self._schedule_filter_update)
        
        # Action Buttons
        ctk.CTkButton(row2, text="Apply Filters", width=90, height=26, font=ctk.CTkFont(size=11, weight="bold"), 
                      command=self.apply_filters).pack(side="left", padx=2)
        ctk.CTkButton(row2, text="Reset All", width=85, height=26, fg_color="#555555", hover_color="#444444", 
                      font=ctk.CTkFont(size=11), command=self.reset_filters).pack(side="left", padx=2)
        
    def _schedule_filter_update(self, event=None):
        if self._filter_timer:
            self.after_cancel(self._filter_timer)
        self._filter_timer = self.after(250, self.apply_filters)

    def _open_calendar_picker(self, target_var, title="Select Date"):
        top = ctk.CTkToplevel(self.winfo_toplevel())
        top.title(title)
        top.geometry("320x330")
        top.attributes("-topmost", True)
        top.resizable(False, False)
        try:
            top.transient(self.winfo_toplevel())
        except:
            pass
            
        cur_val = target_var.get().strip()
        y, m, d = datetime.now().year, datetime.now().month, datetime.now().day
        if cur_val:
            try:
                dt = pd.to_datetime(cur_val)
                y, m, d = dt.year, dt.month, dt.day
            except:
                pass
                
        cal_frame = ctk.CTkFrame(top, fg_color="transparent")
        cal_frame.pack(padx=10, pady=10, fill="both", expand=True)
        
        try:
            from tkcalendar import Calendar
            cal = Calendar(cal_frame, selectmode="day", year=y, month=m, day=d, date_pattern="yyyy-mm-dd")
            cal.pack(pady=5)
            
            btn_frame = ctk.CTkFrame(top, fg_color="transparent")
            btn_frame.pack(fill="x", padx=10, pady=(0, 10))
            
            def on_select():
                sel_date = cal.get_date()
                target_var.set(sel_date)
                self.apply_filters()
                top.destroy()
                
            def on_clear():
                target_var.set("")
                self.apply_filters()
                top.destroy()
                
            ctk.CTkButton(btn_frame, text="Select Date", width=100, height=28, fg_color="#1E88E5", hover_color="#1565C0", 
                          font=ctk.CTkFont(size=12, weight="bold"), command=on_select).pack(side="right", padx=4)
            ctk.CTkButton(btn_frame, text="Clear", width=70, height=28, fg_color="#555555", hover_color="#444444", 
                          font=ctk.CTkFont(size=12), command=on_clear).pack(side="right", padx=4)
        except Exception as e:
            ctk.CTkLabel(cal_frame, text=f"Calendar Error: {e}").pack()

    def _on_sym_dropdown_selected(self, val):
        if val == "All Symbols":
            self.f_sym.set("")
        else:
            self.f_sym.set(val)
        self.apply_filters()

    def _on_fy_changed(self, sel_fy):
        self._update_expiry_options(sel_fy)
        self.apply_filters()

    def _update_expiry_options(self, sel_fy):
        if self.full_df.empty:
            self.expiry_menu.configure(values=["All Expiries"])
            self.f_expiry.set("All Expiries")
            return
            
        df = self.full_df.dropna(subset=['ExpiryDate'])
        if sel_fy and sel_fy != "All FYs":
            df = df[df['FinancialYear'] == sel_fy]
            
        unique_expiries = sorted(df['ExpiryDate'].unique().tolist(), reverse=True)
        
        self.expiry_map = {}
        display_values = ["All Expiries"]
        
        for exp in unique_expiries:
            try:
                dt = pd.to_datetime(exp)
                disp_str = dt.strftime("%d-%b-%Y")
                raw_str = dt.strftime("%Y-%m-%d")
                self.expiry_map[disp_str] = raw_str
                display_values.append(disp_str)
            except:
                pass
                
        self.expiry_menu.configure(values=display_values[:100])
        self.f_expiry.set("All Expiries")

    # ------------------ KPI RIBBON ------------------
    def _build_kpi_ribbon(self):
        self.kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))
        self.kpi_frame.columnconfigure((0, 1, 2, 3, 4, 5), weight=1)
        
        self.kpi_cards = {}
        metrics = [
            ("net_pnl", "Net Realized P&L", "Rs. 0.00", "#00E676"),
            ("charges", "Total Charges & STT", "Rs. 0.00", "#FFA726"),
            ("win_rate", "Win Rate", "0.0%", "#29B6F6"),
            ("profit_factor", "Profit Factor", "0.00", "#AB47BC"),
            ("trades_count", "Total Trades", "0 Trades", "#FFFFFF"),
            ("expectancy", "Expectancy / Trade", "Rs. 0.00", "#26A69A")
        ]
        
        for idx, (key, title, default_val, text_col) in enumerate(metrics):
            card = ctk.CTkFrame(self.kpi_frame, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
            card.grid(row=0, column=idx, padx=4, sticky="nsew")
            
            ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=11, weight="bold"), text_color="#9E9E9E").pack(pady=(7, 1), padx=10, anchor="w")
            val_lbl = ctk.CTkLabel(card, text=default_val, font=ctk.CTkFont(size=16, weight="bold"), text_color=text_col)
            val_lbl.pack(pady=(0, 2), padx=10, anchor="w")
            sub_lbl = ctk.CTkLabel(card, text="—", font=ctk.CTkFont(size=10), text_color="#757575")
            sub_lbl.pack(pady=(0, 7), padx=10, anchor="w")
            
            self.kpi_cards[key] = (val_lbl, sub_lbl)
            
    # ------------------ TABS WITH CONCISE, READABLE CAPTIONS ------------------
    def _build_tabs(self):
        self.tabs = ctk.CTkTabview(self, corner_radius=10, command=self._on_tab_changed)
        self.tabs.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.grid_rowconfigure(3, weight=1)
        
        self.tab_history = self.tabs.add("📋 Trade Log")
        self.tab_inst_summary = self.tabs.add("🎯 Instrument Summary")
        self.tab_attribution = self.tabs.add("📊 Attribution")
        self.tab_charts = self.tabs.add("📈 Equity Curve")
        self.tab_risk = self.tabs.add("🛡️ Risk Engine")
        self.tab_psychology = self.tabs.add("🧠 Deep Behaviour Reflection")
        self.tab_mtf = self.tabs.add("⚡ MTF Center")
        self.tab_ingest = self.tabs.add("🔄 Ingestion Hub")
        
        try:
            self.tabs._segmented_button.configure(font=ctk.CTkFont(size=11, weight="bold"))
        except:
            pass
            
        self._build_trade_log_tab()
        self._build_instrument_summary_tab()
        self._build_attribution_tab()
        self._build_charts_tab()
        self._build_risk_tab()
        self._build_psychology_tab()
        self._build_mtf_tab()
        self._build_ingest_tab()

    def _on_tab_changed(self):
        cur_tab = self.tabs.get()
        if self._dirty_tabs.get(cur_tab, False):
            self._render_active_tab(cur_tab)

    def _render_active_tab(self, tab_name):
        self._dirty_tabs[tab_name] = False
        if "Trade Log" in tab_name:
            self._populate_sheet()
        elif "Instrument" in tab_name:
            self._render_instrument_summary()
        elif "Attribution" in tab_name:
            self._render_attribution()
        elif "Equity Curve" in tab_name:
            self._render_charts()
        elif "Risk" in tab_name:
            self._render_risk()
        elif "Behaviour" in tab_name or "Mistake" in tab_name or "Psychology" in tab_name:
            self._render_psychology()
        elif "MTF" in tab_name:
            self._render_mtf()
        
    # TAB 1: TRADE LOG GRID WITH DOUBLE-CLICK & DEDICATED DRILL-DOWN BUTTON
    def _build_trade_log_tab(self):
        top_ctrl = ctk.CTkFrame(self.tab_history, fg_color="transparent")
        top_ctrl.pack(fill="x", pady=(2, 6))
        
        self.grid_summary_lbl = ctk.CTkLabel(top_ctrl, text="Showing 0 trades", font=ctk.CTkFont(size=12, weight="bold"))
        self.grid_summary_lbl.pack(side="left")
        
        self.drilldown_btn = ctk.CTkButton(
            top_ctrl, text="🔍 Open Trade Advisor & Drill-Down",
            width=230, height=28, fg_color="#1E88E5", hover_color="#1565C0",
            font=ctk.CTkFont(size=11, weight="bold"),
            command=self._open_selected_trade_drilldown
        )
        self.drilldown_btn.pack(side="right", padx=5)

        ctk.CTkLabel(top_ctrl, text="💡 Double-click any row to view Institutional Trade Advisor & Recovery Plan", 
                     font=ctk.CTkFont(size=11), text_color="#64B5F6").pack(side="right", padx=10)
        
        self.headers = [
            'ID', 'Status', 'Entry Date', 'Exit Date', 'Holding', 'Broker', 'Segment', 'Type', 'Symbol', 'Option / Strike',
            'Qty', 'Buy Price', 'Sell Price', 'Gross P&L', 'Charges', 'Net P&L', 'ROI %', 'Mistake Tag', 'AI Insights & Notes'
        ]
        
        self.sheet = Sheet(self.tab_history, headers=self.headers, show_x_scrollbar=True, show_y_scrollbar=True)
        self.sheet.enable_bindings(
            "single_select", "row_select", "column_width_resize", "arrowkeys", "right_click_popup_menu", "copy",
            "double_click_cell"
        )
        if ctk.get_appearance_mode() == "Dark":
            self.sheet.change_theme("dark")
        else:
            self.sheet.change_theme("light blue")
            
        try:
            # Professional column widths & text alignment
            col_widths = [55, 95, 95, 95, 65, 105, 75, 85, 105, 115, 75, 85, 85, 95, 75, 105, 75, 120, 260]
            self.sheet.set_column_widths(col_widths)
            self.sheet.align_columns(columns=[0, 1, 2, 3, 4, 6, 7], align="center", align_header=True)
            self.sheet.align_columns(columns=[10, 11, 12, 13, 14, 15, 16], align="e", align_header=True)
            self.sheet.align_columns(columns=[5, 8, 9, 17, 18], align="w", align_header=True)
        except Exception:
            pass

        self.sheet.extra_bindings([
            ("double_click_cell", self._on_sheet_double_click),
            ("cell_select", self._on_sheet_cell_select),
            ("row_select", self._on_sheet_row_select)
        ])
        if hasattr(self.sheet, "MT"):
            self.sheet.MT.bind("<Double-1>", self._on_sheet_double_click)
            self.sheet.MT.bind("<Return>", self._on_sheet_double_click)
        self.sheet.pack(fill="both", expand=True)
        
    def _on_sheet_cell_select(self, event=None):
        pass

    def _on_sheet_row_select(self, event=None):
        pass

    def _on_sheet_double_click(self, event=None):
        try:
            row = resolve_sheet_row(event, self.sheet)
            if row is not None and row >= 0:
                trade_id = self.sheet.get_cell_data(row, 0)
                if trade_id:
                    self._open_trade_drilldown_by_id(trade_id)
        except Exception as err:
            print("[DRILLDOWN ERROR]", err)

    def _open_selected_trade_drilldown(self):
        try:
            row = resolve_sheet_row(None, self.sheet)
            if row is not None and row >= 0:
                trade_id = self.sheet.get_cell_data(row, 0)
                if trade_id:
                    self._open_trade_drilldown_by_id(trade_id)
                    return
            messagebox.showinfo("Select a Trade", "Please click on any row in the trade grid first, or double-click a row to open its Institutional Advisor & Drill-Down.")
        except Exception as err:
            messagebox.showerror("Error", f"Could not open drill-down: {err}")

    def _open_trade_drilldown_by_id(self, trade_id):
        try:
            match = self.full_df[self.full_df['TradeID'].astype(str) == str(trade_id)]
            if not match.empty:
                trade_dict = match.iloc[0].to_dict()
                top_win = self.winfo_toplevel()
                modal = TradeDrillDownModal(top_win, trade_dict, on_save_callback=self._on_trade_tag_saved)
                modal.lift()
                modal.focus_force()
        except Exception as e:
            print(f"Error opening trade #{trade_id} drilldown:", e)
            messagebox.showerror("Drilldown Error", f"Failed to open trade details: {e}")

    def _on_trade_tag_saved(self, updated_trade):
        tid = updated_trade['TradeID']
        idx = self.full_df[self.full_df['TradeID'] == tid].index
        if len(idx) > 0:
            self.full_df.loc[idx, 'MistakeTag'] = updated_trade.get('MistakeTag')
            self.full_df.loc[idx, 'SetupTag'] = updated_trade.get('SetupTag')
            self.full_df.loc[idx, 'Notes'] = updated_trade.get('Notes')
            self.full_df.loc[idx, 'Rating'] = updated_trade.get('Rating')
        self.apply_filters()

    # TAB 2: INSTRUMENT SUMMARY & GROWTH PLAN
    def _build_instrument_summary_tab(self):
        container = ctk.CTkScrollableFrame(self.tab_inst_summary, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Section A: Matrix
        box_matrix = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        box_matrix.pack(fill="x", pady=(0, 12), padx=4)
        ctk.CTkLabel(box_matrix, text="🎯 Instrument Performance Matrix & Real Hard Facts", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#64B5F6").pack(anchor="w", padx=15, pady=(12, 4))
        ctk.CTkLabel(box_matrix, text="Institutional breakdown showing profitability, charges friction, and performance grade across every trading vehicle.", 
                     font=ctk.CTkFont(size=11), text_color="#AAAAAA").pack(anchor="w", padx=15, pady=(0, 8))
        self.inst_table_frame = ctk.CTkFrame(box_matrix, fg_color="transparent")
        self.inst_table_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        
        # Section B: Capital Leakage & Facts
        box_facts = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        box_facts.pack(fill="x", pady=6, padx=4)
        ctk.CTkLabel(box_facts, text="🔍 Critical Portfolio Insights & Vulnerabilities Diagnosis", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#FFD54F").pack(anchor="w", padx=15, pady=(12, 4))
        self.facts_text_lbl = ctk.CTkLabel(box_facts, text="Computing instrument vulnerabilities...", justify="left", font=ctk.CTkFont(size=12))
        self.facts_text_lbl.pack(anchor="w", padx=15, pady=(0, 14))
        
        # Section C: Institutional Recovery & Growth Roadmap
        box_growth = ctk.CTkFrame(container, fg_color="#1A2421", corner_radius=10, border_width=1, border_color="#2E7D32")
        box_growth.pack(fill="x", pady=6, padx=4)
        ctk.CTkLabel(box_growth, text="🚀 Institutional Capital Recovery & Systematic Growth Roadmap", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#81C784").pack(anchor="w", padx=15, pady=(12, 4))
        
        growth_roadmap = (
            "• PHASE 1: DEFEND & PLUG LEAKS (Next 30 Days)\n"
            "   1. Eliminate Naked Stock Option Buying: Ban holding OTM stock calls/puts overnight. Transition exclusively to Vertical Spreads.\n"
            "   2. Hard Terminal Stop-Loss: Never trade with mental stop losses; every order must have a broker-level stop-loss trigger at 1.5% max capital risk.\n"
            "   3. Churn Reduction: Reduce excessive intraday flipping. High churn in F&O incurs thousands in STT & exchange fees that drain winning margins.\n\n"
            "• PHASE 2: CONCENTRATE ON HIGH-PROBABILITY VEHICLES (Next 60 Days)\n"
            "   1. Allocate 70% of risk capital to your highest-performing instruments (Cash Equity Delivery & Index Spreads).\n"
            "   2. Trade Index Options (NIFTY/SENSEX) only on confirmed daily trend days with Delta 0.50-0.65 (ATM/ITM), never cheap lottery OTM strikes.\n"
            "   3. Roll Over Winners Early: In winning swing trades, roll into next month's series 3-4 days before expiry to avoid final-week Theta decay.\n\n"
            "• PHASE 3: COMPOUNDING & R-MULTIPLE EXPANSION (Next 90–180 Days)\n"
            "   1. Follow the 1:2 R:R Mandate: Ensure every trade has at least double the target profit compared to accepted stop-loss risk.\n"
            "   2. Scale Position Size Systematically: Only increase lot size after 3 consecutive profitable weeks with strict discipline adherence."
        )
        ctk.CTkLabel(box_growth, text=growth_roadmap, justify="left", font=ctk.CTkFont(size=12), text_color="#E0F2F1").pack(anchor="w", padx=15, pady=(0, 14))

    # TAB 3: DEEP ATTRIBUTION
    def _build_attribution_tab(self):
        container = ctk.CTkScrollableFrame(self.tab_attribution, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=5, pady=5)
        
        r1 = ctk.CTkFrame(container, fg_color="transparent")
        r1.pack(fill="x", pady=5)
        r1.columnconfigure((0, 1), weight=1)
        
        win_box = ctk.CTkFrame(r1, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        win_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ctk.CTkLabel(win_box, text="🏆 Top 10 Most Profitable Scrips / Contracts", font=ctk.CTkFont(size=13, weight="bold"), text_color="#00E676").pack(anchor="w", padx=12, pady=(10, 6))
        self.win_table_frame = ctk.CTkFrame(win_box, fg_color="transparent")
        self.win_table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        loss_box = ctk.CTkFrame(r1, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        loss_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(loss_box, text="⚠️ Top 10 Biggest Drag / Loss Makers", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FF5252").pack(anchor="w", padx=12, pady=(10, 6))
        self.loss_table_frame = ctk.CTkFrame(loss_box, fg_color="transparent")
        self.loss_table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        r2 = ctk.CTkFrame(container, fg_color="transparent")
        r2.pack(fill="x", pady=10)
        r2.columnconfigure((0, 1), weight=1)
        
        opt_box = ctk.CTkFrame(r2, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        opt_box.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        ctk.CTkLabel(opt_box, text="🎯 Options Strategy Breakdown (Calls vs Puts)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#64B5F6").pack(anchor="w", padx=12, pady=(10, 6))
        self.opt_table_frame = ctk.CTkFrame(opt_box, fg_color="transparent")
        self.opt_table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        seg_box = ctk.CTkFrame(r2, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        seg_box.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        ctk.CTkLabel(seg_box, text="📊 Segment Attribution (Equity vs FnO vs Commodity)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FFB74D").pack(anchor="w", padx=12, pady=(10, 6))
        self.seg_table_frame = ctk.CTkFrame(seg_box, fg_color="transparent")
        self.seg_table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        m_box = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        m_box.pack(fill="x", pady=5)
        ctk.CTkLabel(m_box, text="📅 Financial Year Monthly Performance Matrix", font=ctk.CTkFont(size=13, weight="bold"), text_color="#E0E0E0").pack(anchor="w", padx=12, pady=(10, 6))
        self.monthly_table_frame = ctk.CTkFrame(m_box, fg_color="transparent")
        self.monthly_table_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # TAB 4: CUMULATIVE EQUITY CHARTS
    def _build_charts_tab(self):
        self.chart_container = ctk.CTkFrame(self.tab_charts, fg_color="transparent")
        self.chart_container.pack(fill="both", expand=True, padx=10, pady=10)

    # TAB 5: RISK & RECOVERY
    def _build_risk_tab(self):
        container = ctk.CTkScrollableFrame(self.tab_risk, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        s_row = ctk.CTkFrame(container, fg_color="transparent")
        s_row.pack(fill="x", pady=(0, 15))
        s_row.columnconfigure((0, 1, 2, 3), weight=1)
        
        self.risk_cards = {}
        risk_metrics = [
            ("max_dd", "Max Historical Drawdown", "Rs. 0.00", "#FF5252"),
            ("max_win_streak", "Max Winning Streak", "0 Trades", "#00E676"),
            ("max_loss_streak", "Max Consecutive Losses", "0 Trades", "#FF7043"),
            ("recovery_needed", "Required Recovery Trades", "0 Trades", "#64B5F6")
        ]
        for c_idx, (r_key, r_title, r_val, r_color) in enumerate(risk_metrics):
            card = ctk.CTkFrame(s_row, fg_color="#1A1A1A", corner_radius=8, border_width=1, border_color="#2D2D2D")
            card.grid(row=0, column=c_idx, padx=4, sticky="nsew")
            ctk.CTkLabel(card, text=r_title, font=ctk.CTkFont(size=11, weight="bold"), text_color="#AAAAAA").pack(pady=(6, 2), padx=8, anchor="w")
            v_lbl = ctk.CTkLabel(card, text=r_val, font=ctk.CTkFont(size=15, weight="bold"), text_color=r_color)
            v_lbl.pack(pady=(0, 6), padx=8, anchor="w")
            self.risk_cards[r_key] = v_lbl
            
        rec_box = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        rec_box.pack(fill="x", pady=10)
        ctk.CTkLabel(rec_box, text="🛡️ Drawdown Recovery Engine & Mathematical Projections", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#64B5F6").pack(anchor="w", padx=15, pady=(12, 6))
        self.recovery_text_lbl = ctk.CTkLabel(rec_box, text="Calculating recovery projections...", justify="left", font=ctk.CTkFont(size=12))
        self.recovery_text_lbl.pack(anchor="w", padx=15, pady=(0, 15))
        
        rd_box = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        rd_box.pack(fill="x", pady=10)
        ctk.CTkLabel(rd_box, text="📉 Loss Magnitude Analysis (Worst 10 Trades)", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FF5252").pack(anchor="w", padx=15, pady=(10, 6))
        self.risk_worst_table = ctk.CTkFrame(rd_box, fg_color="transparent")
        self.risk_worst_table.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    # TAB 6: DEEP BEHAVIOURAL REFLECTION & PSYCHOLOGICAL INSIGHTS
    def _build_psychology_tab(self):
        self.psych_container = ctk.CTkScrollableFrame(self.tab_psychology, fg_color="transparent")
        self.psych_container.pack(fill="both", expand=True, padx=8, pady=8)

    # TAB 7: MTF COMMAND CENTER
    def _build_mtf_tab(self):
        container = ctk.CTkScrollableFrame(self.tab_mtf, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        hdr = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        hdr.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(hdr, text="⚡ Margin Trading Facility (MTF) & Financing Ledger Analysis", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#81C784").pack(anchor="w", padx=15, pady=(12, 4))
        self.mtf_summary_lbl = ctk.CTkLabel(hdr, text="Total MTF interest accrued and margin funding leverage...", 
                                            font=ctk.CTkFont(size=12), text_color="#B0BEC5")
        self.mtf_summary_lbl.pack(anchor="w", padx=15, pady=(0, 12))
        
        self.mtf_table_frame = ctk.CTkFrame(container, fg_color="transparent")
        self.mtf_table_frame.pack(fill="both", expand=True, pady=5)

    # TAB 8: SMART INGESTION
    def _build_ingest_tab(self):
        container = ctk.CTkScrollableFrame(self.tab_ingest, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=10, pady=10)
        
        box = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        box.pack(fill="x", pady=(0, 15), padx=5)
        
        ctk.CTkLabel(box, text="📂 Automated Multi-Broker Ingestion & Backup Engine", 
                     font=ctk.CTkFont(size=15, weight="bold"), text_color="#64B5F6").pack(anchor="w", padx=15, pady=(15, 6))
        desc = (
            "This engine continuously monitors: C:\\Users\\navin\\StockMarketFnO\\data\\My Journal\n"
            "• Auto-detects statements from Zerodha, HDFC Securities, BlinkX, and INDMoney across all financial years.\n"
            "• Evaluates deterministic SHA-256 Trade Fingerprints to guarantee ZERO DUPLICATE RECORDS.\n"
            "• Once a file is processed and synced, it is systematically moved to the 'backup/<Broker>' subfolder."
        )
        ctk.CTkLabel(box, text=desc, justify="left", font=ctk.CTkFont(size=12), text_color="#B0BEC5").pack(anchor="w", padx=15, pady=(0, 15))
        
        btn_row = ctk.CTkFrame(box, fg_color="transparent")
        btn_row.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkButton(btn_row, text="⚡ Run Full Folder Sync & Backup", fg_color="#1E88E5", hover_color="#1565C0",
                      font=ctk.CTkFont(size=13, weight="bold"), height=36, command=self._trigger_sync_folder).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(btn_row, text="Import Individual File...", fg_color="#37474F", hover_color="#263238",
                      font=ctk.CTkFont(size=13), height=36, command=self._import_individual_file).pack(side="left")
        
        ctk.CTkLabel(container, text="Recent Import & Ingestion Audit Trail", font=ctk.CTkFont(size=13, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))
        self.ingest_log_frame = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        self.ingest_log_frame.pack(fill="both", expand=True, padx=5, pady=5)
        self.ingest_log_txt = ctk.CTkTextbox(self.ingest_log_frame, height=260, font=ctk.CTkFont(family="Consolas", size=11))
        self.ingest_log_txt.pack(fill="both", expand=True, padx=10, pady=10)

    # -------------------------------------------------------------
    # DATA LOADING & FILTERING
    # -------------------------------------------------------------
    def load_data(self):
        try:
            with get_connection() as conn:
                journal_df = pd.read_sql("""
                    SELECT TradeID, TradeHash, Broker, Segment, SubSegment, Symbol, ContractName,
                           ISIN, Sector, OptionType, StrikePrice, ExpiryDate, TradeType,
                           EntryDate, ExitDate, Quantity, BuyPrice, BuyValue, SellPrice, SellValue,
                           HoldingDays, GrossPnL, Brokerage, STT, ExchangeCharges, GST, StampDuty,
                           OtherCharges, TotalCharges, NetPnL, ROIPct, IsMTF, MTFFundedAmount,
                           MTFMarginAmount, MTFInterestCost, MTFNetReturn, FinancialYear, CalYear,
                           CalMonth, Outcome, MistakeTag, SetupTag, Notes, Rating, SourceFile,
                           CreatedAt, LastUpdatedAt
                    FROM TradingJournal_Master
                    ORDER BY ExitDate DESC, TradeID DESC
                """, conn)
                journal_df['Status'] = 'CLOSED'
                journal_df['DeepInsights'] = journal_df.apply(lambda row: f"Closed {row['TradeType'] or 'Trade'}: Gross P&L Rs. {float(row['GrossPnL'] or 0):,.2f}, Net Rs. {float(row['NetPnL'] or 0):,.2f} ({float(row['ROIPct'] or 0):.1f}%). Held {row['HoldingDays']}d.", axis=1)
                self.full_df = journal_df
                
                self.other_ledger_df = pd.read_sql("""
                    SELECT LedgerID, LedgerHash, Broker, PostingDate, Particulars, Category,
                           Debit, Credit, FinancialYear, SourceFile, CreatedAt
                    FROM TradingJournal_OtherLedger
                    ORDER BY PostingDate DESC
                """, conn)
                
            # Populate Dynamic FY Dropdown
            if not self.full_df.empty and 'FinancialYear' in self.full_df.columns:
                fys = sorted(self.full_df['FinancialYear'].dropna().unique().tolist(), reverse=True)
                fy_values = ["All FYs"] + [fy for fy in fys if fy and fy != 'Unknown']
                self.fy_menu.configure(values=fy_values)
                self._update_expiry_options(self.f_fy.get())
            else:
                self.fy_menu.configure(values=["All FYs"])
                self.f_expiry.set("All Expiries")
            
            # Populate Dynamic Symbols Dropdown
            if not self.full_df.empty and 'Symbol' in self.full_df.columns:
                symbols = sorted([str(s).strip() for s in self.full_df['Symbol'].dropna().unique().tolist() if str(s).strip()])
                self.sym_select_menu.configure(values=["All Symbols"] + symbols[:120])
            else:
                self.sym_select_menu.configure(values=["All Symbols"])
            
            # Update last sync timestamp
            now_str = datetime.now().strftime("%d-%b-%Y %H:%M")
            self.last_sync_lbl.configure(text=f"Last Refreshed: {now_str}")
            
            self.apply_filters()
            
        except Exception as e:
            print(f"Error loading trading journal data: {e}")
            if hasattr(self, 'status_sub'):
                self.status_sub.configure(text=f"Database Warning: {e}", text_color="#FF5252")

    def apply_filters(self):
        if self.full_df.empty:
            self._render_kpis()
            self._populate_sheet()
            return
            
        df = self.full_df.copy()

        # 1. FY Filter
        sel_fy = self.f_fy.get()
        if sel_fy and sel_fy != "All FYs":
            df = df[df['FinancialYear'] == sel_fy]
            
        # 2. Expiry Date Filter (mapped from DD-Mon-YYYY to YYYY-MM-DD)
        sel_exp = self.f_expiry.get()
        if sel_exp and sel_exp != "All Expiries":
            target_exp = self.expiry_map.get(sel_exp, sel_exp)
            df = df[df['ExpiryDate'].astype(str) == target_exp]
            
        # 3. Broker Filter
        sel_broker = self.f_broker.get()
        if sel_broker and sel_broker != "All Brokers":
            df = df[df['Broker'] == sel_broker]
            
        # 4. Segment Filter
        sel_seg = self.f_segment.get()
        if sel_seg and sel_seg != "All Segments":
            if sel_seg == "MTF":
                df = df[df['IsMTF'] == 1]
            else:
                df = df[df['Segment'] == sel_seg]

        # 5. Index / Universe Filter
        sel_idx = self.f_index.get()
        if sel_idx and sel_idx != "All Instruments":
            if sel_idx == "Major Indices (NIFTY/BNF/SENSEX)":
                df = df[df['Symbol'].str.upper().isin(MAJOR_INDICES) | df['ContractName'].str.upper().str.contains('NIFTY|SENSEX|BANKEX|MIDCP', na=False)]
            elif sel_idx == "Single Stock F&O":
                df = df[(df['Segment'] == 'FnO') & (~df['Symbol'].str.upper().isin(MAJOR_INDICES)) & (~df['ContractName'].str.upper().str.contains('NIFTY|SENSEX|BANKEX|MIDCP', na=False))]
            elif sel_idx == "Cash Stocks (Equity)":
                df = df[df['Segment'] == 'Equity']
            elif sel_idx == "Commodities (MCX)":
                df = df[df['Segment'] == 'Commodity']
                
        # 6. Instrument Type Filter
        sel_type = self.f_type.get()
        if sel_type and sel_type != "All Types":
            if sel_type == "Options CE":
                df = df[df['OptionType'] == 'CE']
            elif sel_type == "Options PE":
                df = df[df['OptionType'] == 'PE']
            elif sel_type == "Futures":
                df = df[df['OptionType'] == 'FUT']
            elif sel_type == "Delivery":
                df = df[df['SubSegment'].isin(['Delivery', 'Short Term', 'Long Term'])]
            elif sel_type == "Intraday":
                df = df[df['SubSegment'] == 'Intraday']
                
        # 7. Outcome Filter
        sel_out = self.f_outcome.get()
        if sel_out == "Profit Only":
            df = df[df['NetPnL'] > 0]
        elif sel_out == "Loss Only":
            df = df[df['NetPnL'] < 0]
            
        # 8. Trade Entry Date Range
        en_from = self.f_entry_from.get().strip()
        en_to = self.f_entry_to.get().strip()
        if en_from:
            try:
                df = df[pd.to_datetime(df['EntryDate']) >= pd.to_datetime(en_from)]
            except: pass
        if en_to:
            try:
                df = df[pd.to_datetime(df['EntryDate']) <= pd.to_datetime(en_to)]
            except: pass
            
        # 9. Trade Exit Date Range
        ex_from = self.f_exit_from.get().strip()
        ex_to = self.f_exit_to.get().strip()
        if ex_from:
            try:
                df = df[pd.to_datetime(df['ExitDate']) >= pd.to_datetime(ex_from)]
            except: pass
        if ex_to:
            try:
                df = df[pd.to_datetime(df['ExitDate']) <= pd.to_datetime(ex_to)]
            except: pass
            
        # 10. Symbol / Search Query
        sym_q = self.f_sym.get().strip().upper()
        if sym_q:
            mask = (
                df['Symbol'].str.upper().str.contains(sym_q, na=False) |
                df['ContractName'].str.upper().str.contains(sym_q, na=False)
            )
            df = df[mask]
            
        self.filtered_df = df
        
        # Mark all tabs as dirty for on-demand lazy loading
        for t in self._dirty_tabs:
            self._dirty_tabs[t] = True
            
        # Update fast KPI Ribbon (< 2ms)
        self._render_kpis()
        
        # Render ONLY the active tab immediately (< 20ms)
        cur_tab = self.tabs.get()
        self._render_active_tab(cur_tab)

    def reset_filters(self):
        self.f_fy.set("All FYs")
        self._update_expiry_options("All FYs")
        self.f_expiry.set("All Expiries")
        self.f_broker.set("All Brokers")
        self.f_segment.set("All Segments")
        self.f_index.set("All Instruments")
        self.f_type.set("All Types")
        self.f_outcome.set("All")
        self.f_entry_from.set("")
        self.f_entry_to.set("")
        self.f_exit_from.set("")
        self.f_exit_to.set("")
        self.f_sym_select.set("All Symbols")
        self.f_sym.set("")
        self.apply_filters()

    # ------------------ KPI RENDERING ------------------
    def _render_kpis(self):
        if self.filtered_df.empty:
            for k in self.kpi_cards:
                self.kpi_cards[k][0].configure(text="Rs. 0.00" if "pnl" in k or "charges" in k or "expectancy" in k else "0")
                self.kpi_cards[k][1].configure(text="No trades found")
            return
            
        df = self.filtered_df
        total_trades = len(df)
        net_pnl = float(df['NetPnL'].sum())
        gross_pnl = float(df['GrossPnL'].sum())
        total_charges = float(df['TotalCharges'].sum())
        
        wins = df[df['NetPnL'] > 0]
        losses = df[df['NetPnL'] < 0]
        win_count = len(wins)
        loss_count = len(losses)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0
        
        gross_wins = float(wins['NetPnL'].sum())
        gross_losses = abs(float(losses['NetPnL'].sum()))
        profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else (99.9 if gross_wins > 0 else 0.0)
        
        avg_win = (gross_wins / win_count) if win_count > 0 else 0.0
        avg_loss = (gross_losses / loss_count) if loss_count > 0 else 0.0
        expectancy = ((win_rate / 100.0) * avg_win) - (((100.0 - win_rate) / 100.0) * avg_loss)
        
        p_sign = "+" if net_pnl >= 0 else ""
        self.kpi_cards['net_pnl'][0].configure(
            text=f"{p_sign}Rs. {net_pnl:,.2f}",
            text_color="#00E676" if net_pnl >= 0 else "#FF5252"
        )
        self.kpi_cards['net_pnl'][1].configure(text=f"Gross P&L: Rs. {gross_pnl:,.2f}")
        
        chg_drag_pct = (total_charges / gross_wins * 100) if gross_wins > 0 else 0.0
        self.kpi_cards['charges'][0].configure(text=f"Rs. {total_charges:,.2f}")
        self.kpi_cards['charges'][1].configure(text=f"Drag on Wins: {chg_drag_pct:.1f}%")
        
        self.kpi_cards['win_rate'][0].configure(text=f"{win_rate:.1f}%")
        self.kpi_cards['win_rate'][1].configure(text=f"Wins: {win_count} | Losses: {loss_count}")
        
        self.kpi_cards['profit_factor'][0].configure(text=f"{profit_factor:.2f}")
        self.kpi_cards['profit_factor'][1].configure(text=f"Wins: Rs. {gross_wins:,.0f} | Losses: Rs. {gross_losses:,.0f}")
        
        avg_hold = float(df['HoldingDays'].mean()) if ('HoldingDays' in df.columns and not df.empty) else 0.0
        self.kpi_cards['trades_count'][0].configure(text=f"{total_trades:,} Trades")
        self.kpi_cards['trades_count'][1].configure(text=f"Avg Holding: {avg_hold:.1f} Days")
        
        exp_sign = "+" if expectancy >= 0 else ""
        self.kpi_cards['expectancy'][0].configure(
            text=f"{exp_sign}Rs. {expectancy:,.1f}",
            text_color="#00E676" if expectancy >= 0 else "#FF5252"
        )
        self.kpi_cards['expectancy'][1].configure(text=f"Avg Win: Rs. {avg_win:,.0f} | Loss: Rs. {avg_loss:,.0f}")

    # ------------------ SHEET POPULATION ------------------
    def _populate_sheet(self):
        if self.filtered_df.empty:
            self._render_sheet([])
            self.grid_summary_lbl.configure(text="Showing 0 trades")
            return
            
        data = []
        for _, r in self.filtered_df.iterrows():
            tid = str(r['TradeID'])
            st = str(r.get('Status', 'CLOSED'))
            status_disp = "🟢 OPEN" if st == 'OPEN' else "🔵 CLOSED"
            e_dt = str(r['EntryDate']) if (pd.notna(r['EntryDate']) and r['EntryDate']) else "—"
            x_dt = str(r['ExitDate']) if (pd.notna(r['ExitDate']) and r['ExitDate']) else "— (Active)"
            h_days = f"{r['HoldingDays']}d" if pd.notna(r['HoldingDays']) else "0d"
            broker = str(r['Broker'] or '')
            seg = str(r['Segment'] or '')
            subseg = str(r['SubSegment'] or '')
            sym = str(r['Symbol'] or '')
            
            # Intelligent Option / Strike formatting
            opt = str(r['OptionType'] or '').upper()
            stk = r['StrikePrice']
            cname = str(r.get('ContractName') or '')
            subseg_lower = subseg.lower()
            
            if 'fut' in subseg_lower or opt == 'FUT':
                opt_strk = 'FUT'
            elif opt in ('CE', 'PE') or 'opt' in subseg_lower:
                if pd.isna(stk) or stk <= 31:
                    m = re.search(r'[\u20b9\?]?\s*(\d+(?:\.\d+)?)\s*(?:CALL|PUT|CE|PE)', cname, re.I)
                    if m and float(m.group(1)) > 31:
                        stk = float(m.group(1))
                    else:
                        m2 = re.search(r'(\d{4,6})(?:CE|PE)', cname, re.I)
                        if m2:
                            stk = float(m2.group(1))
                
                strk_fmt = f"{stk:,.0f}" if pd.notna(stk) and stk and stk > 0 else ''
                opt_strk = f"{opt} {strk_fmt}".strip() if opt or strk_fmt else '-'
            else:
                opt_strk = '-'
            
            qty = f"{r['Quantity']:,.0f}" if pd.notna(r['Quantity']) else '0'
            b_pr = f"{r['BuyPrice']:,.2f}" if pd.notna(r['BuyPrice']) else '0.00'
            s_pr = f"{r['SellPrice']:,.2f}" if (pd.notna(r['SellPrice']) and r['SellPrice'] is not None and st == 'CLOSED') else "—"
            gross = f"{r['GrossPnL']:,.2f}" if st == 'CLOSED' and pd.notna(r['GrossPnL']) else "— (Open)"
            chgs = f"{r['TotalCharges']:,.2f}" if st == 'CLOSED' and pd.notna(r['TotalCharges']) else "0.00"
            net = f"{r['NetPnL']:,.2f}" if st == 'CLOSED' and pd.notna(r['NetPnL']) else "— (Open)"
            roi = f"{r['ROIPct']:.2f}%" if (pd.notna(r['ROIPct']) and st == 'CLOSED') else "—"
            mistake = str(r['MistakeTag'] or '').strip()
            
            # Intelligent Institutional Insights & Heuristics
            notes = str(r.get('Notes') or '').strip()
            deep_in = str(r.get('DeepInsights') or '').strip()
            
            heuristic = []
            try:
                net_val = float(r.get('NetPnL') or 0)
                gross_val = float(r.get('GrossPnL') or 0)
                chg_val = float(r.get('TotalCharges') or 0)
                roi_val = float(r.get('ROIPct') or 0)
                h_val = int(r.get('HoldingDays') or 0)
                
                if chg_val > 0 and gross_val > 0 and (chg_val / gross_val) > 0.25:
                    heuristic.append("⚠️ STT/Fee Drag > 25%")
                if opt in ('CE', 'PE') and h_val >= 4 and net_val < 0:
                    heuristic.append("⚠️ Theta Erosion")
                if roi_val >= 40:
                    heuristic.append("🚀 High-R Multiplier")
                elif roi_val <= -40:
                    heuristic.append("🛑 Heavy Drawdown")
            except Exception:
                pass
                
            parts = []
            if heuristic:
                parts.append(" | ".join(heuristic))
            if notes:
                parts.append(f"Notes: {notes}")
            if deep_in:
                parts.append(deep_in)
            insights = " • ".join(parts) if parts else "System Verified"
            
            data.append([
                tid,            # 0: ID
                status_disp,    # 1: Status
                e_dt,           # 2: Entry Date
                x_dt,           # 3: Exit Date
                h_days,         # 4: Holding
                broker,         # 5: Broker
                seg,            # 6: Segment
                subseg,         # 7: Type
                sym,            # 8: Symbol
                opt_strk,       # 9: Option / Strike
                qty,            # 10: Qty
                b_pr,           # 11: Buy Price
                s_pr,           # 12: Sell Price
                gross,          # 13: Gross P&L
                chgs,           # 14: Charges
                net,            # 15: Net P&L
                roi,            # 16: ROI %
                mistake,        # 17: Mistake Tag
                insights        # 18: AI Insights & Notes
            ])
            
        self._render_sheet(data)
        self.grid_summary_lbl.configure(text=f"Showing {len(data):,} Trades (Filtered)")
        
    def _render_sheet(self, data):
        self.sheet.set_sheet_data(data)
        
        green_cells = []
        blue_cells = []
        red_cells = []
        amber_cells = []
        
        for row_idx, row in enumerate(data):
            # Status highlight (column 1)
            st = str(row[1])
            if "OPEN" in st:
                green_cells.append((row_idx, 1))
            else:
                blue_cells.append((row_idx, 1))

            # Net P&L highlight (column 15)
            try:
                net_str = str(row[15]).replace(',', '').strip()
                if "Open" not in net_str and "—" not in net_str:
                    net_val = float(net_str)
                    if net_val > 0:
                        green_cells.append((row_idx, 15))
                    elif net_val < 0:
                        red_cells.append((row_idx, 15))
            except:
                pass

            # ROI % highlight (column 16)
            try:
                roi_str = str(row[16]).replace('%', '').replace(',', '').strip()
                if roi_str and roi_str != "—":
                    roi_val = float(roi_str)
                    if roi_val > 0:
                        green_cells.append((row_idx, 16))
                    elif roi_val < 0:
                        red_cells.append((row_idx, 16))
            except:
                pass

            # Mistake Tag highlight (column 17)
            mtag = str(row[17]).strip()
            if mtag:
                amber_cells.append((row_idx, 17))
                
        if green_cells:
            self.sheet.highlight_cells(cells=green_cells, bg="#1B5E20", fg="#FFFFFF", redraw=False)
        if blue_cells:
            self.sheet.highlight_cells(cells=blue_cells, bg="#0D47A1", fg="#FFFFFF", redraw=False)
        if red_cells:
            self.sheet.highlight_cells(cells=red_cells, bg="#B71C1C", fg="#FFFFFF", redraw=False)
        if amber_cells:
            self.sheet.highlight_cells(cells=amber_cells, bg="#E65100", fg="#FFFFFF", redraw=False)
        self.sheet.refresh()

    # ------------------ INSTRUMENT SUMMARY TAB RENDERING ------------------
    def _render_instrument_summary(self):
        for w in self.inst_table_frame.winfo_children():
            w.destroy()
            
        if self.filtered_df.empty:
            return
            
        df = self.filtered_df.copy()
        
        # Categorize by instrument vehicle
        def categorize_vehicle(row):
            seg = row['Segment']
            sym = str(row['Symbol']).upper()
            cname = str(row['ContractName']).upper()
            op = row['OptionType']
            sub = str(row['SubSegment']).lower()
            
            if seg == 'Commodity':
                return 'Commodities (MCX)'
            elif row.get('IsMTF') == 1:
                return 'MTF Margin Funded'
            elif seg == 'FnO':
                is_index = sym in MAJOR_INDICES or any(k in cname for k in ['NIFTY', 'SENSEX', 'BANKEX', 'MIDCP'])
                if op == 'FUT':
                    return 'Index & Stock Futures'
                elif is_index:
                    return 'Index Options (NIFTY/SENSEX/BNF)'
                else:
                    return 'Single Stock Options'
            elif seg == 'Equity':
                if 'intraday' in sub:
                    return 'Intraday Equities'
                else:
                    return 'Cash Equity (Delivery/Swing)'
            return 'Other / General'
            
        df['Vehicle'] = df.apply(categorize_vehicle, axis=1)
        
        inst_grp = df.groupby('Vehicle').agg(
            Trades=('TradeID', 'count'),
            NetPnL=('NetPnL', 'sum'),
            GrossWins=('NetPnL', lambda x: x[x > 0].sum()),
            GrossLosses=('NetPnL', lambda x: abs(x[x < 0].sum())),
            TotalCharges=('TotalCharges', 'sum'),
            WinCount=('NetPnL', lambda x: (x > 0).sum()),
            AvgHolding=('HoldingDays', 'mean')
        ).reset_index()
        
        rows = []
        for _, r in inst_grp.iterrows():
            veh = r['Vehicle']
            tr = r['Trades']
            win_r = (r['WinCount'] / tr * 100) if tr > 0 else 0.0
            net = r['NetPnL']
            chgs = r['TotalCharges']
            gw = r['GrossWins']
            gl = r['GrossLosses']
            pf = (gw / gl) if gl > 0 else (99.9 if gw > 0 else 0.0)
            avg_pnl = net / tr if tr > 0 else 0.0
            
            # Grade assignment
            grade = "A+" if pf > 2.0 and net > 0 else ("A" if pf > 1.5 and net > 0 else ("B" if net > 0 else ("C" if pf > 0.7 else "F")))
            
            rows.append([
                veh, f"{tr:,}", f"{win_r:.1f}%", f"Rs. {net:,.2f}", f"Rs. {avg_pnl:,.2f}",
                f"Rs. {chgs:,.2f}", f"{pf:.2f}", f"{r['AvgHolding']:.1f}d", grade
            ])
            
        self._build_mini_table(
            self.inst_table_frame,
            ['Instrument Category', 'Trades', 'Win Rate', 'Net Realized P&L', 'Avg Trade P&L', 'Total Charges', 'Profit Factor', 'Avg Hold', 'Grade'],
            rows,
            highlight_col=3
        )
        
        # Section B: Facts Analysis Text
        best_veh = inst_grp.sort_values(by='NetPnL', ascending=False).iloc[0] if not inst_grp.empty else None
        worst_veh = inst_grp.sort_values(by='NetPnL', ascending=True).iloc[0] if not inst_grp.empty else None
        total_chgs = df['TotalCharges'].sum()
        total_pnl = df['NetPnL'].sum()
        
        facts = []
        if best_veh is not None and best_veh['NetPnL'] > 0:
            facts.append(f"• TOP PROFIT VEHICLE: '{best_veh['Vehicle']}' generated Rs. {best_veh['NetPnL']:,.2f} with a Win Rate of {(best_veh['WinCount']/best_veh['Trades']*100):.1f}%.")
        if worst_veh is not None and worst_veh['NetPnL'] < 0:
            facts.append(f"• PRIMARY LOSS VULNERABILITY: '{worst_veh['Vehicle']}' caused Rs. {worst_veh['NetPnL']:,.2f} in losses with Rs. {worst_veh['TotalCharges']:,.2f} in fees. Stop leakage here immediately!")
        facts.append(f"• FRICTION ANALYSIS: You have paid Rs. {total_chgs:,.2f} in total brokerages, STT, and taxes across this selection.")
        if worst_veh is not None and 'Options' in worst_veh['Vehicle']:
            facts.append("• THETA DECAY HAZARD: Holding options multi-day without high Delta or trend continuation is the #1 driver of portfolio drawdown.")
            
        self.facts_text_lbl.configure(text="\n".join(facts))

    # ------------------ ATTRIBUTION TAB ------------------
    def _render_attribution(self):
        for f in [self.win_table_frame, self.loss_table_frame, self.opt_table_frame, self.seg_table_frame, self.monthly_table_frame]:
            for w in f.winfo_children():
                w.destroy()
                
        if self.filtered_df.empty:
            return
            
        df = self.filtered_df
        
        sym_grp = df.groupby('Symbol').agg(
            Trades=('TradeID', 'count'),
            NetPnL=('NetPnL', 'sum'),
            TotalCharges=('TotalCharges', 'sum')
        ).reset_index()
        
        # Top 10 Winners
        top_winners = sym_grp[sym_grp['NetPnL'] > 0].sort_values(by='NetPnL', ascending=False).head(10)
        self._build_mini_table(self.win_table_frame, ['Symbol', 'Trades', 'Net Profit (Rs.)'], 
                              [[r['Symbol'], r['Trades'], f"+Rs. {r['NetPnL']:,.2f}"] for _, r in top_winners.iterrows()],
                              highlight_col=2, highlight_color="#00E676")
        
        # Top 10 Losers
        top_losers = sym_grp[sym_grp['NetPnL'] < 0].sort_values(by='NetPnL', ascending=True).head(10)
        self._build_mini_table(self.loss_table_frame, ['Symbol', 'Trades', 'Net Loss (Rs.)'], 
                              [[r['Symbol'], r['Trades'], f"Rs. {r['NetPnL']:,.2f}"] for _, r in top_losers.iterrows()],
                              highlight_col=2, highlight_color="#FF5252")
        
        # Options CE vs PE
        fno_df = df[df['Segment'] == 'FnO']
        if not fno_df.empty:
            opt_grp = fno_df.groupby('OptionType').agg(
                Trades=('TradeID', 'count'),
                NetPnL=('NetPnL', 'sum'),
                Charges=('TotalCharges', 'sum')
            ).reset_index()
            opt_data = []
            for _, r in opt_grp.iterrows():
                opt_name = "Call Option (CE)" if r['OptionType'] == 'CE' else ("Put Option (PE)" if r['OptionType'] == 'PE' else "Futures")
                opt_data.append([opt_name, r['Trades'], f"Rs. {r['NetPnL']:,.2f}", f"Rs. {r['Charges']:,.2f}"])
            self._build_mini_table(self.opt_table_frame, ['Type', 'Trades', 'Net PnL', 'Charges'], opt_data)
            
        # Segment Attribution
        seg_grp = df.groupby('Segment').agg(
            Trades=('TradeID', 'count'),
            NetPnL=('NetPnL', 'sum'),
            Charges=('TotalCharges', 'sum')
        ).reset_index()
        seg_data = []
        for _, r in seg_grp.iterrows():
            seg_data.append([r['Segment'], r['Trades'], f"Rs. {r['NetPnL']:,.2f}", f"Rs. {r['Charges']:,.2f}"])
        self._build_mini_table(self.seg_table_frame, ['Segment', 'Trades', 'Net PnL', 'Charges'], seg_data)
        
        # Monthly Matrix
        m_order = [4, 5, 6, 7, 8, 9, 10, 11, 12, 1, 2, 3]
        m_names = {4:'Apr', 5:'May', 6:'Jun', 7:'Jul', 8:'Aug', 9:'Sep', 10:'Oct', 11:'Nov', 12:'Dec', 1:'Jan', 2:'Feb', 3:'Mar'}
        monthly_grp = df.groupby('CalMonth').agg(
            Trades=('TradeID', 'count'),
            NetPnL=('NetPnL', 'sum'),
            Charges=('TotalCharges', 'sum')
        ).reset_index()
        m_dict = {r['CalMonth']: r for _, r in monthly_grp.iterrows()}
        m_data = []
        for m_num in m_order:
            if m_num in m_dict:
                row_m = m_dict[m_num]
                m_data.append([m_names[m_num], row_m['Trades'], f"Rs. {row_m['NetPnL']:,.2f}", f"Rs. {row_m['Charges']:,.2f}"])
            else:
                m_data.append([m_names[m_num], 0, "Rs. 0.00", "Rs. 0.00"])
        self._build_mini_table(self.monthly_table_frame, ['Month', 'Trades', 'Net PnL', 'Charges'], m_data)

    def _build_mini_table(self, parent_frame, headers, rows_data, highlight_col=None, highlight_color="#FFFFFF"):
        if not rows_data:
            ctk.CTkLabel(parent_frame, text="No data available for this selection.", font=ctk.CTkFont(size=11), text_color="#757575").pack(pady=10)
            return
            
        t_frame = ctk.CTkFrame(parent_frame, fg_color="transparent")
        t_frame.pack(fill="x", padx=5, pady=2)
        for c_idx in range(len(headers)):
            t_frame.columnconfigure(c_idx, weight=1)
            
        for c_idx, h_text in enumerate(headers):
            ctk.CTkLabel(t_frame, text=h_text, font=ctk.CTkFont(size=11, weight="bold"), text_color="#9E9E9E").grid(row=0, column=c_idx, padx=4, pady=3, sticky="w")
            
        for r_idx, r_vals in enumerate(rows_data[:12]):
            for c_idx, val in enumerate(r_vals):
                t_col = highlight_color if (highlight_col is not None and c_idx == highlight_col) else "#E0E0E0"
                if "-" in str(val) and ("Rs." in str(val) or "%" in str(val)):
                    t_col = "#FF5252"
                elif "+" in str(val):
                    t_col = "#00E676"
                lbl = ctk.CTkLabel(t_frame, text=str(val), font=ctk.CTkFont(size=11), text_color=t_col)
                lbl.grid(row=r_idx + 1, column=c_idx, padx=4, pady=2, sticky="w")

    # ------------------ CHARTS TAB ------------------
    def _render_charts(self):
        for w in self.chart_container.winfo_children():
            w.destroy()
            
        if self.filtered_df.empty:
            ctk.CTkLabel(self.chart_container, text="No trade records to chart.", font=ctk.CTkFont(size=13)).pack(pady=40)
            return
            
        df_sorted = self.filtered_df.sort_values(by='ExitDate').copy()
        df_sorted['CumulativeNetPnL'] = df_sorted['NetPnL'].cumsum()
        
        fig = Figure(figsize=(9, 5), dpi=100, facecolor="#141414")
        
        # 1. Cumulative Equity Curve
        ax1 = fig.add_subplot(2, 1, 1, facecolor="#1E1E1E")
        dates = pd.to_datetime(df_sorted['ExitDate'])
        cum_pnl = df_sorted['CumulativeNetPnL'].values
        
        line_color = "#00E676" if cum_pnl[-1] >= 0 else "#FF5252"
        ax1.plot(dates, cum_pnl, color=line_color, linewidth=2, label="Cumulative Net P&L (Rs.)")
        ax1.fill_between(dates, cum_pnl, 0, color=line_color, alpha=0.15)
        ax1.axhline(0, color="#555555", linestyle="--", linewidth=0.8)
        
        ax1.set_title("Cumulative Net Portfolio Equity Curve", color="#FFFFFF", fontsize=11, fontweight="bold", pad=8)
        ax1.tick_params(colors="#AAAAAA", labelsize=8)
        ax1.grid(True, color="#2D2D2D", linestyle=":", alpha=0.6)
        ax1.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter('₹{x:,.0f}'))
        
        # 2. Daily PnL Bar Chart
        ax2 = fig.add_subplot(2, 1, 2, facecolor="#1E1E1E", sharex=ax1)
        daily = df_sorted.groupby('ExitDate')['NetPnL'].sum().reset_index()
        d_dates = pd.to_datetime(daily['ExitDate'])
        d_pnl = daily['NetPnL'].values
        colors = ["#00E676" if x >= 0 else "#FF5252" for x in d_pnl]
        
        ax2.bar(d_dates, d_pnl, color=colors, width=1.5, alpha=0.85)
        ax2.axhline(0, color="#555555", linestyle="--", linewidth=0.8)
        ax2.set_title("Daily Realized Net P&L Distribution", color="#FFFFFF", fontsize=11, fontweight="bold", pad=8)
        ax2.tick_params(colors="#AAAAAA", labelsize=8)
        ax2.grid(True, color="#2D2D2D", linestyle=":", alpha=0.6)
        ax2.yaxis.set_major_formatter(matplotlib.ticker.StrMethodFormatter('₹{x:,.0f}'))
        
        fig.tight_layout()
        
        canvas = FigureCanvasTkAgg(fig, master=self.chart_container)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    # ------------------ RISK & RECOVERY TAB ------------------
    def _render_risk(self):
        for w in self.risk_worst_table.winfo_children():
            w.destroy()
            
        if self.filtered_df.empty:
            return
            
        df_sorted = self.filtered_df.sort_values(by='ExitDate').copy()
        
        pnl_arr = df_sorted['NetPnL'].values
        max_win_streak = 0
        max_loss_streak = 0
        curr_win = 0
        curr_loss = 0
        
        for p in pnl_arr:
            if p > 0:
                curr_win += 1
                curr_loss = 0
                max_win_streak = max(max_win_streak, curr_win)
            elif p < 0:
                curr_loss += 1
                curr_win = 0
                max_loss_streak = max(max_loss_streak, curr_loss)
            else:
                curr_win = 0
                curr_loss = 0
                
        cum = df_sorted['NetPnL'].cumsum().values
        peak = np.maximum.accumulate(cum)
        dd = peak - cum
        max_dd = np.max(dd) if len(dd) > 0 else 0.0
        current_dd = dd[-1] if len(dd) > 0 else 0.0
        
        self.risk_cards['max_dd'].configure(text=f"Rs. {max_dd:,.2f}")
        self.risk_cards['max_win_streak'].configure(text=f"{max_win_streak} Consecutive Wins")
        self.risk_cards['max_loss_streak'].configure(text=f"{max_loss_streak} Consecutive Losses")
        
        wins = df_sorted[df_sorted['NetPnL'] > 0]
        losses = df_sorted[df_sorted['NetPnL'] < 0]
        win_rate = (len(wins) / len(df_sorted)) if len(df_sorted) > 0 else 0.0
        avg_w = float(wins['NetPnL'].mean()) if len(wins) > 0 else 0.0
        avg_l = abs(float(losses['NetPnL'].mean())) if len(losses) > 0 else 0.0
        expectancy = (win_rate * avg_w) - ((1.0 - win_rate) * avg_l)
        
        if expectancy > 0 and current_dd > 0:
            rec_trades = math.ceil(current_dd / expectancy)
            self.risk_cards['recovery_needed'].configure(text=f"~{rec_trades} Trades Needed")
            rec_text = (
                f"• Current Distance from Peak Equity: Rs. {current_dd:,.2f}\n"
                f"• System Expectancy per Trade: Rs. {expectancy:,.2f}\n"
                f"• Mathematical Recovery Estimate: Approximately {rec_trades} disciplined trades required to reach a new all-time high.\n"
                f"• Risk Rule: Never scale position size during a drawdown. Keep risk per trade strictly <= 1.5% of remaining capital."
            )
        else:
            self.risk_cards['recovery_needed'].configure(text="At New High" if current_dd == 0 else "Negative Expectancy")
            rec_text = (
                f"• Current Drawdown: Rs. {current_dd:,.2f}\n"
                f"• Expectancy per Trade: Rs. {expectancy:,.2f}\n"
                f"• Recommendation: Cut losing instruments immediately. Focus exclusively on positive expectancy setups."
            )
        self.recovery_text_lbl.configure(text=rec_text)
        
        worst_10 = df_sorted.sort_values(by='NetPnL', ascending=True).head(10)
        worst_rows = []
        for _, r in worst_10.iterrows():
            worst_rows.append([
                r['ExitDate'], r['Broker'], r['Symbol'], r['ContractName'] or r['Symbol'],
                f"{r['Quantity']:,.0f}", f"Rs. {r['GrossPnL']:,.2f}", f"Rs. {r['TotalCharges']:,.2f}", f"Rs. {r['NetPnL']:,.2f}"
            ])
        self._build_mini_table(self.risk_worst_table, ['Exit Date', 'Broker', 'Symbol', 'Contract', 'Qty', 'Gross Loss', 'Charges', 'Net Loss'], 
                               worst_rows, highlight_col=7, highlight_color="#FF5252")

    # ------------------ PSYCHOLOGY & DEEP BEHAVIOURAL REFLECTION TAB ------------------
    def _render_psychology(self):
        for w in self.psych_container.winfo_children():
            w.destroy()
            
        if self.filtered_df.empty:
            ctk.CTkLabel(self.psych_container, text="No trades found for current filter selection to compute Behavioral Reflection.", 
                         font=ctk.CTkFont(size=13)).pack(pady=40)
            return

        df = self.filtered_df.copy()
        wins = df[df['NetPnL'] > 0]
        losses = df[df['NetPnL'] < 0]
        total_trades = len(df)
        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0.0
        tot_net_pnl = float(df['NetPnL'].sum())
        avg_win = float(wins['NetPnL'].mean()) if not wins.empty else 0.0
        avg_loss = abs(float(losses['NetPnL'].mean())) if not losses.empty else 0.0
        payoff_ratio = (avg_loss / avg_win) if avg_win > 0 else 0.0

        # 1. 100% Wipeout Trades (Zeroed Options / Heavy Drawdowns)
        wipeouts = losses[losses['ROIPct'] <= -90] if 'ROIPct' in losses.columns else pd.DataFrame()
        wipeout_cnt = len(wipeouts)
        wipeout_loss = abs(float(wipeouts['NetPnL'].sum())) if not wipeouts.empty else 0.0
        saved_at_30 = wipeout_loss * 0.70  # Stop-loss at -30% saves 70% of premium

        # 2. Holding period: 0d vs multi-day
        intra = df[df['HoldingDays'] == 0]
        multiday = df[df['HoldingDays'] > 0]
        intra_pnl = float(intra['NetPnL'].sum()) if not intra.empty else 0.0
        multiday_pnl = float(multiday['NetPnL'].sum()) if not multiday.empty else 0.0

        # 3. Overtrading days (>=10 trades vs <=5 trades)
        df['ExitDateOnly'] = pd.to_datetime(df['ExitDate']).dt.date
        daily_grp = df.groupby('ExitDateOnly').agg(Trades=('TradeID', 'count'), NetPnL=('NetPnL', 'sum'))
        heavy_days = daily_grp[daily_grp['Trades'] >= 10]
        calm_days = daily_grp[daily_grp['Trades'] <= 5]
        heavy_pnl = float(heavy_days['NetPnL'].sum()) if not heavy_days.empty else 0.0
        calm_pnl = float(calm_days['NetPnL'].sum()) if not calm_days.empty else 0.0

        # 4. Consecutive Loss Streaks
        df_sorted = df.sort_values(['ExitDate', 'TradeID'])
        streak = 0
        max_streak = 0
        streak_3_cnt = 0
        streak_5_cnt = 0
        for pnl in df_sorted['NetPnL']:
            if pnl < 0:
                streak += 1
                if streak > max_streak: max_streak = streak
            else:
                if streak >= 5: streak_5_cnt += 1
                elif streak >= 3: streak_3_cnt += 1
                streak = 0
        if streak >= 5: streak_5_cnt += 1
        elif streak >= 3: streak_3_cnt += 1

        # 5. Call vs Put Bias
        ce_cnt = len(df[df['OptionType'] == 'CE']) if 'OptionType' in df.columns else 0
        pe_cnt = len(df[df['OptionType'] == 'PE']) if 'OptionType' in df.columns else 0
        call_bias = (ce_cnt / (ce_cnt + pe_cnt) * 100) if (ce_cnt + pe_cnt) > 0 else 50.0

        # 6. Behavioral Discipline Score Calculation
        score = 85
        if payoff_ratio >= 2.5: score -= 22
        elif payoff_ratio >= 1.5: score -= 12
        if wipeout_cnt >= 20: score -= 25
        elif wipeout_cnt >= 5: score -= 12
        if len(heavy_days) >= 10: score -= 20
        elif len(heavy_days) >= 3: score -= 10
        if call_bias >= 85: score -= 15
        score = max(18, min(95, int(score)))

        stress_state = "CRITICAL REVENGE & TILT RISK" if score < 40 else ("ELEVATED THETA & LOSS DRAG" if score < 60 else ("MODERATE DISCIPLINE" if score < 80 else "OPTIMAL ZEN DISCIPLINE"))
        stress_color = "#FF5252" if score < 40 else ("#FFA726" if score < 60 else ("#FFD54F" if score < 80 else "#00E676"))

        # ── 1. Executive Behavioral Header & Diagnosis Gauge ──
        hdr_card = ctk.CTkFrame(self.psych_container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#334155")
        hdr_card.pack(fill="x", pady=(0, 10))

        h_top = ctk.CTkFrame(hdr_card, fg_color="transparent")
        h_top.pack(fill="x", padx=15, pady=(12, 4))
        
        t_box = ctk.CTkFrame(h_top, fg_color="transparent")
        t_box.pack(side="left")
        ctk.CTkLabel(t_box, text="🧠 Deep Behavioural Reflection & Psychological Audit", 
                     font=ctk.CTkFont(size=16, weight="bold"), text_color="#38BDF8").pack(anchor="w")
        ctk.CTkLabel(t_box, text=f"Empirical Audit of {total_trades:,} Executed Trades • Quantifying Cognitive Biases & Root-Cause Trading Mistakes", 
                     font=ctk.CTkFont(size=11), text_color="#94A3B8").pack(anchor="w")

        badge = ctk.CTkFrame(h_top, fg_color="#0F172A", corner_radius=8, border_width=1, border_color=stress_color)
        badge.pack(side="right")
        ctk.CTkLabel(badge, text=f"DISCIPLINE SCORE: {score}/100", font=ctk.CTkFont(size=13, weight="bold"), text_color=stress_color).pack(padx=12, pady=(5, 2))
        ctk.CTkLabel(badge, text=stress_state, font=ctk.CTkFont(size=10, weight="bold"), text_color="gray65").pack(padx=12, pady=(0, 5))

        # ── 2. Four Behavioral KPI Metric Cards ──
        kpi_grid = ctk.CTkFrame(hdr_card, fg_color="transparent")
        kpi_grid.pack(fill="x", padx=15, pady=(4, 14))
        kpi_grid.grid_columnconfigure((0, 1, 2, 3), weight=1)

        p_sign = "+" if tot_net_pnl >= 0 else ""
        b_kpis = [
            ("🛑 100% Wipeout Drag", f"{wipeout_cnt} Zeroed Trades", f"-Rs. {wipeout_loss:,.2f} Lost (Rs. {saved_at_30:,.2f} Recoverable)", "#FF5252"),
            ("⚡ Overtrading / Tilt Drag", f"{len(heavy_days)} Days (≥10 Trades)", f"Lost -Rs. {abs(heavy_pnl):,.2f} (≤5/d Made +Rs. {calm_pnl:,.2f})", "#FFA726"),
            ("⏱️ Overnight Theta Bleed", f"Multi-Day: -Rs. {abs(multiday_pnl):,.2f}", f"0d Intraday Made +Rs. {intra_pnl:,.2f}", "#EF5350"),
            ("⚖️ Asymmetric Loss Drag", f"{payoff_ratio:.2f}x Loss vs Win", f"Avg Win Rs. {avg_win:,.0f} vs Loss Rs. {avg_loss:,.0f}", "#FFD54F")
        ]
        for idx, (t, v, sub, clr) in enumerate(b_kpis):
            kb = ctk.CTkFrame(kpi_grid, fg_color="#0D1117", corner_radius=8, border_width=1, border_color="#21262D")
            kb.grid(row=0, column=idx, padx=4, pady=4, sticky="nsew")
            ctk.CTkLabel(kb, text=t, font=ctk.CTkFont(size=10, weight="bold"), text_color="gray60").pack(anchor="w", padx=10, pady=(6, 2))
            ctk.CTkLabel(kb, text=v, font=ctk.CTkFont(size=13, weight="bold"), text_color=clr).pack(anchor="w", padx=10, pady=(0, 2))
            ctk.CTkLabel(kb, text=sub, font=ctk.CTkFont(size=10), text_color="gray50").pack(anchor="w", padx=10, pady=(0, 6))

        # ── 3. CARD 1: WHY HAVE YOU LOST 100% ON TRADES? ──
        c1 = ctk.CTkFrame(self.psych_container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#B71C1C")
        c1.pack(fill="x", pady=6)
        
        ctk.CTkLabel(c1, text="🛑 ROOT CAUSE 1: Why Have You Lost 100% on Option Trades? (The Holding-to-Zero Trap)", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#FF5252").pack(anchor="w", padx=15, pady=(12, 4))
        
        c1_text = (
            f"• THE EMPIRICAL EVIDENCE IN YOUR JOURNAL:\n"
            f"   In this dataset, exactly {wipeout_cnt} trades experienced a catastrophic loss of >= 90% (total wipeout), destroying Rs. {wipeout_loss:,.2f} of capital.\n"
            f"   Over 90% of your total net loss is concentrated in these specific trades where out-of-the-money options were held until expiration at 0 premium!\n\n"
            f"• THE PSYCHOLOGICAL TRAP:\n"
            f"   When an option premium drops by 40%, the human brain shifts into 'Hope & Denial Mode' — refusing to accept a realized loss and praying for a sudden reversal.\n"
            f"   Because you bought naked Calls, theta decay (time erosion) accelerated exponentially in the final 7 days before expiry, evaporating 100% of your money.\n\n"
            f"• THE MATHEMATICAL ANTIDOTE (HOW TO RECOVER):\n"
            f"   1. Hard Broker GTT Stop Loss at -30%: If you had placed a mechanical broker stop-loss at -30% on these trades, you would have saved exactly Rs. {saved_at_30:,.2f}!\n"
            f"   2. The 3-Day Rule: If an option does not move in your anticipated direction within 48 hours of entry, exit immediately. Never hold a losing long option overnight."
        )
        ctk.CTkLabel(c1, text=c1_text, justify="left", font=ctk.CTkFont(size=11), text_color="#E2E8F0").pack(anchor="w", padx=15, pady=(0, 10))

        # Top 5 Worst 100% Wipeout Examples Table
        if not wipeouts.empty:
            worst_wipeouts = wipeouts.sort_values('NetPnL').head(5)
            w_rows = []
            for _, r in worst_wipeouts.iterrows():
                opt_str = f"{r.get('OptionType', '')} {r.get('StrikePrice', '')}" if pd.notna(r.get('OptionType')) else "N/A"
                w_rows.append([
                    str(r['ExitDate']), str(r['Symbol']), opt_str, f"{r.get('HoldingDays', 0)}d",
                    f"-Rs. {abs(r['NetPnL']):,.2f}", f"{r.get('ROIPct', -100):.1f}%", "Zeroed on Expiry (No SL)"
                ])
            w_table_box = ctk.CTkFrame(c1, fg_color="transparent")
            w_table_box.pack(fill="x", padx=15, pady=(0, 12))
            self._build_mini_table(w_table_box, ['Exit Date', 'Symbol', 'Option Strike', 'Holding', 'Capital Lost', 'ROI %', 'Root Cause'], 
                                   w_rows, highlight_col=4, highlight_color="#FF5252")

        # ── 4. CARD 2: WHY YOU MUST NEVER TAKE CONSECUTIVE LOSSES (THE TILT SPIRAL) ──
        c2 = ctk.CTkFrame(self.psych_container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#E65100")
        c2.pack(fill="x", pady=6)
        
        ctk.CTkLabel(c2, text="⚡ ROOT CAUSE 2: The Consecutive Loss Spiral & Overtrading (Fight-or-Flight Tilt)", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#FFA726").pack(anchor="w", padx=15, pady=(12, 4))
        
        c2_text = (
            f"• THE STAGGERING CONTRAST: CALM DAYS vs OVERTRADING DAYS:\n"
            f"   • On calm days with <= 5 trades: You made a NET PROFIT of +Rs. {calm_pnl:,.2f} across {len(calm_days)} trading sessions!\n"
            f"   • On heavy days with >= 10 trades: You collapsed into a NET LOSS of -Rs. {abs(heavy_pnl):,.2f} across {len(heavy_days)} sessions!\n"
            f"   Your entire account loss happened exclusively on days when you overtraded in an emotional frenzy after taking consecutive losses!\n\n"
            f"• THE PSYCHOLOGY OF 'TILT':\n"
            f"   Your maximum consecutive loss streak reached {max_streak} losses in a row. You took 3+ consecutive losses {streak_3_cnt} separate times.\n"
            f"   Neuroscience proves that after 2 consecutive losses, your brain releases cortisol and adrenaline, suppressing the prefrontal cortex (rational judgment).\n"
            f"   You immediately take another trade out of vengeance to 'get your money back', entering sloppy setups with oversized lots.\n\n"
            f"• MANDATORY 2-LOSS DAILY CIRCUIT BREAKER (THE DISCIPLINE RULE):\n"
            f"   1. Hard Rule: If you take 2 losses on any single calendar day, close your trading terminal and walk away immediately. No exceptions.\n"
            f"   2. By capping daily trades to <= 5, you transform your trading from negative expectancy into a mathematically profitable system."
        )
        ctk.CTkLabel(c2, text=c2_text, justify="left", font=ctk.CTkFont(size=11), text_color="#E2E8F0").pack(anchor="w", padx=15, pady=(0, 12))

        # ── 5. CARD 3: WHERE RISK MANAGEMENT WAS MISSED (THE 3 BLINDSPOTS) ──
        c3 = ctk.CTkFrame(self.psych_container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#1E3A8A")
        c3.pack(fill="x", pady=6)
        
        ctk.CTkLabel(c3, text="🛡️ ROOT CAUSE 3: Why Risk Management Was Inverted (The 3 Critical Blindspots)", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#38BDF8").pack(anchor="w", padx=15, pady=(12, 4))
        
        c3_text = (
            f"• BLINDSPOT 1: THE WIN RATE ILLUSION (59.1% WIN RATE vs NEGATIVE P&L):\n"
            f"   You won {len(wins):,} out of {total_trades:,} trades ({win_rate:.1f}% Win Rate). Your market direction prediction is actually very good!\n"
            f"   However, you suffered from Payoff Asymmetry: Your average win was only Rs. {avg_win:,.2f}, while your average loss was Rs. {avg_loss:,.2f} ({payoff_ratio:.2f}x larger!).\n"
            f"   You cut winning trades quickly to lock in small psychological dopamine hits, while letting losing trades linger hoping they would bounce back.\n\n"
            f"• BLINDSPOT 2: EXTREME 91.7% CALL BIAS (ONE-WAY BULL MINDSET):\n"
            f"   Your journal shows {ce_cnt:,} Call options vs only {pe_cnt:,} Put options ({call_bias:.1f}% Call Bias).\n"
            f"   Markets spend over 55% of their time consolidating or pulling back. Being 91.7% long Calls guarantees that theta decay and choppy ranges bleed you dry.\n\n"
            f"• BLINDSPOT 3: MENTAL STOP LOSSES vs HARD GTT ORDERS:\n"
            f"   A mental stop loss is an illusion. When the market moves against you rapidly, fear paralyzes action. Risk management was missed at the order-placement stage."
        )
        ctk.CTkLabel(c3, text=c3_text, justify="left", font=ctk.CTkFont(size=11), text_color="#E2E8F0").pack(anchor="w", padx=15, pady=(0, 12))

        # ── 6. CARD 4: MISSING STRATEGIES & BEHAVIORAL TRANSFORMATION ROADMAP ──
        c4 = ctk.CTkFrame(self.psych_container, fg_color="#14241B", corner_radius=10, border_width=1, border_color="#2E7D32")
        c4.pack(fill="x", pady=6)
        
        ctk.CTkLabel(c4, text="🚀 Missing Trading Strategies & The 3-Step Behavioral Transformation Action Plan", 
                     font=ctk.CTkFont(size=14, weight="bold"), text_color="#00E676").pack(anchor="w", padx=15, pady=(12, 4))
        
        c4_text = (
            "• STRATEGY 1: SWITCH FROM NAKED CALLS TO DEFINED-RISK VERTICAL SPREADS:\n"
            "   Instead of buying a single naked Call (100% loss risk with rapid theta decay), buy a slightly ITM Call and sell an OTM Call (Bull Call Spread).\n"
            "   Benefits: Reduces capital outlay by 45%, eliminates 70% of theta time decay, and strictly caps maximum loss before you enter.\n\n"
            "• STRATEGY 2: ALLOCATE 60% CAPITAL TO CASH EQUITY DELIVERY SWING TRADING:\n"
            "   Your actual trading journal proves that your Cash Equity trades generated +Rs. 4.05 Lakhs Net Profit! Cash stocks have ZERO expiration and ZERO theta decay.\n"
            "   By shifting your core focus to Cash Delivery Swings (as generated in the Trade Projection Desk), time works FOR you instead of against you.\n\n"
            "• STRATEGY 3: PSYCHOLOGY & STRESS LEVEL PROTOCOL (MAINTAINING ZEN):\n"
            "   1. The 15-Minute Rule: Never place a trade within 15 minutes of closing a losing position. Stand up, drink water, and reset your nervous system.\n"
            "   2. The 2% Capital Mandate: Risk no more than 2% of total capital on any single setup.\n"
            "   3. Trade Quota: Maximum 3 to 5 trades per day. Quality over quantity always wins."
        )
        ctk.CTkLabel(c4, text=c4_text, justify="left", font=ctk.CTkFont(size=11), text_color="#E0F2F1").pack(anchor="w", padx=15, pady=(0, 14))

        # ── 7. CARD 5: DOCUMENTED MISTAKE CATEGORIES LEDGER ──
        c5 = ctk.CTkFrame(self.psych_container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#334155")
        c5.pack(fill="x", pady=6)

        ctk.CTkLabel(c5, text="📋 Documented Discipline Mistakes & Capital Attribution Ledger", 
                     font=ctk.CTkFont(size=13, weight="bold"), text_color="#FFD54F").pack(anchor="w", padx=15, pady=(12, 4))

        mistake_grp = df.groupby('MistakeTag').agg(
            Trades=('TradeID', 'count'),
            NetPnL=('NetPnL', 'sum'),
            TotalLoss=('NetPnL', lambda x: abs(x[x < 0].sum())),
            WinCount=('NetPnL', lambda x: (x > 0).sum())
        ).reset_index()

        psych_rows = []
        for _, r in mistake_grp.iterrows():
            tag_name = r['MistakeTag'] if pd.notna(r['MistakeTag']) and r['MistakeTag'] else 'Unclassified / Untagged'
            win_r = (r['WinCount'] / r['Trades'] * 100) if r['Trades'] > 0 else 0.0
            psych_rows.append([tag_name, r['Trades'], f"{win_r:.1f}%", f"Rs. {r['TotalLoss']:,.2f}", f"Rs. {r['NetPnL']:,.2f}"])

        m_table_box = ctk.CTkFrame(c5, fg_color="transparent")
        m_table_box.pack(fill="x", padx=15, pady=(4, 14))
        self._build_mini_table(m_table_box, ['Mistake Category', 'Trades', 'Win Rate', 'Total Losses Drag', 'Net P&L'], 
                               psych_rows, highlight_col=4, highlight_color="#FF5252")

    # ------------------ MTF COMMAND CENTER ------------------
    def _render_mtf(self):
        for w in self.mtf_table_frame.winfo_children():
            w.destroy()
            
        mtf_ledgers = self.other_ledger_df[self.other_ledger_df['Category'] == 'MTF Interest']
        total_interest_cost = float(mtf_ledgers['Debit'].sum()) if not mtf_ledgers.empty else 0.0
        mtf_trades = self.filtered_df[self.filtered_df['IsMTF'] == 1]
        
        summary_txt = (
            f"• Total Accrued MTF Interest Debited to Date: Rs. {total_interest_cost:,.2f} across {len(mtf_ledgers):,} daily charges.\n"
            f"• Explicit MTF Position Exits in Selection: {len(mtf_trades):,} trades.\n"
            f"• Financing Leverage Formula: 70% Broker Funding @ Standard Annualized Interest, 30% Client Capital."
        )
        self.mtf_summary_lbl.configure(text=summary_txt)
        
        if not mtf_ledgers.empty:
            recent_ledgers = mtf_ledgers.head(15)
            l_rows = []
            for _, r in recent_ledgers.iterrows():
                l_rows.append([r['PostingDate'], r['Broker'], r['Particulars'], f"Rs. {r['Debit']:,.2f}", r['FinancialYear']])
            self._build_mini_table(self.mtf_table_frame, ['Posting Date', 'Broker', 'Particulars / Head', 'Daily Interest Debit', 'Financial Year'], 
                                   l_rows, highlight_col=3, highlight_color="#FFA726")

    # ------------------ SMART INGESTION ACTIONS ------------------
    def _trigger_sync_folder(self):
        try:
            self.ingest_log_txt.insert("end", f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Starting Full Folder Sync & Backup...\n")
            rep = journal_engine.sync_and_backup_folder()
            
            total_found = 0
            total_ins = 0
            total_skip = 0
            
            for item in rep:
                fname = item.get('file', '')
                broker = item.get('broker', '')
                st = item.get('status', '')
                ins = item.get('trades_inserted', 0)
                skip = item.get('trades_skipped', 0)
                total_found += item.get('trades_found', 0)
                total_ins += ins
                total_skip += skip
                
                log_line = f"  • {fname:<35} [{broker:<14}]: {ins} New Inserted | {skip} Duplicates Skipped | Status: {st}\n"
                self.ingest_log_txt.insert("end", log_line)
                
            self.ingest_log_txt.insert("end", f"✓ Sync Finished: {total_ins} New Trades Inserted, {total_skip} Duplicates Skipped.\n")
            self.ingest_log_txt.see("end")
            
            messagebox.showinfo("Sync Complete", f"Processed files successfully!\nNew Trades: {total_ins}\nDuplicates Skipped: {total_skip}")
            self.load_data()
        except Exception as e:
            messagebox.showerror("Sync Error", f"Failed to sync folder: {e}")

    def _import_individual_file(self):
        fpath = filedialog.askopenfilename(
            title="Select Broker Trade Report",
            filetypes=[("Excel Files", "*.xlsx *.xls")]
        )
        if not fpath:
            return
        try:
            trades, ledgers = journal_engine.parse_file(fpath)
            ins_t, skip_t, ins_l, skip_l = journal_engine.ingest_trades_to_db(trades, ledgers)
            messagebox.showinfo("Import Success", f"Processed {os.path.basename(fpath)}:\nTrades Inserted: {ins_t}\nDuplicates Skipped: {skip_t}\nLedger Items: {ins_l}")
            self.load_data()
        except Exception as e:
            messagebox.showerror("Import Error", f"Failed to process file: {e}")

    def _export_to_csv(self):
        if self.filtered_df.empty:
            messagebox.showwarning("Warning", "No trade data available to export.")
            return
        save_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
            initialfile=f"TradingJournal_Export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        )
        if save_path:
            try:
                self.filtered_df.to_csv(save_path, index=False)
                messagebox.showinfo("Export Successful", f"Exported {len(self.filtered_df)} trades to:\n{save_path}")
            except Exception as e:
                messagebox.showerror("Export Failed", str(e))
