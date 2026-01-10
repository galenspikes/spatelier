"""
NAS video workflow integration tests.

Tests the complete video download and processing workflow
on NAS including transcription and subtitle embedding.
"""

import pytest
import tempfile
import time
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import Mock, patch

from core.config import Config
from modules.video.services.download_service import VideoDownloadService
# Removed imports for deleted modular architecture
from database.connection import DatabaseManager
from database.repository import MediaFileRepository, ProcessingJobRepository, AnalyticsRepository
from tests.fixtures.nas_fixtures import *


class TestNASVideoWorkflow:
    """Integration tests for NAS video workflow."""
    
    def test_nas_single_video_download_workflow(self, nas_test_directory: Path, nas_config: Config, nas_available: bool):
        """Test complete single video download workflow on NAS."""
        if not nas_available:
            pytest.skip("NAS not available for testing")
        
        # Mock the actual download to avoid network calls
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            mock_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_instance
            
            # Mock video info
            mock_instance.extract_info.return_value = {
                "id": "test_video_123",
                "title": "Test Video for NAS",
                "duration": 120,
                "uploader": "Test Uploader",
                "thumbnail": "https://example.com/thumb.jpg"
            }
            
            # Mock download (create a test file)
            def mock_download(url):
                # Create a test video file in temp directory
                temp_dir = Path(".temp/99999")
                temp_dir.mkdir(parents=True, exist_ok=True)
                test_video = temp_dir / "Test Video for NAS [test_video_123].mp4"
                test_video.write_bytes(b'simulated video content for NAS test')
                return True
            
            mock_instance.download.side_effect = mock_download
            
            # Create downloader
            downloader = VideoDownloadService(nas_config, verbose=True)
            
            # Test download to NAS
            result = downloader.download(
                url="https://youtube.com/watch?v=test_video_123",
                output_path=nas_test_directory / "Test Video for NAS [test_video_123].mp4",
                transcribe=True
            )
            
            # Verify result
            assert result.success == True
            assert "Test Video for NAS [test_video_123].mp4" in str(result.output_path)
            
            # Verify file exists on NAS
            nas_video_file = nas_test_directory / "Test Video for NAS [test_video_123].mp4"
            assert nas_video_file.exists()
            assert nas_video_file.read_bytes() == b'simulated video content for NAS test'
            
            # Cleanup
            nas_video_file.unlink(missing_ok=True)
            shutil.rmtree(Path(".temp/99999"), ignore_errors=True)
    
    def test_nas_playlist_download_workflow(self, nas_test_directory: Path, nas_config: Config, nas_available: bool):
        """Test complete playlist download workflow on NAS."""
        if not nas_available:
            pytest.skip("NAS not available for testing")
        
        # Mock playlist info
        mock_playlist_info = {
            "id": "playlist_123",
            "title": "Test Playlist for NAS",
            "uploader": "Test Uploader",
            "entries": [
                {
                    "id": "video1",
                    "title": "Video 1",
                    "duration": 60,
                    "uploader": "Test Uploader"
                },
                {
                    "id": "video2", 
                    "title": "Video 2",
                    "duration": 90,
                    "uploader": "Test Uploader"
                }
            ]
        }
        
        with patch('yt_dlp.YoutubeDL') as mock_ydl:
            mock_instance = Mock()
            mock_ydl.return_value.__enter__.return_value = mock_instance
            
            # Mock playlist extraction
            mock_instance.extract_info.return_value = mock_playlist_info
            
            # Mock individual video downloads
            def mock_download(url):
                # Create test files in temp directory
                temp_dir = Path(".temp/88888/Test Playlist for NAS [playlist_123]")
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                if "video1" in url:
                    test_video = temp_dir / "Video 1 [video1].mp4"
                    test_video.write_bytes(b'simulated video 1 content')
                elif "video2" in url:
                    test_video = temp_dir / "Video 2 [video2].mp4"
                    test_video.write_bytes(b'simulated video 2 content')
                return True
            
            mock_instance.download.side_effect = mock_download
            
            # Create downloader
            downloader = VideoDownloadService(nas_config, verbose=True)
            
            # Test playlist download to NAS
            result = downloader.download_playlist_with_transcription(
                url="https://youtube.com/playlist?list=playlist_123",
                output_path=nas_test_directory,
                transcribe=True,
                continue_download=False
            )
            
            # Verify result
            assert result.success == True
            
            # Verify playlist directory exists on NAS
            nas_playlist_dir = nas_test_directory / "Test Playlist for NAS [playlist_123]"
            assert nas_playlist_dir.exists()
            assert nas_playlist_dir.is_dir()
            
            # Verify individual videos exist
            video1 = nas_playlist_dir / "Video 1 [video1].mp4"
            video2 = nas_playlist_dir / "Video 2 [video2].mp4"
            assert video1.exists()
            assert video2.exists()
            
            # Verify content
            assert video1.read_bytes() == b'simulated video 1 content'
            assert video2.read_bytes() == b'simulated video 2 content'
            
            # Cleanup
            shutil.rmtree(nas_playlist_dir, ignore_errors=True)
            shutil.rmtree(Path(".temp/88888"), ignore_errors=True)
    
    def test_nas_transcription_workflow(self, nas_test_directory: Path, nas_config: Config, nas_available: bool):
        """Test transcription workflow on NAS."""
        if not nas_available:
            pytest.skip("NAS not available for testing")
        
        # Create a test video file on NAS
        test_video = nas_test_directory / "transcription_test.mp4"
        test_video.write_bytes(b'simulated video content for transcription test')
        
        # Mock transcription service
        mock_transcription_data = {
            "language": "en",
            "language_name": "English",
            "duration": 120.0,
            "segments": [
                {
                    "id": 0,
                    "start": 0.0,
                    "end": 5.0,
                    "text": "Hello, this is a test transcription for NAS.",
                    "words": [
                        {"word": "Hello", "start": 0.0, "end": 0.5},
                        {"word": "this", "start": 0.5, "end": 1.0},
                        {"word": "is", "start": 1.0, "end": 1.5},
                        {"word": "a", "start": 1.5, "end": 2.0},
                        {"word": "test", "start": 2.0, "end": 2.5},
                        {"word": "transcription", "start": 2.5, "end": 3.0},
                        {"word": "for", "start": 3.0, "end": 3.5},
                        {"word": "NAS", "start": 3.5, "end": 4.0}
                    ]
                }
            ],
            "text": "Hello, this is a test transcription for NAS.",
            "processing_time": 10.0,
            "model_used": "whisper-base"
        }
        
        with patch('modules.video.transcription_service.TranscriptionService') as mock_transcription:
            mock_service = Mock()
            mock_transcription.return_value = mock_service
            mock_service.transcribe_video.return_value = mock_transcription_data
            
            # Create downloader
            downloader = VideoDownloadService(nas_config, verbose=True)
            
            # Test transcription
            result = downloader._transcribe_video(test_video)
            
            # Verify transcription result
            assert result is not None
            assert result["language"] == "en"
            assert result["text"] == "Hello, this is a test transcription for NAS."
            assert len(result["segments"]) == 1
            
            # Cleanup
            test_video.unlink(missing_ok=True)
    
    def test_nas_subtitle_embedding_workflow(self, nas_test_directory: Path, nas_config: Config, nas_available: bool):
        """Test subtitle embedding workflow on NAS."""
        if not nas_available:
            pytest.skip("NAS not available for testing")
        
        # Create a test video file on NAS
        test_video = nas_test_directory / "subtitle_test.mp4"
        test_video.write_bytes(b'simulated video content for subtitle test')
        
        # Mock ffmpeg for subtitle embedding
        with patch('subprocess.run') as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_result.stdout = "ffmpeg subtitle embedding output"
            mock_result.stderr = ""
            mock_run.return_value = mock_result
            
            # Create downloader
            downloader = VideoDownloadService(nas_config, verbose=True)
            
            # Test subtitle embedding
            result = downloader._embed_subtitles_into_video(
                test_video,
                {
                    "language": "en",
                    "language_name": "English",
                    "segments": [
                        {
                            "id": 0,
                            "start": 0.0,
                            "end": 5.0,
                            "text": "Test subtitle for NAS"
                        }
                    ]
                }
            )
            
            # Verify result
            assert result is not None
            assert result.exists()
            assert result.name.endswith("_with_subs.mp4")
            
            # Cleanup
            test_video.unlink(missing_ok=True)
            result.unlink(missing_ok=True)
    
    def test_nas_job_isolation_workflow(self, nas_test_directory: Path, nas_config: Config, nas_available: bool):
        """Test job isolation workflow on NAS."""
        if not nas_available:
            pytest.skip("NAS not available for testing")
        
        # Test multiple concurrent jobs
        job_ids = [11111, 22222, 33333]
        results = []
        
        for job_id in job_ids:
            # Create temp directory for job
            temp_dir = Path(f".temp/{job_id}")
            temp_dir.mkdir(parents=True, exist_ok=True)
            
            # Create test file in temp directory
            test_file = temp_dir / f"job_{job_id}_test.mp4"
            test_file.write_bytes(f'job {job_id} content'.encode())
            
            # Test move to NAS
            downloader = VideoDownloadService(nas_config, verbose=True)
            nas_dest = nas_test_directory / f"job_{job_id}_final.mp4"
            
            success = downloader._move_file_to_final_destination(test_file, nas_dest)
            results.append((job_id, success, nas_dest))
        
        # Verify all jobs completed successfully
        for job_id, success, nas_dest in results:
            assert success == True, f"Job {job_id} failed"
            assert nas_dest.exists(), f"Job {job_id} file not found on NAS"
            assert nas_dest.read_bytes() == f'job {job_id} content'.encode()
            
            # Cleanup
            nas_dest.unlink(missing_ok=True)
            shutil.rmtree(Path(f".temp/{job_id}"), ignore_errors=True)
    
    def test_nas_error_recovery_workflow(self, nas_test_directory: Path, nas_config: Config, nas_available: bool):
        """Test error recovery workflow on NAS."""
        if not nas_available:
            pytest.skip("NAS not available for testing")
        
        # Test with insufficient permissions
        read_only_dir = nas_test_directory / "read_only"
        read_only_dir.mkdir(exist_ok=True)
        
        try:
            # Make directory read-only (simulate permission error)
            read_only_dir.chmod(0o444)
            
            # Test move operation (should fail gracefully)
            temp_file = Path(tempfile.mktemp(suffix='.mp4'))
            temp_file.write_bytes(b'test content')
            
            downloader = VideoDownloadService(nas_config, verbose=True)
            nas_dest = read_only_dir / "test.mp4"
            
            success = downloader._move_file_to_final_destination(temp_file, nas_dest)
            
            # Should fail gracefully
            assert success == False
            assert not nas_dest.exists()
            
        finally:
            # Restore permissions and cleanup
            read_only_dir.chmod(0o755)
            temp_file.unlink(missing_ok=True)
            shutil.rmtree(read_only_dir, ignore_errors=True)
    
    def test_nas_large_file_workflow(self, nas_test_directory: Path, nas_config: Config, nas_available: bool):
        """Test large file handling workflow on NAS."""
        if not nas_available:
            pytest.skip("NAS not available for testing")
        
        # Create a large test file (10MB)
        large_content = b'\x00' * (10 * 1024 * 1024)
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as temp_file:
            temp_file.write(large_content)
            temp_file_path = Path(temp_file.name)
        
        try:
            # Test move operation with large file
            downloader = VideoDownloadService(nas_config, verbose=True)
            nas_dest = nas_test_directory / "large_file_test.mp4"
            
            start_time = time.time()
            success = downloader._move_file_to_final_destination(temp_file_path, nas_dest)
            move_time = time.time() - start_time
            
            # Verify success
            assert success == True
            assert nas_dest.exists()
            assert nas_dest.stat().st_size == len(large_content)
            
            # Log performance
            throughput_mbps = (len(large_content) / (1024 * 1024)) / move_time
            print(f"Large file move: {move_time:.3f}s, {throughput_mbps:.2f} MB/s")
            
            # Cleanup
            nas_dest.unlink(missing_ok=True)
            
        finally:
            # Cleanup temp file
            temp_file_path.unlink(missing_ok=True)
    
    def test_nas_workflow_performance(self, nas_test_directory: Path, nas_config: Config, nas_available: bool):
        """Test overall NAS workflow performance."""
        if not nas_available:
            pytest.skip("NAS not available for testing")
        
        # Test multiple file operations
        num_files = 20
        file_size = 1024 * 1024  # 1MB each
        
        start_time = time.time()
        
        # Create files
        test_files = []
        for i in range(num_files):
            test_file = nas_test_directory / f"perf_test_{i}.mp4"
            test_file.write_bytes(b'\x00' * file_size)
            test_files.append(test_file)
        
        create_time = time.time() - start_time
        
        # Read files
        start_time = time.time()
        for test_file in test_files:
            content = test_file.read_bytes()
            assert len(content) == file_size
        
        read_time = time.time() - start_time
        
        # Delete files
        start_time = time.time()
        for test_file in test_files:
            test_file.unlink()
        
        delete_time = time.time() - start_time
        
        # Log performance
        total_size_mb = (num_files * file_size) / (1024 * 1024)
        print(f"NAS workflow performance:")
        print(f"  Files: {num_files}")
        print(f"  Total size: {total_size_mb:.1f} MB")
        print(f"  Create time: {create_time:.3f}s ({total_size_mb/create_time:.2f} MB/s)")
        print(f"  Read time: {read_time:.3f}s ({total_size_mb/read_time:.2f} MB/s)")
        print(f"  Delete time: {delete_time:.3f}s")
        print(f"  Total time: {create_time + read_time + delete_time:.3f}s")
    
    def test_nas_workflow_monitoring(self, nas_test_directory: Path, nas_config: Config, nas_available: bool):
        """Test NAS workflow monitoring and metrics."""
        if not nas_available:
            pytest.skip("NAS not available for testing")
        
        # Test with monitoring
        operations = []
        
        def monitored_operation(operation_name: str, func, *args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                success = True
                error = None
            except Exception as e:
                result = None
                success = False
                error = str(e)
            
            end_time = time.time()
            operations.append({
                "name": operation_name,
                "start_time": start_time,
                "end_time": end_time,
                "duration": end_time - start_time,
                "success": success,
                "error": error,
                "result": result
            })
            return result
        
        # Perform monitored operations
        test_file = nas_test_directory / "monitoring_test.mp4"
        
        monitored_operation(
            "create_file",
            test_file.write_bytes,
            b'monitoring test content'
        )
        
        monitored_operation(
            "read_file",
            test_file.read_bytes
        )
        
        monitored_operation(
            "delete_file",
            test_file.unlink
        )
        
        # Analyze results
        total_operations = len(operations)
        successful_operations = sum(1 for op in operations if op["success"])
        total_time = sum(op["duration"] for op in operations)
        avg_time = total_time / total_operations if total_operations > 0 else 0
        
        print(f"NAS workflow monitoring:")
        print(f"  Total operations: {total_operations}")
        print(f"  Successful operations: {successful_operations}")
        print(f"  Success rate: {successful_operations/total_operations*100:.1f}%")
        print(f"  Total time: {total_time:.3f}s")
        print(f"  Average time: {avg_time:.3f}s")
        
        # Verify all operations succeeded
        assert successful_operations == total_operations, f"Some operations failed: {[op for op in operations if not op['success']]}"
