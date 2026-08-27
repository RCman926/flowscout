// FlowScout Pro - Offline Data Manager
// Caches real-time data for offline access and background sync

class OfflineDataManager {
    constructor() {
        this.dbName = 'FlowScoutProDB';
        this.dbVersion = 1;
        this.db = null;
        this.syncQueue = [];
        this.lastSyncTime = null;
        this.syncInterval = null;
    }

    // Initialize IndexedDB
    async init() {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, this.dbVersion);

            request.onerror = () => reject(request.error);
            request.onsuccess = () => {
                this.db = request.result;
                console.log('[OfflineData] IndexedDB initialized');
                resolve();
            };

            request.onupgradeneeded = (event) => {
                const db = event.target.result;

                // Store for flow data (options chain, prices, signals)
                if (!db.objectStoreNames.contains('flowData')) {
                    const flowStore = db.createObjectStore('flowData', { keyPath: 'symbol' });
                    flowStore.createIndex('timestamp', 'timestamp', { unique: false });
                }

                // Store for recent updates (last N updates per symbol)
                if (!db.objectStoreNames.contains('recentUpdates')) {
                    const updateStore = db.createObjectStore('recentUpdates', { keyPath: 'id', autoIncrement: true });
                    updateStore.createIndex('symbol', 'symbol', { unique: false });
                    updateStore.createIndex('timestamp', 'timestamp', { unique: false });
                }

                // Store for signals history
                if (!db.objectStoreNames.contains('signals')) {
                    const signalStore = db.createObjectStore('signals', { keyPath: 'id', autoIncrement: true });
                    signalStore.createIndex('symbol', 'symbol', { unique: false });
                    signalStore.createIndex('timestamp', 'timestamp', { unique: false });
                }

                // Store for performance data
                if (!db.objectStoreNames.contains('performance')) {
                    const perfStore = db.createObjectStore('performance', { keyPath: 'id', autoIncrement: true });
                    perfStore.createIndex('timestamp', 'timestamp', { unique: false });
                }

                console.log('[OfflineData] IndexedDB schema created');
            };
        });
    }

    // Cache flow data when received from WebSocket
    async cacheFlowData(symbol, data) {
        if (!this.db) await this.init();

        const transaction = this.db.transaction(['flowData', 'recentUpdates'], 'readwrite');
        const flowStore = transaction.objectStore('flowData');
        const updateStore = transaction.objectStore('recentUpdates');

        const flowData = {
            symbol: symbol,
            ...data,
            timestamp: Date.now(),
            cached: true
        };

        // Store latest data per symbol
        await flowStore.put(flowData);

        // Store in recent updates (keep last 100 per symbol)
        await updateStore.add({
            symbol: symbol,
            data: data,
            timestamp: Date.now()
        });

        // Clean up old updates (keep only last 100 per symbol)
        const index = updateStore.index('symbol');
        const request = index.getAll(symbol);
        request.onsuccess = () => {
            const updates = request.result.sort((a, b) => b.timestamp - a.timestamp);
            if (updates.length > 100) {
                const toDelete = updates.slice(100);
                toDelete.forEach(item => updateStore.delete(item.id));
            }
        };

        console.log(`[OfflineData] Cached flow data for ${symbol}`);
    }

    // Get cached flow data for a symbol
    async getCachedFlowData(symbol) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['flowData'], 'readonly');
            const store = transaction.objectStore('flowData');
            const request = store.get(symbol);

            request.onsuccess = () => {
                resolve(request.result || null);
            };
            request.onerror = () => reject(request.error);
        });
    }

    // Get all cached symbols
    async getCachedSymbols() {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['flowData'], 'readonly');
            const store = transaction.objectStore('flowData');
            const request = store.getAll();

            request.onsuccess = () => {
                const symbols = request.result.map(item => item.symbol);
                resolve(symbols);
            };
            request.onerror = () => reject(request.error);
        });
    }

    // Cache signal data
    async cacheSignal(symbol, signalData) {
        if (!this.db) await this.init();

        const transaction = this.db.transaction(['signals'], 'readwrite');
        const store = transaction.objectStore('signals');

        await store.add({
            symbol: symbol,
            ...signalData,
            timestamp: Date.now()
        });

        console.log(`[OfflineData] Cached signal for ${symbol}`);
    }

    // Get recent signals for a symbol
    async getRecentSignals(symbol, limit = 10) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['signals'], 'readonly');
            const store = transaction.objectStore('signals');
            const index = store.index('symbol');
            const request = index.getAll(symbol);

            request.onsuccess = () => {
                const signals = request.result
                    .sort((a, b) => b.timestamp - a.timestamp)
                    .slice(0, limit);
                resolve(signals);
            };
            request.onerror = () => reject(request.error);
        });
    }

    // Cache performance data
    async cachePerformance(performanceData) {
        if (!this.db) await this.init();

        const transaction = this.db.transaction(['performance'], 'readwrite');
        const store = transaction.objectStore('performance');

        await store.add({
            ...performanceData,
            timestamp: Date.now()
        });
    }

    // Get cached performance data
    async getCachedPerformance(limit = 50) {
        if (!this.db) await this.init();

        return new Promise((resolve, reject) => {
            const transaction = this.db.transaction(['performance'], 'readonly');
            const store = transaction.objectStore('performance');
            const index = store.index('timestamp');
            const request = index.getAll();

            request.onsuccess = () => {
                const data = request.result
                    .sort((a, b) => b.timestamp - a.timestamp)
                    .slice(0, limit);
                resolve(data);
            };
            request.onerror = () => reject(request.error);
        });
    }

    // Check if we're online
    isOnline() {
        return navigator.onLine;
    }

    // Get data age in seconds
    getDataAge(timestamp) {
        if (!timestamp) return Infinity;
        return Math.floor((Date.now() - timestamp) / 1000);
    }

    // Format data age for display
    formatDataAge(seconds) {
        if (seconds < 60) return `${seconds}s ago`;
        if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
        return `${Math.floor(seconds / 3600)}h ago`;
    }

    // Queue action for sync when online
    queueAction(action) {
        this.syncQueue.push({
            ...action,
            timestamp: Date.now()
        });
        this.saveSyncQueue();
    }

    // Save sync queue to localStorage
    saveSyncQueue() {
        try {
            localStorage.setItem('flowscout_sync_queue', JSON.stringify(this.syncQueue));
        } catch (e) {
            console.warn('[OfflineData] Failed to save sync queue:', e);
        }
    }

    // Load sync queue from localStorage
    loadSyncQueue() {
        try {
            const saved = localStorage.getItem('flowscout_sync_queue');
            if (saved) {
                this.syncQueue = JSON.parse(saved);
            }
        } catch (e) {
            console.warn('[OfflineData] Failed to load sync queue:', e);
        }
    }

    // Process sync queue when online
    async processSyncQueue() {
        if (!this.isOnline() || this.syncQueue.length === 0) return;

        console.log(`[OfflineData] Processing ${this.syncQueue.length} queued actions`);

        // Process actions (e.g., send to server)
        // This would integrate with your WebSocket or API
        const processed = [];
        for (const action of this.syncQueue) {
            try {
                // Process action (implement based on your needs)
                // For now, just log it
                console.log('[OfflineData] Processing action:', action);
                processed.push(action);
            } catch (e) {
                console.error('[OfflineData] Failed to process action:', e);
            }
        }

        // Remove processed actions
        this.syncQueue = this.syncQueue.filter(a => !processed.includes(a));
        this.saveSyncQueue();
    }

    // Start background sync
    startBackgroundSync(intervalMs = 60000) {
        if (this.syncInterval) return;

        this.syncInterval = setInterval(() => {
            if (this.isOnline()) {
                this.processSyncQueue();
            }
        }, intervalMs);

        // Also process on online event
        window.addEventListener('online', () => {
            console.log('[OfflineData] Connection restored, processing sync queue');
            this.processSyncQueue();
        });
    }

    // Stop background sync
    stopBackgroundSync() {
        if (this.syncInterval) {
            clearInterval(this.syncInterval);
            this.syncInterval = null;
        }
    }

    // Clear all cached data
    async clearCache() {
        if (!this.db) await this.init();

        const stores = ['flowData', 'recentUpdates', 'signals', 'performance'];
        const transaction = this.db.transaction(stores, 'readwrite');

        await Promise.all(stores.map(storeName => {
            const store = transaction.objectStore(storeName);
            return store.clear();
        }));

        console.log('[OfflineData] Cache cleared');
    }

    // Get cache statistics
    async getCacheStats() {
        if (!this.db) await this.init();

        const stats = {
            flowData: 0,
            recentUpdates: 0,
            signals: 0,
            performance: 0,
            totalSize: 0
        };

        const stores = ['flowData', 'recentUpdates', 'signals', 'performance'];
        const transaction = this.db.transaction(stores, 'readonly');

        for (const storeName of stores) {
            const store = transaction.objectStore(storeName);
            const request = store.count();
            request.onsuccess = () => {
                stats[storeName] = request.result;
            };
        }

        // Estimate size (rough calculation)
        try {
            const estimate = await navigator.storage.estimate();
            stats.totalSize = estimate.usage || 0;
            stats.quota = estimate.quota || 0;
        } catch (e) {
            console.warn('[OfflineData] Could not estimate storage:', e);
        }

        return stats;
    }
}

// Export for use in main app
if (typeof window !== 'undefined') {
    window.OfflineDataManager = OfflineDataManager;
}

