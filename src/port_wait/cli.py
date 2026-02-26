"""Click-based CLI interface for port-wait."""

import sys
import json
import click
from typing import List, Tuple
from .waiter import PortWaiter


@click.command()
@click.argument("targets", nargs=-1, required=True)
@click.option("--timeout", "-t", default=30.0, help="Maximum time to wait in seconds", type=float)
@click.option("--interval", "-i", default=0.5, help="Initial retry interval in seconds", type=float)
@click.option("--max-interval", default=5.0, help="Maximum retry interval in seconds", type=float)
@click.option("--connection-timeout", default=2.0, help="Connection timeout in seconds", type=float)
@click.option("--expected-status", default=200, help="Expected HTTP status code", type=int)
@click.option("--method", default="GET", help="HTTP method (GET/POST/HEAD)", type=click.Choice(["GET", "POST", "HEAD"]))
@click.option("--header", "-H", multiple=True, help="HTTP header (format: 'Key: Value')")
@click.option("--any", "any_mode", is_flag=True, help="Succeed if ANY target is ready (default: ALL)")
@click.option("--verbose", "-v", is_flag=True, help="Show retry attempts and connection status")
@click.option("--quiet", "-q", is_flag=True, help="Only output on failure")
@click.option("--json", "json_output", is_flag=True, help="Output results as JSON")
def main(targets: Tuple[str], timeout: float, interval: float, max_interval: float,
         connection_timeout: float, expected_status: int, method: str, header: Tuple[str],
         any_mode: bool, verbose: bool, quiet: bool, json_output: bool):
    """Wait for TCP ports or HTTP endpoints to become available.
    
    TARGETS can be:
    - TCP ports: host:port (e.g., localhost:5432, db:3306)
    - HTTP endpoints: http(s)://url (e.g., http://api:8080/health)
    
    Examples:
      port-wait localhost:5432
      port-wait http://api:8080/health --expected-status 200
      port-wait db:5432 redis:6379 --any
    """
    headers = {}
    for h in header:
        if ":" in h:
            key, value = h.split(":", 1)
            headers[key.strip()] = value.strip()

    waiter = PortWaiter(
        timeout=timeout,
        initial_interval=interval,
        max_interval=max_interval,
        connection_timeout=connection_timeout
    )

    kwargs = {
        "expected_status": expected_status,
        "method": method,
        "headers": headers if headers else None
    }

    if len(targets) == 1:
        result = waiter.wait_for_target(targets[0], verbose=verbose, **kwargs)
        results = [result]
    else:
        target_list: List[Tuple[str, dict]] = [(t, kwargs) for t in targets]
        results = waiter.wait_for_multiple(target_list, all_mode=not any_mode, verbose=verbose)

    all_success = all(r.success for r in results)
    any_success = any(r.success for r in results)
    success = any_success if any_mode else all_success

    if json_output:
        output = {
            "success": success,
            "mode": "any" if any_mode else "all",
            "results": [r.to_dict() for r in results]
        }
        print(json.dumps(output, indent=2))
    elif not quiet or not success:
        for result in results:
            status = "✓" if result.success else "✗"
            msg = f"{status} {result.target}"
            if verbose or not result.success:
                msg += f" (attempts: {result.attempts}, elapsed: {result.elapsed:.1f}s)"
            if result.error:
                msg += f" - {result.error}"
            print(msg)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()