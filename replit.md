# Overview

This is a comprehensive options trading platform built with Streamlit that provides real-time market data analysis, options pricing, technical indicators, and alert management. The platform integrates with Interactive Brokers (IBKR) API for live trading data and implements advanced options analytics including Greeks calculation, volatility analysis, and risk management tools. The system is designed for professional traders who need sophisticated analysis capabilities with a clean, intuitive interface.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Streamlit Web Application**: Single-page application with sidebar controls and main dashboard
- **Real-time Updates**: Session state management for persistent data across user interactions
- **Interactive Visualizations**: Plotly integration for dynamic charts and graphs
- **Responsive Layout**: Wide layout configuration with expandable sidebar for trading controls

## Backend Architecture
- **Modular Component Design**: Separation of concerns across multiple specialized modules
  - `options_engine.py`: Options pricing, Greeks calculation, and volatility analysis
  - `market_data.py`: Real-time and historical market data fetching
  - `technical_indicators.py`: Technical analysis calculations using TA-Lib
  - `alerts.py`: Multi-channel notification system
  - `utils.py`: Shared utility functions for formatting and calculations

## Data Processing
- **Options Pricing Models**: Black-Scholes implementation for theoretical pricing
- **Greeks Calculation**: Delta, Gamma, Theta, Vega, and Rho calculations
- **Technical Analysis**: RSI, MACD, Bollinger Bands, Stochastic oscillators, and volume indicators
- **Risk Management**: Position sizing, P&L tracking, and risk metrics

## Real-time Data Architecture
- **IBKR API Integration**: EClient/EWrapper pattern for live market data
- **Caching Strategy**: 30-second cache duration for API calls to reduce latency
- **Asynchronous Processing**: Async/await pattern for non-blocking data fetching
- **Error Handling**: Comprehensive error management with fallback mechanisms

## Alert System Architecture
- **Multi-channel Notifications**: Telegram bot integration and email alerts
- **Alert Cooldown**: Spam prevention with 5-minute cooldown periods
- **Alert History**: Logging and tracking of all sent notifications
- **Configurable Triggers**: Price-based and technical indicator-based alert conditions

# External Dependencies

## Multi-Broker Integration
- **Interactive Brokers (IBKR)**: Primary institutional-grade API with TWS/Gateway integration
- **TD Ameritrade**: REST API integration with real-time options data
- **Charles Schwab**: Professional trading platform integration
- **E*TRADE**: Retail broker API with options support
- **Fidelity**: Commission-free options trading integration
- **Robinhood**: Zero-commission retail platform
- **Webull**: Advanced charting and options flow data
- **Alpaca**: Stock trading API (no options support)
- **Unified Data Engine**: Aggregates data from all connected brokers with quality scoring

## Financial Data APIs
- **Interactive Brokers API (IBKR)**: Primary source for real-time options and stock data
- **Yahoo Finance (yfinance)**: Backup data source for historical price information
- **Connection Requirements**: Local TWS/IB Gateway running on localhost:7497

## Technical Analysis Libraries
- **TA-Lib**: Advanced technical indicator calculations
- **SciPy**: Statistical functions for options pricing and analysis
- **NumPy/Pandas**: Core data manipulation and numerical computing

## Visualization and UI
- **Streamlit**: Web application framework with auto-refresh capabilities
- **Plotly**: Interactive charting and visualization library

## Communication Services
- **Telegram Bot API**: Real-time alert delivery via Telegram
- **SMTP Email**: Email-based alert system with Gmail integration
- **Required Environment Variables**:
  - `TELEGRAM_BOT_TOKEN`: Bot authentication token
  - `SMTP_SERVER`, `SMTP_PORT`: Email server configuration
  - `SENDER_EMAIL`, `SENDER_PASSWORD`: Email credentials

## Social Trading Platform
- **Community Data Management**: JSON-based storage for community insights and social trading data
- **Signal Validation System**: Real-time tracking and validation of trading signals
- **Leaderboard System**: Performance ranking and trader verification
- **Copy Trading Integration**: Automated trader following and performance tracking

## Machine Learning (Planned)
- **TensorFlow/Keras**: Neural network models for price prediction
- **Scikit-learn**: Random Forest and preprocessing utilities
- **TextBlob**: Sentiment analysis for market news integration

## Development and Deployment
- **Python 3.8+**: Core runtime environment
- **asyncio**: Asynchronous programming support
- **Environment Variables**: Configuration management for API keys and credentials

# Recent Updates (August 2025)

## Multi-Broker Integration & Animated Market Mood (August 27, 2025)
- **Multi-Broker Integration**: Added comprehensive broker integration system supporting 8 major brokers (IBKR, TD Ameritrade, Schwab, E*TRADE, Fidelity, Robinhood, Webull, Alpaca)
- **Unified Data Aggregation**: Real-time data collection and aggregation from multiple broker sources with quality indicators
- **Broker Comparison Engine**: Automatic detection of best execution, lowest cost, and fastest data providers
- **Animated Market Mood Indicator**: Real-time animated gauge showing market sentiment with 5-component analysis (Technical, Flow, Sentiment, Volatility, Momentum)
- **Professional Mood Insights**: AI-generated trading insights based on current market mood (Extreme Fear to Extreme Greed scale)
- **Visual Mood History**: Animated timeline of market mood changes with component breakdowns

## Live Data Infrastructure Implementation (January 2025)
- **API Bypass System**: Comprehensive web scraping infrastructure to get LIVE data from Yahoo Finance website (bypassing 15-minute API delay)
- **Multi-Source Data Aggregation**: Real-time data from Yahoo Finance, MarketWatch, CNBC, and Bloomberg with quality indicators
- **Data Authentication Proof**: Clear indicators showing LIVE vs DELAYED vs FALLBACK status with source attribution
- **Cost-Effective Solution**: FREE real-time data solution vs institutional feeds costing $1,500-10,000/month
- **Professional Risk Management**: Balanced portfolio allocation across Conservative (40%), Moderate (35%), Aggressive (20%), and Speculation (5%) strategies

## Balanced Trading Strategy System
- **Conservative Income Strategies**: 70-80% win rate targeting 25-50% returns through covered calls and cash-secured puts
- **Moderate Growth Plays**: 50-60% win rate targeting 50-150% returns with near-ATM options
- **Aggressive Swing Trades**: 35-45% win rate targeting 200-500% returns with OTM positions
- **Speculation Plays**: 15-25% win rate targeting 500-2000% returns with far OTM lottery tickets
- **Professional Position Sizing**: Account-based allocation with realistic win rates and target returns

## Institutional-Grade Analytics Implementation
- **Gamma Exposure Engine**: Live GEX levels showing dealer positioning and gamma flip points for support/resistance identification
- **Institutional Flow Tracker**: Real-time detection of block trades (>100 contracts), sweep orders, and dark pool prints with sentiment analysis
- **Advanced Greeks Monitoring**: Portfolio-level Delta, Gamma, Theta, Vega analysis with risk assessment and time decay tracking
- **High-Profit Options Chain**: Comprehensive strike ladder with risk categorization from conservative to speculative
- **Enhanced Position Sizing**: Multi-tiered approach balancing steady income with high-growth opportunities

## Architecture Enhancements
- **Real-Time Data Infrastructure**: Live web scraping bypasses with fallback mechanisms and data quality validation
- **Professional Risk Management Module**: Comprehensive strategy generator across all risk levels with expected returns
- **Modular Analytics Engines**: Separated gamma exposure, flow tracking, and Greeks calculation into specialized modules
- **Beautiful UI Implementation**: Clean, professional interface with risk-level color coding and portfolio balance visualization