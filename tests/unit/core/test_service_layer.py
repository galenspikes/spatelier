"""
Tests for service layer architecture.

This module tests the service factory and interfaces.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from core.config import Config
from core.database_service import DatabaseServiceFactory, RepositoryContainer
from core.interfaces import (
    IDatabaseService,
    IMetadataService,
    IPlaylistService,
    IRepositoryContainer,
    ITranscriptionService,
    IVideoDownloadService,
)
from core.service_factory import ServiceFactory


class TestServiceFactory:
    """Test service factory functionality."""

    def test_service_factory_creation(self):
        """Test service factory creation."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)
        assert factory is not None
        assert factory.config is config
        assert factory.verbose is False

    def test_create_database_service(self):
        """Test creating database service."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        with patch("core.service_factory.DatabaseServiceFactory") as mock_db_factory:
            mock_instance = Mock(spec=IDatabaseService)
            mock_db_factory.return_value = mock_instance

            service = factory.create_database_service()
            assert service is mock_instance
            mock_db_factory.assert_called_once_with(config, verbose=False)

    def test_create_video_download_service(self):
        """Test creating video download service."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        with patch("modules.video.services.VideoDownloadService") as mock_service:
            with patch.object(factory, "create_database_service", return_value=Mock()):
                mock_instance = Mock(spec=IVideoDownloadService)
                mock_service.return_value = mock_instance

                service = factory.create_video_download_service()
                assert service is mock_instance
                # The service is called with config, verbose, and db_service parameters
                mock_service.assert_called_once()

    def test_create_metadata_service(self):
        """Test creating metadata service."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        with patch("modules.video.services.MetadataService") as mock_service:
            with patch.object(factory, "create_database_service", return_value=Mock()):
                mock_instance = Mock(spec=IMetadataService)
                mock_service.return_value = mock_instance

                service = factory.create_metadata_service()
                assert service is mock_instance
                # The service is called with config, verbose, and db_service parameters
                mock_service.assert_called_once()

    def test_create_transcription_service(self):
        """Test creating transcription service."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        with patch(
            "modules.video.services.transcription_service.TranscriptionService"
        ) as mock_service:
            with patch.object(factory, "create_database_service", return_value=Mock()):
                mock_instance = Mock(spec=ITranscriptionService)
                mock_service.return_value = mock_instance

                service = factory.create_transcription_service()
                assert service is mock_instance
                # The service is called with config, verbose, and db_service parameters
                mock_service.assert_called_once()

    def test_create_playlist_service(self):
        """Test creating playlist service."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        with patch("modules.video.services.PlaylistService") as mock_service:
            with patch.object(factory, "create_database_service", return_value=Mock()):
                mock_instance = Mock(spec=IPlaylistService)
                mock_service.return_value = mock_instance

                service = factory.create_playlist_service()
                assert service is mock_instance
                # The service is called with config, verbose, and db_service parameters
                mock_service.assert_called_once()

    def test_database_property_lazy_loading(self):
        """Test that database property loads services lazily."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        with patch.object(factory, "create_database_service") as mock_create:
            mock_service = Mock(spec=IDatabaseService)
            mock_create.return_value = mock_service

            # Access database property
            service = factory.database

            assert service is mock_service
            mock_create.assert_called_once()

    def test_repositories_property_lazy_loading(self):
        """Test that repositories property loads services lazily."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        with patch.object(factory, "create_database_service") as mock_create:
            mock_db_service = Mock(spec=IDatabaseService)
            mock_repos = Mock(spec=IRepositoryContainer)
            mock_db_service.initialize.return_value = mock_repos
            mock_create.return_value = mock_db_service

            # Access repositories property
            repos = factory.repositories

            assert repos is mock_repos
            mock_create.assert_called_once()
            mock_db_service.initialize.assert_called_once()

    def test_video_download_property_lazy_loading(self):
        """Test that video_download property loads services lazily."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        with patch.object(factory, "create_video_download_service") as mock_create:
            mock_service = Mock(spec=IVideoDownloadService)
            mock_create.return_value = mock_service

            # Access video_download property
            service = factory.video_download

            assert service is mock_service
            mock_create.assert_called_once()

    def test_metadata_property_lazy_loading(self):
        """Test that metadata property loads services lazily."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        with patch.object(factory, "create_metadata_service") as mock_create:
            mock_service = Mock(spec=IMetadataService)
            mock_create.return_value = mock_service

            # Access metadata property
            service = factory.metadata

            assert service is mock_service
            mock_create.assert_called_once()

    def test_transcription_property_lazy_loading(self):
        """Test that transcription property loads services lazily."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        with patch.object(factory, "create_transcription_service") as mock_create:
            mock_service = Mock(spec=ITranscriptionService)
            mock_create.return_value = mock_service

            # Access transcription property
            service = factory.transcription

            assert service is mock_service
            mock_create.assert_called_once()

    def test_playlist_property_lazy_loading(self):
        """Test that playlist property loads services lazily."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        with patch.object(factory, "create_playlist_service") as mock_create:
            mock_service = Mock(spec=IPlaylistService)
            mock_create.return_value = mock_service

            # Access playlist property
            service = factory.playlist

            assert service is mock_service
            mock_create.assert_called_once()

    def test_job_queue_property_lazy_loading(self):
        """Test that job_queue property loads services lazily."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        with patch("core.job_queue.JobQueue") as mock_job_queue:
            mock_instance = Mock()
            mock_job_queue.return_value = mock_instance

            # Access job_queue property
            queue = factory.job_queue

            assert queue is mock_instance
            mock_job_queue.assert_called_once_with(config, False)

    def test_context_manager(self):
        """Test service factory as context manager."""
        config = Config()

        with ServiceFactory(config, verbose=False) as factory:
            assert factory is not None
            assert factory.config is config

    def test_close_all_services(self):
        """Test closing all services."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        # Mock services
        mock_db_service = Mock()
        mock_db_service.close_connections = Mock()
        factory._database_service = mock_db_service
        factory._repositories = Mock()
        factory._video_download_service = Mock()
        factory._metadata_service = Mock()
        factory._transcription_service = Mock()
        factory._playlist_service = Mock()
        factory._job_queue = Mock()

        # Close all services
        factory.close_all_services()

        # Check that database service close was called
        mock_db_service.close_connections.assert_called_once()

        # Check that all services are reset to None
        assert factory._database_service is None
        assert factory._repositories is None
        assert factory._video_download_service is None
        assert factory._metadata_service is None
        assert factory._transcription_service is None
        assert factory._playlist_service is None
        assert factory._job_queue is None

    def test_initialize_database(self):
        """Test initialize_database method."""
        config = Config()
        factory = ServiceFactory(config, verbose=False)

        # Mock the database service and its initialize method
        mock_db_service = Mock(spec=IDatabaseService)
        mock_repos = Mock(spec=IRepositoryContainer)
        mock_db_service.initialize.return_value = mock_repos
        factory._database_service = mock_db_service

        repos = factory.initialize_database()
        assert repos is mock_repos
        mock_db_service.initialize.assert_called_once()


class TestRepositoryContainer:
    """Test repository container functionality."""

    def test_repository_container_initialization(self):
        """Test repository container initialization."""
        mock_session = Mock()
        repos = RepositoryContainer(mock_session, verbose=False)

        assert repos.session is mock_session
        assert repos.verbose == False
        assert repos.media is not None
        assert repos.jobs is not None
        assert repos.analytics is not None
        assert repos.playlists is not None
        assert repos.playlist_videos is not None
