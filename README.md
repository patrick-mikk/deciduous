# UofT Course Dashboard

A comprehensive academic planning tool for University of Toronto students, featuring course search, transcript management, and degree progress tracking.

## Quick Start

```bash
# Install dependencies
pip install -r config/requirements.txt

# Run the application (Option 1: Using startup script)
python scripts/start.py

# Run the application (Option 2: Windows batch file)
scripts/start.bat

# Run the application (Option 3: Direct execution)
cd src && python main.py
```

## Project Structure

```
├── src/           # Main application code
├── docs/          # Documentation and guides
├── legacy/        # Original modules (no longer in active use)
├── data/          # Database files
├── config/        # Configuration files
├── tests/         # Test suite (planned)
├── assets/        # Resources (planned)
└── scripts/       # Development scripts (planned)
```

## Documentation

- **[Architecture Guide](docs/ARCHITECTURE.md)** - System architecture and design
- **[Developer Guide](docs/DEVELOPER_GUIDE.md)** - Setup and development workflow
- **[User Guide](docs/README.md)** - Feature overview and usage instructions
- **[Master Plan](docs/master_plan.md)** - Future development roadmap

## Features

- **Course Search**: Real-time search of UofT Academic Calendar
- **Transcript Management**: GPA calculation and academic tracking
- **Degree Progress**: Requirements tracking and breadth categories
- **Course Planning**: Future course planning and scheduling
- **Analytics**: Academic performance analysis and reporting

## Support

See the [Developer Guide](docs/DEVELOPER_GUIDE.md) for troubleshooting and setup instructions.

---

**Note**: This tool is for educational use. Please respect the University of Toronto's terms of service.