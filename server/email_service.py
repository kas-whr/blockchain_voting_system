"""
Email Service for Token Distribution

Sends one-time voting tokens to voters via email.
"""

import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


class EmailConfig:
    """Email service configuration."""

    def __init__(self,
                 smtp_host="localhost",
                 smtp_port=1025,
                 sender_email="voting@system.local",
                 sender_name="Voting System"):
        """
        Initialize email configuration.

        Args:
            smtp_host: SMTP server hostname
            smtp_port: SMTP server port
            sender_email: Sender email address
            sender_name: Sender display name
        """
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.sender_email = sender_email
        self.sender_name = sender_name


class EmailService:
    """Service for sending voting tokens via email."""

    def __init__(self, config=None):
        """
        Initialize email service.

        Args:
            config: EmailConfig instance (optional, uses defaults if None)
        """
        self.config = config or EmailConfig()
        self.sent_emails = []

    def send_voting_token(self, recipient_email, token, test_mode=False):
        """
        Send voting token to a recipient.

        Args:
            recipient_email: Recipient email address
            token: Voting token to send
            test_mode: If True, don't actually send (useful for testing)

        Returns:
            bool: True if sent successfully

        Raises:
            Exception: If email fails to send
        """
        subject = "Your Voting Token"

        # Create email body
        body = f"""
Anonymous Voting System

Your one-time voting token is:

    {token}

Keep this token safe. You will need it to vote.

Instructions:
1. Connect to the voting system
2. When prompted, enter your voting token
3. Select your candidate
4. Submit your vote
5. You will receive a digital receipt that you can use to verify your vote

Important:
- Each token can only be used once
- Do not share your token with anyone
- This token is NOT tied to your identity in the system

Best regards,
Voting System Administrator
"""

        if test_mode:
            print(f"[TEST MODE] Email would be sent to {recipient_email}")
            print(f"Subject: {subject}")
            print(f"Body: {body[:100]}...")
            self.sent_emails.append({
                "to": recipient_email,
                "timestamp": datetime.now().isoformat(),
                "status": "test_mode"
            })
            return True

        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.config.sender_name} <{self.config.sender_email}>"
            msg["To"] = recipient_email

            # Add body
            part = MIMEText(body, "plain")
            msg.attach(part)

            # Send email
            with smtplib.SMTP(self.config.smtp_host, self.config.smtp_port) as server:
                server.sendmail(
                    self.config.sender_email,
                    [recipient_email],
                    msg.as_string()
                )

            # Log sent email
            self.sent_emails.append({
                "to": recipient_email,
                "timestamp": datetime.now().isoformat(),
                "status": "sent"
            })

            return True

        except Exception as e:
            print(f"✗ Failed to send email to {recipient_email}: {e}")
            self.sent_emails.append({
                "to": recipient_email,
                "timestamp": datetime.now().isoformat(),
                "status": "failed",
                "error": str(e)
            })
            raise

    def send_tokens_batch(self, email_token_pairs, test_mode=False):
        """
        Send tokens to multiple recipients.

        Args:
            email_token_pairs: List of (email, token) tuples
            test_mode: If True, don't actually send

        Returns:
            dict: {
                "total": int,
                "sent": int,
                "failed": int
            }
        """
        results = {
            "total": len(email_token_pairs),
            "sent": 0,
            "failed": 0
        }

        for email, token in email_token_pairs:
            try:
                self.send_voting_token(email, token, test_mode=test_mode)
                results["sent"] += 1
            except Exception as e:
                results["failed"] += 1
                print(f"✗ Failed to send token to {email}: {e}")

        return results

    def get_sent_log(self):
        """Get log of sent emails."""
        return self.sent_emails.copy()

    def clear_log(self):
        """Clear sent email log."""
        self.sent_emails = []
