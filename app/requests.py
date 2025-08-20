"""Request management components for leave, permission, and sick leave"""

import logging
from datetime import date, datetime

from nicegui import ui
from nicegui.events import UploadEventArguments

from app.auth import AuthService
from app.services import RequestService, FileService
from app.models import RequestCreate, RequestType, RequestStatus, FileType

logger = logging.getLogger(__name__)


def create_request_form():
    """Create responsive request submission form"""
    current_user = AuthService.get_current_user()
    if current_user is None:
        ui.notify("Please log in first", type="negative")
        return

    with ui.card().classes("w-full max-w-2xl mx-auto p-6 shadow-lg"):
        ui.label("Submit Request").classes("text-2xl font-bold mb-6 text-center")

        # Request type selection
        ui.label("Request Type").classes("text-sm font-medium text-gray-700 mb-2")
        request_type_select = ui.select(
            options={
                RequestType.PERMISSION: "Permission Request",
                RequestType.LEAVE: "Leave Request",
                RequestType.SICK_LEAVE: "Sick Leave Request",
            }
        ).classes("w-full mb-4")

        # Title
        ui.label("Title").classes("text-sm font-medium text-gray-700 mb-2")
        title_input = ui.input(label="Request title", placeholder="Brief description of your request").classes(
            "w-full mb-4"
        )

        # Date range
        ui.label("Date Range").classes("text-sm font-medium text-gray-700 mb-2")
        with ui.row().classes("w-full gap-4 mb-4"):
            start_date_input = ui.date(value=date.today().isoformat()).classes("flex-1")

            end_date_input = ui.date(value=date.today().isoformat()).classes("flex-1")

        # Reason
        ui.label("Reason").classes("text-sm font-medium text-gray-700 mb-2")
        reason_input = (
            ui.textarea(
                label="Detailed reason for request",
                placeholder="Please provide a detailed explanation for your request",
            )
            .classes("w-full mb-4")
            .props("rows=4")
        )

        # Document uploads
        ui.label("Supporting Documents").classes("text-sm font-medium text-gray-700 mb-2")
        ui.label("Upload relevant documents (medical certificates, letters, etc.)").classes(
            "text-xs text-gray-500 mb-2"
        )

        uploaded_files = []

        def handle_document_upload(e: UploadEventArguments):
            try:
                if current_user.id is None:
                    ui.notify("User ID not found", type="negative")
                    return
                file_record = FileService.save_upload_file(e, current_user.id, FileType.DOCUMENT)
                if file_record is not None:
                    uploaded_files.append(file_record.id)
                    ui.notify(f'Document "{e.name}" uploaded successfully', type="positive")
                    refresh_file_list()
                else:
                    ui.notify("Failed to upload document", type="negative")
            except Exception as ex:
                logger.error(f"Document upload error for user {current_user.id}: {str(ex)}")
                ui.notify(f"Upload error: {str(ex)}", type="negative")

        ui.upload(label="Upload documents", on_upload=handle_document_upload, multiple=True).classes(
            "w-full mb-2"
        ).props('accept=".pdf,.doc,.docx,.jpg,.jpeg,.png"')

        # File list display
        file_list_container = ui.column().classes("mb-4")

        @ui.refreshable
        def refresh_file_list():
            with file_list_container:
                file_list_container.clear()
                if uploaded_files:
                    ui.label(f"{len(uploaded_files)} document(s) uploaded").classes("text-sm text-green-600")
                    for i, file_id in enumerate(uploaded_files):
                        with ui.row().classes("items-center gap-2"):
                            ui.icon("description").classes("text-gray-400")
                            ui.label(f"Document {i + 1}").classes("text-sm")
                            ui.button(icon="delete", on_click=lambda event, idx=i: remove_file(idx)).props(
                                "size=sm flat color=negative"
                            )

        def remove_file(index: int):
            if 0 <= index < len(uploaded_files):
                uploaded_files.pop(index)
                refresh_file_list()
                ui.notify("Document removed", type="info")

        refresh_file_list()

        # Submit button
        async def submit_request():
            # Validation
            if not request_type_select.value:
                ui.notify("Please select a request type", type="negative")
                return

            if not title_input.value:
                ui.notify("Please enter a title", type="negative")
                return

            if not reason_input.value:
                ui.notify("Please provide a reason", type="negative")
                return

            if not start_date_input.value or not end_date_input.value:
                ui.notify("Please select both start and end dates", type="negative")
                return

            try:
                # Convert date strings to date objects
                start_date_obj = datetime.fromisoformat(start_date_input.value).date()
                end_date_obj = datetime.fromisoformat(end_date_input.value).date()

                if end_date_obj < start_date_obj:
                    ui.notify("End date must be after start date", type="negative")
                    return

                request_data = RequestCreate(
                    request_type=request_type_select.value,
                    title=title_input.value,
                    reason=reason_input.value,
                    start_date=start_date_obj,
                    end_date=end_date_obj,
                    supporting_document_ids=uploaded_files,
                )

                if current_user.id is None:
                    ui.notify("User ID not found", type="negative")
                    return

                new_request = RequestService.create_request(current_user.id, request_data)

                # Show success dialog
                with ui.dialog() as success_dialog:
                    with ui.card().classes("p-6"):
                        ui.label("✅ Request Submitted Successfully!").classes("text-xl font-bold text-green-600 mb-4")
                        ui.label(f"Request ID: #{new_request.id}").classes("text-gray-600")
                        ui.label(f"Type: {request_data.request_type.value.replace('_', ' ').title()}").classes(
                            "text-gray-600"
                        )
                        ui.label(f"Date Range: {start_date_obj} to {end_date_obj}").classes("text-gray-600")
                        ui.label("Status: Pending Approval").classes("text-orange-600 font-semibold")

                        ui.label("Your request has been submitted and is pending manager approval.").classes(
                            "text-sm text-gray-500 mt-4"
                        )

                        with ui.row().classes("mt-4 gap-2"):
                            ui.button(
                                "View Requests", on_click=lambda: (success_dialog.close(), ui.navigate.to("/requests"))
                            ).classes("bg-blue-500 text-white")
                            ui.button(
                                "Dashboard", on_click=lambda: (success_dialog.close(), ui.navigate.to("/dashboard"))
                            ).props("outline")

                await success_dialog

            except Exception as e:
                logger.error(f"Failed to submit request: {str(e)}")
                ui.notify(f"Failed to submit request: {str(e)}", type="negative")

        ui.button("Submit Request", icon="send", on_click=submit_request).classes(
            "w-full bg-blue-500 hover:bg-blue-600 text-white py-3 text-lg font-semibold"
        )


@ui.refreshable
def show_request_history():
    """Show user's request history"""
    current_user = AuthService.get_current_user()
    if current_user is None:
        ui.label("Please log in first").classes("text-red-500")
        return

    ui.label("My Requests").classes("text-2xl font-bold mb-6")

    if current_user.id is None:
        ui.label("User ID not found").classes("text-red-500")
        return

    requests = RequestService.get_user_requests(current_user.id, limit=20)

    if not requests:
        with ui.card().classes("p-6 text-center"):
            ui.label("No requests found").classes("text-gray-500 text-lg")
            ui.label("Submit your first request to get started").classes("text-gray-400 text-sm mt-2")
            ui.button("Submit Request", on_click=lambda: ui.navigate.to("/submit-request")).classes(
                "mt-4 bg-blue-500 text-white"
            )
        return

    # Create responsive cards for requests
    with ui.column().classes("gap-4 w-full"):
        for request in requests:
            # Status color mapping
            status_colors = {
                RequestStatus.PENDING: "bg-orange-100 text-orange-800",
                RequestStatus.APPROVED: "bg-green-100 text-green-800",
                RequestStatus.REJECTED: "bg-red-100 text-red-800",
            }

            # Request type icons
            type_icons = {
                RequestType.PERMISSION: "event_available",
                RequestType.LEAVE: "vacation_rental",
                RequestType.SICK_LEAVE: "medical_services",
            }

            with ui.card().classes("w-full p-6 hover:shadow-md transition-shadow"):
                # Header row
                with ui.row().classes("w-full items-start justify-between mb-4"):
                    with ui.column().classes("items-start flex-1"):
                        with ui.row().classes("items-center gap-2 mb-1"):
                            ui.icon(type_icons.get(request.request_type, "description")).classes("text-blue-600")
                            ui.label(request.title).classes("font-semibold text-lg")

                        ui.label(f"#{request.id} • {request.request_type.value.replace('_', ' ').title()}").classes(
                            "text-sm text-gray-500"
                        )

                    # Status badge
                    ui.label(request.status.value.title()).classes(
                        f"px-3 py-1 rounded-full text-xs font-medium {status_colors.get(request.status, 'bg-gray-100 text-gray-800')}"
                    )

                # Date range
                with ui.row().classes("items-center gap-4 mb-3"):
                    ui.label("📅").classes("text-lg")
                    ui.label(f"{request.start_date} to {request.end_date}").classes("font-mono text-gray-700")

                    # Calculate duration
                    duration = (request.end_date - request.start_date).days + 1
                    ui.label(f"({duration} day{'s' if duration != 1 else ''})").classes("text-sm text-gray-500")

                # Reason
                ui.label("Reason:").classes("text-sm font-medium text-gray-700")
                ui.label(request.reason).classes("text-sm text-gray-600 mb-3 leading-relaxed")

                # Manager notes (if any)
                if request.manager_notes:
                    ui.label("Manager Notes:").classes("text-sm font-medium text-gray-700")
                    ui.label(request.manager_notes).classes("text-sm text-gray-600 mb-3 leading-relaxed")

                # Supporting documents
                if request.supporting_documents:
                    ui.label(f"{len(request.supporting_documents)} supporting document(s) attached").classes(
                        "text-xs text-blue-600"
                    )

                # Footer with timestamps
                with ui.row().classes("w-full items-center justify-between mt-4 pt-3 border-t border-gray-200"):
                    ui.label(f"Submitted: {request.created_at.strftime('%b %d, %Y at %I:%M %p')}").classes(
                        "text-xs text-gray-500"
                    )

                    if request.reviewed_at:
                        ui.label(f"Reviewed: {request.reviewed_at.strftime('%b %d, %Y')}").classes(
                            "text-xs text-gray-500"
                        )


def create():
    """Create request management pages"""

    @ui.page("/submit-request")
    def submit_request_page():
        if not AuthService.is_authenticated():
            ui.navigate.to("/login")
            return

        with ui.column().classes("min-h-screen bg-gray-50 p-4"):
            # Navigation header
            with ui.row().classes("w-full max-w-2xl mx-auto items-center justify-between mb-6"):
                ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/requests")).props("flat")
                ui.label("Submit Request").classes("text-xl font-bold")
                ui.button("View Requests", on_click=lambda: ui.navigate.to("/requests")).props("outline")

            create_request_form()

    @ui.page("/requests")
    def requests_page():
        if not AuthService.is_authenticated():
            ui.navigate.to("/login")
            return

        with ui.column().classes("min-h-screen bg-gray-50 p-4 max-w-4xl mx-auto"):
            # Navigation header
            with ui.row().classes("w-full items-center justify-between mb-6"):
                ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/dashboard")).props("flat")
                ui.label("My Requests").classes("text-2xl font-bold")
                ui.button("New Request", icon="add", on_click=lambda: ui.navigate.to("/submit-request")).classes(
                    "bg-blue-500 text-white"
                )

            show_request_history()
