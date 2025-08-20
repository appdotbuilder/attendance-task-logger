"""Task logging and management components"""

import logging
from datetime import date, datetime
from decimal import Decimal

from nicegui import ui
from nicegui.events import UploadEventArguments

from app.auth import AuthService
from app.services import TaskLogService, FileService
from app.models import TaskLogCreate, TaskLogUpdate, FileType, TaskLog

logger = logging.getLogger(__name__)


def create_task_form():
    """Create responsive task logging form"""
    current_user = AuthService.get_current_user()
    if current_user is None:
        ui.notify("Please log in first", type="negative")
        return

    with ui.card().classes("w-full max-w-2xl mx-auto p-6 shadow-lg"):
        ui.label("Log Task").classes("text-2xl font-bold mb-6 text-center")

        # Task date
        ui.label("Task Date").classes("text-sm font-medium text-gray-700 mb-2")
        task_date_input = ui.date(value=date.today().isoformat()).classes("w-full mb-4")

        # Title
        ui.label("Task Title").classes("text-sm font-medium text-gray-700 mb-2")
        title_input = ui.input(label="Task title", placeholder="Brief description of the task").classes("w-full mb-4")

        # Description
        ui.label("Description").classes("text-sm font-medium text-gray-700 mb-2")
        description_input = (
            ui.textarea(
                label="Detailed task description",
                placeholder="Provide detailed information about what was accomplished",
            )
            .classes("w-full mb-4")
            .props("rows=4")
        )

        # Duration, Status, Priority row
        ui.label("Task Details").classes("text-sm font-medium text-gray-700 mb-2")
        with ui.row().classes("w-full gap-4 mb-4"):
            duration_input = ui.number(label="Hours Spent", value=0.0, step=0.25, precision=2).classes("flex-1")

            status_select = ui.select(
                options=["in_progress", "completed", "on_hold", "cancelled"], value="in_progress", label="Status"
            ).classes("flex-1")

            priority_select = ui.select(
                options=["low", "medium", "high", "urgent"], value="medium", label="Priority"
            ).classes("flex-1")

        # Category
        ui.label("Category (Optional)").classes("text-sm font-medium text-gray-700 mb-2")
        category_input = ui.input(
            label="Task category", placeholder="e.g., Development, Testing, Documentation"
        ).classes("w-full mb-4")

        # Tags
        ui.label("Tags (Optional)").classes("text-sm font-medium text-gray-700 mb-2")
        tags_input = ui.input(label="Tags (comma-separated)", placeholder="e.g., frontend, bug-fix, urgent").classes(
            "w-full mb-4"
        )

        # Attachments
        ui.label("Attachments").classes("text-sm font-medium text-gray-700 mb-2")
        ui.label("Upload relevant files, screenshots, or documents").classes("text-xs text-gray-500 mb-2")

        uploaded_files = []

        def handle_file_upload(e: UploadEventArguments):
            try:
                if current_user.id is None:
                    ui.notify("User ID not found", type="negative")
                    return
                file_record = FileService.save_upload_file(e, current_user.id, FileType.ATTACHMENT)
                if file_record is not None:
                    uploaded_files.append(file_record.id)
                    ui.notify(f'File "{e.name}" uploaded successfully', type="positive")
                    refresh_file_list()
                else:
                    ui.notify("Failed to upload file", type="negative")
            except Exception as ex:
                logger.error(f"File upload error for user {current_user.id}: {str(ex)}")
                ui.notify(f"Upload error: {str(ex)}", type="negative")

        ui.upload(label="Upload attachments", on_upload=handle_file_upload, multiple=True).classes("w-full mb-2")

        # File list display
        file_list_container = ui.column().classes("mb-4")

        @ui.refreshable
        def refresh_file_list():
            with file_list_container:
                file_list_container.clear()
                if uploaded_files:
                    ui.label(f"{len(uploaded_files)} file(s) attached").classes("text-sm text-green-600")
                    for i, file_id in enumerate(uploaded_files):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("attachment").classes("text-gray-400")
                            ui.label(f"File {i + 1}").classes("text-sm")
                            ui.button(icon="delete", on_click=lambda event, idx=i: remove_file(idx)).props(
                                "size=sm flat color=negative"
                            )

        def remove_file(index: int):
            if 0 <= index < len(uploaded_files):
                uploaded_files.pop(index)
                refresh_file_list()
                ui.notify("File removed", type="info")

        refresh_file_list()

        # Submit button
        async def submit_task():
            # Validation
            if not title_input.value:
                ui.notify("Please enter a task title", type="negative")
                return

            if not description_input.value:
                ui.notify("Please provide a task description", type="negative")
                return

            if not task_date_input.value:
                ui.notify("Please select a task date", type="negative")
                return

            try:
                # Convert date string to date object
                task_date_obj = datetime.fromisoformat(task_date_input.value).date()

                # Parse tags
                tags_list = []
                if tags_input.value:
                    tags_list = [tag.strip() for tag in tags_input.value.split(",") if tag.strip()]

                # Convert duration to Decimal
                duration_decimal = None
                if duration_input.value is not None and duration_input.value > 0:
                    duration_decimal = Decimal(str(duration_input.value))

                task_data = TaskLogCreate(
                    task_date=task_date_obj,
                    title=title_input.value,
                    description=description_input.value,
                    duration_hours=duration_decimal,
                    status=status_select.value or "in_progress",
                    priority=priority_select.value or "medium",
                    category=category_input.value or None,
                    attachment_ids=uploaded_files,
                    tags=tags_list,
                )

                if current_user.id is None:
                    ui.notify("User ID not found", type="negative")
                    return

                new_task = TaskLogService.create_task_log(current_user.id, task_data)

                # Show success dialog
                with ui.dialog() as success_dialog:
                    with ui.card().classes("p-6"):
                        ui.label("✅ Task Logged Successfully!").classes("text-xl font-bold text-green-600 mb-4")
                        ui.label(f"Task: {new_task.title}").classes("text-gray-700 font-semibold")
                        ui.label(f"Date: {task_date_obj}").classes("text-gray-600")
                        ui.label(f"Status: {new_task.status.title()}").classes("text-gray-600")
                        if duration_decimal:
                            ui.label(f"Duration: {duration_decimal} hours").classes("text-gray-600")

                        ui.label("Your task has been logged successfully.").classes("text-sm text-gray-500 mt-4")

                        with ui.row().classes("mt-4 gap-2"):
                            ui.button(
                                "View Tasks", on_click=lambda: (success_dialog.close(), ui.navigate.to("/tasks"))
                            ).classes("bg-blue-500 text-white")
                            ui.button("Log Another", on_click=lambda: success_dialog.close()).props("outline")

                await success_dialog

                # Clear form after successful submission
                title_input.value = ""
                description_input.value = ""
                category_input.value = ""
                tags_input.value = ""
                duration_input.value = 0.0
                uploaded_files.clear()
                refresh_file_list()

            except Exception as e:
                logger.error(f"Failed to log task: {str(e)}")
                ui.notify(f"Failed to log task: {str(e)}", type="negative")

        with ui.row().classes("gap-2"):
            ui.button(
                "Save as Draft",
                icon="save",
                on_click=lambda: ui.notify("Draft functionality would be implemented", type="info"),
            ).props("outline").classes("flex-1")

            ui.button("Log Task", icon="add_task", on_click=submit_task).classes(
                "flex-1 bg-blue-500 hover:bg-blue-600 text-white py-3 text-lg font-semibold"
            )


@ui.refreshable
def show_task_history():
    """Show user's task history"""
    current_user = AuthService.get_current_user()
    if current_user is None:
        ui.label("Please log in first").classes("text-red-500")
        return

    # Filter controls
    with ui.row().classes("w-full items-center gap-4 mb-6"):
        ui.label("My Tasks").classes("text-2xl font-bold")

        # Date filter
        filter_date = ui.date()

        # Clear filter button
        ui.button("All Tasks", icon="clear", on_click=lambda: filter_date.set_value(None)).props("outline")

    # Get filtered tasks
    filter_date_obj = None
    if filter_date.value:
        try:
            filter_date_obj = datetime.fromisoformat(filter_date.value).date()
        except (ValueError, TypeError):
            logger.warning(f"Invalid date filter value: {filter_date.value}")
            pass

    if current_user.id is None:
        ui.label("User ID not found").classes("text-red-500")
        return

    tasks = TaskLogService.get_user_task_logs(current_user.id, task_date=filter_date_obj, limit=50)

    if not tasks:
        with ui.card().classes("p-6 text-center"):
            if filter_date_obj:
                ui.label(f"No tasks found for {filter_date_obj}").classes("text-gray-500 text-lg")
            else:
                ui.label("No tasks logged yet").classes("text-gray-500 text-lg")
                ui.label("Start logging your daily activities to track your work").classes("text-gray-400 text-sm mt-2")
            ui.button("Log Task", on_click=lambda: ui.navigate.to("/log-task")).classes("mt-4 bg-blue-500 text-white")
        return

    # Group tasks by date
    from collections import defaultdict

    tasks_by_date = defaultdict(list)
    for task in tasks:
        tasks_by_date[task.task_date].append(task)

    # Display tasks grouped by date
    with ui.column().classes("gap-6 w-full"):
        for task_date, date_tasks in tasks_by_date.items():
            # Date header
            with ui.card().classes("w-full p-4 bg-blue-50"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label(task_date.strftime("%A, %B %d, %Y")).classes("text-lg font-bold text-blue-800")
                    ui.label(f"{len(date_tasks)} task{'s' if len(date_tasks) != 1 else ''}").classes(
                        "text-sm text-blue-600"
                    )

            # Tasks for this date
            with ui.column().classes("gap-3 ml-4"):
                for task in date_tasks:
                    create_task_card(task)


def create_task_card(task: TaskLog):
    """Create a card for displaying a single task"""
    # Priority colors
    priority_colors = {
        "low": "bg-gray-100 text-gray-800",
        "medium": "bg-blue-100 text-blue-800",
        "high": "bg-orange-100 text-orange-800",
        "urgent": "bg-red-100 text-red-800",
    }

    # Status colors
    status_colors = {
        "in_progress": "bg-yellow-100 text-yellow-800",
        "completed": "bg-green-100 text-green-800",
        "on_hold": "bg-gray-100 text-gray-800",
        "cancelled": "bg-red-100 text-red-800",
    }

    with ui.card().classes("w-full p-5 hover:shadow-md transition-shadow border-l-4 border-blue-400"):
        # Header row
        with ui.row().classes("w-full items-start justify-between mb-3"):
            with ui.column().classes("items-start flex-1"):
                ui.label(task.title).classes("font-semibold text-lg text-gray-800")
                if task.category:
                    ui.label(task.category).classes("text-sm text-blue-600 font-medium")

            with ui.row().classes("gap-2"):
                # Priority badge
                ui.label(task.priority.title()).classes(
                    f"px-2 py-1 rounded text-xs font-medium {priority_colors.get(task.priority, 'bg-gray-100 text-gray-800')}"
                )

                # Status badge
                ui.label(task.status.replace("_", " ").title()).classes(
                    f"px-2 py-1 rounded text-xs font-medium {status_colors.get(task.status, 'bg-gray-100 text-gray-800')}"
                )

        # Description
        ui.label(task.description).classes("text-gray-700 mb-3 leading-relaxed")

        # Duration and tags row
        with ui.row().classes("w-full items-center justify-between mb-3"):
            if task.duration_hours:
                with ui.row().classes("items-center gap-1"):
                    ui.icon("schedule").classes("text-gray-500 text-sm")
                    ui.label(f"{task.duration_hours} hours").classes("text-sm text-gray-600 font-medium")
            else:
                ui.label("")  # Empty space

            # Tags
            if task.tags:
                with ui.row().classes("gap-1 flex-wrap"):
                    for tag in task.tags:
                        ui.label(f"#{tag}").classes("text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded")

        # Attachments
        if task.attachments:
            with ui.row().classes("items-center gap-2 mb-3"):
                ui.icon("attachment").classes("text-gray-500 text-sm")
                ui.label(f"{len(task.attachments)} attachment{'s' if len(task.attachments) != 1 else ''}").classes(
                    "text-sm text-gray-600"
                )

        # Footer with edit/delete actions and timestamp
        with ui.row().classes("w-full items-center justify-between pt-3 border-t border-gray-200"):
            ui.label(f"Logged: {task.created_at.strftime('%I:%M %p')}").classes("text-xs text-gray-500")

            with ui.row().classes("gap-2"):
                ui.button("Edit", icon="edit", on_click=lambda event, t=task: edit_task(t)).props("size=sm outline")

                ui.button("Delete", icon="delete", on_click=lambda event, t=task: delete_task(t)).props(
                    "size=sm flat color=negative"
                )


async def edit_task(task: TaskLog):
    """Edit task dialog"""
    with ui.dialog() as edit_dialog, ui.card().classes("p-6 w-96"):
        ui.label(f"Edit Task: {task.title}").classes("text-lg font-bold mb-4")

        title_input = ui.input(label="Title", value=task.title).classes("w-full mb-3")
        description_input = (
            ui.textarea(label="Description", value=task.description).classes("w-full mb-3").props("rows=3")
        )

        with ui.row().classes("w-full gap-2 mb-3"):
            duration_input = ui.number(
                label="Hours", value=float(task.duration_hours) if task.duration_hours else 0.0, step=0.25, precision=2
            ).classes("flex-1")
            status_select = ui.select(
                options=["in_progress", "completed", "on_hold", "cancelled"], value=task.status, label="Status"
            ).classes("flex-1")

        priority_select = ui.select(
            options=["low", "medium", "high", "urgent"], value=task.priority, label="Priority"
        ).classes("w-full mb-4")

        with ui.row().classes("gap-2"):
            ui.button("Cancel", on_click=edit_dialog.close).props("outline")

            def save_changes():
                try:
                    duration_decimal = None
                    if duration_input.value is not None and duration_input.value > 0:
                        duration_decimal = Decimal(str(duration_input.value))

                    update_data = TaskLogUpdate(
                        title=title_input.value,
                        description=description_input.value,
                        duration_hours=duration_decimal,
                        status=status_select.value,
                        priority=priority_select.value,
                    )

                    if task.id is None:
                        ui.notify("Task ID not found", type="negative")
                        return

                    updated_task = TaskLogService.update_task_log(task.id, update_data)
                    if updated_task:
                        ui.notify("Task updated successfully", type="positive")
                        show_task_history.refresh()
                        edit_dialog.close()
                    else:
                        ui.notify("Failed to update task", type="negative")

                except Exception as e:
                    logger.error(f"Error updating task: {str(e)}")
                    ui.notify(f"Error updating task: {str(e)}", type="negative")

            ui.button("Save", on_click=save_changes).classes("bg-blue-500 text-white")

    await edit_dialog


async def delete_task(task: TaskLog):
    """Delete task confirmation dialog"""
    with ui.dialog() as delete_dialog, ui.card().classes("p-6"):
        ui.label("Delete Task").classes("text-lg font-bold text-red-600 mb-4")
        ui.label(f'Are you sure you want to delete "{task.title}"?').classes("mb-4")
        ui.label("This action cannot be undone.").classes("text-sm text-gray-500 mb-4")

        with ui.row().classes("gap-2"):
            ui.button("Cancel", on_click=delete_dialog.close).props("outline")

            def confirm_delete():
                try:
                    if task.id is None:
                        ui.notify("Task ID not found", type="negative")
                        return

                    if TaskLogService.delete_task_log(task.id):
                        ui.notify("Task deleted successfully", type="positive")
                        show_task_history.refresh()
                        delete_dialog.close()
                    else:
                        ui.notify("Failed to delete task", type="negative")
                except Exception as e:
                    logger.error(f"Error deleting task {task.id}: {str(e)}")
                    ui.notify(f"Error deleting task: {str(e)}", type="negative")

            ui.button("Delete", on_click=confirm_delete).classes("bg-red-500 text-white")

    await delete_dialog


def create():
    """Create task management pages"""

    @ui.page("/log-task")
    def log_task_page():
        if not AuthService.is_authenticated():
            ui.navigate.to("/login")
            return

        with ui.column().classes("min-h-screen bg-gray-50 p-4"):
            # Navigation header
            with ui.row().classes("w-full max-w-2xl mx-auto items-center justify-between mb-6"):
                ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/tasks")).props("flat")
                ui.label("Log Task").classes("text-xl font-bold")
                ui.button("View Tasks", on_click=lambda: ui.navigate.to("/tasks")).props("outline")

            create_task_form()

    @ui.page("/tasks")
    def tasks_page():
        if not AuthService.is_authenticated():
            ui.navigate.to("/login")
            return

        with ui.column().classes("min-h-screen bg-gray-50 p-4 max-w-4xl mx-auto"):
            # Navigation header
            with ui.row().classes("w-full items-center justify-between mb-6"):
                ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/dashboard")).props("flat")
                ui.label("Tasks").classes("text-2xl font-bold")
                ui.button("Log Task", icon="add", on_click=lambda: ui.navigate.to("/log-task")).classes(
                    "bg-blue-500 text-white"
                )

            show_task_history()
