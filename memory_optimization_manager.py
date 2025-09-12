"""
Memory Optimization Manager - Session State and Data Structure Optimization
Optimizes memory usage for maximum performance and responsiveness
"""

import gc
import sys
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import streamlit as st
from dataclasses import dataclass, asdict

@dataclass
class MemoryStats:
    """Memory usage statistics"""
    total_memory_mb: float
    session_memory_mb: float
    cache_memory_mb: float  
    optimization_savings_mb: float
    gc_collections: int

class MemoryOptimizationManager:
    """
    Advanced memory optimization for session state and data structures
    - Efficient session state management
    - Automatic garbage collection
    - Memory-optimized data structures
    - Lazy loading and cleanup
    """
    
    def __init__(self):
        self.start_time = time.time()
        self.initial_memory = self._get_memory_usage()
        self.optimizations_applied = []
        self.cleanup_threshold_mb = 50  # Trigger cleanup at 50MB
        self.last_cleanup = datetime.now()
        
    def optimize_session_state(self):
        """Optimize Streamlit session state for better performance"""
        optimizations = []
        
        # 1. Remove redundant session state entries
        redundant_keys = []
        for key in st.session_state.keys():
            if key.startswith('temp_') or key.endswith('_old'):
                redundant_keys.append(key)
        
        for key in redundant_keys:
            del st.session_state[key]
            optimizations.append(f"Removed redundant key: {key}")
        
        # 2. Convert large objects to memory-efficient formats
        for key, value in st.session_state.items():
            if isinstance(value, dict) and len(value) > 100:
                # Convert large dicts to more memory-efficient structure
                optimized_value = self._optimize_dict_structure(value)
                st.session_state[key] = optimized_value
                optimizations.append(f"Optimized large dict: {key}")
        
        # 3. Implement lazy loading for heavy objects
        heavy_objects = ['professional_ai', 'signal_coordinator', 'prediction_tracker']
        for obj_name in heavy_objects:
            if obj_name in st.session_state:
                # Keep reference but implement lazy reloading
                st.session_state[f"{obj_name}_lazy"] = True
                optimizations.append(f"Set lazy loading for: {obj_name}")
        
        # 4. Clear expired cached computations
        current_time = datetime.now()
        expired_keys = []
        
        for key in st.session_state.keys():
            if key.endswith('_cached_time'):
                base_key = key.replace('_cached_time', '')
                cached_time = st.session_state.get(key)
                
                if isinstance(cached_time, datetime):
                    age_seconds = (current_time - cached_time).total_seconds()
                    if age_seconds > 300:  # 5 minutes
                        expired_keys.extend([key, base_key, f"{base_key}_cached"])
        
        for key in expired_keys:
            if key in st.session_state:
                del st.session_state[key]
                optimizations.append(f"Removed expired cache: {key}")
        
        self.optimizations_applied.extend(optimizations)
        return len(optimizations)
    
    def _optimize_dict_structure(self, data_dict: Dict) -> Dict:
        """Optimize dictionary structure for memory efficiency"""
        if not isinstance(data_dict, dict):
            return data_dict
        
        optimized = {}
        for key, value in data_dict.items():
            # Convert string numbers to actual numbers to save memory
            if isinstance(value, str) and value.replace('.', '').replace('-', '').isdigit():
                try:
                    optimized[key] = float(value) if '.' in value else int(value)
                except ValueError:
                    optimized[key] = value
            # Truncate very long strings that aren't needed in full
            elif isinstance(value, str) and len(value) > 200:
                optimized[key] = value[:200] + "..." if not key.endswith('_full') else value
            else:
                optimized[key] = value
        
        return optimized
    
    def perform_memory_cleanup(self, force: bool = False) -> Dict[str, Any]:
        """Perform comprehensive memory cleanup"""
        current_memory = self._get_memory_usage()
        memory_delta = current_memory - self.initial_memory
        
        # Check if cleanup is needed
        if not force and memory_delta < self.cleanup_threshold_mb:
            return {'cleanup_needed': False, 'memory_usage_mb': current_memory}
        
        cleanup_stats = {
            'pre_cleanup_memory': current_memory,
            'optimizations_applied': [],
            'memory_freed_mb': 0.0,
            'gc_collections': 0
        }
        
        # 1. Optimize session state
        session_optimizations = self.optimize_session_state()
        cleanup_stats['optimizations_applied'].append(f"Session state: {session_optimizations} items")
        
        # 2. Force garbage collection
        initial_gc_count = len(gc.get_objects())
        gc.collect()  # Full collection
        gc.collect()  # Second pass for circular references
        final_gc_count = len(gc.get_objects())
        
        cleanup_stats['gc_collections'] = initial_gc_count - final_gc_count
        
        # 3. Clear Python caches
        if hasattr(sys, '_clear_type_cache'):
            sys._clear_type_cache()
            cleanup_stats['optimizations_applied'].append("Cleared type cache")
        
        # 4. Update memory stats
        post_cleanup_memory = self._get_memory_usage()
        cleanup_stats['memory_freed_mb'] = current_memory - post_cleanup_memory
        cleanup_stats['post_cleanup_memory'] = post_cleanup_memory
        
        self.last_cleanup = datetime.now()
        
        logging.info(f"Memory cleanup freed {cleanup_stats['memory_freed_mb']:.2f} MB")
        return cleanup_stats
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            process = psutil.Process()
            return process.memory_info().rss / 1024 / 1024  # Convert to MB
        except ImportError:
            # Fallback to sys.getsizeof for rough estimate
            return sys.getsizeof(st.session_state) / 1024 / 1024
    
    def get_memory_stats(self) -> MemoryStats:
        """Get comprehensive memory statistics"""
        current_memory = self._get_memory_usage()
        
        # Estimate session state memory
        session_memory = 0.0
        try:
            for key, value in st.session_state.items():
                session_memory += sys.getsizeof(value) / 1024 / 1024
        except:
            session_memory = 10.0  # Default estimate
        
        # Estimate cache memory
        cache_memory = 5.0  # Rough estimate
        
        return MemoryStats(
            total_memory_mb=current_memory,
            session_memory_mb=session_memory,
            cache_memory_mb=cache_memory,
            optimization_savings_mb=max(0, self.initial_memory - current_memory),
            gc_collections=len(gc.get_objects())
        )
    
    def should_trigger_cleanup(self) -> bool:
        """Determine if memory cleanup should be triggered"""
        current_memory = self._get_memory_usage()
        memory_increase = current_memory - self.initial_memory
        
        time_since_cleanup = (datetime.now() - self.last_cleanup).total_seconds()
        
        # Trigger cleanup if:
        # 1. Memory increased by more than threshold
        # 2. Haven't cleaned up in last 5 minutes and memory > 30MB
        # 3. Session state has more than 50 keys
        
        return (
            memory_increase > self.cleanup_threshold_mb or
            (time_since_cleanup > 300 and current_memory > 30) or
            len(st.session_state) > 50
        )
    
    def optimize_data_structures(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize data structures for memory efficiency"""
        optimized_data = {}
        
        for key, value in data.items():
            if isinstance(value, dict):
                # Recursively optimize nested dictionaries
                optimized_data[key] = self.optimize_data_structures(value)
            elif isinstance(value, list) and len(value) > 100:
                # Optimize large lists by removing duplicates and compacting
                if all(isinstance(x, (int, float, str)) for x in value):
                    # Remove duplicates while preserving order for simple types
                    seen = set()
                    optimized_list = []
                    for item in value:
                        if item not in seen:
                            seen.add(item)
                            optimized_list.append(item)
                    optimized_data[key] = optimized_list
                else:
                    optimized_data[key] = value
            else:
                optimized_data[key] = value
        
        return optimized_data
    
    def create_memory_efficient_cache(self, max_size: int = 100) -> Dict:
        """Create a memory-efficient LRU cache"""
        from collections import OrderedDict
        
        class MemoryEfficientCache(OrderedDict):
            def __init__(self, max_size=max_size):
                super().__init__()
                self.max_size = max_size
            
            def __setitem__(self, key, value):
                if key in self:
                    # Move to end (most recently used)
                    self.move_to_end(key)
                elif len(self) >= self.max_size:
                    # Remove oldest item
                    self.popitem(last=False)
                
                # Optimize value before storing
                if isinstance(value, dict):
                    value = memory_manager.optimize_data_structures(value)
                
                super().__setitem__(key, value)
            
            def get_memory_usage(self):
                return sum(sys.getsizeof(v) for v in self.values()) / 1024 / 1024
        
        return MemoryEfficientCache(max_size)

# Global memory optimization manager
memory_manager = MemoryOptimizationManager()

# Streamlit integration functions
def optimize_streamlit_session():
    """Optimize Streamlit session for better performance"""
    return memory_manager.optimize_session_state()

def perform_automatic_cleanup():
    """Perform automatic memory cleanup if needed"""
    if memory_manager.should_trigger_cleanup():
        return memory_manager.perform_memory_cleanup()
    return None

def get_memory_dashboard_stats():
    """Get memory stats for dashboard display"""
    return memory_manager.get_memory_stats()

def create_efficient_cache(max_size: int = 100):
    """Create memory-efficient cache for data storage"""
    return memory_manager.create_memory_efficient_cache(max_size)