import configparser
from typing import List, Tuple, Dict, Any, Optional # For type hinting

def load_config(config_path: str = "config/config.ini") -> Optional[configparser.ConfigParser]:
    """
    Loads the configuration file from the given path.

    Args:
        config_path: Path to the configuration file (e.g., "config/config.ini").

    Returns:
        A ConfigParser object if successful, None otherwise.
    """
    parser = configparser.ConfigParser()
    try:
        # Check if the file was actually read
        if not parser.read(config_path, encoding='utf-8'):
            print(f"Error: Configuration file not found or empty at {config_path}")
            return None
        return parser
    except configparser.Error as e:
        print(f"Error parsing configuration file {config_path}: {e}")
        return None
    except FileNotFoundError: # Though parser.read should handle this by returning empty list
        print(f"Error: Configuration file not found at {config_path}")
        return None

def get_general_settings(config: configparser.ConfigParser) -> Dict[str, Any]:
    """
    Retrieves general settings.
    """
    settings = {}
    try:
        if config.has_section('General'):
            if config.has_option('General', 'send_time'):
                settings['send_time'] = config.get('General', 'send_time')
            else:
                print("Warning: 'send_time' not found in [General] section. Using default or None.")
                settings['send_time'] = None # Or a default value like "08:00"
        else:
            print("Warning: [General] section not found in config. Using default settings.")
            settings['send_time'] = None # Or a default
    except configparser.Error as e:
        print(f"Error reading [General] settings: {e}")
        settings['send_time'] = None # Fallback
    return settings

def get_assets_to_track(config: configparser.ConfigParser) -> List[Tuple[str, str]]:
    """
    Retrieves the list of assets to track from the [Assets] section.
    Assets are expected in the format: TICKER = MARKET (e.g., AAPL = NASDAQ).
    """
    assets = []
    if config.has_section('Assets'):
        try:
            for ticker, market in config.items('Assets'):
                # Comments in INI might be read as items if not handled by parser settings.
                # Standard configparser typically ignores lines starting with # or ;
                # We assume valid ticker=market lines.
                if ticker and market: # Ensure neither is empty
                    assets.append((ticker.upper(), market.upper()))
                else:
                    print(f"Warning: Skipping invalid asset entry: '{ticker} = {market}'")
        except configparser.Error as e:
            print(f"Error reading [Assets] section: {e}")
            return [] # Return empty list on error
    else:
        print("Warning: [Assets] section not found in config. No assets will be tracked.")
    return assets

def get_email_settings(config: configparser.ConfigParser) -> Dict[str, Any]:
    """
    Retrieves email settings.
    Converts recipient_emails to a list and smtp_port to an int.
    """
    settings = {
        'sender_email': None,
        'sender_password': None,
        'recipient_emails': [],
        'smtp_server': None,
        'smtp_port': None
    }
    if not config.has_section('Email'):
        print("Error: [Email] section not found in configuration.")
        return settings # Return defaults/None

    try:
        if config.has_option('Email', 'sender_email'):
            settings['sender_email'] = config.get('Email', 'sender_email')
        else:
            print("Error: 'sender_email' not found in [Email] section.")

        if config.has_option('Email', 'sender_password'):
            settings['sender_password'] = config.get('Email', 'sender_password')
        else:
            print("Error: 'sender_password' not found in [Email] section.")

        if config.has_option('Email', 'recipient_emails'):
            recipients_str = config.get('Email', 'recipient_emails')
            settings['recipient_emails'] = [email.strip() for email in recipients_str.split(',') if email.strip()]
        else:
            print("Error: 'recipient_emails' not found in [Email] section.")
        
        if config.has_option('Email', 'smtp_server'):
            settings['smtp_server'] = config.get('Email', 'smtp_server')
        else:
            print("Error: 'smtp_server' not found in [Email] section.")

        if config.has_option('Email', 'smtp_port'):
            try:
                settings['smtp_port'] = config.getint('Email', 'smtp_port')
            except ValueError:
                print("Error: 'smtp_port' in [Email] section is not a valid integer. Please check config.")
                settings['smtp_port'] = None # Or a default like 587
        else:
            print("Error: 'smtp_port' not found in [Email] section.")

    except configparser.Error as e:
        print(f"Error reading [Email] settings: {e}")
        # Reset to defaults on parsing error for the section
        return {
            'sender_email': None, 'sender_password': None, 'recipient_emails': [],
            'smtp_server': None, 'smtp_port': None
        }
        
    # Check if essential fields are missing and issue a warning or error
    if not all([settings['sender_email'], settings['sender_password'], settings['recipient_emails'], settings['smtp_server'], settings['smtp_port'] is not None]):
        print("Warning: Some essential email settings are missing. Email functionality may be impaired.")
        
    return settings
