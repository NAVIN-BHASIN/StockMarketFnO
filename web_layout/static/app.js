const WS_URL_HYPERLIQUID = 'wss://api.hyperliquid.xyz/ws';

class ChartPane {
    constructor(containerElement, id) {
        this.container = containerElement;
        this.id = id;
        
        // Setup UI references
        this.brokerSelect = this.container.querySelector('.broker-select');
        this.symbolInput = this.container.querySelector('.symbol-input');
        this.timeframeSelect = this.container.querySelector('.timeframe-select');
        this.loadBtn = this.container.querySelector('.load-btn');
        this.chartContainer = this.container.querySelector('.chart-container');
        
        this.tickerSymbol = this.container.querySelector('.ticker-symbol');
        this.tickerPrice = this.container.querySelector('.ticker-price');
        this.tickerBar = this.container.querySelector('.ticker-bar');
        
        // Plotly uses a string div ID, so we need to assign unique IDs
        this.chartDivId = `plotly-chart-${this.id}`;
        this.chartContainer.innerHTML = `<div id="${this.chartDivId}" style="width:100%; height:100%;"></div>`;
        
        this.ws = null;
        this.pollInterval = null;
        this.lastPrice = 0;
        this.historicalData = [];
        
        this.initChart();
        this.attachEvents();
    }
    
    initChart() {
        // Initial empty plot
        const layout = {
            plot_bgcolor: '#131722',
            paper_bgcolor: '#131722',
            font: { color: '#d1d4dc' },
            margin: { l: 40, r: 40, t: 10, b: 20 },
            xaxis: {
                showgrid: true,
                gridcolor: '#2a2e39',
                rangeslider: { visible: false }
            },
            yaxis: {
                showgrid: true,
                gridcolor: '#2a2e39',
            }
        };
        
        Plotly.newPlot(this.chartDivId, [], layout, {responsive: true, displayModeBar: false});
    }
    
    attachEvents() {
        this.loadBtn.addEventListener('click', () => this.loadData());
        
        // Enter key to load
        this.symbolInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.loadData();
        });
    }
    
    async loadData() {
        const broker = this.brokerSelect.value;
        const symbol = this.symbolInput.value.trim().toUpperCase();
        const timeframe = this.timeframeSelect.value;
        
        if (!symbol) return;
        
        this.tickerSymbol.textContent = symbol;
        this.cleanupLiveFeeds();
        
        // Fetch Historical Data from Backend
        try {
            const res = await fetch(`/api/historical?broker=${broker}&symbol=${symbol}&timeframe=${timeframe}`);
            const data = await res.json();
            
            if (data && data.length > 0) {
                // Ensure data is sorted by time and unique
                this.historicalData = data.sort((a, b) => a.time - b.time);
                
                const dates = this.historicalData.map(d => new Date(d.time * 1000));
                const opens = this.historicalData.map(d => d.open);
                const highs = this.historicalData.map(d => d.high);
                const lows = this.historicalData.map(d => d.low);
                const closes = this.historicalData.map(d => d.close);
                
                const trace = {
                    x: dates,
                    open: opens,
                    high: highs,
                    low: lows,
                    close: closes,
                    type: 'candlestick',
                    xaxis: 'x',
                    yaxis: 'y',
                    increasing: {line: {color: '#00E676'}},
                    decreasing: {line: {color: '#FF1744'}}
                };
                
                const layout = {
                    plot_bgcolor: '#131722',
                    paper_bgcolor: '#131722',
                    font: { color: '#d1d4dc' },
                    margin: { l: 40, r: 40, t: 10, b: 20 },
                    xaxis: {
                        showgrid: true,
                        gridcolor: '#2a2e39',
                        rangeslider: { visible: false }
                    },
                    yaxis: {
                        showgrid: true,
                        gridcolor: '#2a2e39',
                    }
                };

                Plotly.react(this.chartDivId, [trace], layout, {responsive: true, displayModeBar: false});
                
                this.lastPrice = this.historicalData[this.historicalData.length - 1].close;
                this.updateTickerPrice(this.lastPrice);
            } else {
                this.historicalData = [];
                Plotly.react(this.chartDivId, [], {}, {responsive: true, displayModeBar: false});
                this.updateTickerPrice(0);
            }
        } catch (e) {
            console.error("Error loading historical data:", e);
        }
        
        // Setup Live Feed
        if (broker === 'hyperliquid') {
            this.setupHyperliquidWS(symbol);
        } else if (broker === 'yfinance') {
            this.setupYFinancePolling(symbol);
        }
    }
    
    cleanupLiveFeeds() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
    
    setupHyperliquidWS(symbol) {
        this.ws = new WebSocket(WS_URL_HYPERLIQUID);
        
        this.ws.onopen = () => {
            const msg = {
                "method": "subscribe",
                "subscription": { "type": "trades", "coin": symbol }
            };
            this.ws.send(JSON.stringify(msg));
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            if (data.channel === "trades" && data.data && data.data.length > 0) {
                const latestTrade = data.data[data.data.length - 1];
                const price = parseFloat(latestTrade.px);
                this.handleLiveTick(price);
            }
        };
        
        this.ws.onerror = (e) => console.error("Hyperliquid WS Error:", e);
    }
    
    setupYFinancePolling(symbol) {
        this.pollInterval = setInterval(async () => {
            try {
                const res = await fetch(`/api/quote?symbol=${symbol}`);
                const data = await res.json();
                if (data.price) {
                    this.handleLiveTick(data.price);
                }
            } catch (e) {}
        }, 5000);
    }
    
    handleLiveTick(price) {
        if (price === this.lastPrice) return;
        
        const isUp = price > this.lastPrice;
        this.lastPrice = price;
        
        this.updateTickerPrice(price);
        this.flashTicker(isUp);
        
        if (this.historicalData.length > 0) {
            // Update last candle in historicalData
            let lastCandle = this.historicalData[this.historicalData.length - 1];
            lastCandle.close = price;
            lastCandle.high = Math.max(lastCandle.high, price);
            lastCandle.low = Math.min(lastCandle.low, price);
            
            // Re-render plotly chart
            // For optimal performance, we could use Plotly.extendTraces or restyle,
            // but react is robust enough for simple grid dashboards
            const dates = this.historicalData.map(d => new Date(d.time * 1000));
            const opens = this.historicalData.map(d => d.open);
            const highs = this.historicalData.map(d => d.high);
            const lows = this.historicalData.map(d => d.low);
            const closes = this.historicalData.map(d => d.close);
            
            const update = {
                x: [dates],
                open: [opens],
                high: [highs],
                low: [lows],
                close: [closes]
            };
            
            Plotly.update(this.chartDivId, update);
        }
    }
    
    updateTickerPrice(price) {
        this.tickerPrice.textContent = price.toFixed(2);
    }
    
    flashTicker(isUp) {
        this.tickerBar.classList.remove('flash-green', 'flash-red');
        void this.tickerBar.offsetWidth; 
        this.tickerBar.classList.add(isUp ? 'flash-green' : 'flash-red');
        
        setTimeout(() => {
            this.tickerBar.classList.remove('flash-green', 'flash-red');
        }, 300);
    }
}

// Layout Management
const gridContainer = document.getElementById('grid-container');
const chartCountSelect = document.getElementById('chart-count');
const paneTemplate = document.getElementById('pane-template');

let panes = [];

function initLayout() {
    const savedCount = localStorage.getItem('chartCount') || '4';
    chartCountSelect.value = savedCount;
    
    chartCountSelect.addEventListener('change', (e) => {
        const count = parseInt(e.target.value);
        localStorage.setItem('chartCount', count);
        renderGrid(count);
    });
    
    renderGrid(parseInt(savedCount));
}

function renderGrid(count) {
    // Clean up old
    panes.forEach(p => p.cleanupLiveFeeds());
    panes = [];
    gridContainer.innerHTML = '';
    
    // Update grid CSS class
    gridContainer.className = `grid-layout-${count}`;
    
    for (let i = 0; i < count; i++) {
        const paneNode = paneTemplate.content.cloneNode(true);
        const paneDiv = paneNode.querySelector('.chart-pane');
        gridContainer.appendChild(paneNode);
        
        const pane = new ChartPane(paneDiv, i);
        panes.push(pane);
        
        if (i === 0) {
            pane.brokerSelect.value = 'yfinance';
            pane.symbolInput.value = 'RELIANCE';
        } else if (i === 1) {
            pane.brokerSelect.value = 'yfinance';
            pane.symbolInput.value = 'TCS';
        } else if (i === 2) {
            pane.brokerSelect.value = 'yfinance';
            pane.symbolInput.value = 'INFY';
        } else if (i === 3) {
            pane.brokerSelect.value = 'yfinance';
            pane.symbolInput.value = 'HDFCBANK';
        }
        
        setTimeout(() => pane.loadData(), 100);
    }
}

// Start
document.addEventListener('DOMContentLoaded', () => {
    initLayout();
});


