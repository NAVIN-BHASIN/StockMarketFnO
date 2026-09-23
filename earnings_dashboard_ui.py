import customtkinter as ctk
import pandas as pd
from datetime import datetime

class ResultCard(ctk.CTkFrame):
    def __init__(self, master, row_data, is_yoy=True, history_callback=None):
        super().__init__(master, fg_color="#1a1a24", corner_radius=10, border_width=1, border_color="#2c2c3a")
        
        # Data unpacking
        sym = row_data.get('Symbol', '')
        name = row_data.get('CompanyName', sym)
        if pd.isna(name): name = sym
        
        date_str = str(row_data.get('Quarter_End', ''))
        
        rev = row_data.get('Revenue', 0) / 10000000.0
        gp = row_data.get('Gross_Profit', 0) / 10000000.0
        np_val = row_data.get('Net_Profit', 0) / 10000000.0
        
        rev_yoy = row_data.get('Revenue_Growth_YoY', 0)
        gp_yoy = row_data.get('Gross_Profit_Growth_YoY', 0)
        np_yoy = row_data.get('Net_Profit_Growth_YoY', 0)
        
        rev_qoq = row_data.get('Revenue_Growth_QoQ', 0)
        gp_qoq = row_data.get('Gross_Profit_Growth_QoQ', 0)
        np_qoq = row_data.get('Net_Profit_Growth_QoQ', 0)
        
        rev_g = rev_yoy if is_yoy else rev_qoq
        gp_g = gp_yoy if is_yoy else gp_qoq
        np_g = np_yoy if is_yoy else np_qoq
        
        if pd.isna(rev_g): rev_g = 0
        if pd.isna(gp_g): gp_g = 0
        if pd.isna(np_g): np_g = 0
        
        # Calculate previous values mathematically based on growth %
        def calc_prev(val, growth):
            if pd.isna(val) or pd.isna(growth) or val == 0: return 0
            return val / (1 + (growth / 100.0))
            
        prev_rev = calc_prev(rev, rev_g)
        prev_gp = calc_prev(gp, gp_g)
        prev_np = calc_prev(np_val, np_g)
        
        # Header (Date, Symbol)
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=15, pady=(15, 5))
        
        ctk.CTkLabel(hdr, text=date_str, font=ctk.CTkFont(size=10), text_color="gray60").pack(side="left")
        ctk.CTkLabel(hdr, text="Rs.Cr.", font=ctk.CTkFont(size=10), text_color="gray60").pack(side="right")
        
        display_name = str(name)
        if len(display_name) > 20: display_name = display_name[:18] + "..."
        name_lbl = ctk.CTkLabel(self, text=display_name, font=ctk.CTkFont(size=14, weight="bold"), anchor="w")
        name_lbl.pack(fill="x", padx=15)
        
        # Separator
        ctk.CTkFrame(self, height=1, fg_color="#333344").pack(fill="x", padx=15, pady=10)
        
        # Table Container
        tbl_cont = ctk.CTkFrame(self, fg_color="transparent")
        tbl_cont.pack(fill="x", padx=15, pady=(0, 5))
        
        tbl_cont.grid_columnconfigure(0, weight=2) # Title
        tbl_cont.grid_columnconfigure(1, weight=1) # Latest
        tbl_cont.grid_columnconfigure(2, weight=1) # Previous
        tbl_cont.grid_columnconfigure(3, weight=1) # Growth
        
        prev_label = "YoY Prev" if is_yoy else "QoQ Prev"
        
        # Table Header
        ctk.CTkLabel(tbl_cont, text="Metrics", font=ctk.CTkFont(size=11), text_color="gray60", anchor="w").grid(row=0, column=0, sticky="w", pady=(0,5))
        ctk.CTkLabel(tbl_cont, text="Latest", font=ctk.CTkFont(size=11), text_color="gray60", anchor="e").grid(row=0, column=1, sticky="e", padx=5, pady=(0,5))
        ctk.CTkLabel(tbl_cont, text=prev_label, font=ctk.CTkFont(size=11), text_color="gray60", anchor="e").grid(row=0, column=2, sticky="e", padx=5, pady=(0,5))
        ctk.CTkLabel(tbl_cont, text="Growth", font=ctk.CTkFont(size=11), text_color="gray60", anchor="e").grid(row=0, column=3, sticky="e", pady=(0,5))
        
        self.row_idx = 1
        # Helper for rows
        def add_row(title, val_latest, val_prev, grw):
            ctk.CTkLabel(tbl_cont, text=title, font=ctk.CTkFont(size=12), anchor="w").grid(row=self.row_idx, column=0, sticky="w", pady=2)
            ctk.CTkLabel(tbl_cont, text=f"{val_latest:,.0f}", font=ctk.CTkFont(size=12), anchor="e").grid(row=self.row_idx, column=1, sticky="e", padx=5, pady=2)
            ctk.CTkLabel(tbl_cont, text=f"{val_prev:,.0f}", font=ctk.CTkFont(size=12), text_color="gray70", anchor="e").grid(row=self.row_idx, column=2, sticky="e", padx=5, pady=2)
            
            c_color = "#00E676" if grw > 0 else "#FF5252" if grw < 0 else "gray70"
            g_str = f"+{grw:.1f}%" if grw > 0 else f"{grw:.1f}%"
            ctk.CTkLabel(tbl_cont, text=g_str, font=ctk.CTkFont(size=12, weight="bold"), text_color=c_color, anchor="e").grid(row=self.row_idx, column=3, sticky="e", pady=2)
            self.row_idx += 1            
        
        add_row("Revenue", rev, prev_rev, rev_g)
        add_row("Gross Profit", gp, prev_gp, gp_g)
        add_row("Net Profit", np_val, prev_np, np_g)
        
        # Footer
        ftr = ctk.CTkFrame(self, fg_color="transparent")
        ftr.pack(fill="x", padx=15, pady=(15, 15))
        btn = ctk.CTkButton(ftr, text=f"{sym} History", width=100, height=24, fg_color="#2a2a35", hover_color="#3a3a45", font=ctk.CTkFont(size=11))
        btn.pack(side="left")
        if history_callback:
            btn.configure(command=lambda s=sym: history_callback(s))


class EarningsCalendarFrame(ctk.CTkFrame):
    def __init__(self, master, db):
        super().__init__(master, fg_color="transparent")
        self.db = db
        
        # Header
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=10, pady=(10, 0))
        ctk.CTkLabel(hdr, text="RESULT CALENDAR", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        
        # Timeline Container
        self.timeline = ctk.CTkScrollableFrame(self, orientation="horizontal", height=180, fg_color="#1a1a1a", corner_radius=10)
        self.timeline.pack(fill="x", padx=10, pady=10)
        
        self.load_calendar()
        
    def load_calendar(self, quarter_end="All", valid_symbols=None, sector="All"):
        # Update Header
        hdr_txt = "RESULT CALENDAR"
        if quarter_end != "All": hdr_txt += f" | {quarter_end}"
        if sector != "All": hdr_txt += f" | {sector}"
        
        for w in self.winfo_children():
            if isinstance(w, ctk.CTkFrame) and w != self.timeline:
                for child in w.winfo_children():
                    if isinstance(child, ctk.CTkLabel) and "CALENDAR" in child.cget("text"):
                        child.configure(text=hdr_txt)
        
        where_clause = "1=1"
        if valid_symbols is not None and len(valid_symbols) > 0:
            if len(valid_symbols) == 1:
                where_clause += f" AND Symbol = '{valid_symbols[0]}'"
            else:
                where_clause += f" AND Symbol IN {tuple(valid_symbols)}"
        elif valid_symbols is not None and len(valid_symbols) == 0:
            where_clause += " AND 1=0"
            
        if quarter_end != "All":
            where_clause += f" AND Earnings_Date <= '{quarter_end}' AND Earnings_Date >= DATEADD(month, -3, '{quarter_end}')"
        else:
            where_clause += " AND Earnings_Date >= DATEADD(day, -7, GETDATE()) AND Earnings_Date <= DATEADD(day, 30, GETDATE())"
            
        query = f"""
        SELECT Earnings_Date, COUNT(*) as Count, 
               STRING_AGG(Symbol, ',') as Symbols
        FROM Corporate_Earnings_Calendar
        WHERE {where_clause}
        GROUP BY Earnings_Date
        ORDER BY Earnings_Date DESC
        """
        try:
            for widget in self.timeline.winfo_children(): widget.destroy()
            
            with self.db.get_connection() as conn:
                df = pd.read_sql(query, conn)
                
            for _, row in df.iterrows():
                date = row['Earnings_Date']
                count = row['Count']
                syms = row['Symbols'].split(',')[:3] # Show up to 3
                
                dt_str = pd.to_datetime(date).strftime("%d %b")
                
                day_frm = ctk.CTkFrame(self.timeline, fg_color="transparent")
                day_frm.pack(side="left", padx=15)
                
                ctk.CTkLabel(day_frm, text=dt_str, font=ctk.CTkFont(size=14, weight="bold")).pack()
                ctk.CTkLabel(day_frm, text=f"{count} Earnings", font=ctk.CTkFont(size=11), text_color="gray60").pack()
                
                ctk.CTkFrame(day_frm, width=80, height=2, fg_color="#333").pack(pady=5)
                
                for s in syms:
                    ctk.CTkLabel(day_frm, text=s, font=ctk.CTkFont(size=11, weight="bold")).pack()
                    
        except Exception as e:
            print(f"Error loading calendar: {e}")

class EarningsDashboardFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, db):
        super().__init__(master, corner_radius=15)
        self.db = db
        
        #  Result Calendar 
        self.calendar = EarningsCalendarFrame(self, db)
        self.calendar.pack(fill="x", pady=(0, 10))
        
        #  Top Summary Section 
        self.summary_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.summary_frame.pack(fill="x", padx=20, pady=5)

        
        self.lbl_total = self.create_summary_card(self.summary_frame, "Results So Far", "--")
        self.lbl_pos = self.create_summary_card(self.summary_frame, "Positive Growth", "--", "#00E676")
        self.lbl_neg = self.create_summary_card(self.summary_frame, "Negative Growth", "--", "#FF5252")
        self.lbl_top_sec = self.create_summary_card(self.summary_frame, "Top Sector", "--", "#4FC3F7")
        self.lbl_bot_sec = self.create_summary_card(self.summary_frame, "Underperforming", "--", "#FFB300")
        
        #  Middle Action Row 
        mid_row = ctk.CTkFrame(self, fg_color="transparent")
        mid_row.pack(fill="x", padx=20, pady=10)
        
        title = ctk.CTkLabel(mid_row, text="RAPID RESULTS", font=ctk.CTkFont(size=22, weight="bold"))
        title.pack(side="left")
        
        # Filter Toggles
        self.radio_var = ctk.StringVar(value="YoY")
        radio_frame = ctk.CTkFrame(self.summary_frame, fg_color="transparent")
        radio_frame.pack(side="right")
        
        ctk.CTkRadioButton(radio_frame, text="QoQ", variable=self.radio_var, value="QoQ", command=self.refresh_cards).pack(side="left", padx=10)
        ctk.CTkRadioButton(radio_frame, text="YoY", variable=self.radio_var, value="YoY", command=self.refresh_cards).pack(side="left", padx=10)
        
        #  Category Tabs 
        self.cat_seg = ctk.CTkSegmentedButton(
            self,
            values=["Latest Results", "Best Performer", "Worst Performer", "Positive Turnaround"],
            command=self.on_category_change,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.cat_seg.set("Latest Results")
        self.cat_seg.pack(fill="x", padx=20, pady=(0, 20))
        
        #  Scrollable Cards Area 
        self.cards_inner = ctk.CTkFrame(self, fg_color="transparent")
        self.cards_inner.pack(fill="both", expand=True, padx=20)
        
        self.load_data()
        
    def create_summary_card(self, parent, title, val, color="white"):
        card = ctk.CTkFrame(parent, fg_color="#161b22", corner_radius=10, border_width=1, border_color="#30363d")
        card.pack(side="left", fill="both", expand=True, padx=5)
        
        ctk.CTkLabel(card, text=title, font=ctk.CTkFont(size=12), text_color="gray70").pack(pady=(15, 5))
        val_lbl = ctk.CTkLabel(card, text=val, font=ctk.CTkFont(size=20, weight="bold"), text_color=color)
        val_lbl.pack(pady=(0, 15))
        return val_lbl

    def load_data(self, quarter_end="All", cap="All", index_filter="All", sector="All", industry="All", symbol="All"):
        self.current_quarter_end = quarter_end
        
        # Get valid symbols based on filters
        df_symbols = self.db.get_cash_stocks(sector=sector, industry=industry, cap=cap, index_filter=index_filter)
        if isinstance(df_symbols, pd.DataFrame) and not df_symbols.empty:
            valid_symbols = df_symbols['Symbol'].tolist()
            if symbol != "All" and symbol in valid_symbols:
                valid_symbols = [symbol]
            elif symbol != "All":
                valid_symbols = []
        elif isinstance(df_symbols, list):
            valid_symbols = df_symbols
            if symbol != "All" and symbol in valid_symbols:
                valid_symbols = [symbol]
            elif symbol != "All":
                valid_symbols = []
        else:
            valid_symbols = []
            
        self.valid_symbols = valid_symbols
        self.calendar.load_calendar(quarter_end=quarter_end, valid_symbols=valid_symbols, sector=sector)
        
        # Fetch summary data
        try:
            where_clause = "1=1"
            if quarter_end != "All": where_clause += f" AND c.Quarter_End = '{quarter_end}'"
                
            query = f"""
            SELECT c.*, s.Sector, s.CompanyName
            FROM Corporate_Earnings_Master c
            LEFT JOIN nseauto.NSE_Stock_Classification_Master s ON c.Symbol = s.Symbol
            WHERE {where_clause}
            """
            
            with self.db.get_connection() as conn:
                df = pd.read_sql(query, conn)
                
            if valid_symbols is not None and len(valid_symbols) > 0:
                df = df[df['Symbol'].isin(valid_symbols)]
            elif valid_symbols is not None and len(valid_symbols) == 0:
                df = pd.DataFrame()

                
            if not df.empty:
                # Basic stats
                total = len(df)
                latest_q = df['Quarter_End'].max() if 'Quarter_End' in df.columns else ""
                
                self.lbl_total.configure(text=f"{total} ({latest_q})")
                
                pos = len(df[df['Net_Profit_Growth_YoY'] > 0])
                neg = len(df[df['Net_Profit_Growth_YoY'] < 0])
                self.lbl_pos.configure(text=f"^ {pos}")
                self.lbl_neg.configure(text=f"v {neg}")
                
                # Top sector
                sec_grp = df.groupby('Sector')['Net_Profit_Growth_YoY'].mean().dropna()
                if not sec_grp.empty:
                    top_sec = str(sec_grp.idxmax())
                    bot_sec = str(sec_grp.idxmin())
                    self.lbl_top_sec.configure(text=top_sec[:10] + ".." if len(top_sec)>10 else top_sec)
                    self.lbl_bot_sec.configure(text=bot_sec[:10] + ".." if len(bot_sec)>10 else bot_sec)
                
                self.df_cache = df
                self.refresh_cards()
            else:
                self.lbl_total.configure(text="0")
                self.lbl_pos.configure(text="0")
                self.lbl_neg.configure(text="0")
                self.lbl_top_sec.configure(text="--")
                self.lbl_bot_sec.configure(text="--")
                for widget in self.cards_inner.winfo_children(): widget.destroy()
                
        except Exception as e:
            print(f"Error loading dashboard: {e}")
            
    def on_category_change(self, value):
        self.refresh_cards()
        
    def refresh_cards(self):
        for widget in self.cards_inner.winfo_children():
            widget.destroy()
            
        is_yoy = self.radio_var.get() == "YoY"
        sort_col = "Net_Profit_Growth_YoY" if is_yoy else "Net_Profit_Growth_QoQ"
        
        try:
            q_filter = getattr(self, "current_quarter_end", "All")
            valid_symbols = getattr(self, "valid_symbols", None)
            
            where_clause = "1=1"
            if q_filter != "All": where_clause += f" AND c.Quarter_End = '{q_filter}'"
            
            query = f"""
            SELECT c.*, s.CompanyName 
            FROM Corporate_Earnings_Master c
            LEFT JOIN nseauto.NSE_Stock_Classification_Master s ON c.Symbol = s.Symbol
            INNER JOIN (
                SELECT Symbol, MAX(Quarter_End) as MaxQ FROM Corporate_Earnings_Master c2 WHERE {where_clause.replace('c.', 'c2.')} GROUP BY Symbol
            ) latest ON c.Symbol = latest.Symbol AND c.Quarter_End = latest.MaxQ
            WHERE {where_clause}
            """
            with self.db.get_connection() as conn:
                df_show = pd.read_sql(query, conn)
                
            if valid_symbols is not None and len(valid_symbols) > 0:
                df_show = df_show[df_show['Symbol'].isin(valid_symbols)]
            elif valid_symbols is not None and len(valid_symbols) == 0:
                df_show = pd.DataFrame()
                
            cat = self.cat_seg.get()
            
            if cat == "Latest Results":
                df_show = df_show.sort_values('Quarter_End', ascending=False)
            elif cat == "Best Performer":
                df_show = df_show.sort_values(sort_col, ascending=False)
            elif cat == "Worst Performer":
                df_show = df_show.sort_values(sort_col, ascending=True)
            elif cat == "Positive Turnaround":
                df_show = df_show[df_show[sort_col] > 50].sort_values(sort_col, ascending=False)
                
            df_show = df_show.head(12) # show top 12 cards
            
            cols = 3
            for i, (_, row) in enumerate(df_show.iterrows()):
                r = i // cols
                c = i % cols
                card = ResultCard(self.cards_inner, row, is_yoy, history_callback=self.show_history) 
                card.grid(row=r, column=c, padx=10, pady=10, sticky="nsew")
                self.cards_inner.grid_columnconfigure(c, weight=1)
                
        except Exception as e:
            print(f"Error loading cards: {e}")

    def show_history(self, symbol):
        query = f"SELECT Quarter_End, Revenue, Gross_Profit, Net_Profit, Revenue_Growth_YoY, Net_Profit_Growth_YoY FROM Corporate_Earnings_Master WHERE Symbol = '{symbol}' ORDER BY Quarter_End DESC"
        try:
            with self.db.get_connection() as conn:
                df = pd.read_sql(query, conn)
                
            # Formatting data for display
            df['Quarter_End'] = df['Quarter_End'].astype(str)
            for col in ['Revenue', 'Gross_Profit', 'Net_Profit']:
                df[col] = pd.to_numeric(df[col], errors='coerce') / 10000000.0
                df[col] = df[col].apply(lambda x: f"{x:,.0f}" if pd.notna(x) else "-")
                
            for col in ['Revenue_Growth_YoY', 'Net_Profit_Growth_YoY']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df[col] = df[col].apply(lambda x: f"{x:.2f}%" if pd.notna(x) else "-")
                
            top = ctk.CTkToplevel(self)
            top.title(f"{symbol} - Historical Corporate Earnings")
            top.geometry("700x400")
            top.transient(self.winfo_toplevel())
            
            from tksheet import Sheet
            sheet = Sheet(top, data=df.values.tolist(), headers=["Quarter End", "Revenue (Rs.Cr)", "Gross Profit", "Net Profit", "Rev YoY %", "PAT YoY %"])
            sheet.enable_bindings(("single_select", "row_select", "column_width_resize", "arrowkeys", "copy", "rc_sort"))
            if ctk.get_appearance_mode() == "Dark": sheet.change_theme("dark")
            sheet.pack(fill="both", expand=True, padx=20, pady=20)
            
        except Exception as e:
            print(f"Error fetching history: {e}")
