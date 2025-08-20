from app.database import create_tables
from nicegui import ui

# Import all modules
import app.attendance
import app.requests
import app.tasks
import app.dashboard
from app.auth import create_user_selector, AuthService


def startup() -> None:
    # Apply modern theme colors
    ui.colors(
        primary="#2563eb",  # Professional blue
        secondary="#64748b",  # Subtle gray
        accent="#10b981",  # Success green
        positive="#10b981",
        negative="#ef4444",  # Error red
        warning="#f59e0b",  # Warning amber
        info="#3b82f6",  # Info blue
    )

    # Create database tables
    create_tables()

    # Register all module routes
    app.attendance.create()
    app.requests.create()
    app.tasks.create()
    app.dashboard.create()

    @ui.page("/")
    def index():
        # Redirect to dashboard if authenticated, otherwise to login
        if AuthService.is_authenticated():
            ui.navigate.to("/dashboard")
        else:
            ui.navigate.to("/login")

    @ui.page("/login")
    def login_page():
        # Redirect to dashboard if already authenticated
        if AuthService.is_authenticated():
            ui.navigate.to("/dashboard")
            return

        # Mobile-first responsive layout
        with ui.column().classes(
            "min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4"
        ):
            # App branding
            with ui.column().classes("text-center mb-8"):
                ui.icon("business").classes("text-6xl text-blue-600 mb-2")
                ui.label("Employee Portal").classes("text-3xl font-bold text-gray-800")
                ui.label("Attendance & Task Management").classes("text-lg text-gray-600")

            # User selection
            create_user_selector()
