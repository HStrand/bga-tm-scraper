"""
Email Notification System for Terraforming Mars Scraper

Handles sending email notifications when scraping runs complete,
including comprehensive statistics and run summaries.
"""

import smtplib
import os
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


class EmailNotifier:
    """Handles email notifications for scraping runs"""
    
    def __init__(self, sender_email: str, app_password: str, recipient_email: str = None):
        self.sender_email = sender_email
        self.app_password = app_password
        self.recipient_email = recipient_email or sender_email
        
    def send_scraping_completion_email(self, 
                                     termination_reason: str,
                                     session_stats: Dict[str, Any],
                                     registry_stats: Dict[str, Any],
                                     start_time: datetime,
                                     end_time: datetime = None) -> bool:
        """
        Send email notification when scraping run completes
        
        Args:
            termination_reason: Why the scraping stopped (e.g., "Daily replay limit reached")
            session_stats: Statistics from this scraping session
            registry_stats: Overall registry statistics
            start_time: When the scraping run started
            end_time: When the scraping run ended (defaults to now)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        if end_time is None:
            end_time = datetime.now()
            
        try:
            subject = "Terraforming Mars Scraper - Daily run completed"
            body = self._generate_email_body(
                termination_reason, session_stats, registry_stats, start_time, end_time
            )
            
            return self._send_email(subject, body)
            
        except Exception as e:
            logger.error(f"Failed to send completion email: {e}")
            return False
    
    def _generate_email_body(self, 
                           termination_reason: str,
                           session_stats: Dict[str, Any],
                           registry_stats: Dict[str, Any],
                           start_time: datetime,
                           end_time: datetime) -> str:
        """Generate HTML email body with comprehensive statistics"""
        
        duration = end_time - start_time
        duration_str = str(duration).split('.')[0]  # Remove microseconds
        
        # Format timestamps
        start_str = start_time.strftime("%Y-%m-%d %H:%M:%S")
        end_str = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #2c3e50; color: white; padding: 15px; border-radius: 5px; }}
                .section {{ margin: 20px 0; padding: 15px; border: 1px solid #ddd; border-radius: 5px; }}
                .stats-table {{ width: 100%; border-collapse: collapse; margin: 10px 0; }}
                .stats-table th, .stats-table td {{ padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }}
                .stats-table th {{ background-color: #f2f2f2; }}
                .success {{ color: #27ae60; }}
                .warning {{ color: #f39c12; }}
                .error {{ color: #e74c3c; }}
                .highlight {{ background-color: #ecf0f1; padding: 10px; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚀 Terraforming Mars Scraper - Daily Run Completed</h2>
            </div>
            
            <div class="section">
                <h3>📊 Run Summary</h3>
                <div class="highlight">
                    <strong>Termination Reason:</strong> {termination_reason}<br>
                    <strong>Start Time:</strong> {start_str}<br>
                    <strong>End Time:</strong> {end_str}<br>
                    <strong>Duration:</strong> {duration_str}
                </div>
            </div>
            
            <div class="section">
                <h3>🎯 Session Statistics</h3>
                <table class="stats-table">
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Games Processed</td><td>{session_stats.get('games_processed', 0)}</td></tr>
                    <tr><td>Successful Scrapes</td><td class="success">{session_stats.get('successful_scrapes', 0)}</td></tr>
                    <tr><td>Successful Parses</td><td class="success">{session_stats.get('successful_parses', 0)}</td></tr>
                    <tr><td>Failed Operations</td><td class="error">{session_stats.get('failed_operations', 0)}</td></tr>
                    <tr><td>Skipped Games</td><td class="warning">{session_stats.get('skipped_games', 0)}</td></tr>
                </table>
            </div>
            
            <div class="section">
                <h3>📈 Overall Registry Statistics</h3>
                <table class="stats-table">
                    <tr><th>Metric</th><th>Value</th></tr>
                    <tr><td>Total Games Tracked</td><td>{registry_stats.get('total_games', 0)}</td></tr>
                    <tr><td>Successfully Scraped</td><td class="success">{registry_stats.get('scraped_games', 0)}</td></tr>
                    <tr><td>Successfully Parsed</td><td class="success">{registry_stats.get('parsed_games', 0)}</td></tr>
                    <tr><td>Arena Mode Games</td><td>{registry_stats.get('arena_games', 0)}</td></tr>
                    <tr><td>Failed/Skipped</td><td class="error">{registry_stats.get('failed_games', 0)}</td></tr>
                    <tr><td>Scrape Success Rate</td><td>{registry_stats.get('scrape_success_rate', 0):.1f}%</td></tr>
                    <tr><td>Parse Success Rate</td><td>{registry_stats.get('parse_success_rate', 0):.1f}%</td></tr>
                </table>
            </div>
            
            {self._generate_next_steps_section(termination_reason)}
            
            <div class="section">
                <p><em>This is an automated notification from your Terraforming Mars BGA Scraper.</em></p>
            </div>
        </body>
        </html>
        """
        
        return html_body
    
    def _generate_next_steps_section(self, termination_reason: str) -> str:
        """Generate next steps section based on termination reason"""
        if "limit reached" in termination_reason.lower():
            return """
            <div class="section">
                <h3>⏰ Next Steps</h3>
                <div class="highlight">
                    <strong>Daily Limit Reached:</strong> BGA has daily limits on replay access to prevent server overload.<br>
                    <strong>Recommendation:</strong> Wait until tomorrow or for the limit to reset before running again.<br>
                    <strong>Typical Reset:</strong> Limits usually reset around midnight UTC or after 24 hours.
                </div>
            </div>
            """
        elif "error" in termination_reason.lower():
            return """
            <div class="section">
                <h3>⚠️ Next Steps</h3>
                <div class="highlight">
                    <strong>Error Encountered:</strong> The scraping run was terminated due to an error.<br>
                    <strong>Recommendation:</strong> Check the scraper.log file for detailed error information.<br>
                    <strong>Action:</strong> Resolve any issues and restart the scraping process.
                </div>
            </div>
            """
        else:
            return """
            <div class="section">
                <h3>✅ Next Steps</h3>
                <div class="highlight">
                    <strong>Run Completed Successfully:</strong> All available games have been processed.<br>
                    <strong>Recommendation:</strong> You can run the scraper again later to check for new games.<br>
                    <strong>Analysis:</strong> Consider running your analysis scripts on the updated dataset.
                </div>
            </div>
            """
    
    def _send_email(self, subject: str, body: str) -> bool:
        """Send HTML email using Gmail SMTP"""
        try:
            message = MIMEMultipart("alternative")
            message["From"] = self.sender_email
            message["To"] = self.recipient_email
            message["Subject"] = subject
            
            # Add HTML content
            html_part = MIMEText(body, "html")
            message.attach(html_part)
            
            # Send email
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, self.recipient_email, message.as_string())
            
            logger.info(f"Email notification sent successfully to {self.recipient_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False


def create_email_notifier_from_config():
    """Create EmailNotifier instance from config settings"""
    try:
        import config
        
        # Check if email settings are configured
        if not hasattr(config, 'EMAIL_NOTIFICATIONS_ENABLED') or not config.EMAIL_NOTIFICATIONS_ENABLED:
            return None
            
        if not hasattr(config, 'EMAIL_SENDER') or not hasattr(config, 'EMAIL_APP_PASSWORD'):
            logger.warning("Email settings not configured in config.py")
            return None
            
        recipient = getattr(config, 'EMAIL_RECIPIENT', config.EMAIL_SENDER)
        
        return EmailNotifier(
            sender_email=config.EMAIL_SENDER,
            app_password=config.EMAIL_APP_PASSWORD,
            recipient_email=recipient
        )
        
    except ImportError:
        logger.warning("Config module not available for email notifications")
        return None
    except Exception as e:
        logger.error(f"Failed to create email notifier from config: {e}")
        return None
