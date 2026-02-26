"""Core logic for TCP port and HTTP health checking with retry/backoff."""

import socket
import time
import requests
from typing import Optional, Dict, List, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed


class WaitResult:
    def __init__(self, success: bool, target: str, attempts: int, elapsed: float, error: Optional[str] = None):
        self.success = success
        self.target = target
        self.attempts = attempts
        self.elapsed = elapsed
        self.error = error

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "target": self.target,
            "attempts": self.attempts,
            "elapsed_seconds": round(self.elapsed, 2),
            "error": self.error
        }


class PortWaiter:
    def __init__(self, timeout: float = 30.0, initial_interval: float = 0.5,
                 max_interval: float = 5.0, connection_timeout: float = 2.0):
        self.timeout = timeout
        self.initial_interval = initial_interval
        self.max_interval = max_interval
        self.connection_timeout = connection_timeout

    def check_tcp_port(self, host: str, port: int) -> bool:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.connection_timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            return result == 0
        except (socket.gaierror, socket.timeout, OSError):
            return False

    def check_http_endpoint(self, url: str, expected_status: int = 200,
                           method: str = "GET", headers: Optional[Dict[str, str]] = None) -> bool:
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=headers or {},
                timeout=self.connection_timeout,
                allow_redirects=True
            )
            return response.status_code == expected_status
        except (requests.RequestException, Exception):
            return False

    def wait_for_target(self, target: str, verbose: bool = False, **kwargs) -> WaitResult:
        start_time = time.time()
        attempts = 0
        interval = self.initial_interval

        while time.time() - start_time < self.timeout:
            attempts += 1
            
            if target.startswith("http://") or target.startswith("https://"):
                success = self.check_http_endpoint(
                    target,
                    expected_status=kwargs.get("expected_status", 200),
                    method=kwargs.get("method", "GET"),
                    headers=kwargs.get("headers")
                )
            else:
                try:
                    host, port = target.rsplit(":", 1)
                    success = self.check_tcp_port(host, int(port))
                except ValueError:
                    return WaitResult(False, target, attempts, time.time() - start_time,
                                    "Invalid target format. Use host:port or http(s)://url")

            if success:
                return WaitResult(True, target, attempts, time.time() - start_time)

            if verbose:
                print(f"Attempt {attempts}: {target} not ready, retrying in {interval:.1f}s...")

            time.sleep(interval)
            interval = min(interval * 2, self.max_interval)

        return WaitResult(False, target, attempts, time.time() - start_time,
                        f"Timeout after {self.timeout}s")

    def wait_for_multiple(self, targets: List[Tuple[str, dict]], all_mode: bool = True,
                         verbose: bool = False) -> List[WaitResult]:
        with ThreadPoolExecutor(max_workers=len(targets)) as executor:
            futures = {
                executor.submit(self.wait_for_target, target, verbose, **kwargs): target
                for target, kwargs in targets
            }
            
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
                
                if not all_mode and result.success:
                    executor.shutdown(wait=False, cancel_futures=True)
                    return results
            
            return results