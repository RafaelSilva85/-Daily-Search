import logging
import os # For creating the default config file if it doesn't exist

# Configuration imports
from config.settings import (
    load_config, 
    get_general_settings, 
    get_assets_to_track, 
    get_email_settings
)

# Scraper imports
from scraper.market_scrapers import (
    scrape_b3, 
    scrape_nasdaq, 
    scrape_nyse
)

import sys # Required for PyInstaller path detection

# Email imports
from email_sender.emailer import compose_email_content, send_email


# --- Application Path Helper ---
def get_application_path():
    """Determines the base path for the application, whether running as script or frozen executable."""
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # Running in a PyInstaller bundle (frozen)
        # sys.executable is the path to the executable
        application_path = os.path.dirname(sys.executable)
    else:
        # Running as a normal script
        application_path = os.path.dirname(os.path.abspath(__file__))
    return application_path

_APP_BASE_DIR = get_application_path()


# --- Enhanced Logging Setup ---
# Get the root logger
logger = logging.getLogger() # Root logger
logger.setLevel(logging.INFO) # Set global minimum level for the logger

# Define a standard formatter
# Using %(module)s might be noisy if logs from imported libraries are also captured at INFO level.
# For application-specific logs, %(name)s (logger name) can be more useful if you use named loggers.
# For root logger, %(module)s is fine if all app modules use `logging.info` etc. directly.
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(module)s - %(message)s')

# Console Handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO) # Minimum level for console output
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File Handler
# Save log file in the application's base directory 
log_file_path = os.path.join(_APP_BASE_DIR, 'financial_research.log')
try:
    file_handler = logging.FileHandler(log_file_path, mode='a', encoding='utf-8')
    file_handler.setLevel(logging.INFO) 
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    # Initial log to confirm file logging is working.
    # This will go to both console and file if file handler is successful.
    logging.info(f"Application started. Logging to console and to file: {log_file_path}")
except IOError as e:
    logging.error(f"Could not set up file logger at {log_file_path}: {e}. Logging to console only.")


import schedule
import time
import re # For send_time validation

# --- Default Configuration Path ---
# These will be dynamically set to be script-relative in __main__
CONFIG_DIR_NAME = "config" 
DEFAULT_CONFIG_FILENAME = "config.ini"
SAMPLE_CONFIG_FILENAME = "config.ini.sample"


def ensure_config_exists(default_cfg_path: str, sample_cfg_path: str, config_dir: str) -> bool:
    """
    Checks if default_cfg_path exists. If not, copies it from sample_cfg_path.
    Args:
        default_cfg_path: The absolute path to the target config.ini.
        sample_cfg_path: The absolute path to the sample config.ini.sample.
        config_dir: The absolute path to the config directory.
    """
    if not os.path.exists(default_cfg_path):
        logging.info(f"'{default_cfg_path}' not found.")
        if os.path.exists(sample_cfg_path):
            logging.info(f"Copying '{sample_cfg_path}' to '{default_cfg_path}'.")
            try:
                if not os.path.exists(config_dir):
                    os.makedirs(config_dir)
                    logging.info(f"Created directory: {config_dir}")

                with open(sample_cfg_path, 'r', encoding='utf-8') as sample_file:
                    content = sample_file.read()
                with open(default_cfg_path, 'w', encoding='utf-8') as config_file:
                    config_file.write(content)
                logging.info(f"Successfully created '{default_cfg_path}'. Please review and edit it.")
            except IOError as e:
                logging.error(f"Error copying sample config: {e}")
                logging.error(f"Please manually copy '{sample_cfg_path}' to '{default_cfg_path}' and configure it.")
                return False
        else:
            logging.error(f"'{sample_cfg_path}' not found. Cannot create default config.")
            logging.error(f"Please create '{default_cfg_path}' manually or restore '{sample_cfg_path}'.")
            return False
    return True


def run_daily_research(config_path: str):
    """
    Main function to run the daily financial research process.
    Args:
        config_path: Absolute path to the configuration file.
    """
    logging.info("Attempting to run daily financial research...")

    # Note: ensure_config_exists should ideally be called before this,
    # or this function needs the sample_config_path as well to call it.
    # For the scheduling setup, ensure_config_exists is called once upfront.

    # 1. Load Configuration
    logging.info(f"Loading configuration from: {config_path}")
    config = load_config(config_path) # load_config now uses the passed path
    if not config:
        logging.error(f"Failed to load configuration from {config_path}. Task aborted for this run.")
        return

    general_settings = get_general_settings(config)
    assets_to_track = get_assets_to_track(config)
    email_settings = get_email_settings(config)

    logging.info(f"General Settings: Send time - {general_settings.get('send_time', 'N/A')}")

    if not assets_to_track:
        logging.warning("No assets found in configuration to track. Exiting.")
        # Optionally, still send an email saying no assets were configured
        subject = "Financial Research Report - Configuration Issue"
        body = "No assets were configured for tracking. Please check the config.ini file."
        if email_settings.get('sender_email') and email_settings.get('recipient_emails'):
             send_email(
                subject, body,
                email_settings['recipient_emails'],
                email_settings['sender_email'],
                email_settings['sender_password'],
                email_settings['smtp_server'],
                email_settings['smtp_port']
            )
        return

    if not all([email_settings.get('sender_email'), email_settings.get('sender_password'), 
                email_settings.get('recipient_emails'), email_settings.get('smtp_server'), 
                email_settings.get('smtp_port') is not None]):
        logging.error("Essential email settings are missing in the configuration. Cannot send report. Exiting.")
        return
    
    logging.info(f"Found {len(assets_to_track)} assets to track: {assets_to_track}")

    # 2. Scrape Data
    all_scraped_data = []
    # Pass the raw config object to scrapers if they need specific sub-configs,
    # or pass None if they don't use it yet.
    # For now, the scrapers take a generic config:dict, which we can represent with {} if no specific scraper config is needed from the file.
    # Or, we can pass `email_settings` or other relevant parts if a scraper needs it.
    # The current scraper functions do not use the config dict, so passing empty dict.
    scraper_config_dict = {} 

    for asset_symbol, market in assets_to_track:
        logging.info(f"Processing: {asset_symbol} from market: {market}")
        scraped_data_item = None
        try:
            if market == "B3":
                scraped_data_item = scrape_b3(asset_symbol, scraper_config_dict)
            elif market == "NASDAQ":
                scraped_data_item = scrape_nasdaq(asset_symbol, scraper_config_dict)
            elif market == "NYSE":
                scraped_data_item = scrape_nyse(asset_symbol, scraper_config_dict)
            else:
                logging.warning(f"Unknown market '{market}' for asset '{asset_symbol}'. Skipping.")
                continue # Skip to next asset

            if scraped_data_item:
                all_scraped_data.append(scraped_data_item)
                logging.info(f"Successfully scraped data for {asset_symbol}.")
            else:
                logging.warning(f"No data returned from scraper for {asset_symbol}.")
        
        except Exception as e:
            logging.error(f"Error scraping data for {asset_symbol} ({market}): {e}", exc_info=False) # exc_info=True for full traceback
            # Append a placeholder if an error occurs to show it was attempted
            all_scraped_data.append({
                "asset": asset_symbol,
                "price": None,
                "news_links": [],
                "error": str(e) # Optionally include error message in report
            })

    # 3. Compose and Send Email
    logging.info("Composing email content...")
    email_subject, email_body_html = compose_email_content(all_scraped_data)

    logging.info("Attempting to send email report...")
    
    # Add a check to ensure all email settings are valid before calling send_email
    # This was already done above, but double check specific critical values if needed
    
    success = send_email(
        subject=email_subject,
        body_html=email_body_html,
        recipient_emails=email_settings['recipient_emails'],
        sender_email=email_settings['sender_email'],
        sender_password=email_settings['sender_password'],
        smtp_server=email_settings['smtp_server'],
        smtp_port=email_settings['smtp_port']
    )

    if success:
        logging.info("Email report sent successfully.")
    else:
        logging.error("Failed to send email report.")

    logging.info("Daily financial research process finished.")


if __name__ == "__main__":
    # Config paths are now relative to _APP_BASE_DIR
    config_dir_abs_path = os.path.join(_APP_BASE_DIR, CONFIG_DIR_NAME)
    default_config_abs_path = os.path.join(config_dir_abs_path, DEFAULT_CONFIG_FILENAME)
    sample_config_abs_path = os.path.join(config_dir_abs_path, SAMPLE_CONFIG_FILENAME)

    # Ensure config.ini exists, copying from sample if needed. 
    # This needs to happen before attempting to load configuration for scheduling.
    if not ensure_config_exists(default_config_abs_path, sample_config_abs_path, config_dir_abs_path):
        # Logging.critical will be caught by the new handlers
        logging.critical("Configuration file setup failed. Cannot proceed. Exiting.")
        return

    # Load configuration to get send_time for scheduling
    config = load_config(default_config_abs_path) 
    if not config:
        logging.critical(f"Failed to load configuration from '{default_config_abs_path}' for scheduling. Exiting.")
        return

    general_settings = get_general_settings(config)
    send_time_str = general_settings.get("send_time")

    if not send_time_str:
        logging.critical("Send time not found in general settings ([General] -> send_time). Cannot schedule. Exiting.")
        return

    # Validate HH:MM format for send_time_str
    if not re.match(r"^\d{2}:\d{2}$", send_time_str):
        logging.critical(f"Invalid send_time format '{send_time_str}'. Expected HH:MM. Cannot schedule. Exiting.")
        return
    
    # Perform an initial run immediately
    logging.info("Performing initial run of daily research...")
    # Pass the absolute path to run_daily_research
    run_daily_research(config_path=default_config_abs_path) 
    logging.info("Initial run complete.")

    # Schedule the task
    logging.info(f"Scheduling daily research task to run every day at {send_time_str}.")
    # Pass the absolute path to the scheduled job
    schedule.every().day.at(send_time_str).do(run_daily_research, config_path=default_config_abs_path)

    logging.info("Scheduler started. Waiting for scheduled tasks...")
    while True:
        schedule.run_pending()
        time.sleep(60) # Check every 60 seconds
