"""
NutriAI Health Portal - Diet Plan Tests
Tests for diet plan generation, history, and detail views.
"""

import uuid
import json
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

from app.models.document import Document
from app.models.diet_plan import DietPlan
from app.models.user import FoodAllergy


class TestDietPlanPage:
    """Tests for the diet plan generator page."""

    def test_diet_plan_page_renders(self, authenticated_client):
        """Diet plan page should render for authenticated users."""
        response = authenticated_client.get("/diet-plan")
        assert response.status_code == 200

    def test_diet_plan_page_requires_auth(self, client):
        """Diet plan page should redirect unauthenticated users."""
        response = client.get("/diet-plan", follow_redirects=False)
        assert response.status_code == 302


class TestDietPlanHistory:
    """Tests for the diet plan history page."""

    def test_history_page_renders(self, authenticated_client):
        """History page should render for authenticated users."""
        response = authenticated_client.get("/diet-plan/history")
        assert response.status_code == 200

    def test_history_shows_user_plans(self, authenticated_client, db_session, test_user):
        """History should display the user's diet plans."""
        plan = DietPlan(
            id=uuid.uuid4(),
            user_id=test_user.id,
            document_ids=json.dumps([str(uuid.uuid4())]),
            plan_title="Test Diet Plan",
            plan_summary="A test diet plan for unit testing",
            foods_to_eat=json.dumps(["Vegetables", "Lean protein", "Whole grains"]),
            foods_to_avoid=json.dumps(["Processed sugar", "Fried foods"]),
            weekly_meal_plan=json.dumps({
                "Monday": {"breakfast": "Oatmeal", "lunch": "Salad", "dinner": "Grilled chicken"},
            }),
            nutritional_guidelines=json.dumps({"calories": 2000, "protein": "80g"}),
            allergy_notes=json.dumps(["Avoid peanuts due to severe allergy"]),
            generated_at=datetime.utcnow(),
            is_active=True,
        )
        db_session.add(plan)
        db_session.commit()

        response = authenticated_client.get("/diet-plan/history")
        assert response.status_code == 200
        assert "Test Diet Plan" in response.text


class TestDietPlanGeneration:
    """Tests for AI diet plan generation."""

    @patch("app.routers.diet_plans.create_diet_plan")
    def test_generate_diet_plan_success(self, mock_create, authenticated_client, db_session, test_user):
        """Generate should succeed with valid document selection."""
        # Create a completed document
        doc_id = uuid.uuid4()
        doc = Document(
            id=doc_id,
            user_id=test_user.id,
            document_type="lab_report",
            original_filename="lab_results.pdf",
            blob_name="lab-blob.pdf",
            blob_url="https://storage.blob.core.windows.net/lab-blob.pdf",
            ocr_status="completed",
            ocr_content="Blood sugar: 95 mg/dL, Cholesterol: 180 mg/dL",
            uploaded_at=datetime.utcnow(),
        )
        db_session.add(doc)
        db_session.commit()

        # Mock the diet plan creation service
        mock_plan = MagicMock()
        mock_plan.id = uuid.uuid4()
        mock_plan.plan_title = "Generated Diet Plan"
        mock_create.return_value = mock_plan

        response = authenticated_client.post(
            "/diet-plan/generate",
            data={
                "document_ids": [str(doc_id)],
                "additional_notes": "I prefer vegetarian meals",
            },
            follow_redirects=False,
        )
        assert response.status_code in [200, 302]

    def test_generate_without_documents(self, authenticated_client):
        """Generate should fail without selecting any documents."""
        response = authenticated_client.post(
            "/diet-plan/generate",
            data={
                "document_ids": [],
                "additional_notes": "",
            },
            follow_redirects=False,
        )
        # Should redirect back with error or return validation error
        assert response.status_code in [200, 302, 422]


class TestDietPlanDetail:
    """Tests for viewing individual diet plan details."""

    def test_view_own_plan(self, authenticated_client, db_session, test_user):
        """Users should be able to view their own diet plans."""
        plan_id = uuid.uuid4()
        plan = DietPlan(
            id=plan_id,
            user_id=test_user.id,
            document_ids=json.dumps([str(uuid.uuid4())]),
            plan_title="My Diet Plan",
            plan_summary="Personalized plan for the test user",
            foods_to_eat=json.dumps(["Fruits", "Vegetables"]),
            foods_to_avoid=json.dumps(["Allergens"]),
            weekly_meal_plan=json.dumps({}),
            nutritional_guidelines=json.dumps({}),
            allergy_notes=json.dumps([]),
            generated_at=datetime.utcnow(),
            is_active=True,
        )
        db_session.add(plan)
        db_session.commit()

        response = authenticated_client.get(f"/diet-plan/{plan_id}")
        assert response.status_code == 200
        assert "My Diet Plan" in response.text

    def test_view_nonexistent_plan(self, authenticated_client):
        """Viewing a non-existent plan should return 404."""
        fake_id = uuid.uuid4()
        response = authenticated_client.get(f"/diet-plan/{fake_id}")
        assert response.status_code == 404

    def test_view_other_users_plan(self, authenticated_client, db_session):
        """Users should not be able to view other users' diet plans."""
        other_user_id = uuid.uuid4()
        plan_id = uuid.uuid4()
        plan = DietPlan(
            id=plan_id,
            user_id=other_user_id,
            document_ids=json.dumps([]),
            plan_title="Not My Plan",
            plan_summary="Someone else's plan",
            foods_to_eat=json.dumps([]),
            foods_to_avoid=json.dumps([]),
            weekly_meal_plan=json.dumps({}),
            nutritional_guidelines=json.dumps({}),
            allergy_notes=json.dumps([]),
            generated_at=datetime.utcnow(),
            is_active=True,
        )
        db_session.add(plan)
        db_session.commit()

        response = authenticated_client.get(f"/diet-plan/{plan_id}")
        assert response.status_code in [403, 404]


class TestAllergyAwareness:
    """Tests for allergy integration in diet planning."""

    def test_allergies_shown_on_generate_page(self, authenticated_client, db_session, test_user):
        """Generate page should display user's food allergies."""
        allergy = FoodAllergy(
            id=uuid.uuid4(),
            user_id=test_user.id,
            allergen_name="Peanuts",
            severity="severe",
            notes="Anaphylaxis risk",
        )
        db_session.add(allergy)
        db_session.commit()

        response = authenticated_client.get("/diet-plan")
        assert response.status_code == 200
        assert "Peanuts" in response.text or "peanuts" in response.text
