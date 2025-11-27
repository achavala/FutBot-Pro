"""Email and SMS notification service for trade alerts."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class NotificationConfig:
    """Configuration for notifications."""
    
    email_enabled: bool = True
    sms_enabled: bool = True
    email_to: str = ""
    sms_to: str = ""
    
    # Email settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""
    
    # SMS settings (Twilio)
    twilio_account_sid: str = ""
    twilio_auth_token: str = ""
    twilio_from_number: str = ""


class NotificationService:
    """Service for sending email and SMS notifications."""
    
    def __init__(self, config: Optional[NotificationConfig] = None):
        self.config = config or self._load_config()
        self._email_client = None
        self._sms_client = None
        
    def _load_config(self) -> NotificationConfig:
        """Load configuration from environment variables."""
        return NotificationConfig(
            email_enabled=os.getenv("NOTIFICATIONS_EMAIL_ENABLED", "true").lower() == "true",
            sms_enabled=os.getenv("NOTIFICATIONS_SMS_ENABLED", "true").lower() == "true",
            email_to=os.getenv("NOTIFICATIONS_EMAIL_TO", "chavala.akkayya@gmail.com"),
            sms_to=os.getenv("NOTIFICATIONS_SMS_TO", "+12012149984"),
            smtp_server=os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", ""),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            twilio_account_sid=os.getenv("TWILIO_ACCOUNT_SID", ""),
            twilio_auth_token=os.getenv("TWILIO_AUTH_TOKEN", ""),
            twilio_from_number=os.getenv("TWILIO_FROM_NUMBER", ""),
        )
    
    def send_trade_notification(
        self,
        symbol: str,
        side: str,  # "BUY" or "SELL"
        quantity: float,
        price: float,
        order_id: Optional[str] = None,
        pnl: Optional[float] = None,
        pnl_pct: Optional[float] = None,
    ) -> bool:
        """
        Send notification for a trade execution.
        
        Args:
            symbol: Trading symbol
            side: "BUY" or "SELL"
            quantity: Number of shares
            price: Execution price
            order_id: Optional order ID
            pnl: Optional profit/loss (for sells)
            pnl_pct: Optional profit/loss percentage (for sells)
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build message
        if side.upper() == "BUY":
            subject = f"🟢 BUY: {symbol}"
            message = f"""
Trade Executed - BUY

Symbol: {symbol}
Action: BUY
Quantity: {quantity:.2f} shares
Price: ${price:.2f}
Total Value: ${quantity * price:.2f}
Time: {timestamp}
"""
            if order_id:
                message += f"Order ID: {order_id}\n"
        else:  # SELL
            subject = f"🔴 SELL: {symbol}"
            pnl_str = ""
            if pnl is not None:
                pnl_sign = "+" if pnl >= 0 else ""
                pnl_str = f"\nProfit/Loss: {pnl_sign}${pnl:.2f}"
                if pnl_pct is not None:
                    pnl_str += f" ({pnl_sign}{pnl_pct:.2f}%)"
            
            message = f"""
Trade Executed - SELL

Symbol: {symbol}
Action: SELL
Quantity: {quantity:.2f} shares
Price: ${price:.2f}
Total Value: ${quantity * price:.2f}
Time: {timestamp}
{pnl_str}
"""
            if order_id:
                message += f"Order ID: {order_id}\n"
        
        # Send notifications
        success = True
        if self.config.email_enabled:
            email_success = self._send_email(subject, message)
            success = success and email_success
        
        if self.config.sms_enabled:
            sms_success = self._send_sms(message)
            success = success and sms_success
        
        return success
    
    def _send_email(self, subject: str, message: str) -> bool:
        """Send email notification."""
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            if not self.config.email_to or not self.config.smtp_username or not self.config.smtp_password:
                logger.warning("Email not configured. Set SMTP_USERNAME, SMTP_PASSWORD, and NOTIFICATIONS_EMAIL_TO")
                return False
            
            msg = MIMEMultipart()
            msg['From'] = self.config.smtp_username
            msg['To'] = self.config.email_to
            msg['Subject'] = subject
            
            msg.attach(MIMEText(message, 'plain'))
            
            server = smtplib.SMTP(self.config.smtp_server, self.config.smtp_port)
            server.starttls()
            server.login(self.config.smtp_username, self.config.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email notification sent to {self.config.email_to}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return False
    
    def _send_sms(self, message: str) -> bool:
        """Send SMS notification via Twilio."""
        try:
            from twilio.rest import Client
            
            if not self.config.twilio_account_sid or not self.config.twilio_auth_token:
                logger.warning("SMS not configured. Set TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN")
                return False
            
            if not self.config.sms_to:
                logger.warning("SMS recipient not configured. Set NOTIFICATIONS_SMS_TO")
                return False
            
            client = Client(self.config.twilio_account_sid, self.config.twilio_auth_token)
            
            # Truncate message if too long (SMS limit is 1600 chars, but keep it shorter)
            sms_message = message[:500] if len(message) > 500 else message
            
            client.messages.create(
                body=sms_message,
                from_=self.config.twilio_from_number,
                to=self.config.sms_to
            )
            
            logger.info(f"SMS notification sent to {self.config.sms_to}")
            return True
            
        except ImportError:
            logger.warning("Twilio not installed. Run: pip install twilio")
            return False
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
            return False

