"""
Telegram Bot for UMEagleEye Infrastructure Monitoring
Sends alerts and notifications about discovered assets and critical events
"""

import logging
from typing import Optional

from dotenv import load_dotenv

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TelegramBot:
    """Telegram bot for sending infrastructure notifications."""

    def __init__(self, bot_token: str, chat_id: str):
        """
        Initialize Telegram bot.

        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Telegram chat/channel ID to send messages to
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"
        logger.info(f"Telegram bot initialized for chat {chat_id}")

    async def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send a text message to Telegram.

        Args:
            text: Message text (supports HTML formatting)
            parse_mode: "HTML" or "Markdown"

        Returns:
            True if successful, False otherwise
        """
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.api_url}/sendMessage",
                    json={
                        "chat_id": self.chat_id,
                        "text": text,
                        "parse_mode": parse_mode,
                    },
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as response:
                    if response.status == 200:
                        logger.info(f"Message sent successfully")
                        return True
                    else:
                        logger.error(f"Failed to send message: {response.status}")
                        return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def send_message_sync(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        Send a text message synchronously (blocking).

        Args:
            text: Message text (supports HTML formatting)
            parse_mode: "HTML" or "Markdown"

        Returns:
            True if successful, False otherwise
        """
        try:
            import requests

            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    "chat_id": int(self.chat_id),
                    "text": text,
                    "parse_mode": parse_mode,
                },
                timeout=10,
            )
            logger.debug(f"API URL: {self.api_url}, Chat ID: {int(self.chat_id)}")
            if response.status_code == 200:
                logger.info("Message sent successfully")
                return True
            else:
                logger.error(f"Failed to send message: {response.status_code}")
                logger.error(f"Response: {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            return False

    def notify_asset_discovered(self, hostname: str, ip: str, device_type: str) -> bool:
        """Send notification when a new asset is discovered."""
        message = f"""
<b>🆕 Asset Discovered</b>

<b>Hostname:</b> {hostname}
<b>IP Address:</b> {ip}
<b>Device Type:</b> {device_type}

A new asset has been added to the infrastructure inventory.
        """
        return self.send_message_sync(message.strip())

    def notify_critical_asset(
        self, hostname: str, ip: str, criticality: int, reason: str = None
    ) -> bool:
        """Send alert for critical asset."""
        reason_text = f"<b>Reason:</b> {reason}\n" if reason else ""
        message = f"""
<b>🚨 Critical Asset Alert</b>

<b>Hostname:</b> {hostname}
<b>IP Address:</b> {ip}
<b>Criticality Score:</b> {criticality}/10
{reason_text}
This asset requires immediate attention.
        """
        return self.send_message_sync(message.strip())

    def notify_scan_completed(
        self, network_range: str, discovered_count: int, stored_count: int
    ) -> bool:
        """Send notification when network scan completes."""
        message = f"""
<b>✅ Network Scan Completed</b>

<b>Network Range:</b> {network_range}
<b>Hosts Discovered:</b> {discovered_count}
<b>Assets Stored:</b> {stored_count}

Scan has finished. Check the dashboard for results.
        """
        return self.send_message_sync(message.strip())

    def notify_scan_failed(self, network_range: str, error: str) -> bool:
        """Send alert when network scan fails."""
        message = f"""
<b>❌ Network Scan Failed</b>

<b>Network Range:</b> {network_range}
<b>Error:</b> {error}

Please check the worker logs and retry.
        """
        return self.send_message_sync(message.strip())

    def send_daily_summary(
        self, total_assets: int, critical_assets: int, new_assets: int
    ) -> bool:
        """Send daily summary report."""
        message = f"""
<b>📊 Daily Summary Report</b>

<b>Total Assets:</b> {total_assets}
<b>Critical Assets:</b> {critical_assets}
<b>New Assets (today):</b> {new_assets}

Review the full dashboard for more details.
        """
        return self.send_message_sync(message.strip())


def get_telegram_bot() -> Optional[TelegramBot]:
    """Create Telegram bot instance from environment variables."""
    import os
    from pathlib import Path
    
    # Load from project root
    env_path = Path(__file__).parent.parent / ".env"
    load_dotenv(env_path)
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not bot_token or not chat_id:
        logger.warning("Telegram credentials not configured. Bot disabled.")
        return None

    return TelegramBot(bot_token, chat_id)


if __name__ == "__main__":
    # Example usage
    import os
    from pathlib import Path
    
    # Load from project root
    env_path = Path(__file__).parent.parent / ".env"
    print(f"Loading .env from: {env_path}")
    print(f"  File exists: {env_path.exists()}")
    
    load_dotenv(env_path)
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "YOUR_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "YOUR_CHAT_ID")
    
    print(f"  TELEGRAM_BOT_TOKEN: {'✓ Set' if bot_token != 'YOUR_BOT_TOKEN' else '✗ Not set'}")
    print(f"  TELEGRAM_CHAT_ID: {'✓ Set' if chat_id != 'YOUR_CHAT_ID' else '✗ Not set'}")

    if bot_token == "YOUR_BOT_TOKEN":
        print("Please configure TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables")
        print("\nSetup instructions:")
        print("1. Create a Telegram bot with @BotFather")
        print("2. Get your chat ID using @userinfobot")
        print("3. Set environment variables:")
        print("   export TELEGRAM_BOT_TOKEN=your_token")
        print("   export TELEGRAM_CHAT_ID=your_chat_id")
    else:
        bot = TelegramBot(bot_token, chat_id)
        # Test the bot
        sent = bot.send_message_sync("<b>Test Message</b>\nTelegram bot is working!")
        if sent:
            print("Test message sent!")
        else:
            print("Test message failed. Check TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID and network access.")
