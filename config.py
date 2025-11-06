"""
Configuration management for DUANO API client
"""

import os
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class DuanoConfig:
    """Configuration class for DUANO API client with OAuth2 support"""
    
    # OAuth2 Configuration
    client_id: str = field(default_factory=lambda: os.getenv('DUANO_CLIENT_ID', '3'))
    client_secret: str = field(default_factory=lambda: os.getenv('DUANO_CLIENT_SECRET', 'KBPJZ11EwPjAmEUKFWDoXGQaDdMRPFES2P6VCxEC'))
    base_url: str = field(default_factory=lambda: os.getenv('DUANO_API_BASE_URL', 'https://api.duano.com'))
    redirect_uri: str = field(default_factory=lambda: os.getenv('DUANO_REDIRECT_URI', 'https://mothership-prospecting.onrender.com/oauth/callback'))
    
    # Request Configuration
    timeout: int = field(default_factory=lambda: int(os.getenv('DUANO_TIMEOUT', '30')))
    max_retries: int = field(default_factory=lambda: int(os.getenv('DUANO_MAX_RETRIES', '3')))
    
    # Debug and Logging
    debug: bool = field(default_factory=lambda: os.getenv('DUANO_DEBUG', 'false').lower() == 'true')
    log_level: str = field(default_factory=lambda: os.getenv('DUANO_LOG_LEVEL', 'INFO'))
    
    # Pagination defaults
    default_page_size: int = field(default_factory=lambda: int(os.getenv('DUANO_DEFAULT_PAGE_SIZE', '50')))
    max_page_size: int = field(default_factory=lambda: int(os.getenv('DUANO_MAX_PAGE_SIZE', '1000')))
    
    def validate(self) -> None:
        """Validate configuration"""
        if not self.client_id:
            raise ValueError("Client ID is required. Set DUANO_CLIENT_ID environment variable or pass client_id parameter.")
        
        if not self.client_secret:
            raise ValueError("Client secret is required. Set DUANO_CLIENT_SECRET environment variable or pass client_secret parameter.")
        
        if not self.base_url:
            raise ValueError("Base URL is required.")
        
        if self.timeout <= 0:
            raise ValueError("Timeout must be greater than 0")
        
        if self.max_retries < 0:
            raise ValueError("Max retries must be 0 or greater")
    
    @classmethod
    def from_env(cls) -> 'DuanoConfig':
        """Create configuration from environment variables"""
        return cls()
    
    @classmethod
    def from_dict(cls, config_dict: dict) -> 'DuanoConfig':
        """Create configuration from dictionary"""
        return cls(**config_dict)


def load_config(config_file: Optional[str] = None) -> DuanoConfig:
    """
    Load configuration from environment variables or config file
    
    Args:
        config_file: Optional path to configuration file
        
    Returns:
        DuanoConfig instance
    """
    if config_file and os.path.exists(config_file):
        # If you want to support config files in the future
        # you can add JSON/YAML loading here
        pass
    
    config = DuanoConfig.from_env()
    config.validate()
    return config
