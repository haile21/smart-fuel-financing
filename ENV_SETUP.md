# Environment Variables Setup Guide

## What is the .env file?

The `.env` file contains configuration settings for your application. It's used for local development and should **never** be committed to git (it's in `.gitignore`).

## Required Environment Variables

Create a `.env` file in the root directory with the following variables:

### 1. DATABASE_URL (Required)

**Format:** `postgresql://username:password@host:port/database_name`

**Examples:**

```env
# Default PostgreSQL setup (if using default postgres user)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fuel_finance

# Custom PostgreSQL user
DATABASE_URL=postgresql://fuel_user:your_password@localhost:5432/fuel_finance

# Remote PostgreSQL (if using cloud database)
DATABASE_URL=postgresql://user:pass@db.example.com:5432/fuel_finance

# Docker PostgreSQL (if running PostgreSQL in Docker)
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fuel_finance
```

**How to get your database URL:**
1. If using default PostgreSQL installation:
   - Username: `postgres` (or your PostgreSQL username)
   - Password: Your PostgreSQL password (default might be `postgres` or empty)
   - Host: `localhost`
   - Port: `5432` (default PostgreSQL port)
   - Database: `fuel_finance` (create this database first)

2. If using Docker:
   ```bash
   docker run --name fuel-postgres \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=fuel_finance \
     -p 5432:5432 \
     -d postgres:15
   ```
   Then use: `postgresql://postgres:postgres@localhost:5432/fuel_finance`

### 2. SECRET_KEY (Required)

**What it is:** A secret key used to sign JWT tokens. Must be kept secret!

**How to generate:**

**Windows (PowerShell):**
```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

**macOS/Linux:**
```bash
openssl rand -hex 32
```

**Python:**
```python
python -c "import secrets; print(secrets.token_hex(32))"
```

**Example:**
```env
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
```

⚠️ **Important:** Use a different SECRET_KEY for production!

### 3. ALGORITHM (Optional)

**Default:** `HS256`

**Options:** `HS256`, `HS384`, `HS512`

```env
ALGORITHM=HS256
```

### 4. ACCESS_TOKEN_EXPIRE_MINUTES (Optional)

**Default:** `10080` (7 days)

**Common values:**
- `60` = 1 hour
- `1440` = 1 day
- `10080` = 7 days
- `43200` = 30 days

```env
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

### 5. PORT (Optional)

**Default:** `8000`

Only needed if you want to run on a different port.

```env
PORT=8000
```

## Complete .env File Example

Create a file named `.env` in the root directory:

```env
# Database Configuration
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/fuel_finance

# JWT Secret Key (Generate a new one!)
SECRET_KEY=your-secret-key-change-in-production-use-env-var

# JWT Algorithm
ALGORITHM=HS256

# Token expiration (7 days)
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Server Port
PORT=8000
```

## Quick Setup

### Step 1: Copy the example file

**Windows:**
```cmd
copy .env.example .env
```

**macOS/Linux:**
```bash
cp .env.example .env
```

### Step 2: Edit .env file

Open `.env` in your text editor and update:

1. **DATABASE_URL** - Match your PostgreSQL setup
2. **SECRET_KEY** - Generate a new secure key (see above)

### Step 3: Verify

The application will automatically load these variables when it starts.

## Testing Your Configuration

After setting up `.env`, test it:

```bash
# Start the server
uvicorn app.main:app --reload

# Check health endpoint
curl http://localhost:8000/health
```

If you see `{"status": "healthy"}`, your configuration is working!

## Common Issues

### Issue: "Could not connect to database"

**Solution:**
1. Check PostgreSQL is running:
   ```bash
   # Windows
   pg_isready
   
   # macOS/Linux
   sudo systemctl status postgresql
   ```

2. Verify DATABASE_URL format:
   ```
   postgresql://username:password@host:port/database_name
   ```

3. Test connection:
   ```bash
   psql -U postgres -d fuel_finance
   ```

### Issue: "Invalid SECRET_KEY"

**Solution:**
- Generate a new SECRET_KEY using one of the methods above
- Make sure it's at least 32 characters long
- Don't use spaces or special characters that might cause issues

### Issue: "Environment variable not found"

**Solution:**
1. Make sure `.env` file is in the root directory (same level as `app/`)
2. Check file name is exactly `.env` (not `.env.txt` or `.env.example`)
3. Restart your server after changing `.env`

## Security Notes

⚠️ **Never commit .env to git!**

The `.env` file is already in `.gitignore`, but double-check:

```bash
# Check if .env is ignored
git check-ignore .env
```

If it returns `.env`, you're good!

## Production Environment Variables

For production (e.g., Render), set these in your hosting platform's environment variables section, not in a `.env` file.

See [DEPLOYMENT.md](DEPLOYMENT.md) for production setup.

