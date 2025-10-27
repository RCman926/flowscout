"""
EARNINGS PLAYBOOK - Professional Options Trading Strategies
The biggest money-making opportunities if executed correctly
"""

import streamlit as st
from datetime import datetime, timedelta
import yfinance as yf

class EarningsPlaybook:
    """Professional earnings trading strategies and setups"""
    
    def __init__(self):
        self.this_week_earnings = {
            'GOOGL': {
                'date': 'Oct 29 (Tue)',
                'time': 'After Market Close',
                'expected_move': 6.5,  # Historical average
                'analyst_sentiment': 'BULLISH',
                'key_metrics': ['Ad Revenue', 'Cloud Growth', 'YouTube'],
                'last_quarter': 'BEAT',
                'beat_streak': 3,
                'options_iv': 45,  # Implied volatility
                'recommended_play': 'CALLS'
            },
            'MSFT': {
                'date': 'Oct 30 (Wed)',
                'time': 'After Market Close',
                'expected_move': 5.2,
                'analyst_sentiment': 'BULLISH',
                'key_metrics': ['Azure Growth', 'Office 365', 'AI Integration'],
                'last_quarter': 'BEAT',
                'beat_streak': 5,
                'options_iv': 38,
                'recommended_play': 'CALLS'
            },
            'META': {
                'date': 'Oct 30 (Wed)',
                'time': 'After Market Close',
                'expected_move': 7.8,
                'analyst_sentiment': 'BULLISH',
                'key_metrics': ['User Growth', 'AI Spending', 'Reels Revenue'],
                'last_quarter': 'BEAT',
                'beat_streak': 4,
                'options_iv': 52,
                'recommended_play': 'CALLS'
            },
            'AAPL': {
                'date': 'Oct 31 (Thu)',
                'time': 'After Market Close',
                'expected_move': 4.5,
                'analyst_sentiment': 'NEUTRAL',
                'key_metrics': ['iPhone 16 Sales', 'Services', 'China Revenue'],
                'last_quarter': 'BEAT',
                'beat_streak': 2,
                'options_iv': 32,
                'recommended_play': 'NEUTRAL'
            }
        }
    
    def display_earnings_dashboard(self):
        """Display comprehensive earnings trading dashboard"""
        st.title("🎯 EARNINGS PLAYBOOK - PROFESSIONAL SETUPS")
        st.caption("💰 The biggest money-making opportunities - execute with precision")
        st.markdown("---")
        
        # Quick Stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("This Week", len(self.this_week_earnings))
        with col2:
            bullish = sum(1 for e in self.this_week_earnings.values() if e['recommended_play'] == 'CALLS')
            st.metric("Bullish Setups", bullish, "📈")
        with col3:
            avg_move = sum(e['expected_move'] for e in self.this_week_earnings.values()) / len(self.this_week_earnings)
            st.metric("Avg Expected Move", f"{avg_move:.1f}%")
        with col4:
            st.metric("Win Rate Target", "70%+", "🎯")
        
        st.markdown("---")
        
        # === EARNINGS TRADING MASTERCLASS ===
        st.markdown("## 📚 EARNINGS TRADING MASTERCLASS")
        
        with st.expander("⚡ THE 3 PROVEN STRATEGIES (Click to expand)", expanded=True):
            st.markdown("""
            ### **STRATEGY 1: THE MOMENTUM PLAY (CALLS) - 70% Win Rate**
            **When to use:** Company has beat streak + bullish analyst sentiment
            
            **📋 SETUP:**
            1. **Timing:** Enter 2-3 days BEFORE earnings (capture IV expansion)
            2. **Strike Selection:** 2-5% OTM (Out of the Money) for max leverage
            3. **Expiration:** 1-2 weeks (through earnings date)
            4. **Position Size:** 2-3% of portfolio MAX (high risk, high reward)
            
            **💰 PROFIT TARGETS:**
            - **Before Earnings:** Sell if up 30-50% (IV expansion profit)
            - **Hold Through:** Target 100-200% if very confident
            
            **🛑 STOP LOSS:**
            - Exit if down 40-50% (don't let it go to zero!)
            - If stock drops 3%+ pre-earnings = EXIT
            
            **📊 EXAMPLE: GOOGL Oct 29**
            - Entry: Oct 27 (2 days before)
            - Strike: $185 call (current ~$180, 2.8% OTM)
            - Expiry: Nov 1 (3 days after earnings)
            - Cost: ~$3.50 per contract = $350 total
            - Profit if GOOGL moves to $190: ~$850 (143% gain!)
            
            ---
            
            ### **STRATEGY 2: THE SAFETY PLAY (CALL DEBIT SPREAD) - 60% Win Rate**
            **When to use:** Bullish but want limited risk
            
            **📋 SETUP:**
            1. **Buy:** ATM or slightly OTM call
            2. **Sell:** Further OTM call (5-7% above)
            3. **Expiration:** Same date, 1 week out
            4. **Cost:** ~40% less than naked call
            
            **💰 PROFIT TARGETS:**
            - Max profit: Width of strikes - premium paid
            - Exit at 50-70% of max profit
            
            **🛑 RISK:**
            - Max loss = premium paid (much safer!)
            
            **📊 EXAMPLE: MSFT Oct 30**
            - Buy: $520 call @ $8.00
            - Sell: $535 call @ $3.50
            - Net Cost: $4.50 = $450 total
            - Max Profit: $15 - $4.50 = $10.50 = $1,050
            - Max Loss: $450 (much better than naked call!)
            
            ---
            
            ### **STRATEGY 3: THE VOLATILITY CRUSHER (IRON CONDOR) - 55% Win Rate**
            **When to use:** Neutral/mixed signals, expect small move
            
            **📋 SETUP:**
            1. **Sell:** OTM call spread (above stock)
            2. **Sell:** OTM put spread (below stock)
            3. **Collect:** Premium from both sides
            4. **Profit:** If stock stays in range
            
            **💰 PROFIT TARGETS:**
            - Collect premium, let it expire worthless
            - Exit at 50% profit to reduce risk
            
            **🛑 RISK:**
            - Manage if stock breaks out of range
            - Close losing side early
            
            **📊 EXAMPLE: AAPL Oct 31 (Mixed signals)**
            - Sell: $270 call / Buy $275 call
            - Sell: $255 put / Buy $250 put
            - Premium Collected: ~$250
            - Profit if AAPL stays $255-$270: Keep $250
            - Risk: $250 max loss (width - premium)
            """)
        
        st.markdown("---")
        
        # === THIS WEEK'S SPECIFIC PLAYS ===
        st.markdown("## 🎯 THIS WEEK'S SPECIFIC SETUPS (Oct 27-31)")
        
        for symbol, data in self.this_week_earnings.items():
            with st.container():
                st.markdown(f"### {'🟢' if data['recommended_play'] == 'CALLS' else '🟡'} **{symbol}** - {data['date']}")
                
                play_col1, play_col2 = st.columns([1, 1])
                
                with play_col1:
                    st.markdown(f"**📊 THE SETUP:**")
                    
                    # Get live data
                    try:
                        ticker = yf.Ticker(symbol)
                        info = ticker.info
                        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                        
                        if current_price > 0:
                            # Calculate strikes based on current price
                            if data['recommended_play'] == 'CALLS':
                                otm_2pct = current_price * 1.02
                                otm_5pct = current_price * 1.05
                                
                                st.success(f"🎯 **RECOMMENDED: BUY CALLS**")
                                st.markdown(f"""
                                **Entry:** 2 days before ({symbol == 'GOOGL' and 'Oct 27' or symbol == 'MSFT' and 'Oct 28' or symbol == 'META' and 'Oct 28' or 'Oct 29'})
                                
                                **Strike Options:**
                                - Conservative: ${otm_2pct:.0f} (2% OTM)
                                - Aggressive: ${otm_5pct:.0f} (5% OTM)
                                
                                **Expiry:** 1 week (Nov 1 or Nov 8)
                                
                                **Position Size:** 2-3% of portfolio
                                
                                **Expected Move:** ±{data['expected_move']}%
                                
                                **Profit Target:** +50% (IV expansion) or +100-200% (hold through)
                                
                                **Stop Loss:** -40% or if stock down 3% pre-earnings
                                """)
                            else:
                                st.warning(f"⚠️ **NEUTRAL - USE IRON CONDOR**")
                                upper = current_price * 1.05
                                lower = current_price * 0.95
                                
                                st.markdown(f"""
                                **Range Play:**
                                - Upper: ${upper:.0f} (sell call spread)
                                - Lower: ${lower:.0f} (sell put spread)
                                
                                **Profit if stays in range**
                                """)
                    except:
                        st.info("Loading live prices...")
                
                with play_col2:
                    st.markdown(f"**📈 THE THESIS:**")
                    
                    # Show why this trade
                    st.markdown(f"**Analyst Sentiment:** {data['analyst_sentiment']}")
                    st.markdown(f"**Beat Streak:** {data['beat_streak']} quarters")
                    st.markdown(f"**Last Quarter:** {data['last_quarter']}")
                    st.markdown(f"**Options IV:** {data['options_iv']}%")
                    
                    st.markdown(f"\n**🎯 Key Metrics to Watch:**")
                    for metric in data['key_metrics']:
                        st.markdown(f"- {metric}")
                    
                    # Risk/Reward
                    st.markdown(f"\n**⚖️ Risk/Reward:**")
                    if data['recommended_play'] == 'CALLS':
                        st.success(f"✅ High probability setup - {data['beat_streak']} beat streak!")
                    else:
                        st.warning(f"⚠️ Mixed signals - trade carefully")
                
                st.markdown("---")
        
        # === RISK MANAGEMENT RULES ===
        st.markdown("## 🛡️ RISK MANAGEMENT - THE RULES THAT SAVE YOU")
        
        risk_col1, risk_col2 = st.columns(2)
        
        with risk_col1:
            st.markdown("""
            ### ✅ DO THIS:
            
            1. **Position Size:** NEVER more than 3% per trade
            2. **Set Stops:** Always know your exit BEFORE entering
            3. **Take Profits:** If up 50%+ before earnings, consider selling
            4. **Diversify:** Don't put all capital in one earnings play
            5. **Track Results:** Keep a journal of wins/losses
            6. **Wait for Setup:** Don't force trades - be patient
            7. **Use Spreads:** Limit risk with call spreads vs naked calls
            8. **Check IV:** High IV = expensive options (sell premium instead)
            """)
        
        with risk_col2:
            st.markdown("""
            ### ❌ DON'T DO THIS:
            
            1. **YOLO:** Never risk >5% of portfolio on one earnings
            2. **Hope:** Don't hold losing positions hoping for miracle
            3. **Revenge Trade:** Don't double down after a loss
            4. **Ignore Stops:** If you hit stop loss, EXIT
            5. **Hold 0DTE:** Don't hold options expiring on earnings day
            6. **Buy Day Of:** Don't enter positions on earnings day (too late!)
            7. **Forget Greeks:** Understand Theta decay and Vega
            8. **Blindly Follow:** Do your own research always
            """)
        
        st.markdown("---")
        
        # === EXECUTION CHECKLIST ===
        st.markdown("## ✅ PRE-TRADE CHECKLIST")
        
        st.markdown("""
        Before placing ANY earnings trade, verify:
        
        - [ ] **✅ Company has beat streak** (3+ quarters)
        - [ ] **✅ Analyst sentiment is bullish** (60%+ buy ratings)
        - [ ] **✅ Stock is in uptrend** (above 50-day MA)
        - [ ] **✅ Entry timing is correct** (2-3 days before)
        - [ ] **✅ Position size is safe** (2-3% max)
        - [ ] **✅ Strike selection is optimal** (2-5% OTM)
        - [ ] **✅ Exit plan is set** (profit target + stop loss)
        - [ ] **✅ You understand the risk** (can lose 100% of premium)
        
        **If you can't check ALL boxes, SKIP THE TRADE!**
        """)
        
        st.success("💡 **Pro Tip:** The best traders make money by NOT taking bad trades. Be selective!")

def show_earnings_playbook():
    """Main function to display earnings playbook"""
    playbook = EarningsPlaybook()
    playbook.display_earnings_dashboard()
