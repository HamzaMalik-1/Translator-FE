"""
API Key Manager for handling multiple API keys with quota tracking
"""
import os
import threading
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

class APIKeyManager:
    """Manages multiple API keys with quota tracking and failover"""
    
    def __init__(self):
        self.api_keys = []
        self.current_key_index = 0
        self.key_usage = {}  # Track usage per key
        self.key_errors = {}  # Track errors per key
        self.key_enabled = {}  # Track if key is enabled
        self.lock = threading.Lock()
        self.load_api_keys()
        
    def load_api_keys(self):
        """Load API keys from environment variables"""
        api_keys = []
        i = 1
        
        # First try the main key
        main_key = os.getenv("GEMINI_API_KEY")
        if main_key:
            api_keys.append(main_key)
            print(f"Loaded main API key")
        
        # Try numbered keys
        while True:
            key_name = f"GEMINI_API_KEY_{i}"
            key = os.getenv(key_name)
            if key:
                api_keys.append(key)
                print(f"Loaded {key_name}")
                i += 1
            else:
                break
        
        # Try comma-separated list
        key_list = os.getenv("GEMINI_API_KEYS")
        if key_list:
            keys = [k.strip() for k in key_list.split(",") if k.strip()]
            api_keys.extend(keys)
            print(f"Loaded {len(keys)} keys from GEMINI_API_KEYS")
        
        if not api_keys:
            print("CRITICAL ERROR: No API keys found in environment variables.")
            print("Add keys as: GEMINI_API_KEY, GEMINI_API_KEY_1, GEMINI_API_KEY_2, etc.")
            return
        
        self.api_keys = api_keys
        
        # Initialize tracking for each key
        for idx, key in enumerate(api_keys):
            self.key_usage[idx] = {
                'count': 0,
                'last_used': None,
                'quota_exceeded': False,
                'quota_reset_time': None
            }
            self.key_errors[idx] = {
                'error_count': 0,
                'last_error': None,
                'consecutive_errors': 0
            }
            self.key_enabled[idx] = True
        
        print(f"Loaded {len(api_keys)} API keys")
    
    def get_current_key(self):
        """Get the currently active API key"""
        with self.lock:
            if not self.api_keys:
                return None
            return self.api_keys[self.current_key_index]
    
    def get_next_key(self):
        """Rotate to the next available API key"""
        with self.lock:
            if not self.api_keys:
                return None
            
            original_index = self.current_key_index
            start_index = (self.current_key_index + 1) % len(self.api_keys)
            
            # Try to find an enabled key
            for i in range(len(self.api_keys)):
                idx = (start_index + i) % len(self.api_keys)
                if self.key_enabled[idx]:
                    self.current_key_index = idx
                    print(f"Switched to API key {idx + 1}")
                    return self.api_keys[idx]
            
            # If no enabled keys found, reset all and use the original
            print("All keys disabled, resetting...")
            for idx in range(len(self.api_keys)):
                self.key_enabled[idx] = True
                self.key_errors[idx]['consecutive_errors'] = 0
            
            self.current_key_index = original_index
            return self.api_keys[original_index]
    
    def record_success(self, key_index):
        """Record successful API call"""
        with self.lock:
            if key_index in self.key_usage:
                self.key_usage[key_index]['count'] += 1
                self.key_usage[key_index]['last_used'] = datetime.now()
                self.key_usage[key_index]['quota_exceeded'] = False
                self.key_errors[key_index]['consecutive_errors'] = 0
    
    def record_error(self, key_index, error_message):
        """Record API error and handle key disabling"""
        with self.lock:
            if key_index not in self.key_errors:
                return
            
            self.key_errors[key_index]['error_count'] += 1
            self.key_errors[key_index]['last_error'] = error_message
            self.key_errors[key_index]['consecutive_errors'] += 1
            
            # Check for quota exceeded
            if "quota" in error_message.lower() or "429" in error_message:
                self.key_usage[key_index]['quota_exceeded'] = True
                # Set reset time to 1 hour from now
                self.key_usage[key_index]['quota_reset_time'] = datetime.now() + timedelta(hours=1)
                print(f"Key {key_index + 1} quota exceeded. Will retry after 1 hour.")
                # Disable key temporarily
                self.key_enabled[key_index] = False
            
            # Disable key if too many consecutive errors
            if self.key_errors[key_index]['consecutive_errors'] > 5:
                print(f"Key {key_index + 1} disabled due to {self.key_errors[key_index]['consecutive_errors']} consecutive errors")
                self.key_enabled[key_index] = False
                # Re-enable after 30 minutes
                import threading as th
                th.Timer(1800, self.enable_key, args=[key_index]).start()
    
    def enable_key(self, key_index):
        """Re-enable a disabled key"""
        with self.lock:
            if key_index in self.key_enabled:
                self.key_enabled[key_index] = True
                self.key_errors[key_index]['consecutive_errors'] = 0
                print(f"Key {key_index + 1} re-enabled")
    
    def check_quota_reset(self):
        """Check if any keys need to be re-enabled after quota reset"""
        with self.lock:
            now = datetime.now()
            for idx in self.key_usage:
                reset_time = self.key_usage[idx].get('quota_reset_time')
                if reset_time and now >= reset_time and self.key_usage[idx]['quota_exceeded']:
                    self.key_usage[idx]['quota_exceeded'] = False
                    self.key_usage[idx]['quota_reset_time'] = None
                    self.key_enabled[idx] = True
                    self.key_errors[idx]['consecutive_errors'] = 0
                    print(f"Key {idx + 1} quota reset")
    
    def get_status(self):
        """Get status of all API keys"""
        with self.lock:
            status = []
            for idx in range(len(self.api_keys)):
                status.append({
                    'key_index': idx + 1,
                    'enabled': self.key_enabled.get(idx, False),
                    'usage_count': self.key_usage.get(idx, {}).get('count', 0),
                    'quota_exceeded': self.key_usage.get(idx, {}).get('quota_exceeded', False),
                    'error_count': self.key_errors.get(idx, {}).get('error_count', 0),
                    'consecutive_errors': self.key_errors.get(idx, {}).get('consecutive_errors', 0)
                })
            return status