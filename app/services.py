"""Service layer for attendance and task management"""

import uuid
from datetime import datetime, date
from typing import Optional, List
from pathlib import Path

from sqlmodel import select, desc
from nicegui import events

from app.database import get_session
from app.models import (
    User,
    UserCreate,
    AttendanceRecord,
    AttendanceCheckIn,
    AttendanceCheckOut,
    Request,
    RequestCreate,
    RequestUpdate,
    TaskLog,
    TaskLogCreate,
    TaskLogUpdate,
    File,
    FileType,
)


class UserService:
    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        with get_session() as session:
            return session.get(User, user_id)

    @staticmethod
    def get_user_by_employee_id(employee_id: str) -> Optional[User]:
        with get_session() as session:
            statement = select(User).where(User.employee_id == employee_id)
            return session.exec(statement).first()

    @staticmethod
    def get_all_users() -> List[User]:
        with get_session() as session:
            statement = select(User).where(User.is_active)
            return list(session.exec(statement).all())

    @staticmethod
    def create_user(user_data: UserCreate) -> User:
        with get_session() as session:
            user = User(
                employee_id=user_data.employee_id,
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                phone_number=user_data.phone_number,
                department=user_data.department,
                position=user_data.position,
            )
            session.add(user)
            session.commit()
            session.refresh(user)
            return user


class FileService:
    UPLOAD_DIR = Path("uploads")

    @staticmethod
    def ensure_upload_dir():
        FileService.UPLOAD_DIR.mkdir(exist_ok=True)

    @staticmethod
    def save_upload_file(
        upload_event: events.UploadEventArguments, user_id: int, file_type: FileType = FileType.ATTACHMENT
    ) -> Optional[File]:
        """Save uploaded file and create database record"""
        if not upload_event.content:
            return None

        FileService.ensure_upload_dir()

        # Generate unique filename
        file_extension = Path(upload_event.name).suffix
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = FileService.UPLOAD_DIR / unique_filename

        try:
            # Save file to disk
            with open(file_path, "wb") as f:
                f.write(upload_event.content.read())

            # Create database record
            with get_session() as session:
                file_record = File(
                    filename=unique_filename,
                    original_filename=upload_event.name,
                    file_path=str(file_path),
                    file_size=len(upload_event.content.read()),
                    mime_type=upload_event.type or "application/octet-stream",
                    file_type=file_type,
                    uploaded_by=user_id,
                )
                session.add(file_record)
                session.commit()
                session.refresh(file_record)
                return file_record

        except Exception as e:
            # Clean up file if database save fails
            if file_path.exists():
                file_path.unlink()
            raise e

    @staticmethod
    def get_file(file_id: int) -> Optional[File]:
        with get_session() as session:
            return session.get(File, file_id)


class AttendanceService:
    @staticmethod
    def get_user_attendance_records(user_id: int, limit: int = 50) -> List[AttendanceRecord]:
        with get_session() as session:
            statement = (
                select(AttendanceRecord)
                .where(AttendanceRecord.user_id == user_id)
                .order_by(desc(AttendanceRecord.id))
                .limit(limit)
            )
            return list(session.exec(statement).all())

    @staticmethod
    def get_todays_attendance(user_id: int) -> Optional[AttendanceRecord]:
        """Get today's attendance record if exists"""
        today = date.today()
        with get_session() as session:
            statement = select(AttendanceRecord).where(
                AttendanceRecord.user_id == user_id, AttendanceRecord.check_in_date == today
            )
            return session.exec(statement).first()

    @staticmethod
    def check_in(user_id: int, check_in_data: AttendanceCheckIn) -> AttendanceRecord:
        """Create new attendance record for check-in"""
        now = datetime.now()

        # Prepare location data
        location_data = None
        if check_in_data.location_latitude is not None and check_in_data.location_longitude is not None:
            location_data = {
                "latitude": check_in_data.location_latitude,
                "longitude": check_in_data.location_longitude,
                "address": check_in_data.location_address or "Unknown location",
            }

        with get_session() as session:
            attendance = AttendanceRecord(
                user_id=user_id,
                check_in_date=now.date(),
                check_in_time=now.time(),
                check_in_photo_id=check_in_data.check_in_photo_id,
                check_in_location=location_data,
                notes=check_in_data.notes,
            )
            session.add(attendance)
            session.commit()
            session.refresh(attendance)
            return attendance

    @staticmethod
    def check_out(attendance_id: int, check_out_data: AttendanceCheckOut) -> Optional[AttendanceRecord]:
        """Update existing attendance record with check-out information"""
        now = datetime.now()

        # Prepare location data
        location_data = None
        if check_out_data.location_latitude is not None and check_out_data.location_longitude is not None:
            location_data = {
                "latitude": check_out_data.location_latitude,
                "longitude": check_out_data.location_longitude,
                "address": check_out_data.location_address or "Unknown location",
            }

        with get_session() as session:
            attendance = session.get(AttendanceRecord, attendance_id)
            if attendance is None:
                return None

            attendance.check_out_time = now.time()
            attendance.check_out_photo_id = check_out_data.check_out_photo_id
            attendance.check_out_location = location_data
            attendance.updated_at = now

            session.add(attendance)
            session.commit()
            session.refresh(attendance)
            return attendance


class RequestService:
    @staticmethod
    def get_user_requests(user_id: int, limit: int = 50) -> List[Request]:
        with get_session() as session:
            statement = select(Request).where(Request.user_id == user_id).order_by(desc(Request.id)).limit(limit)
            return list(session.exec(statement).all())

    @staticmethod
    def create_request(user_id: int, request_data: RequestCreate) -> Request:
        with get_session() as session:
            request = Request(
                user_id=user_id,
                request_type=request_data.request_type,
                title=request_data.title,
                reason=request_data.reason,
                start_date=request_data.start_date,
                end_date=request_data.end_date,
                supporting_documents=[str(doc_id) for doc_id in request_data.supporting_document_ids],
            )
            session.add(request)
            session.commit()
            session.refresh(request)
            return request

    @staticmethod
    def update_request(request_id: int, request_data: RequestUpdate) -> Optional[Request]:
        with get_session() as session:
            request = session.get(Request, request_id)
            if request is None:
                return None

            # Update only provided fields
            if request_data.title is not None:
                request.title = request_data.title
            if request_data.reason is not None:
                request.reason = request_data.reason
            if request_data.start_date is not None:
                request.start_date = request_data.start_date
            if request_data.end_date is not None:
                request.end_date = request_data.end_date
            if request_data.status is not None:
                request.status = request_data.status
            if request_data.manager_notes is not None:
                request.manager_notes = request_data.manager_notes

            request.updated_at = datetime.utcnow()
            session.add(request)
            session.commit()
            session.refresh(request)
            return request

    @staticmethod
    def get_request(request_id: int) -> Optional[Request]:
        with get_session() as session:
            return session.get(Request, request_id)


class TaskLogService:
    @staticmethod
    def get_user_task_logs(user_id: int, task_date: Optional[date] = None, limit: int = 50) -> List[TaskLog]:
        with get_session() as session:
            statement = select(TaskLog).where(TaskLog.user_id == user_id)

            if task_date is not None:
                statement = statement.where(TaskLog.task_date == task_date)

            statement = statement.order_by(desc(TaskLog.id)).limit(limit)
            return list(session.exec(statement).all())

    @staticmethod
    def create_task_log(user_id: int, task_data: TaskLogCreate) -> TaskLog:
        with get_session() as session:
            task_log = TaskLog(
                user_id=user_id,
                task_date=task_data.task_date,
                title=task_data.title,
                description=task_data.description,
                duration_hours=task_data.duration_hours,
                status=task_data.status,
                priority=task_data.priority,
                category=task_data.category,
                attachments=[str(att_id) for att_id in task_data.attachment_ids],
                tags=task_data.tags,
            )
            session.add(task_log)
            session.commit()
            session.refresh(task_log)
            return task_log

    @staticmethod
    def update_task_log(task_id: int, task_data: TaskLogUpdate) -> Optional[TaskLog]:
        with get_session() as session:
            task_log = session.get(TaskLog, task_id)
            if task_log is None:
                return None

            # Update only provided fields
            if task_data.title is not None:
                task_log.title = task_data.title
            if task_data.description is not None:
                task_log.description = task_data.description
            if task_data.duration_hours is not None:
                task_log.duration_hours = task_data.duration_hours
            if task_data.status is not None:
                task_log.status = task_data.status
            if task_data.priority is not None:
                task_log.priority = task_data.priority
            if task_data.category is not None:
                task_log.category = task_data.category
            if task_data.attachment_ids is not None:
                task_log.attachments = [str(att_id) for att_id in task_data.attachment_ids]
            if task_data.tags is not None:
                task_log.tags = task_data.tags

            task_log.updated_at = datetime.utcnow()
            session.add(task_log)
            session.commit()
            session.refresh(task_log)
            return task_log

    @staticmethod
    def get_task_log(task_id: int) -> Optional[TaskLog]:
        with get_session() as session:
            return session.get(TaskLog, task_id)

    @staticmethod
    def delete_task_log(task_id: int) -> bool:
        with get_session() as session:
            task_log = session.get(TaskLog, task_id)
            if task_log is None:
                return False

            session.delete(task_log)
            session.commit()
            return True
