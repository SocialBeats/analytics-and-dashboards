# FastAPI MongoDB Template

A production-ready template for building REST APIs with **FastAPI** and **MongoDB**. This template follows best practices for project structure, includes comprehensive testing, Docker support, and is ready for deployment.

## Features

- **FastAPI Framework**: Modern, fast, async web framework
- **MongoDB Integration**: Async MongoDB driver (Motor) with connection pooling
- **Structured Architecture**: Clean separation of concerns (endpoints, services, models, schemas)
- **Configuration Management**: Environment-based configuration with Pydantic Settings
- **Error Handling**: Centralized exception handling with custom exceptions
- **Logging**: Structured JSON logging with configurable levels
- **Testing**: Comprehensive test suite with pytest and pytest-asyncio
- **Docker Support**: Multi-stage Dockerfile and docker-compose setup
- **Code Quality**: Pre-commit hooks, Black, Ruff, isort, and mypy
- **API Documentation**: Auto-generated OpenAPI (Swagger) and ReDoc documentation
- **CORS Support**: Configurable CORS middleware
- **Health Checks**: Database connectivity health check endpoint

## Project Structure

```text
.
├── app/
│   ├── __init__.py
│   ├── core/                  # Core functionality
│   │   ├── config.py          # Configuration management
│   │   ├── logging.py         # Logging setup
│   │   └── exceptions.py      # Custom exceptions
│   ├── database/              # Database configuration
│   │   ├── config.py          # MongoDB connection
│   │   └── __init__.py
│   ├── endpoints/             # API endpoints (routes)
│   │   ├── health.py          # Health check endpoint
│   │   └── items.py           # Item CRUD endpoints
│   ├── models/                # Database models
│   │   ├── item.py            # Item model
│   │   └── __init__.py
│   ├── schemas/               # Pydantic schemas (request/response)
│   │   ├── item.py            # Item schemas
│   │   └── __init__.py
│   └── services/              # Business logic layer
│       ├── item_service.py    # Item business logic
│       └── __init__.py
├── tests/                     # Test suite
│   ├── conftest.py            # Pytest fixtures
│   ├── test_health.py         # Health endpoint tests
│   └── test_items.py          # Item endpoint tests
├── main.py                    # Application entry point
├── requirements.txt           # Production dependencies
├── requirements-dev.txt       # Development dependencies
├── .env.example               # Environment variables template
├── Dockerfile                 # Docker image definition
├── docker-compose.yml         # Docker compose configuration
├── pyproject.toml             # Python project configuration
├── pytest.ini                 # Pytest configuration
├── .pre-commit-config.yaml    # Pre-commit hooks
└── README.md                  # This file
```

## Requirements

- **Python 3.11+**
- **MongoDB 7.0+**
- **Docker & Docker Compose** (optional, for containerized deployment)

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd analytics-and-dashboards

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
nano .env
```

**Key environment variables:**

- `MONGODB_URL`: MongoDB connection string
- `MONGODB_DB_NAME`: Database name
- `ENVIRONMENT`: development/staging/production
- `LOG_LEVEL`: DEBUG/INFO/WARNING/ERROR/CRITICAL

### 3. Run Locally

**Option A: With local MongoDB**

```bash

# Start MongoDB (if not already running)
mongod --dbpath /path/to/data

# Run the application
uvicorn main:app --reload
```

**Option B: With Docker Compose** (Recommended)

```bash

# Start all services (API + MongoDB)
docker-compose up

# Or run in detached mode
docker-compose up -d

# Include Mongo Express (Web UI for MongoDB)
docker-compose --profile dev up
```

### 4. Access the API

- **API Documentation (Swagger)**: http://localhost:8000/docs
- **Alternative Documentation (ReDoc)**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/v1/health
- **Mongo Express** (if using dev profile): http://localhost:8081

## API Endpoints

### Health

- `GET /api/v1/health` - Health check with database connectivity status

### Items (CRUD Example)

- `GET /api/v1/items` - List all items (with pagination)
- `GET /api/v1/items/{item_id}` - Get specific item
- `POST /api/v1/items` - Create new item
- `PUT /api/v1/items/{item_id}` - Update existing item
- `DELETE /api/v1/items/{item_id}` - Delete item

## Development

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Code Quality

```bash
# Format code with Black
black app/ tests/

# Sort imports with isort
isort app/ tests/

# Lint with Ruff
ruff check app/ tests/

# Type check with mypy
mypy app/
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_items.py

# Run with verbose output
pytest -v
```

## Docker Deployment

### Build and Run

```bash
# Build image
docker build -t fastapi-mongodb-template .

# Run container
docker run -p 8000:8000 \
  -e MONGODB_URL=mongodb://host.docker.internal:27017 \
  fastapi-mongodb-template
```

### Docker Compose Services

```yaml
- api: FastAPI application (port 8000)
- mongodb: MongoDB database (port 27017)
- mongo-express: Web UI for MongoDB (port 8081) [dev profile only]
```

**Commands:**

``` bash
# Start services
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Remove volumes (clears database)
docker-compose down -v
```

## Production Deployment

### Environment Configuration

For production, ensure you set:

```bash
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
MONGODB_URL=<production-mongodb-url>
SECRET_KEY=<strong-random-secret>
CORS_ORIGINS=https://your-domain.com
```

### Security Considerations

1. **Never commit `.env` files** to version control
2. **Use strong SECRET_KEY** for production
3. **Configure CORS** appropriately for your domain
4. **Use MongoDB authentication** in production
5. **Enable SSL/TLS** for MongoDB connections
6. **Use environment secrets** management (AWS Secrets Manager, Azure Key Vault, etc.)

### Deployment Options

- **Docker**: Use the provided Dockerfile
- **Cloud Platforms**: AWS ECS, Google Cloud Run, Azure Container Instances
- **Kubernetes**: Create deployment manifests
- **Traditional VPS**: Use systemd service or supervisor

## Extending the Template

### Adding New Endpoints

1. **Create schema** in `app/schemas/`
2. **Create model** in `app/models/`
3. **Create service** in `app/services/`
4. **Create endpoint** in `app/endpoints/`
5. **Register router** in `main.py`
6. **Add tests** in `tests/`

### Example: Adding a User Resource

```python
# 1. app/schemas/user.py
class UserCreate(BaseModel):
    name: str
    email: str

# 2. app/services/user_service.py
class UserService:
    async def create(self, user_data: UserCreate):
        # Business logic here
        pass

# 3. app/endpoints/users.py
router = APIRouter()

@router.post("/users")
async def create_user(user: UserCreate, service: UserService = Depends()):
    return await service.create(user)

# 4. main.py
from app.endpoints import users
app.include_router(users.router, prefix="/api/v1", tags=["users"])
```

## Common Issues

### MongoDB Connection Failed

- Ensure MongoDB is running
- Check `MONGODB_URL` in `.env`
- Verify network connectivity

### Import Errors

- Ensure virtual environment is activated
- Install all dependencies: `pip install -r requirements.txt`

### Tests Failing

- Ensure test database is accessible
- Check MongoDB is running
- Review test configuration in `pytest.ini`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and code quality checks
5. Submit a pull request

## License

This template is provided as-is for use in your projects.

## Support

For issues, questions, or contributions, please refer to the project's issue tracker.

---

**Built with FastAPI & MongoDB** 🚀
