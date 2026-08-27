"""
Input Sanitization & Validation
Comprehensive input validation for security and data integrity
"""

import re
import logging
from typing import Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class InputValidator:
    """
    Input validation and sanitization utilities
    Prevents injection attacks and ensures data integrity
    """
    
    # Symbol validation regex
    SYMBOL_PATTERN = re.compile(r'^[A-Z]{1,5}$')
    
    # Numeric validation
    NUMERIC_PATTERN = re.compile(r'^-?\d+(\.\d+)?$')
    
    @staticmethod
    def validate_symbol(symbol: str) -> Tuple[bool, Optional[str]]:
        """
        Validate stock symbol format
        
        Args:
            symbol: Stock symbol to validate
            
        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        if not isinstance(symbol, str):
            return False, "Symbol must be a string"
        
        if not symbol:
            return False, "Symbol cannot be empty"
        
        if not InputValidator.SYMBOL_PATTERN.match(symbol):
            return False, f"Invalid symbol format: {symbol}. Must be 1-5 uppercase letters"
        
        return True, None
    
    @staticmethod
    def sanitize_symbol(symbol: str) -> str:
        """
        Sanitize stock symbol
        
        Args:
            symbol: Stock symbol to sanitize
            
        Returns:
            Sanitized symbol
        """
        if not isinstance(symbol, str):
            raise ValueError("Symbol must be a string")
        
        # Convert to uppercase and strip whitespace
        sanitized = symbol.upper().strip()
        
        # Remove any non-alphabetic characters
        sanitized = re.sub(r'[^A-Z]', '', sanitized)
        
        # Limit length
        sanitized = sanitized[:5]
        
        return sanitized
    
    @staticmethod
    def validate_numeric(value: Any, min_val: Optional[float] = None, 
                        max_val: Optional[float] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate and sanitize numeric input
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        try:
            num = float(value)
            
            if min_val is not None and num < min_val:
                return False, f"Value {num} below minimum {min_val}"
            
            if max_val is not None and num > max_val:
                return False, f"Value {num} above maximum {max_val}"
            
            return True, None
            
        except (ValueError, TypeError):
            return False, f"Invalid numeric value: {value}"
    
    @staticmethod
    def sanitize_numeric(value: Any, min_val: Optional[float] = None, 
                        max_val: Optional[float] = None) -> float:
        """
        Sanitize and validate numeric input
        
        Args:
            value: Value to sanitize
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            
        Returns:
            Sanitized numeric value
            
        Raises:
            ValueError: If value is invalid
        """
        try:
            num = float(value)
            
            if min_val is not None and num < min_val:
                raise ValueError(f"Value {num} below minimum {min_val}")
            
            if max_val is not None and num > max_val:
                raise ValueError(f"Value {num} above maximum {max_val}")
            
            return num
            
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid numeric value: {value}") from e
    
    @staticmethod
    def validate_timestamp(timestamp: Any) -> Tuple[bool, Optional[str]]:
        """
        Validate timestamp format
        
        Args:
            timestamp: Timestamp to validate (ISO string or Unix timestamp)
            
        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        try:
            if isinstance(timestamp, str):
                datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            elif isinstance(timestamp, (int, float)):
                datetime.fromtimestamp(timestamp)
            else:
                return False, f"Invalid timestamp type: {type(timestamp)}"
            
            return True, None
            
        except (ValueError, TypeError, OSError) as e:
            return False, f"Invalid timestamp format: {e}"
    
    @staticmethod
    def sanitize_string(value: Any, max_length: Optional[int] = None, 
                       allow_empty: bool = True) -> str:
        """
        Sanitize string input
        
        Args:
            value: Value to sanitize
            max_length: Maximum string length
            allow_empty: Whether empty strings are allowed
            
        Returns:
            Sanitized string
            
        Raises:
            ValueError: If value is invalid
        """
        if not isinstance(value, str):
            value = str(value)
        
        # Strip whitespace
        sanitized = value.strip()
        
        # Check empty
        if not allow_empty and not sanitized:
            raise ValueError("String cannot be empty")
        
        # Check length
        if max_length and len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @staticmethod
    def validate_json_structure(data: Any, required_fields: Optional[list] = None,
                               field_types: Optional[dict] = None) -> Tuple[bool, Optional[str]]:
        """
        Validate JSON structure
        
        Args:
            data: Data to validate
            required_fields: List of required field names
            field_types: Dict mapping field names to expected types
            
        Returns:
            (is_valid: bool, error_message: Optional[str])
        """
        if not isinstance(data, dict):
            return False, "Data must be a dictionary"
        
        # Check required fields
        if required_fields:
            for field in required_fields:
                if field not in data:
                    return False, f"Missing required field: {field}"
        
        # Check field types
        if field_types:
            for field, expected_type in field_types.items():
                if field in data:
                    if not isinstance(data[field], expected_type):
                        return False, f"Field {field} must be of type {expected_type.__name__}"
        
        return True, None
    
    @staticmethod
    def sanitize_dict(data: Any, allowed_keys: Optional[list] = None) -> dict:
        """
        Sanitize dictionary by removing disallowed keys
        
        Args:
            data: Dictionary to sanitize
            allowed_keys: List of allowed keys (None = allow all)
            
        Returns:
            Sanitized dictionary
        """
        if not isinstance(data, dict):
            raise ValueError("Data must be a dictionary")
        
        if allowed_keys is None:
            return dict(data)
        
        return {k: v for k, v in data.items() if k in allowed_keys}


# Global instance
input_validator = InputValidator()

