"""Tests for core waiter functionality."""

import pytest
import socket
import time
from unittest.mock import patch, Mock, MagicMock
from port_wait.waiter import PortWaiter, WaitResult


class TestWaitResult:
    def test_to_dict_success(self):
        result = WaitResult(True, "localhost:5432", 3, 1.5)
        data = result.to_dict()
        assert data["success"] is True
        assert data["target"] == "localhost:5432"
        assert data["attempts"] == 3
        assert data["elapsed_seconds"] == 1.5
        assert data["error"] is None

    def test_to_dict_with_error(self):
        result = WaitResult(False, "localhost:9999", 5, 30.0, "Connection refused")
        data = result.to_dict()
        assert data["success"] is False
        assert data["error"] == "Connection refused"


class TestPortWaiter:
    def test_init_defaults(self):
        waiter = PortWaiter()
        assert waiter.timeout == 30.0
        assert waiter.initial_interval == 0.5
        assert waiter.max_interval == 5.0
        assert waiter.connection_timeout == 2.0

    def test_init_custom_values(self):
        waiter = PortWaiter(timeout=60.0, initial_interval=1.0, max_interval=10.0, connection_timeout=5.0)
        assert waiter.timeout == 60.0
        assert waiter.initial_interval == 1.0
        assert waiter.max_interval == 10.0
        assert waiter.connection_timeout == 5.0

    @patch('socket.socket')
    def test_check_tcp_port_success(self, mock_socket):
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0
        mock_socket.return_value = mock_sock
        
        waiter = PortWaiter()
        result = waiter.check_tcp_port("localhost", 5432)
        
        assert result is True
        mock_sock.connect_ex.assert_called_once_with(("localhost", 5432))
        mock_sock.close.assert_called_once()

    @patch('socket.socket')
    def test_check_tcp_port_failure(self, mock_socket):
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 1
        mock_socket.return_value = mock_sock
        
        waiter = PortWaiter()
        result = waiter.check_tcp_port("localhost", 9999)
        
        assert result is False

    @patch('socket.socket')
    def test_check_tcp_port_exception(self, mock_socket):
        mock_socket.side_effect = socket.gaierror("Name resolution failed")
        
        waiter = PortWaiter()
        result = waiter.check_tcp_port("invalid-host", 5432)
        
        assert result is False

    @patch('requests.request')
    def test_check_http_endpoint_success(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        waiter = PortWaiter()
        result = waiter.check_http_endpoint("http://localhost:8080/health")
        
        assert result is True
        mock_request.assert_called_once()

    @patch('requests.request')
    def test_check_http_endpoint_wrong_status(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 500
        mock_request.return_value = mock_response
        
        waiter = PortWaiter()
        result = waiter.check_http_endpoint("http://localhost:8080/health", expected_status=200)
        
        assert result is False

    @patch('requests.request')
    def test_check_http_endpoint_custom_status(self, mock_request):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_request.return_value = mock_response
        
        waiter = PortWaiter()
        result = waiter.check_http_endpoint("http://api/resource", expected_status=201, method="POST")
        
        assert result is True

    @patch('requests.request')
    def test_check_http_endpoint_exception(self, mock_request):
        mock_request.side_effect = Exception("Connection error")
        
        waiter = PortWaiter()
        result = waiter.check_http_endpoint("http://localhost:8080/health")
        
        assert result is False

    @patch.object(PortWaiter, 'check_tcp_port')
    def test_wait_for_target_tcp_success(self, mock_check):
        mock_check.return_value = True
        
        waiter = PortWaiter(timeout=5.0)
        result = waiter.wait_for_target("localhost:5432")
        
        assert result.success is True
        assert result.target == "localhost:5432"
        assert result.attempts >= 1
        assert result.error is None

    @patch.object(PortWaiter, 'check_tcp_port')
    def test_wait_for_target_tcp_timeout(self, mock_check):
        mock_check.return_value = False
        
        waiter = PortWaiter(timeout=1.0, initial_interval=0.2)
        result = waiter.wait_for_target("localhost:9999")
        
        assert result.success is False
        assert result.attempts > 1
        assert "Timeout" in result.error

    @patch.object(PortWaiter, 'check_http_endpoint')
    def test_wait_for_target_http_success(self, mock_check):
        mock_check.return_value = True
        
        waiter = PortWaiter(timeout=5.0)
        result = waiter.wait_for_target("http://localhost:8080/health")
        
        assert result.success is True
        assert result.target == "http://localhost:8080/health"

    def test_wait_for_target_invalid_format(self):
        waiter = PortWaiter(timeout=1.0)
        result = waiter.wait_for_target("invalid-target")
        
        assert result.success is False
        assert "Invalid target format" in result.error

    @patch.object(PortWaiter, 'wait_for_target')
    def test_wait_for_multiple_all_mode_success(self, mock_wait):
        mock_wait.side_effect = [
            WaitResult(True, "localhost:5432", 1, 0.5),
            WaitResult(True, "localhost:6379", 1, 0.5)
        ]
        
        waiter = PortWaiter()
        targets = [("localhost:5432", {}), ("localhost:6379", {})]
        results = waiter.wait_for_multiple(targets, all_mode=True)
        
        assert len(results) == 2
        assert all(r.success for r in results)

    @patch.object(PortWaiter, 'wait_for_target')
    def test_wait_for_multiple_any_mode_partial_success(self, mock_wait):
        mock_wait.side_effect = [
            WaitResult(True, "localhost:5432", 1, 0.5),
            WaitResult(False, "localhost:9999", 5, 30.0, "Timeout")
        ]
        
        waiter = PortWaiter()
        targets = [("localhost:5432", {}), ("localhost:9999", {})]
        results = waiter.wait_for_multiple(targets, all_mode=False)
        
        assert len(results) == 2
        assert any(r.success for r in results)
