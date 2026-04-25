with open(r'c:\Users\navin\StockMarketFnO\main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for line in lines:
    if 'stats = "🎯 ADVANCED INTELLIGENCE' in line:
        new_lines.append('        stats = "🎯 ADVANCED INTELLIGENCE REPORT 🎯\\n" + "="*60 + "\\n\\n"\n')
    elif 'stats += f"📊 Total Trades Executed:' in line:
        new_lines.append('        stats += f"📊 Total Trades Executed: {len(df)}\\n"\n')
    elif 'stats += f"🏆 Overall Strike Rate:' in line:
        new_lines.append('        stats += f"🏆 Overall Strike Rate: {win_rate:.1f}%\\n"\n')
    elif 'stats += "-"*60 +' in line:
        new_lines.append('        stats += "-"*60 + "\\n"\n')
    elif 'stats += f"💰 Gross P&L: ₹{total_gross:,.2f}' in line:
        new_lines.append('        stats += f"💰 Gross P&L: ₹{total_gross:,.2f}\\n"\n')
    elif 'stats += f"💸 Total Brokerage & Taxes: ₹{total_charges:,.2f}' in line:
        new_lines.append('        stats += f"💸 Total Brokerage & Taxes: ₹{total_charges:,.2f}  (Eating {(total_charges/abs(total_gross)*100 if total_gross!=0 else 0):.1f}% of Gross)\\n"\n')
    elif 'stats += f"✅ NET REALIZED P&L: ₹{total_net_pnl:,.2f}' in line:
        new_lines.append('        stats += f"✅ NET REALIZED P&L: ₹{total_net_pnl:,.2f}\\n"\n')
    elif 'stats += "🚀 TOP WINNING METRICS:' in line:
        new_lines.append('        stats += "🚀 TOP WINNING METRICS:\\n"\n')
    elif 'stats += f"   • Best Single Trade:' in line:
        new_lines.append('        stats += f"   • Best Single Trade: {best_trade[\'Symbol\']} (+₹{best_trade[\'PnL\']:,.2f}) via {best_trade[\'Broker\']}\\n"\n')
    elif 'stats += f"   • Most Profitable Broker:' in line:
        new_lines.append('        stats += f"   • Most Profitable Broker: {best_broker} (+₹{broker_pnl.get(best_broker,0):,.2f})\\n"\n')
    elif 'stats += "   • Broker Win Rates:' in line:
        new_lines.append('        stats += "   • Broker Win Rates:\\n"\n')
    elif 'stats += f"        {b}: {w_pct:.1f}%' in line:
        new_lines.append('            stats += f"        {b}: {w_pct:.1f}% ({broker_wins.get(b,0)}/{broker_trades[b]} wins) -> Net P&L: ₹{broker_pnl[b]:,.2f}\\n"\n')
    elif 'stats += "\\n🩸 TOP LOSING METRICS:' in line:
        new_lines.append('        stats += "\\n🩸 TOP LOSING METRICS:\\n"\n')
    elif 'stats += f"   • Worst Single Trade:' in line:
        new_lines.append('        stats += f"   • Worst Single Trade: {worst_trade[\'Symbol\']} (₹{worst_trade[\'PnL\']:,.2f}) via {worst_trade[\'Broker\']}\\n"\n')
    elif 'stats += f"   • Least Profitable Broker:' in line:
        new_lines.append('        stats += f"   • Least Profitable Broker: {worst_broker} (₹{broker_pnl.get(worst_broker,0):,.2f})\\n"\n')
    elif 'stats += "   • Biggest Wealth Destroyers' in line:
        new_lines.append('        stats += "   • Biggest Wealth Destroyers (Symbols):\\n"\n')
    elif 'stats += f"        {s}: ₹{p:,.2f}' in line:
        new_lines.append('                stats += f"        {s}: ₹{p:,.2f}\\n"\n')
    elif 'stats += "\\n📅 MONTH-WISE P&L TREND:' in line:
        new_lines.append('            stats += "\\n📅 MONTH-WISE P&L TREND:\\n"\n')
    elif 'stats += f"   • {r[\'ExitDate\'].strftime(' in line:
        new_lines.append('                stats += f"   • {r[\'ExitDate\'].strftime(\'%b %Y\')}: ₹{r[\'NetPnL\']:,.2f}\\n"\n')
    elif line.strip() == '"':
        pass # Skip empty EOL quotes
    else:
        new_lines.append(line)

with open(r'c:\Users\navin\StockMarketFnO\main.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
