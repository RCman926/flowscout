import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import asyncio

class OptionsSignalGenerator:
    def __init__(self):
        self.risk_levels = {
            'conservative': {'stop_loss': 0.25, 'take_profit': 0.50, 'max_risk': 0.02},
            'moderate': {'stop_loss': 0.35, 'take_profit': 0.75, 'max_risk': 0.05},
            'aggressive': {'stop_loss': 0.50, 'take_profit': 1.00, 'max_risk': 0.10}
        }
        
    def generate_options_signal(self, symbol, current_price, predicted_price, indicators, confidence):
        """Generate detailed options trading signal with specific pricing"""
        try:
            signal_type = self._determine_signal_type(current_price, predicted_price, indicators, confidence)
            
            if signal_type == "NO_TRADE":
                return {
                    'signal': 'NO_TRADE',
                    'confidence': confidence,
                    'reason': 'Insufficient confidence or conflicting indicators'
                }
            
            # Calculate strike prices
            strikes = self._calculate_strike_prices(current_price, signal_type)
            
            # Get expiry recommendations
            expiry_dates = self._get_expiry_recommendations(signal_type)
            
            # Calculate premium estimates and targets
            premium_data = self._estimate_option_premiums(current_price, strikes, expiry_dates, indicators)
            
            # Risk management levels
            risk_targets = self._calculate_risk_targets(premium_data, signal_type)
            
            return {
                'signal': signal_type,
                'confidence': confidence,
                'stock_price': current_price,
                'predicted_price': predicted_price,
                'strikes': strikes,
                'expiry_dates': expiry_dates,
                'premium_estimates': premium_data,
                'risk_targets': risk_targets,
                'position_sizing': self._calculate_position_sizing(current_price),
                'reasoning': self._generate_reasoning(current_price, predicted_price, indicators, signal_type)
            }
            
        except Exception as e:
            print(f"Options signal generation error: {e}")
            return {'signal': 'ERROR', 'error': str(e)}
    
    def _determine_signal_type(self, current_price, predicted_price, indicators, confidence):
        """Determine if signal is BUY_CALL, BUY_PUT, or NO_TRADE"""
        try:
            price_change_pct = (predicted_price - current_price) / current_price
            
            # Minimum confidence threshold
            if confidence < 0.01:  # 1% minimum
                return "NO_TRADE"
            
            # Technical confirmation
            rsi = indicators.get('rsi', 50)
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            bb_percent = indicators.get('bb_percent', 50)
            
            # Bullish conditions for calls
            if price_change_pct > 0.005:  # At least 0.5% predicted increase
                bullish_score = 0
                if rsi < 70: bullish_score += 1  # Not overbought
                if macd > macd_signal: bullish_score += 1  # MACD bullish
                if bb_percent < 80: bullish_score += 1  # Not at upper BB
                if price_change_pct > 0.02: bullish_score += 1  # Strong prediction
                
                if bullish_score >= 3:
                    return "BUY_CALL"
            
            # Bearish conditions for puts
            elif price_change_pct < -0.005:  # At least 0.5% predicted decrease
                bearish_score = 0
                if rsi > 30: bearish_score += 1  # Not oversold
                if macd < macd_signal: bearish_score += 1  # MACD bearish
                if bb_percent > 20: bearish_score += 1  # Not at lower BB
                if price_change_pct < -0.02: bearish_score += 1  # Strong prediction
                
                if bearish_score >= 3:
                    return "BUY_PUT"
            
            return "NO_TRADE"
            
        except Exception as e:
            print(f"Signal determination error: {e}")
            return "NO_TRADE"
    
    def _calculate_strike_prices(self, current_price, signal_type):
        """Calculate recommended strike prices"""
        try:
            if signal_type == "BUY_CALL":
                # For calls: ITM, ATM, and OTM strikes
                return {
                    'primary': round(current_price + 5, 0),  # Slightly OTM
                    'conservative': round(current_price, 0),  # ATM
                    'aggressive': round(current_price + 10, 0),  # More OTM
                    'itm': round(current_price - 5, 0)  # ITM
                }
            elif signal_type == "BUY_PUT":
                # For puts: ITM, ATM, and OTM strikes
                return {
                    'primary': round(current_price - 5, 0),  # Slightly OTM
                    'conservative': round(current_price, 0),  # ATM
                    'aggressive': round(current_price - 10, 0),  # More OTM
                    'itm': round(current_price + 5, 0)  # ITM
                }
            else:
                return {}
                
        except Exception as e:
            print(f"Strike calculation error: {e}")
            return {}
    
    def _get_expiry_recommendations(self, signal_type):
        """Get recommended expiry dates"""
        try:
            today = datetime.now()
            
            # Calculate common expiry dates
            weekly_expiry = today + timedelta(days=7 - today.weekday() + 4)  # Next Friday
            monthly_expiry = today + timedelta(days=30)
            earnings_expiry = today + timedelta(days=14)  # 2 weeks for earnings plays
            
            return {
                'weekly': weekly_expiry.strftime('%Y-%m-%d'),
                'monthly': monthly_expiry.strftime('%Y-%m-%d'), 
                'earnings': earnings_expiry.strftime('%Y-%m-%d'),
                'recommended': weekly_expiry.strftime('%Y-%m-%d')  # Default to weekly for most trades
            }
            
        except Exception as e:
            print(f"Expiry calculation error: {e}")
            return {}
    
    def _estimate_option_premiums(self, stock_price, strikes, expiry_dates, indicators):
        """Estimate option premiums and pricing targets"""
        try:
            # Simplified premium estimation based on IV and time decay
            iv = indicators.get('implied_volatility', 0.25)  # Default 25% IV
            
            premiums = {}
            
            for strike_type, strike_price in strikes.items():
                if strike_price <= 0:
                    continue
                    
                # Calculate moneyness
                moneyness = strike_price / stock_price
                
                # Estimate premium based on moneyness and IV
                if strike_type in ['primary', 'conservative']:
                    # For ATM/near ATM options
                    if 0.95 <= moneyness <= 1.05:  # ATM
                        estimated_premium = stock_price * iv * 0.1  # Rough estimate
                    elif moneyness > 1.05:  # OTM calls
                        estimated_premium = stock_price * iv * 0.05
                    else:  # ITM calls
                        estimated_premium = stock_price * iv * 0.15
                    
                    premiums[strike_type] = {
                        'strike': strike_price,
                        'estimated_premium': round(estimated_premium, 2),
                        'entry_target': round(estimated_premium * 0.95, 2),  # Buy 5% below estimate
                        'conservative_exit': round(estimated_premium * 1.5, 2),  # 50% profit
                        'moderate_exit': round(estimated_premium * 2.0, 2),  # 100% profit
                        'aggressive_exit': round(estimated_premium * 3.0, 2),  # 200% profit
                        'stop_loss': round(estimated_premium * 0.5, 2)  # 50% loss
                    }
                    
            return premiums
            
        except Exception as e:
            print(f"Premium estimation error: {e}")
            return {}
    
    def _calculate_risk_targets(self, premium_data, signal_type):
        """Calculate risk management targets"""
        try:
            risk_targets = {}
            
            for risk_level, params in self.risk_levels.items():
                risk_targets[risk_level] = {
                    'max_loss_pct': params['stop_loss'],
                    'target_profit_pct': params['take_profit'],
                    'position_size_pct': params['max_risk'],
                    'description': f"{risk_level.title()} - Stop: {params['stop_loss']:.0%}, Target: {params['take_profit']:.0%}"
                }
            
            return risk_targets
            
        except Exception as e:
            print(f"Risk targets calculation error: {e}")
            return {}
    
    def _calculate_position_sizing(self, stock_price):
        """Calculate position sizing recommendations"""
        try:
            # Account size assumptions for different risk levels
            account_sizes = [1000, 5000, 10000, 25000, 50000]
            
            position_sizing = {}
            
            for account_size in account_sizes:
                for risk_level, params in self.risk_levels.items():
                    max_risk_amount = account_size * params['max_risk']
                    
                    # Estimate contracts based on premium (using $2 average premium)
                    avg_premium = 2.0
                    max_contracts = int(max_risk_amount / (avg_premium * 100))
                    
                    if account_size not in position_sizing:
                        position_sizing[account_size] = {}
                    
                    position_sizing[account_size][risk_level] = {
                        'max_risk_amount': max_risk_amount,
                        'suggested_contracts': max(1, max_contracts),
                        'max_premium_per_contract': round(max_risk_amount / max(1, max_contracts) / 100, 2)
                    }
            
            return position_sizing
            
        except Exception as e:
            print(f"Position sizing error: {e}")
            return {}
    
    def _generate_reasoning(self, current_price, predicted_price, indicators, signal_type):
        """Generate reasoning for the signal"""
        try:
            price_change = predicted_price - current_price
            price_change_pct = (price_change / current_price) * 100
            
            reasoning = []
            
            # Price prediction reasoning
            if signal_type == "BUY_CALL":
                reasoning.append(f"AI predicts {price_change_pct:+.2f}% price increase to ${predicted_price:.2f}")
            elif signal_type == "BUY_PUT":
                reasoning.append(f"AI predicts {price_change_pct:+.2f}% price decrease to ${predicted_price:.2f}")
            
            # Technical reasoning
            rsi = indicators.get('rsi', 50)
            if rsi > 70:
                reasoning.append(f"RSI overbought at {rsi:.1f}")
            elif rsi < 30:
                reasoning.append(f"RSI oversold at {rsi:.1f}")
            else:
                reasoning.append(f"RSI neutral at {rsi:.1f}")
            
            # MACD reasoning
            macd = indicators.get('macd', 0)
            macd_signal = indicators.get('macd_signal', 0)
            if macd > macd_signal:
                reasoning.append("MACD showing bullish momentum")
            else:
                reasoning.append("MACD showing bearish momentum")
            
            return " • ".join(reasoning)
            
        except Exception as e:
            print(f"Reasoning generation error: {e}")
            return "Technical analysis suggests this trade setup"
    
    def format_signal_display(self, signal_data):
        """Format signal data for display"""
        try:
            if signal_data.get('signal') in ['NO_TRADE', 'ERROR']:
                return signal_data
            
            # Create formatted display
            formatted = {
                'header': f"📊 {signal_data['signal']} Signal",
                'confidence': f"Confidence: {signal_data['confidence']:.1%}",
                'current_price': f"Current Price: ${signal_data['stock_price']:.2f}",
                'target_price': f"Target Price: ${signal_data['predicted_price']:.2f}",
                'reasoning': signal_data['reasoning']
            }
            
            # Add strike and premium information
            if 'primary' in signal_data.get('premium_estimates', {}):
                primary = signal_data['premium_estimates']['primary']
                formatted['primary_trade'] = {
                    'strike': f"Strike: ${primary['strike']:.0f}",
                    'entry': f"Entry: ${primary['entry_target']:.2f}",
                    'targets': f"Targets: ${primary['conservative_exit']:.2f} / ${primary['moderate_exit']:.2f} / ${primary['aggressive_exit']:.2f}",
                    'stop_loss': f"Stop Loss: ${primary['stop_loss']:.2f}"
                }
            
            return formatted
            
        except Exception as e:
            print(f"Signal formatting error: {e}")
            return signal_data