import json
import os
# from typing import Any, Dict  # Not supported in Jython

class ConfigManager:
    
    def __init__(self, config_file='gmapper_config.json'):
        self.config_file = config_file
        self.config = self._load_config()
        self._apply_defaults()
    
    def _load_config(self):
        """Load configuration from file if it exists"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print("[Gmapper] Error loading config file: {}".format(e))
                return {}
        return {}
    
    def _apply_defaults(self):
        """Apply default values for missing configuration"""
        defaults = {
            'cost_threshold': 5.0,  # USD per 1k requests
            'google_service_account_key': None,  # Path to service account JSON
            'enable_caching': True,
            'cache_ttl': 3600,  # 1 hour
            'request_timeout': 5,  # seconds
            'max_retries': 3,
            'log_level': 'INFO',
            'create_issues': True,
            'issue_severity_unrestricted': 'High',
            'issue_severity_expensive': 'Medium',
            'monitored_tools': ['proxy'],  # Which Burp tools to monitor
            'excluded_hosts': [],  # Hosts to exclude from scanning
            'pricing_overrides': {},  # Custom pricing overrides
            'report_format': 'table'  # 'table' or 'json'
        }
        
        for key, value in defaults.items():
            if key not in self.config:
                self.config[key] = value
    
    def get(self, key, default=None):
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set a configuration value"""
        self.config[key] = value
        self._save_config()
    
    def _save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print("[Gmapper] Error saving config file: {}".format(e))
    
    def update_pricing(self, service, cost_per_1k):
        """Update custom pricing for a service"""
        if 'pricing_overrides' not in self.config:
            self.config['pricing_overrides'] = {}
        
        self.config['pricing_overrides'][service] = cost_per_1k
        self._save_config()
    
    def is_host_excluded(self, host):
        """Check if a host is in the exclusion list"""
        excluded_hosts = self.config.get('excluded_hosts', [])
        for excluded in excluded_hosts:
            if excluded in host:
                return True
        return False
    
    def get_severity_for_issue_type(self, issue_type):
        """Get the configured severity for a specific issue type"""
        if issue_type == 'unrestricted':
            return self.config.get('issue_severity_unrestricted', 'High')
        elif issue_type == 'expensive':
            return self.config.get('issue_severity_expensive', 'Medium')
        else:
            return 'Information'
    
    def should_monitor_tool(self, tool_flag):
        """Check if a specific Burp tool should be monitored"""
        monitored_tools = self.config.get('monitored_tools', ['proxy'])
        
        # Map tool flags to names (simplified)
        tool_map = {
            0x00000004: 'proxy',
            0x00000008: 'scanner',
            0x00000010: 'intruder',
            0x00000020: 'repeater'
        }
        
        tool_name = tool_map.get(tool_flag, 'unknown')
        return tool_name in monitored_tools
    
    def get_example_config(self):
        """Generate an example configuration file content"""
        example = {
            "cost_threshold": 5.0,
            "google_service_account_key": "/path/to/service-account-key.json",
            "enable_caching": True,
            "cache_ttl": 3600,
            "request_timeout": 5,
            "max_retries": 3,
            "log_level": "INFO",
            "create_issues": True,
            "issue_severity_unrestricted": "High",
            "issue_severity_expensive": "Medium",
            "monitored_tools": ["proxy", "scanner", "repeater"],
            "excluded_hosts": ["localhost", "127.0.0.1", "internal.company.com"],
            "pricing_overrides": {
                "maps_javascript": 8.00,
                "custom_service": 10.00
            },
            "report_format": "table"
        }
        return json.dumps(example, indent=2)