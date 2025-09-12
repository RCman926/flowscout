"""
Optimized Cache Manager - Smart Multi-Tier Caching System
Professional-grade caching with sub-5s critical data updates
"""

import asyncio
import time
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from collections import defaultdict, OrderedDict
import logging
import threading
import streamlit as st

@dataclass
class CacheEntry:
    """Smart cache entry with metadata"""
    data: Any
    timestamp: datetime
    ttl_seconds: int
    access_count: int
    last_access: datetime
    data_hash: str
    cache_tier: str
    priority: int
    size_bytes: int

@dataclass  
class CacheStats:
    """Cache performance statistics"""
    hits: int = 0
    misses: int = 0
    invalidations: int = 0
    size_bytes: int = 0
    entries_count: int = 0
    hot_tier_hits: int = 0
    warm_tier_hits: int = 0
    cold_tier_hits: int = 0

class SmartCacheManager:
    """
    Advanced multi-tier caching system optimized for trading data
    - HOT: Critical data (prices, volume) - 5s TTL, highest priority
    - WARM: Important data (technical indicators) - 15s TTL  
    - COLD: Background data (news, earnings) - 60s TTL
    - FROZEN: Static data (company info) - 300s TTL
    """
    
    def __init__(self, max_memory_mb: int = 100):
        # Multi-tier cache storage
        self.hot_cache: Dict[str, CacheEntry] = OrderedDict()
        self.warm_cache: Dict[str, CacheEntry] = OrderedDict() 
        self.cold_cache: Dict[str, CacheEntry] = OrderedDict()
        self.frozen_cache: Dict[str, CacheEntry] = OrderedDict()
        
        # Cache configuration
        self.cache_tiers = {
            'HOT': {'ttl': 5, 'max_entries': 200, 'priority': 100},
            'WARM': {'ttl': 15, 'max_entries': 500, 'priority': 75},
            'COLD': {'ttl': 60, 'max_entries': 1000, 'priority': 50},
            'FROZEN': {'ttl': 300, 'max_entries': 2000, 'priority': 25}
        }
        
        # Memory management
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        self.current_memory_bytes = 0
        
        # Performance tracking
        self.stats = CacheStats()
        self.access_patterns = defaultdict(list)
        
        # Prefetch system
        self.prefetch_queue = asyncio.Queue(maxsize=50)
        self.prefetch_patterns = defaultdict(int)
        
        # Background maintenance
        self.maintenance_lock = threading.Lock()
        self.last_maintenance = datetime.now()
        self.maintenance_interval = 30  # seconds
        
        # Change detection
        self.data_signatures = {}
        self.change_callbacks = {}
        
    def _get_cache_by_tier(self, tier: str) -> Dict[str, CacheEntry]:
        """Get cache storage by tier name"""
        tier_map = {
            'HOT': self.hot_cache,
            'WARM': self.warm_cache, 
            'COLD': self.cold_cache,
            'FROZEN': self.frozen_cache
        }
        return tier_map.get(tier, self.warm_cache)
    
    def _calculate_data_hash(self, data: Any) -> str:
        """Calculate hash for change detection"""
        try:
            if isinstance(data, dict):
                # Sort dict keys for consistent hashing
                sorted_data = json.dumps(data, sort_keys=True, default=str)
            else:
                sorted_data = str(data)
            return hashlib.md5(sorted_data.encode()).hexdigest()[:16]
        except Exception:
            return hashlib.md5(str(data).encode()).hexdigest()[:16]
    
    def _calculate_size(self, data: Any) -> int:
        """Estimate data size in bytes"""
        try:
            if isinstance(data, (dict, list)):
                return len(json.dumps(data, default=str).encode())
            return len(str(data).encode())
        except Exception:
            return 1024  # Default estimate
    
    def _should_prefetch(self, key: str) -> bool:
        """Determine if key should be prefetched based on access patterns"""
        recent_accesses = [
            access for access in self.access_patterns[key] 
            if (datetime.now() - access).seconds < 300
        ]
        return len(recent_accesses) >= 3  # Accessed 3+ times in 5 minutes
    
    def get(self, key: str, tier: str = 'WARM') -> Optional[Any]:
        """Get data from cache with intelligent tier checking"""
        now = datetime.now()
        
        # Check all tiers in priority order
        for check_tier in ['HOT', 'WARM', 'COLD', 'FROZEN']:
            cache = self._get_cache_by_tier(check_tier)
            
            if key in cache:
                entry = cache[key]
                
                # Check if entry is still valid
                age_seconds = (now - entry.timestamp).total_seconds()
                if age_seconds <= entry.ttl_seconds:
                    # Update access metadata
                    entry.access_count += 1
                    entry.last_access = now
                    self.access_patterns[key].append(now)
                    
                    # Update statistics
                    self.stats.hits += 1
                    if check_tier == 'HOT':
                        self.stats.hot_tier_hits += 1
                    elif check_tier == 'WARM':
                        self.stats.warm_tier_hits += 1
                    elif check_tier == 'COLD':
                        self.stats.cold_tier_hits += 1
                    
                    # Schedule prefetch if access pattern suggests it
                    # DISABLED: asyncio.create_task causes RuntimeError in Streamlit
                    # if self._should_prefetch(key):
                    #     asyncio.create_task(self._schedule_prefetch(key, tier))
                    
                    return entry.data
                else:
                    # Entry expired, remove it
                    self._remove_entry(key, check_tier)
        
        # Cache miss
        self.stats.misses += 1
        self._perform_background_maintenance()
        return None
    
    def set(self, key: str, data: Any, tier: str = 'WARM', 
            change_callback: Optional[Callable] = None) -> bool:
        """Set data in cache with intelligent change detection"""
        now = datetime.now()
        cache = self._get_cache_by_tier(tier)
        config = self.cache_tiers[tier]
        
        # Calculate data signature for change detection
        data_hash = self._calculate_data_hash(data)
        
        # Check if data actually changed
        old_signature = self.data_signatures.get(key)
        if old_signature == data_hash:
            # Data unchanged, just update timestamp of existing entry
            if key in cache:
                cache[key].timestamp = now
                cache[key].last_access = now
                return False  # No actual change
        
        # Data changed or new entry
        data_size = self._calculate_size(data)
        
        # Memory management - evict if needed
        self._ensure_memory_capacity(data_size)
        self._ensure_tier_capacity(tier)
        
        # Create new cache entry
        entry = CacheEntry(
            data=data,
            timestamp=now,
            ttl_seconds=config['ttl'],
            access_count=1,
            last_access=now,
            data_hash=data_hash,
            cache_tier=tier,
            priority=config['priority'],
            size_bytes=data_size
        )
        
        # Store entry
        cache[key] = entry
        self.data_signatures[key] = data_hash
        self.current_memory_bytes += data_size
        self.stats.entries_count += 1
        self.stats.size_bytes += data_size
        
        # Execute change callback if provided
        if change_callback:
            self.change_callbacks[key] = change_callback
            try:
                change_callback(key, data)
            except Exception as e:
                logging.warning(f"Cache change callback failed for {key}: {e}")
        
        return True  # Actual change occurred
    
    def _remove_entry(self, key: str, tier: str):
        """Remove entry from cache and update statistics"""
        cache = self._get_cache_by_tier(tier)
        if key in cache:
            entry = cache[key]
            self.current_memory_bytes -= entry.size_bytes
            self.stats.size_bytes -= entry.size_bytes
            self.stats.entries_count -= 1
            del cache[key]
            
    def _ensure_memory_capacity(self, needed_bytes: int):
        """Ensure sufficient memory capacity using LRU eviction"""
        while (self.current_memory_bytes + needed_bytes) > self.max_memory_bytes:
            # Find least recently used entry across all tiers
            lru_key, lru_tier = None, None
            lru_time = datetime.now()
            
            for tier_name in ['FROZEN', 'COLD', 'WARM', 'HOT']:
                cache = self._get_cache_by_tier(tier_name)
                for key, entry in cache.items():
                    if entry.last_access < lru_time:
                        lru_time = entry.last_access
                        lru_key = key
                        lru_tier = tier_name
            
            if lru_key:
                self._remove_entry(lru_key, lru_tier)
            else:
                break  # No entries to evict
    
    def _ensure_tier_capacity(self, tier: str):
        """Ensure tier doesn't exceed max entries"""
        cache = self._get_cache_by_tier(tier)
        config = self.cache_tiers[tier]
        
        while len(cache) >= config['max_entries']:
            # Remove least recently used entry from this tier
            lru_key = min(cache.keys(), 
                         key=lambda k: cache[k].last_access)
            self._remove_entry(lru_key, tier)
    
    async def _schedule_prefetch(self, key: str, tier: str):
        """Schedule prefetch for frequently accessed keys"""
        try:
            await self.prefetch_queue.put((key, tier))
            self.prefetch_patterns[key] += 1
        except asyncio.QueueFull:
            pass  # Skip if queue full
    
    def _perform_background_maintenance(self):
        """Perform background cache maintenance"""
        now = datetime.now()
        if (now - self.last_maintenance).seconds < self.maintenance_interval:
            return
            
        with self.maintenance_lock:
            if (now - self.last_maintenance).seconds < self.maintenance_interval:
                return  # Double-check with lock
                
            self.last_maintenance = now
            
            # Clean expired entries
            total_removed = 0
            for tier_name in ['HOT', 'WARM', 'COLD', 'FROZEN']:
                cache = self._get_cache_by_tier(tier_name)
                config = self.cache_tiers[tier_name]
                
                expired_keys = []
                for key, entry in cache.items():
                    age_seconds = (now - entry.timestamp).total_seconds()
                    if age_seconds > entry.ttl_seconds:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    self._remove_entry(key, tier_name)
                    total_removed += 1
            
            # Clean old access patterns
            cutoff_time = now - timedelta(hours=1)
            for key in list(self.access_patterns.keys()):
                self.access_patterns[key] = [
                    access for access in self.access_patterns[key]
                    if access > cutoff_time
                ]
                if not self.access_patterns[key]:
                    del self.access_patterns[key]
            
            if total_removed > 0:
                logging.info(f"Cache maintenance: removed {total_removed} expired entries")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get comprehensive cache statistics"""
        hit_rate = (self.stats.hits / max(1, self.stats.hits + self.stats.misses)) * 100
        
        tier_stats = {}
        for tier_name in ['HOT', 'WARM', 'COLD', 'FROZEN']:
            cache = self._get_cache_by_tier(tier_name)
            tier_stats[tier_name] = {
                'entries': len(cache),
                'max_entries': self.cache_tiers[tier_name]['max_entries'],
                'ttl_seconds': self.cache_tiers[tier_name]['ttl']
            }
        
        return {
            'hit_rate_percent': round(hit_rate, 2),
            'total_hits': self.stats.hits,
            'total_misses': self.stats.misses,
            'memory_usage_mb': round(self.current_memory_bytes / (1024*1024), 2),
            'memory_limit_mb': round(self.max_memory_bytes / (1024*1024), 2),
            'total_entries': self.stats.entries_count,
            'tier_breakdown': tier_stats,
            'hot_tier_hit_rate': round(self.stats.hot_tier_hits / max(1, self.stats.hits) * 100, 1),
            'prefetch_queue_size': self.prefetch_queue.qsize()
        }
    
    def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching pattern"""
        invalidated = 0
        
        for tier_name in ['HOT', 'WARM', 'COLD', 'FROZEN']:
            cache = self._get_cache_by_tier(tier_name)
            keys_to_remove = [
                key for key in cache.keys() 
                if pattern in key
            ]
            
            for key in keys_to_remove:
                self._remove_entry(key, tier_name)
                invalidated += 1
        
        self.stats.invalidations += invalidated
        return invalidated
    
    def clear_tier(self, tier: str) -> int:
        """Clear all entries from specific tier"""
        cache = self._get_cache_by_tier(tier)
        count = len(cache)
        
        for key in list(cache.keys()):
            self._remove_entry(key, tier)
            
        return count
    
    def promote_to_hot(self, key: str) -> bool:
        """Promote frequently accessed data to HOT tier"""
        # Find entry in any tier
        for tier_name in ['WARM', 'COLD', 'FROZEN']:
            cache = self._get_cache_by_tier(tier_name)
            if key in cache:
                entry = cache[key]
                
                # Remove from current tier
                self._remove_entry(key, tier_name)
                
                # Add to HOT tier with updated TTL
                self.set(key, entry.data, 'HOT')
                return True
        
        return False

# Global cache manager instance
cache_manager = SmartCacheManager(max_memory_mb=150)

# Streamlit integration functions
def st_cache_data_smart(ttl_seconds: int = 15, tier: str = 'WARM'):
    """Enhanced Streamlit cache decorator with smart tiering"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Create cache key from function name and arguments
            cache_key = f"{func.__name__}_{hash(str(args) + str(sorted(kwargs.items())))}"
            
            # Try to get from smart cache
            cached_result = cache_manager.get(cache_key, tier)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, tier)
            
            return result
        return wrapper
    return decorator

def get_smart_cache_stats():
    """Get cache statistics for dashboard display"""
    return cache_manager.get_cache_stats()

def clear_smart_cache(pattern: str = None):
    """Clear smart cache with optional pattern matching"""
    if pattern:
        return cache_manager.invalidate_pattern(pattern)
    else:
        total = 0
        for tier in ['HOT', 'WARM', 'COLD', 'FROZEN']:
            total += cache_manager.clear_tier(tier)
        return total