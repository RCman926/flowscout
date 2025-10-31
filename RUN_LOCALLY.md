# How to Run This App Locally with IBKR

## Step 1: Download the Code
From Replit, download all files to your desktop (or use `git clone` if you have git)

## Step 2: Install Dependencies
Open PowerShell in the project folder:
```powershell
pip install streamlit yfinance pandas numpy plotly ta-lib-easy scikit-learn ibapi
```

## Step 3: Start TWS/IB Gateway
- Open TWS or IB Gateway on your desktop
- Enable API connections (Configuration → API → Settings)
- Note the port (usually 7497 for TWS Live, 4001 for Gateway Live)

## Step 4: Run the App
In PowerShell:
```powershell
streamlit run app.py --server.port 5000
```

## Step 5: Open in Browser
Browser will auto-open to: http://localhost:5000

Now IBKR will connect because TWS and the app are both on your desktop!
