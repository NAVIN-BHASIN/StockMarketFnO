# HFT Decision Terminal & AI Intelligence Engine
## Professional Hedge Fund Trading Terminal

![License](https://img.shields.io/badge/License-Proprietary-blue.svg)
![Python](https://img.shields.io/badge/Python-3.9+-green.svg)
![Framework](https://img.shields.io/badge/UI-CustomTkinter-blue.svg)

### 🚀 Overview
The **HFT Decision Terminal** is a high-performance, institutional-grade analytics platform designed for professional traders. It integrates real-time market data, deep Open Interest (OI) analysis, and AI-driven predictive modeling to identify high-conviction trade setups in the F&O segment.

### 📂 Professional Documentation (SDLC)
We follow a world-class Software Development Life Cycle (SDLC) process. Detailed documentation can be found in the `docs/` directory:

1.  **[Business Requirements Document (BRD)](docs/BRD.md)** - Project objectives, stakeholders, and functional scope.
2.  **[Architecture & Design](docs/Architecture_and_Design.md)** - Technical stack, system components, and data flow.
3.  **[Application Flow](docs/Application_Flow.md)** - User journey and internal logic paths.
4.  **[Features Guide](docs/Features_Guide.md)** - Deep dive into terminal capabilities and AI tools.

### ✨ Key Features
- **AI Stocks Screener:** Multi-dimensional scanning of 180+ F&O stocks.
- **HFT Decision Engine:** Conviction-based trade signals and "Must-Trade" alerts.
- **Advanced Options Intelligence:** Strike-level PCR and strategy feasibility analysis.
- **Historical Data Terminal:** Multi-timeframe (D/W/M/Y) OHLCV viewer with professional resampling.

### 🛠️ Installation & Setup
1. **Clone the repository:**
   ```bash
   git clone https://github.com/NAVIN-BHASIN/StockMarketFnO.git
   ```
2. **Setup Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
4. **Database Configuration:**
   Ensure your SQL Server instance is running and update `db_utils.py` with your credentials.

---
*Proprietary Intelligence developed for Professional Trading Desks.*
