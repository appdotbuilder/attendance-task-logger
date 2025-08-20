"""Attendance management components"""

import logging
from datetime import datetime
from typing import Optional

from nicegui import ui
from nicegui.events import UploadEventArguments

from app.auth import AuthService
from app.services import AttendanceService, FileService
from app.models import AttendanceCheckIn, AttendanceCheckOut, FileType, AttendanceRecord

logger = logging.getLogger(__name__)


def create_check_in_form():
    """Create responsive check-in form"""
    current_user = AuthService.get_current_user()
    if current_user is None:
        ui.notify("Please log in first", type="negative")
        return

    # Check if already checked in today
    if current_user.id is None:
        ui.notify("User ID not found", type="negative")
        return
    today_attendance = AttendanceService.get_todays_attendance(current_user.id)
    if today_attendance is not None and today_attendance.check_out_time is None:
        ui.notify("You have already checked in today", type="warning")
        create_check_out_form(today_attendance)
        return

    with ui.card().classes("w-full max-w-md mx-auto p-6 shadow-lg"):
        ui.label("Check In").classes("text-2xl font-bold mb-6 text-center")
        ui.label(f"Welcome, {current_user.first_name}!").classes("text-lg text-gray-600 text-center mb-4")

        # Current date and time display
        now = datetime.now()
        ui.label(f"{now.strftime('%A, %B %d, %Y')}").classes("text-center text-gray-500 mb-2")
        ui.label(f"{now.strftime('%I:%M %p')}").classes("text-center text-2xl font-bold text-blue-600 mb-6")

        # Photo upload
        ui.label("Check-in Photo").classes("text-sm font-medium text-gray-700 mb-2")
        ui.upload(
            label="Take or upload photo", on_upload=lambda e: handle_photo_upload(e, "checkin"), multiple=False
        ).classes("w-full mb-4").props('accept="image/*" capture="environment"')

        # Location fields
        ui.label("Location (Optional)").classes("text-sm font-medium text-gray-700 mb-2")
        location_input = ui.input(
            label="Address or location description", placeholder="Office, Home, Client site, etc."
        ).classes("w-full mb-4")

        # Notes
        ui.label("Notes (Optional)").classes("text-sm font-medium text-gray-700 mb-2")
        notes_input = (
            ui.textarea(label="Any additional notes", placeholder="Optional check-in notes")
            .classes("w-full mb-6")
            .props("rows=2")
        )

        # Location detection button
        location_coords = {"lat": None, "lng": None}

        def detect_location():
            # In a real app, this would use browser geolocation API
            ui.notify("Location detection would be implemented with browser geolocation API", type="info")

        ui.button("Detect Current Location", icon="location_on", on_click=detect_location).classes("w-full mb-4").props(
            "outline"
        )

        # Store uploaded photo ID
        uploaded_photo_id: dict[str, Optional[int]] = {"value": None}

        def handle_photo_upload(e: UploadEventArguments, upload_type: str):
            try:
                if current_user.id is None:
                    ui.notify("User ID not found", type="negative")
                    return
                file_record = FileService.save_upload_file(e, current_user.id, FileType.PHOTO)
                if file_record is not None and file_record.id is not None:
                    uploaded_photo_id["value"] = file_record.id
                    ui.notify("Photo uploaded successfully", type="positive")
                else:
                    ui.notify("Failed to upload photo", type="negative")
            except Exception as ex:
                logger.error(f"Photo upload error for user {current_user.id}: {str(ex)}")
                ui.notify(f"Upload error: {str(ex)}", type="negative")

        # Check-in button
        async def perform_check_in():
            try:
                if current_user.id is None:
                    ui.notify("User ID not found", type="negative")
                    return

                check_in_data = AttendanceCheckIn(
                    check_in_photo_id=uploaded_photo_id["value"],
                    location_latitude=location_coords["lat"],
                    location_longitude=location_coords["lng"],
                    location_address=location_input.value or None,
                    notes=notes_input.value or None,
                )

                attendance = AttendanceService.check_in(current_user.id, check_in_data)
                ui.notify("Check-in successful!", type="positive")

                # Show success message and redirect
                with ui.dialog() as success_dialog:
                    with ui.card().classes("p-6"):
                        ui.label("✅ Checked In Successfully!").classes("text-xl font-bold text-green-600 mb-4")
                        ui.label(f"Time: {attendance.check_in_time.strftime('%I:%M %p')}").classes("text-gray-600")
                        if attendance.notes:
                            ui.label(f"Notes: {attendance.notes}").classes("text-sm text-gray-500 mt-2")
                        ui.button("Continue", on_click=lambda: success_dialog.close()).classes(
                            "mt-4 bg-green-500 text-white"
                        )

                await success_dialog
                ui.navigate.to("/dashboard")

            except Exception as e:
                logger.error(f"Check-in failed: {str(e)}")
                ui.notify(f"Check-in failed: {str(e)}", type="negative")

        ui.button("Check In Now", icon="schedule", on_click=perform_check_in).classes(
            "w-full bg-green-500 hover:bg-green-600 text-white py-3 text-lg font-semibold"
        )


def create_check_out_form(attendance_record: AttendanceRecord):
    """Create check-out form for existing attendance record"""
    current_user = AuthService.get_current_user()
    if current_user is None:
        return

    with ui.card().classes("w-full max-w-md mx-auto p-6 shadow-lg mt-6"):
        ui.label("Check Out").classes("text-2xl font-bold mb-6 text-center")

        # Show check-in info
        ui.label("Checked in at:").classes("text-sm text-gray-600")
        ui.label(f"{attendance_record.check_in_time.strftime('%I:%M %p')}").classes("text-lg font-semibold mb-4")

        # Current time
        now = datetime.now()
        ui.label(f"Current time: {now.strftime('%I:%M %p')}").classes(
            "text-center text-xl font-bold text-blue-600 mb-6"
        )

        # Photo upload for check-out
        ui.label("Check-out Photo (Optional)").classes("text-sm font-medium text-gray-700 mb-2")
        ui.upload(
            label="Take or upload check-out photo", on_upload=lambda e: handle_checkout_photo_upload(e), multiple=False
        ).classes("w-full mb-4").props('accept="image/*" capture="environment"')

        # Location for check-out
        ui.label("Location (Optional)").classes("text-sm font-medium text-gray-700 mb-2")
        location_input = ui.input(label="Check-out location", placeholder="Office, Home, Client site, etc.").classes(
            "w-full mb-6"
        )

        # Store uploaded photo ID
        uploaded_photo_id: dict[str, Optional[int]] = {"value": None}
        location_coords = {"lat": None, "lng": None}

        def handle_checkout_photo_upload(e: UploadEventArguments):
            try:
                if current_user.id is None:
                    ui.notify("User ID not found", type="negative")
                    return
                file_record = FileService.save_upload_file(e, current_user.id, FileType.PHOTO)
                if file_record is not None and file_record.id is not None:
                    uploaded_photo_id["value"] = file_record.id
                    ui.notify("Check-out photo uploaded", type="positive")
                else:
                    ui.notify("Failed to upload photo", type="negative")
            except Exception as ex:
                logger.error(f"Check-out photo upload error for user {current_user.id}: {str(ex)}")
                ui.notify(f"Upload error: {str(ex)}", type="negative")

        # Check-out button
        async def perform_check_out():
            try:
                check_out_data = AttendanceCheckOut(
                    check_out_photo_id=uploaded_photo_id["value"],
                    location_latitude=location_coords["lat"],
                    location_longitude=location_coords["lng"],
                    location_address=location_input.value or None,
                )

                if attendance_record.id is None:
                    ui.notify("Attendance record ID not found", type="negative")
                    return

                updated_attendance = AttendanceService.check_out(attendance_record.id, check_out_data)
                if updated_attendance is None:
                    ui.notify("Check-out failed - attendance record not found", type="negative")
                    return

                ui.notify("Check-out successful!", type="positive")

                # Calculate hours worked
                if updated_attendance.check_out_time is not None:
                    check_in_dt = datetime.combine(attendance_record.check_in_date, attendance_record.check_in_time)
                    check_out_dt = datetime.combine(attendance_record.check_in_date, updated_attendance.check_out_time)
                    hours_worked = (check_out_dt - check_in_dt).total_seconds() / 3600
                    hours_text = f"{hours_worked:.2f}"
                else:
                    hours_text = "0.00"

                # Show success message
                with ui.dialog() as success_dialog:
                    with ui.card().classes("p-6"):
                        ui.label("✅ Checked Out Successfully!").classes("text-xl font-bold text-green-600 mb-4")
                        if updated_attendance.check_out_time is not None:
                            ui.label(
                                f"Check-out time: {updated_attendance.check_out_time.strftime('%I:%M %p')}"
                            ).classes("text-gray-600")
                        ui.label(f"Hours worked: {hours_text}").classes("text-gray-600")
                        ui.button("Continue", on_click=lambda: success_dialog.close()).classes(
                            "mt-4 bg-green-500 text-white"
                        )

                await success_dialog
                ui.navigate.to("/dashboard")

            except Exception as e:
                logger.error(f"Check-out failed: {str(e)}")
                ui.notify(f"Check-out failed: {str(e)}", type="negative")

        ui.button("Check Out Now", icon="exit_to_app", on_click=perform_check_out).classes(
            "w-full bg-red-500 hover:bg-red-600 text-white py-3 text-lg font-semibold"
        )


@ui.refreshable
def show_attendance_history():
    """Show user's attendance history"""
    current_user = AuthService.get_current_user()
    if current_user is None:
        ui.label("Please log in first").classes("text-red-500")
        return

    ui.label("Attendance History").classes("text-2xl font-bold mb-6")

    if current_user.id is None:
        ui.label("User ID not found").classes("text-red-500")
        return

    attendance_records = AttendanceService.get_user_attendance_records(current_user.id, limit=20)

    if not attendance_records:
        with ui.card().classes("p-6 text-center"):
            ui.label("No attendance records found").classes("text-gray-500")
        return

    # Create responsive table/cards for attendance records
    with ui.column().classes("gap-4 w-full"):
        for record in attendance_records:
            with ui.card().classes("w-full p-4 hover:shadow-md transition-shadow"):
                with ui.row().classes("w-full items-center justify-between"):
                    # Date and day
                    with ui.column().classes("items-start"):
                        ui.label(record.check_in_date.strftime("%B %d, %Y")).classes("font-semibold text-lg")
                        ui.label(record.check_in_date.strftime("%A")).classes("text-sm text-gray-500")

                    # Check-in/out times
                    with ui.column().classes("items-center"):
                        ui.label("Check-in").classes("text-xs text-gray-500")
                        ui.label(record.check_in_time.strftime("%I:%M %p")).classes("font-mono text-green-600")

                        if record.check_out_time is not None:
                            ui.label("Check-out").classes("text-xs text-gray-500 mt-1")
                            ui.label(record.check_out_time.strftime("%I:%M %p")).classes("font-mono text-red-600")
                        else:
                            ui.label("Not checked out").classes("text-xs text-orange-500 mt-1")

                    # Hours worked (if checked out)
                    if record.check_out_time is not None:
                        check_in_dt = datetime.combine(record.check_in_date, record.check_in_time)
                        check_out_dt = datetime.combine(record.check_in_date, record.check_out_time)
                        hours = (check_out_dt - check_in_dt).total_seconds() / 3600

                        with ui.column().classes("items-end"):
                            ui.label("Hours").classes("text-xs text-gray-500")
                            ui.label(f"{hours:.2f}h").classes("font-semibold text-blue-600")

                # Notes if available
                if record.notes:
                    ui.label(f"Notes: {record.notes}").classes("text-sm text-gray-600 mt-2")


def create():
    """Create attendance management pages"""

    @ui.page("/checkin")
    def checkin_page():
        if not AuthService.is_authenticated():
            ui.navigate.to("/login")
            return

        # Mobile-first responsive layout
        with ui.column().classes("min-h-screen bg-gray-50 p-4"):
            create_check_in_form()

    @ui.page("/attendance")
    def attendance_page():
        if not AuthService.is_authenticated():
            ui.navigate.to("/login")
            return

        with ui.column().classes("min-h-screen bg-gray-50 p-4 max-w-4xl mx-auto"):
            # Navigation header
            with ui.row().classes("w-full items-center justify-between mb-6"):
                ui.button(icon="arrow_back", on_click=lambda: ui.navigate.to("/dashboard")).props("flat")
                ui.label("Attendance").classes("text-2xl font-bold")
                ui.button("Check In", icon="schedule", on_click=lambda: ui.navigate.to("/checkin")).classes(
                    "bg-green-500 text-white"
                )

            show_attendance_history()
