# port-wait

Block script execution until TCP ports open or HTTP endpoints return healthy responses

## Features

- Wait for single or multiple TCP ports to become available with configurable timeout
- HTTP/HTTPS health check support with expected status code validation (default 200)
- Exponential backoff retry strategy with configurable initial interval and max attempts
- Parallel monitoring of multiple ports/endpoints with all-or-any success modes
- Verbose output mode showing retry attempts and connection status
- Exit code 0 on success, 1 on timeout for easy shell script integration
- Support for custom HTTP headers and request methods (GET/POST/HEAD)
- Connection timeout separate from overall wait timeout
- Quiet mode for CI environments (only output on failure)
- JSON output mode for programmatic consumption

## How to Use

Use this project when you need to:

- Quickly solve problems related to port-wait
- Integrate python functionality into your workflow
- Learn how python handles common patterns with click

## Installation

```bash
# Clone the repository
git clone https://github.com/KurtWeston/port-wait.git
cd port-wait

# Install dependencies
pip install -r requirements.txt
```

## Usage

```bash
python main.py
```

## Built With

- python using click

## Dependencies

- `click`
- `requests`
- `pytest`
- `pytest-timeout`

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
