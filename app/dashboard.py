"""Main dashboard and navigation components"""

from datetime import datetime, date, timedelta

from nicegui import ui
from app.auth import AuthService
from app.services import AttendanceService, RequestService, TaskLogService
from app.models import RequestStatus


def create_stats_card(title: str, value: str, icon: str, color: str = "blue"):
    """Create a statistics card for the dashboard"""
    with ui.card().classes(
        f"p-6 bg-white shadow-lg rounded-xl hover:shadow-xl transition-shadow border-l-4 border-{color}-500"
    ):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("items-start"):
                ui.label(title).classes("text-sm text-gray-500 uppercase tracking-wider font-medium")
                ui.label(value).classes("text-3xl font-bold text-gray-800 mt-2")
            ui.icon(icon).classes(f"text-4xl text-{color}-500")


def create_quick_actions():
    """Create quick action buttons"""
    ui.label("Quick Actions").classes("text-xl font-bold mb-4 text-gray-800")

    actions = [
        {"label": "Check In", "icon": "login", "color": "green", "route": "/checkin"},
        {"label": "Log Task", "icon": "add_task", "color": "blue", "route": "/log-task"},
        {"label": "Submit Request", "icon": "send", "color": "orange", "route": "/submit-request"},
        {"label": "View Attendance", "icon": "schedule", "color": "purple", "route": "/attendance"},
    ]

    with ui.row().classes("gap-4 w-full flex-wrap"):
        for action in actions:
            with (
                ui.card()
                .classes(
                    f"p-4 cursor-pointer hover:shadow-lg transition-shadow border-l-4 border-{action['color']}-500 flex-1 min-w-40"
                )
                .on("click", lambda event, route=action["route"]: ui.navigate.to(route))
            ):
                with ui.column().classes("items-center text-center"):
                    ui.icon(action["icon"]).classes(f"text-3xl text-{action['color']}-500 mb-2")
                    ui.label(action["label"]).classes("font-semibold text-gray-700")


@ui.refreshable
def create_dashboard_stats():
    """Create dashboard statistics overview"""
    current_user = AuthService.get_current_user()
    if current_user is None:
        return

    # Get statistics
    today = date.today()
    week_start = today - timedelta(days=today.weekday())

    if current_user.id is None:
        return

    # Today's attendance
    today_attendance = AttendanceService.get_todays_attendance(current_user.id)

    # Week's attendance count
    week_attendance = AttendanceService.get_user_attendance_records(current_user.id, limit=100)
    week_count = sum(1 for record in week_attendance if record.check_in_date >= week_start)

    # Pending requests
    user_requests = RequestService.get_user_requests(current_user.id, limit=50)
    pending_requests = sum(1 for req in user_requests if req.status == RequestStatus.PENDING)

    # Today's tasks
    today_tasks = TaskLogService.get_user_task_logs(current_user.id, task_date=today, limit=100)

    ui.label("Overview").classes("text-xl font-bold mb-4 text-gray-800")

    with ui.row().classes("gap-4 w-full flex-wrap mb-6"):
        # Check-in status
        if today_attendance:
            if today_attendance.check_out_time:
                create_stats_card("Today's Status", "Checked Out", "check_circle", "green")
            else:
                create_stats_card("Today's Status", "Checked In", "schedule", "blue")
        else:
            create_stats_card("Today's Status", "Not Checked In", "schedule", "gray")

        # Week's attendance
        create_stats_card("This Week", f"{week_count} Days", "calendar_today", "purple")

        # Pending requests
        create_stats_card("Pending Requests", str(pending_requests), "pending", "orange")

        # Today's tasks
        create_stats_card("Today's Tasks", str(len(today_tasks)), "task_alt", "blue")


@ui.refreshable
def create_recent_activity():
    """Create recent activity feed"""
    current_user = AuthService.get_current_user()
    if current_user is None:
        return

    ui.label("Recent Activity").classes("text-xl font-bold mb-4 text-gray-800")

    if current_user.id is None:
        ui.label("User ID not found").classes("text-red-500")
        return

    # Get recent data
    recent_attendance = AttendanceService.get_user_attendance_records(current_user.id, limit=3)
    recent_requests = RequestService.get_user_requests(current_user.id, limit=3)
    recent_tasks = TaskLogService.get_user_task_logs(current_user.id, limit=3)

    # Combine and sort by date
    activities = []

    for record in recent_attendance:
        activities.append(
            {
                "date": record.created_at,
                "type": "attendance",
                "title": "Attendance Record",
                "description": f"Checked in at {record.check_in_time.strftime('%I:%M %p')} on {record.check_in_date.strftime('%b %d')}",
                "icon": "schedule",
                "color": "blue",
            }
        )

    for request in recent_requests:
        status_colors = {
            RequestStatus.PENDING: "orange",
            RequestStatus.APPROVED: "green",
            RequestStatus.REJECTED: "red",
        }
        activities.append(
            {
                "date": request.created_at,
                "type": "request",
                "title": request.title,
                "description": f"{request.request_type.value.replace('_', ' ').title()} - {request.status.value.title()}",
                "icon": "send",
                "color": status_colors.get(request.status, "gray"),
            }
        )

    for task in recent_tasks:
        activities.append(
            {
                "date": task.created_at,
                "type": "task",
                "title": task.title,
                "description": f"{task.status.replace('_', ' ').title()} - {task.task_date.strftime('%b %d')}",
                "icon": "task_alt",
                "color": "blue",
            }
        )

    # Sort by date (newest first)
    activities.sort(key=lambda x: x["date"], reverse=True)

    if not activities:
        with ui.card().classes("p-6 text-center"):
            ui.label("No recent activity").classes("text-gray-500")
            ui.label("Start by checking in or logging a task").classes("text-sm text-gray-400 mt-2")
        return

    with ui.column().classes("gap-3 w-full"):
        for activity in activities[:5]:  # Show only 5 most recent
            with ui.card().classes("p-4 hover:shadow-md transition-shadow"):
                with ui.row().classes("w-full items-start gap-3"):
                    ui.icon(activity["icon"]).classes(f"text-2xl text-{activity['color']}-500 mt-1")

                    with ui.column().classes("flex-1"):
                        ui.label(activity["title"]).classes("font-semibold text-gray-800")
                        ui.label(activity["description"]).classes("text-sm text-gray-600")
                        ui.label(activity["date"].strftime("%b %d, %I:%M %p")).classes("text-xs text-gray-500 mt-1")


def create_mobile_navigation():
    """Create mobile-friendly bottom navigation"""
    current_user = AuthService.get_current_user()
    if current_user is None:
        return

    nav_items = [
        {"icon": "dashboard", "label": "Dashboard", "route": "/dashboard"},
        {"icon": "schedule", "label": "Attendance", "route": "/attendance"},
        {"icon": "task_alt", "label": "Tasks", "route": "/tasks"},
        {"icon": "send", "label": "Requests", "route": "/requests"},
    ]

    with ui.row().classes("fixed bottom-0 left-0 right-0 bg-white shadow-lg border-t border-gray-200 p-2 z-50"):
        for item in nav_items:
            with (
                ui.column()
                .classes("flex-1 items-center py-2 cursor-pointer hover:bg-gray-50 rounded")
                .on("click", lambda event, route=item["route"]: ui.navigate.to(route))
            ):
                ui.icon(item["icon"]).classes("text-xl text-gray-600")
                ui.label(item["label"]).classes("text-xs text-gray-600 mt-1")


def create_header():
    """Create header with user info and logout"""
    current_user = AuthService.get_current_user()
    if current_user is None:
        return

    with ui.row().classes("w-full items-center justify-between p-4 bg-white shadow-sm border-b border-gray-200"):
        # Welcome message
        with ui.column():
            ui.label(f"Welcome back, {current_user.first_name}!").classes("text-xl font-bold text-gray-800")
            ui.label(datetime.now().strftime("%A, %B %d, %Y")).classes("text-sm text-gray-500")

        # User menu
        with ui.button(icon="account_circle").props("flat round"):
            with ui.menu():
                with ui.column().classes("p-4 min-w-48"):
                    ui.label(f"{current_user.first_name} {current_user.last_name}").classes("font-semibold")
                    ui.label(current_user.employee_id).classes("text-sm text-gray-600")
                    ui.label(current_user.department or "No Department").classes("text-xs text-gray-500")

                    ui.separator().classes("my-2")

                    def logout():
                        AuthService.logout_user()
                        ui.notify("Logged out successfully", type="positive")
                        ui.navigate.to("/login")

                    ui.button("Logout", icon="logout", on_click=logout).props("flat").classes("w-full")


def create():
    """Create dashboard and main navigation pages"""

    @ui.page("/dashboard")
    def dashboard_page():
        if not AuthService.is_authenticated():
            ui.navigate.to("/login")
            return

        # Add responsive CSS for mobile
        ui.add_head_html("""
        <style>
            @media (max-width: 768px) {
                .q-page-container { padding-bottom: 80px !important; }
            }
        </style>
        """)

        with ui.column().classes("min-h-screen bg-gray-50"):
            create_header()

            with ui.column().classes("flex-1 p-4 max-w-6xl mx-auto w-full"):
                # Stats overview
                create_dashboard_stats()

                ui.separator().classes("my-6")

                # Quick actions
                create_quick_actions()

                ui.separator().classes("my-6")

                # Recent activity
                create_recent_activity()

                # Add some bottom padding for mobile navigation
                ui.space().classes("h-20 md:h-0")

            # Mobile navigation (only on mobile)
            ui.add_head_html("""
            <style>
                @media (min-width: 769px) {
                    .mobile-nav { display: none !important; }
                }
            </style>
            """)

            with ui.row().classes(
                "mobile-nav fixed bottom-0 left-0 right-0 bg-white shadow-lg border-t border-gray-200 p-2 z-50"
            ):
                nav_items = [
                    {"icon": "dashboard", "label": "Home", "route": "/dashboard"},
                    {"icon": "schedule", "label": "Attendance", "route": "/attendance"},
                    {"icon": "task_alt", "label": "Tasks", "route": "/tasks"},
                    {"icon": "send", "label": "Requests", "route": "/requests"},
                ]

                for item in nav_items:
                    with (
                        ui.column()
                        .classes("flex-1 items-center py-2 cursor-pointer hover:bg-gray-50 rounded")
                        .on("click", lambda event, route=item["route"]: ui.navigate.to(route))
                    ):
                        ui.icon(item["icon"]).classes("text-xl text-gray-600")
                        ui.label(item["label"]).classes("text-xs text-gray-600 mt-1")
