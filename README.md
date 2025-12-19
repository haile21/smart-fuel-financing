# Smart Fuel Financing Backend

A comprehensive FastAPI backend for a fuel financing system that acts as a clearinghouse between Banks, Drivers/Agencies, and Fuel Stations.

## Features

- 🔐 **Role-Based Access Control**: SUPER_ADMIN, BANK_ADMIN, DRIVER, AGENT, MERCHANT
- 💳 **Credit Management**: Credit lines, risk scoring, loan management
- 📱 **QR Code Transactions**: Two-phase commit (Hold & Capture) for fuel transactions
- 🏦 **Bank Portal**: Approve/reject credit line requests
- 📊 **Credit Scoring**: AI-powered risk assessment
- 🔔 **Notifications**: SMS, email, push, in-app notifications
- 💰 **Payment Processing**: Payment gateway integration ready
- 📍 **Station Management**: Real-time fuel availability tracking

## Tech Stack

- **Framework**: FastAPI 0.115.0
- **Database**: PostgreSQL (SQLAlchemy 2.0)
- **Authentication**: JWT tokens, OTP
- **Deployment**: Render-ready

## Quick Start

### Local Development

1. **Clone repository**
```bash
git clone <repository-url>
cd smart-fuel-financing
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your database URL and secret key
```

5. **Run database migrations**
```bash
alembic upgrade head
```

6. **Start server**
```bash
uvicorn app.main:app --reload
```

7. **Access API docs**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Deployment to Render

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed deployment instructions.

### Quick Deploy Steps

1. Push code to GitHub/GitLab
2. Create PostgreSQL database on Render
3. Create Web Service on Render
4. Set environment variables:
   - `DATABASE_URL` (from PostgreSQL service)
   - `SECRET_KEY` (generate strong key)
   - `ALGORITHM=HS256`
   - `ACCESS_TOKEN_EXPIRE_MINUTES=10080`
5. Deploy and run migrations
6. Create super admin user

## API Structure

See [API_STRUCTURE.md](API_STRUCTURE.md) for complete endpoint documentation.

### Main Endpoints

- **Auth**: `/auth/otp/send`, `/auth/otp/verify`
- **Drivers**: `/drivers/*`
- **Stations**: `/stations/*`
- **Agents**: `/agents/*`
- **Merchants**: `/merchants/*`
- **Loans**: `/loans/*`
- **Transactions**: `/transactions/*`
- **Admin**: `/admin/*`

## Role Management

See [ROLE_MANAGEMENT.md](ROLE_MANAGEMENT.md) for role-based access control details.

### Roles

- **SUPER_ADMIN**: System owner, full access
- **BANK_ADMIN**: Bank administrator
- **DRIVER**: End user/driver
- **AGENT**: Onboards fuel stations
- **MERCHANT**: Provides fuel services

## Database Schema

Key entities:
- `User` - User accounts with roles
- `Driver` - Driver profiles
- `Bank` - Financial institutions
- `Merchant` - Fuel station operators
- `FuelStation` - Physical fuel stations
- `CreditLine` - Credit lines with optimistic locking
- `Transaction` - Fuel transactions (two-phase commit)
- `Loan` - Loan records
- `CreditLineRequest` - Credit line requests

## Environment Variables

```bash
DATABASE_URL=postgresql://user:password@host:port/database
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=10080
```

## Project Structure

```
app/
├── core/           # Core configuration and security
├── db/             # Database session and base
├── models/         # SQLAlchemy models
├── routers/        # API route handlers
├── schemas/        # Pydantic schemas
└── services/       # Business logic services
```

## Testing

```bash
# Run tests (when implemented)
pytest

# Run with coverage
pytest --cov=app
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Make changes
4. Submit pull request

## License

[Your License Here]

## Support

For issues and questions, please open an issue on GitHub.

