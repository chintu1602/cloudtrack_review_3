"""
Notification Service - Service Bus Consumer + Email Sender
Background asyncio task that subscribes to Service Bus and sends meal reminder emails.
"""

import asyncio
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from config import get_settings
from database import get_db_session
from models import Notification

logger = logging.getLogger(__name__)
settings = get_settings()


def build_meal_reminder_html(data: dict) -> str:
    """Build styled HTML email for meal reminder."""
    meal_type = data.get("meal_type", "meal").capitalize()
    day_name = data.get("day_name", "Today")
    foods_to_eat = data.get("foods_to_eat", [])
    foods_to_avoid = data.get("foods_to_avoid", [])
    app_url = settings.APP_URL

    eat_rows = ""
    for food in foods_to_eat:
        eat_rows += f"""
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0; color: #333;">{food.get('food_name', '')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0; color: #666;">{food.get('portion_size', '')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0; color: #666;">{food.get('timing', '')}</td>
        </tr>"""

    avoid_rows = ""
    for food in foods_to_avoid:
        avoid_rows += f"""
        <tr>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0; color: #333;">{food.get('food_name', '')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0; color: #666;">{food.get('reason', '')}</td>
            <td style="padding: 8px 12px; border-bottom: 1px solid #e0e0e0; color: #666;">{food.get('risk_level', '')}</td>
        </tr>"""

    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"></head>
    <body style="margin: 0; padding: 0; font-family: 'Inter', Arial, sans-serif; background-color: #f5f5f5;">
        <div style="max-width: 600px; margin: 0 auto; background: #ffffff;">
            <!-- Header -->
            <div style="background: linear-gradient(135deg, #2E7D32 0%, #1565C0 100%); padding: 24px; text-align: center;">
                <h1 style="color: #ffffff; margin: 0; font-size: 24px;">🍽️ NutriAI Meal Reminder</h1>
                <p style="color: rgba(255,255,255,0.9); margin: 8px 0 0; font-size: 14px;">Your {meal_type} for {day_name}</p>
            </div>

            <div style="padding: 24px;">
                <!-- What to Eat -->
                <div style="margin-bottom: 24px;">
                    <h2 style="color: #2E7D32; font-size: 18px; margin-bottom: 12px; border-bottom: 2px solid #2E7D32; padding-bottom: 8px;">
                        ✅ What to Eat
                    </h2>
                    <table style="width: 100%; border-collapse: collapse; background: #E8F5E9; border-radius: 8px; overflow: hidden;">
                        <thead>
                            <tr style="background: #2E7D32;">
                                <th style="padding: 10px 12px; text-align: left; color: #fff; font-size: 13px;">Food</th>
                                <th style="padding: 10px 12px; text-align: left; color: #fff; font-size: 13px;">Portion</th>
                                <th style="padding: 10px 12px; text-align: left; color: #fff; font-size: 13px;">Timing</th>
                            </tr>
                        </thead>
                        <tbody>
                            {eat_rows}
                        </tbody>
                    </table>
                </div>

                <!-- What NOT to Eat -->
                <div style="margin-bottom: 24px;">
                    <h2 style="color: #C62828; font-size: 18px; margin-bottom: 12px; border-bottom: 2px solid #C62828; padding-bottom: 8px;">
                        ❌ What NOT to Eat
                    </h2>
                    <table style="width: 100%; border-collapse: collapse; background: #FFEBEE; border-radius: 8px; overflow: hidden;">
                        <thead>
                            <tr style="background: #C62828;">
                                <th style="padding: 10px 12px; text-align: left; color: #fff; font-size: 13px;">Food</th>
                                <th style="padding: 10px 12px; text-align: left; color: #fff; font-size: 13px;">Reason</th>
                                <th style="padding: 10px 12px; text-align: left; color: #fff; font-size: 13px;">Risk</th>
                            </tr>
                        </thead>
                        <tbody>
                            {avoid_rows}
                        </tbody>
                    </table>
                </div>
            </div>

            <!-- Footer -->
            <div style="background: #212121; padding: 20px; text-align: center;">
                <p style="color: rgba(255,255,255,0.7); margin: 0 0 8px; font-size: 13px;">
                    View your full diet plan on NutriAI Health Portal
                </p>
                <a href="{app_url}/dashboard" style="display: inline-block; background: #2E7D32; color: #fff; padding: 10px 24px; border-radius: 20px; text-decoration: none; font-weight: 600; font-size: 14px;">
                    Open NutriAI →
                </a>
                <p style="color: rgba(255,255,255,0.5); margin: 12px 0 0; font-size: 11px;">
                    © 2026 NutriAI Health Portal. This is an automated reminder.
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_email_smtp(to_email: str, subject: str, html_content: str):
    """Send email via SMTP."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.SMTP_FROM_EMAIL
        msg["To"] = to_email
        msg.attach(MIMEText(html_content, "html"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM_EMAIL, to_email, msg.as_string())

        logger.info(f"Email sent via SMTP to {to_email}")
    except Exception as e:
        logger.error(f"SMTP email error: {e}")
        raise


def send_email_sendgrid(to_email: str, subject: str, html_content: str):
    """Send email via SendGrid."""
    try:
        import sendgrid
        from sendgrid.helpers.mail import Mail, Email, To, Content

        sg = sendgrid.SendGridAPIClient(api_key=settings.SENDGRID_API_KEY)
        message = Mail(
            from_email=Email(settings.SENDGRID_FROM_EMAIL),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content),
        )
        sg.client.mail.send.post(request_body=message.get())
        logger.info(f"Email sent via SendGrid to {to_email}")
    except Exception as e:
        logger.error(f"SendGrid email error: {e}")
        raise


def send_email(to_email: str, subject: str, html_content: str):
    """Send email using configured provider."""
    if settings.EMAIL_PROVIDER == "sendgrid":
        send_email_sendgrid(to_email, subject, html_content)
    else:
        send_email_smtp(to_email, subject, html_content)


async def service_bus_consumer():
    """Background asyncio task that subscribes to Service Bus and processes meal reminders."""
    if not settings.AZURE_SERVICE_BUS_CONNECTION_STRING:
        logger.warning("Service Bus connection string not configured, consumer disabled")
        return

    try:
        from azure.servicebus.aio import ServiceBusClient as AsyncServiceBusClient

        logger.info("Starting Service Bus consumer...")

        async with AsyncServiceBusClient.from_connection_string(
            settings.AZURE_SERVICE_BUS_CONNECTION_STRING
        ) as client:
            receiver = client.get_subscription_receiver(
                topic_name=settings.AZURE_SERVICE_BUS_TOPIC_NAME,
                subscription_name=settings.AZURE_SERVICE_BUS_SUBSCRIPTION_NAME,
            )

            async with receiver:
                while True:
                    try:
                        messages = await receiver.receive_messages(max_message_count=10, max_wait_time=30)

                        for msg in messages:
                            try:
                                body = json.loads(str(msg))
                                user_email = body.get("user_email", "")
                                meal_type = body.get("meal_type", "meal").capitalize()
                                day_name = body.get("day_name", "Today")

                                if user_email:
                                    subject = f"NutriAI Reminder: Your {meal_type} for {day_name}"
                                    html = build_meal_reminder_html(body)
                                    send_email(user_email, subject, html)

                                # Create notification record
                                db = get_db_session()
                                try:
                                    notification = Notification(
                                        user_id=body.get("user_id"),
                                        message=f"Meal reminder: {meal_type} for {day_name} has been sent to your email.",
                                        type="success",
                                        icon="fa-utensils",
                                        is_read=False,
                                        email_sent=True,
                                    )
                                    db.add(notification)
                                    db.commit()
                                finally:
                                    db.close()

                                await receiver.complete_message(msg)
                                logger.info(f"Processed meal reminder for {user_email}: {meal_type} - {day_name}")

                            except Exception as e:
                                logger.error(f"Error processing message: {e}")
                                await receiver.abandon_message(msg)

                    except Exception as e:
                        logger.error(f"Service Bus receive error: {e}")
                        await asyncio.sleep(10)

    except ImportError:
        logger.warning("azure-servicebus not installed, consumer disabled")
    except Exception as e:
        logger.error(f"Service Bus consumer fatal error: {e}")
