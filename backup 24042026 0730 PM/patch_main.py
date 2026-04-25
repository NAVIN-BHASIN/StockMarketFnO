with open('main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1) Call init_strat_filters from init_symbols
old1 = '    def init_symbols(self):\n        symbols = self.db.get_symbols()\n        if symbols:\n            self.symbol_dropdown.configure(values=symbols)\n            self.symbol_var.set(symbols[0])'
new1 = '''    def init_symbols(self):
        symbols = self.db.get_symbols()
        if symbols:
            self.symbol_dropdown.configure(values=symbols)
            self.symbol_var.set(symbols[0])
        self.init_strat_filters()'''

if old1 in content:
    content = content.replace(old1, new1, 1)
    print("Patch 1: init_strat_filters call added OK")
else:
    print("Patch 1 NOT FOUND")

# 2) Add OI and Delivery% intelligence block into _update_strat_ui before narrative
old2 = '        oi_chg_pct = ""\n        if not df.empty and len(df) >= 2:\n            try:\n                oi_now  = float(df[\'OI_NO_CON\'].iloc[-1])\n                oi_prev = float(df[\'OI_NO_CON\'].iloc[-2])\n                oi_chg_pct = f"{((oi_now - oi_prev)/max(oi_prev,1)*100):+.1f}%"\n            except Exception:\n                oi_chg_pct = "N/A"'

new2 = '''        # \u2500\u2500 OI & Delivery % intelligence \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
        oi_chg_pct = "N/A"
        oi_intel   = "OI data unavailable"
        deliv_intel = "Delivery data unavailable"
        if not df.empty and len(df) >= 2:
            try:
                oi_now  = float(df['OI_NO_CON'].iloc[-1])
                oi_prev = float(df['OI_NO_CON'].iloc[-2])
                oi_pct  = (oi_now - oi_prev) / max(oi_prev, 1) * 100
                oi_chg_pct = f"{oi_pct:+.1f}%"
                if oi_pct > 5:
                    oi_intel = f"OI rising sharply ({oi_chg_pct}) - Strong fresh {('LONG' if price > vwap else 'SHORT')} buildup. HIGH conviction."
                elif oi_pct > 1:
                    oi_intel = f"OI increasing ({oi_chg_pct}) - Moderate position buildup."
                elif oi_pct < -5:
                    oi_intel = f"OI falling sharply ({oi_chg_pct}) - Major unwinding. AVOID new positions."
                elif oi_pct < -1:
                    oi_intel = f"OI decreasing ({oi_chg_pct}) - Positions being closed. Be cautious."
                else:
                    oi_intel = f"OI stable ({oi_chg_pct}) - No strong institutional directional bet."
            except Exception:
                pass

            # Delivery % (DELVP column if present)
            try:
                deliv_cols = [c for c in df.columns if 'DELV' in c.upper() or 'DELIV' in c.upper()]
                if deliv_cols:
                    deliv_pct = float(df[deliv_cols[0]].iloc[-1])
                    if deliv_pct > 60:
                        deliv_intel = (f"Delivery% = {deliv_pct:.1f}%  \u2014  HIGH institutional footprint. "
                                       "Smart money is accumulating. Strong conviction - reduce trap risk.")
                    elif deliv_pct > 40:
                        deliv_intel = (f"Delivery% = {deliv_pct:.1f}%  \u2014  Moderate institutional activity. "
                                       "Mix of real buyers and speculators.")
                    else:
                        deliv_intel = (f"Delivery% = {deliv_pct:.1f}%  \u2014  LOW delivery. "
                                       "Mostly speculative/intraday activity. HIGH TRAP RISK for positional trades.")
                else:
                    deliv_intel = "Delivery% not available in database for this symbol."
            except Exception:
                pass'''

if old2 in content:
    content = content.replace(old2, new2, 1)
    print("Patch 2: OI+Delivery intelligence added OK")
else:
    print("Patch 2 NOT FOUND")
    idx = content.find("oi_chg_pct")
    print("Found 'oi_chg_pct' at:", idx)
    print(repr(content[idx:idx+300]))

# 3) Add OI and delivery to the narrative f-string
old3 = '            f"  OI Change   : {oi_chg_pct}  (rising OI = conviction; falling = unwinding)\\n\\n"'
new3 = ('            f"  OI Change   : {oi_chg_pct}  (rising OI = conviction; falling = unwinding)\\n"\n'
        '            f"  OI Analysis : {oi_intel}\\n"\n'
        '            f"  Smart Money : {deliv_intel}\\n\\n"')
if old3 in content:
    content = content.replace(old3, new3, 1)
    print("Patch 3: narrative lines added OK")
else:
    print("Patch 3 NOT FOUND")

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("File written.")
