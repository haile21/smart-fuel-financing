# Deployment Guide for Render

## Prerequisites

1. Render account (https://render.com)
2. PostgreSQL database (can be created on Render)
3. Environment variables configured

## Step 1: Prepare Database

### Create PostgreSQL Database on Render

1. Go to Render Dashboard
2. Click "New +" → "PostgreSQL"
3. Configure:
   - Name: `fuel-financing-db`
   - Database: `fuel_finance`
   - User: Auto-generated
   - Password: Auto-generated (save this!)
4. Copy the **Internal Database URL** (for Render services) or **External Database URL** (for local development)

## Step 2: Set Up Web Service

### Create Web Service

1. Go to Render Dashboard
2. Click "New +" → "Web Service"
3. Connect your Git repository (GitHub/GitLab/Bitbucket)
4. Configure:
   - **Name**: `fuel-financing-api`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Health Check Path**: `/docs` (FastAPI docs)

### Environment Variables

Add these environment variables in Render Dashboard:

```bash
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=your-secret-key-change-this-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

**Important**: 
- Use the **Internal Database URL** from your PostgreSQL service
- Generate a strong `SECRET_KEY` (use: `openssl rand -hex 32`)

## Step 3: Database Migration

### Option 1: Run Migration via Render Shell

1. Go to your web service
2. Click "Shell"
3. Run:
```bash
cd /opt/render/project/src
alembic upgrade head
```

### Option 2: Create Initial Migration

If you haven't created migrations yet:

```bash
# Locally
alembic init alembic
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```

Then commit and push to trigger Render deployment.

## Step 4: Create Initial Super Admin

After deployment, create the first super admin user:

### Via API (after deployment)

```bash
# First, create super admin via direct database insert or API
# You'll need to temporarily allow user creation without auth

# Or use Render Shell to run Python script:
python scripts/create_super_admin.py
```

### Create Script: `scripts/create_super_admin.py`

```python
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import SessionLocal
from app.services.user_service import UserService
from app.models.entities import UserRole

def create_super_admin():
    db = SessionLocal()
    try:
        service = UserService(db)
        admin = service.create_user(
            role=UserRole.SUPER_ADMIN,
            email="admin@system.com",
            username="superadmin",
            password="ChangeThisPassword123!",
            full_name="System Administrator",
            created_by_user_id=None,
        )
        print(f"Super admin created: {admin.id}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_super_admin()
```

## Step 5: Verify Deployment

1. Check service logs in Render Dashboard
2. Visit `https://your-service.onrender.com/docs` - Should show FastAPI docs
3. Test health endpoint: `GET /docs`

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@host:5432/db` |
| `SECRET_KEY` | JWT secret key | `your-secret-key-here` |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiration | `10080` (7 days) |

## Render-Specific Configuration

### Health Check

Render automatically checks `/docs` endpoint. FastAPI provides this by default.

### Port Configuration

Render sets `$PORT` environment variable. Our start command uses it: `--port $PORT`

### Build & Deploy

Render automatically:
1. Detects Python project
2. Runs `pip install -r requirements.txt`
3. Starts service with `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

## Troubleshooting

### Database Connection Issues

- Verify `DATABASE_URL` uses **Internal Database URL** (for Render services)
- Check database is running
- Verify credentials are correct

### Migration Errors

- Run migrations manually via Render Shell
- Check Alembic version table exists

### Import Errors

- Verify all dependencies in `requirements.txt`
- Check Python version matches `runtime.txt`

### Port Issues

- Ensure start command uses `$PORT` variable
- Check service is listening on `0.0.0.0` not `127.0.0.1`

## Post-Deployment Checklist

- [ ] Database migrations completed
- [ ] Super admin user created
- [ ] Environment variables set
- [ ] Health check passing (`/docs` accessible)
- [ ] Test API endpoints
- [ ] Update CORS settings if needed (for frontend)
- [ ] Set up monitoring/alerts

## Additional Configuration

### CORS (if needed for frontend)

Add to `app/main.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Static Files (if needed)

Render can serve static files. Configure in `render.yaml` or use a CDN.

## Monitoring

- Render provides built-in logs and metrics
- Check service logs for errors
- Monitor database connections
- Set up alerts for service downtime

## Scaling

- Render auto-scales based on traffic
- Upgrade plan for higher limits
- Consider database connection pooling for high traffic

