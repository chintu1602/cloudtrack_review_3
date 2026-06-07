"""
NutriAI Health Portal - Azure OpenAI Service
Generates personalized diet plans using GPT-4 with strict allergy safety constraints.
"""

import json
import logging
from typing import Optional

from openai import AzureOpenAI

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def get_openai_client() -> AzureOpenAI:
    """Create an Azure OpenAI client."""
    return AzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        api_key=settings.AZURE_OPENAI_KEY,
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )


def truncate_to_tokens(text: str, max_tokens: int = 4000) -> str:
    """
    Truncate text to approximately max_tokens.
    Uses rough estimation of ~4 characters per token.
    """
    max_chars = max_tokens * 4
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    # Try to break at a word boundary
    last_space = truncated.rfind(" ")
    if last_space > max_chars * 0.8:
        truncated = truncated[:last_space]
    return truncated + "\n\n[Content truncated due to length]"


def build_system_prompt(allergies: list) -> str:
    """
    Build the system prompt for diet plan generation.
    Explicitly lists all patient allergies with severity and instructs GPT-4
    to never recommend any allergen food under any circumstances.
    """
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

    system_prompt = f"""You are a professional clinical nutritionist and dietitian AI assistant for the NutriAI Health Portal.
Your role is to analyze patient medical documents (lab reports, prescriptions, etc.) and generate personalized,
safe, and medically-appropriate diet plans.

{allergy_section}

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


def generate_diet_plan(
    ocr_content: str,
    allergies: list,
    additional_notes: Optional[str] = None,
) -> Optional[dict]:
    """
    Generate a personalized diet plan using Azure OpenAI GPT-4.
    
    Args:
        ocr_content: Combined OCR text from patient documents (truncated to 4000 tokens)
        allergies: List of patient allergies with allergen_name, severity, and notes
        additional_notes: Optional additional notes from the patient
        
    Returns:
        Parsed JSON dict with diet plan or None on failure
    """
    try:
        client = get_openai_client()

        # Truncate OCR content to 4000 tokens
        truncated_content = truncate_to_tokens(ocr_content, max_tokens=4000)

        system_prompt = build_system_prompt(allergies)

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

        # Validate required fields
        if not validate_diet_plan_json(diet_plan_data):
            logger.error("GPT-4 response failed validation")
            return None

        logger.info("Diet plan generated successfully")
        return diet_plan_data

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GPT-4 JSON response: {e}")
        return None
    except Exception as e:
        logger.error(f"Error generating diet plan with OpenAI: {e}")
        return None


def validate_diet_plan_json(data: dict) -> bool:
    """
    Validate the structure of the GPT-4 diet plan response.
    
    Args:
        data: Parsed JSON dict from GPT-4
        
    Returns:
        True if the structure is valid
    """
    required_fields = [
        "plan_title",
        "plan_summary",
        "foods_to_eat",
        "foods_to_avoid",
        "weekly_meal_plan",
        "nutritional_guidelines",
        "allergy_notes",
        "additional_recommendations",
    ]

    for field in required_fields:
        if field not in data:
            logger.warning(f"Missing required field in diet plan: {field}")
            return False

    # Validate foods_to_eat structure
    if isinstance(data["foods_to_eat"], list):
        for item in data["foods_to_eat"]:
            if not isinstance(item, dict) or "food_name" not in item:
                logger.warning("Invalid foods_to_eat item structure")
                return False

    # Validate foods_to_avoid structure
    if isinstance(data["foods_to_avoid"], list):
        for item in data["foods_to_avoid"]:
            if not isinstance(item, dict) or "food_name" not in item:
                logger.warning("Invalid foods_to_avoid item structure")
                return False

    # Validate weekly_meal_plan has days
    if isinstance(data["weekly_meal_plan"], dict):
        required_days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        for day in required_days:
            if day not in data["weekly_meal_plan"]:
                logger.warning(f"Missing day in weekly_meal_plan: {day}")
                # Not a hard failure - GPT-4 might use different casing
                pass

    # Validate nutritional_guidelines
    if not isinstance(data["nutritional_guidelines"], dict):
        logger.warning("nutritional_guidelines is not a dict")
        return False

    return True
