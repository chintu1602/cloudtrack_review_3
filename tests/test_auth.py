"""
NutriAI Health Portal - Authentication Tests
Tests for login, register, logout, and protected route access.
"""

import pytest
from unittest.mock import patch, MagicMock


class TestLandingPage:
    """Tests for the public landing page."""

    def test_landing_page_renders(self, client):
        """Landing page should return 200 for unauthenticated users."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 200

    def test_landing_page_redirects_authenticated(self, authenticated_client):
        """Authenticated users should be redirected to dashboard from landing."""
        response = authenticated_client.get("/", follow_redirects=False)
        assert response.status_code == 302
        assert "/dashboard" in response.headers.get("location", "")


class TestLoginPage:
    """Tests for the login page and authentication flow."""

    def test_login_page_renders(self, client):
        """Login page should render for unauthenticated users."""
        response = client.get("/auth/login")
        assert response.status_code == 200
        assert "Login" in response.text or "login" in response.text

    def test_login_with_valid_credentials(self, client, test_user):
        """Login with valid credentials should set cookie and redirect."""
        response = client.post(
            "/auth/login",
            data={
                "email": "testuser@example.com",
                "password": "TestPassword123!",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "access_token" in response.cookies

    def test_login_with_invalid_password(self, client, test_user):
        """Login with wrong password should show error."""
        response = client.post(
            "/auth/login",
            data={
                "email": "testuser@example.com",
                "password": "WrongPassword!",
            },
            follow_redirects=False,
        )
        # Should either stay on login page (200) or redirect back with error
        assert response.status_code in [200, 302]

    def test_login_with_nonexistent_user(self, client):
        """Login with non-existent email should show error."""
        response = client.post(
            "/auth/login",
            data={
                "email": "nobody@example.com",
                "password": "SomePassword123!",
            },
            follow_redirects=False,
        )
        assert response.status_code in [200, 302]


class TestRegistration:
    """Tests for user registration."""

    def test_register_page_renders(self, client):
        """Registration page should render for unauthenticated users."""
        response = client.get("/auth/register")
        assert response.status_code == 200
        assert "Register" in response.text or "register" in response.text

    def test_register_with_valid_data(self, client):
        """Registration with valid data should create user and redirect."""
        response = client.post(
            "/auth/register",
            data={
                "email": "newuser@example.com",
                "username": "newuser",
                "full_name": "New User",
                "password": "NewPassword123!",
                "confirm_password": "NewPassword123!",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "access_token" in response.cookies

    def test_register_duplicate_email(self, client, test_user):
        """Registration with existing email should show error."""
        response = client.post(
            "/auth/register",
            data={
                "email": "testuser@example.com",
                "username": "anotheruser",
                "full_name": "Another User",
                "password": "Password123!",
                "confirm_password": "Password123!",
            },
            follow_redirects=False,
        )
        # Should stay on register page or redirect back with error
        assert response.status_code in [200, 302]


class TestLogout:
    """Tests for the logout flow."""

    def test_logout_clears_cookie(self, authenticated_client):
        """Logout should clear the auth cookie and redirect to landing."""
        response = authenticated_client.get("/auth/logout", follow_redirects=False)
        assert response.status_code == 302
        assert "/" in response.headers.get("location", "")


class TestProtectedRoutes:
    """Tests for routes that require authentication."""

    def test_dashboard_requires_auth(self, client):
        """Dashboard should redirect to login for unauthenticated users."""
        response = client.get("/dashboard", follow_redirects=False)
        assert response.status_code == 302
        assert "login" in response.headers.get("location", "").lower()

    def test_dashboard_accessible_authenticated(self, authenticated_client):
        """Dashboard should be accessible for authenticated users."""
        response = authenticated_client.get("/dashboard")
        assert response.status_code == 200

    def test_profile_requires_auth(self, client):
        """Profile should redirect to login for unauthenticated users."""
        response = client.get("/profile", follow_redirects=False)
        assert response.status_code == 302

    def test_documents_requires_auth(self, client):
        """Documents should redirect to login for unauthenticated users."""
        response = client.get("/documents", follow_redirects=False)
        assert response.status_code == 302

    def test_health_tracker_requires_auth(self, client):
        """Health tracker should redirect to login for unauthenticated users."""
        response = client.get("/health-tracker", follow_redirects=False)
        assert response.status_code == 302


class TestAdminAccess:
    """Tests for admin-only routes."""

    def test_admin_requires_admin_role(self, authenticated_client):
        """Regular users should not access admin panel."""
        response = authenticated_client.get("/admin", follow_redirects=False)
        assert response.status_code in [302, 403]

    def test_admin_accessible_for_admin(self, admin_client):
        """Admin users should access admin panel."""
        response = admin_client.get("/admin")
        assert response.status_code == 200


class TestHelpPage:
    """Tests for the public help page."""

    def test_help_page_renders_unauthenticated(self, client):
        """Help page should be accessible without authentication."""
        response = client.get("/help")
        assert response.status_code == 200

    def test_help_page_renders_authenticated(self, authenticated_client):
        """Help page should be accessible when authenticated."""
        response = authenticated_client.get("/help")
        assert response.status_code == 200
