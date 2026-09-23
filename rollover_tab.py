import customtkinter as ctk
from tkinter import ttk
from tksheet import Sheet
import threading

class RolloverIntelligenceTab(ctk.CTkFrame):
    def __init__(self, master, db):
        super().__init__(master, fg_color="transparent")
        self.db = db
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)
        
        #  Internal Tabview for Rollover
        self.rtabs = ctk.CTkTabview(self, corner_radius=10)
        self.rtabs.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        self.rtabs.add("Visual Analytics")
        self.rtabs.add("Comprehensive Grid")
        self.rtabs.add("History & Ingestion")
        
        self.setup_visual_tab(self.rtabs.tab("Visual Analytics"))
        self.setup_grid_tab(self.rtabs.tab("Comprehensive Grid"))
        self.setup_history_tab(self.rtabs.tab("History & Ingestion"))
        
        self.after(500, self.refresh_all)

    def setup_visual_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure((0, 1), weight=1)
        
        # Top: Nifty vs Market Chart
        self.nifty_chart_frame = ctk.CTkFrame(parent, fg_color="#1a1a1a", corner_radius=12)
        self.nifty_chart_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Bottom: Sector wise Chart
        self.sector_chart_frame = ctk.CTkFrame(parent, fg_color="#1a1a1a", corner_radius=12)
        self.sector_chart_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def setup_grid_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        
        ctrl = ctk.CTkFrame(parent, fg_color="transparent")
        ctrl.grid(row=0, column=0, sticky="ew", padx=10, pady=5)
        
        ctk.CTkLabel(ctrl, text="Comprehensive Rollover Intelligence", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        
        self.f_sector = ctk.StringVar(value="All")
        ctk.CTkOptionMenu(ctrl, variable=self.f_sector, values=["All"] + self.db.get_all_sectors(), command=lambda _: self.load_grid_data()).pack(side="right", padx=10)
        ctk.CTkLabel(ctrl, text="Filter Sector:").pack(side="right")
        
        self.sheet = Sheet(parent)
        self.sheet.enable_bindings()
        if ctk.get_appearance_mode() == "Dark": self.sheet.change_theme("dark")
        self.sheet.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)

    def setup_history_tab(self, parent):
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_rowconfigure(1, weight=1)
        
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        self.import_btn = ctk.CTkButton(top, text=" Import New Axis PDF", fg_color="#E65100", command=self.import_pdf)
        self.import_btn.pack(side="right")
        ctk.CTkLabel(top, text="Import History & File Log", font=ctk.CTkFont(size=18, weight="bold")).pack(side="left")
        
        parent.grid_rowconfigure(1, weight=1)
        parent.grid_columnconfigure(0, weight=1)

        cols = ["Import Date", "Filename", "Action"]
        self.hist_tree = ttk.Treeview(parent, columns=cols, show="headings", height=15)
        for c in cols: self.hist_tree.heading(c, text=c)
        self.hist_tree.column("Action", width=150)
        self.hist_tree.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)
        self.hist_tree.bind("<Double-1>", self.on_history_click)

    def refresh_all(self):
        threading.Thread(target=self.load_charts, daemon=True).start()
        self.load_grid_data()
        self.load_history()

    def load_charts(self):
        #  Chart 1: Nifty vs Marketwide
        df1 = self.db.get_nifty_vs_market_rollover()
        if not df1.empty:
            self.after(0, lambda: self.plot_nifty_vs_market(df1))
            
        #  Chart 2: Sectorwise Comparison
        df2 = self.db.get_sectorwise_comparison()
        if not df2.empty:
            self.after(0, lambda: self.plot_sectorwise(df2))

    def plot_nifty_vs_market(self, df):
        for w in self.nifty_chart_frame.winfo_children(): w.destroy()
        
        fig, ax1 = plt.subplots(figsize=(10, 4), dpi=90)
        fig.patch.set_facecolor('#1a1a1a')
        ax1.set_facecolor('#1a1a1a')
        
        dates = pd.to_datetime(df['Report_Date']).dt.strftime('%b\'%y')
        x = range(len(dates))
        
        # Bars for MarketRoll (Gray) and NiftyRoll (Burgundy)
        ax1.bar(x, df['MarketRoll'], width=0.3, label='Market-wide', color='gray', alpha=0.7)
        ax1.bar([i-0.2 for i in x], df['NiftyRoll'], width=0.3, label='Nifty', color='#9b0033')
        
        # Line for trend
        ax1.plot(x, df['NiftyRoll'], color='#4FC3F7', marker='o', linewidth=2)
        
        ax1.set_title("Nifty Rollover Vs Market-wide Rollover", color='white', fontsize=12, pad=15)
        ax1.set_xticks(x)
        ax1.set_xticklabels(dates, rotation=45, color='white', fontsize=8)
        ax1.tick_params(colors='white', labelsize=8)
        ax1.set_ylim(50, 100)
        ax1.grid(True, axis='y', color='#333333', linestyle='--', alpha=0.5)
        
        canvas = FigureCanvasTkAgg(fig, master=self.nifty_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def plot_sectorwise(self, df):
        for w in self.sector_chart_frame.winfo_children(): w.destroy()
        
        # Pivot to get Curr vs Prev
        pivot = df.pivot(index='Sector', columns='Report_Date', values='AvgRoll')
        if pivot.shape[1] < 2: return
        
        fig, ax = plt.subplots(figsize=(10, 4), dpi=90)
        fig.patch.set_facecolor('#1a1a1a')
        ax.set_facecolor('#1a1a1a')
        
        sectors = pivot.index
        x = range(len(sectors))
        
        prev_date = pivot.columns[0]
        curr_date = pivot.columns[1]
        
        ax.bar([i-0.15 for i in x], pivot[prev_date], width=0.3, label='Prev Expiry', color='gray', alpha=0.7)
        ax.bar([i+0.15 for i in x], pivot[curr_date], width=0.3, label='Curr Expiry', color='#9b0033')
        
        ax.set_title("Sector wise Rollover", color='white', fontsize=12, pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(sectors, rotation=90, color='white', fontsize=8)
        ax.tick_params(colors='white', labelsize=8)
        ax.set_ylim(0, 110)
        ax.legend(facecolor='#1a1a1a', labelcolor='white', fontsize=8)
        ax.grid(True, axis='y', color='#333333', linestyle='--', alpha=0.5)
        
        fig.tight_layout()
        canvas = FigureCanvasTkAgg(fig, master=self.sector_chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)

    def load_grid_data(self):
        df = self.db.get_comprehensive_rollover_table(self.f_sector.get())
        if df.empty: 
            self.sheet.set_sheet_data([["No data available"]])
            return
            
        # Prepare headers: Symbol, Dates..., L3M, L6M, Rise/Fall
        headers = df.columns.tolist()
        self.sheet.headers(headers)
        
        data = []
        for _, row in df.iterrows():
            r_data = []
            for col in headers:
                val = row[col]
                if isinstance(val, float):
                    r_data.append(f"{val:.2f}%")
                else:
                    r_data.append(str(val))
            data.append(r_data)
            
        self.sheet.set_sheet_data(data)
        self.sheet.set_all_column_widths(100)

    def load_history(self):
        for item in self.hist_tree.get_children(): self.hist_tree.delete(item)
        df = self.db.get_rollover_history_log()
        if not df.empty:
            for _, row in df.iterrows():
                self.hist_tree.insert("", "end", values=(row['Date'], row['Filename'], " Open Analysis"))

    def on_history_click(self, event):
        item = self.hist_tree.identify_row(event.y)
        if item:
            self.rtabs.set("Visual Analytics")

    def import_pdf(self):
        from tkinter import filedialog
        file_path = filedialog.askopenfilename(
            initialdir=r"c:\Users\navin\StockMarketFnO\data\Rollover Files",
            title="Select Axis Rollover PDF",
            filetypes=(("PDF files", "*.pdf"), ("all files", "*.*"))
        )
        if file_path:
            threading.Thread(target=self._import_bg, args=(file_path,), daemon=True).start()

    def _import_bg(self, file_path):
        self.after(0, lambda: self.import_btn.configure(text="Importing...", state="disabled"))
        try:
            import pdfplumber
            import re
            
            report_date = None
            date_match = re.search(r'(\d{2}-\d{2}-\d{4})', file_path)
            if date_match:
                from datetime import datetime
                report_date = datetime.strptime(date_match.group(1), '%d-%m-%Y').strftime('%Y-%m-%d')
            else:
                report_date = pd.Timestamp.now().strftime('%Y-%m-%d')
                
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
                        
                        try:
                            def clean_float(val):
                                if val is None: return 0.0
                                s = str(val).replace('%','').replace(',','').replace('(','-').replace(')','').strip()
                                return float(s) if s and s != '-' else 0.0
                            
                            roll_pct = clean_float(row[1])
                            avg_roll = clean_float(row[2])
                            cost_pct = clean_float(row[3])
                            oi_chg = clean_float(row[4])
                            pr_chg = clean_float(row[5])
                            basis = clean_float(row[6])
                            near_oi = int(clean_float(row[7]))
                            next_oi = int(clean_float(row[8]))
                            far_oi = int(clean_float(row[9]))
                            total_oi = int(clean_float(row[10]))
                            
                            meta = sector_map.get(sym, {'Sector': 'Others', 'Industry': 'Others'})
                            sent = "Neutral"
                            if roll_pct > avg_roll and pr_chg > 0: sent = "Long Buildup ^^"
                            elif roll_pct > avg_roll and pr_chg < 0: sent = "Short Buildup vv"
                            elif roll_pct < avg_roll and pr_chg > 0: sent = "Short Covering ^"
                            elif roll_pct < avg_roll and pr_chg < 0: sent = "Long Unwinding v"

                            data_to_insert.append((report_date, sym, meta['Sector'], meta['Industry'], roll_pct, avg_roll, cost_pct, oi_chg, pr_chg, basis, near_oi, next_oi, far_oi, total_oi, sent))
                        except: continue

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
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Error", f"Failed to import PDF: {str(e)}"))
        finally:
            self.after(0, lambda: self.import_btn.configure(text=" Import New Axis PDF", state="normal"))
