"""Test the service layer functionality"""

import pytest
from datetime import date
from decimal import Decimal

from app.database import reset_db
from app.services import UserService, AttendanceService, RequestService, TaskLogService, FileService
from app.models import (
    UserCreate,
    AttendanceCheckIn,
    AttendanceCheckOut,
    RequestCreate,
    RequestType,
    RequestStatus,
    TaskLogCreate,
    TaskLogUpdate,
)


@pytest.fixture(autouse=True)
def reset_database():
    """Reset database before each test"""
    reset_db()
    yield
    reset_db()


@pytest.fixture
def sample_user():
    """Create a sample user for testing"""
    user_data = UserCreate(
        employee_id="TEST001",
        email="test@example.com",
        first_name="Test",
        last_name="User",
        department="Testing",
        position="Test Engineer",
    )
    return UserService.create_user(user_data)


class TestUserService:
    def test_create_user(self):
        """Test user creation"""
        user_data = UserCreate(
            employee_id="EMP001",
            email="john@example.com",
            first_name="John",
            last_name="Doe",
            department="Engineering",
            position="Developer",
        )

        user = UserService.create_user(user_data)

        assert user.id is not None
        assert user.employee_id == "EMP001"
        assert user.email == "john@example.com"
        assert user.first_name == "John"
        assert user.last_name == "Doe"
        assert user.department == "Engineering"
        assert user.position == "Developer"
        assert user.is_active is True

    def test_get_user_by_id(self, sample_user):
        """Test retrieving user by ID"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        retrieved_user = UserService.get_user_by_id(sample_user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == sample_user.id
        assert retrieved_user.employee_id == sample_user.employee_id

    def test_get_user_by_employee_id(self, sample_user):
        """Test retrieving user by employee ID"""
        retrieved_user = UserService.get_user_by_employee_id(sample_user.employee_id)

        assert retrieved_user is not None
        assert retrieved_user.employee_id == sample_user.employee_id

    def test_get_nonexistent_user(self):
        """Test retrieving nonexistent user returns None"""
        user = UserService.get_user_by_id(999999)
        assert user is None

        user = UserService.get_user_by_employee_id("NONEXISTENT")
        assert user is None

    def test_get_all_users(self, sample_user):
        """Test retrieving all active users"""
        users = UserService.get_all_users()
        assert len(users) == 1
        assert users[0].id == sample_user.id


class TestAttendanceService:
    def test_check_in(self, sample_user):
        """Test attendance check-in"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        check_in_data = AttendanceCheckIn(
            location_latitude=37.7749,
            location_longitude=-122.4194,
            location_address="San Francisco, CA",
            notes="Test check-in",
        )

        attendance = AttendanceService.check_in(sample_user.id, check_in_data)

        assert attendance.id is not None
        assert attendance.user_id == sample_user.id
        assert attendance.check_in_date == date.today()
        assert attendance.check_in_location is not None
        assert attendance.check_in_location["latitude"] == 37.7749
        assert attendance.check_in_location["longitude"] == -122.4194
        assert attendance.check_in_location["address"] == "San Francisco, CA"
        assert attendance.notes == "Test check-in"
        assert attendance.check_out_time is None

    def test_check_out(self, sample_user):
        """Test attendance check-out"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        # First check in
        check_in_data = AttendanceCheckIn(notes="Morning check-in")
        attendance = AttendanceService.check_in(sample_user.id, check_in_data)

        if attendance.id is None:
            pytest.fail("Attendance record ID is None")

        # Then check out
        check_out_data = AttendanceCheckOut(
            location_latitude=37.7849, location_longitude=-122.4094, location_address="Different location"
        )

        updated_attendance = AttendanceService.check_out(attendance.id, check_out_data)

        assert updated_attendance is not None
        assert updated_attendance.check_out_time is not None
        assert updated_attendance.check_out_location is not None
        assert updated_attendance.check_out_location["latitude"] == 37.7849

    def test_get_todays_attendance(self, sample_user):
        """Test retrieving today's attendance"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        # No attendance initially
        today_attendance = AttendanceService.get_todays_attendance(sample_user.id)
        assert today_attendance is None

        # Check in
        check_in_data = AttendanceCheckIn(notes="Today check-in")
        AttendanceService.check_in(sample_user.id, check_in_data)

        # Should find today's attendance
        today_attendance = AttendanceService.get_todays_attendance(sample_user.id)
        assert today_attendance is not None
        assert today_attendance.check_in_date == date.today()

    def test_get_user_attendance_records(self, sample_user):
        """Test retrieving user attendance records"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        # Create multiple attendance records
        for i in range(3):
            check_in_data = AttendanceCheckIn(notes=f"Check-in {i + 1}")
            AttendanceService.check_in(sample_user.id, check_in_data)

        records = AttendanceService.get_user_attendance_records(sample_user.id)
        assert len(records) == 3

        # Should be ordered by date desc (most recent first)
        for record in records:
            assert record.user_id == sample_user.id


class TestRequestService:
    def test_create_request(self, sample_user):
        """Test creating a request"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        request_data = RequestCreate(
            request_type=RequestType.LEAVE,
            title="Annual Leave Request",
            reason="Family vacation",
            start_date=date.today(),
            end_date=date(2024, 12, 31),
            supporting_document_ids=[],
        )

        request = RequestService.create_request(sample_user.id, request_data)

        assert request.id is not None
        assert request.user_id == sample_user.id
        assert request.request_type == RequestType.LEAVE
        assert request.title == "Annual Leave Request"
        assert request.reason == "Family vacation"
        assert request.status == RequestStatus.PENDING

    def test_get_request(self, sample_user):
        """Test retrieving a specific request"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        request_data = RequestCreate(
            request_type=RequestType.PERMISSION,
            title="Doctor Appointment",
            reason="Medical checkup",
            start_date=date.today(),
            end_date=date.today(),
        )

        created_request = RequestService.create_request(sample_user.id, request_data)

        if created_request.id is None:
            pytest.fail("Created request ID is None")

        retrieved_request = RequestService.get_request(created_request.id)

        assert retrieved_request is not None
        assert retrieved_request.id == created_request.id
        assert retrieved_request.title == "Doctor Appointment"

    def test_get_user_requests(self, sample_user):
        """Test retrieving all user requests"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        # Create multiple requests
        request_types = [RequestType.LEAVE, RequestType.PERMISSION, RequestType.SICK_LEAVE]
        for req_type in request_types:
            request_data = RequestCreate(
                request_type=req_type,
                title=f"{req_type.value} request",
                reason="Test reason",
                start_date=date.today(),
                end_date=date.today(),
            )
            RequestService.create_request(sample_user.id, request_data)

        requests = RequestService.get_user_requests(sample_user.id)
        assert len(requests) == 3

        # Should be ordered by created_at desc
        for request in requests:
            assert request.user_id == sample_user.id

    def test_get_nonexistent_request(self):
        """Test retrieving nonexistent request returns None"""
        request = RequestService.get_request(999999)
        assert request is None


class TestTaskLogService:
    def test_create_task_log(self, sample_user):
        """Test creating a task log"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        task_data = TaskLogCreate(
            task_date=date.today(),
            title="Fix bug in authentication",
            description="Resolved issue with user login validation",
            duration_hours=Decimal("2.5"),
            status="completed",
            priority="high",
            category="Bug Fix",
            attachment_ids=[],
            tags=["authentication", "bug-fix", "urgent"],
        )

        task_log = TaskLogService.create_task_log(sample_user.id, task_data)

        assert task_log.id is not None
        assert task_log.user_id == sample_user.id
        assert task_log.task_date == date.today()
        assert task_log.title == "Fix bug in authentication"
        assert task_log.description == "Resolved issue with user login validation"
        assert task_log.duration_hours == Decimal("2.5")
        assert task_log.status == "completed"
        assert task_log.priority == "high"
        assert task_log.category == "Bug Fix"
        assert task_log.tags == ["authentication", "bug-fix", "urgent"]

    def test_update_task_log(self, sample_user):
        """Test updating a task log"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        # Create task
        task_data = TaskLogCreate(
            task_date=date.today(),
            title="Initial task",
            description="Initial description",
            status="in_progress",
            priority="medium",
        )

        task_log = TaskLogService.create_task_log(sample_user.id, task_data)

        if task_log.id is None:
            pytest.fail("Task log ID is None")

        # Update task
        update_data = TaskLogUpdate(
            title="Updated task title", status="completed", priority="high", duration_hours=Decimal("1.5")
        )

        updated_task = TaskLogService.update_task_log(task_log.id, update_data)

        assert updated_task is not None
        assert updated_task.title == "Updated task title"
        assert updated_task.status == "completed"
        assert updated_task.priority == "high"
        assert updated_task.duration_hours == Decimal("1.5")
        # Description should remain unchanged
        assert updated_task.description == "Initial description"

    def test_get_user_task_logs(self, sample_user):
        """Test retrieving user task logs"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        # Create tasks for different dates
        today = date.today()

        task_data_1 = TaskLogCreate(task_date=today, title="Today task", description="Task for today")

        task_data_2 = TaskLogCreate(task_date=today, title="Another today task", description="Another task for today")

        TaskLogService.create_task_log(sample_user.id, task_data_1)
        TaskLogService.create_task_log(sample_user.id, task_data_2)

        # Get all tasks
        all_tasks = TaskLogService.get_user_task_logs(sample_user.id)
        assert len(all_tasks) == 2

        # Get tasks for specific date
        today_tasks = TaskLogService.get_user_task_logs(sample_user.id, task_date=today)
        assert len(today_tasks) == 2

        # Get tasks for different date
        different_date_tasks = TaskLogService.get_user_task_logs(sample_user.id, task_date=date(2024, 1, 1))
        assert len(different_date_tasks) == 0

    def test_delete_task_log(self, sample_user):
        """Test deleting a task log"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        # Create task
        task_data = TaskLogCreate(
            task_date=date.today(), title="Task to delete", description="This task will be deleted"
        )

        task_log = TaskLogService.create_task_log(sample_user.id, task_data)

        if task_log.id is None:
            pytest.fail("Task log ID is None")

        # Delete task
        result = TaskLogService.delete_task_log(task_log.id)
        assert result is True

        # Verify task is deleted
        deleted_task = TaskLogService.get_task_log(task_log.id)
        assert deleted_task is None

    def test_delete_nonexistent_task(self):
        """Test deleting nonexistent task returns False"""
        result = TaskLogService.delete_task_log(999999)
        assert result is False

    def test_get_nonexistent_task(self):
        """Test retrieving nonexistent task returns None"""
        task = TaskLogService.get_task_log(999999)
        assert task is None


class TestFileService:
    def test_ensure_upload_dir(self):
        """Test upload directory creation"""
        # This should not raise an error
        FileService.ensure_upload_dir()
        assert FileService.UPLOAD_DIR.exists()

    def test_get_nonexistent_file(self):
        """Test retrieving nonexistent file returns None"""
        file_record = FileService.get_file(999999)
        assert file_record is None


class TestServiceIntegration:
    def test_full_attendance_workflow(self, sample_user):
        """Test complete attendance workflow"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        # Check that user has no attendance today
        today_attendance = AttendanceService.get_todays_attendance(sample_user.id)
        assert today_attendance is None

        # Check in
        check_in_data = AttendanceCheckIn(location_address="Office", notes="Starting work day")
        attendance = AttendanceService.check_in(sample_user.id, check_in_data)
        assert attendance.check_out_time is None

        # Verify today's attendance exists
        today_attendance = AttendanceService.get_todays_attendance(sample_user.id)
        assert today_attendance is not None
        assert today_attendance.id == attendance.id

        # Check out
        if attendance.id is None:
            pytest.fail("Attendance ID is None")

        check_out_data = AttendanceCheckOut(location_address="Office")
        updated_attendance = AttendanceService.check_out(attendance.id, check_out_data)

        assert updated_attendance is not None
        assert updated_attendance.check_out_time is not None

    def test_full_request_workflow(self, sample_user):
        """Test complete request workflow"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        # Create request
        request_data = RequestCreate(
            request_type=RequestType.LEAVE,
            title="Vacation Request",
            reason="Annual vacation with family",
            start_date=date.today(),
            end_date=date(2024, 12, 31),
        )

        request = RequestService.create_request(sample_user.id, request_data)
        assert request.status == RequestStatus.PENDING

        # Verify request appears in user's requests
        user_requests = RequestService.get_user_requests(sample_user.id)
        assert len(user_requests) == 1
        assert user_requests[0].id == request.id

    def test_task_log_with_decimal_hours(self, sample_user):
        """Test task logging with decimal hours"""
        if sample_user.id is None:
            pytest.fail("Sample user ID is None")

        task_data = TaskLogCreate(
            task_date=date.today(),
            title="Code Review",
            description="Reviewed pull request #123",
            duration_hours=Decimal("1.75"),  # 1 hour 45 minutes
            status="completed",
            priority="medium",
        )

        task_log = TaskLogService.create_task_log(sample_user.id, task_data)
        assert task_log.duration_hours == Decimal("1.75")

        # Update with different decimal value
        if task_log.id is None:
            pytest.fail("Task log ID is None")

        update_data = TaskLogUpdate(duration_hours=Decimal("2.25"))
        updated_task = TaskLogService.update_task_log(task_log.id, update_data)

        assert updated_task is not None
        assert updated_task.duration_hours == Decimal("2.25")
