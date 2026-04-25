# Application Flow Document
## HFT Decision Terminal

### 1. User Journey: Initialization
1. User launches `main.py`.
2. System initializes `DatabaseHelper` and checks SQL Server connection.
3. `MarketAPI` initializes and fetches initial market breadth data.
4. Main Dashboard loads with "Global Markets" as the default view.

### 2. Main Navigation Flow
- **Global Markets:** Real-time indices -> Click Index -> View Components -> Click Component -> View History.
- **Futures/Options Analysis:** Select Sector -> Select Industry -> Search Symbol -> Analyze.
- **HFT Decision Engine:** Select Symbol -> Analyze & Predict -> View Targets/Backtest.
- **AI Stocks Screener:** Launch Deep Scan -> Filter Top Momentum Picks -> Drilldown into History.

### 3. Intelligence Engine Logic Flow
1. **Fetch:** Get latest BhavCopy data and Live Spot price.
2. **Analysis:**
   - Calculate OI Change and Price Change.
   - Categorize Buildup (Long/Short/Covering/Unwinding).
   - Compute PCR and Momentum scores.
3. **Justification:** Generate AI narrative based on indicator convergences.
4. **Display:** Sort by Conviction Score and display in "LIVE MUST TRADE".

### 4. Historical Data Drilldown Flow
1. User double-clicks a symbol.
2. `HistoricalDataViewer` opens.
3. Background threads fetch Daily, Weekly, Monthly, and Yearly data.
4. User toggles timeframe -> UI resamples and redraws chart/sheet instantly.

### 5. Error & Fallback Flow
- **No DB Connection:** Terminal enters "Live API only" mode for basic spot prices.
- **API Rate Limit:** System caches previous values and retries with backoff.
- **Data Gap:** UI displays "Insufficient Data" for chart components without crashing.
