"""
Free email notification service for pizza orders
No cost alternative to SMS
"""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class FreeEmailService:
    """Send free email notifications to customers"""
    
    def __init__(self):
        # Using Gmail (free) - credentials from .env
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email = os.getenv("GMAIL_EMAIL")
        self.password = os.getenv("GMAIL_APP_PASSWORD")
        self.demo_mode = False  # Enable real emails
        
    def send_order_accepted_email(self, customer_email: str, order_data: dict):
        """Send order accepted email (FREE)"""
        try:
            subject = f"🍕 Order Accepted - #{order_data.get('order_id')}"
            
            html_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #d32f2f;">🍕 ORDER ACCEPTED!</h2>
                
                <div style="background: #e8f5e8; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3>✅ Your order has been accepted by the restaurant!</h3>
                    <p><strong>Order ID:</strong> #{order_data.get('order_id')}</p>
                    <p><strong>Items:</strong></p>
                    <ul>
            """
            
            for item in order_data.get('items', []):
                html_body += f"<li>{item.get('pizza')} ({item.get('size')}) x{item.get('quantity')}</li>"
            
            html_body += f"""
                    </ul>
                    <p><strong>Total:</strong> Rs.{order_data.get('total_price')}</p>
                    <p><strong>Preparation Time:</strong> {order_data.get('prep_time')}</p>
                    <p><strong>🍕 Ready for Pickup:</strong> {order_data.get('estimated_ready')}</p>
                    <p><strong>🚚 Estimated Delivery:</strong> {order_data.get('estimated_delivery')}</p>
                </div>
                
                <p>We'll email you again when your pizza is ready for delivery!</p>
                <p>Thank you for choosing us! 🍕</p>
            </div>
            """
            
            if self.demo_mode:
                print("\n" + "="*60)
                print("📧 FREE EMAIL NOTIFICATION 1: ORDER ACCEPTED")
                print("="*60)
                print(f"📧 To: {customer_email}")
                print(f"📝 Subject: {subject}")
                print("📄 Content: Order acceptance confirmation with details")
                print("💰 Cost: FREE")
                print("="*60)
                return True
            else:
                # Send real email
                msg = MIMEMultipart()
                msg['From'] = self.email
                msg['To'] = customer_email
                msg['Subject'] = subject
                msg.attach(MIMEText(html_body, 'html'))
                
                try:
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                    server.starttls()
                    server.login(self.email, self.password)
                    server.send_message(msg)
                    server.quit()
                    
                    print(f"✅ REAL EMAIL SENT to {customer_email}")
                    print(f"📧 Subject: {subject}")
                    return True
                    
                except Exception as email_error:
                    print(f"❌ Email sending failed: {email_error}")
                    # Fallback to demo mode
                    print("\n" + "="*60)
                    print("📧 EMAIL FALLBACK (Demo Mode)")
                    print("="*60)
                    print(f"📧 To: {customer_email}")
                    print(f"📝 Subject: {subject}")
                    print("📄 Content: Order acceptance confirmation")
                    print("⚠️  Real email failed, showing demo")
                    print("="*60)
                    return False
                
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False
    
    def send_pizza_ready_email(self, customer_email: str, order_data: dict):
        """Send pizza ready email (FREE)"""
        try:
            subject = f"🍕 Pizza Ready for Delivery - #{order_data.get('order_id')}"
            
            html_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #d32f2f;">🍕 PIZZA READY FOR DELIVERY!</h2>
                
                <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3>🚚 Your pizza is ready and out for delivery!</h3>
                    <p><strong>Order ID:</strong> #{order_data.get('order_id')}</p>
                    <p><strong>Items:</strong></p>
                    <ul>
            """
            
            for item in order_data.get('items', []):
                html_body += f"<li>{item.get('pizza')} ({item.get('size')})</li>"
            
            html_body += f"""
                    </ul>
                    <p><strong>📍 Delivery will arrive shortly!</strong></p>
                </div>
                
                <p>Thank you for your patience! 🍕</p>
            </div>
            """
            
            if self.demo_mode:
                print("\n" + "="*60)
                print("📧 FREE EMAIL NOTIFICATION 2: PIZZA READY & OUT FOR DELIVERY")
                print("="*60)
                print(f"📧 To: {customer_email}")
                print(f"📝 Subject: {subject}")
                print("📄 Content: Pizza ready for delivery notification")
                print("💰 Cost: FREE")
                print("="*60)
                return True
            else:
                # Send real email
                msg = MIMEMultipart()
                msg['From'] = self.email
                msg['To'] = customer_email
                msg['Subject'] = subject
                msg.attach(MIMEText(html_body, 'html'))
                
                try:
                    server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                    server.starttls()
                    server.login(self.email, self.password)
                    server.send_message(msg)
                    server.quit()
                    
                    print(f"✅ REAL EMAIL SENT to {customer_email}")
                    print(f"📧 Subject: {subject}")
                    return True
                    
                except Exception as email_error:
                    print(f"❌ Email sending failed: {email_error}")
                    # Fallback to demo mode
                    print("\n" + "="*60)
                    print("📧 EMAIL FALLBACK (Demo Mode)")
                    print("="*60)
                    print(f"📧 To: {customer_email}")
                    print(f"📝 Subject: {subject}")
                    print("📄 Content: Pizza ready notification")
                    print("⚠️  Real email failed, showing demo")
                    print("="*60)
                    return False
                
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False
    
    def send_order_rejected_email(self, customer_email: str, order_data: dict):
        """Send order rejection email (FREE)"""
        try:
            subject = f"🍕 Order Update - #{order_data.get('order_id')}"
            
            html_body = f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #d32f2f;">🍕 Order Update</h2>
                
                <div style="background: #ffebee; padding: 20px; border-radius: 8px; margin: 20px 0;">
                    <h3>We're sorry, but we cannot fulfill your order at this time.</h3>
                    <p><strong>Order ID:</strong> #{order_data.get('order_id')}</p>
                    <p><strong>Items:</strong></p>
                    <ul>
            """
            
            for item in order_data.get('items', []):
                html_body += f"<li>{item.get('pizza')} ({item.get('size')}) x{item.get('quantity')}</li>"
            
            html_body += f"""
                    </ul>
                    <p><strong>Total:</strong> Rs.{order_data.get('total_price')}</p>
                    <p>This may be due to ingredient availability or high demand. Please try ordering again later or contact us directly.</p>
                </div>
                
                <p>We apologize for any inconvenience. Thank you for choosing us! 🍕</p>
            </div>
            """
            
            if self.demo_mode:
                print("\n" + "="*60)
                print("📧 FREE EMAIL NOTIFICATION: ORDER REJECTED")
                print("="*60)
                print(f"📧 To: {customer_email}")
                print(f"📝 Subject: {subject}")
                print("📄 Content: Order rejection notification")
                print("💰 Cost: FREE")
                print("="*60)
                return True
            else:
                # Send real email
                msg = MIMEMultipart()
                msg['From'] = self.email
                msg['To'] = customer_email
                msg['Subject'] = subject
                msg.attach(MIMEText(html_body, 'html'))
                
                with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                    server.starttls()
                    server.login(self.email, self.password)
                    server.send_message(msg)
                
                return True
                
        except Exception as e:
            print(f"Email sending failed: {e}")
            return False

# Global free email service
free_email_service = FreeEmailService()
