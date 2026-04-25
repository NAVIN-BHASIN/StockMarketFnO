# Design and Architecture Document
## System: HFT Decision Terminal

### 1. Architectural Overview
The application follows a **Model-View-Controller (MVC)** inspired architecture, built on a modular Python foundation. It is designed for high-concurrency data fetching and real-time UI updates.

### 2. Technology Stack
- **Frontend:** CustomTkinter (Professional UI framework), TkSheet (High-performance data grids).
- **Backend:** Python 3.x.
- **Data Analysis:** Pandas, NumPy, Scikit-Learn (RandomForest for AI predictions).
- **Visualization:** Matplotlib with Tkinter integration.
- **Data Source:** YFinance, custom MarketAPI (JSON-based), SQL Server (BhavCopy storage).

### 3. Component Design
#### 3.1 Data Layer (`db_utils.py`)
- `DatabaseHelper`: Centralized class for all SQL Server interactions. Handles historical data retrieval, ML feature extraction, and symbol metadata.
- Connection pooling is managed to ensure thread-safe operations.

#### 3.2 Live Feed Layer (`market_api.py`)
- `MarketAPI`: Encapsulates all external API calls. Provides live spot prices, index components, and global market news.

#### 3.3 Intelligence Engine (`main.py`)
- `HedgeFundEngineFrame`: The core logic layer that processes live data through the "HF Algorithm" to generate conviction scores.
- `AI Stocks Screener`: Background thread-based scanner that processes the entire F&O universe.

#### 3.4 Reusable UI Components
- `HistoricalDataViewer`: A standard component for multi-timeframe OHLCV visualization.
- `Best10DrilldownWindow`: Specialized drilldown for OI and technical analysis.

### 4. Data Flow
1. **Trigger:** User interaction or background timer.
2. **Fetch:** `MarketAPI` fetches live data; `db_utils` fetches historical context.
3. **Process:** Data is pushed through technical indicator calculators and AI models.
4. **Render:** Cleaned data is presented in color-coded `Sheet` or `Treeview` components.

### 5. Security & Stability
- Thread-safe background tasks to prevent UI freezing.
- Error handling at every API/DB gateway to ensure terminal uptime.
