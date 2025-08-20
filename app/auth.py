"""User authentication and session management"""

from typing import Optional
from nicegui import app, ui
from app.services import UserService
from app.models import User, UserCreate


class AuthService:
    @staticmethod
    def get_current_user() -> Optional[User]:
        """Get currently logged in user from session storage"""
        user_id = app.storage.user.get("user_id")
        if user_id is None:
            return None
        return UserService.get_user_by_id(user_id)

    @staticmethod
    def login_user(user: User) -> None:
        """Set user as current logged in user"""
        app.storage.user["user_id"] = user.id
        app.storage.user["employee_id"] = user.employee_id
        app.storage.user["full_name"] = f"{user.first_name} {user.last_name}"

    @staticmethod
    def logout_user() -> None:
        """Clear user session"""
        app.storage.user.clear()

    @staticmethod
    def is_authenticated() -> bool:
        """Check if user is authenticated"""
        return app.storage.user.get("user_id") is not None


def create_user_selector():
    """Create a user selection component for authentication simulation"""
    with ui.card().classes("w-full max-w-md mx-auto p-6 shadow-lg"):
        ui.label("Select User").classes("text-xl font-bold mb-4")
        ui.label("Choose your employee profile to continue").classes("text-gray-600 mb-4")

        users = UserService.get_all_users()

        if not users:
            # Create default users if none exist
            default_users = [
                UserCreate(
                    employee_id="EMP001",
                    email="john.doe@company.com",
                    first_name="John",
                    last_name="Doe",
                    department="Engineering",
                    position="Software Developer",
                ),
                UserCreate(
                    employee_id="EMP002",
                    email="jane.smith@company.com",
                    first_name="Jane",
                    last_name="Smith",
                    department="Marketing",
                    position="Marketing Manager",
                ),
                UserCreate(
                    employee_id="EMP003",
                    email="mike.johnson@company.com",
                    first_name="Mike",
                    last_name="Johnson",
                    department="Sales",
                    position="Sales Representative",
                ),
            ]

            for user_data in default_users:
                UserService.create_user(user_data)

            users = UserService.get_all_users()

        def login_as_user(user: User):
            AuthService.login_user(user)
            ui.notify(f"Logged in as {user.first_name} {user.last_name}", type="positive")
            ui.navigate.to("/dashboard")

        for user in users:
            with (
                ui.card()
                .classes("w-full p-4 mb-2 cursor-pointer hover:bg-gray-50")
                .on("click", lambda event, u=user: login_as_user(u))
            ):
                ui.label(f"{user.first_name} {user.last_name}").classes("font-semibold")
                ui.label(f"{user.employee_id} • {user.position}").classes("text-sm text-gray-600")
                ui.label(user.department or "No Department").classes("text-xs text-gray-500")


def require_auth():
    """Decorator to require authentication for pages"""

    def decorator(func):
        def wrapper(*args, **kwargs):
            if not AuthService.is_authenticated():
                ui.navigate.to("/login")
                return
            return func(*args, **kwargs)

        return wrapper

    return decorator
