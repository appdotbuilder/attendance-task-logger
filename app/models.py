from sqlmodel import SQLModel, Field, Relationship, JSON, Column
from datetime import datetime, date, time
from typing import Optional, List, Dict, Any
from enum import Enum
from decimal import Decimal


# Enums for status and types
class RequestType(str, Enum):
    PERMISSION = "permission"
    LEAVE = "leave"
    SICK_LEAVE = "sick_leave"


class RequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class FileType(str, Enum):
    PHOTO = "photo"
    DOCUMENT = "document"
    ATTACHMENT = "attachment"


# Base file model for managing uploads
class File(SQLModel, table=True):
    __tablename__ = "files"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    filename: str = Field(max_length=255)
    original_filename: str = Field(max_length=255)
    file_path: str = Field(max_length=500)
    file_size: int = Field(ge=0)  # File size in bytes
    mime_type: str = Field(max_length=100)
    file_type: FileType = Field(default=FileType.ATTACHMENT)
    uploaded_by: int = Field(foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    uploader: "User" = Relationship(back_populates="uploaded_files")


# User model for employees
class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    employee_id: str = Field(unique=True, max_length=50)
    email: str = Field(unique=True, max_length=255)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    department: Optional[str] = Field(default=None, max_length=100)
    position: Optional[str] = Field(default=None, max_length=100)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    attendance_records: List["AttendanceRecord"] = Relationship(back_populates="user")
    requests: List["Request"] = Relationship(back_populates="user")
    task_logs: List["TaskLog"] = Relationship(back_populates="user")
    uploaded_files: List[File] = Relationship(back_populates="uploader")


# Attendance record model
class AttendanceRecord(SQLModel, table=True):
    __tablename__ = "attendance_records"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    check_in_date: date = Field()
    check_in_time: time = Field()
    check_in_photo_id: Optional[int] = Field(default=None, foreign_key="files.id")
    check_in_location: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))  # Store lat, lng, address
    check_out_time: Optional[time] = Field(default=None)
    check_out_photo_id: Optional[int] = Field(default=None, foreign_key="files.id")
    check_out_location: Optional[Dict[str, Any]] = Field(default=None, sa_column=Column(JSON))
    notes: Optional[str] = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="attendance_records")


# Request model for permissions, leave, sick leave
class Request(SQLModel, table=True):
    __tablename__ = "requests"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    request_type: RequestType = Field()
    title: str = Field(max_length=200)
    reason: str = Field(max_length=1000)
    start_date: date = Field()
    end_date: date = Field()
    status: RequestStatus = Field(default=RequestStatus.PENDING)
    supporting_documents: List[str] = Field(default=[], sa_column=Column(JSON))  # List of file IDs
    manager_notes: Optional[str] = Field(default=None, max_length=500)
    reviewed_by: Optional[int] = Field(default=None)
    reviewed_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="requests")


# Task log model for daily activities
class TaskLog(SQLModel, table=True):
    __tablename__ = "task_logs"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    task_date: date = Field()
    title: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    duration_hours: Optional[Decimal] = Field(default=None, decimal_places=2)
    status: str = Field(default="in_progress", max_length=50)
    priority: str = Field(default="medium", max_length=20)  # low, medium, high, urgent
    category: Optional[str] = Field(default=None, max_length=100)
    attachments: List[str] = Field(default=[], sa_column=Column(JSON))  # List of file IDs
    tags: List[str] = Field(default=[], sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="task_logs")


# Non-persistent schemas for API and forms


# User schemas
class UserCreate(SQLModel, table=False):
    employee_id: str = Field(max_length=50)
    email: str = Field(max_length=255)
    first_name: str = Field(max_length=100)
    last_name: str = Field(max_length=100)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    department: Optional[str] = Field(default=None, max_length=100)
    position: Optional[str] = Field(default=None, max_length=100)


class UserUpdate(SQLModel, table=False):
    email: Optional[str] = Field(default=None, max_length=255)
    first_name: Optional[str] = Field(default=None, max_length=100)
    last_name: Optional[str] = Field(default=None, max_length=100)
    phone_number: Optional[str] = Field(default=None, max_length=20)
    department: Optional[str] = Field(default=None, max_length=100)
    position: Optional[str] = Field(default=None, max_length=100)


# Attendance schemas
class AttendanceCheckIn(SQLModel, table=False):
    check_in_photo_id: Optional[int] = Field(default=None)
    location_latitude: Optional[float] = Field(default=None)
    location_longitude: Optional[float] = Field(default=None)
    location_address: Optional[str] = Field(default=None, max_length=500)
    notes: Optional[str] = Field(default=None, max_length=500)


class AttendanceCheckOut(SQLModel, table=False):
    check_out_photo_id: Optional[int] = Field(default=None)
    location_latitude: Optional[float] = Field(default=None)
    location_longitude: Optional[float] = Field(default=None)
    location_address: Optional[str] = Field(default=None, max_length=500)


# Request schemas
class RequestCreate(SQLModel, table=False):
    request_type: RequestType = Field()
    title: str = Field(max_length=200)
    reason: str = Field(max_length=1000)
    start_date: date = Field()
    end_date: date = Field()
    supporting_document_ids: List[int] = Field(default=[])


class RequestUpdate(SQLModel, table=False):
    title: Optional[str] = Field(default=None, max_length=200)
    reason: Optional[str] = Field(default=None, max_length=1000)
    start_date: Optional[date] = Field(default=None)
    end_date: Optional[date] = Field(default=None)
    status: Optional[RequestStatus] = Field(default=None)
    manager_notes: Optional[str] = Field(default=None, max_length=500)


# Task log schemas
class TaskLogCreate(SQLModel, table=False):
    task_date: date = Field()
    title: str = Field(max_length=200)
    description: str = Field(max_length=2000)
    duration_hours: Optional[Decimal] = Field(default=None, decimal_places=2)
    status: str = Field(default="in_progress", max_length=50)
    priority: str = Field(default="medium", max_length=20)
    category: Optional[str] = Field(default=None, max_length=100)
    attachment_ids: List[int] = Field(default=[])
    tags: List[str] = Field(default=[])


class TaskLogUpdate(SQLModel, table=False):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    duration_hours: Optional[Decimal] = Field(default=None, decimal_places=2)
    status: Optional[str] = Field(default=None, max_length=50)
    priority: Optional[str] = Field(default=None, max_length=20)
    category: Optional[str] = Field(default=None, max_length=100)
    attachment_ids: Optional[List[int]] = Field(default=None)
    tags: Optional[List[str]] = Field(default=None)


# File upload schema
class FileUpload(SQLModel, table=False):
    filename: str = Field(max_length=255)
    file_type: FileType = Field(default=FileType.ATTACHMENT)
    mime_type: str = Field(max_length=100)


# Response schemas for API
class AttendanceRecordResponse(SQLModel, table=False):
    id: int
    check_in_date: str  # ISO format date
    check_in_time: str  # ISO format time
    check_out_time: Optional[str] = Field(default=None)
    check_in_location: Optional[Dict[str, Any]] = Field(default=None)
    check_out_location: Optional[Dict[str, Any]] = Field(default=None)
    notes: Optional[str] = Field(default=None)
    created_at: str  # ISO format datetime


class RequestResponse(SQLModel, table=False):
    id: int
    request_type: RequestType
    title: str
    reason: str
    start_date: str  # ISO format date
    end_date: str  # ISO format date
    status: RequestStatus
    manager_notes: Optional[str] = Field(default=None)
    created_at: str  # ISO format datetime
    updated_at: str  # ISO format datetime


class TaskLogResponse(SQLModel, table=False):
    id: int
    task_date: str  # ISO format date
    title: str
    description: str
    duration_hours: Optional[Decimal] = Field(default=None)
    status: str
    priority: str
    category: Optional[str] = Field(default=None)
    tags: List[str] = Field(default=[])
    created_at: str  # ISO format datetime
    updated_at: str  # ISO format datetime
