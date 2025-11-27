# Email and SMS Notifications Setup Guide

This guide explains how to set up email and SMS notifications for trade alerts.

## Overview

The system sends notifications when:
- **BUY orders** are executed
- **SELL orders** are executed
- **Positions are closed** (with profit/loss information)

## Email Setup (Gmail)

### 1. Enable App Password

1. Go to your Google Account settings: https://myaccount.google.com/
2. Navigate to **Security** → **2-Step Verification** (enable if not already)
3. Go to **App passwords**: https://myaccount.google.com/apppasswords
4. Create a new app password for "Mail"
5. Copy the 16-character password

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# Email Settings
NOTIFICATIONS_EMAIL_ENABLED=true
NOTIFICATIONS_EMAIL_TO=chavala.akkayya@gmail.com
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
```

## SMS Setup (Twilio)

### 1. Create Twilio Account

1. Sign up at https://www.twilio.com/try-twilio
2. Get your Account SID and Auth Token from the dashboard
3. Get a phone number (free trial includes $15.50 credit)

### 2. Configure Environment Variables

Add to your `.env` file:

```bash
# SMS Settings
NOTIFICATIONS_SMS_ENABLED=true
NOTIFICATIONS_SMS_TO=+12012149984
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_FROM_NUMBER=+1234567890  # Your Twilio phone number
```

### 3. Install Twilio

```bash
pip install twilio
```

## Configuration

### Default Settings

The system is pre-configured with:
- **Email**: `chavala.akkayya@gmail.com`
- **SMS**: `+1 201 214 9984`

### Disable Notifications

To disable email or SMS:

```bash
NOTIFICATIONS_EMAIL_ENABLED=false
NOTIFICATIONS_SMS_ENABLED=false
```

## Notification Format

### Buy Notification

```
Trade Executed - BUY

Symbol: QQQ
Action: BUY
Quantity: 5.23 shares
Price: $191.25
Total Value: $1000.00
Time: 2025-11-21 14:30:00
Order ID: abc123
```

### Sell Notification

```
Trade Executed - SELL

Symbol: QQQ
Action: SELL
Quantity: 5.23 shares
Price: $248.50
Total Value: $1300.00
Time: 2025-11-21 15:45:00
Profit/Loss: +$300.00 (+30.00%)
Order ID: xyz789
```

## Testing

Test notifications manually:

```python
from services.notifications import NotificationService

service = NotificationService()

# Test buy notification
service.send_trade_notification(
    symbol="QQQ",
    side="BUY",
    quantity=5.23,
    price=191.25,
    order_id="test-123"
)

# Test sell notification
service.send_trade_notification(
    symbol="QQQ",
    side="SELL",
    quantity=5.23,
    price=248.50,
    order_id="test-456",
    pnl=300.00,
    pnl_pct=30.00
)
```

## Troubleshooting

### Email Not Working

1. **Check credentials**: Verify SMTP_USERNAME and SMTP_PASSWORD are correct
2. **App password**: Make sure you're using an app password, not your regular password
3. **2FA**: Ensure 2-Step Verification is enabled
4. **Firewall**: Check if port 587 is blocked

### SMS Not Working

1. **Twilio credentials**: Verify TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
2. **Phone number format**: Use E.164 format: +12012149984
3. **Twilio number**: Ensure TWILIO_FROM_NUMBER is correct
4. **Account balance**: Check Twilio account has credits
5. **Installation**: Run `pip install twilio`

### Check Logs

Notifications are logged. Check logs for errors:

```bash
tail -f logs/api_server.log | grep -i notification
```

## Security Notes

- **Never commit** `.env` file to git
- Use **app passwords** for email (not your main password)
- Keep Twilio credentials secure
- Consider using environment variables in production

## Cost

- **Email**: Free (Gmail)
- **SMS**: ~$0.0075 per message (Twilio pricing)
  - Free trial: $15.50 credit (~2,000 messages)

## Support

If notifications aren't working:
1. Check logs for error messages
2. Verify all environment variables are set
3. Test email/SMS manually
4. Check firewall/network settings

