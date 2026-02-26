"""Tests for CLI interface."""

import pytest
import json
from click.testing import CliRunner
from unittest.mock import patch, Mock
from port_wait.cli import main
from port_wait.waiter import WaitResult


class TestCLI:
    def setup_method(self):
        self.runner = CliRunner()

    @patch('port_wait.cli.PortWaiter')
    def test_single_target_success(self, mock_waiter_class):
        mock_waiter = Mock()
        mock_waiter.wait_for_target.return_value = WaitResult(True, "localhost:5432", 1, 0.5)
        mock_waiter_class.return_value = mock_waiter
        
        result = self.runner.invoke(main, ['localhost:5432'])
        
        assert result.exit_code == 0
        mock_waiter.wait_for_target.assert_called_once()

    @patch('port_wait.cli.PortWaiter')
    def test_single_target_failure(self, mock_waiter_class):
        mock_waiter = Mock()
        mock_waiter.wait_for_target.return_value = WaitResult(False, "localhost:9999", 5, 30.0, "Timeout")
        mock_waiter_class.return_value = mock_waiter
        
        result = self.runner.invoke(main, ['localhost:9999'])
        
        assert result.exit_code == 1

    @patch('port_wait.cli.PortWaiter')
    def test_multiple_targets_all_mode(self, mock_waiter_class):
        mock_waiter = Mock()
        mock_waiter.wait_for_multiple.return_value = [
            WaitResult(True, "localhost:5432", 1, 0.5),
            WaitResult(True, "localhost:6379", 1, 0.5)
        ]
        mock_waiter_class.return_value = mock_waiter
        
        result = self.runner.invoke(main, ['localhost:5432', 'localhost:6379'])
        
        assert result.exit_code == 0
        mock_waiter.wait_for_multiple.assert_called_once()

    @patch('port_wait.cli.PortWaiter')
    def test_multiple_targets_any_mode(self, mock_waiter_class):
        mock_waiter = Mock()
        mock_waiter.wait_for_multiple.return_value = [
            WaitResult(True, "localhost:5432", 1, 0.5),
            WaitResult(False, "localhost:9999", 5, 30.0, "Timeout")
        ]
        mock_waiter_class.return_value = mock_waiter
        
        result = self.runner.invoke(main, ['localhost:5432', 'localhost:9999', '--any'])
        
        assert result.exit_code == 0

    @patch('port_wait.cli.PortWaiter')
    def test_json_output(self, mock_waiter_class):
        mock_waiter = Mock()
        mock_waiter.wait_for_target.return_value = WaitResult(True, "localhost:5432", 1, 0.5)
        mock_waiter_class.return_value = mock_waiter
        
        result = self.runner.invoke(main, ['localhost:5432', '--json'])
        
        assert result.exit_code == 0
        output = json.loads(result.output)
        assert output["success"] is True
        assert "results" in output

    @patch('port_wait.cli.PortWaiter')
    def test_custom_timeout(self, mock_waiter_class):
        mock_waiter = Mock()
        mock_waiter.wait_for_target.return_value = WaitResult(True, "localhost:5432", 1, 0.5)
        mock_waiter_class.return_value = mock_waiter
        
        result = self.runner.invoke(main, ['localhost:5432', '--timeout', '60'])
        
        assert result.exit_code == 0
        mock_waiter_class.assert_called_once()
        call_kwargs = mock_waiter_class.call_args[1]
        assert call_kwargs['timeout'] == 60.0

    @patch('port_wait.cli.PortWaiter')
    def test_http_endpoint_with_status(self, mock_waiter_class):
        mock_waiter = Mock()
        mock_waiter.wait_for_target.return_value = WaitResult(True, "http://api:8080/health", 1, 0.5)
        mock_waiter_class.return_value = mock_waiter
        
        result = self.runner.invoke(main, ['http://api:8080/health', '--expected-status', '200'])
        
        assert result.exit_code == 0
        call_args = mock_waiter.wait_for_target.call_args
        assert call_args[1]['expected_status'] == 200

    @patch('port_wait.cli.PortWaiter')
    def test_http_custom_method(self, mock_waiter_class):
        mock_waiter = Mock()
        mock_waiter.wait_for_target.return_value = WaitResult(True, "http://api:8080/health", 1, 0.5)
        mock_waiter_class.return_value = mock_waiter
        
        result = self.runner.invoke(main, ['http://api:8080/health', '--method', 'POST'])
        
        assert result.exit_code == 0
        call_args = mock_waiter.wait_for_target.call_args
        assert call_args[1]['method'] == 'POST'

    @patch('port_wait.cli.PortWaiter')
    def test_http_custom_headers(self, mock_waiter_class):
        mock_waiter = Mock()
        mock_waiter.wait_for_target.return_value = WaitResult(True, "http://api:8080/health", 1, 0.5)
        mock_waiter_class.return_value = mock_waiter
        
        result = self.runner.invoke(main, [
            'http://api:8080/health',
            '-H', 'Authorization: Bearer token123',
            '-H', 'X-Custom: value'
        ])
        
        assert result.exit_code == 0
        call_args = mock_waiter.wait_for_target.call_args
        headers = call_args[1]['headers']
        assert headers['Authorization'] == 'Bearer token123'
        assert headers['X-Custom'] == 'value'

    def test_no_targets_error(self):
        result = self.runner.invoke(main, [])
        assert result.exit_code != 0

    @patch('port_wait.cli.PortWaiter')
    def test_verbose_mode(self, mock_waiter_class):
        mock_waiter = Mock()
        mock_waiter.wait_for_target.return_value = WaitResult(True, "localhost:5432", 1, 0.5)
        mock_waiter_class.return_value = mock_waiter
        
        result = self.runner.invoke(main, ['localhost:5432', '--verbose'])
        
        assert result.exit_code == 0
        call_args = mock_waiter.wait_for_target.call_args
        assert call_args[1]['verbose'] is True

    @patch('port_wait.cli.PortWaiter')
    def test_quiet_mode_success(self, mock_waiter_class):
        mock_waiter = Mock()
        mock_waiter.wait_for_target.return_value = WaitResult(True, "localhost:5432", 1, 0.5)
        mock_waiter_class.return_value = mock_waiter
        
        result = self.runner.invoke(main, ['localhost:5432', '--quiet'])
        
        assert result.exit_code == 0
        assert result.output == ''

    @patch('port_wait.cli.PortWaiter')
    def test_quiet_mode_failure(self, mock_waiter_class):
        mock_waiter = Mock()
        mock_waiter.wait_for_target.return_value = WaitResult(False, "localhost:9999", 5, 30.0, "Timeout")
        mock_waiter_class.return_value = mock_waiter
        
        result = self.runner.invoke(main, ['localhost:9999', '--quiet'])
        
        assert result.exit_code == 1
        assert len(result.output) > 0
