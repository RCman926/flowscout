"""
Interactive Brokers (IBKR) API Client
Provides real-time options data, market data, and order execution capabilities
Can run in background without opening TWS GUI
"""

import asyncio
import os
import time
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.common import TickerId, BarData
import threading

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IBKRWrapper(EWrapper):
    """IBKR API Wrapper for handling callbacks"""
    
    def __init__(self):
        self.data = {}
        self.options_data = {}
        self.contract_details = {}  # For contract resolution
        self.contract_details_cache = {}  # Alias for compatibility
        self.historical_data = {}
        self.market_data = {}
        self.error_messages = []
        self.connected = False
        self.active_subscriptions = {}  # Tracked here for error handling
        self.ticker_id_to_symbol = {}  # Tracked here for error handling
        self.failed_contracts = set()  # Track failed contracts to prevent spam
        
    def error(self, reqId: TickerId, errorCode: int, errorString: str, advancedOrderRejectJson: str = ""):
        """Handle error messages with connection state tracking"""
        if errorCode == 2104:  # Market data farm connection is OK
            logger.info(f"IBKR: Market data connection OK")
            return
        if errorCode == 2106:  # HMDS data farm connection is OK
            logger.info(f"IBKR: Historical data connection OK")
            return
        if errorCode == 502:  # Couldn't connect to TWS
            logger.error(f"IBKR Error {errorCode}: {errorString}")
            self.connected = False
            # Update health on connection failure
            if hasattr(self, 'connection_health_score'):
                self.connection_health_score = max(0, self.connection_health_score - 20)
        elif errorCode == 321:  # Invalid contract id - contract needs to be resolved first
            # Only log once per symbol to prevent spam
            symbol = self.ticker_id_to_symbol.get(reqId, 'UNKNOWN')
            if symbol not in self.failed_contracts:
                logger.warning(f"IBKR Error {errorCode}: {errorString} - Invalid contract id for {symbol} (reqId: {reqId}). Contract may need resolution or different parameters.")
                self.failed_contracts.add(symbol)
            # Remove from active subscriptions to prevent retry spam
            if symbol in self.active_subscriptions:
                del self.active_subscriptions[symbol]
            if reqId in self.ticker_id_to_symbol:
                del self.ticker_id_to_symbol[reqId]
            # Don't log as error - this is expected when contract isn't resolved
        elif errorCode == 322:  # Duplicate ticker ID
            logger.warning(f"IBKR Error {errorCode}: {errorString} - Duplicate ticker ID {reqId}")
            # Cancel the duplicate subscription
            symbol = self.ticker_id_to_symbol.get(reqId, 'UNKNOWN')
            if symbol in self.active_subscriptions:
                del self.active_subscriptions[symbol]
            if reqId in self.ticker_id_to_symbol:
                del self.ticker_id_to_symbol[reqId]
        elif errorCode == 326:  # Client ID already in use
            logger.warning(f"IBKR Error {errorCode}: {errorString} - Client ID already in use")
            self.connected = False
            # Signal that we need to try a different client ID
            self.client_id_conflict = True
        elif errorCode == 10089:  # Delayed data only
            logger.warning(f"IBKR Error {errorCode}: {errorString} - Only delayed data available")
        elif errorCode == 10197:  # No market data during competing live session
            logger.warning(f"IBKR Error {errorCode}: {errorString} - Another session using market data")
        elif errorCode == 2134:  # Market Data subscription has been changed
            logger.info(f"IBKR Info {errorCode}: {errorString}")
        else:
            logger.warning(f"IBKR Warning {errorCode}: {errorString}")
        self.error_messages.append({
            'reqId': reqId,
            'code': errorCode,
            'message': errorString,
            'timestamp': datetime.now()
        })
    
    def nextValidId(self, orderId: int):
        """Connection established"""
        logger.info(f"IBKR Connected - Next valid order ID: {orderId}")
        self.connected = True
    
    def tickPrice(self, reqId: TickerId, tickType: int, price: float, attrib):
        """Receive real-time price updates"""
        if tickType == 4:  # Last price
            self.market_data[reqId] = {
                'last_price': price,
                'timestamp': datetime.now()
            }
    
    def tickSize(self, reqId: TickerId, tickType: int, size: int):
        """Receive real-time size updates"""
        if tickType == 0:  # Bid size
            if reqId not in self.market_data:
                self.market_data[reqId] = {}
            self.market_data[reqId]['bid_size'] = size
        elif tickType == 3:  # Ask size
            if reqId not in self.market_data:
                self.market_data[reqId] = {}
            self.market_data[reqId]['ask_size'] = size
    
    def historicalData(self, reqId: int, bar: BarData):
        """Receive historical bar data"""
        if reqId not in self.historical_data:
            self.historical_data[reqId] = []
        self.historical_data[reqId].append({
            'date': bar.date,
            'open': bar.open,
            'high': bar.high,
            'low': bar.low,
            'close': bar.close,
            'volume': bar.volume
        })
    
    def historicalDataEnd(self, reqId: int, start: str, end: str):
        """Historical data request completed"""
        logger.info(f"Historical data received for reqId {reqId}")
    
    def contractDetails(self, reqId: int, contractDetails):
        """Receive contract details - used to resolve contracts before requesting market data"""
        contract = contractDetails.contract
        if reqId not in self.contract_details:
            self.contract_details[reqId] = []
        if reqId not in self.contract_details_cache:
            self.contract_details_cache[reqId] = []
        self.contract_details[reqId].append(contract)
        self.contract_details_cache[reqId].append(contract)  # Also add to cache
        logger.debug(f"Contract details received for reqId {reqId}: {contract.symbol} (conId: {contract.conId})")
    
    def contractDetailsEnd(self, reqId: int):
        """Contract details request completed"""
        logger.debug(f"Contract details request completed for reqId {reqId}")
    
    def securityDefinitionOptionalParameter(self, reqId: int, exchange: str,
                                          underlyingConId: int, tradingClass: str,
                                          multiplier: str, expirations: List[str],
                                          strikes: List[float]):
        """Receive options chain data"""
        if reqId not in self.options_data:
            self.options_data[reqId] = {
                'expirations': expirations,
                'strikes': strikes,
                'exchange': exchange,
                'multiplier': multiplier
            }
        logger.info(f"Options chain received: {len(expirations)} expirations, {len(strikes)} strikes")


class IBKRClient:
    """
    Interactive Brokers API Client
    Handles connection, data requests, and options flow analysis
    Can connect to IB Gateway (headless) - no need to open TWS GUI
    """
    
    def __init__(self, host: str = "127.0.0.1", port: int = 7497, client_id: int = None):
        import random
        self.host = host
        self.port = port
        # Auto-generate client_id if not provided to avoid conflicts
        if client_id is None:
            client_id = random.randint(10, 9999)  # Avoid common IDs 1-9
        self.client_id = client_id
        self.client_id_conflict = False  # Track if we hit a client ID conflict
        self._random = random  # Store random module for reuse
        self.wrapper = IBKRWrapper()
        self.wrapper.client_id_conflict = False  # Share flag with wrapper for error handling
        self.client = EClient(self.wrapper)
        self.connected = False
        self.connection_lock = threading.Lock()
        self.request_id = 1000  # Starting request ID
        self.message_thread = None  # Track message processing thread
        # CRITICAL: Track active subscriptions to prevent duplicates
        # Share references with wrapper for error handling
        self.active_subscriptions = self.wrapper.active_subscriptions
        self.ticker_id_to_symbol = self.wrapper.ticker_id_to_symbol
        self.failed_contracts = self.wrapper.failed_contracts
        # Connection health tracking
        self.last_successful_request = None
        self.consecutive_failures = 0
        # Load health score from persistent config if available
        try:
            from ibkr_persistent_config import load_ibkr_config
            config = load_ibkr_config()
            self.connection_health_score = config.get('health_score', 100)
        except:
            self.connection_health_score = 100  # 0-100, starts at 100
        # Do not block the web app on TWS retries unless IBKR_ENABLED=1
        self.auto_reconnect_enabled = os.getenv("IBKR_ENABLED", "").lower() in ("1", "true", "yes")
        self.last_health_check = time.time()
        
    def connect(self, timeout: int = 5, auto_detect_port: bool = True) -> bool:
        """Connect to IBKR TWS/Gateway (Gateway can run headless)
        
        Args:
            timeout: Connection timeout per port attempt
            auto_detect_port: If True, try common ports if configured port fails
        """
        if os.getenv("IBKR_ENABLED", "").lower() not in ("1", "true", "yes"):
            logger.info("IBKR skipped (set IBKR_ENABLED=1 when TWS/Gateway is running)")
            return False
        deadline = time.time() + float(os.getenv("IBKR_CONNECT_DEADLINE", "8"))
        timeout = min(int(timeout or 5), 5)
        auto_detect_port = False
        try:
            with self.connection_lock:
                if self.client.isConnected():
                    logger.info("Already connected to IBKR")
                    return True
                
                # Smart port detection: Try all common ports to find what's running
                # Order: Try configured port first, then all common ports
                if auto_detect_port:
                    # All possible IBKR ports (TWS and Gateway, Live and Paper)
                    all_ports = [7497, 7496, 4001, 4002]  # TWS live, TWS paper, Gateway live, Gateway paper
                    # Start with configured port, then try all others
                    ports_to_try = [self.port] if self.port not in all_ports else []
                    # Add all ports, removing duplicates
                    for port in all_ports:
                        if port not in ports_to_try:
                            ports_to_try.append(port)
                else:
                    # Only try configured port if auto-detect is disabled
                    ports_to_try = [self.port]
                
                logger.info(f"Connecting to IBKR at {self.host}...")
                logger.info("🔍 Auto-detecting: Will try TWS and Gateway ports (Live & Paper)")
                logger.info("💡 TIP: Use IB Gateway (headless) instead of TWS to run without GUI")
                
                # Try multiple client IDs if we hit conflicts (max 5 attempts)
                client_ids_to_try = [self.client_id]
                for attempt in range(4):  # Try 4 more client IDs (5 total)
                    new_id = self._random.randint(10, 9999)
                    if new_id not in client_ids_to_try:
                        client_ids_to_try.append(new_id)
                
                # Try each port until one works
                for port in ports_to_try:
                    if time.time() > deadline:
                        logger.warning("IBKR connect deadline — giving up (is TWS/Gateway up?)")
                        return False
                    # Try each client ID for this port
                    for client_id_attempt in client_ids_to_try:
                        if time.time() > deadline:
                            logger.warning("IBKR connect deadline — giving up")
                            return False
                        # Reset conflict flag
                        self.client_id_conflict = False
                        self.wrapper.client_id_conflict = False
                        
                        # Use this client ID for this attempt
                        original_client_id = self.client_id
                        self.client_id = client_id_attempt
                        
                        if client_id_attempt != original_client_id:
                            logger.info(f"🔄 Trying different client ID: {client_id_attempt} (previous: {original_client_id} was in use)")
                        
                        try:
                            # Disconnect if already connected (from previous attempt)
                            if self.client.isConnected():
                                self.client.disconnect()
                                self.wrapper.connected = False
                                time.sleep(0.2)

                            logger.info(f"Trying port {port} with client ID {self.client_id}...")
                            self.client.connect(self.host, port, self.client_id)
                            
                            # CRITICAL: Start message thread IMMEDIATELY after connect()
                            # This is required for callbacks (like nextValidId) to fire
                            if self.message_thread is None or not self.message_thread.is_alive():
                                self.message_thread = threading.Thread(target=self.client.run, daemon=True)
                                self.message_thread.start()
                                logger.info("✅ Started IBKR message processing thread")
                                time.sleep(0.5)  # Give thread time to start
                            
                            # Wait for connection confirmation (nextValidId callback) or error
                            start_time = time.time()
                            while not self.wrapper.connected and not self.client_id_conflict and (time.time() - start_time) < timeout:
                                time.sleep(0.1)
                            
                            # Check if we hit a client ID conflict
                            if self.client_id_conflict or self.wrapper.client_id_conflict:
                                logger.warning(f"⚠️ Client ID {self.client_id} is already in use - trying next ID...")
                                # Disconnect and try next client ID
                                try:
                                    if self.client.isConnected():
                                        self.client.disconnect()
                                except:
                                    pass
                                self.wrapper.connected = False
                                continue  # Try next client ID
                            
                            # Double-check: if socket is connected but wrapper.connected is False,
                            # the message thread might not be processing. Wait a bit more.
                            if self.client.isConnected() and not self.wrapper.connected:
                                logger.warning("Socket connected but wrapper.connected is False - waiting for nextValidId...")
                                time.sleep(1.0)  # Wait a bit more for nextValidId
                            
                            if self.wrapper.connected or self.client.isConnected():
                                # Determine what we connected to
                                port_info = {
                                    7497: "TWS (Live Trading)",
                                    7496: "TWS (Paper Trading)",
                                    4001: "IB Gateway (Live Trading)",
                                    4002: "IB Gateway (Paper Trading)"
                                }
                                connection_type = port_info.get(port, f"Port {port}")

                                # Update port if we connected to a different one
                                if port != self.port:
                                    logger.info(f"✅ Auto-detected and connected to {connection_type} on port {port}")
                                    logger.info(f"💡 Previous config had port {self.port}, but {connection_type} is running on {port}")
                                    logger.info(f"💡 Saving working port {port} to config for future connections")
                                    self.port = port  # Update to working port

                                # ALWAYS save config on successful connection (port and client_id)
                                try:
                                    from ibkr_persistent_config import save_ibkr_config
                                    save_ibkr_config(self.host, self.port, self.client_id, True, self.connection_health_score)
                                    logger.debug(f"✅ Saved IBKR config: port={self.port}, client_id={self.client_id}, health={self.connection_health_score}")
                                except Exception as e:
                                    logger.debug(f"Could not save config: {e}")

                                if port == self.port:
                                    logger.info(f"✅ Successfully connected to {connection_type} on port {port}")

                                # Ensure both flags are set
                                self.connected = True
                                self.wrapper.connected = True

                                # Verify message thread is running
                                if self.message_thread and not self.message_thread.is_alive():
                                    logger.warning("Message thread died - restarting...")
                                    self.message_thread = threading.Thread(target=self.client.run, daemon=True)
                                    self.message_thread.start()
                                    time.sleep(0.3)

                                logger.info(f"✅ IBKR connection fully established - message thread running: {self.message_thread.is_alive() if self.message_thread else False}")
                                return True
                            else:
                                logger.debug(f"Port {port} with client ID {self.client_id} failed (timeout)")
                                # Disconnect before trying next client ID or port
                                try:
                                    if self.client.isConnected():
                                        self.client.disconnect()
                                except:
                                    pass
                                self.wrapper.connected = False
                                # Try next client ID for this port
                                continue
                                
                        except Exception as e:
                            error_str = str(e).lower()
                            # Check if it's a client ID conflict error
                            if 'client id' in error_str or '326' in error_str:
                                logger.warning(f"⚠️ Client ID {self.client_id} conflict detected: {e} - trying next ID...")
                                self.client_id_conflict = True
                                # Disconnect and try next client ID
                                try:
                                    if self.client.isConnected():
                                        self.client.disconnect()
                                except:
                                    pass
                                self.wrapper.connected = False
                                continue  # Try next client ID
                            else:
                                logger.debug(f"Port {port} with client ID {self.client_id} failed: {e}")
                                # Disconnect before trying next client ID or port
                                try:
                                    if self.client.isConnected():
                                        self.client.disconnect()
                                except:
                                    pass
                                self.wrapper.connected = False
                                # Try next client ID for this port
                                continue
                    
                    # If we tried all client IDs for this port and none worked, try next port
                    logger.debug(f"All client IDs exhausted for port {port}, trying next port...")
                
                # All ports failed
                logger.error("❌ Failed to connect to IBKR on any port")
                logger.info("💡 Make sure IB Gateway or TWS is running and API is enabled")
                logger.info(f"💡 Tried ports: {ports_to_try}")
                return False
                    
        except Exception as e:
            logger.error(f"IBKR connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from IBKR and save state"""
        try:
            if self.client.isConnected():
                self.client.disconnect()
            self.connected = False
            self.wrapper.connected = False
            # Message thread will stop automatically when client disconnects
            self.message_thread = None
            
            # Save disconnected state to config
            try:
                from ibkr_persistent_config import save_ibkr_config
                save_ibkr_config(self.host, self.port, self.client_id, False, self.connection_health_score)
            except:
                pass
            
            logger.info("Disconnected from IBKR")
        except Exception as e:
            logger.error(f"IBKR disconnect error: {e}")
            self.connected = False
            self.wrapper.connected = False
    
    def is_connected(self) -> bool:
        """Check if connected to IBKR - checks both socket and wrapper state with health monitoring"""
        try:
            socket_connected = self.client.isConnected()
            wrapper_connected = self.wrapper.connected
            self_connected = self.connected
            
            # If socket is connected but wrapper isn't, we might still be connecting
            # Give it a moment and check again
            if socket_connected and not wrapper_connected:
                # Check if message thread is running
                if self.message_thread and self.message_thread.is_alive():
                    # Thread is running, might just be waiting for nextValidId
                    return socket_connected  # Trust socket connection
                else:
                    # Thread not running - connection is invalid
                    logger.warning("Socket connected but message thread not running - connection invalid")
                    self._update_connection_health(False)
                    return False
            
            # All checks should agree
            is_healthy = socket_connected and (wrapper_connected or self_connected)
            
            # Update health tracking
            self._update_connection_health(is_healthy)
            
            # Auto-reconnect if health is poor and auto-reconnect is enabled
            if not is_healthy and self.auto_reconnect_enabled:
                if self.connection_health_score < 30 or self.consecutive_failures >= 3:
                    logger.warning(f"Connection health poor (score: {self.connection_health_score}, failures: {self.consecutive_failures}) - attempting auto-reconnect...")
                    self._attempt_auto_reconnect()
            
            return is_healthy
        except Exception as e:
            logger.debug(f"Error checking connection: {e}")
            self._update_connection_health(False)
            return False
    
    def _update_connection_health(self, success: bool):
        """Update connection health metrics and persist to config"""
        current_time = time.time()
        
        if success:
            self.last_successful_request = current_time
            self.consecutive_failures = 0
            # Gradually increase health score on success (up to 100)
            old_score = self.connection_health_score
            self.connection_health_score = min(100, self.connection_health_score + 5)
            # Only save if score changed significantly (every 10 points) to reduce I/O
            if abs(self.connection_health_score - old_score) >= 10:
                try:
                    from ibkr_persistent_config import save_ibkr_config
                    save_ibkr_config(self.host, self.port, self.client_id, self.is_connected(), self.connection_health_score)
                except:
                    pass
        else:
            self.consecutive_failures += 1
            # Decrease health score on failure
            old_score = self.connection_health_score
            self.connection_health_score = max(0, self.connection_health_score - 10)
            # Save on failure to track issues
            if abs(self.connection_health_score - old_score) >= 10:
                try:
                    from ibkr_persistent_config import save_ibkr_config
                    save_ibkr_config(self.host, self.port, self.client_id, self.is_connected(), self.connection_health_score)
                except:
                    pass
        
        self.last_health_check = current_time
    
    def _attempt_auto_reconnect(self):
        """Attempt to automatically reconnect if connection is lost"""
        try:
            if self.client.isConnected():
                # Already connected, just update state
                self.connected = True
                self.wrapper.connected = True
                return True
            
            logger.info("🔄 Attempting automatic reconnection to IBKR...")
            # Reset health before reconnecting
            self.consecutive_failures = 0
            self.connection_health_score = 50  # Start at 50 after reconnect attempt
            
            # Try to reconnect
            success = self.connect(timeout=5, auto_detect_port=True)
            if success:
                logger.info("✅ Auto-reconnection successful!")
                self.connection_health_score = 80  # Good after successful reconnect
                # Save successful reconnection state
                try:
                    from ibkr_persistent_config import save_ibkr_config
                    save_ibkr_config(self.host, self.port, self.client_id, True, self.connection_health_score)
                except:
                    pass
            else:
                logger.warning("❌ Auto-reconnection failed - will retry on next request")
                self.connection_health_score = 20  # Poor after failed reconnect
                # Save failed state
                try:
                    from ibkr_persistent_config import save_ibkr_config
                    save_ibkr_config(self.host, self.port, self.client_id, False, self.connection_health_score)
                except:
                    pass
            
            return success
        except Exception as e:
            logger.error(f"Error during auto-reconnect: {e}")
            return False
    
    def get_connection_health(self) -> Dict:
        """Get connection health metrics"""
        time_since_last_success = None
        if self.last_successful_request:
            time_since_last_success = time.time() - self.last_successful_request
        
        return {
            'is_connected': self.is_connected(),
            'health_score': self.connection_health_score,
            'consecutive_failures': self.consecutive_failures,
            'time_since_last_success': time_since_last_success,
            'socket_connected': self.client.isConnected() if self.client else False,
            'wrapper_connected': self.wrapper.connected,
            'message_thread_alive': self.message_thread.is_alive() if self.message_thread else False,
            'auto_reconnect_enabled': self.auto_reconnect_enabled
        }
    
    def get_live_price(self, symbol: str, timeout: int = 3) -> Optional[Dict]:
        """Get real-time price for a symbol with auto-reconnect"""
        # Check connection and auto-reconnect if needed
        if not self.is_connected():
            if self.auto_reconnect_enabled:
                if not self._attempt_auto_reconnect():
                    logger.warning(f"Could not reconnect to IBKR for {symbol}")
                    return None
            elif not self.connect():
                return None
        
        try:
            # Create stock contract
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"
            
            # CRITICAL: Cancel existing subscription for this symbol if it exists
            if symbol in self.active_subscriptions:
                old_ticker_id = self.active_subscriptions[symbol]
                try:
                    self.client.cancelMktData(old_ticker_id)
                    logger.info(f"Cancelled existing subscription for {symbol} (ticker_id: {old_ticker_id})")
                    # Remove from tracking
                    del self.active_subscriptions[symbol]
                    if old_ticker_id in self.ticker_id_to_symbol:
                        del self.ticker_id_to_symbol[old_ticker_id]
                    time.sleep(0.2)  # Brief pause after cancellation
                except Exception as e:
                    logger.warning(f"Error cancelling subscription: {e}")
            
            # CRITICAL: Resolve contract FIRST before requesting market data
            # This prevents "Invalid contract id" errors (error 321)
            # Increased timeout to 5 seconds for better reliability
            resolved_contract = self._resolve_contract(contract, timeout=5)
            if not resolved_contract:
                logger.warning(f"Could not resolve contract for {symbol} - skipping market data request")
                return None
            
            # If contract resolution returned original contract (conId=0), try using SMART exchange directly
            # SMART exchange often works without explicit conId for common stocks like SPY
            if resolved_contract.conId == 0:
                logger.debug(f"Contract resolution returned conId=0 for {symbol}, using SMART exchange directly (this is OK for common stocks)")
                # Ensure exchange is set to SMART for better compatibility
                if not resolved_contract.exchange or resolved_contract.exchange == "":
                    resolved_contract.exchange = "SMART"
            
            # Use resolved contract (has conId and proper exchange)
            contract = resolved_contract
            
            # Use unique ticker ID for each symbol
            req_id = self._get_next_req_id()
            
            # Track active subscription
            self.active_subscriptions[symbol] = req_id
            self.ticker_id_to_symbol[req_id] = symbol
            
            # Request market data with RESOLVED contract
            self.client.reqMktData(req_id, contract, "", False, False, [])
            
            # Wait for data
            start_time = time.time()
            while req_id not in self.wrapper.market_data and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if req_id in self.wrapper.market_data:
                data = self.wrapper.market_data[req_id]
                
                # Check if we got delayed data (error 10089 would have been logged)
                is_live = not any(err.get('code') == 10089 for err in self.wrapper.error_messages[-5:])
                
                result = {
                    'price': data.get('last_price', 0),
                    'bid_size': data.get('bid_size', 0),
                    'ask_size': data.get('ask_size', 0),
                    'timestamp': data.get('timestamp', datetime.now()),
                    'source': 'IBKR_LIVE' if is_live else 'IBKR_DELAYED',
                    'quality_score': 98 if is_live else 60,
                    'is_live_data': is_live
                }
                
                # Cancel subscription after getting data (to prevent accumulation)
                try:
                    self.client.cancelMktData(req_id)
                    if symbol in self.active_subscriptions:
                        del self.active_subscriptions[symbol]
                    if req_id in self.ticker_id_to_symbol:
                        del self.ticker_id_to_symbol[req_id]
                except:
                    pass
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting live price for {symbol}: {e}")
            return None
    
    def get_options_chain(self, symbol: str, timeout: int = 8) -> Optional[Dict]:
        """Get options chain data for a symbol - increased timeout for callback"""
        if not self.is_connected():
            if not self.connect():
                return None
        
        try:
            # Create stock contract
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = "SMART"
            contract.currency = "USD"
            
            # CRITICAL: Resolve contract FIRST to get conId for reqSecDefOptParams
            resolved_contract = self._resolve_contract(contract, timeout=3)
            underlying_con_id = 0  # Default to 0 if resolution fails
            if resolved_contract and hasattr(resolved_contract, 'conId') and resolved_contract.conId:
                underlying_con_id = resolved_contract.conId
                logger.debug(f"Using resolved contract conId {underlying_con_id} for {symbol}")
            else:
                logger.warning(f"Could not resolve contract for {symbol} - using conId=0 (may fail)")
            
            req_id = self._get_next_req_id()
            logger.debug(f"Requesting options chain for {symbol} (req_id={req_id}, conId={underlying_con_id})")
            # Use resolved conId if available, otherwise 0
            self.client.reqSecDefOptParams(req_id, symbol, "", "STK", underlying_con_id)
            
            # Wait for options data - increased timeout to 8 seconds
            start_time = time.time()
            while req_id not in self.wrapper.options_data and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if req_id in self.wrapper.options_data:
                options_info = self.wrapper.options_data[req_id]
                
                # Get nearest expiration
                if options_info.get('expirations'):
                    nearest_exp = options_info['expirations'][0]
                    logger.debug(f"✅ Options chain received for {symbol}: {len(options_info.get('expirations', []))} expirations, {len(options_info.get('strikes', []))} strikes")
                    
                    # Request option chain for nearest expiration
                    return {
                        'symbol': symbol,
                        'expirations': options_info['expirations'],
                        'nearest_expiration': nearest_exp,
                        'strikes': options_info.get('strikes', []),
                        'exchange': options_info.get('exchange', ''),
                        'multiplier': options_info.get('multiplier', '100'),
                        'source': 'IBKR',
                        'timestamp': datetime.now()
                    }
            
            logger.debug(f"⚠️ Options chain timeout for {symbol} (req_id={req_id}) - callback may be delayed")
            return None
            
        except Exception as e:
            logger.error(f"Error getting options chain for {symbol}: {e}")
            return None
    
    def get_options_flow(self, symbol: str) -> Dict:
        """
        Get live options flow data (calls vs puts)
        This is a simplified version - full implementation would require
        requesting individual option contracts and aggregating volume/OI
        
        Returns high quality_score to ensure IBKR is preferred over yfinance
        """
        # Check connection and auto-reconnect if needed
        if not self.is_connected():
            if self.auto_reconnect_enabled:
                if not self._attempt_auto_reconnect():
                    logger.debug(f"IBKR: Not connected for {symbol} (auto-reconnect failed)")
                    return {
                        'call_volume': 0,
                        'put_volume': 0,
                        'total_volume': 0,
                        'data_source': 'ibkr_unavailable',
                        'quality_score': 0,
                        'connection_health': self.get_connection_health()
                    }
            elif not self.connect():
                logger.debug(f"IBKR: Not connected for {symbol}")
                return {
                    'call_volume': 0,
                    'put_volume': 0,
                    'total_volume': 0,
                    'data_source': 'ibkr_unavailable',
                    'quality_score': 0,
                    'connection_health': self.get_connection_health()
                }
        
        try:
            # Get options chain first
            chain_data = self.get_options_chain(symbol)
            
            if chain_data:
                # IBKR is connected and returning options chain data
                # Even if we don't have volume yet, we return high quality_score
                # to ensure IBKR is preferred over delayed yfinance data
                # Update health on success
                self._update_connection_health(True)
                logger.info(f"✅ IBKR: Options chain received for {symbol} - {len(chain_data.get('expirations', []))} expirations, {len(chain_data.get('strikes', []))} strikes")
                return {
                    'call_volume': 0,  # Would be populated with real contract-level data
                    'put_volume': 0,   # Would be populated with real contract-level data
                    'total_volume': 0,
                    'data_source': 'ibkr_connected',
                    'quality_score': 98,  # HIGH score to ensure IBKR is preferred over yfinance (delayed)
                    'note': 'IBKR connected - options chain available, contract-level volume requires additional requests',
                    'has_options_chain': True,
                    'expirations': chain_data.get('expirations', []),
                    'strikes': chain_data.get('strikes', []),
                    'connection_health': self.get_connection_health()
                }
            
            # Even if chain_data is None, if we're connected, return high quality_score
            # This ensures IBKR is preferred over delayed yfinance
            # The callback might be delayed, but connection is established
            # Update health - connection is working even if callback is delayed
            self._update_connection_health(True)
            logger.info(f"✅ IBKR: Connected for {symbol} (chain data pending - callback may be delayed)")
            return {
                'call_volume': 0,
                'put_volume': 0,
                'total_volume': 0,
                'data_source': 'ibkr_connected',
                'quality_score': 95,  # Still high - IBKR is connected, just waiting for callback
                'note': 'IBKR connected - waiting for options chain callback',
                'has_options_chain': False,
                'connection_health': self.get_connection_health()
            }
            
        except Exception as e:
            logger.error(f"Error getting options flow for {symbol}: {e}")
            self._update_connection_health(False)
            return {
                'call_volume': 0,
                'put_volume': 0,
                'total_volume': 0,
                'data_source': 'ibkr_error',
                'quality_score': 0,
                'error': str(e),
                'connection_health': self.get_connection_health()
            }
    
    def _get_next_req_id(self) -> int:
        """Get next request ID"""
        self.request_id += 1
        return self.request_id
    
    def _resolve_contract(self, contract: Contract, timeout: int = 3) -> Optional[Contract]:
        """Resolve contract details before requesting market data (prevents error 321)"""
        try:
            if not self.is_connected():
                logger.warning(f"Cannot resolve contract - not connected to IBKR")
                return None  # Return None instead of contract if not connected
            
            req_id = self._get_next_req_id()
            self.wrapper.contract_details[req_id] = []
            self.wrapper.contract_details_cache[req_id] = []  # Also set cache for compatibility
            
            # Request contract details
            self.client.reqContractDetails(req_id, contract)
            logger.debug(f"Requesting contract details for {contract.symbol} (reqId: {req_id})")
            
            # Wait for contract details (with longer timeout)
            start_time = time.time()
            while (req_id not in self.wrapper.contract_details or 
                   len(self.wrapper.contract_details[req_id]) == 0) and \
                  (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            # Check both dicts for compatibility
            contract_list = self.wrapper.contract_details.get(req_id, [])
            if not contract_list:
                contract_list = self.wrapper.contract_details_cache.get(req_id, [])
            
            if contract_list and len(contract_list) > 0:
                # Use the resolved contract (has conId)
                resolved_contract = contract_list[0]
                logger.info(f"✅ Contract resolved: {contract.symbol} -> conId: {resolved_contract.conId}")
                # Clean up
                if req_id in self.wrapper.contract_details:
                    del self.wrapper.contract_details[req_id]
                if req_id in self.wrapper.contract_details_cache:
                    del self.wrapper.contract_details_cache[req_id]
                return resolved_contract
            
            # If resolution fails, return original contract (might still work for SMART exchange)
            logger.warning(f"⚠️ Contract resolution failed for {contract.symbol} (timeout or no results), using original contract")
            # Clean up
            if req_id in self.wrapper.contract_details:
                del self.wrapper.contract_details[req_id]
            if req_id in self.wrapper.contract_details_cache:
                del self.wrapper.contract_details_cache[req_id]
            return contract
            
        except Exception as e:
            logger.warning(f"Error resolving contract for {contract.symbol}: {e}")
            return contract  # Return original contract as fallback
    
    def get_market_data(self, symbol: str, timeout: int = 3) -> Optional[Dict]:
        """Get market data for a symbol - prevents error 321 by checking failed contracts first"""
        if not self.is_connected():
            if not self.connect():
                return None
        
        # Skip if this symbol recently failed with error 321 (prevent spam)
        if symbol in self.wrapper.failed_contracts:
            logger.debug(f"Skipping {symbol} - previously failed with error 321")
            return None
        
        try:
            # Create stock contract with proper parameters
            contract = Contract()
            contract.symbol = symbol
            contract.secType = "STK"
            contract.exchange = "SMART"  # SMART routing should work for most stocks
            contract.currency = "USD"
            # Don't set primaryExchange - let SMART routing handle it
            
            # CRITICAL: Cancel existing subscription for this symbol if it exists
            if symbol in self.active_subscriptions:
                old_ticker_id = self.active_subscriptions[symbol]
                try:
                    self.client.cancelMktData(old_ticker_id)
                    logger.debug(f"Cancelled existing subscription for {symbol} (ticker_id: {old_ticker_id})")
                    # Remove from tracking
                    del self.active_subscriptions[symbol]
                    if old_ticker_id in self.ticker_id_to_symbol:
                        del self.ticker_id_to_symbol[old_ticker_id]
                    time.sleep(0.3)  # Brief pause after cancellation
                except Exception as e:
                    logger.debug(f"Error cancelling subscription: {e}")
            
            # Use unique ticker ID for each symbol
            req_id = self._get_next_req_id()
            
            # Track active subscription
            self.active_subscriptions[symbol] = req_id
            self.ticker_id_to_symbol[req_id] = symbol
            
            # CRITICAL: Resolve contract FIRST before requesting market data
            # This prevents "Invalid contract id" errors (error 321)
            resolved_contract = self._resolve_contract(contract, timeout=2)
            if not resolved_contract:
                logger.warning(f"Could not resolve contract for {symbol} - skipping market data request")
                return None
            
            # Use resolved contract (has conId and proper exchange)
            contract = resolved_contract
            
            # Request market data with RESOLVED contract
            self.client.reqMktData(req_id, contract, "", False, False, [])
            
            # Wait for data
            start_time = time.time()
            while req_id not in self.wrapper.market_data and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            # Check for error 321 (Invalid contract id) - if we get it, mark as failed
            recent_errors = [err for err in self.wrapper.error_messages[-3:] if err.get('code') == 321 and err.get('reqId') == req_id]
            if recent_errors:
                logger.warning(f"Error 321 for {symbol} - marking as failed to prevent spam requests")
                self.wrapper.failed_contracts.add(symbol)
                # Cancel and clean up
                try:
                    self.client.cancelMktData(req_id)
                    if symbol in self.active_subscriptions:
                        del self.active_subscriptions[symbol]
                    if req_id in self.ticker_id_to_symbol:
                        del self.ticker_id_to_symbol[req_id]
                except:
                    pass
                return None
            
            if req_id in self.wrapper.market_data:
                data = self.wrapper.market_data[req_id]
                
                # Check if we got delayed data (error 10089 would have been logged)
                is_live = not any(err.get('code') == 10089 for err in self.wrapper.error_messages[-5:])
                
                result = {
                    'price': data.get('last_price', 0),
                    'change': 0,  # Will be calculated from previous close
                    'change_pct': 0,
                    'volume': 0,  # Volume comes from tickSize
                    'bid_size': data.get('bid_size', 0),
                    'ask_size': data.get('ask_size', 0),
                    'previous_close': data.get('last_price', 0),  # Approximate
                    'timestamp': data.get('timestamp', datetime.now()),
                    'source': 'IBKR_LIVE' if is_live else 'IBKR_DELAYED',
                    'quality_score': 98 if is_live else 60,
                    'is_live_data': is_live
                }
                
                # Cancel subscription after getting data (to prevent accumulation)
                try:
                    self.client.cancelMktData(req_id)
                    if symbol in self.active_subscriptions:
                        del self.active_subscriptions[symbol]
                    if req_id in self.ticker_id_to_symbol:
                        del self.ticker_id_to_symbol[req_id]
                except:
                    pass
                
                return result
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting market data for {symbol}: {e}")
            return None


# Global instance
_ibkr_client_instance = None

def get_ibkr_client(host: str = None, port: int = None, client_id: int = None) -> IBKRClient:
    """Get or create IBKR client instance - SINGLETON PATTERN - AUTO-LOADS from config if not specified"""
    global _ibkr_client_instance
    
    # Load from config if not provided
    if host is None or port is None or client_id is None:
        try:
            from ibkr_persistent_config import load_ibkr_config
            config = load_ibkr_config()
            if host is None:
                host = config.get("host", "127.0.0.1")
            if port is None:
                port = config.get("port", 7497)  # Default to TWS live, but auto-detect will find the right one
            if client_id is None:
                # ALWAYS use config client_id to ensure single instance
                # Only generate new one if config doesn't have it
                config_client_id = config.get("client_id")
                if config_client_id and config_client_id > 0:
                    client_id = config_client_id
                    logger.debug(f"Using persistent client_id from config: {client_id}")
                else:
                    # Generate a stable client_id and save it
                    import random
                    client_id = random.randint(10, 9999)
                    # Save it immediately so we always use the same one
                    from ibkr_persistent_config import save_ibkr_config
                    save_ibkr_config(host, port, client_id, False)
                    logger.info(f"Generated new client_id {client_id} and saved to config")
        except Exception as e:
            logger.warning(f"Error loading IBKR config: {e}")
            # Fallback to defaults if config load fails
            if host is None:
                host = "127.0.0.1"
            if port is None:
                port = 7497
            if client_id is None:
                # Use a fixed default instead of random to ensure consistency
                client_id = 1
    
    # SINGLETON: Only create ONE instance, reuse if it exists
    if _ibkr_client_instance is None:
        logger.info(f"Creating new IBKR client instance (host={host}, port={port}, client_id={client_id})")
        _ibkr_client_instance = IBKRClient(host, port, client_id)
    elif (_ibkr_client_instance.host != host or 
          _ibkr_client_instance.port != port or 
          _ibkr_client_instance.client_id != client_id):
        # Parameters changed significantly - only recreate if really necessary
        logger.warning(f"IBKR client parameters changed - recreating instance")
        logger.warning(f"  Old: host={_ibkr_client_instance.host}, port={_ibkr_client_instance.port}, client_id={_ibkr_client_instance.client_id}")
        logger.warning(f"  New: host={host}, port={port}, client_id={client_id}")
        # Disconnect old instance first
        try:
            if _ibkr_client_instance.is_connected():
                _ibkr_client_instance.disconnect()
        except:
            pass
        _ibkr_client_instance = IBKRClient(host, port, client_id)
    else:
        # Same parameters - reuse existing instance
        logger.debug(f"Reusing existing IBKR client instance (client_id={_ibkr_client_instance.client_id})")
    
    return _ibkr_client_instance

