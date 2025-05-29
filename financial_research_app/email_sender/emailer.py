from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def compose_email_content(scraped_data: list[dict]) -> tuple[str, str]:
    """
    Composes the email subject and HTML body from the scraped financial data.

    Args:
        scraped_data: A list of dictionaries, where each dictionary is expected
                      to have "asset" (str), "price" (float | None), and
                      "news_links" (list[str]).

    Returns:
        A tuple containing (email_subject, email_body_html).
    """
    current_date = datetime.now().strftime("%Y-%m-%d")
    email_subject = f"Daily Financial Research Report - {current_date}"

    # Start HTML body
    html_body = f"<html><head><style>"
    html_body += "body { font-family: sans-serif; margin: 20px; }"
    html_body += "h2 { color: #333; }"
    html_body += ".asset-block { margin-bottom: 20px; padding: 15px; border: 1px solid #ddd; border-radius: 5px; background-color: #f9f9f9; }"
    html_body += ".asset-title { font-size: 1.2em; font-weight: bold; color: #555; margin-bottom: 10px; }"
    html_body += ".price { margin-bottom: 5px; }"
    html_body += ".news-list { list-style-type: disc; margin-left: 20px; }"
    html_body += ".news-list li { margin-bottom: 5px; }"
    html_body += "a { color: #0066cc; text-decoration: none; }"
    html_body += "a:hover { text-decoration: underline; }"
    html_body += ".no-data { font-style: italic; color: #777; }"
    html_body += "</style></head><body>"
    html_body += f"<h2>Daily Financial Research Report - {current_date}</h2>"

    if not scraped_data:
        html_body += "<p class='no-data'>No assets processed or no data found for today.</p>"
    else:
        for item in scraped_data:
            asset = item.get("asset", "N/A")
            price = item.get("price")
            news_links = item.get("news_links", [])

            html_body += "<div class='asset-block'>"
            html_body += f"<div class='asset-title'>Asset: {asset}</div>"

            # Price formatting (simple heuristic for currency)
            price_str = "Price: Not available"
            if price is not None:
                try:
                    price_val = float(price)
                    if ".SA" in asset.upper(): # Heuristic for B3 assets (BRL)
                        price_str = f"Price: R${price_val:,.2f}"
                    else: # Default to USD for others
                        price_str = f"Price: ${price_val:,.2f}"
                except (ValueError, TypeError):
                     price_str = f"Price: Invalid data ({price})"
            
            html_body += f"<div class='price'>{price_str}</div>"

            if news_links:
                html_body += "<p><strong>Recent Reports/News:</strong></p>"
                html_body += "<ul class='news-list'>"
                for link in news_links:
                    link_text = link
                    if len(link_text) > 100:
                        link_text = link_text[:97] + "..."
                    html_body += f"<li><a href='{link}'>{link_text}</a></li>"
                html_body += "</ul>"
            else:
                html_body += "<p class='no-data'>No new reports found.</p>"
            
            html_body += "</div>"

    html_body += "</body></html>"
    return email_subject, html_body


def send_email(subject: str, body_html: str, recipient_emails: list[str], 
               sender_email: str, sender_password: str, 
               smtp_server: str, smtp_port: int) -> bool:
    """
    Sends an email with HTML content.

    Args:
        subject: The subject of the email.
        body_html: The HTML content of the email body.
        recipient_emails: A list of recipient email addresses.
        sender_email: The email address of the sender.
        sender_password: The password for the sender's email account.
        smtp_server: The SMTP server address (e.g., "smtp.gmail.com").
        smtp_port: The SMTP server port (e.g., 587 for TLS, 465 for SSL).

    Returns:
        True if the email is sent successfully, False otherwise.
    """
    if not recipient_emails:
        print("Error: No recipient emails provided.")
        return False

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipient_emails) # Comma-separated string for header
    msg['Subject'] = subject

    msg.attach(MIMEText(body_html, 'html'))

    try:
        server = None # Initialize server to None for finally block
        if smtp_port == 465: # SSL connection
            server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=10)
        elif smtp_port == 587: # TLS connection
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)
            server.ehlo() # Extended Hello
            server.starttls() # Start TLS encryption
            server.ehlo() # Re-issue ehlo after TLS
        else: # Potentially other ports or unencrypted (not recommended)
            server = smtplib.SMTP(smtp_server, smtp_port, timeout=10)

        server.login(sender_email, sender_password)
        server.sendmail(sender_email, recipient_emails, msg.as_string())
        print(f"Email sent successfully to: {', '.join(recipient_emails)}")
        return True
    except smtplib.SMTPAuthenticationError as e:
        print(f"SMTP Authentication Error: {e}. Check sender email/password.")
    except smtplib.SMTPServerDisconnected as e:
        print(f"SMTP Server Disconnected: {e}. Try again later or check server/port.")
    except smtplib.SMTPConnectError as e:
        print(f"SMTP Connect Error: {e}. Check SMTP server address and port.")
    except smtplib.SMTPException as e:
        print(f"SMTP Error: {e}")
    except ConnectionRefusedError as e: # More specific network error
        print(f"Connection Refused: {e}. Check SMTP server/port and firewall.")
    except TimeoutError as e: # Specific timeout error
        print(f"Connection Timeout: {e}. SMTP server may be slow or unreachable.")
    except Exception as e:
        print(f"An unexpected error occurred while sending email: {e}")
    finally:
        if server:
            try:
                server.quit()
            except smtplib.SMTPServerDisconnected:
                # If already disconnected, quit may raise this. Safe to ignore.
                pass
            except Exception as e:
                print(f"Error quitting SMTP server: {e}")
    return False
