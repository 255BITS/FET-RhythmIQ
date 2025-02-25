# RhythmIQ Development Guide

## Commands
- Run app: `python main.py` (runs on port 8257)
- Start with Docker: `docker-compose up`
- Build for deployment: `python deploy/build.py [service_pattern]`
- Deploy: `python deploy/deploy.py {project} --key {key_path}`

## Code Style
- **Import Order**: stdlib → third-party → local (not strictly enforced)
- **Naming**: snake_case for functions/variables, PascalCase for classes
- **Types**: Use type hints for parameters, Optional[] for nullable values
- **Formatting**: 4-space indentation, 100-char line limit
- **Error Handling**: Use try/except with specific exceptions and logging
- **Database**: Use asyncpg with connection pooling pattern
- **Async**: All route handlers and DB functions should be async

## Architecture
- Quart for async web framework
- Models with class-based design and static factory methods
- Environment variables for configuration with sensible defaults
- HTMX for lightweight frontend interactivity

## Project Structure
- `main.py`: App entry point and routes
- `models.py`: Database models and queries
- `auth_routes.py`: Authentication endpoints
- `templates/`: Jinja2 HTML templates
- `static/`: CSS/JS/images
- `deploy/`: Deployment scripts