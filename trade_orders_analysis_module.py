"""
Trade Orders Analysis Module
============================
Comprehensive Multi-Broker Trade Log & Order Analysis, FIFO Matched Trades Engine,
Open & Closed Trade Status Analytics, Execution Analytics, and Ingestion Hub.
"""

import os
import re
import math
import hashlib
import threading
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

import trade_orders_engine

SERVER = r'.\SQLEXPRESS'
DATABASE = 'Navin_Personal'
CONN_STR = f'DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={SERVER};DATABASE={DATABASE};Trusted_Connection=yes;'

def get_connection():
    return pyodbc.connect(CONN_STR)

def resolve_sheet_row(event, sheet):
    """Robustly resolves the selected row index from a tksheet event or current selection."""
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

# =============================================================================
# MATCHED TRADE AUDIT & DRILL-DOWN MODAL
# =============================================================================
class MatchedTradeDetailModal(ctk.CTkToplevel):
    def __init__(self, master, trade_data):
        super().__init__(master)
        self.trade_data = trade_data
        trade_id = trade_data.get('TradeID', 'N/A')
        symbol = trade_data.get('Symbol', 'Unknown')
        status = trade_data.get('Status', 'OPEN')
        self.title(f"Trade Audit & Matched Legs — #{trade_id} ({symbol} • {status})")
        self.geometry("940x780")
        self.minsize(840, 640)
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

        # 1. Header Badge
        hdr = ctk.CTkFrame(container, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 15))

        status = str(self.trade_data.get('Status', 'OPEN')).upper()
        stat_col = "#00E676" if status == "OPEN" else "#29B6F6"

        stance = str(self.trade_data.get('Stance', 'LONG')).upper()
        stance_col = "#00E676" if stance == "LONG" else "#FF5252"

        ctk.CTkLabel(hdr, text=f"{self.trade_data.get('Symbol', '')}", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkLabel(hdr, text=f" {status} ", fg_color=stat_col, text_color="#000000", corner_radius=6, font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=10)
        ctk.CTkLabel(hdr, text=f" {stance} ", fg_color=stance_col, text_color="#000000", corner_radius=6, font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=5)
        ctk.CTkLabel(hdr, text=f" {self.trade_data.get('Broker', '')} • {self.trade_data.get('Segment', '')} ", fg_color="#333333", corner_radius=6, font=ctk.CTkFont(size=12)).pack(side="left", padx=5)

        pnl = self.trade_data.get('GrossPnL')
        if status == 'CLOSED' and pnl is not None and pd.notna(pnl):
            pnl_val = float(pnl)
            pnl_col = "#00E676" if pnl_val >= 0 else "#FF5252"
            pnl_sign = "+" if pnl_val >= 0 else ""
            pnl_badge = ctk.CTkLabel(hdr, text=f"Gross Realized P&L: {pnl_sign}Rs. {pnl_val:,.2f}",
                                     fg_color=pnl_col, text_color="#000000" if pnl_val >= 0 else "#FFFFFF",
                                     corner_radius=8, font=ctk.CTkFont(size=14, weight="bold"), padx=12, pady=5)
            pnl_badge.pack(side="right")
        else:
            val = float(self.trade_data.get('EntryValue', 0.0) or 0.0)
            val_badge = ctk.CTkLabel(hdr, text=f"Committed Capital: Rs. {val:,.2f}",
                                     fg_color="#1E88E5", text_color="#FFFFFF",
                                     corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"), padx=12, pady=5)
            val_badge.pack(side="right")

        # 2. Key Execution Details Grid
        grid_frame = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        grid_frame.pack(fill="x", pady=(0, 15), padx=5)
        grid_frame.columnconfigure((0, 1, 2, 3), weight=1)

        qty = float(self.trade_data.get('Quantity', 0.0) or 0.0)
        entry_p = float(self.trade_data.get('EntryPrice', 0.0) or 0.0)
        exit_p = self.trade_data.get('ExitPrice')
        exit_p_str = f"Rs. {float(exit_p):,.2f}" if (exit_p is not None and pd.notna(exit_p)) else "— (Active)"
        exit_d = self.trade_data.get('ExitDate')
        exit_d_str = str(exit_d) if (exit_d is not None and pd.notna(exit_d)) else "— (Active Position)"
        roi = self.trade_data.get('ROIPct')
        roi_str = f"{float(roi):+.2f}%" if (roi is not None and pd.notna(roi)) else "—"

        items = [
            ("Trade ID", str(self.trade_data.get('TradeID', ''))),
            ("Contract / Scrip", str(self.trade_data.get('ContractName', ''))),
            ("Trade Status", status),
            ("Financial Year", str(self.trade_data.get('FinancialYear', ''))),
            ("Entry Date", str(self.trade_data.get('EntryDate', ''))),
            ("Entry Price", f"Rs. {entry_p:,.2f}"),
            ("Exit Date", exit_d_str),
            ("Exit Price", exit_p_str),
            ("Quantity", f"{qty:,.2f}"),
            ("Buy Value", f"Rs. {float(self.trade_data.get('BuyValue', 0.0) or 0.0):,.2f}"),
            ("Sell Value", f"Rs. {float(self.trade_data.get('SellValue', 0.0) or 0.0):,.2f}" if status == 'CLOSED' else "—"),
            ("ROI %", roi_str),
            ("Holding Duration", f"{self.trade_data.get('HoldingDays', 0)} Days"),
            ("Option / Strike", f"{self.trade_data.get('OptionType', 'N/A')} {self.trade_data.get('StrikePrice') or ''}".strip()),
            ("Expiry Date", str(self.trade_data.get('ExpiryDate') or 'N/A')),
            ("Outcome", str(self.trade_data.get('Outcome', 'OPEN')))
        ]

        for i, (label, val) in enumerate(items):
            r = i // 4
            c = i % 4
            cell = ctk.CTkFrame(grid_frame, fg_color="transparent")
            cell.grid(row=r, column=c, padx=12, pady=7, sticky="w")
            ctk.CTkLabel(cell, text=label, font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888").pack(anchor="w")
            ctk.CTkLabel(cell, text=str(val), font=ctk.CTkFont(size=12, weight="normal"), text_color="#FFFFFF").pack(anchor="w")

        # 3. Itemized Order Legs Match Audit
        legs_box = ctk.CTkFrame(container, fg_color="#1E1E1E", corner_radius=10, border_width=1, border_color="#2D2D2D")
        legs_box.pack(fill="x", pady=(0, 15), padx=5)

        ctk.CTkLabel(legs_box, text="🧾 Matched Order Legs & Exchange References", font=ctk.CTkFont(size=13, weight="bold"), text_color="#64B5F6").pack(anchor="w", padx=15, pady=(10, 5))

        entry_oid = self.trade_data.get('EntryOrderID', 'N/A')
        exit_oid = self.trade_data.get('ExitOrderID', 'N/A')

        legs_grid = ctk.CTkFrame(legs_box, fg_color="transparent")
        legs_grid.pack(fill="x", padx=15, pady=(0, 10))
        legs_grid.columnconfigure((0, 1), weight=1)

        # Entry Leg Box
        leg1 = ctk.CTkFrame(legs_grid, fg_color="#262626", corner_radius=8)
        leg1.grid(row=0, column=0, padx=5, sticky="nsew")
        ctk.CTkLabel(leg1, text=f"Entry Order Leg #{entry_oid}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00E676").pack(anchor="w", padx=10, pady=(6, 2))
        ctk.CTkLabel(leg1, text=f"Action: {'BUY' if stance=='LONG' else 'SELL'} | Date: {self.trade_data.get('EntryDate')} | Exec Price: Rs. {entry_p:,.2f}", font=ctk.CTkFont(size=11), text_color="#FFFFFF").pack(anchor="w", padx=10, pady=(0, 6))

        # Exit Leg Box
        leg2 = ctk.CTkFrame(legs_grid, fg_color="#262626", corner_radius=8)
        leg2.grid(row=0, column=1, padx=5, sticky="nsew")
        if status == 'CLOSED':
            ctk.CTkLabel(leg2, text=f"Exit Order Leg #{exit_oid}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#29B6F6").pack(anchor="w", padx=10, pady=(6, 2))
            ctk.CTkLabel(leg2, text=f"Action: {'SELL' if stance=='LONG' else 'BUY'} | Date: {exit_d_str} | Exec Price: {exit_p_str}", font=ctk.CTkFont(size=11), text_color="#FFFFFF").pack(anchor="w", padx=10, pady=(0, 6))
        else:
            ctk.CTkLabel(leg2, text="Exit Order Leg — Unclosed", font=ctk.CTkFont(size=11, weight="bold"), text_color="#FFA726").pack(anchor="w", padx=10, pady=(6, 2))
            ctk.CTkLabel(leg2, text="Position remains open in portfolio. Awaiting exit order fill.", font=ctk.CTkFont(size=11), text_color="#9E9E9E").pack(anchor="w", padx=10, pady=(0, 6))

        # 4. Dispute Audit or Institutional Insights
        is_dispute = self.trade_data.get('IsDispute', False) or self.trade_data.get('HoldingStatus') == 'DISPUTE_DATA'
        if is_dispute:
            disp_card = ctk.CTkFrame(container, fg_color="#2A1414", corner_radius=10, border_width=1, border_color="#FF5252")
            disp_card.pack(fill="x", pady=(0, 15), padx=5)
            ctk.CTkLabel(disp_card, text="⚠️ DATA RECONCILIATION & DISPUTE AUDIT", font=ctk.CTkFont(size=13, weight="bold"), text_color="#FF5252").pack(anchor="w", padx=15, pady=(10, 4))
            
            d_reason = self.trade_data.get('DisputeReason') or 'Unequal BUY and SELL execution quantities detected in imported trade logs.'
            d_recon = self.trade_data.get('ReconciliationAdvice') or 'Please provide complete historical trade logs from account inception to balance this position.'
            
            ctk.CTkLabel(disp_card, text=f"• Dispute Diagnosis: {d_reason}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFA726", wraplength=780, justify="left").pack(anchor="w", padx=15, pady=(2, 4))
            ctk.CTkLabel(disp_card, text=f"• Action Required: {d_recon}", font=ctk.CTkFont(size=12), text_color="#FFFFFF", wraplength=780, justify="left").pack(anchor="w", padx=15, pady=(0, 10))
        else:
            adv_card = ctk.CTkFrame(container, fg_color="#172338", corner_radius=10, border_width=1, border_color="#1E88E5")
            adv_card.pack(fill="x", pady=(0, 15), padx=5)
            ctk.CTkLabel(adv_card, text="🧠 Institutional Insights & Strategic Advice", font=ctk.CTkFont(size=13, weight="bold"), text_color="#64B5F6").pack(anchor="w", padx=15, pady=(10, 5))
            insight_txt = self.trade_data.get('Insights', 'Review risk parameters and price trajectory.')
            ctk.CTkLabel(adv_card, text=insight_txt, font=ctk.CTkFont(size=12), text_color="#E3F2FD", wraplength=780, justify="left").pack(anchor="w", padx=15, pady=(0, 10))

        # Close
        ctk.CTkButton(container, text="Dismiss Audit Window", width=160, height=32, fg_color="#333333", hover_color="#444444",
                       command=self.destroy).pack(pady=10)

# =============================================================================
# CURRENT HOLDINGS & DATA DISPUTE AUDIT MODAL
# =============================================================================
class HoldingDisputeDetailModal(ctk.CTkToplevel):
    def __init__(self, master, holding_data):
        super().__init__(master)
        self.holding_data = holding_data
        symbol = holding_data.get('Symbol', 'Unknown')
        status = holding_data.get('HoldingStatus', 'VERIFIED_HOLDING')
        status_disp = holding_data.get('HoldingStatusDisplay', 'Holding')
        self.title(f"Holding & Reconciliation Audit — {symbol} ({status_disp})")
        self.geometry("980x800")
        self.minsize(860, 660)
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

        # 1. Header Badge
        hdr = ctk.CTkFrame(container, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 15))

        status = str(self.holding_data.get('HoldingStatus', 'VERIFIED_HOLDING')).upper()
        is_dispute = bool(self.holding_data.get('IsDispute', False) or status == 'DISPUTE_DATA')

        if is_dispute:
            stat_col = "#FF5252"
            stat_txt = "⚠️ DISPUTE DATA (Incomplete Log)"
        elif "ACTIVE" in status:
            stat_col = "#00E5FF"
            stat_txt = "🟢 ACTIVE DERIVATIVE (Carry Forward)"
        else:
            stat_col = "#00E676"
            stat_txt = "✅ VERIFIED DEMAT HOLDING (Carry Forward)"

        ctk.CTkLabel(hdr, text=f"{self.holding_data.get('Symbol', '')}", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkLabel(hdr, text=f" {stat_txt} ", fg_color=stat_col, text_color="#000000", corner_radius=6, font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=10)
        ctk.CTkLabel(hdr, text=f" {self.holding_data.get('Broker', '')} • {self.holding_data.get('Segment', '')} ", fg_color="#333333", corner_radius=6, font=ctk.CTkFont(size=12)).pack(side="left", padx=5)

        c_val = float(self.holding_data.get('CommittedValue', 0.0) or 0.0)
        m_val = float(self.holding_data.get('CurrentMarketValue', c_val) or c_val)
        val_badge = ctk.CTkLabel(hdr, text=f"Current Market Value: Rs. {m_val:,.2f}",
                                 fg_color="#1E88E5", text_color="#FFFFFF",
                                 corner_radius=8, font=ctk.CTkFont(size=13, weight="bold"), padx=12, pady=5)
        val_badge.pack(side="right")

        # 2. Key Holding & Valuation Metrics Grid
        grid_frame = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        grid_frame.pack(fill="x", pady=(0, 15), padx=5)
        grid_frame.columnconfigure((0, 1, 2, 3), weight=1)

        net_q = float(self.holding_data.get('NetQty', 0.0) or 0.0)
        buy_q = float(self.holding_data.get('BuyQty', 0.0) or 0.0)
        sell_q = float(self.holding_data.get('SellQty', 0.0) or 0.0)
        entry_p = float(self.holding_data.get('AvgEntryPrice', 0.0) or 0.0)
        ltp = float(self.holding_data.get('LTP', entry_p) or entry_p)
        pnl = float(self.holding_data.get('UnrealizedPnL', 0.0) or 0.0)
        roi = float(self.holding_data.get('UnrealizedROIPct', 0.0) or 0.0)
        dte = self.holding_data.get('DTE')
        dte_str = f"{dte} Days" if dte is not None else "N/A"

        items = [
            ("Broker", str(self.holding_data.get('Broker', ''))),
            ("Segment / Product", f"{self.holding_data.get('Segment', '')} • {self.holding_data.get('SubSegment', '')}"),
            ("Contract / Scrip", str(self.holding_data.get('ContractName', ''))),
            ("Stance", str(self.holding_data.get('Stance', 'LONG'))),
            ("Held / Net Quantity", f"{net_q:,.2f}"),
            ("Order Balance", f"Bought: {buy_q:,.0f} | Sold: {sell_q:,.0f}"),
            ("Avg Buy / Entry Price", f"Rs. {entry_p:,.2f}"),
            ("Committed Capital", f"Rs. {c_val:,.2f}"),
            ("Current Price (LTP)", f"Rs. {ltp:,.2f}"),
            ("Current Market Value", f"Rs. {m_val:,.2f}"),
            ("Unrealized P&L", f"{'+' if pnl>=0 else ''}Rs. {pnl:,.2f}"),
            ("Unrealized ROI %", f"{roi:+.2f}%"),
            ("Holding Duration", f"{self.holding_data.get('DaysOpen', 0)} Days Held"),
            ("Expiry Date", str(self.holding_data.get('ExpiryDate') or 'N/A')),
            ("Days to Expiry (DTE)", dte_str),
            ("Expiry Risk", str(self.holding_data.get('DTERisk', 'N/A')))
        ]

        for i, (label, val) in enumerate(items):
            r = i // 4
            c = i % 4
            cell = ctk.CTkFrame(grid_frame, fg_color="transparent")
            cell.grid(row=r, column=c, padx=12, pady=7, sticky="w")
            ctk.CTkLabel(cell, text=label, font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888").pack(anchor="w")
            val_col = "#00E676" if "P&L" in label and pnl >= 0 else ("#FF5252" if "P&L" in label and pnl < 0 else "#FFFFFF")
            ctk.CTkLabel(cell, text=str(val), font=ctk.CTkFont(size=12, weight="normal"), text_color=val_col).pack(anchor="w")

        # 3. Holding Certificate OR Dispute Diagnosis Card
        if is_dispute:
            disp_card = ctk.CTkFrame(container, fg_color="#2A1212", corner_radius=10, border_width=1, border_color="#FF5252")
            disp_card.pack(fill="x", pady=(0, 15), padx=5)

            ctk.CTkLabel(disp_card, text="⚠️ DATA DISPUTE & RECONCILIATION DIAGNOSIS", font=ctk.CTkFont(size=14, weight="bold"), text_color="#FF5252").pack(anchor="w", padx=15, pady=(12, 6))

            d_reason = self.holding_data.get('DisputeReason') or 'Unequal BUY and SELL execution quantities detected in imported trade logs.'
            d_recon = self.holding_data.get('ReconciliationAdvice') or 'Please provide complete historical trade logs from account inception.'

            ctk.CTkLabel(disp_card, text=f"• Discrepancy Reason:\n  {d_reason}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFA726", wraplength=880, justify="left").pack(anchor="w", padx=15, pady=(2, 6))
            ctk.CTkLabel(disp_card, text=f"• Required Dataset / Resolution:\n  {d_recon}", font=ctk.CTkFont(size=12), text_color="#FFFFFF", wraplength=880, justify="left").pack(anchor="w", padx=15, pady=(2, 10))

            instr_box = ctk.CTkFrame(disp_card, fg_color="#181818", corner_radius=8)
            instr_box.pack(fill="x", padx=15, pady=(0, 12))
            instructions = (
                f"How to reconcile this trade:\n"
                f"1. Download historical order log / tradebook from your broker ({self.holding_data.get('Broker', 'Broker')}) from account opening date or expiry square-off report.\n"
                f"2. Save the CSV or Excel file into the Sync Folder: {trade_orders_engine.DEFAULT_ORDER_LOG_DIR}\n"
                f"3. Click 'Sync Folder' on the toolbar to ingest and automatically square off or balance this holding."
            )
            ctk.CTkLabel(instr_box, text=instructions, font=ctk.CTkFont(size=11), text_color="#B0BEC5", justify="left").pack(anchor="w", padx=12, pady=10)
        else:
            cert_card = ctk.CTkFrame(container, fg_color="#102A1A", corner_radius=10, border_width=1, border_color="#00E676")
            cert_card.pack(fill="x", pady=(0, 15), padx=5)

            ctk.CTkLabel(cert_card, text="✅ VERIFIED CURRENT HOLDING PORTFOLIO CERTIFICATE", font=ctk.CTkFont(size=14, weight="bold"), text_color="#00E676").pack(anchor="w", padx=15, pady=(12, 6))
            cert_txt = f"This holding is fully verified with matched transaction history in your {self.holding_data.get('Broker', '')} account. {abs(net_q):,.2f} shares/contracts are actively carried forward."
            ctk.CTkLabel(cert_card, text=cert_txt, font=ctk.CTkFont(size=12, weight="bold"), text_color="#E8F5E9", wraplength=880, justify="left").pack(anchor="w", padx=15, pady=(2, 6))

            sug_act = self.holding_data.get('SuggestedAction', 'Monitor quarterly results and support levels.')
            ctk.CTkLabel(cert_card, text=f"• Portfolio Strategy: {sug_act}", font=ctk.CTkFont(size=12), text_color="#C8E6C9", wraplength=880, justify="left").pack(anchor="w", padx=15, pady=(0, 12))

        # 4. Itemized Execution Orders History (Buy Times & Sell Times Drill-Down)
        orders_list = self.holding_data.get('OrdersList', [])
        if not orders_list:
            try:
                b_name = self.holding_data.get('Broker')
                s_name = self.holding_data.get('Symbol')
                c_name = self.holding_data.get('ContractName')
                with trade_orders_engine.get_connection() as conn:
                    cur = conn.cursor()
                    q = """
                        SELECT OrderID, OrderDate, OrderTime, OrderDateTime, Action, ExecutedQty, ExecutionPrice, BrokerOrderNo, ExchangeOrderNo, SourceFile
                        FROM TradeOrders_Master
                        WHERE Broker = ? AND OrderStatus = 'EXECUTED' AND (Symbol = ? OR ContractName = ?)
                        ORDER BY OrderDateTime ASC
                    """
                    cur.execute(q, (b_name, s_name, c_name))
                    for row in cur.fetchall():
                        dt_v = row[3]
                        orders_list.append({
                            'OrderID': row[0],
                            'Date': str(row[1]) if row[1] else '',
                            'Time': str(row[2]) if row[2] else (dt_v.strftime('%H:%M:%S') if dt_v else ''),
                            'DateTime': dt_v,
                            'Action': row[4],
                            'ExecutedQty': float(row[5]),
                            'ExecutionPrice': float(row[6]),
                            'OrderValue': float(row[5] * row[6]),
                            'BrokerOrderNo': row[7] or '',
                            'ExchangeOrderNo': row[8] or '',
                            'SourceFile': row[9] or ''
                        })
            except Exception as e:
                print(f"Error fetching drill-down orders: {e}")

        drill_box = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        drill_box.pack(fill="both", expand=True, pady=(0, 15), padx=5)

        # Header with Execution Breakdown
        drill_hdr = ctk.CTkFrame(drill_box, fg_color="transparent")
        drill_hdr.pack(fill="x", padx=15, pady=(12, 4))

        b_orders = [o for o in orders_list if o.get('Action') == 'BUY']
        s_orders = [o for o in orders_list if o.get('Action') == 'SELL']

        tot_b_qty = sum(o.get('ExecutedQty', 0.0) for o in b_orders)
        tot_s_qty = sum(o.get('ExecutedQty', 0.0) for o in s_orders)
        tot_b_val = sum(o.get('OrderValue', 0.0) for o in b_orders)
        tot_s_val = sum(o.get('OrderValue', 0.0) for o in s_orders)
        avg_b_price = (tot_b_val / tot_b_qty) if tot_b_qty > 0 else 0.0
        avg_s_price = (tot_s_val / tot_s_qty) if tot_s_qty > 0 else 0.0

        ctk.CTkLabel(drill_hdr, text=f"🧾 Itemized Order Execution Timeline ({len(orders_list)} Executions)",
                      font=ctk.CTkFont(size=14, weight="bold"), text_color="#64B5F6").pack(side="left")

        summary_sub = (
            f"🟢 Bought: {tot_b_qty:,.0f} shares ({len(b_orders)} orders @ avg Rs. {avg_b_price:,.2f})  |  "
            f"🔴 Sold: {tot_s_qty:,.0f} shares ({len(s_orders)} orders @ avg Rs. {avg_s_price:,.2f})  |  "
            f"⚖️ Net Open: {(tot_b_qty - tot_s_qty):,.0f} shares"
        )
        ctk.CTkLabel(drill_box, text=summary_sub, font=ctk.CTkFont(size=11, weight="bold"),
                      text_color="#B0BEC5").pack(anchor="w", padx=15, pady=(0, 8))

        # Embedded Sheet with Execution Details
        sheet_container = ctk.CTkFrame(drill_box, fg_color="transparent")
        sheet_container.pack(fill="both", expand=True, padx=15, pady=(0, 15))
        sheet_container.grid_columnconfigure(0, weight=1)
        sheet_container.grid_rowconfigure(0, weight=1)

        drill_headers = [
            "#", "Execution Date", "Time Details", "Action", "Executed Qty",
            "Execution Price", "Order Value", "Broker Order / Ref No", "Exchange Order ID", "Source File"
        ]

        drill_rows = []
        for i, o in enumerate(orders_list, 1):
            act = str(o.get('Action', '')).upper()
            q_v = float(o.get('ExecutedQty', 0.0))
            p_v = float(o.get('ExecutionPrice', 0.0))
            v_v = float(o.get('OrderValue', q_v * p_v))
            t_str = str(o.get('Time', '')) or '—'
            d_str = str(o.get('Date', '')) or '—'
            b_ref = str(o.get('BrokerOrderNo', '')) or '—'
            e_ref = str(o.get('ExchangeOrderNo', '')) or '—'
            src = str(o.get('SourceFile', '')) or '—'

            drill_rows.append([
                str(i), d_str, t_str,
                f"🟢 BUY" if act == 'BUY' else f"🔴 SELL",
                f"{q_v:,.0f}", f"Rs. {p_v:,.2f}", f"Rs. {v_v:,.2f}",
                b_ref, e_ref, src
            ])

        drill_sheet_height = min(280, max(120, len(drill_rows) * 26 + 40))
        drill_sheet = Sheet(
            sheet_container, data=drill_rows if drill_rows else [["No execution records found"]],
            headers=drill_headers, theme="dark blue", height=drill_sheet_height, show_row_index=False
        )
        drill_sheet.enable_bindings("single_select", "row_select", "column_select", "copy", "select_all")
        drill_sheet.grid(row=0, column=0, sticky="nsew")

        # Color highlight execution actions in sheet
        try:
            for idx_r, o in enumerate(orders_list):
                if o.get('Action') == 'BUY':
                    drill_sheet.highlight_cells(row=idx_r, column=3, fg="#00E676")
                    drill_sheet.highlight_cells(row=idx_r, column=4, fg="#00E676")
                else:
                    drill_sheet.highlight_cells(row=idx_r, column=3, fg="#FF5252")
                    drill_sheet.highlight_cells(row=idx_r, column=4, fg="#FF5252")
        except:
            pass

        # Action Buttons
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(pady=10)

        def open_folder():
            try:
                os.makedirs(trade_orders_engine.DEFAULT_ORDER_LOG_DIR, exist_ok=True)
                os.startfile(trade_orders_engine.DEFAULT_ORDER_LOG_DIR)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open sync folder: {e}")

        ctk.CTkButton(btn_row, text="📁 Open Sync Folder", width=160, height=32, fg_color="#1E88E5", hover_color="#1565C0",
                      font=ctk.CTkFont(size=12, weight="bold"), command=open_folder).pack(side="left", padx=8)

        ctk.CTkButton(btn_row, text="Dismiss Audit Window", width=160, height=32, fg_color="#333333", hover_color="#444444",
                      command=self.destroy).pack(side="left", padx=8)

# =============================================================================
# RECONCILIATION GUIDE MODAL
# =============================================================================
class ReconciliationGuideModal(ctk.CTkToplevel):
    def __init__(self, master, dispute_count=0):
        super().__init__(master)
        self.title("Data Reconciliation & Broker Log Guide")
        self.geometry("880x680")
        self.minsize(760, 560)
        self.attributes("-topmost", True)
        self.after(250, lambda: self.attributes("-topmost", False))
        self.focus_force()
        try: self.grab_set()
        except: pass
        self.dispute_count = dispute_count
        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkScrollableFrame(self, corner_radius=10)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(container, text="Data Integrity & Missing Order Log Resolution Guide", font=ctk.CTkFont(size=20, weight="bold")).pack(anchor="w", pady=(0, 5))
        ctk.CTkLabel(container, text=f"Currently {self.dispute_count} positions have unequal BUY & SELL transactions due to missing historical or expiry logs.",
                     font=ctk.CTkFont(size=12), text_color="#FFA726").pack(anchor="w", pady=(0, 15))

        brokers = [
            ("Zerodha (Kite / Console)", [
                "1. Go to Console -> Reports -> Tradebook.",
                "2. Select Date Range from your account opening date to today.",
                "3. Select Segment: 'Equity' and 'Futures & Options'.",
                "4. Download XLSX format and drop it into the Sync Folder."
            ]),
            ("HDFC Securities", [
                "1. Log into HDFC Sec -> Reports -> Equity Derivatives Orderlog.",
                "2. Download historical Orderlog report for each FY from account inception.",
                "3. Save the Excel file into the Sync Folder."
            ]),
            ("INDMoney", [
                "1. Open INDMoney App/Web -> Stocks -> Reports -> Transaction Report.",
                "2. Select 'All Transactions' since account opening.",
                "3. Export Excel/CSV and drop it into the Sync Folder."
            ]),
            ("BlinkX / JM Financial", [
                "1. Go to Reports -> Trade Report (All Segments: Equity, FnO, Commodity).",
                "2. Download the complete historical report and place it into the Sync Folder."
            ])
        ]

        for b_name, steps in brokers:
            box = ctk.CTkFrame(container, fg_color="#181818", corner_radius=8, border_width=1, border_color="#2D2D2D")
            box.pack(fill="x", pady=6)
            ctk.CTkLabel(box, text=f"🏢 {b_name}", font=ctk.CTkFont(size=13, weight="bold"), text_color="#64B5F6").pack(anchor="w", padx=12, pady=(8, 4))
            for st in steps:
                ctk.CTkLabel(box, text=f"  {st}", font=ctk.CTkFont(size=11), text_color="#D1D5DB").pack(anchor="w", padx=12, pady=1)
            ctk.CTkFrame(box, height=4, fg_color="transparent").pack()

        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(pady=15)

        def open_folder():
            try:
                os.makedirs(trade_orders_engine.DEFAULT_ORDER_LOG_DIR, exist_ok=True)
                os.startfile(trade_orders_engine.DEFAULT_ORDER_LOG_DIR)
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open sync folder: {e}")

        ctk.CTkButton(btn_row, text="📁 Open Sync Folder", width=160, height=32, fg_color="#1E88E5", hover_color="#1565C0",
                      font=ctk.CTkFont(size=12, weight="bold"), command=open_folder).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="Close Guide", width=120, height=32, fg_color="#333333", hover_color="#444444",
                      command=self.destroy).pack(side="left", padx=8)

# =============================================================================
# ORDER DETAIL MODAL
# =============================================================================
class OrderDetailModal(ctk.CTkToplevel):
    def __init__(self, master, order_data):
        super().__init__(master)
        self.order_data = order_data
        order_id = order_data.get('OrderID', 'N/A')
        symbol = order_data.get('Symbol', 'Unknown')
        self.title(f"Order Audit & Execution Detail — #{order_id} ({symbol})")
        self.geometry("900x720")
        self.minsize(800, 600)
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

        # Header Badge
        hdr = ctk.CTkFrame(container, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 15))

        action = str(self.order_data.get('Action', 'BUY')).upper()
        act_col = "#00E676" if action == "BUY" else "#FF5252"
        status = str(self.order_data.get('OrderStatus', 'EXECUTED')).upper()
        
        if 'EXEC' in status: stat_col = "#00E676"
        elif 'CANCEL' in status: stat_col = "#FFA726"
        elif 'REJECT' in status: stat_col = "#FF5252"
        else: stat_col = "#9E9E9E"

        ctk.CTkLabel(hdr, text=f"{self.order_data.get('Symbol', '')}", font=ctk.CTkFont(size=24, weight="bold")).pack(side="left")
        ctk.CTkLabel(hdr, text=f" {action} ", fg_color=act_col, text_color="#000000", corner_radius=6, font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=10)
        ctk.CTkLabel(hdr, text=f" {self.order_data.get('Broker', '')} • {self.order_data.get('Segment', '')} ", fg_color="#333333", corner_radius=6, font=ctk.CTkFont(size=12)).pack(side="left", padx=5)

        status_lbl = ctk.CTkLabel(hdr, text=f"Status: {status}", fg_color=stat_col, text_color="#000000" if stat_col != "#9E9E9E" else "#FFFFFF",
                                  corner_radius=8, font=ctk.CTkFont(size=14, weight="bold"), padx=12, pady=4)
        status_lbl.pack(side="right")

        # Order Specs Grid
        grid_frame = ctk.CTkFrame(container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        grid_frame.pack(fill="x", pady=(0, 15), padx=5)
        grid_frame.columnconfigure((0, 1, 2, 3), weight=1)

        ord_price = float(self.order_data.get('OrderPrice', 0.0) or 0.0)
        exec_price = float(self.order_data.get('ExecutionPrice', 0.0) or 0.0)
        ord_qty = float(self.order_data.get('OrderQty', 0.0) or 0.0)
        exec_qty = float(self.order_data.get('ExecutedQty', 0.0) or 0.0)
        slippage = exec_price - ord_price if ord_price > 0 else 0.0

        details = [
            ("Order ID", str(self.order_data.get('OrderID', ''))),
            ("Contract Name", str(self.order_data.get('ContractName', ''))),
            ("Date & Time", str(self.order_data.get('OrderDateTime', ''))),
            ("Exchange", str(self.order_data.get('Exchange', 'NSE'))),
            ("Order Type", str(self.order_data.get('OrderType', 'LIMIT'))),
            ("Product Type", str(self.order_data.get('Product', 'NRML'))),
            ("Order Qty", f"{ord_qty:,.2f}"),
            ("Executed Qty", f"{exec_qty:,.2f}"),
            ("Order Limit Price", f"Rs. {ord_price:,.2f}"),
            ("Execution Price", f"Rs. {exec_price:,.2f}"),
            ("Trigger Price", f"Rs. {float(self.order_data.get('TriggerPrice', 0.0) or 0.0):,.2f}"),
            ("Price Slippage", f"{slippage:+.2f}"),
            ("Broker Order Ref", str(self.order_data.get('BrokerOrderNo') or 'N/A')),
            ("Exchange Order Ref", str(self.order_data.get('ExchangeOrderNo') or 'N/A')),
            ("Financial Year", str(self.order_data.get('FinancialYear', ''))),
            ("Source File", str(self.order_data.get('SourceFile', '')))
        ]

        for i, (label, val) in enumerate(details):
            r = i // 4
            c = i % 4
            cell = ctk.CTkFrame(grid_frame, fg_color="transparent")
            cell.grid(row=r, column=c, padx=12, pady=7, sticky="w")
            ctk.CTkLabel(cell, text=label, font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888").pack(anchor="w")
            ctk.CTkLabel(cell, text=str(val), font=ctk.CTkFont(size=12, weight="normal"), text_color="#FFFFFF").pack(anchor="w")

        # Close
        ctk.CTkButton(container, text="Close Audit Window", width=160, height=32, fg_color="#333333", hover_color="#444444",
                       command=self.destroy).pack(pady=10)

# =============================================================================
# MAIN TRADE ORDERS ANALYSIS FRAME
# =============================================================================
class TradeOrdersAnalysisFrame(ctk.CTkFrame):
    """
    World-class Trade Orders Analysis Frame featuring:
    1. 2-Tier Omni-Filter Bar with Trade Status Filter (🟢 Open Trades Only DEFAULT, 🔵 Closed Trades Only, All)
    2. FIFO Matched Trades Engine with Realized P&L, matched Buy/Sell legs, and ROI %
    3. Defaulting strictly to Open Trades records on load
    4. Execution KPI Ribbon
    5. Active & Open Trades Snapshot Engine (Today or Snapshot as of any Date, Net Qty, Committed Value, DTE Risk)
    6. Execution & Fill Analytics (Fill Rate, Slippage, Order Status Charts)
    7. Time-of-Day Order Flow Analytics (Hourly distribution)
    8. Broker Execution Benchmark (Zerodha vs HDFC vs BlinkX vs INDMoney)
    9. Ingestion & Archival Sync Hub (1-click sync, SHA-256 deduplication, backup routing)
    """

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        self.full_orders_df = pd.DataFrame()
        self.filtered_orders_df = pd.DataFrame()
        self.matched_trades_df = pd.DataFrame()
        self.filtered_trades_df = pd.DataFrame()
        self.open_trades_df = pd.DataFrame()

        self._filter_timer = None
        self._dirty_tabs = {
            "📋 My Trade Log": True,
            "🎯 Active & Open Trades": True,
            "📊 Execution & Fill Analytics": True,
            "⏰ Time-of-Day Order Flow": True,
            "🏢 Broker Benchmark": True,
            "🔄 Sync & Ingestion Hub": True
        }

        self.expiry_map = {}
        self.distinct_meta = trade_orders_engine.get_distinct_filter_values()

        self._build_header()
        self._build_filter_bar()
        self._build_kpi_ribbon()
        self._build_tabs()

        self.after(100, self.load_data)

    # -------------------------------------------------------------
    # 1. HEADER
    # -------------------------------------------------------------
    def _build_header(self):
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.grid(row=0, column=0, sticky="ew", padx=20, pady=(15, 6))

        left = ctk.CTkFrame(hdr, fg_color="transparent")
        left.pack(side="left")

        ctk.CTkLabel(left, text="My Trade Orders Analysis", font=ctk.CTkFont(size=23, weight="bold"), text_color="#FFFFFF").pack(anchor="w")
        ctk.CTkLabel(left, text="Multi-Broker Matched Trades Log • Open & Closed Status Engine • Realized P&L Analytics • Automated Backup Ingestion",
                     font=ctk.CTkFont(size=11), text_color="#9E9E9E").pack(anchor="w")

        right = ctk.CTkFrame(hdr, fg_color="transparent")
        right.pack(side="right")

        self.last_sync_lbl = ctk.CTkLabel(right, text="Last Sync: Loading...", font=ctk.CTkFont(size=11), text_color="#888888")
        self.last_sync_lbl.pack(side="left", padx=8)

        ctk.CTkButton(right, text=" Sync Folder", width=105, height=30, fg_color="#1E88E5", hover_color="#1565C0",
                      font=ctk.CTkFont(size=12, weight="bold"), command=self._trigger_sync_folder).pack(side="left", padx=3)

        ctk.CTkButton(right, text=" Export CSV", width=95, height=30, fg_color="#37474F", hover_color="#263238",
                      font=ctk.CTkFont(size=12), command=self._export_to_csv).pack(side="left", padx=3)

        ctk.CTkButton(right, text=" Refresh", width=85, height=30, fg_color="#FF8F00", hover_color="#F57C00",
                      font=ctk.CTkFont(size=12, weight="bold"), command=self.load_data).pack(side="left", padx=3)

    # -------------------------------------------------------------
    # 2. 2-TIER OMNI-FILTER BAR (WITH TRADE STATUS DEFAULTING TO OPEN)
    # -------------------------------------------------------------
    def _build_filter_bar(self):
        f_wrap = ctk.CTkFrame(self, fg_color="#1A1A1A", corner_radius=10, border_width=1, border_color="#2A2A2A")
        f_wrap.grid(row=1, column=0, sticky="ew", padx=20, pady=(4, 8))

        # ROW 1: PRIMARY CRITERIA (Trade Status, FY, Broker, Segment, Action, Order Type, Product)
        row1 = ctk.CTkFrame(f_wrap, fg_color="transparent")
        row1.pack(fill="x", padx=10, pady=(6, 3))

        # 1. Trade Status Filter (Supports Holdings & Dispute Data)
        ctk.CTkLabel(row1, text="Trade Status:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#00E676").pack(side="left", padx=(2, 2))
        self.f_trade_status = ctk.StringVar(value="💼 Current Holdings (All Segments)")
        self.trade_status_menu = ctk.CTkOptionMenu(
            row1, variable=self.f_trade_status,
            values=[
                "💼 Current Holdings (All Segments)",
                "✅ Verified Holdings Only",
                "⚠️ Dispute Data (Incomplete Logs)",
                "🟢 Open Trades Only",
                "🔵 Closed Trades Only",
                "All Trades (Open & Closed)",
                "Raw Order Log Book"
            ],
            width=210, height=26, font=ctk.CTkFont(size=11, weight="bold"), command=lambda _: self.apply_filters()
        )
        self.trade_status_menu.pack(side="left", padx=(0, 8))

        # 2. FY Filter
        ctk.CTkLabel(row1, text="FY:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64B5F6").pack(side="left", padx=(2, 2))
        self.f_fy = ctk.StringVar(value="All FYs")
        fy_values = self.distinct_meta.get('financial_years', ["All FYs"])
        self.fy_menu = ctk.CTkOptionMenu(row1, variable=self.f_fy, values=fy_values, width=95, height=26, font=ctk.CTkFont(size=11),
                                         command=self._on_fy_changed)
        self.fy_menu.pack(side="left", padx=(0, 8))

        # 3. Broker Filter
        ctk.CTkLabel(row1, text="Broker:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(2, 2))
        self.f_broker = ctk.StringVar(value="All Brokers")
        broker_vals = self.distinct_meta.get('brokers', ["All Brokers", "Zerodha", "HDFC Securities", "BlinkX", "INDMoney"])
        self.broker_menu = ctk.CTkOptionMenu(row1, variable=self.f_broker, values=broker_vals,
                                             width=115, height=26, font=ctk.CTkFont(size=11), command=lambda _: self.apply_filters())
        self.broker_menu.pack(side="left", padx=(0, 8))

        # 4. Segment Filter
        ctk.CTkLabel(row1, text="Segment:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(2, 2))
        self.f_segment = ctk.StringVar(value="All Segments")
        seg_vals = self.distinct_meta.get('segments', ["All Segments", "Equity", "FnO", "Commodity"])
        self.segment_menu = ctk.CTkOptionMenu(row1, variable=self.f_segment, values=seg_vals,
                                              width=105, height=26, font=ctk.CTkFont(size=11), command=lambda _: self.apply_filters())
        self.segment_menu.pack(side="left", padx=(0, 8))

        # 5. Stance / Action Filter (All / LONG / SHORT)
        ctk.CTkLabel(row1, text="Stance:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(2, 2))
        self.f_action = ctk.StringVar(value="All")
        self.action_menu = ctk.CTkOptionMenu(row1, variable=self.f_action, values=["All", "LONG", "SHORT"],
                                             width=85, height=26, font=ctk.CTkFont(size=11), command=lambda _: self.apply_filters())
        self.action_menu.pack(side="left", padx=(0, 8))

        # 6. Order Type (LIMIT / MARKET)
        ctk.CTkLabel(row1, text="Type:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(2, 2))
        self.f_type = ctk.StringVar(value="All Types")
        self.type_menu = ctk.CTkOptionMenu(row1, variable=self.f_type, values=["All Types", "LIMIT", "MARKET", "SL", "SL-M"],
                                           width=95, height=26, font=ctk.CTkFont(size=11), command=lambda _: self.apply_filters())
        self.type_menu.pack(side="left", padx=(0, 8))

        # 7. Product (CNC / NRML / MIS / Margin)
        ctk.CTkLabel(row1, text="Product:", font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(2, 2))
        self.f_product = ctk.StringVar(value="All Products")
        self.product_menu = ctk.CTkOptionMenu(row1, variable=self.f_product, values=["All Products", "CNC", "NRML", "MIS", "Margin"],
                                              width=100, height=26, font=ctk.CTkFont(size=11), command=lambda _: self.apply_filters())
        self.product_menu.pack(side="left", padx=(0, 4))

        # ROW 2: DATE RANGE (WITH 📅 CALENDAR) + EXPIRY DATE + SYMBOL DROPDOWN & SEARCH
        row2 = ctk.CTkFrame(f_wrap, fg_color="transparent")
        row2.pack(fill="x", padx=10, pady=(2, 6))

        # Trade Date Range
        ctk.CTkLabel(row2, text="Date Range:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#4FC3F7").pack(side="left", padx=(2, 2))
        self.f_date_from = ctk.StringVar()
        self.date_from_e = ctk.CTkEntry(row2, textvariable=self.f_date_from, placeholder_text="YYYY-MM-DD", width=88, height=26, font=ctk.CTkFont(size=11))
        self.date_from_e.pack(side="left", padx=1)
        self.date_from_e.bind("<KeyRelease>", self._schedule_filter_update)
        ctk.CTkButton(row2, text="📅", width=26, height=26, fg_color="#333333", hover_color="#444444",
                      command=lambda: self._open_calendar_picker(self.f_date_from, "Select From Date")).pack(side="left", padx=(1, 3))

        ctk.CTkLabel(row2, text="to", font=ctk.CTkFont(size=11)).pack(side="left", padx=1)
        self.f_date_to = ctk.StringVar()
        self.date_to_e = ctk.CTkEntry(row2, textvariable=self.f_date_to, placeholder_text="YYYY-MM-DD", width=88, height=26, font=ctk.CTkFont(size=11))
        self.date_to_e.pack(side="left", padx=1)
        self.date_to_e.bind("<KeyRelease>", self._schedule_filter_update)
        ctk.CTkButton(row2, text="📅", width=26, height=26, fg_color="#333333", hover_color="#444444",
                      command=lambda: self._open_calendar_picker(self.f_date_to, "Select To Date")).pack(side="left", padx=(1, 8))

        # Expiry Date Filter
        ctk.CTkLabel(row2, text="Expiry Date:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#CE93D8").pack(side="left", padx=(2, 2))
        self.f_expiry = ctk.StringVar(value="All Expiries")
        self.expiry_menu = ctk.CTkOptionMenu(row2, variable=self.f_expiry, values=["All Expiries"], width=125, height=26, font=ctk.CTkFont(size=11),
                                             command=lambda _: self.apply_filters())
        self.expiry_menu.pack(side="left", padx=(0, 8))

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
        try: top.transient(self.winfo_toplevel())
        except: pass

        cur_val = target_var.get().strip()
        y, m, d = datetime.now().year, datetime.now().month, datetime.now().day
        if cur_val:
            try:
                dt = pd.to_datetime(cur_val)
                y, m, d = dt.year, dt.month, dt.day
            except: pass

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
        if val == "All Symbols": self.f_sym.set("")
        else: self.f_sym.set(val)
        self.apply_filters()

    def _on_fy_changed(self, sel_fy):
        self._update_expiry_options(sel_fy)
        self.apply_filters()

    def _update_expiry_options(self, sel_fy):
        if self.full_orders_df.empty: return
        df = self.full_orders_df.dropna(subset=['ExpiryDate'])
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
            except: pass

        self.expiry_menu.configure(values=display_values[:100])
        self.f_expiry.set("All Expiries")

    # -------------------------------------------------------------
    # 3. EXECUTION KPI RIBBON
    # -------------------------------------------------------------
    def _build_kpi_ribbon(self):
        self.kpi_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_frame.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 8))
        self.kpi_frame.columnconfigure((0, 1, 2, 3, 4, 5), weight=1)

        self.kpi_cards = {}
        metrics = [
            ("total_trades", "Open Trades", "0", "#00E676"),
            ("committed_open", "Committed Capital", "Rs. 0.00", "#64B5F6"),
            ("realized_pnl", "Realized P&L", "Rs. 0.00", "#29B6F6"),
            ("win_rate", "Win Rate %", "0.0%", "#FFA726"),
            ("closed_trades", "Closed Trades", "0", "#CE93D8"),
            ("friction_orders", "Total Order Fills", "0", "#FFFFFF")
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

    # -------------------------------------------------------------
    # 4. TABS
    # -------------------------------------------------------------
    def _build_tabs(self):
        self.tabs = ctk.CTkTabview(self, corner_radius=10, command=self._on_tab_changed)
        self.tabs.grid(row=3, column=0, sticky="nsew", padx=20, pady=(0, 15))
        self.grid_rowconfigure(3, weight=1)

        self.tab_orders = self.tabs.add("📋 My Trade Log")
        self.tab_open = self.tabs.add("💼 Current Holdings Portfolio")
        self.tab_analytics = self.tabs.add("📊 Execution & Fill Analytics")
        self.tab_flow = self.tabs.add("⏰ Time-of-Day Order Flow")
        self.tab_brokers = self.tabs.add("🏢 Broker Benchmark")
        self.tab_sync = self.tabs.add("🔄 Sync & Ingestion Hub")

        try:
            self.tabs._segmented_button.configure(font=ctk.CTkFont(size=11, weight="bold"))
        except: pass

        self._build_trade_log_tab()
        self._build_open_trades_tab()
        self._build_analytics_tab()
        self._build_flow_tab()
        self._build_brokers_tab()
        self._build_sync_tab()

    def _on_tab_changed(self):
        cur_tab = self.tabs.get()
        if self._dirty_tabs.get(cur_tab, False):
            self._render_active_tab(cur_tab)

    def _render_active_tab(self, tab_name):
        self._dirty_tabs[tab_name] = False
        if "Trade Log" in tab_name:
            self._populate_trade_log_sheet()
        elif "Current Holdings" in tab_name or "Active & Open" in tab_name:
            self._populate_open_trades_sheet()
        elif "Execution & Fill" in tab_name:
            self._render_analytics()
        elif "Time-of-Day" in tab_name:
            self._render_flow()
        elif "Broker Benchmark" in tab_name:
            self._render_brokers()
        elif "Sync & Ingestion" in tab_name:
            self._update_sync_tab_status()

    # -------------------------------------------------------------
    # TAB 1: MY TRADE LOG (MATCHED TRADES & OPEN TRADES)
    # -------------------------------------------------------------
    def _build_trade_log_tab(self):
        parent = self.tab_orders
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        # Top Bar within Tab
        tb = ctk.CTkFrame(parent, fg_color="transparent")
        tb.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 5))

        self.trade_log_count_lbl = ctk.CTkLabel(tb, text="Showing 0 open trades", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00E676")
        self.trade_log_count_lbl.pack(side="left", padx=5)

        ctk.CTkLabel(tb, text="💡 Double-click any row to inspect matched Buy/Sell legs, execution slippage & audit trail",
                     font=ctk.CTkFont(size=11, slant="italic"), text_color="#888888").pack(side="left", padx=15)

        ctk.CTkButton(tb, text="🔍 Inspect Matched Legs & Audit", width=220, height=28, fg_color="#1E88E5", hover_color="#1565C0",
                      font=ctk.CTkFont(size=11, weight="bold"), command=self._open_selected_trade_modal).pack(side="right", padx=5)

        # Sheet Container
        s_box = ctk.CTkFrame(parent, fg_color="#121212", corner_radius=8)
        s_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 5))
        s_box.grid_columnconfigure(0, weight=1)
        s_box.grid_rowconfigure(0, weight=1)

        self.matched_headers = [
            "Trade ID", "Status", "Broker", "Segment", "Symbol", "Contract / Scrip", "Stance", "Quantity",
            "Entry Date", "Entry Price", "Exit Date", "Exit Price", "Buy Value", "Sell Value", "Gross P&L",
            "ROI %", "Holding Days", "Expiry Date", "DTE Risk", "Deep Insights"
        ]

        self.trade_sheet = Sheet(
            s_box,
            data=[[]],
            headers=self.matched_headers,
            theme="dark blue",
            height=500,
            show_row_index=True
        )
        self.trade_sheet.enable_bindings(
            "single_select", "row_select", "column_select", "row_height_resize",
            "double_click_row_selection", "copy", "select_all"
        )
        self.trade_sheet.grid(row=0, column=0, sticky="nsew")

        # Double click bindings
        self.trade_sheet.extra_bindings("cell_select", self._on_trade_sheet_click)
        self.trade_sheet.extra_bindings("row_select", self._on_trade_sheet_click)
        self.trade_sheet.bind("<Double-Button-1>", self._on_trade_sheet_double_click)

    def _on_trade_sheet_click(self, event=None):
        self._last_selected_trade_row = resolve_sheet_row(event, self.trade_sheet)

    def _on_trade_sheet_double_click(self, event=None):
        r = resolve_sheet_row(event, self.trade_sheet)
        if r is not None:
            self._last_selected_trade_row = r
            self._open_selected_trade_modal()

    def _open_selected_trade_modal(self):
        r = getattr(self, '_last_selected_trade_row', None)
        mode = self.f_trade_status.get()
        if "Raw Order" in mode:
            if r is None or self.filtered_orders_df.empty or r < 0 or r >= len(self.filtered_orders_df):
                messagebox.showinfo("Selection Required", "Please select an order row to inspect.")
                return
            OrderDetailModal(self, self.filtered_orders_df.iloc[r].to_dict())
        else:
            if r is None or self.filtered_trades_df.empty or r < 0 or r >= len(self.filtered_trades_df):
                messagebox.showinfo("Selection Required", "Please select a trade row to inspect matched legs.")
                return
            MatchedTradeDetailModal(self, self.filtered_trades_df.iloc[r].to_dict())

    def _populate_trade_log_sheet(self):
        mode = self.f_trade_status.get()

        if "Raw Order" in mode:
            # Display Raw Orders Log
            df = self.filtered_orders_df
            raw_headers = [
                "Order ID", "Date", "Time", "Broker", "Segment", "Symbol", "Contract / Instrument",
                "Action", "Status", "Order Qty", "Exec Qty", "Order Price", "Exec Price", "Slippage",
                "Type", "Product", "Exchange Ref", "Rejection Reason"
            ]
            self.trade_sheet.headers(raw_headers)

            if df.empty:
                self.trade_sheet.set_sheet_data([[]])
                self.trade_log_count_lbl.configure(text="Showing 0 raw orders", text_color="#9E9E9E")
                return

            rows = []
            for _, r in df.iterrows():
                ord_p = float(r.get('OrderPrice', 0.0) or 0.0)
                exc_p = float(r.get('ExecutionPrice', 0.0) or 0.0)
                slip = exc_p - ord_p if ord_p > 0 else 0.0
                rows.append([
                    str(r.get('OrderID', '')), str(r.get('OrderDate', '')), str(r.get('OrderTime', '')),
                    str(r.get('Broker', '')), str(r.get('Segment', '')), str(r.get('Symbol', '')),
                    str(r.get('ContractName', '')), str(r.get('Action', '')), str(r.get('OrderStatus', '')),
                    f"{float(r.get('OrderQty', 0.0) or 0.0):,.0f}", f"{float(r.get('ExecutedQty', 0.0) or 0.0):,.0f}",
                    f"Rs. {ord_p:,.2f}", f"Rs. {exc_p:,.2f}", f"{slip:+.2f}" if ord_p > 0 else "0.00",
                    str(r.get('OrderType', '')), str(r.get('Product', '')),
                    str(r.get('ExchangeOrderNo') or r.get('BrokerOrderNo') or 'N/A'), str(r.get('RejectionReason') or '')
                ])
            self.trade_sheet.set_sheet_data(rows)
            self.trade_log_count_lbl.configure(text=f"Showing {len(rows):,} raw orders", text_color="#64B5F6")
            return

        # Display Matched Trades (Open / Closed / All)
        self.trade_sheet.headers(self.matched_headers)
        df = self.filtered_trades_df

        if df.empty:
            self.trade_sheet.set_sheet_data([[]])
            status_text = "open" if "Open Trades Only" in mode else ("closed" if "Closed Trades Only" in mode else "matched")
            self.trade_log_count_lbl.configure(text=f"Showing 0 {status_text} trades", text_color="#9E9E9E")
            return

        rows = []
        for _, r in df.iterrows():
            st = str(r.get('Status', 'OPEN'))
            stance = str(r.get('Stance', 'LONG'))
            exit_d = r.get('ExitDate')
            exit_p = r.get('ExitPrice')
            exit_d_str = str(exit_d) if (exit_d is not None and pd.notna(exit_d)) else "— (Active)"
            exit_p_str = f"Rs. {float(exit_p):,.2f}" if (exit_p is not None and pd.notna(exit_p)) else "—"

            pnl = r.get('GrossPnL')
            if st == 'CLOSED' and pnl is not None and pd.notna(pnl):
                pnl_f = float(pnl)
                pnl_str = f"+Rs. {pnl_f:,.2f}" if pnl_f >= 0 else f"-Rs. {abs(pnl_f):,.2f}"
            else:
                pnl_str = "— (Open Position)"

            roi = r.get('ROIPct')
            roi_str = f"{float(roi):+.1f}%" if (roi is not None and pd.notna(roi) and st == 'CLOSED') else "—"

            rows.append([
                str(r.get('TradeID', '')),
                f"🟢 OPEN" if st == 'OPEN' else "🔵 CLOSED",
                str(r.get('Broker', '')),
                str(r.get('Segment', '')),
                str(r.get('Symbol', '')),
                str(r.get('ContractName', '')),
                f"🟢 {stance}" if stance == 'LONG' else f"🔴 {stance}",
                f"{float(r.get('Quantity', 0.0)):,.2f}",
                str(r.get('EntryDate', '')),
                f"Rs. {float(r.get('EntryPrice', 0.0)):,.2f}",
                exit_d_str,
                exit_p_str,
                f"Rs. {float(r.get('BuyValue', 0.0) or 0.0):,.2f}",
                f"Rs. {float(r.get('SellValue', 0.0) or 0.0):,.2f}" if st == 'CLOSED' else "—",
                pnl_str,
                roi_str,
                f"{r.get('HoldingDays', 0)}d",
                str(r.get('ExpiryDate') or '—'),
                str(r.get('DTERisk') or ('Closed' if st == 'CLOSED' else 'N/A')),
                str(r.get('Insights', ''))
            ])

        self.trade_sheet.set_sheet_data(rows)
        lbl_col = "#00E676" if "Open Trades Only" in mode else ("#29B6F6" if "Closed Trades Only" in mode else "#FFA726")
        mode_txt = "Open Trades" if "Open Trades Only" in mode else ("Closed Trades" if "Closed Trades Only" in mode else "All Trades (Open + Closed)")
        self.trade_log_count_lbl.configure(text=f"Showing {len(rows):,} {mode_txt}", text_color=lbl_col)

        # Highlight cell statuses & P&L
        try:
            for idx, r in enumerate(df.itertuples()):
                st = getattr(r, 'Status', 'OPEN')
                pnl = getattr(r, 'GrossPnL', None)
                stance = getattr(r, 'Stance', 'LONG')

                if st == 'OPEN':
                    self.trade_sheet.highlight_cells(row=idx, column=1, fg="#00E676")
                else:
                    self.trade_sheet.highlight_cells(row=idx, column=1, fg="#29B6F6")

                if stance == 'LONG':
                    self.trade_sheet.highlight_cells(row=idx, column=6, fg="#00E676")
                else:
                    self.trade_sheet.highlight_cells(row=idx, column=6, fg="#FF5252")

                if st == 'CLOSED' and pnl is not None and pd.notna(pnl):
                    if float(pnl) >= 0:
                        self.trade_sheet.highlight_cells(row=idx, column=14, fg="#00E676")
                    else:
                        self.trade_sheet.highlight_cells(row=idx, column=14, fg="#FF5252")
        except: pass

    # -------------------------------------------------------------
    # TAB 2: CURRENT HOLDINGS & CARRY FORWARD PORTFOLIO (ALL SEGMENTS)
    # -------------------------------------------------------------
    def _build_open_trades_tab(self):
        parent = self.tab_open
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(3, weight=1)

        # 1. Top Controls & Snapshot Toolbar (Row 0)
        tb = ctk.CTkFrame(parent, fg_color="#181818", corner_radius=8)
        tb.grid(row=0, column=0, sticky="ew", padx=10, pady=(6, 4))

        # Snapshot Mode Selector
        ctk.CTkLabel(tb, text="Snapshot Mode:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64B5F6").pack(side="left", padx=(10, 4))
        self.open_mode_var = ctk.StringVar(value="Current Holdings (Today)")
        self.open_mode_menu = ctk.CTkOptionMenu(
            tb, variable=self.open_mode_var,
            values=["Current Holdings (Today)", "As of Specific Date (Historical Replay)"],
            width=205, height=26, font=ctk.CTkFont(size=11),
            command=self._on_open_mode_changed
        )
        self.open_mode_menu.pack(side="left", padx=(0, 6))

        # As-of Date Entry + Calendar (hidden by default)
        self.as_of_lbl = ctk.CTkLabel(tb, text="As of:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#FFA726")
        self.as_of_var = ctk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        self.as_of_entry = ctk.CTkEntry(tb, textvariable=self.as_of_var, width=90, height=26, font=ctk.CTkFont(size=11))
        self.as_of_cal_btn = ctk.CTkButton(tb, text="📅", width=26, height=26, fg_color="#333333", hover_color="#444444",
                                           command=lambda: self._open_calendar_picker(self.as_of_var, "Select Snapshot As-of Date"))

        # Action Buttons
        ctk.CTkButton(tb, text="🔄 Refresh Live LTP", width=145, height=26, fg_color="#0091EA", hover_color="#0077C2",
                      font=ctk.CTkFont(size=11, weight="bold"), command=self._refresh_live_ltp).pack(side="left", padx=4)

        ctk.CTkButton(tb, text="🔍 Inspect Holding & Audit", width=160, height=26, fg_color="#2E7D32", hover_color="#1B5E20",
                      font=ctk.CTkFont(size=11, weight="bold"), command=self._open_selected_holding_modal).pack(side="left", padx=4)

        ctk.CTkButton(tb, text="📥 Export CSV", width=95, height=26, fg_color="#37474F", hover_color="#263238",
                      font=ctk.CTkFont(size=11), command=self._export_holdings_csv).pack(side="left", padx=4)

        def _open_sync_folder():
            try:
                os.makedirs(trade_orders_engine.DEFAULT_ORDER_LOG_DIR, exist_ok=True)
                os.startfile(trade_orders_engine.DEFAULT_ORDER_LOG_DIR)
            except Exception as e:
                messagebox.showerror("Error", f"Could not open folder: {e}")

        ctk.CTkButton(tb, text="📁 Sync Folder", width=95, height=26, fg_color="#4E342E", hover_color="#3E2723",
                      font=ctk.CTkFont(size=11), command=_open_sync_folder).pack(side="left", padx=4)

        # Right Summary Label
        self.open_summary_lbl = ctk.CTkLabel(tb, text="Loading Holdings...", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00E676")
        self.open_summary_lbl.pack(side="right", padx=15)

        # 2. Primary Segment Switcher (Row 1)
        seg_frame = ctk.CTkFrame(parent, fg_color="transparent")
        seg_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(2, 4))
        seg_frame.grid_columnconfigure(0, weight=1)

        self.holding_segment_var = ctk.StringVar(value="📈 Active Equity Holdings")
        self.holding_segment_ctl = ctk.CTkSegmentedButton(
            seg_frame,
            values=[
                "📈 Active Equity Holdings",
                "⚡ Active FnO Holdings",
                "🪙 Active Commodity Holdings",
                "🛠️ Data Reconciliation Hub"
            ],
            variable=self.holding_segment_var,
            font=ctk.CTkFont(size=12, weight="bold"),
            selected_color="#1E88E5",
            selected_hover_color="#1565C0",
            command=self._on_segment_tab_changed
        )
        self.holding_segment_ctl.pack(side="left", fill="x", expand=True)

        # 3. Dynamic Executive Decision Intelligence & KPI Suite (Row 2)
        self.exec_container = ctk.CTkFrame(parent, fg_color="#141414", corner_radius=8, border_width=1, border_color="#262626")
        self.exec_container.grid(row=2, column=0, sticky="ew", padx=10, pady=(2, 6))
        self.exec_container.grid_columnconfigure(0, weight=1)

        # Sub-frame for 4 KPI Cards
        self.kpi_cards_frame = ctk.CTkFrame(self.exec_container, fg_color="transparent")
        self.kpi_cards_frame.pack(fill="x", padx=6, pady=(6, 4))
        self.kpi_cards_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)

        self.holding_kpis = {}
        h_kpi_defs = [
            ("card_1", "📦 Verified Demat Capital", "Rs. 0.00", "0 Delivery Stocks Held", "#00E676"),
            ("card_2", "💼 Current Portfolio Value", "Rs. 0.00", "Unrealized P&L: Rs. 0.00", "#64B5F6"),
            ("card_3", "🏆 Top Wealth Contributors", "Analyzing...", "Top 3 Long Positions", "#FFD600"),
            ("card_4", "🎯 Live Quotes & Decision Health", "🟢 Live LTP Active", "Real-time NSE Quotes", "#00E5FF")
        ]
        for col_idx, (k_id, title, init_v, init_sub, color) in enumerate(h_kpi_defs):
            c_box = ctk.CTkFrame(self.kpi_cards_frame, fg_color="#1E1E1E", corner_radius=6, border_width=1, border_color="#2A2A2A")
            c_box.grid(row=0, column=col_idx, sticky="nsew", padx=3, pady=2)
            ctk.CTkLabel(c_box, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color="#A0A0A0").pack(anchor="w", padx=8, pady=(4, 1))
            v_lbl = ctk.CTkLabel(c_box, text=init_v, font=ctk.CTkFont(size=14, weight="bold"), text_color=color)
            v_lbl.pack(anchor="w", padx=8, pady=(0, 1))
            s_lbl = ctk.CTkLabel(c_box, text=init_sub, font=ctk.CTkFont(size=10), text_color="#888888")
            s_lbl.pack(anchor="w", padx=8, pady=(0, 4))
            self.holding_kpis[k_id] = (v_lbl, s_lbl)

        # Sub-frame for Decision Quick-Filters & Action Ribbon
        self.exec_action_frame = ctk.CTkFrame(self.exec_container, fg_color="#1A1A1A", corner_radius=6)
        self.exec_action_frame.pack(fill="x", padx=6, pady=(0, 6))

        # 4. Sheet Container & tksheet (Row 3)
        s_box = ctk.CTkFrame(parent, fg_color="#121212", corner_radius=8)
        s_box.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 5))
        s_box.grid_columnconfigure(0, weight=1)
        s_box.grid_rowconfigure(0, weight=1)

        self.equity_headers = [
            "Status", "Broker", "Symbol", "Company / Scrip", "Held Qty", "Avg Buy Price",
            "Committed Capital", "Current Price (LTP)", "Day's Change %", "Current Market Value",
            "Unrealized P&L", "Unrealized ROI %", "Decision Verdict", "Trailing Stoploss",
            "Actionable Guidance", "Days Held"
        ]

        self.fno_headers = [
            "Status", "Broker", "Symbol", "Contract Name", "Option Type", "Strike Price",
            "Expiry Date", "DTE", "Stance", "Held Qty", "Avg Entry Price", "Committed Capital",
            "Current Price", "Current MTM Value", "Unrealized P&L", "ROI %", "Decision Verdict",
            "Actionable Guidance", "Days Open"
        ]

        self.commodity_headers = [
            "Status", "Broker", "Symbol", "Contract Name", "Expiry Date", "DTE", "Stance",
            "Held Qty", "Avg Entry Price", "Committed Capital", "Current Price", "MTM P&L",
            "ROI %", "Decision Verdict", "Actionable Guidance"
        ]

        self.reconciliation_headers = [
            "Dispute Type", "Broker", "Segment", "Symbol", "Contract / Scrip",
            "Deficit / Expired Qty", "Avg Price", "Committed / Sold Val", "Dispute Reason & Diagnosis",
            "Days Unresolved", "Recommended 1-Click Action"
        ]

        self.open_sheet = Sheet(
            s_box, data=[[]], headers=self.equity_headers, theme="dark blue", height=450, show_row_index=True
        )
        self.open_sheet.enable_bindings(
            "single_select", "row_select", "column_select", "row_height_resize", "copy", "select_all"
        )
        self.open_sheet.grid(row=0, column=0, sticky="nsew")

        # Double-click and single-click bindings
        self.open_sheet.extra_bindings("cell_select", self._on_open_sheet_click)
        self.open_sheet.extra_bindings("row_select", self._on_open_sheet_click)
        self.open_sheet.bind("<Double-Button-1>", self._on_open_sheet_double_click)
        self._selected_holding_row_idx = None
        self._current_holdings_display_df = pd.DataFrame()
        self.decision_filter_var = ctk.StringVar(value="🌟 All Equity")

    def _on_open_mode_changed(self, val):
        if "Specific Date" in val:
            self.as_of_lbl.pack(side="left", padx=(5, 2))
            self.as_of_entry.pack(side="left", padx=1)
            self.as_of_cal_btn.pack(side="left", padx=(1, 5))
        else:
            self.as_of_lbl.pack_forget()
            self.as_of_entry.pack_forget()
            self.as_of_cal_btn.pack_forget()
        self._refresh_open_trades()

    def _on_segment_tab_changed(self, val):
        self.decision_filter_var.set("🌟 All Positions")
        self._populate_open_trades_sheet()

    def _on_decision_filter_chip_changed(self, val):
        self._populate_open_trades_sheet()

    def _refresh_open_trades(self):
        mode = self.open_mode_var.get()
        as_of = self.as_of_var.get().strip() if "Specific Date" in mode else None
        filts = {
            'broker': self.f_broker.get(),
            'segment': self.f_segment.get(),
            'symbol': self.f_sym.get().strip()
        }
        self.open_trades_df = trade_orders_engine.compute_open_positions(as_of_date=as_of, filters=filts)
        self._populate_open_trades_sheet()

    def _refresh_live_ltp(self):
        mode = self.open_mode_var.get()
        as_of = self.as_of_var.get().strip() if "Specific Date" in mode else None
        filts = {
            'broker': self.f_broker.get(),
            'segment': self.f_segment.get(),
            'symbol': self.f_sym.get().strip()
        }
        self.open_summary_lbl.configure(text="⏳ Fetching Real-Time LTP Quotes...", text_color="#00E5FF")
        self.update_idletasks()
        self.open_trades_df = trade_orders_engine.compute_open_positions(as_of_date=as_of, filters=filts, force_refresh_ltp=True)
        self._populate_open_trades_sheet()

    def _run_auto_resolve_equity(self):
        confirm = messagebox.askyesno(
            "Auto-Resolve Demat Disputes",
            "This will create balancing opening acquisition entries for the 54 historical pre-log delivery sales (where shares were sold from Demat that were acquired before order logs began).\n\n"
            "This balances all pre-log sales to 0 shares cleanly, resolving negative delivery disputes.\n\n"
            "Do you want to proceed?"
        )
        if not confirm:
            return
        inserted, msg = trade_orders_engine.auto_resolve_equity_inception_disputes()
        messagebox.showinfo("Resolution Complete", f"{msg}\n\nRecomputing portfolio holdings...")
        self._refresh_open_trades()

    def _run_auto_square_off_derivatives(self):
        confirm = messagebox.askyesno(
            "Auto-Square Off Expired Derivatives",
            "This will create exchange expiry settlement entries at expiry date for all expired F&O / Commodity contracts that had no closing trade in the raw log.\n\n"
            "This cleanly closes out all historical expired contracts.\n\n"
            "Do you want to proceed?"
        )
        if not confirm:
            return
        inserted, msg = trade_orders_engine.auto_square_off_expired_derivatives()
        messagebox.showinfo("Settlement Complete", f"{msg}\n\nRecomputing portfolio holdings...")
        self._refresh_open_trades()

    def _run_undo_auto_resolve(self):
        confirm = messagebox.askyesno(
            "Undo Inception Reconciliation",
            "This will remove all auto-generated Demat opening acquisition records and revert positions to raw logbook state.\n\nProceed?"
        )
        if not confirm:
            return
        del_eq, _ = trade_orders_engine.undo_auto_resolve_equity_inception()
        del_fno, _ = trade_orders_engine.undo_auto_square_off_expired_derivatives()
        messagebox.showinfo("Reverted", f"Reverted {del_eq} Demat inception records and {del_fno} derivative settlement records.")
        self._refresh_open_trades()

    def _open_reconciliation_guide(self):
        dispute_cnt = 0
        if not self.open_trades_df.empty:
            dispute_cnt = len(self.open_trades_df[self.open_trades_df['HoldingStatus'] == 'DISPUTE_DATA'])
        ReconciliationGuideModal(self, dispute_count=dispute_cnt)

    def _on_open_sheet_click(self, event=None):
        r_idx = resolve_sheet_row(event, self.open_sheet)
        if r_idx is not None and r_idx >= 0:
            self._selected_holding_row_idx = r_idx

    def _on_open_sheet_double_click(self, event=None):
        r_idx = resolve_sheet_row(event, self.open_sheet)
        if r_idx is None or r_idx < 0:
            r_idx = self._selected_holding_row_idx
        if r_idx is not None and r_idx >= 0 and not self._current_holdings_display_df.empty and r_idx < len(self._current_holdings_display_df):
            row_data = self._current_holdings_display_df.iloc[r_idx].to_dict()
            HoldingDisputeDetailModal(self, row_data)

    def _open_selected_holding_modal(self):
        if self._selected_holding_row_idx is not None and not self._current_holdings_display_df.empty and self._selected_holding_row_idx < len(self._current_holdings_display_df):
            row_data = self._current_holdings_display_df.iloc[self._selected_holding_row_idx].to_dict()
            HoldingDisputeDetailModal(self, row_data)
        else:
            messagebox.showinfo("Select Holding", "Please select a holding row in the table first or double-click any row to inspect.")

    def _export_holdings_csv(self):
        if self._current_holdings_display_df.empty:
            messagebox.showinfo("Export CSV", "No holdings data to export.")
            return
        fpath = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], title="Export Current Holdings Portfolio")
        if fpath:
            try:
                self._current_holdings_display_df.to_csv(fpath, index=False)
                messagebox.showinfo("Export Successful", f"Holdings exported successfully to:\n{fpath}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export holdings: {e}")

    def _render_decision_actions_ribbon(self, seg_mode, df_seg):
        for w in self.exec_action_frame.winfo_children():
            w.destroy()

        if "Active Equity" in seg_mode:
            # Decision filter chips
            tot_cnt = len(df_seg)
            sh_cnt = len(df_seg[df_seg['DecisionVerdict'].str.contains('STRONG HOLD', na=False)])
            pt_cnt = len(df_seg[df_seg['DecisionVerdict'].str.contains('PROFIT TRIM', na=False)])
            acc_cnt = len(df_seg[df_seg['DecisionVerdict'].str.contains('ACCUMULATE', na=False)])
            mon_cnt = len(df_seg[df_seg['DecisionVerdict'].str.contains('MONITOR', na=False)])
            cut_cnt = len(df_seg[df_seg['DecisionVerdict'].str.contains('RISK CUT', na=False)])

            ctk.CTkLabel(self.exec_action_frame, text="Institutional Decision Filter:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64B5F6").pack(side="left", padx=(10, 8), pady=4)

            chip_vals = [
                f"🌟 All Equity ({tot_cnt})",
                f"🟢 Strong Hold ({sh_cnt})",
                f"🟡 Profit Trim ({pt_cnt})",
                f"🟢 Accumulate ({acc_cnt})",
                f"🟠 Monitor ({mon_cnt})",
                f"🔴 Risk Cut ({cut_cnt})"
            ]

            # If current var not in chip_vals, default to All
            cur_v = self.decision_filter_var.get()
            if not any(cur_v in cv for cv in chip_vals):
                self.decision_filter_var.set(chip_vals[0])

            self.decision_seg_btn = ctk.CTkSegmentedButton(
                self.exec_action_frame,
                values=chip_vals,
                variable=self.decision_filter_var,
                font=ctk.CTkFont(size=10, weight="bold"),
                selected_color="#2E7D32",
                command=self._on_decision_filter_chip_changed
            )
            self.decision_seg_btn.pack(side="left", padx=5, pady=4)

        elif "Reconciliation" in seg_mode:
            # 1-Click Action Buttons for Data Disputes
            ctk.CTkLabel(self.exec_action_frame, text="⚡ 1-Click Resolution Hub:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#FF5252").pack(side="left", padx=(10, 8), pady=4)

            ctk.CTkButton(
                self.exec_action_frame, text="⚡ Auto-Resolve Demat Disputes (Pre-Log Buys)",
                height=26, fg_color="#D32F2F", hover_color="#B71C1C", font=ctk.CTkFont(size=11, weight="bold"),
                command=self._run_auto_resolve_equity
            ).pack(side="left", padx=5, pady=4)

            ctk.CTkButton(
                self.exec_action_frame, text="🔄 Auto-Square Off Expired Derivatives",
                height=26, fg_color="#C2185B", hover_color="#880E4F", font=ctk.CTkFont(size=11, weight="bold"),
                command=self._run_auto_square_off_derivatives
            ).pack(side="left", padx=5, pady=4)

            ctk.CTkButton(
                self.exec_action_frame, text="↩️ Undo Reconciliations",
                height=26, fg_color="#424242", hover_color="#616161", font=ctk.CTkFont(size=11),
                command=self._run_undo_auto_resolve
            ).pack(side="left", padx=5, pady=4)

            ctk.CTkButton(
                self.exec_action_frame, text="📋 Reconciliation Guide",
                height=26, fg_color="#1E88E5", hover_color="#1565C0", font=ctk.CTkFont(size=11, weight="bold"),
                command=self._open_reconciliation_guide
            ).pack(side="right", padx=10, pady=4)

        else:
            # FnO or Commodity Guidance
            ctk.CTkLabel(
                self.exec_action_frame,
                text="⚡ Institutional Risk Management: Monitor Days to Expiry (DTE) closely. Roll over contracts with DTE <= 2 to avoid exchange settlement & physical delivery margin calls.",
                font=ctk.CTkFont(size=11, weight="bold"), text_color="#00E5FF"
            ).pack(side="left", padx=10, pady=6)

    def _populate_open_trades_sheet(self):
        df_all = self.open_trades_df
        if df_all.empty:
            self.open_sheet.set_sheet_data([[]])
            self.open_summary_lbl.configure(text="0 Holdings Found")
            self._current_holdings_display_df = pd.DataFrame()
            return

        seg_tab = self.holding_segment_var.get()

        # 1. Filter by Segment View
        if "Active Equity" in seg_tab:
            base_df = df_all[(df_all['Segment'] == 'Equity') & (df_all['HoldingStatus'] == 'VERIFIED_HOLDING')].copy()
            active_headers = self.equity_headers
        elif "Active FnO" in seg_tab:
            base_df = df_all[(df_all['Segment'] == 'FnO') & (df_all['HoldingStatus'] == 'ACTIVE_DERIVATIVE')].copy()
            active_headers = self.fno_headers
        elif "Active Commodity" in seg_tab:
            base_df = df_all[(df_all['Segment'] == 'Commodity') & (df_all['HoldingStatus'] == 'ACTIVE_DERIVATIVE')].copy()
            active_headers = self.commodity_headers
        else:
            # Data Reconciliation Hub (Dispute Data)
            base_df = df_all[df_all['HoldingStatus'] == 'DISPUTE_DATA'].copy()
            active_headers = self.reconciliation_headers

        # 2. Render Action / Filter Ribbon
        self._render_decision_actions_ribbon(seg_tab, base_df)

        # 3. Apply Decision Filter if on Active Equity
        disp_df = base_df.copy()
        if "Active Equity" in seg_tab:
            dec_chip = self.decision_filter_var.get()
            if "Strong Hold" in dec_chip:
                disp_df = disp_df[disp_df['DecisionVerdict'].str.contains('STRONG HOLD', na=False)]
            elif "Profit Trim" in dec_chip:
                disp_df = disp_df[disp_df['DecisionVerdict'].str.contains('PROFIT TRIM', na=False)]
            elif "Accumulate" in dec_chip:
                disp_df = disp_df[disp_df['DecisionVerdict'].str.contains('ACCUMULATE', na=False)]
            elif "Monitor" in dec_chip:
                disp_df = disp_df[disp_df['DecisionVerdict'].str.contains('MONITOR', na=False)]
            elif "Risk Cut" in dec_chip:
                disp_df = disp_df[disp_df['DecisionVerdict'].str.contains('RISK CUT', na=False)]

        self._current_holdings_display_df = disp_df.reset_index(drop=True)

        # 4. Update the 4 Executive KPI Cards based on Active Segment
        verified_eq = df_all[(df_all['Segment'] == 'Equity') & (df_all['HoldingStatus'] == 'VERIFIED_HOLDING')]
        active_fno = df_all[(df_all['Segment'] == 'FnO') & (df_all['HoldingStatus'] == 'ACTIVE_DERIVATIVE')]
        active_comm = df_all[(df_all['Segment'] == 'Commodity') & (df_all['HoldingStatus'] == 'ACTIVE_DERIVATIVE')]
        disputes = df_all[df_all['HoldingStatus'] == 'DISPUTE_DATA']

        tot_demat_cap = verified_eq['CommittedValue'].sum() if not verified_eq.empty else 0.0
        tot_market_val = verified_eq['CurrentMarketValue'].sum() if not verified_eq.empty else 0.0
        tot_unreal_pnl = verified_eq['UnrealizedPnL'].sum() if not verified_eq.empty else 0.0
        tot_unreal_roi = (tot_unreal_pnl / tot_demat_cap * 100) if tot_demat_cap > 0 else 0.0

        if "Active Equity" in seg_tab:
            # Top 3 Gainers
            top_gainers_str = "None"
            if not verified_eq.empty:
                top_3 = verified_eq.sort_values(by='UnrealizedPnL', ascending=False).head(3)
                parts = []
                for idx_t, r_t in top_3.iterrows():
                    parts.append(f"{r_t['Symbol']} ({r_t['UnrealizedROIPct']:+.1f}%)")
                top_gainers_str = " | ".join(parts)

            self.holding_kpis["card_1"][0].configure(text=f"Rs. {tot_demat_cap:,.2f}")
            self.holding_kpis["card_1"][1].configure(text=f"{len(verified_eq)} Delivery Stocks Held Across Brokers")

            self.holding_kpis["card_2"][0].configure(text=f"Rs. {tot_market_val:,.2f}")
            pnl_sign = "+" if tot_unreal_pnl >= 0 else ""
            pnl_col = "#00E676" if tot_unreal_pnl >= 0 else "#FF5252"
            self.holding_kpis["card_2"][1].configure(
                text=f"Unrealized P&L: {pnl_sign}Rs. {tot_unreal_pnl:,.2f} ({tot_unreal_roi:+.1f}%)",
                text_color=pnl_col
            )

            self.holding_kpis["card_3"][0].configure(text=top_gainers_str)
            self.holding_kpis["card_3"][1].configure(text="Top Wealth Compounders in Portfolio")

            self.holding_kpis["card_4"][0].configure(text="🟢 Live Quotes Active")
            self.holding_kpis["card_4"][1].configure(text="Real-Time LTP Quotes Cached (Yahoo/NSE)")

            self.open_summary_lbl.configure(
                text=f"Showing {len(disp_df)} of {len(verified_eq)} Verified Demat Stocks | Mkt Val: Rs. {tot_market_val:,.2f}"
            )

        elif "Active FnO" in seg_tab:
            fno_cap = active_fno['CommittedValue'].sum() if not active_fno.empty else 0.0
            fno_symbols = ", ".join(list(active_fno['Symbol'].unique())) if not active_fno.empty else "None"
            min_dte = active_fno['DTE'].min() if not active_fno.empty else "N/A"

            self.holding_kpis["card_1"][0].configure(text=f"{len(active_fno)} Open Contracts")
            self.holding_kpis["card_1"][1].configure(text=f"Active Symbols: {fno_symbols}")

            self.holding_kpis["card_2"][0].configure(text=f"Rs. {fno_cap:,.2f}")
            self.holding_kpis["card_2"][1].configure(text="Committed Derivative Capital", text_color="#64B5F6")

            self.holding_kpis["card_3"][0].configure(text=f"Min DTE: {min_dte} Days")
            self.holding_kpis["card_3"][1].configure(text="🚨 Rollover Warning if DTE <= 2")

            self.holding_kpis["card_4"][0].configure(text="⚡ F&O Carry Forward")
            self.holding_kpis["card_4"][1].configure(text="Strict Stoploss Recommended")

            self.open_summary_lbl.configure(
                text=f"Showing {len(disp_df)} Active F&O Carry Forward Contracts | Committed: Rs. {fno_cap:,.2f}"
            )

        elif "Active Commodity" in seg_tab:
            comm_cap = active_comm['CommittedValue'].sum() if not active_comm.empty else 0.0
            self.holding_kpis["card_1"][0].configure(text=f"{len(active_comm)} Open Contracts")
            self.holding_kpis["card_1"][1].configure(text="Active MCX Commodity Positions")

            self.holding_kpis["card_2"][0].configure(text=f"Rs. {comm_cap:,.2f}")
            self.holding_kpis["card_2"][1].configure(text="Committed Commodity Margin", text_color="#64B5F6")

            self.holding_kpis["card_3"][0].configure(text="0 Tender Risks")
            self.holding_kpis["card_3"][1].configure(text="MCX Delivery Risk Clean")

            self.holding_kpis["card_4"][0].configure(text="🪙 Commodity Desk")
            self.holding_kpis["card_4"][1].configure(text="Active Positions Monitored")

            self.open_summary_lbl.configure(
                text=f"Showing {len(disp_df)} Active Commodity Positions | Committed: Rs. {comm_cap:,.2f}"
            )

        else:
            # Data Reconciliation Hub
            eq_disp_cnt = len(disputes[disputes['Segment'] == 'Equity'])
            fno_disp_cnt = len(disputes[disputes['Segment'].isin(['FnO', 'Commodity'])])

            self.holding_kpis["card_1"][0].configure(text=f"{len(disputes)} Total Disputes")
            self.holding_kpis["card_1"][1].configure(text="Positions Awaiting Historical Inception / Expiry Balance")

            self.holding_kpis["card_2"][0].configure(text=f"{eq_disp_cnt} Pre-Log Demat Sells")
            self.holding_kpis["card_2"][1].configure(text="Click '⚡ Auto-Resolve Demat Disputes'", text_color="#FFA726")

            self.holding_kpis["card_3"][0].configure(text=f"{fno_disp_cnt} Expired Contracts")
            self.holding_kpis["card_3"][1].configure(text="Click '🔄 Auto-Square Off Expired'")

            self.holding_kpis["card_4"][0].configure(text="🛠️ 2 Automated Fixes Ready")
            self.holding_kpis["card_4"][1].configure(text="Reconciles to 0 Discrepancies Instantly")

            self.open_summary_lbl.configure(
                text=f"Dispute Resolution Hub: {len(disp_df)} Unreconciled Items ({eq_disp_cnt} Pre-Log Sells, {fno_disp_cnt} Expired F&O)"
            )

        # 5. Populate Sheet Rows with Proper Headers
        self.open_sheet.headers(active_headers)

        rows = []
        for _, r in disp_df.iterrows():
            stat_disp = str(r.get('HoldingStatusDisplay', '✅ VERIFIED HOLDING'))
            broker = str(r.get('Broker', ''))
            seg = str(r.get('Segment', ''))
            sym = str(r.get('Symbol', ''))
            cname = str(r.get('ContractName', ''))
            net_q = float(r.get('NetQty', 0.0))
            entry_p = float(r.get('AvgEntryPrice', 0.0))
            c_val = float(r.get('CommittedValue', 0.0))
            ltp = float(r.get('LTP', entry_p))
            day_chg = float(r.get('DayChangePct', 0.0))
            m_val = float(r.get('CurrentMarketValue', c_val))
            pnl = float(r.get('UnrealizedPnL', 0.0))
            roi = float(r.get('UnrealizedROIPct', 0.0))
            verdict = str(r.get('DecisionVerdict', '🟢 STRONG HOLD'))
            advice = str(r.get('DecisionAdvice') or r.get('ReconciliationAdvice', ''))
            trailing_sl = r.get('TrailingStoploss')
            sl_str = f"Rs. {trailing_sl:,.2f}" if (trailing_sl is not None and pd.notna(trailing_sl)) else "—"
            days_held = f"{r.get('DaysOpen', 0)} days"
            dte = r.get('DTE')
            dte_disp = f"{dte}d" if dte is not None else "—"
            exp_date = str(r.get('ExpiryDate') or 'N/A')
            stance = str(r.get('Stance', 'LONG'))

            if "Active Equity" in seg_tab:
                rows.append([
                    stat_disp, broker, sym, cname, f"{net_q:,.0f}", f"Rs. {entry_p:,.2f}",
                    f"Rs. {c_val:,.2f}", f"Rs. {ltp:,.2f}", f"{day_chg:+.2f}%", f"Rs. {m_val:,.2f}",
                    f"{'+' if pnl>=0 else ''}Rs. {pnl:,.2f}", f"{roi:+.2f}%", verdict, sl_str,
                    advice, days_held
                ])
            elif "Active FnO" in seg_tab:
                rows.append([
                    stat_disp, broker, sym, cname, str(r.get('OptionType', 'N/A')),
                    str(r.get('StrikePrice') or 'N/A'), exp_date, dte_disp, stance,
                    f"{net_q:,.0f}", f"Rs. {entry_p:,.2f}", f"Rs. {c_val:,.2f}",
                    f"Rs. {ltp:,.2f}", f"Rs. {m_val:,.2f}", f"{'+' if pnl>=0 else ''}Rs. {pnl:,.2f}",
                    f"{roi:+.2f}%", verdict, advice, days_held
                ])
            elif "Active Commodity" in seg_tab:
                rows.append([
                    stat_disp, broker, sym, cname, exp_date, dte_disp, stance,
                    f"{net_q:,.0f}", f"Rs. {entry_p:,.2f}", f"Rs. {c_val:,.2f}",
                    f"Rs. {ltp:,.2f}", f"{'+' if pnl>=0 else ''}Rs. {pnl:,.2f}", f"{roi:+.2f}%",
                    verdict, advice
                ])
            else:
                # Reconciliation Hub
                d_type = "Pre-Log Delivery Sell" if seg == 'Equity' else f"Expired Contract ({exp_date})"
                d_diag = str(r.get('DisputeReason', ''))
                rows.append([
                    d_type, broker, seg, sym, cname, f"{abs(net_q):,.0f}",
                    f"Rs. {entry_p:,.2f}", f"Rs. {c_val:,.2f}", d_diag, days_held,
                    advice
                ])

        self.open_sheet.set_sheet_data(rows)

        # 6. High-Precision Cell Highlights
        try:
            for idx, r in enumerate(disp_df.itertuples()):
                h_stat = getattr(r, 'HoldingStatus', '')
                pnl_v = getattr(r, 'UnrealizedPnL', 0.0)
                v_badge = getattr(r, 'DecisionVerdict', '')

                if "Active Equity" in seg_tab:
                    # Column 7: LTP -> Vibrant Cyan
                    self.open_sheet.highlight_cells(row=idx, column=7, fg="#00E5FF")
                    # Column 8: Day Change %
                    chg_v = getattr(r, 'DayChangePct', 0.0)
                    if chg_v > 0:
                        self.open_sheet.highlight_cells(row=idx, column=8, fg="#00E676")
                    elif chg_v < 0:
                        self.open_sheet.highlight_cells(row=idx, column=8, fg="#FF5252")
                    # Column 10 & 11: Unrealized P&L & ROI
                    if pnl_v > 0:
                        self.open_sheet.highlight_cells(row=idx, column=10, fg="#00E676")
                        self.open_sheet.highlight_cells(row=idx, column=11, fg="#00E676")
                    elif pnl_v < 0:
                        self.open_sheet.highlight_cells(row=idx, column=10, fg="#FF5252")
                        self.open_sheet.highlight_cells(row=idx, column=11, fg="#FF5252")
                    # Column 12: Decision Verdict badge
                    if "STRONG HOLD" in v_badge or "ACCUMULATE" in v_badge:
                        self.open_sheet.highlight_cells(row=idx, column=12, fg="#00E676")
                    elif "PROFIT TRIM" in v_badge:
                        self.open_sheet.highlight_cells(row=idx, column=12, fg="#FFD600")
                    elif "MONITOR" in v_badge:
                        self.open_sheet.highlight_cells(row=idx, column=12, fg="#FF9100")
                    elif "RISK CUT" in v_badge:
                        self.open_sheet.highlight_cells(row=idx, column=12, fg="#FF5252")

                elif "Active FnO" in seg_tab:
                    self.open_sheet.highlight_cells(row=idx, column=0, fg="#00E5FF")
                    self.open_sheet.highlight_cells(row=idx, column=12, fg="#00E5FF")
                    dte_v = getattr(r, 'DTE', None)
                    if dte_v is not None and dte_v <= 2:
                        self.open_sheet.highlight_cells(row=idx, column=7, fg="#FF5252")
                        self.open_sheet.highlight_cells(row=idx, column=16, fg="#FF5252")

                elif "Reconciliation" in seg_tab:
                    self.open_sheet.highlight_cells(row=idx, column=0, fg="#FFA726")
                    self.open_sheet.highlight_cells(row=idx, column=5, fg="#FF5252")
                    self.open_sheet.highlight_cells(row=idx, column=10, fg="#64B5F6")
        except:
            pass

    # -------------------------------------------------------------
    # TAB 3: EXECUTION & FILL ANALYTICS
    # -------------------------------------------------------------
    def _build_analytics_tab(self):
        parent = self.tab_analytics
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        self.analytics_container = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.analytics_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _render_analytics(self):
        for w in self.analytics_container.winfo_children(): w.destroy()
        df = self.filtered_orders_df
        if df.empty:
            ctk.CTkLabel(self.analytics_container, text="No orders data available for selected filters.", font=ctk.CTkFont(size=14)).pack(pady=40)
            return

        tot_orders = len(df)
        exec_orders = len(df[df['OrderStatus'] == 'EXECUTED'])
        cancel_orders = len(df[df['OrderStatus'] == 'CANCELLED'])
        reject_orders = len(df[df['OrderStatus'] == 'REJECTED'])
        fill_pct = (exec_orders / tot_orders * 100) if tot_orders > 0 else 0.0

        exec_df = df[df['OrderStatus'] == 'EXECUTED']
        tot_turnover = (exec_df['ExecutedQty'] * exec_df['ExecutionPrice']).sum()

        top_kpi = ctk.CTkFrame(self.analytics_container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        top_kpi.pack(fill="x", pady=(0, 15))
        top_kpi.columnconfigure((0, 1, 2, 3), weight=1)

        stat_cards = [
            ("Execution Fill Rate", f"{fill_pct:.1f}%", "#00E676", f"{exec_orders:,} of {tot_orders:,} orders"),
            ("Cancellation Rate", f"{(cancel_orders/tot_orders*100):.1f}%", "#FFA726", f"{cancel_orders:,} cancelled"),
            ("Rejection Rate", f"{(reject_orders/tot_orders*100):.1f}%", "#FF5252", f"{reject_orders:,} rejected"),
            ("Total Executed Volume", f"Rs. {tot_turnover:,.2f}", "#64B5F6", f"Avg Rs. {(tot_turnover/exec_orders if exec_orders > 0 else 0):,.2f}/order")
        ]

        for i, (t, val, col, sub) in enumerate(stat_cards):
            cell = ctk.CTkFrame(top_kpi, fg_color="transparent")
            cell.grid(row=0, column=i, padx=15, pady=10, sticky="w")
            ctk.CTkLabel(cell, text=t, font=ctk.CTkFont(size=11, weight="bold"), text_color="#888888").pack(anchor="w")
            ctk.CTkLabel(cell, text=val, font=ctk.CTkFont(size=18, weight="bold"), text_color=col).pack(anchor="w")
            ctk.CTkLabel(cell, text=sub, font=ctk.CTkFont(size=10), text_color="#757575").pack(anchor="w")

        chart_box = ctk.CTkFrame(self.analytics_container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        chart_box.pack(fill="both", expand=True, pady=(0, 15))

        fig = Figure(figsize=(10, 6), dpi=100, facecolor="#181818")
        ax1 = fig.add_subplot(221, facecolor="#181818")
        status_counts = df['OrderStatus'].value_counts()
        colors = ['#00E676', '#FFA726', '#FF5252', '#78909C', '#AB47BC']
        ax1.pie(status_counts, labels=status_counts.index, autopct='%1.1f%%',
                colors=colors[:len(status_counts)], textprops={'color': '#FFFFFF', 'fontsize': 8},
                startangle=140, wedgeprops={'edgecolor': '#181818', 'linewidth': 1.5})
        ax1.set_title("Order Status Breakdown", color="#FFFFFF", fontsize=10, fontweight="bold")

        ax2 = fig.add_subplot(222, facecolor="#181818")
        exec_df_c = exec_df.copy()
        exec_df_c['TurnoverLakhs'] = (exec_df_c['ExecutedQty'] * exec_df_c['ExecutionPrice']) / 1e5
        broker_to = exec_df_c.groupby('Broker')['TurnoverLakhs'].sum().sort_values(ascending=False)
        bars = ax2.bar(broker_to.index, broker_to.values, color='#1E88E5', edgecolor='#1565C0')
        ax2.set_title("Turnover by Broker (Rs. Lakhs)", color="#FFFFFF", fontsize=10, fontweight="bold")
        ax2.tick_params(colors='#FFFFFF', labelsize=8)
        ax2.set_ylabel("Turnover (Rs. L)", color='#FFFFFF', fontsize=8)
        for spine in ax2.spines.values(): spine.set_color('#333333')

        ax3 = fig.add_subplot(223, facecolor="#181818")
        type_counts = df['OrderType'].value_counts()
        ax3.bar(type_counts.index, type_counts.values, color='#26A69A', edgecolor='#00897B')
        ax3.set_title("Orders by Type (Limit vs Market)", color="#FFFFFF", fontsize=10, fontweight="bold")
        ax3.tick_params(colors='#FFFFFF', labelsize=8)
        ax3.set_ylabel("Order Count", color='#FFFFFF', fontsize=8)
        for spine in ax3.spines.values(): spine.set_color('#333333')

        ax4 = fig.add_subplot(224, facecolor="#181818")
        seg_counts = df['Segment'].value_counts()
        ax4.bar(seg_counts.index, seg_counts.values, color='#AB47BC', edgecolor='#8E24AA')
        ax4.set_title("Orders by Market Segment", color="#FFFFFF", fontsize=10, fontweight="bold")
        ax4.tick_params(colors='#FFFFFF', labelsize=8)
        ax4.set_ylabel("Order Count", color='#FFFFFF', fontsize=8)
        for spine in ax4.spines.values(): spine.set_color('#333333')

        fig.tight_layout(pad=2.0)
        canvas = FigureCanvasTkAgg(fig, master=chart_box)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

    # -------------------------------------------------------------
    # TAB 4: TIME-OF-DAY ORDER FLOW
    # -------------------------------------------------------------
    def _build_flow_tab(self):
        parent = self.tab_flow
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        self.flow_container = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.flow_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _render_flow(self):
        for w in self.flow_container.winfo_children(): w.destroy()
        df = self.filtered_orders_df
        if df.empty or 'OrderTime' not in df.columns:
            ctk.CTkLabel(self.flow_container, text="No order time data available.", font=ctk.CTkFont(size=14)).pack(pady=40)
            return

        df_time = df.copy()
        df_time['Hour'] = pd.to_datetime(df_time['OrderTime'], format='%H:%M:%S', errors='coerce').dt.hour
        df_time = df_time.dropna(subset=['Hour'])
        df_time['Hour'] = df_time['Hour'].astype(int)
        hourly_counts = df_time['Hour'].value_counts().sort_index()

        chart_box = ctk.CTkFrame(self.flow_container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        chart_box.pack(fill="both", expand=True, pady=(0, 15))

        fig = Figure(figsize=(10, 4.5), dpi=100, facecolor="#181818")
        ax = fig.add_subplot(111, facecolor="#181818")

        hours_labels = [f"{h:02d}:00" for h in hourly_counts.index]
        ax.bar(hours_labels, hourly_counts.values, color='#00E676', alpha=0.85, edgecolor='#00B0FF', width=0.55)
        ax.set_title("Intraday Order Placement Volume by Hour (IST)", color="#FFFFFF", fontsize=11, fontweight="bold")
        ax.set_xlabel("Trading Hour", color="#FFFFFF", fontsize=9)
        ax.set_ylabel("Number of Orders", color="#FFFFFF", fontsize=9)
        ax.tick_params(colors='#FFFFFF', labelsize=8)
        for spine in ax.spines.values(): spine.set_color('#333333')

        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=chart_box)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)

        tbl_box = ctk.CTkFrame(self.flow_container, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        tbl_box.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(tbl_box, text="⚡ Market Session Flow Breakdown", font=ctk.CTkFont(size=13, weight="bold"), text_color="#64B5F6").pack(anchor="w", padx=15, pady=(10, 5))

        phases = [
            ("🌅 Market Open Rush (09:15 - 10:30)", df_time[(df_time['Hour'] == 9) | ((df_time['Hour'] == 10))]),
            ("☕ Mid-Session & Trend Consolidation (10:30 - 13:30)", df_time[(df_time['Hour'] >= 11) & (df_time['Hour'] <= 13)]),
            ("🚀 Closing Rush & Expiry Squaring (13:30 - 15:30)", df_time[(df_time['Hour'] >= 14) & (df_time['Hour'] <= 15)])
        ]

        grid = ctk.CTkFrame(tbl_box, fg_color="transparent")
        grid.pack(fill="x", padx=15, pady=(0, 10))
        grid.columnconfigure((0, 1, 2), weight=1)

        for i, (name, subset) in enumerate(phases):
            card = ctk.CTkFrame(grid, fg_color="#222222", corner_radius=8)
            card.grid(row=0, column=i, padx=5, sticky="nsew")

            ctk.CTkLabel(card, text=name, font=ctk.CTkFont(size=11, weight="bold"), text_color="#FFB74D").pack(anchor="w", padx=10, pady=(8, 2))
            ctk.CTkLabel(card, text=f"{len(subset):,} Orders", font=ctk.CTkFont(size=16, weight="bold"), text_color="#FFFFFF").pack(anchor="w", padx=10, pady=(0, 2))
            
            exec_sub = subset[subset['OrderStatus'] == 'EXECUTED']
            sub_fill = (len(exec_sub) / len(subset) * 100) if len(subset) > 0 else 0.0
            ctk.CTkLabel(card, text=f"Fill Rate: {sub_fill:.1f}% | Executed: {len(exec_sub):,}", font=ctk.CTkFont(size=10), text_color="#9E9E9E").pack(anchor="w", padx=10, pady=(0, 8))

    # -------------------------------------------------------------
    # TAB 5: BROKER BENCHMARK
    # -------------------------------------------------------------
    def _build_brokers_tab(self):
        parent = self.tab_brokers
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(0, weight=1)
        self.brokers_container = ctk.CTkScrollableFrame(parent, fg_color="transparent")
        self.brokers_container.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

    def _render_brokers(self):
        for w in self.brokers_container.winfo_children(): w.destroy()
        df = self.filtered_orders_df
        if df.empty:
            ctk.CTkLabel(self.brokers_container, text="No broker data available.", font=ctk.CTkFont(size=14)).pack(pady=40)
            return

        brokers = df['Broker'].unique()
        cards_grid = ctk.CTkFrame(self.brokers_container, fg_color="transparent")
        cards_grid.pack(fill="x", pady=(0, 15))
        cards_grid.columnconfigure(tuple(range(len(brokers))), weight=1)

        for idx, b in enumerate(sorted(brokers)):
            b_df = df[df['Broker'] == b]
            tot = len(b_df)
            exec_cnt = len(b_df[b_df['OrderStatus'] == 'EXECUTED'])
            cancel_cnt = len(b_df[b_df['OrderStatus'] == 'CANCELLED'])
            reject_cnt = len(b_df[b_df['OrderStatus'] == 'REJECTED'])
            fill = (exec_cnt / tot * 100) if tot > 0 else 0.0

            b_exec = b_df[b_df['OrderStatus'] == 'EXECUTED']
            b_to = (b_exec['ExecutedQty'] * b_exec['ExecutionPrice']).sum()

            card = ctk.CTkFrame(cards_grid, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
            card.grid(row=0, column=idx, padx=6, sticky="nsew")

            ctk.CTkLabel(card, text=b, font=ctk.CTkFont(size=15, weight="bold"), text_color="#64B5F6").pack(anchor="w", padx=12, pady=(10, 4))
            ctk.CTkLabel(card, text=f"Total Orders: {tot:,}", font=ctk.CTkFont(size=12), text_color="#FFFFFF").pack(anchor="w", padx=12, pady=1)
            ctk.CTkLabel(card, text=f"Fill Rate: {fill:.1f}% ({exec_cnt:,} Executed)", font=ctk.CTkFont(size=12, weight="bold"), text_color="#00E676").pack(anchor="w", padx=12, pady=1)
            ctk.CTkLabel(card, text=f"Cancelled / Rejected: {cancel_cnt + reject_cnt:,}", font=ctk.CTkFont(size=11), text_color="#FFA726").pack(anchor="w", padx=12, pady=1)
            ctk.CTkLabel(card, text=f"Turnover: Rs. {b_to:,.2f}", font=ctk.CTkFont(size=12, weight="bold"), text_color="#CE93D8").pack(anchor="w", padx=12, pady=(1, 10))

    # -------------------------------------------------------------
    # TAB 6: SYNC & INGESTION HUB
    # -------------------------------------------------------------
    def _build_sync_tab(self):
        parent = self.tab_sync
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(parent, fg_color="#181818", corner_radius=10, border_width=1, border_color="#2D2D2D")
        top_bar.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 10))

        ctk.CTkLabel(top_bar, text="📁 Source Directory:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#9E9E9E").grid(row=0, column=0, padx=15, pady=(10, 2), sticky="w")
        self.src_path_lbl = ctk.CTkLabel(top_bar, text=trade_orders_engine.DEFAULT_ORDER_LOG_DIR, font=ctk.CTkFont(size=11), text_color="#64B5F6")
        self.src_path_lbl.grid(row=0, column=1, padx=5, pady=(10, 2), sticky="w")

        ctk.CTkLabel(top_bar, text="📦 Archive / Backup Directory:", font=ctk.CTkFont(size=11, weight="bold"), text_color="#9E9E9E").grid(row=1, column=0, padx=15, pady=(2, 10), sticky="w")
        self.bak_path_lbl = ctk.CTkLabel(top_bar, text=trade_orders_engine.BACKUP_DIR, font=ctk.CTkFont(size=11), text_color="#CE93D8")
        self.bak_path_lbl.grid(row=1, column=1, padx=5, pady=(2, 10), sticky="w")

        btn_row = ctk.CTkFrame(top_bar, fg_color="transparent")
        btn_row.grid(row=2, column=0, columnspan=2, padx=15, pady=(0, 12), sticky="w")

        ctk.CTkButton(btn_row, text="⚡ Ingest & Sync New Files Now", width=220, height=32, fg_color="#1E88E5", hover_color="#1565C0",
                      font=ctk.CTkFont(size=12, weight="bold"), command=self._trigger_sync_folder).pack(side="left", padx=(0, 8))

        ctk.CTkButton(btn_row, text="📁 Open Source Folder", width=160, height=32, fg_color="#333333", hover_color="#444444",
                      font=ctk.CTkFont(size=12), command=lambda: os.startfile(trade_orders_engine.DEFAULT_ORDER_LOG_DIR)).pack(side="left", padx=4)

        ctk.CTkButton(btn_row, text="📁 Open Backup Folder", width=160, height=32, fg_color="#333333", hover_color="#444444",
                      font=ctk.CTkFont(size=12), command=lambda: os.startfile(trade_orders_engine.BACKUP_DIR)).pack(side="left", padx=4)

        log_box = ctk.CTkFrame(parent, fg_color="#121212", corner_radius=10, border_width=1, border_color="#2D2D2D")
        log_box.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        log_box.grid_columnconfigure(0, weight=1)
        log_box.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(log_box, text="📜 Real-Time Ingestion & Audit Stream", font=ctk.CTkFont(size=12, weight="bold"), text_color="#FFA726").grid(row=0, column=0, padx=15, pady=(10, 5), sticky="w")

        self.sync_textbox = ctk.CTkTextbox(log_box, font=ctk.CTkFont(family="Consolas", size=11), fg_color="#0A0A0A", text_color="#00E676")
        self.sync_textbox.grid(row=1, column=0, sticky="nsew", padx=15, pady=(0, 15))

    def _update_sync_tab_status(self):
        try:
            p_files = len([f for f in os.listdir(trade_orders_engine.DEFAULT_ORDER_LOG_DIR) if f.endswith(('.xlsx', '.xls', '.csv')) and not f.startswith('~$')])
            self.log_sync_msg(f"Status Checked: {p_files} files currently in Order Log folder. Total DB records: {len(self.full_orders_df):,}")
        except: pass

    def log_sync_msg(self, msg):
        self.sync_textbox.insert("end", f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
        self.sync_textbox.see("end")

    # -------------------------------------------------------------
    # 5. DATA INGESTION & FILTER APPLICATION
    # -------------------------------------------------------------
    def load_data(self):
        """Loads data from TradeOrders_Master and populates UI."""
        try:
            filts = trade_orders_engine.get_distinct_filter_values()
            orders_df = trade_orders_engine.fetch_orders_data()
            matched_df = trade_orders_engine.match_orders_to_trades()
            open_df = trade_orders_engine.compute_open_positions()
            self._on_data_loaded(filts, orders_df, matched_df, open_df)
        except Exception as e:
            print(f"Error loading trade orders data: {e}")

    def _on_data_loaded(self, filts, orders_df, matched_df, open_df):
        self.distinct_meta = filts
        self.full_orders_df = orders_df
        self.matched_trades_df = matched_df
        self.open_trades_df = open_df

        self.last_sync_lbl.configure(text=f"Last Sync: {datetime.now().strftime('%d-%b %H:%M')}")

        fy_vals = self.distinct_meta.get('financial_years', ["All FYs"])
        self.fy_menu.configure(values=fy_vals)
        self._update_expiry_options(self.f_fy.get())

        if not orders_df.empty:
            top_syms = ["All Symbols"] + list(orders_df['Symbol'].value_counts().head(40).index)
            self.sym_select_menu.configure(values=top_syms)

        self.apply_filters()

    def apply_filters(self):
        mode = self.f_trade_status.get()

        # 1. Synchronize Current Holdings DataFrame across Segments, Broker, Symbol
        as_of = self.as_of_var.get().strip() if (hasattr(self, 'open_mode_var') and "Specific Date" in self.open_mode_var.get()) else None
        filts_holdings = {
            'broker': self.f_broker.get(),
            'segment': self.f_segment.get(),
            'symbol': self.f_sym.get().strip()
        }
        if "Verified Holdings" in mode:
            filts_holdings['holding_filter'] = 'VERIFIED'
        elif "Dispute Data" in mode:
            filts_holdings['holding_filter'] = 'DISPUTE'

        self.open_trades_df = trade_orders_engine.compute_open_positions(as_of_date=as_of, filters=filts_holdings)

        # 2. Filter Raw Orders (for Analytics, Benchmark, Flow tabs or Raw Order view)
        df_ord = self.full_orders_df.copy() if not self.full_orders_df.empty else pd.DataFrame()
        if not df_ord.empty:
            fy = self.f_fy.get()
            if fy and fy != "All FYs": df_ord = df_ord[df_ord['FinancialYear'] == fy]
            b = self.f_broker.get()
            if b and b != "All Brokers": df_ord = df_ord[df_ord['Broker'] == b]
            s = self.f_segment.get()
            if s and s != "All Segments": df_ord = df_ord[df_ord['Segment'] == s]
            if hasattr(self, 'f_status'):
                st = self.f_status.get()
                if st and st != "All Statuses" and st != "All": df_ord = df_ord[df_ord['OrderStatus'] == st]
            otyp = self.f_type.get()
            if otyp and otyp != "All Types": df_ord = df_ord[df_ord['OrderType'] == otyp]
            p = self.f_product.get()
            if p and p != "All Products": df_ord = df_ord[df_ord['Product'] == p]
            sym = self.f_sym.get().strip()
            if sym:
                df_ord = df_ord[df_ord['Symbol'].astype(str).str.contains(sym, case=False, na=False) |
                                df_ord['ContractName'].astype(str).str.contains(sym, case=False, na=False)]
            d_from = self.f_date_from.get().strip()
            if d_from:
                try: df_ord = df_ord[pd.to_datetime(df_ord['OrderDate']) >= pd.to_datetime(d_from)]
                except: pass
            d_to = self.f_date_to.get().strip()
            if d_to:
                try: df_ord = df_ord[pd.to_datetime(df_ord['OrderDate']) <= pd.to_datetime(d_to)]
                except: pass
            exp_disp = self.f_expiry.get()
            if exp_disp and exp_disp != "All Expiries":
                raw_exp = self.expiry_map.get(exp_disp)
                if raw_exp: df_ord = df_ord[df_ord['ExpiryDate'].astype(str) == raw_exp]

        self.filtered_orders_df = df_ord

        # 3. Filter Matched Trades (for My Trade Log tab)
        df_trd = self.matched_trades_df.copy() if not self.matched_trades_df.empty else pd.DataFrame()
        if not df_trd.empty:
            if "Current Holdings" in mode or "Open Trades Only" in mode:
                df_trd = df_trd[df_trd['Status'] == 'OPEN']
            elif "Verified Holdings" in mode:
                if 'HoldingStatus' in df_trd.columns:
                    df_trd = df_trd[(df_trd['Status'] == 'OPEN') & (df_trd['HoldingStatus'].isin(['VERIFIED_HOLDING', 'ACTIVE_DERIVATIVE']))]
                else:
                    df_trd = df_trd[df_trd['Status'] == 'OPEN']
            elif "Dispute Data" in mode:
                if 'HoldingStatus' in df_trd.columns:
                    df_trd = df_trd[(df_trd['Status'] == 'OPEN') & (df_trd['HoldingStatus'] == 'DISPUTE_DATA')]
                else:
                    df_trd = df_trd[df_trd['Status'] == 'OPEN']
            elif "Closed Trades Only" in mode:
                df_trd = df_trd[df_trd['Status'] == 'CLOSED']

            # Stance filter
            act = self.f_action.get()
            if act and act != "All":
                df_trd = df_trd[df_trd['Stance'] == act]

            # FY filter
            fy = self.f_fy.get()
            if fy and fy != "All FYs":
                df_trd = df_trd[df_trd['FinancialYear'] == fy]

            # Broker filter
            b = self.f_broker.get()
            if b and b != "All Brokers":
                df_trd = df_trd[df_trd['Broker'] == b]

            # Segment filter
            s = self.f_segment.get()
            if s and s != "All Segments":
                df_trd = df_trd[df_trd['Segment'] == s]

            # Date Range filter
            d_from = self.f_date_from.get().strip()
            if d_from:
                try:
                    dt_f = pd.to_datetime(d_from).date()
                    def match_from(r):
                        if r.get('Status') == 'CLOSED':
                            ed = pd.to_datetime(r.get('ExitDate')).date() if (pd.notna(r.get('ExitDate')) and r.get('ExitDate')) else None
                            en = pd.to_datetime(r.get('EntryDate')).date() if (pd.notna(r.get('EntryDate')) and r.get('EntryDate')) else None
                            return (ed and ed >= dt_f) or (en and en >= dt_f)
                        else:
                            en = pd.to_datetime(r.get('EntryDate')).date() if (pd.notna(r.get('EntryDate')) and r.get('EntryDate')) else None
                            return en and en >= dt_f
                    df_trd = df_trd[df_trd.apply(match_from, axis=1)]
                except: pass

            d_to = self.f_date_to.get().strip()
            if d_to:
                try:
                    dt_t = pd.to_datetime(d_to).date()
                    def match_to(r):
                        if r.get('Status') == 'CLOSED':
                            ed = pd.to_datetime(r.get('ExitDate')).date() if (pd.notna(r.get('ExitDate')) and r.get('ExitDate')) else None
                            en = pd.to_datetime(r.get('EntryDate')).date() if (pd.notna(r.get('EntryDate')) and r.get('EntryDate')) else None
                            return (ed and ed <= dt_t) or (en and en <= dt_t)
                        else:
                            en = pd.to_datetime(r.get('EntryDate')).date() if (pd.notna(r.get('EntryDate')) and r.get('EntryDate')) else None
                            return en and en <= dt_t
                    df_trd = df_trd[df_trd.apply(match_to, axis=1)]
                except: pass

            # Expiry filter
            exp_disp = self.f_expiry.get()
            if exp_disp and exp_disp != "All Expiries":
                raw_exp = self.expiry_map.get(exp_disp)
                if raw_exp: df_trd = df_trd[df_trd['ExpiryDate'].astype(str) == raw_exp]

            # Symbol filter
            sym = self.f_sym.get().strip()
            if sym:
                df_trd = df_trd[df_trd['Symbol'].astype(str).str.contains(sym, case=False, na=False) |
                                df_trd['ContractName'].astype(str).str.contains(sym, case=False, na=False)]

        self.filtered_trades_df = df_trd

        self._update_kpi_cards()
        self._mark_all_tabs_dirty()
        self._render_active_tab(self.tabs.get())

    def reset_filters(self):
        self.f_trade_status.set("💼 Current Holdings (All Segments)")
        self.f_fy.set("All FYs")
        self.f_broker.set("All Brokers")
        self.f_segment.set("All Segments")
        if hasattr(self, 'f_status'): self.f_status.set("All Statuses")
        self.f_action.set("All")
        self.f_type.set("All Types")
        self.f_product.set("All Products")
        self.f_date_from.set("")
        self.f_date_to.set("")
        self.f_expiry.set("All Expiries")
        self.f_sym_select.set("All Symbols")
        self.f_sym.set("")

        self.apply_filters()

    def _mark_all_tabs_dirty(self):
        for k in self._dirty_tabs:
            self._dirty_tabs[k] = True

    def _update_kpi_cards(self):
        mode = self.f_trade_status.get()
        df = self.filtered_trades_df

        if not self.matched_trades_df.empty:
            open_recs = self.matched_trades_df[self.matched_trades_df['Status'] == 'OPEN']
            closed_recs = self.matched_trades_df[self.matched_trades_df['Status'] == 'CLOSED']

            tot_open_cnt = len(open_recs)
            tot_open_val = open_recs['EntryValue'].sum() if not open_recs.empty else 0.0

            tot_closed_cnt = len(closed_recs)
            tot_closed_pnl = closed_recs['GrossPnL'].sum() if not closed_recs.empty else 0.0
            wins = len(closed_recs[closed_recs['GrossPnL'] > 0]) if not closed_recs.empty else 0
            win_r = (wins / tot_closed_cnt * 100) if tot_closed_cnt > 0 else 0.0

            pnl_sign = "+" if tot_closed_pnl >= 0 else ""
            pnl_col = "#00E676" if tot_closed_pnl >= 0 else "#FF5252"

            if ("Current Holdings" in mode or "Verified Holdings" in mode or "Open Trades" in mode or "Dispute Data" in mode) and not self.open_trades_df.empty:
                v_h = self.open_trades_df[self.open_trades_df['HoldingStatus'].isin(['VERIFIED_HOLDING', 'ACTIVE_DERIVATIVE'])]
                d_h = self.open_trades_df[self.open_trades_df['HoldingStatus'] == 'DISPUTE_DATA']
                demat_c = len(self.open_trades_df[self.open_trades_df['HoldingStatus'] == 'VERIFIED_HOLDING'])
                fno_c = len(self.open_trades_df[self.open_trades_df['HoldingStatus'] == 'ACTIVE_DERIVATIVE'])
                dispute_c = len(d_h)
                tot_v_cap = v_h['CommittedValue'].sum() if not v_h.empty else 0.0

                self._set_kpi("total_trades", f"{len(v_h):,} Verified", f"{demat_c} Demat, {fno_c} F&O Active")
                self._set_kpi("committed_open", f"Rs. {tot_v_cap:,.2f}", f"Verified committed capital")
                self._set_kpi("realized_pnl", f"⚠️ {dispute_c:,} Disputed", f"Unequal Buy/Sell (Need logs)", "#FFA726" if dispute_c > 0 else "#00E676")
                self._set_kpi("win_rate", f"{win_r:.1f}%", f"{wins} profitable closed trades")
                self._set_kpi("closed_trades", f"{tot_closed_cnt:,}", f"Historical closed trades")
                self._set_kpi("friction_orders", f"{len(self.full_orders_df):,}", f"Total orders ingested")

            elif "Closed Trades Only" in mode:
                cur_closed_cnt = len(df)
                cur_pnl = df['GrossPnL'].sum() if not df.empty else 0.0
                cur_wins = len(df[df['GrossPnL'] > 0]) if not df.empty else 0
                cur_win_r = (cur_wins / cur_closed_cnt * 100) if cur_closed_cnt > 0 else 0.0
                c_sign = "+" if cur_pnl >= 0 else ""
                c_col = "#00E676" if cur_pnl >= 0 else "#FF5252"

                self._set_kpi("total_trades", f"{cur_closed_cnt:,}", f"{cur_wins} Wins, {cur_closed_cnt - cur_wins} Losses")
                self._set_kpi("committed_open", f"Rs. {tot_open_val:,.2f}", f"{tot_open_cnt:,} open positions held")
                self._set_kpi("realized_pnl", f"{c_sign}Rs. {cur_pnl:,.2f}", f"Filtered closed P&L", c_col)
                self._set_kpi("win_rate", f"{cur_win_r:.1f}%", f"{cur_wins} of {cur_closed_cnt:,} closed")
                self._set_kpi("closed_trades", f"{cur_closed_cnt:,}", f"Matched closed trades")
                self._set_kpi("friction_orders", f"{len(self.full_orders_df):,}", f"Total orders ingested")

            else:
                self._set_kpi("total_trades", f"{len(df):,}", f"Active selection")
                self._set_kpi("committed_open", f"Rs. {tot_open_val:,.2f}", f"{tot_open_cnt:,} open positions")
                self._set_kpi("realized_pnl", f"{pnl_sign}Rs. {tot_closed_pnl:,.2f}", f"Realized P&L", pnl_col)
                self._set_kpi("win_rate", f"{win_r:.1f}%", f"{wins} Wins")
                self._set_kpi("closed_trades", f"{tot_closed_cnt:,}", f"Closed trades")
                self._set_kpi("friction_orders", f"{len(self.full_orders_df):,}", f"Total orders ingested")

    def _set_kpi(self, key, val, sub, text_col=None):
        if key in self.kpi_cards:
            v_lbl, s_lbl = self.kpi_cards[key]
            v_lbl.configure(text=val)
            if text_col: v_lbl.configure(text_color=text_col)
            s_lbl.configure(text=sub)

    # -------------------------------------------------------------
    # 6. SYNC FOLDER TRIGGER
    # -------------------------------------------------------------
    def _trigger_sync_folder(self):
        self.tabs.set("🔄 Sync & Ingestion Hub")
        self.log_sync_msg("⚡ Starting Ingestion & Deduplication Pipeline...")

        def worker():
            res = trade_orders_engine.sync_trade_orders()
            self.after(0, lambda: self._on_sync_finished(res))

        threading.Thread(target=worker, daemon=True).start()

    def _on_sync_finished(self, res):
        self.log_sync_msg(f"Finished: {res['total_files']} files checked, {res['processed_files']} files archived.")
        self.log_sync_msg(f"New Orders Inserted: {res['new_orders_inserted']}, Duplicates Skipped: {res['duplicates_skipped']}")
        for d in res['details']:
            self.log_sync_msg(f" • {d}")
        for err in res['errors']:
            self.log_sync_msg(f" [INFO] {err}")

        self.load_data()
        messagebox.showinfo(
            "Sync Complete",
            f"Sync Complete!\n\nNew Orders Ingested: {res['new_orders_inserted']}\nDuplicates Prevented: {res['duplicates_skipped']}\nFiles Archived to Backup: {res['processed_files']}"
        )

    # -------------------------------------------------------------
    # 7. EXPORT CSV
    # -------------------------------------------------------------
    def _export_to_csv(self):
        mode = self.f_trade_status.get()
        if "Raw Order" in mode:
            df_to_export = self.filtered_orders_df
            default_name = f"Raw_Orders_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        elif "Active & Open" in self.tabs.get():
            df_to_export = self.open_trades_df
            default_name = f"Active_Open_Positions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            df_to_export = self.filtered_trades_df
            status_tag = "Open" if "Open" in mode else ("Closed" if "Closed" in mode else "All")
            default_name = f"My_Trade_Log_{status_tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"

        if df_to_export.empty:
            messagebox.showinfo("Export Warning", "No records available to export for the current view.")
            return

        fpath = filedialog.asksaveasfilename(
            defaultextension=".csv",
            initialfile=default_name,
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")]
        )
        if fpath:
            try:
                df_to_export.to_csv(fpath, index=False)
                messagebox.showinfo("Export Successful", f"Successfully exported {len(df_to_export):,} records to:\n{fpath}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to save CSV file:\n{e}")
