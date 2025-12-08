import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.host = os.getenv('EMAIL_HOST')
        self.port = int(os.getenv('EMAIL_PORT', 587))
        self.username = os.getenv('EMAIL_USERNAME')
        self.password = os.getenv('EMAIL_PASSWORD')
        self.from_email = os.getenv('EMAIL_FROM')
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str,
        text_content: str = None
    ):
        """
        Send an email using SMTP with STARTTLS
        """
        try:
            # Create message
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = self.from_email
            message['To'] = to_email
            
            # Add plain text version (fallback)
            if text_content:
                text_part = MIMEText(text_content, 'plain')
                message.attach(text_part)
            
            # Add HTML version
            html_part = MIMEText(html_content, 'html')
            message.attach(html_part)
            
            # Send email with explicit STARTTLS configuration
            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.username,
                password=self.password,
                use_tls=False,  # We're using STARTTLS instead of direct TLS
                start_tls=True,  # Enable STARTTLS
                timeout=10
            )
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {str(e)}", exc_info=True)
            return False
    
    async def send_password_reset_email(self, to_email: str, reset_link: str, username: str):
        """
        Send password reset email with nice HTML formatting
        """
        subject = "Reset Your Password - BetYetu"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .container {{
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background-color: #4CAF50;
                    color: white;
                    padding: 20px;
                    text-align: center;
                    border-radius: 5px 5px 0 0;
                }}
                .content {{
                    background-color: #f9f9f9;
                    padding: 30px;
                    border-radius: 0 0 5px 5px;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    margin: 20px 0;
                    background-color: #4CAF50;
                    color: white !important;
                    text-decoration: none;
                    border-radius: 5px;
                    font-weight: bold;
                }}
                .footer {{
                    margin-top: 20px;
                    padding-top: 20px;
                    border-top: 1px solid #ddd;
                    font-size: 12px;
                    color: #666;
                }}
                .warning {{
                    background-color: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 10px;
                    margin: 15px 0;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Reset Your Password</h1>
                </div>
                <div class="content">
                    <p>Hi {username},</p>
                    
                    <p>We received a request to reset your password for your BetYetu account.</p>
                    
                    <p>Click the button below to reset your password:</p>
                    
                    <center>
                        <a href="{reset_link}" class="button">Reset Password</a>
                    </center>
                    
                    <p>Or copy and paste this link into your browser:</p>
                    <p style="word-break: break-all; color: #666;">{reset_link}</p>
                    
                    <div class="warning">
                        <strong>⚠️ Security Notice:</strong>
                        <ul>
                            <li>This link expires in 1 hour</li>
                            <li>If you didn't request this, please ignore this email</li>
                            <li>Your password will remain unchanged</li>
                        </ul>
                    </div>
                    
                    <div class="footer">
                        <p>If you have any questions, contact us at support@betyetu.com</p>
                        <p>© 2024 BetYetu. All rights reserved.</p>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """
        
        text_content = f"""
        Hi {username},
        
        We received a request to reset your password for your BetYetu account.
        
        Click this link to reset your password:
        {reset_link}
        
        This link expires in 1 hour.
        
        If you didn't request this, please ignore this email.
        Your password will remain unchanged.
        
        © 2024 BetYetu
        """
        
        return await self.send_email(to_email, subject, html_content, text_content)

# Create global instance
email_service = EmailService()