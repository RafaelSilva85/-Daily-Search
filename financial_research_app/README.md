# Daily Financial Research Emailer

## Description
The Daily Financial Research Emailer is a Python application designed to automate the process of fetching financial data for a list of specified assets. It collects the previous day's closing prices and links to recent official news, reports, or filings from relevant sources (B3 News for Brazilian assets, SEC EDGAR for US assets). Finally, it compiles this information into an HTML email summary and sends it to configured recipients.

## Features
*   Daily automated financial data collection.
*   Supports assets from B3 (Brazil), NASDAQ, and NYSE.
*   Fetches the previous trading day's closing price using `yfinance`.
*   Scrapes links to new official reports, filings, and relevant facts (from B3 News portal and SEC EDGAR database).
*   Sends a consolidated HTML email report summarizing the findings for each asset.
*   Configurable asset list, email settings, and scheduling time via a `config.ini` file.
*   Logs application activity and errors to both the console and a persistent file (`financial_research.log`).
*   Scheduled daily execution at a user-defined time.

## Prerequisites
*   Python 3.7+ (due to f-strings, `datetime.fromisoformat`, and `schedule` library compatibility; developed with Python 3.10+)
*   Pip (Python package installer, usually comes with Python)

## Setup Instructions
1.  **Download/Clone:**
    *   If this is a Git repository: `git clone <repository_url>`
    *   Otherwise, download the source code and extract it.
2.  **Navigate to Project Directory:**
    ```bash
    cd financial_research_app
    ```
3.  **Create a Python Virtual Environment:**
    ```bash
    python -m venv venv
    ```
4.  **Activate the Virtual Environment:**
    *   **Windows:**
        ```bash
        venv\Scripts\activate
        ```
    *   **macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```
5.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
6.  **Set Up Configuration:**
    *   In the `config` subdirectory, rename or copy `config.ini.sample` to `config.ini`.
    *   Edit `config.ini` with your specific details as explained below.

## Configuration (`config/config.ini`)

The application is configured using the `config.ini` file.

### `[General]` Section
*   `send_time`: The time in HH:MM format (24-hour clock) when the daily email report should be sent.
    *   Example: `send_time = 08:00`

### `[Assets]` Section
*   List the assets you want to track, one per line.
*   Format: `ASSET_SYMBOL = MARKET_EXCHANGE`
*   Supported `MARKET_EXCHANGE` values:
    *   `B3`: For assets listed on the Brazilian Stock Exchange (e.g., PETR4, VALE3).
    *   `NASDAQ`: For assets listed on the NASDAQ Stock Market (e.g., AAPL, MSFT, GOOGL).
    *   `NYSE`: For assets listed on the New York Stock Exchange (e.g., JPM, V).
*   Example:
    ```ini
    PETR4 = B3
    AAPL = NASDAQ
    MSFT = NASDAQ
    JPM = NYSE
    ```

### `[Email]` Section
*   `sender_email`: Your email address that will be used to send the reports.
*   `sender_password`: The password for your `sender_email` account.
    *   **Important for Gmail users:** If you have 2-Factor Authentication (2FA) enabled on your Gmail account, you cannot use your regular password here. You need to generate an "App Password".
        *   To generate an App Password for Gmail:
            1.  Go to your Google Account settings (myaccount.google.com).
            2.  Navigate to "Security".
            3.  Under "Signing in to Google," click on "App passwords" (you might need to enable 2-Step Verification first if it's not already).
            4.  Select "Mail" for the app and "Other (Custom name)" for the device, give it a name (e.g., "PythonFinancialReport"), and click "Generate".
            5.  Use the generated 16-character password as your `sender_password`.
*   `recipient_emails`: A comma-separated list of email addresses that will receive the daily report.
    *   Example: `recipient1@example.com, anotherperson@example.com, me@mydomain.com`
*   `smtp_server`: The SMTP (Simple Mail Transfer Protocol) server address for your email provider.
    *   Examples: `smtp.gmail.com` (for Gmail), `smtp.office365.com` (for Outlook.com/Office365), `smtp.mail.yahoo.com` (for Yahoo Mail).
*   `smtp_port`: The port number for the SMTP server. This often depends on the security protocol (TLS/SSL).
    *   `587` is common for TLS encryption (recommended).
    *   `465` is common for SSL encryption.

## Running the Application
1.  Ensure your virtual environment is activated (see "Setup Instructions").
2.  Make sure you are in the root `financial_research_app` directory (the one containing `main.py`).
3.  Run the main script:
    ```bash
    python main.py
    ```
4.  The script will perform an initial run of the research and email process immediately.
5.  After the initial run, it will schedule the task to run daily at the time specified by `send_time` in your `config.ini`.
6.  Keep the script running in a terminal. For continuous operation on a server, consider using a process manager like `screen`, `tmux`, or setting it up as a systemd service (on Linux).

## Logging
*   Application activity, progress, and errors are logged to the console in real-time.
*   A persistent log file, `financial_research.log`, is created in the application's root directory (same directory as `main.py`). Logs from each run are appended to this file, providing a historical record.

## Troubleshooting
*   **Email not sending:**
    *   Double-check all settings in the `[Email]` section of `config.ini` (especially `sender_email`, `sender_password`, `smtp_server`, `smtp_port`).
    *   If using Gmail, ensure you're using an App Password if 2FA is enabled.
    *   Some email providers might require you to enable "less secure app access" if you're not using 2FA/App Passwords (not recommended for security).
    *   Check `financial_research.log` for specific error messages from `smtplib` which can indicate authentication failures, connection issues, or other server-side problems.
*   **No data for an asset / "Price: Not available":**
    *   Verify the `ASSET_SYMBOL` and `MARKET_EXCHANGE` in `config.ini` are correct.
    *   For price issues, `yfinance` might not find the ticker or have data for it.
    *   For news/reports, the asset might not have had any new relevant documents published within the last 48 hours.
    *   Check `financial_research.log` for any errors related to that specific asset during scraping.
*   **CIK errors (for US stocks - NASDAQ/NYSE):**
    *   The application maps ticker symbols to SEC Central Index Keys (CIKs) using a file from the SEC. If you see errors like "CIK not found," ensure the ticker symbol is correct.
    *   For very newly listed companies, the SEC's `ticker.txt` mapping file might not yet include them.
*   **"Invalid send_time format" error:**
    *   Ensure `send_time` in `config.ini` is in strict HH:MM format (e.g., `07:30` or `15:45`).

## Modules Overview
*   `main.py`: The main executable script that orchestrates the application flow, including configuration loading, scheduling, and calling other modules.
*   `/config`: Contains modules for handling application configuration.
    *   `settings.py`: Parses `config.ini`.
    *   `config.ini.sample`: A template configuration file.
*   `/scraper`: Contains modules responsible for fetching financial data.
    *   `market_scrapers.py`: Implements scraping logic for B3, NASDAQ (via SEC EDGAR), and NYSE (via SEC EDGAR).
    *   `utils.py`: Utility functions for scrapers (e.g., fetching prices via `yfinance`).
*   `/email_sender`: Contains modules for composing and sending email reports.
    *   `emailer.py`: Implements email composition (HTML) and sending via SMTP.
*   `requirements.txt`: Lists all Python package dependencies for the project.
*   `financial_research.log`: The application's log file, created in the root directory.

---
*This README provides a general guide. You may need to adapt paths or commands slightly based on your specific OS or Python environment nuances.*
