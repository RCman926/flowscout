"""
User Authentication System
Simple, secure authentication for multi-user support
"""

import json
import os
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class UserAuth:
    """
    Simple authentication system for multi-user support
    Uses secure password hashing and session tokens
    """
    
    def __init__(self):
        self.users_file = "users.json"
        self.sessions_file = "sessions.json"
        self.users = {}  # username -> {password_hash, email, created_at, preferences}
        self.sessions = {}  # token -> {username, expires_at}
        self.session_duration_hours = 24  # Sessions last 24 hours
        
        self._load_users()
        self._load_sessions()
        self._cleanup_expired_sessions()
    
    def _load_users(self):
        """Load users from file"""
        try:
            if os.path.exists(self.users_file):
                with open(self.users_file, 'r') as f:
                    self.users = json.load(f)
                logger.info(f"Loaded {len(self.users)} users")
        except Exception as e:
            logger.error(f"Error loading users: {e}")
            self.users = {}
    
    def _save_users(self):
        """Save users to file"""
        try:
            with open(self.users_file, 'w') as f:
                json.dump(self.users, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving users: {e}")
    
    def _load_sessions(self):
        """Load sessions from file"""
        try:
            if os.path.exists(self.sessions_file):
                with open(self.sessions_file, 'r') as f:
                    data = json.load(f)
                    # Convert expires_at strings back to datetime for validation
                    for token, session in data.items():
                        if isinstance(session.get('expires_at'), str):
                            try:
                                session['expires_at'] = datetime.fromisoformat(session['expires_at'])
                            except:
                                pass
                    self.sessions = data
        except Exception as e:
            logger.error(f"Error loading sessions: {e}")
            self.sessions = {}
    
    def _save_sessions(self):
        """Save sessions to file"""
        try:
            # Convert datetime to string for JSON
            sessions_to_save = {}
            for token, session in self.sessions.items():
                sessions_to_save[token] = {
                    'username': session['username'],
                    'expires_at': session['expires_at'].isoformat() if isinstance(session['expires_at'], datetime) else session['expires_at']
                }
            with open(self.sessions_file, 'w') as f:
                json.dump(sessions_to_save, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving sessions: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256 with salt"""
        salt = secrets.token_hex(16)
        hash_obj = hashlib.sha256()
        hash_obj.update((password + salt).encode())
        return f"{salt}:{hash_obj.hexdigest()}"
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash"""
        try:
            salt, stored_hash = password_hash.split(':')
            hash_obj = hashlib.sha256()
            hash_obj.update((password + salt).encode())
            return hash_obj.hexdigest() == stored_hash
        except:
            return False
    
    def _cleanup_expired_sessions(self):
        """Remove expired sessions"""
        now = datetime.now()
        expired = [token for token, session in self.sessions.items() 
                  if isinstance(session.get('expires_at'), datetime) and session['expires_at'] < now]
        for token in expired:
            del self.sessions[token]
        if expired:
            self._save_sessions()
    
    def register_user(self, username: str, password: str, email: Optional[str] = None) -> Tuple[bool, str]:
        """
        Register a new user
        
        Returns:
            (success, message)
        """
        if username in self.users:
            return False, "Username already exists"
        
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        
        password_hash = self._hash_password(password)
        self.users[username] = {
            'password_hash': password_hash,
            'email': email,
            'created_at': datetime.now().isoformat(),
            'preferences': {
                'watchlist': ['SPY'],
                'theme': 'dark',
                'notifications_enabled': True,
                'default_account_size': 10000
            }
        }
        self._save_users()
        logger.info(f"New user registered: {username}")
        return True, "User registered successfully"
    
    def login(self, username: str, password: str) -> Tuple[bool, Optional[str], str]:
        """
        Login user and create session
        
        Returns:
            (success, token, message)
        """
        if username not in self.users:
            return False, None, "Invalid username or password"
        
        if not self._verify_password(password, self.users[username]['password_hash']):
            return False, None, "Invalid username or password"
        
        # Create session token
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now() + timedelta(hours=self.session_duration_hours)
        
        self.sessions[token] = {
            'username': username,
            'expires_at': expires_at
        }
        self._save_sessions()
        
        logger.info(f"User logged in: {username}")
        return True, token, "Login successful"
    
    def verify_token(self, token: str) -> Tuple[bool, Optional[str]]:
        """
        Verify session token
        
        Returns:
            (is_valid, username)
        """
        self._cleanup_expired_sessions()
        
        if token not in self.sessions:
            return False, None
        
        session = self.sessions[token]
        expires_at = session.get('expires_at')
        
        if isinstance(expires_at, str):
            try:
                expires_at = datetime.fromisoformat(expires_at)
            except:
                return False, None
        
        if expires_at < datetime.now():
            del self.sessions[token]
            self._save_sessions()
            return False, None
        
        return True, session['username']
    
    def logout(self, token: str) -> bool:
        """Logout user (invalidate session)"""
        if token in self.sessions:
            del self.sessions[token]
            self._save_sessions()
            return True
        return False
    
    def get_user_preferences(self, username: str) -> Dict:
        """Get user preferences"""
        if username in self.users:
            return self.users[username].get('preferences', {})
        return {}
    
    def update_user_preferences(self, username: str, preferences: Dict) -> bool:
        """Update user preferences"""
        if username not in self.users:
            return False
        
        current_prefs = self.users[username].get('preferences', {})
        current_prefs.update(preferences)
        self.users[username]['preferences'] = current_prefs
        self._save_users()
        return True
    
    def get_user_watchlist(self, username: str) -> list:
        """Get user's watchlist"""
        prefs = self.get_user_preferences(username)
        return prefs.get('watchlist', ['SPY'])
    
    def update_user_watchlist(self, username: str, watchlist: list) -> bool:
        """Update user's watchlist"""
        prefs = self.get_user_preferences(username)
        prefs['watchlist'] = watchlist
        return self.update_user_preferences(username, prefs)


# Global instance
user_auth = UserAuth()

