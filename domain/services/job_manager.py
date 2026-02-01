"""
Job management domain service.

Handles job creation, updates, and status management,
keeping job persistence logic separate from business logic.
"""

from typing import Optional


class JobManager:
    """
    Domain service for managing processing jobs.

    Handles job creation, status updates, and coordination,
    keeping persistence logic separate from business logic.
    """

    def __init__(self, repositories, logger=None):
        """
        Initialize job manager.

        Args:
            repositories: Repository container
            logger: Optional logger
        """
        self.repos = repositories
        self.logger = logger

    def create_job(
        self,
        job_type: str,
        input_path: str,
        output_path: str,
        parameters: Optional[dict] = None,
    ) -> Optional[int]:
        """
        Create a processing job.

        Args:
            job_type: Type of job (e.g., "download_video")
            input_path: Input path (e.g., URL)
            output_path: Output path
            parameters: Optional job parameters

        Returns:
            Job ID if successful, None otherwise
        """
        try:
            job = self.repos.jobs.create(
                media_file_id=None,  # Will be updated after processing
                job_type=job_type,
                input_path=input_path,
                output_path=output_path,
                parameters=str(parameters) if parameters else "",
            )
            if self.logger:
                self.logger.info(f"Created {job_type} job: {job.id}")
            return job.id
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to create job: {e}")
            return None

    def update_job_status(
        self,
        job_id: int,
        status: str,
        error_message: Optional[str] = None,
    ) -> bool:
        """
        Update job status.

        Args:
            job_id: Job ID
            status: New status
            error_message: Optional error message

        Returns:
            True if successful, False otherwise
        """
        try:
            from database.models import ProcessingStatus

            status_enum = ProcessingStatus(status) if isinstance(status, str) else status
            self.repos.jobs.update_status(job_id, status_enum, error_message=error_message)
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to update job status: {e}")
            return False

    def update_job(
        self,
        job_id: int,
        media_file_id: Optional[int] = None,
        output_path: Optional[str] = None,
    ) -> bool:
        """
        Update job with media file ID and/or output path.

        Args:
            job_id: Job ID
            media_file_id: Optional media file ID
            output_path: Optional output path

        Returns:
            True if successful, False otherwise
        """
        try:
            # SQLite expects str for path columns, not Path
            path_str = str(output_path) if output_path is not None else None
            self.repos.jobs.update(
                job_id,
                media_file_id=media_file_id,
                output_path=path_str,
            )
            return True
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to update job: {e}")
            return False
