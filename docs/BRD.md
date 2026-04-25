# Business Requirements Document (BRD)
## Project: HFT Decision Terminal & AI Intelligence Engine

### 1. Executive Summary
The HFT Decision Terminal is an institutional-grade trading platform designed to provide professional traders and hedge funds with real-time market intelligence, quantitative analytics, and AI-driven trade signals. The platform focuses on the Futures and Options (F&O) segment of the Indian and Global markets.

### 2. Business Objectives
- **Data-Driven Decision Making:** Provide traders with accurate OI (Open Interest), PCR (Put-Call Ratio), and historical backtesting data.
- **Efficiency:** Automate the screening of 180+ F&O stocks for momentum and breakouts.
- **Edge:** Leverage AI and machine learning to predict price movements and identify high-conviction "Must-Trade" setups.

### 3. Key Stakeholders
- Professional Intraday and Swing Traders.
- Quantitative Research Desks.
- Portfolio Managers.

### 4. Functional Requirements
#### 4.1 Global Markets & Macro View
- Real-time tracking of Indian and Global indices.
- Live market breadth (Advances/Declines).
- Categorized news feeds (Indian, Global, Geopolitical).

#### 4.2 HFT Decision Engine
- AI-based predictions for Intraday, Swing, and Monthly timeframes.
- "Live Best 10 Trades" algorithm based on conviction scores.
- Automated backtesting statistics for selected symbols.

#### 4.3 AI Stocks Screener
- Full F&O universe scanning for momentum and technical breakouts.
- Intelligence-based justification for every scan result.
- Integrated winning probability scoring.

#### 4.4 Advanced Drilldown & History
- Multi-timeframe historical data viewer (Daily, Weekly, Monthly, Yearly).
- Deep-dive options analysis including strike-level PCR and strategy feasibility.

### 5. Non-Functional Requirements
- **Performance:** Sub-second UI response time during market scans.
- **Reliability:** Stable connection to SQL Server and Market APIs.
- **Usability:** High-density, professional dark-mode interface.
