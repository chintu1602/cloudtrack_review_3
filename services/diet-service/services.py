"""
Diet Service - Business Logic
GPT-4 diet plan generation with validation/retry, PDF generation,
and Azure Service Bus meal reminder publishing.
"""

import io
import json
import logging
from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID

from openai import AzureOpenAI
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from sqlalchemy.orm import Session

from config import get_settings
from models import Document, DietPlan, FoodAllergy, User

logger = logging.getLogger(__name__)
settings = get_settings()


# ============================================================
# OpenAI / GPT-4
# ============================================================

def get_openai_client() -> AzureOpenAI:
    return AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )


def truncate_to_tokens(text: str, max_tokens: int = 4000) -> str:
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]
    return truncated + "\n\n[Content truncated due to length]"


def build_system_prompt(allergies: list, enhanced: bool = False) -> str:
    allergy_section = ""
    if allergies:
        allergy_section = "\n\n⚠️ CRITICAL PATIENT ALLERGIES - NEVER RECOMMEND THESE FOODS:\n"
        for allergy in allergies:
            allergy_section += f"- {allergy['allergen_name']} (Severity: {allergy['severity'].upper()})"
            if allergy.get('notes'):
                allergy_section += f" - Notes: {allergy['notes']}"
            allergy_section += "\n"
        allergy_section += "\nYou MUST NEVER recommend any food containing the above allergens. "
        allergy_section += "This is a medical safety requirement. If any allergen is found in a food item, "
        allergy_section += "it MUST be listed in foods_to_avoid with appropriate risk level. "
        allergy_section += "Include specific allergy warnings in the allergy_notes field."
    else:
        allergy_section = "\n\nNo known food allergies reported for this patient."

    enhanced_instruction = ""
    if enhanced:
        enhanced_instruction = """

IMPORTANT: You MUST include at least 5 foods to eat and at least 5 foods to avoid.
Each food_to_eat item MUST have food_name, reason, portion_size, and timing fields.
Each food_to_avoid item MUST have food_name, reason, and risk_level fields.
Failure to include these fields will result in rejection of your response.
"""

    system_prompt = f"""You are a professional clinical nutritionist and dietitian AI assistant for the NutriAI Health Portal.
Your role is to analyze patient medical documents (lab reports, prescriptions, etc.) and generate personalized,
safe, and medically-appropriate diet plans.

{allergy_section}
{enhanced_instruction}

You MUST respond with valid JSON in the following exact structure:
{{
    "plan_title": "A descriptive title for the diet plan",
    "plan_summary": "A 2-3 sentence summary of the overall diet plan and its goals",
    "foods_to_eat": [
        {{
            "food_name": "Name of the food",
            "reason": "Medical reason why this food is recommended",
            "portion_size": "Recommended portion size (e.g., '1 cup', '100g')",
            "timing": "When to eat (e.g., 'Morning', 'With lunch')",
            "frequency": "How often (e.g., 'Daily', '3 times per week')"
        }}
    ],
    "foods_to_avoid": [
        {{
            "food_name": "Name of the food to avoid",
            "reason": "Medical reason why this food should be avoided",
            "risk_level": "high/medium/low"
        }}
    ],
    "weekly_meal_plan": {{
        "monday": {{
            "breakfast": "Detailed breakfast description",
            "lunch": "Detailed lunch description",
            "dinner": "Detailed dinner description",
            "snacks": "Recommended snacks"
        }},
        "tuesday": {{ ... }},
        "wednesday": {{ ... }},
        "thursday": {{ ... }},
        "friday": {{ ... }},
        "saturday": {{ ... }},
        "sunday": {{ ... }}
    }},
    "nutritional_guidelines": {{
        "daily_calories": 2000,
        "protein_grams": 60,
        "carbs_grams": 250,
        "fats_grams": 65,
        "fiber_grams": 30,
        "water_liters": 2.5
    }},
    "allergy_notes": [
        "Specific allergy-related warnings and notes"
    ],
    "additional_recommendations": [
        "Additional lifestyle and dietary recommendations"
    ]
}}

Guidelines:
1. Base your recommendations on the medical data provided in the documents.
2. Be specific with food names, portions, and timing.
3. Consider the patient's medical conditions when making recommendations.
4. Ensure the weekly meal plan is varied and nutritionally balanced.
5. Always prioritize patient safety, especially regarding allergies.
6. Provide practical, actionable advice that patients can easily follow.
7. Include all 7 days (monday through sunday) in the weekly meal plan.
8. Each day must have breakfast, lunch, dinner, and snacks.
"""
    return system_prompt


def validate_diet_plan_json(data: dict) -> bool:
    """Validate the GPT-4 response structure including food item fields."""
    required_fields = [
        "plan_title", "plan_summary", "foods_to_eat", "foods_to_avoid",
        "weekly_meal_plan", "nutritional_guidelines", "allergy_notes", "additional_recommendations",
    ]

    for field in required_fields:
        if field not in data:
            logger.warning(f"Missing required field: {field}")
            return False

    # Validate foods_to_eat is non-empty with required sub-fields
    if not isinstance(data["foods_to_eat"], list) or len(data["foods_to_eat"]) == 0:
        logger.warning("foods_to_eat is empty or not a list")
        return False

    for item in data["foods_to_eat"]:
        if not isinstance(item, dict):
            return False
        for req in ["food_name", "reason", "portion_size", "timing"]:
            if req not in item or not item[req]:
                logger.warning(f"foods_to_eat item missing '{req}'")
                return False

    # Validate foods_to_avoid is non-empty with required sub-fields
    if not isinstance(data["foods_to_avoid"], list) or len(data["foods_to_avoid"]) == 0:
        logger.warning("foods_to_avoid is empty or not a list")
        return False

    for item in data["foods_to_avoid"]:
        if not isinstance(item, dict):
            return False
        for req in ["food_name", "reason", "risk_level"]:
            if req not in item or not item[req]:
                logger.warning(f"foods_to_avoid item missing '{req}'")
                return False

    if not isinstance(data["nutritional_guidelines"], dict):
        return False

    return True


def generate_diet_plan_ai(
    ocr_content: str,
    allergies: list,
    additional_notes: Optional[str] = None,
) -> Optional[dict]:
    """
    Generate a diet plan with up to 3 attempts (retry with enhanced prompt).
    """
    client = get_openai_client()
    truncated_content = truncate_to_tokens(ocr_content, max_tokens=4000)

    for attempt in range(3):
        try:
            enhanced = attempt > 0
            system_prompt = build_system_prompt(allergies, enhanced=enhanced)

            user_message = f"""Please analyze the following medical document content and generate a personalized diet plan.

--- MEDICAL DOCUMENT CONTENT ---
{truncated_content}
--- END DOCUMENT CONTENT ---
"""
            if additional_notes:
                user_message += f"""
--- ADDITIONAL PATIENT NOTES ---
{additional_notes}
--- END NOTES ---
"""

            logger.info(f"GPT-4 attempt {attempt + 1}/3 (enhanced={enhanced})")

            response = client.chat.completions.create(
                model=settings.AZURE_OPENAI_DEPLOYMENT_NAME,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=4000,
            )

            response_text = response.choices[0].message.content
            diet_plan_data = json.loads(response_text)

            if validate_diet_plan_json(diet_plan_data):
                logger.info(f"Diet plan generated successfully on attempt {attempt + 1}")
                return diet_plan_data
            else:
                logger.warning(f"Validation failed on attempt {attempt + 1}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error on attempt {attempt + 1}: {e}")
        except Exception as e:
            logger.error(f"OpenAI error on attempt {attempt + 1}: {e}")

    logger.error("All 3 diet plan generation attempts failed")
    return None


# ============================================================
# Service Bus - Meal Reminder Publishing
# ============================================================

def publish_meal_reminders(diet_plan: DietPlan, user_email: str):
    """
    Publish 28 messages (7 days × 4 meals) to Service Bus topic
    with scheduled_enqueue_time at actual meal times.
    """
    if not settings.AZURE_SERVICE_BUS_CONNECTION_STRING:
        logger.warning("Service Bus connection string not configured, skipping meal reminders")
        return

    try:
        from azure.servicebus import ServiceBusClient, ServiceBusMessage

        meal_times = {
            "breakfast": 8,   # 8:00 AM UTC
            "lunch": 13,      # 1:00 PM UTC
            "snack": 16,      # 4:00 PM UTC
            "dinner": 19,     # 7:00 PM UTC
        }

        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        today = datetime.utcnow().date()
        # Find next Monday
        days_ahead = (7 - today.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        next_monday = today + timedelta(days=days_ahead)

        servicebus_client = ServiceBusClient.from_connection_string(
            settings.AZURE_SERVICE_BUS_CONNECTION_STRING
        )

        with servicebus_client:
            sender = servicebus_client.get_topic_sender(topic_name=settings.AZURE_SERVICE_BUS_TOPIC_NAME)
            with sender:
                messages_sent = 0
                weekly_plan = diet_plan.weekly_meal_plan or {}

                for day_index, day_name in enumerate(days):
                    day_date = next_monday + timedelta(days=day_index)
                    day_plan = weekly_plan.get(day_name, {})

                    for meal_type, hour in meal_times.items():
                        meal_key = "snacks" if meal_type == "snack" else meal_type
                        meal_description = day_plan.get(meal_key, day_plan.get(meal_type, ""))

                        # Build foods_to_eat and foods_to_avoid for this meal
                        foods_eat = []
                        for food in (diet_plan.foods_to_eat or []):
                            foods_eat.append({
                                "food_name": food.get("food_name", ""),
                                "portion_size": food.get("portion_size", ""),
                                "timing": food.get("timing", ""),
                                "reason": food.get("reason", ""),
                            })

                        foods_avoid = []
                        for food in (diet_plan.foods_to_avoid or []):
                            foods_avoid.append({
                                "food_name": food.get("food_name", ""),
                                "reason": food.get("reason", ""),
                                "risk_level": food.get("risk_level", ""),
                            })

                        message_body = json.dumps({
                            "user_id": str(diet_plan.user_id),
                            "user_email": user_email,
                            "meal_type": meal_type,
                            "foods_to_eat": foods_eat,
                            "foods_to_avoid": foods_avoid,
                            "day_name": day_name.capitalize(),
                            "meal_description": meal_description,
                        })

                        scheduled_time = datetime(
                            day_date.year, day_date.month, day_date.day,
                            hour, 0, 0
                        )

                        msg = ServiceBusMessage(
                            body=message_body,
                            content_type="application/json",
                            subject=f"meal-reminder-{day_name}-{meal_type}",
                            scheduled_enqueue_time_utc=scheduled_time,
                        )
                        sender.send_messages(msg)
                        messages_sent += 1

                logger.info(f"Published {messages_sent} meal reminder messages to Service Bus")

    except ImportError:
        logger.warning("azure-servicebus not installed, skipping meal reminders")
    except Exception as e:
        logger.error(f"Error publishing meal reminders to Service Bus: {e}")


# ============================================================
# Diet Plan Orchestration
# ============================================================

def create_diet_plan(
    db: Session,
    user_id: str,
    document_ids: List[str],
    additional_notes: Optional[str] = None,
) -> Optional[DietPlan]:
    try:
        # Fetch documents
        documents = []
        combined_ocr = ""
        for doc_id in document_ids:
            doc = db.query(Document).filter(
                Document.id == doc_id,
                Document.user_id == user_id,
                Document.ocr_status == "completed",
            ).first()
            if doc and doc.ocr_content:
                documents.append(doc)
                combined_ocr += f"\n--- Document: {doc.original_filename} (Type: {doc.document_type}) ---\n"
                combined_ocr += doc.ocr_content + "\n"

        if not documents:
            logger.warning(f"No valid documents found for user: {user_id}")
            return None

        # Gather allergies
        allergies = db.query(FoodAllergy).filter(FoodAllergy.user_id == user_id).all()
        allergy_list = [
            {"allergen_name": a.allergen_name, "severity": a.severity, "notes": a.notes or ""}
            for a in allergies
        ]

        # Generate with AI (with retry/validation)
        plan_data = generate_diet_plan_ai(
            ocr_content=combined_ocr,
            allergies=allergy_list,
            additional_notes=additional_notes,
        )

        if not plan_data:
            logger.error("All GPT-4 attempts failed")
            return None

        # Save to database
        diet_plan = DietPlan(
            user_id=user_id,
            document_ids=[str(d.id) for d in documents],
            plan_title=plan_data.get("plan_title", "Personalized Diet Plan"),
            plan_summary=plan_data.get("plan_summary", ""),
            foods_to_eat=plan_data.get("foods_to_eat", []),
            foods_to_avoid=plan_data.get("foods_to_avoid", []),
            weekly_meal_plan=plan_data.get("weekly_meal_plan", {}),
            nutritional_guidelines=plan_data.get("nutritional_guidelines", {}),
            allergy_notes=plan_data.get("allergy_notes", []),
            additional_recommendations=plan_data.get("additional_recommendations", []),
            is_active=True,
        )
        db.add(diet_plan)
        db.commit()
        db.refresh(diet_plan)

        # Publish meal reminders to Service Bus
        user = db.query(User).filter(User.id == user_id).first()
        user_email = user.email if user else ""
        publish_meal_reminders(diet_plan, user_email)

        logger.info(f"Diet plan created: {diet_plan.id}")
        return diet_plan

    except Exception as e:
        logger.error(f"Error creating diet plan: {e}")
        db.rollback()
        return None


def get_diet_plans(db: Session, user_id: str) -> List[DietPlan]:
    return (
        db.query(DietPlan)
        .filter(DietPlan.user_id == user_id)
        .order_by(DietPlan.generated_at.desc())
        .all()
    )


def get_diet_plan_detail(db: Session, plan_id: str, user_id: str) -> Optional[DietPlan]:
    return (
        db.query(DietPlan)
        .filter(DietPlan.id == plan_id, DietPlan.user_id == user_id)
        .first()
    )


# ============================================================
# PDF Generation
# ============================================================

def generate_diet_plan_pdf(plan: DietPlan) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5 * inch, bottomMargin=0.5 * inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "CustomTitle", parent=styles["Title"],
        fontSize=20, textColor=colors.HexColor("#2E7D32"), spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "CustomHeading", parent=styles["Heading2"],
        fontSize=14, textColor=colors.HexColor("#1565C0"), spaceAfter=8, spaceBefore=12,
    )
    body_style = styles["Normal"]
    body_style.fontSize = 10
    body_style.leading = 14

    elements = []

    elements.append(Paragraph(f"🥗 {plan.plan_title}", title_style))
    elements.append(Paragraph(f"Generated: {plan.generated_at.strftime('%B %d, %Y')}", body_style))
    elements.append(Spacer(1, 12))

    if plan.plan_summary:
        elements.append(Paragraph("Plan Summary", heading_style))
        elements.append(Paragraph(plan.plan_summary, body_style))
        elements.append(Spacer(1, 8))

    if plan.foods_to_eat:
        elements.append(Paragraph("✅ Foods to Eat", heading_style))
        table_data = [["Food", "Reason", "Portion", "Timing"]]
        for food in plan.foods_to_eat:
            table_data.append([
                food.get("food_name", ""), food.get("reason", ""),
                food.get("portion_size", ""), food.get("timing", ""),
            ])
        table = Table(table_data, colWidths=[1.5 * inch, 2.5 * inch, 1.2 * inch, 1.3 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E7D32")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#E8F5E9"), colors.white]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 8))

    if plan.foods_to_avoid:
        elements.append(Paragraph("❌ Foods to Avoid", heading_style))
        table_data = [["Food", "Reason", "Risk Level"]]
        for food in plan.foods_to_avoid:
            table_data.append([
                food.get("food_name", ""), food.get("reason", ""), food.get("risk_level", ""),
            ])
        table = Table(table_data, colWidths=[2 * inch, 3 * inch, 1.5 * inch])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#C62828")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#FFEBEE"), colors.white]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 8))

    if plan.weekly_meal_plan:
        elements.append(Paragraph("📅 Weekly Meal Plan", heading_style))
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in days:
            day_plan = plan.weekly_meal_plan.get(day, {})
            if day_plan:
                elements.append(Paragraph(f"<b>{day.capitalize()}</b>", body_style))
                for meal_type in ["breakfast", "lunch", "dinner", "snacks"]:
                    meal = day_plan.get(meal_type, "")
                    if meal:
                        elements.append(Paragraph(f"  • {meal_type.capitalize()}: {meal}", body_style))
                elements.append(Spacer(1, 4))

    if plan.nutritional_guidelines:
        elements.append(Paragraph("📊 Nutritional Guidelines", heading_style))
        ng = plan.nutritional_guidelines
        guidelines_text = f"""
        Daily Calories: {ng.get('daily_calories', 'N/A')} kcal |
        Protein: {ng.get('protein_grams', 'N/A')}g |
        Carbs: {ng.get('carbs_grams', 'N/A')}g |
        Fats: {ng.get('fats_grams', 'N/A')}g |
        Fiber: {ng.get('fiber_grams', 'N/A')}g |
        Water: {ng.get('water_liters', 'N/A')}L
        """
        elements.append(Paragraph(guidelines_text.strip(), body_style))
        elements.append(Spacer(1, 8))

    if plan.allergy_notes:
        elements.append(Paragraph("⚠️ Allergy Notes", heading_style))
        for note in plan.allergy_notes:
            elements.append(Paragraph(f"• {note}", body_style))
        elements.append(Spacer(1, 8))

    if plan.additional_recommendations:
        elements.append(Paragraph("💡 Additional Recommendations", heading_style))
        for rec in plan.additional_recommendations:
            elements.append(Paragraph(f"• {rec}", body_style))

    elements.append(Spacer(1, 20))
    footer_style = ParagraphStyle("Footer", parent=body_style, fontSize=8, textColor=colors.grey)
    elements.append(Paragraph(
        "Generated by NutriAI Health Portal. This plan is AI-generated and should be reviewed by a healthcare professional.",
        footer_style,
    ))

    doc.build(elements)
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes
