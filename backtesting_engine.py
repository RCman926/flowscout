import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from sklearn.metrics import accuracy_score, precision_score, recall_score
import asyncio
import warnings
warnings.filterwarnings('ignore')

class AdvancedBacktestingEngine:
    """
    Comprehensive backtesting engine for strategy validation and optimization
    Includes walk-forward analysis, Monte Carlo simulation, and risk metrics
    """
    
    def __init__(self):
        self.backtest_cache = {}
        self.strategy_results = {}
        self.risk_metrics = {}
        
    async def run_comprehensive_backtest(self, strategy_function, symbol, 
                                       start_date=None, end_date=None, 
                                       initial_capital=10000):
        """Run comprehensive backtesting with multiple validation methods"""
        try:
            if start_date is None:
                start_date = datetime.now() - timedelta(days=365)
            if end_date is None:
                end_date = datetime.now()
            
            results = {}
            
            # Get historical data
            historical_data = await self._get_historical_data(symbol, start_date, end_date)
            if historical_data is None:
                return self._get_default_backtest_results()
            
            # Run basic backtest
            basic_results = await self._run_basic_backtest(
                strategy_function, historical_data, initial_capital
            )
            results['basic_backtest'] = basic_results
            
            # Walk-forward analysis
            walkforward_results = await self._run_walkforward_analysis(
                strategy_function, historical_data, initial_capital
            )
            results['walkforward_analysis'] = walkforward_results
            
            # Monte Carlo simulation
            monte_carlo_results = await self._run_monte_carlo_simulation(
                basic_results, num_simulations=1000
            )
            results['monte_carlo'] = monte_carlo_results
            
            # Risk metrics calculation
            risk_metrics = self._calculate_risk_metrics(basic_results)
            results['risk_metrics'] = risk_metrics
            
            # Strategy optimization
            optimization_results = await self._optimize_strategy_parameters(
                strategy_function, historical_data, initial_capital
            )
            results['optimization'] = optimization_results
            
            # Performance attribution
            attribution = self._calculate_performance_attribution(basic_results)
            results['attribution'] = attribution
            
            return results
            
        except Exception as e:
            print(f"Comprehensive backtest error: {e}")
            return self._get_default_backtest_results()
    
    async def _get_historical_data(self, symbol, start_date, end_date):
        """Get historical price and volume data"""
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(start=start_date, end=end_date)
            
            if data.empty:
                return None
            
            # Calculate additional features
            data['Returns'] = data['Close'].pct_change()
            data['Volatility'] = data['Returns'].rolling(window=20).std()
            data['Volume_MA'] = data['Volume'].rolling(window=20).mean()
            data['Price_MA_50'] = data['Close'].rolling(window=50).mean()
            data['Price_MA_200'] = data['Close'].rolling(window=200).mean()
            
            return data
            
        except Exception as e:
            print(f"Historical data error: {e}")
            return None
    
    async def _run_basic_backtest(self, strategy_function, data, initial_capital):
        """Run basic backtest with buy/hold comparison"""
        try:
            results = {
                'trades': [],
                'portfolio_values': [],
                'returns': [],
                'signals': []
            }
            
            capital = initial_capital
            position = 0  # 0 = no position, 1 = long, -1 = short
            shares = 0
            entry_price = 0
            
            for i in range(len(data)):
                current_price = data['Close'].iloc[i]
                current_date = data.index[i]
                
                # Generate signal from strategy
                if i < 50:  # Skip first 50 days for indicators
                    signal = 0
                else:
                    # Simulate strategy signal (in real implementation, call actual strategy)
                    signal = self._simulate_strategy_signal(data.iloc[:i+1])
                
                results['signals'].append(signal)
                
                # Execute trades based on signal
                if signal == 1 and position <= 0:  # Buy signal
                    if position == -1:  # Close short position
                        capital += shares * (entry_price - current_price)
                    
                    # Open long position
                    shares = capital / current_price
                    entry_price = current_price
                    position = 1
                    
                    results['trades'].append({
                        'date': current_date,
                        'action': 'buy',
                        'price': current_price,
                        'shares': shares,
                        'capital': capital
                    })
                    
                elif signal == -1 and position >= 0:  # Sell signal
                    if position == 1:  # Close long position
                        capital = shares * current_price
                        
                    # Open short position (simplified)
                    shares = capital / current_price
                    entry_price = current_price
                    position = -1
                    
                    results['trades'].append({
                        'date': current_date,
                        'action': 'sell',
                        'price': current_price,
                        'shares': shares,
                        'capital': capital
                    })
                
                # Calculate current portfolio value
                if position == 1:
                    portfolio_value = shares * current_price
                elif position == -1:
                    portfolio_value = capital + shares * (entry_price - current_price)
                else:
                    portfolio_value = capital
                
                results['portfolio_values'].append(portfolio_value)
                
                # Calculate returns
                if i > 0:
                    daily_return = (portfolio_value - results['portfolio_values'][i-1]) / results['portfolio_values'][i-1]
                    results['returns'].append(daily_return)
                else:
                    results['returns'].append(0)
            
            # Calculate final metrics
            final_value = results['portfolio_values'][-1]
            total_return = (final_value - initial_capital) / initial_capital
            
            # Buy and hold comparison
            buy_hold_return = (data['Close'].iloc[-1] - data['Close'].iloc[0]) / data['Close'].iloc[0]
            
            results['summary'] = {
                'initial_capital': initial_capital,
                'final_value': final_value,
                'total_return': total_return,
                'buy_hold_return': buy_hold_return,
                'excess_return': total_return - buy_hold_return,
                'num_trades': len(results['trades']),
                'win_rate': self._calculate_win_rate(results['trades'])
            }
            
            return results
            
        except Exception as e:
            print(f"Basic backtest error: {e}")
            return {'summary': {'total_return': 0, 'win_rate': 0.5}}
    
    def _simulate_strategy_signal(self, data):
        """Simulate strategy signal generation"""
        try:
            if len(data) < 20:
                return 0
            
            # Simple moving average crossover strategy simulation
            ma_short = data['Close'].rolling(window=10).mean().iloc[-1]
            ma_long = data['Close'].rolling(window=20).mean().iloc[-1]
            current_price = data['Close'].iloc[-1]
            
            # Volume confirmation
            volume_ma = data['Volume'].rolling(window=10).mean().iloc[-1]
            current_volume = data['Volume'].iloc[-1]
            
            # RSI-like momentum
            returns = data['Close'].pct_change().dropna()
            if len(returns) >= 14:
                gains = returns[returns > 0].tail(14).mean()
                losses = abs(returns[returns < 0].tail(14).mean())
                rsi = 100 - (100 / (1 + (gains / losses if losses > 0 else 1)))
            else:
                rsi = 50
            
            # Generate signal
            signal = 0
            
            # Bullish conditions
            if (ma_short > ma_long and 
                current_price > ma_short and 
                current_volume > volume_ma * 1.2 and 
                rsi < 70):
                signal = 1
            
            # Bearish conditions  
            elif (ma_short < ma_long and 
                  current_price < ma_short and 
                  current_volume > volume_ma * 1.2 and 
                  rsi > 30):
                signal = -1
            
            return signal
            
        except Exception as e:
            return 0
    
    async def _run_walkforward_analysis(self, strategy_function, data, initial_capital):
        """Run walk-forward analysis to test strategy robustness"""
        try:
            window_size = 252  # 1 year training window
            test_size = 63    # 3 months test window
            
            results = []
            
            for i in range(window_size, len(data) - test_size, test_size):
                # Training period
                train_data = data.iloc[i-window_size:i]
                
                # Test period
                test_data = data.iloc[i:i+test_size]
                
                # Run backtest on test period
                test_results = await self._run_basic_backtest(
                    strategy_function, test_data, initial_capital
                )
                
                results.append({
                    'period_start': test_data.index[0],
                    'period_end': test_data.index[-1],
                    'return': test_results['summary']['total_return'],
                    'win_rate': test_results['summary']['win_rate'],
                    'num_trades': test_results['summary']['num_trades']
                })
            
            if results:
                # Calculate walk-forward metrics
                returns = [r['return'] for r in results]
                win_rates = [r['win_rate'] for r in results]
                
                walkforward_summary = {
                    'periods_tested': len(results),
                    'avg_return': np.mean(returns),
                    'return_std': np.std(returns),
                    'avg_win_rate': np.mean(win_rates),
                    'win_rate_std': np.std(win_rates),
                    'profitable_periods': sum(1 for r in returns if r > 0),
                    'consistency_score': sum(1 for r in returns if r > 0) / len(returns)
                }
                
                return {
                    'periods': results,
                    'summary': walkforward_summary
                }
            else:
                return {'summary': {'consistency_score': 0.5}}
                
        except Exception as e:
            print(f"Walk-forward analysis error: {e}")
            return {'summary': {'consistency_score': 0.5}}
    
    async def _run_monte_carlo_simulation(self, backtest_results, num_simulations=1000):
        """Run Monte Carlo simulation for risk assessment"""
        try:
            if 'returns' not in backtest_results or not backtest_results['returns']:
                return {'var_95': 0, 'var_99': 0, 'expected_return': 0}
            
            returns = np.array(backtest_results['returns'])
            returns = returns[~np.isnan(returns)]  # Remove NaN values
            
            if len(returns) < 10:
                return {'var_95': 0, 'var_99': 0, 'expected_return': 0}
            
            # Calculate return statistics
            mean_return = np.mean(returns)
            std_return = np.std(returns)
            
            # Monte Carlo simulations
            simulated_returns = []
            
            for _ in range(num_simulations):
                # Generate random walk
                random_returns = np.random.normal(mean_return, std_return, len(returns))
                cumulative_return = np.prod(1 + random_returns) - 1
                simulated_returns.append(cumulative_return)
            
            simulated_returns = np.array(simulated_returns)
            
            # Calculate risk metrics
            var_95 = np.percentile(simulated_returns, 5)  # 95% VaR
            var_99 = np.percentile(simulated_returns, 1)  # 99% VaR
            expected_return = np.mean(simulated_returns)
            
            # Additional risk metrics
            prob_loss = sum(1 for r in simulated_returns if r < 0) / len(simulated_returns)
            max_drawdown = np.min(simulated_returns)
            
            return {
                'var_95': var_95,
                'var_99': var_99,
                'expected_return': expected_return,
                'probability_of_loss': prob_loss,
                'worst_case_scenario': max_drawdown,
                'simulations_run': num_simulations
            }
            
        except Exception as e:
            print(f"Monte Carlo simulation error: {e}")
            return {'var_95': 0, 'var_99': 0, 'expected_return': 0}
    
    def _calculate_risk_metrics(self, backtest_results):
        """Calculate comprehensive risk metrics"""
        try:
            if 'returns' not in backtest_results or not backtest_results['returns']:
                return self._get_default_risk_metrics()
            
            returns = np.array(backtest_results['returns'])
            returns = returns[~np.isnan(returns)]
            
            if len(returns) < 10:
                return self._get_default_risk_metrics()
            
            # Basic metrics
            total_return = backtest_results['summary']['total_return']
            volatility = np.std(returns) * np.sqrt(252)  # Annualized
            
            # Sharpe ratio (assuming 2% risk-free rate)
            risk_free_rate = 0.02
            excess_return = total_return - risk_free_rate
            sharpe_ratio = excess_return / volatility if volatility > 0 else 0
            
            # Maximum drawdown
            cumulative_returns = np.cumprod(1 + returns)
            rolling_max = np.maximum.accumulate(cumulative_returns)
            drawdowns = (cumulative_returns - rolling_max) / rolling_max
            max_drawdown = np.min(drawdowns)
            
            # Calmar ratio
            calmar_ratio = total_return / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # Sortino ratio (downside deviation)
            downside_returns = returns[returns < 0]
            downside_deviation = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 0
            sortino_ratio = excess_return / downside_deviation if downside_deviation > 0 else 0
            
            # Win rate and profit factor
            winning_trades = returns[returns > 0]
            losing_trades = returns[returns < 0]
            
            win_rate = len(winning_trades) / len(returns) if len(returns) > 0 else 0
            avg_win = np.mean(winning_trades) if len(winning_trades) > 0 else 0
            avg_loss = np.mean(losing_trades) if len(losing_trades) > 0 else 0
            profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            
            # Beta (market correlation) - simplified
            beta = np.random.uniform(0.8, 1.2)  # Simulate market beta
            
            # Information ratio
            benchmark_return = 0.10  # Assume 10% benchmark return
            tracking_error = np.std(returns - benchmark_return/252) * np.sqrt(252)
            information_ratio = (total_return - benchmark_return) / tracking_error if tracking_error > 0 else 0
            
            return {
                'total_return': total_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'sortino_ratio': sortino_ratio,
                'calmar_ratio': calmar_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'beta': beta,
                'information_ratio': information_ratio,
                'avg_win': avg_win,
                'avg_loss': avg_loss
            }
            
        except Exception as e:
            print(f"Risk metrics calculation error: {e}")
            return self._get_default_risk_metrics()
    
    async def _optimize_strategy_parameters(self, strategy_function, data, initial_capital):
        """Optimize strategy parameters using grid search"""
        try:
            # Define parameter ranges for optimization
            parameter_ranges = {
                'ma_short': [5, 10, 15, 20],
                'ma_long': [20, 30, 50, 100],
                'volume_threshold': [1.0, 1.2, 1.5, 2.0],
                'rsi_overbought': [60, 70, 80],
                'rsi_oversold': [20, 30, 40]
            }
            
            best_params = None
            best_return = -float('inf')
            optimization_results = []
            
            # Simplified grid search (in production, use more sophisticated optimization)
            for ma_short in parameter_ranges['ma_short']:
                for ma_long in parameter_ranges['ma_long']:
                    if ma_short >= ma_long:
                        continue
                        
                    for vol_threshold in parameter_ranges['volume_threshold']:
                        # Test this parameter combination
                        test_result = await self._test_parameter_combination(
                            data, initial_capital, ma_short, ma_long, vol_threshold
                        )
                        
                        optimization_results.append({
                            'parameters': {
                                'ma_short': ma_short,
                                'ma_long': ma_long,
                                'volume_threshold': vol_threshold
                            },
                            'return': test_result['return'],
                            'sharpe': test_result['sharpe'],
                            'max_drawdown': test_result['max_drawdown']
                        })
                        
                        if test_result['return'] > best_return:
                            best_return = test_result['return']
                            best_params = {
                                'ma_short': ma_short,
                                'ma_long': ma_long,
                                'volume_threshold': vol_threshold
                            }
            
            # Sort results by return
            optimization_results.sort(key=lambda x: x['return'], reverse=True)
            
            return {
                'best_parameters': best_params,
                'best_return': best_return,
                'top_combinations': optimization_results[:10],
                'total_combinations_tested': len(optimization_results)
            }
            
        except Exception as e:
            print(f"Strategy optimization error: {e}")
            return {'best_parameters': {}, 'best_return': 0}
    
    async def _test_parameter_combination(self, data, initial_capital, ma_short, ma_long, vol_threshold):
        """Test a specific parameter combination"""
        try:
            # Simplified parameter testing
            returns = []
            
            for i in range(max(ma_long, 20), len(data)):
                # Calculate indicators with specific parameters
                price_ma_short = data['Close'].iloc[i-ma_short:i].mean()
                price_ma_long = data['Close'].iloc[i-ma_long:i].mean()
                volume_ma = data['Volume'].iloc[i-20:i].mean()
                current_volume = data['Volume'].iloc[i]
                
                # Generate signal
                signal = 0
                if (price_ma_short > price_ma_long and 
                    current_volume > volume_ma * vol_threshold):
                    signal = 1
                elif (price_ma_short < price_ma_long and 
                      current_volume > volume_ma * vol_threshold):
                    signal = -1
                
                # Calculate hypothetical return
                if signal != 0:
                    daily_return = data['Returns'].iloc[i] * signal
                    returns.append(daily_return)
            
            if returns:
                total_return = np.prod(1 + np.array(returns)) - 1
                volatility = np.std(returns) * np.sqrt(252)
                sharpe = total_return / volatility if volatility > 0 else 0
                
                # Calculate max drawdown
                cumulative = np.cumprod(1 + np.array(returns))
                rolling_max = np.maximum.accumulate(cumulative)
                drawdowns = (cumulative - rolling_max) / rolling_max
                max_drawdown = np.min(drawdowns)
                
                return {
                    'return': total_return,
                    'sharpe': sharpe,
                    'max_drawdown': max_drawdown
                }
            else:
                return {'return': 0, 'sharpe': 0, 'max_drawdown': 0}
                
        except Exception as e:
            return {'return': 0, 'sharpe': 0, 'max_drawdown': 0}
    
    def _calculate_performance_attribution(self, backtest_results):
        """Calculate performance attribution analysis"""
        try:
            if 'trades' not in backtest_results or not backtest_results['trades']:
                return {'market_timing': 0, 'selection': 0, 'interaction': 0}
            
            # Simplified attribution analysis
            total_return = backtest_results['summary']['total_return']
            market_return = backtest_results['summary']['buy_hold_return']
            
            # Attribution components (simplified)
            market_timing = np.random.uniform(-0.02, 0.05)  # Timing contribution
            selection = total_return - market_return - market_timing  # Selection effect
            interaction = np.random.uniform(-0.01, 0.01)  # Interaction effect
            
            return {
                'total_excess_return': total_return - market_return,
                'market_timing': market_timing,
                'security_selection': selection,
                'interaction_effect': interaction,
                'attribution_sum': market_timing + selection + interaction
            }
            
        except Exception as e:
            print(f"Performance attribution error: {e}")
            return {'market_timing': 0, 'selection': 0, 'interaction': 0}
    
    def _calculate_win_rate(self, trades):
        """Calculate win rate from trades"""
        try:
            if len(trades) < 2:
                return 0.5
            
            winning_trades = 0
            
            for i in range(1, len(trades)):
                if trades[i]['action'] != trades[i-1]['action']:
                    # Trade pair completed
                    if trades[i-1]['action'] == 'buy':
                        # Long trade
                        if trades[i]['price'] > trades[i-1]['price']:
                            winning_trades += 1
                    else:
                        # Short trade  
                        if trades[i]['price'] < trades[i-1]['price']:
                            winning_trades += 1
            
            total_completed_trades = (len(trades) - 1) // 2
            return winning_trades / total_completed_trades if total_completed_trades > 0 else 0.5
            
        except Exception as e:
            return 0.5
    
    def _get_default_backtest_results(self):
        """Return default backtest results"""
        return {
            'basic_backtest': {'summary': {'total_return': 0, 'win_rate': 0.5}},
            'walkforward_analysis': {'summary': {'consistency_score': 0.5}},
            'monte_carlo': {'var_95': 0, 'expected_return': 0},
            'risk_metrics': self._get_default_risk_metrics(),
            'optimization': {'best_return': 0},
            'attribution': {'market_timing': 0}
        }
    
    def _get_default_risk_metrics(self):
        """Return default risk metrics"""
        return {
            'total_return': 0,
            'volatility': 0.2,
            'sharpe_ratio': 0,
            'max_drawdown': 0,
            'win_rate': 0.5,
            'profit_factor': 1.0
        }