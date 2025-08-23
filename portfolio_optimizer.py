import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from scipy.optimize import minimize
import asyncio
import warnings
warnings.filterwarnings('ignore')

class PortfolioOptimizationEngine:
    """
    Advanced portfolio optimization for multi-symbol trading strategies
    Implements Modern Portfolio Theory, risk parity, and Kelly criterion
    """
    
    def __init__(self):
        self.correlation_cache = {}
        self.optimization_cache = {}
        self.cache_duration = 3600  # 1 hour
        
    async def optimize_portfolio(self, symbols, expected_returns=None, 
                               risk_tolerance='moderate', method='sharpe'):
        """
        Optimize portfolio allocation across multiple symbols
        
        Args:
            symbols: List of symbols to include in portfolio
            expected_returns: Dict of expected returns per symbol
            risk_tolerance: 'conservative', 'moderate', 'aggressive'
            method: 'sharpe', 'min_variance', 'risk_parity', 'kelly'
        """
        try:
            # Get correlation matrix and risk metrics
            correlation_matrix = await self._get_correlation_matrix(symbols)
            risk_metrics = await self._get_risk_metrics(symbols)
            
            if expected_returns is None:
                expected_returns = await self._estimate_expected_returns(symbols)
            
            # Optimize based on method
            if method == 'sharpe':
                weights = self._optimize_sharpe_ratio(
                    expected_returns, correlation_matrix, risk_metrics
                )
            elif method == 'min_variance':
                weights = self._optimize_minimum_variance(correlation_matrix, risk_metrics)
            elif method == 'risk_parity':
                weights = self._optimize_risk_parity(correlation_matrix, risk_metrics)
            elif method == 'kelly':
                weights = self._optimize_kelly_criterion(
                    expected_returns, correlation_matrix, risk_metrics
                )
            else:
                weights = self._equal_weight_portfolio(symbols)
            
            # Apply risk tolerance constraints
            weights = self._apply_risk_tolerance(weights, risk_tolerance)
            
            # Calculate portfolio metrics
            portfolio_metrics = self._calculate_portfolio_metrics(
                weights, expected_returns, correlation_matrix, risk_metrics
            )
            
            return {
                'weights': weights,
                'expected_return': portfolio_metrics['expected_return'],
                'expected_volatility': portfolio_metrics['volatility'],
                'sharpe_ratio': portfolio_metrics['sharpe_ratio'],
                'diversification_ratio': portfolio_metrics['diversification_ratio'],
                'max_weight': max(weights.values()),
                'optimization_method': method,
                'risk_tolerance': risk_tolerance
            }
            
        except Exception as e:
            print(f"Portfolio optimization error: {e}")
            return self._get_equal_weight_fallback(symbols)
    
    async def _get_correlation_matrix(self, symbols):
        """Calculate correlation matrix for symbols"""
        try:
            cache_key = f"corr_{'_'.join(sorted(symbols))}"
            if self._is_cache_valid(cache_key):
                return self.correlation_cache[cache_key]['data']
            
            # Get historical data for all symbols
            end_date = datetime.now()
            start_date = end_date - timedelta(days=252)  # 1 year of data
            
            price_data = {}
            for symbol in symbols:
                ticker = yf.Ticker(symbol)
                hist = ticker.history(start=start_date, end=end_date)
                if not hist.empty:
                    price_data[symbol] = hist['Close']
            
            if len(price_data) < 2:
                # Return identity matrix if insufficient data
                return pd.DataFrame(np.eye(len(symbols)), 
                                  index=symbols, columns=symbols)
            
            # Create DataFrame and calculate returns
            df = pd.DataFrame(price_data)
            returns = df.pct_change().dropna()
            
            # Calculate correlation matrix
            correlation_matrix = returns.corr()
            
            # Fill any NaN values with 0 (uncorrelated)
            correlation_matrix = correlation_matrix.fillna(0)
            
            # Ensure all symbols are included
            for symbol in symbols:
                if symbol not in correlation_matrix.index:
                    # Add uncorrelated row/column for missing symbols
                    correlation_matrix.loc[symbol] = 0
                    correlation_matrix[symbol] = 0
                    correlation_matrix.loc[symbol, symbol] = 1
            
            # Cache result
            self.correlation_cache[cache_key] = {
                'data': correlation_matrix,
                'timestamp': datetime.now()
            }
            
            return correlation_matrix
            
        except Exception as e:
            print(f"Correlation matrix error: {e}")
            # Return identity matrix as fallback
            return pd.DataFrame(np.eye(len(symbols)), 
                              index=symbols, columns=symbols)
    
    async def _get_risk_metrics(self, symbols):
        """Get risk metrics for each symbol"""
        try:
            risk_metrics = {}
            
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="1y")
                    
                    if not hist.empty:
                        returns = hist['Close'].pct_change().dropna()
                        
                        # Calculate risk metrics
                        volatility = returns.std() * np.sqrt(252)  # Annualized
                        var_95 = np.percentile(returns, 5)  # 5% VaR
                        skewness = returns.skew()
                        kurtosis = returns.kurtosis()
                        
                        # Maximum drawdown
                        cumulative = (1 + returns).cumprod()
                        rolling_max = cumulative.expanding().max()
                        drawdown = (cumulative - rolling_max) / rolling_max
                        max_drawdown = drawdown.min()
                        
                        risk_metrics[symbol] = {
                            'volatility': volatility,
                            'var_95': var_95,
                            'skewness': skewness,
                            'kurtosis': kurtosis,
                            'max_drawdown': max_drawdown
                        }
                    else:
                        risk_metrics[symbol] = self._get_default_risk_metrics()
                        
                except Exception as e:
                    print(f"Risk metrics error for {symbol}: {e}")
                    risk_metrics[symbol] = self._get_default_risk_metrics()
            
            return risk_metrics
            
        except Exception as e:
            print(f"Risk metrics calculation error: {e}")
            return {symbol: self._get_default_risk_metrics() for symbol in symbols}
    
    async def _estimate_expected_returns(self, symbols):
        """Estimate expected returns for symbols"""
        try:
            expected_returns = {}
            
            for symbol in symbols:
                try:
                    ticker = yf.Ticker(symbol)
                    hist = ticker.history(period="2y")  # 2 years for better estimate
                    
                    if not hist.empty:
                        returns = hist['Close'].pct_change().dropna()
                        
                        # Use multiple estimation methods
                        historical_mean = returns.mean() * 252  # Annualized
                        
                        # Exponentially weighted average (more recent bias)
                        weights = np.exp(np.linspace(-1, 0, len(returns)))
                        weights /= weights.sum()
                        weighted_mean = np.sum(returns * weights) * 252
                        
                        # Trend-based estimate
                        trend_return = (hist['Close'].iloc[-1] / hist['Close'].iloc[-252] - 1) if len(hist) >= 252 else 0
                        
                        # Combine estimates
                        expected_return = (
                            0.4 * historical_mean + 
                            0.4 * weighted_mean + 
                            0.2 * trend_return
                        )
                        
                        expected_returns[symbol] = expected_return
                    else:
                        expected_returns[symbol] = 0.08  # Default 8% expected return
                        
                except Exception as e:
                    print(f"Expected return estimation error for {symbol}: {e}")
                    expected_returns[symbol] = 0.08
            
            return expected_returns
            
        except Exception as e:
            print(f"Expected returns estimation error: {e}")
            return {symbol: 0.08 for symbol in symbols}
    
    def _optimize_sharpe_ratio(self, expected_returns, correlation_matrix, risk_metrics):
        """Optimize portfolio for maximum Sharpe ratio"""
        try:
            symbols = list(expected_returns.keys())
            n_assets = len(symbols)
            
            # Convert to arrays
            returns_array = np.array([expected_returns[symbol] for symbol in symbols])
            volatilities = np.array([risk_metrics[symbol]['volatility'] for symbol in symbols])
            
            # Create covariance matrix
            corr_array = correlation_matrix.loc[symbols, symbols].values
            cov_matrix = np.outer(volatilities, volatilities) * corr_array
            
            # Objective function (negative Sharpe ratio)
            def negative_sharpe(weights):
                portfolio_return = np.sum(weights * returns_array)
                portfolio_volatility = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
                
                # Risk-free rate assumption
                risk_free_rate = 0.02
                
                if portfolio_volatility == 0:
                    return -1000  # Avoid division by zero
                
                sharpe = (portfolio_return - risk_free_rate) / portfolio_volatility
                return -sharpe  # Negative because we minimize
            
            # Constraints
            constraints = [
                {'type': 'eq', 'fun': lambda weights: np.sum(weights) - 1},  # Weights sum to 1
            ]
            
            # Bounds (0 to 40% per asset)
            bounds = [(0, 0.4) for _ in range(n_assets)]
            
            # Initial guess (equal weights)
            initial_weights = np.array([1/n_assets] * n_assets)
            
            # Optimize
            result = minimize(
                negative_sharpe,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'maxiter': 1000}
            )
            
            if result.success:
                weights = result.x
                return {symbol: weight for symbol, weight in zip(symbols, weights)}
            else:
                return self._equal_weight_portfolio(symbols)
                
        except Exception as e:
            print(f"Sharpe optimization error: {e}")
            return self._equal_weight_portfolio(list(expected_returns.keys()))
    
    def _optimize_minimum_variance(self, correlation_matrix, risk_metrics):
        """Optimize for minimum portfolio variance"""
        try:
            symbols = list(risk_metrics.keys())
            n_assets = len(symbols)
            
            # Get volatilities
            volatilities = np.array([risk_metrics[symbol]['volatility'] for symbol in symbols])
            
            # Create covariance matrix
            corr_array = correlation_matrix.loc[symbols, symbols].values
            cov_matrix = np.outer(volatilities, volatilities) * corr_array
            
            # Objective function (portfolio variance)
            def portfolio_variance(weights):
                return np.dot(weights, np.dot(cov_matrix, weights))
            
            # Constraints
            constraints = [
                {'type': 'eq', 'fun': lambda weights: np.sum(weights) - 1},
            ]
            
            # Bounds
            bounds = [(0, 0.5) for _ in range(n_assets)]
            
            # Initial guess
            initial_weights = np.array([1/n_assets] * n_assets)
            
            # Optimize
            result = minimize(
                portfolio_variance,
                initial_weights,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints
            )
            
            if result.success:
                weights = result.x
                return {symbol: weight for symbol, weight in zip(symbols, weights)}
            else:
                return self._equal_weight_portfolio(symbols)
                
        except Exception as e:
            print(f"Minimum variance optimization error: {e}")
            return self._equal_weight_portfolio(list(risk_metrics.keys()))
    
    def _optimize_risk_parity(self, correlation_matrix, risk_metrics):
        """Optimize for risk parity (equal risk contribution)"""
        try:
            symbols = list(risk_metrics.keys())
            n_assets = len(symbols)
            
            # Get volatilities
            volatilities = np.array([risk_metrics[symbol]['volatility'] for symbol in symbols])
            
            # Risk parity weights (inverse volatility weighting)
            inv_vol = 1 / volatilities
            weights = inv_vol / np.sum(inv_vol)
            
            # Apply diversification adjustment based on correlations
            avg_correlation = correlation_matrix.loc[symbols, symbols].values.mean()
            diversification_factor = 1 - avg_correlation
            
            # Adjust weights based on diversification
            if diversification_factor > 0.5:
                # High diversification - maintain risk parity
                pass
            else:
                # Low diversification - move toward equal weighting
                equal_weights = np.array([1/n_assets] * n_assets)
                blend_factor = 1 - diversification_factor
                weights = blend_factor * equal_weights + (1 - blend_factor) * weights
            
            return {symbol: weight for symbol, weight in zip(symbols, weights)}
            
        except Exception as e:
            print(f"Risk parity optimization error: {e}")
            return self._equal_weight_portfolio(list(risk_metrics.keys()))
    
    def _optimize_kelly_criterion(self, expected_returns, correlation_matrix, risk_metrics):
        """Optimize using Kelly criterion for growth maximization"""
        try:
            symbols = list(expected_returns.keys())
            n_assets = len(symbols)
            
            # Convert to arrays
            returns_array = np.array([expected_returns[symbol] for symbol in symbols])
            volatilities = np.array([risk_metrics[symbol]['volatility'] for symbol in symbols])
            
            # Create covariance matrix
            corr_array = correlation_matrix.loc[symbols, symbols].values
            cov_matrix = np.outer(volatilities, volatilities) * corr_array
            
            # Kelly criterion: f = μ / σ² (simplified for portfolio)
            # More sophisticated: f = Σ^(-1) * μ
            
            try:
                inv_cov_matrix = np.linalg.inv(cov_matrix)
                kelly_weights = np.dot(inv_cov_matrix, returns_array)
            except np.linalg.LinAlgError:
                # If matrix is singular, use diagonal approximation
                kelly_weights = returns_array / (volatilities ** 2)
            
            # Normalize to sum to 1 and apply bounds
            kelly_weights = np.maximum(0, kelly_weights)  # No short selling
            
            if np.sum(kelly_weights) > 0:
                kelly_weights = kelly_weights / np.sum(kelly_weights)
            else:
                kelly_weights = np.array([1/n_assets] * n_assets)
            
            # Apply maximum position size limits (Kelly can be aggressive)
            max_position = 0.3
            kelly_weights = np.minimum(kelly_weights, max_position)
            kelly_weights = kelly_weights / np.sum(kelly_weights)  # Renormalize
            
            return {symbol: weight for symbol, weight in zip(symbols, kelly_weights)}
            
        except Exception as e:
            print(f"Kelly criterion optimization error: {e}")
            return self._equal_weight_portfolio(list(expected_returns.keys()))
    
    def _apply_risk_tolerance(self, weights, risk_tolerance):
        """Apply risk tolerance constraints to weights"""
        try:
            if risk_tolerance == 'conservative':
                # More equal weighting, lower max position
                max_weight = 0.25
                concentration_penalty = 0.3
            elif risk_tolerance == 'moderate':
                # Balanced approach
                max_weight = 0.35
                concentration_penalty = 0.2
            else:  # aggressive
                # Allow higher concentration
                max_weight = 0.5
                concentration_penalty = 0.1
            
            # Apply maximum weight constraint
            adjusted_weights = {}
            for symbol, weight in weights.items():
                adjusted_weights[symbol] = min(weight, max_weight)
            
            # Renormalize
            total_weight = sum(adjusted_weights.values())
            if total_weight > 0:
                for symbol in adjusted_weights:
                    adjusted_weights[symbol] /= total_weight
            
            # Apply concentration penalty (move toward equal weighting)
            n_assets = len(adjusted_weights)
            equal_weight = 1 / n_assets
            
            final_weights = {}
            for symbol, weight in adjusted_weights.items():
                final_weights[symbol] = (
                    (1 - concentration_penalty) * weight + 
                    concentration_penalty * equal_weight
                )
            
            return final_weights
            
        except Exception as e:
            print(f"Risk tolerance application error: {e}")
            return weights
    
    def _calculate_portfolio_metrics(self, weights, expected_returns, 
                                   correlation_matrix, risk_metrics):
        """Calculate portfolio performance metrics"""
        try:
            symbols = list(weights.keys())
            
            # Expected portfolio return
            portfolio_return = sum(weights[symbol] * expected_returns[symbol] 
                                 for symbol in symbols)
            
            # Portfolio volatility
            volatilities = [risk_metrics[symbol]['volatility'] for symbol in symbols]
            weight_array = np.array([weights[symbol] for symbol in symbols])
            vol_array = np.array(volatilities)
            
            corr_array = correlation_matrix.loc[symbols, symbols].values
            cov_matrix = np.outer(vol_array, vol_array) * corr_array
            
            portfolio_variance = np.dot(weight_array, np.dot(cov_matrix, weight_array))
            portfolio_volatility = np.sqrt(portfolio_variance)
            
            # Sharpe ratio
            risk_free_rate = 0.02
            sharpe_ratio = (portfolio_return - risk_free_rate) / portfolio_volatility if portfolio_volatility > 0 else 0
            
            # Diversification ratio
            weighted_avg_vol = sum(weights[symbol] * volatilities[i] 
                                 for i, symbol in enumerate(symbols))
            diversification_ratio = weighted_avg_vol / portfolio_volatility if portfolio_volatility > 0 else 1
            
            return {
                'expected_return': portfolio_return,
                'volatility': portfolio_volatility,
                'sharpe_ratio': sharpe_ratio,
                'diversification_ratio': diversification_ratio
            }
            
        except Exception as e:
            print(f"Portfolio metrics calculation error: {e}")
            return {
                'expected_return': 0.08,
                'volatility': 0.15,
                'sharpe_ratio': 0.4,
                'diversification_ratio': 1.0
            }
    
    def _equal_weight_portfolio(self, symbols):
        """Create equal weight portfolio as fallback"""
        weight = 1.0 / len(symbols)
        return {symbol: weight for symbol in symbols}
    
    def _get_equal_weight_fallback(self, symbols):
        """Return equal weight portfolio with basic metrics"""
        weights = self._equal_weight_portfolio(symbols)
        return {
            'weights': weights,
            'expected_return': 0.08,
            'expected_volatility': 0.15,
            'sharpe_ratio': 0.4,
            'diversification_ratio': 1.0,
            'max_weight': 1.0 / len(symbols),
            'optimization_method': 'equal_weight',
            'risk_tolerance': 'moderate'
        }
    
    def _get_default_risk_metrics(self):
        """Return default risk metrics"""
        return {
            'volatility': 0.25,
            'var_95': -0.03,
            'skewness': 0,
            'kurtosis': 3,
            'max_drawdown': -0.15
        }
    
    def _is_cache_valid(self, cache_key):
        """Check if cached data is still valid"""
        if cache_key not in self.correlation_cache:
            return False
        
        cache_time = self.correlation_cache[cache_key]['timestamp']
        time_diff = (datetime.now() - cache_time).total_seconds()
        return time_diff < self.cache_duration
    
    async def get_position_sizing_recommendation(self, symbol, portfolio_value, 
                                               signal_confidence, risk_per_trade=0.02):
        """
        Calculate optimal position size using Kelly criterion and risk management
        
        Args:
            symbol: Trading symbol
            portfolio_value: Total portfolio value
            signal_confidence: Confidence in the trading signal (0-1)
            risk_per_trade: Maximum risk per trade as fraction of portfolio
        """
        try:
            # Get symbol risk metrics
            risk_metrics = await self._get_risk_metrics([symbol])
            symbol_vol = risk_metrics[symbol]['volatility']
            
            # Base position size using fixed fractional risk
            base_position_size = (portfolio_value * risk_per_trade) / symbol_vol
            
            # Adjust by signal confidence
            confidence_adjusted_size = base_position_size * signal_confidence
            
            # Apply Kelly criterion adjustment
            # Simplified Kelly: f = (bp - q) / b, where b=odds, p=win_prob, q=lose_prob
            estimated_win_prob = 0.5 + (signal_confidence - 0.5) * 0.3  # Convert confidence to win probability
            estimated_lose_prob = 1 - estimated_win_prob
            avg_win_loss_ratio = 1.5  # Assume 1.5:1 win/loss ratio
            
            kelly_fraction = (avg_win_loss_ratio * estimated_win_prob - estimated_lose_prob) / avg_win_loss_ratio
            kelly_fraction = max(0, min(kelly_fraction, 0.25))  # Cap at 25% of portfolio
            
            kelly_position_size = portfolio_value * kelly_fraction
            
            # Take the more conservative of the two approaches
            recommended_size = min(confidence_adjusted_size, kelly_position_size)
            
            # Final safeguards
            max_position_size = portfolio_value * 0.2  # Never more than 20% in one position
            recommended_size = min(recommended_size, max_position_size)
            
            position_pct = recommended_size / portfolio_value
            
            return {
                'recommended_position_size': recommended_size,
                'position_percentage': position_pct,
                'kelly_fraction': kelly_fraction,
                'risk_adjusted_size': confidence_adjusted_size,
                'max_risk_per_trade': risk_per_trade,
                'estimated_win_probability': estimated_win_prob
            }
            
        except Exception as e:
            print(f"Position sizing error: {e}")
            # Conservative fallback
            conservative_size = portfolio_value * 0.05  # 5% of portfolio
            return {
                'recommended_position_size': conservative_size,
                'position_percentage': 0.05,
                'kelly_fraction': 0.05,
                'risk_adjusted_size': conservative_size
            }