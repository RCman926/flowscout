"""
Differential Refresh Coordinator - Smart Scheduling System
Optimizes refresh rates for different data types with priority-based scheduling
"""

import asyncio
import time
from typing import Dict, List, Any, Optional, Callable, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import logging
import threading
from collections import defaultdict
import streamlit as st
from optimized_cache_manager import cache_manager

class DataPriority(Enum):
    """Data priority levels for refresh scheduling - INSTITUTIONAL PROFESSIONAL"""
    CRITICAL = 1    # Prices - 3s refresh (real-time)
    HIGH = 2        # Technical indicators - 10s refresh  
    MEDIUM = 3      # Options flow - 5s refresh (professional)
    LOW = 4         # News, sentiment - 60s refresh
    BACKGROUND = 5  # Company info, earnings - 300s refresh

@dataclass
class RefreshTask:
    """Individual refresh task configuration"""
    key: str
    data_type: str
    priority: DataPriority
    refresh_interval: int
    fetch_function: Callable
    cache_tier: str
    last_refresh: Optional[datetime] = None
    next_refresh: Optional[datetime] = None
    error_count: int = 0
    max_errors: int = 3
    is_active: bool = True
    batch_group: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)

class DifferentialRefreshCoordinator:
    """
    Smart refresh coordinator that optimizes data fetching based on:
    - Data priority and criticality
    - Market hours and trading activity
    - API rate limits and error handling
    - Batch processing opportunities
    - User access patterns
    """
    
    def __init__(self):
        # Task management
        self.tasks: Dict[str, RefreshTask] = {}
        self.priority_queues: Dict[DataPriority, List[RefreshTask]] = {
            priority: [] for priority in DataPriority
        }
        
        # Scheduling configuration - INSTITUTIONAL PROFESSIONAL RATES
        self.base_intervals = {
            DataPriority.CRITICAL: 3,     # Price data - 3s (institutional real-time)
            DataPriority.HIGH: 10,        # Technical indicators - 10s
            DataPriority.MEDIUM: 5,       # Options flow - 5s (professional)
            DataPriority.LOW: 60,         # News/sentiment - 60s
            DataPriority.BACKGROUND: 300  # Static/company data - 5min
        }
        
        # Market-aware scheduling
        self.market_hours_multiplier = 1.0    # 1x during market hours
        self.after_hours_multiplier = 2.0     # 2x slower after hours
        self.weekend_multiplier = 4.0         # 4x slower on weekends
        
        # Rate limiting
        self.api_rate_limits = {
            'yahoo_finance': {'max_per_minute': 120, 'current_count': 0, 'reset_time': None},
            'web_scraping': {'max_per_minute': 60, 'current_count': 0, 'reset_time': None},
            'news_apis': {'max_per_minute': 100, 'current_count': 0, 'reset_time': None}
        }
        
        # Batch processing - INSTITUTIONAL PROFESSIONAL RATES
        self.batch_groups = {
            'market_data': {'symbols': [], 'interval': 3, 'max_batch_size': 10},      # 3s real-time
            'options_flow': {'symbols': [], 'interval': 5, 'max_batch_size': 5},     # 5s professional
            'technical_analysis': {'symbols': [], 'interval': 10, 'max_batch_size': 8},  # 10s
            'news_data': {'symbols': [], 'interval': 60, 'max_batch_size': 20}       # 60s
        }
        
        # Performance tracking
        self.execution_stats = defaultdict(list)
        self.error_tracking = defaultdict(int)
        
        # Async management
        self.scheduler_task = None
        self.batch_processor_task = None
        self.is_running = False
        self.lock = threading.Lock()
        
    def register_task(self, key: str, data_type: str, priority: DataPriority,
                     fetch_function: Callable, cache_tier: str = 'WARM',
                     batch_group: Optional[str] = None,
                     dependencies: List[str] = None) -> RefreshTask:
        """Register a new refresh task"""
        
        # Calculate refresh interval based on priority and market conditions
        base_interval = self.base_intervals[priority]
        current_multiplier = self._get_market_multiplier()
        refresh_interval = int(base_interval * current_multiplier)
        
        task = RefreshTask(
            key=key,
            data_type=data_type,
            priority=priority,
            refresh_interval=refresh_interval,
            fetch_function=fetch_function,
            cache_tier=cache_tier,
            batch_group=batch_group,
            dependencies=dependencies or []
        )
        
        # Schedule initial refresh
        now = datetime.now()
        task.last_refresh = now
        task.next_refresh = now + timedelta(seconds=refresh_interval)
        
        with self.lock:
            self.tasks[key] = task
            self.priority_queues[priority].append(task)
            
            # Add to batch group if specified
            if batch_group and batch_group in self.batch_groups:
                symbol = key.split('_')[0]  # Extract symbol from key
                if symbol not in self.batch_groups[batch_group]['symbols']:
                    self.batch_groups[batch_group]['symbols'].append(symbol)
        
        logging.info(f"Registered refresh task: {key} (Priority: {priority.name}, Interval: {refresh_interval}s)")
        return task
    
    def _get_market_multiplier(self) -> float:
        """Get current market-aware refresh multiplier"""
        # Avoid circular import by implementing market hours check locally
        from datetime import datetime, time as time_obj
        from zoneinfo import ZoneInfo
        
        def is_market_open_local(dt=None, tz='America/New_York'):
            """Local market hours check to avoid circular import"""
            dt = dt or datetime.now(ZoneInfo(tz))
            weekday = dt.weekday()  # 0=Monday, 6=Sunday
            current_time = dt.time()
            
            if weekday >= 5:  # Saturday or Sunday
                return False
            
            market_open_time = time_obj(9, 30)
            market_close_time = time_obj(16, 0)
            
            return market_open_time <= current_time <= market_close_time
        
        now = datetime.now()
        
        # Weekend check
        if now.weekday() >= 5:  # Saturday or Sunday
            return self.weekend_multiplier
        
        # Market hours check
        if is_market_open_local():
            return self.market_hours_multiplier
        else:
            return self.after_hours_multiplier
    
    async def start_coordinator(self):
        """Start the refresh coordinator with async scheduling"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start main scheduler
        self.scheduler_task = asyncio.create_task(self._run_scheduler())
        
        # Start batch processor
        self.batch_processor_task = asyncio.create_task(self._run_batch_processor())
        
        logging.info("Differential refresh coordinator started")
    
    async def stop_coordinator(self):
        """Stop the refresh coordinator"""
        self.is_running = False
        
        if self.scheduler_task:
            self.scheduler_task.cancel()
        if self.batch_processor_task:
            self.batch_processor_task.cancel()
            
        logging.info("Differential refresh coordinator stopped")
    
    async def _run_scheduler(self):
        """Main scheduler loop"""
        while self.is_running:
            try:
                await self._execute_scheduled_tasks()
                await asyncio.sleep(1)  # Check every second for precision
            except Exception as e:
                logging.error(f"Scheduler error: {e}")
                await asyncio.sleep(5)  # Back off on errors
    
    async def _run_batch_processor(self):
        """Batch processing loop"""
        while self.is_running:
            try:
                await self._process_batches()
                await asyncio.sleep(5)  # Process batches every 5 seconds
            except Exception as e:
                logging.error(f"Batch processor error: {e}")
                await asyncio.sleep(10)
    
    async def _execute_scheduled_tasks(self):
        """Execute tasks that are due for refresh"""
        now = datetime.now()
        executed_count = 0
        
        # Process tasks by priority (CRITICAL first)
        for priority in DataPriority:
            tasks = self.priority_queues[priority]
            due_tasks = [
                task for task in tasks
                if task.is_active and task.next_refresh and task.next_refresh <= now
            ]
            
            for task in due_tasks[:5]:  # Limit concurrent tasks per priority
                if self._check_rate_limit(task.data_type):
                    try:
                        await self._execute_single_task(task)
                        executed_count += 1
                    except Exception as e:
                        await self._handle_task_error(task, e)
        
        if executed_count > 0:
            logging.debug(f"Executed {executed_count} refresh tasks")
    
    async def _execute_single_task(self, task: RefreshTask):
        """Execute a single refresh task with performance tracking"""
        start_time = time.time()
        
        try:
            # Check dependencies
            for dep_key in task.dependencies:
                if dep_key in self.tasks and not self._is_dependency_ready(dep_key):
                    logging.debug(f"Task {task.key} waiting for dependency {dep_key}")
                    return
            
            # Execute fetch function
            if asyncio.iscoroutinefunction(task.fetch_function):
                data = await task.fetch_function(task.key)
            else:
                data = task.fetch_function(task.key)
            
            # Check if data actually changed before caching
            data_changed = cache_manager.set(task.key, data, task.cache_tier)
            
            # Update task timing
            execution_time = time.time() - start_time
            now = datetime.now()
            task.last_refresh = now
            
            # Adaptive interval adjustment based on data changes
            if data_changed:
                # Data changed - maintain current interval
                task.next_refresh = now + timedelta(seconds=task.refresh_interval)
            else:
                # Data unchanged - extend interval slightly (up to 50%)
                extended_interval = min(
                    task.refresh_interval * 1.5,
                    task.refresh_interval + 30
                )
                task.next_refresh = now + timedelta(seconds=extended_interval)
            
            # Track performance
            self.execution_stats[task.key].append({
                'timestamp': now,
                'execution_time': execution_time,
                'data_changed': data_changed
            })
            
            # Keep only last 10 stats per task
            if len(self.execution_stats[task.key]) > 10:
                self.execution_stats[task.key] = self.execution_stats[task.key][-10:]
            
            # Reset error count on success
            task.error_count = 0
            
            # Update rate limit tracking
            self._update_rate_limit(task.data_type)
            
            logging.debug(f"Task {task.key} executed in {execution_time:.3f}s, changed: {data_changed}")
            
        except Exception as e:
            await self._handle_task_error(task, e)
            raise
    
    async def _handle_task_error(self, task: RefreshTask, error: Exception):
        """Handle task execution errors with exponential backoff"""
        task.error_count += 1
        self.error_tracking[task.key] += 1
        
        if task.error_count >= task.max_errors:
            task.is_active = False
            logging.error(f"Task {task.key} disabled after {task.max_errors} consecutive errors")
        else:
            # Exponential backoff for retry
            backoff_seconds = min(60, 2 ** task.error_count)
            task.next_refresh = datetime.now() + timedelta(seconds=task.refresh_interval + backoff_seconds)
            logging.warning(f"Task {task.key} error (attempt {task.error_count}): {error}")
    
    def _check_rate_limit(self, data_type: str) -> bool:
        """Check if API rate limit allows this request"""
        api_category = self._get_api_category(data_type)
        rate_info = self.api_rate_limits.get(api_category)
        
        if not rate_info:
            return True
        
        now = datetime.now()
        
        # Reset counter if minute has passed
        if not rate_info['reset_time'] or now >= rate_info['reset_time']:
            rate_info['current_count'] = 0
            rate_info['reset_time'] = now + timedelta(minutes=1)
        
        # Check if under limit
        if rate_info['current_count'] < rate_info['max_per_minute']:
            return True
        
        logging.debug(f"Rate limit reached for {api_category}")
        return False
    
    def _update_rate_limit(self, data_type: str):
        """Update rate limit counter after successful request"""
        api_category = self._get_api_category(data_type)
        rate_info = self.api_rate_limits.get(api_category)
        
        if rate_info:
            rate_info['current_count'] += 1
    
    def _get_api_category(self, data_type: str) -> str:
        """Map data type to API category for rate limiting"""
        if data_type in ['market_data', 'options_data', 'price_data']:
            return 'yahoo_finance'
        elif data_type in ['options_flow', 'volume_analysis']:
            return 'web_scraping'
        elif data_type in ['news_data', 'sentiment_data']:
            return 'news_apis'
        else:
            return 'yahoo_finance'  # Default
    
    def _is_dependency_ready(self, dep_key: str) -> bool:
        """Check if dependency task has recent data"""
        cached_data = cache_manager.get(dep_key)
        return cached_data is not None
    
    async def _process_batches(self):
        """Process batch groups for efficient API usage"""
        for group_name, group_config in self.batch_groups.items():
            symbols = group_config['symbols']
            max_batch_size = group_config['max_batch_size']
            
            if len(symbols) >= 2:  # Only batch if we have multiple symbols
                # Split into batches
                for i in range(0, len(symbols), max_batch_size):
                    batch_symbols = symbols[i:i + max_batch_size]
                    await self._execute_batch(group_name, batch_symbols)
    
    async def _execute_batch(self, group_name: str, symbols: List[str]):
        """Execute batch request for multiple symbols"""
        try:
            if group_name == 'market_data':
                await self._batch_fetch_market_data(symbols)
            elif group_name == 'options_flow':
                await self._batch_fetch_options_flow(symbols)
            # Add more batch types as needed
                
        except Exception as e:
            logging.error(f"Batch execution error for {group_name}: {e}")
    
    async def _batch_fetch_market_data(self, symbols: List[str]):
        """Batch fetch market data for multiple symbols"""
        try:
            import yfinance as yf
            
            # Use yfinance's ability to fetch multiple tickers at once
            tickers_str = ' '.join(symbols)
            data = yf.download(tickers_str, period='1d', interval='1m', 
                             progress=False, show_errors=False)
            
            # Process and cache each symbol's data
            for symbol in symbols:
                try:
                    if len(symbols) > 1 and not data.empty:
                        # Multiple symbols - data is multi-index
                        symbol_data = data.xs(symbol, axis=1, level=1) if symbol in data.columns.get_level_values(1) else None
                    else:
                        # Single symbol or fallback
                        symbol_data = data
                    
                    if symbol_data is not None and not symbol_data.empty:
                        # Convert to standard format
                        current_price = symbol_data['Close'].iloc[-1]
                        prev_close = symbol_data['Close'].iloc[0]
                        
                        processed_data = {
                            'symbol': symbol,
                            'price': float(current_price),
                            'change': float(current_price - prev_close),
                            'change_pct': float((current_price - prev_close) / prev_close * 100),
                            'volume': int(symbol_data['Volume'].iloc[-1]),
                            'data_source': 'yahoo_batch',
                            'quality_score': 95,
                            'batch_processed': True
                        }
                        
                        # Cache in HOT tier for immediate access
                        cache_manager.set(f"{symbol}_market_data", processed_data, 'HOT')
                        
                except Exception as e:
                    logging.warning(f"Batch processing failed for symbol {symbol}: {e}")
                    
        except Exception as e:
            logging.error(f"Batch market data fetch failed: {e}")
    
    async def _batch_fetch_options_flow(self, symbols: List[str]):
        """Batch fetch options flow data"""
        # Implementation would depend on options data API
        pass
    
    def get_coordinator_stats(self) -> Dict[str, Any]:
        """Get comprehensive coordinator statistics"""
        active_tasks = sum(1 for task in self.tasks.values() if task.is_active)
        error_tasks = sum(1 for task in self.tasks.values() if task.error_count > 0)
        
        priority_breakdown = {}
        for priority in DataPriority:
            tasks = self.priority_queues[priority]
            priority_breakdown[priority.name] = {
                'total': len(tasks),
                'active': sum(1 for t in tasks if t.is_active),
                'errors': sum(1 for t in tasks if t.error_count > 0)
            }
        
        return {
            'total_tasks': len(self.tasks),
            'active_tasks': active_tasks,
            'error_tasks': error_tasks,
            'market_multiplier': self._get_market_multiplier(),
            'priority_breakdown': priority_breakdown,
            'batch_groups': {k: len(v['symbols']) for k, v in self.batch_groups.items()},
            'is_running': self.is_running
        }
    
    def force_refresh(self, key: str) -> bool:
        """Force immediate refresh of a specific task"""
        if key in self.tasks:
            task = self.tasks[key]
            task.next_refresh = datetime.now()
            return True
        return False
    
    def pause_task(self, key: str) -> bool:
        """Temporarily pause a refresh task"""
        if key in self.tasks:
            self.tasks[key].is_active = False
            return True
        return False
    
    def resume_task(self, key: str) -> bool:
        """Resume a paused refresh task"""
        if key in self.tasks:
            task = self.tasks[key]
            task.is_active = True
            task.error_count = 0  # Reset errors when resuming
            task.next_refresh = datetime.now() + timedelta(seconds=task.refresh_interval)
            return True
        return False

# Global coordinator instance
refresh_coordinator = DifferentialRefreshCoordinator()