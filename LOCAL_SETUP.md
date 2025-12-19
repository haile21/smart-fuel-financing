# Local Development Setup Guide

This guide will help you set up and run the Smart Fuel Financing Backend locally.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.10+** (check with `python --version`)
- **PostgreSQL 12+** (check with `psql --version`)
- **Git** (for cloning the repository)

## Step-by-Step Setup

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd "smart fuel financing"
```

### 2. Create Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` in your terminal prompt when activated.

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Set Up PostgreSQL Database

#### Option A: Using PostgreSQL installed locally

1. **Start PostgreSQL service:**
   - Windows: Check Services or use `pg_ctl start`
   - macOS: `brew services start postgresql`
   - Linux: `sudo systemctl start postgresql`

2. **Create database:**
```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE fuel_finance;

# Create user (optional, if not using default postgres user)
CREATE USER fuel_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE fuel_finance TO fuel_user;

# Exit psql
\q
```

#### Option B: Using Docker (Recommended)

```bash
# Run PostgreSQL in Docker
docker run --name fuel-postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=fuel_finance \
  -p 5432:5432 \
  -d postgres:15

# Verify it's running
docker ps
```

### 5. Configure Environment Variables

1. **Copy the example environment file:**
```bash
# Windows
copy .env.example .env

# macOS/Linux
cp .env.example .env
```

2. **Edit `.env` file** with your database credentials:

```env
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fuel_finance
SECRET_KEY=your-secret-key-change-in-production-use-env-var
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
PORT=8000
```

**Generate a secure SECRET_KEY:**
```bash
# Windows (PowerShell)
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))

# macOS/Linux
openssl rand -hex 32
```

### 6. Initialize Alembic (Database Migrations)

If Alembic is not already initialized:

```bash
# Initialize Alembic
alembic init alembic

# This creates an alembic/ directory with configuration
```

**Configure `alembic.ini`:**
- Set `sqlalchemy.url` to your database URL (or leave it commented to use environment variable)

**Update `alembic/env.py`:**
- Import your models and Base
- Set `target_metadata = Base.metadata`

### 7. Create Database Tables

```bash
# Create initial migration (if models exist)
alembic revision --autogenerate -m "Initial migration"

# Apply migrations
alembic upgrade head
```

**If you get errors**, you may need to manually create the tables first. Check `app/models/entities.py` for all models.

### 8. Create Super Admin User

```bash
python scripts/create_super_admin.py
```

This will prompt you for:
- Username
- Phone number
- Password
- Email (optional)

### 9. Start the Development Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The `--reload` flag enables auto-reload on code changes.

### 10. Verify Installation

1. **Check server is running:**
   - Open browser: http://localhost:8000
   - Should see: `{"message": "Smart Fuel Financing API"}`

2. **Access API Documentation:**
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

3. **Test health endpoint:**
   - http://localhost:8000/health
   - Should return: `{"status": "healthy"}`

## Common Issues & Solutions

### Issue: `ModuleNotFoundError` or import errors

**Solution:**
```bash
# Make sure virtual environment is activated
# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: `psycopg2` installation fails

**Solution (Windows):**
```bash
# Install pre-compiled wheel
pip install psycopg2-binary
```

**Solution (macOS):**
```bash
# Install PostgreSQL development headers
brew install postgresql
pip install psycopg2-binary
```

### Issue: Database connection error

**Solution:**
1. Verify PostgreSQL is running:
   ```bash
   # Windows
   pg_isready
   
   # macOS/Linux
   sudo systemctl status postgresql
   ```

2. Check database URL in `.env`:
   ```
   DATABASE_URL=postgresql://username:password@localhost:5432/database_name
   ```

3. Test connection:
   ```bash
   psql -U postgres -d fuel_finance
   ```

### Issue: `alembic: command not found`

**Solution:**
```bash
# Make sure virtual environment is activated
pip install alembic
```

### Issue: Port 8000 already in use

**Solution:**
```bash
# Use a different port
uvicorn app.main:app --reload --port 8001

# Or find and kill the process using port 8000
# Windows
netstat -ano | findstr :8000
taskkill /PID <PID> /F

# macOS/Linux
lsof -ti:8000 | xargs kill
```

### Issue: Migration errors

**Solution:**
```bash
# Drop and recreate database (WARNING: Deletes all data!)
psql -U postgres -c "DROP DATABASE fuel_finance;"
psql -U postgres -c "CREATE DATABASE fuel_finance;"
alembic upgrade head
```

## Development Workflow

### Making Changes

1. **Create a new feature branch:**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes**

3. **Create migration (if database changes):**
   ```bash
   alembic revision --autogenerate -m "Description of changes"
   alembic upgrade head
   ```

4. **Test locally:**
   - Use Swagger UI at http://localhost:8000/docs
   - Test endpoints manually

5. **Commit changes:**
   ```bash
   git add .
   git commit -m "Description of changes"
   ```

### Testing API Endpoints

1. **Using Swagger UI** (Recommended):
   - Go to http://localhost:8000/docs
   - Click "Authorize" and enter your JWT token
   - Test endpoints interactively

2. **Using curl:**
   ```bash
   # Get OTP
   curl -X POST "http://localhost:8000/auth/otp/send" \
     -H "Content-Type: application/json" \
     -d '{"phone_number": "+251911234567"}'
   
   # Verify OTP and get token
   curl -X POST "http://localhost:8000/auth/otp/verify" \
     -H "Content-Type: application/json" \
     -d '{"phone_number": "+251911234567", "otp_code": "123456"}'
   ```

3. **Using Python requests:**
   ```python
   import requests
   
   response = requests.post(
       "http://localhost:8000/auth/otp/send",
       json={"phone_number": "+251911234567"}
   )
   print(response.json())
   ```

## Project Structure

```
smart fuel financing/
├── app/
│   ├── core/           # Configuration and security
│   ├── db/             # Database session
│   ├── models/         # SQLAlchemy models
│   ├── routers/        # API endpoints
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic
│   └── main.py         # FastAPI app entry point
├── alembic/            # Database migrations
├── scripts/            # Utility scripts
├── .env                # Environment variables (create this)
├── .env.example        # Example environment file
├── requirements.txt    # Python dependencies
└── README.md           # Project documentation
```

## Next Steps

1. ✅ Server running locally
2. ✅ Database connected
3. ✅ Super admin created
4. 📝 Explore API docs at http://localhost:8000/docs
5. 📝 Test endpoints
6. 📝 Start developing!

## Useful Commands

```bash
# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Run server with auto-reload
uvicorn app.main:app --reload

# Run server on specific port
uvicorn app.main:app --reload --port 8001

# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1

# Check migration status
alembic current
alembic history

# Deactivate virtual environment
deactivate
```

## Getting Help

- Check API documentation: http://localhost:8000/docs
- Review architecture: See `ARCHITECTURE.md`
- Check API structure: See `API_STRUCTURE.md`
- Deployment guide: See `DEPLOYMENT.md`

