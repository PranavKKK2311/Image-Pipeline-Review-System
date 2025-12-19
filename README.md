# SKU Image Pipeline

A full-stack application for **SKU (Stock Keeping Unit) generation** and **product image validation** with a human-in-the-loop review workflow. Built with **FastAPI** (Python) backend and **React + TypeScript** frontend.

![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React-18-61DAFB?style=flat&logo=react&logoColor=black)
![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=flat&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat&logo=vite&logoColor=white)

---

## Features

### Core Services
- **SKU Generator** - Creates unique, deterministic product codes with collision resolution
- **Image Validator** - Automated quality checks (background, blur, coverage, similarity)
- **Review Queue** - Human-in-the-loop workflow for borderline cases

### User Roles
| Role | Capabilities |
|------|-------------|
| **Vendor** | Upload product images, track submission status, receive feedback |
| **Official** | Review pending submissions, approve/reject with feedback |

### Tech Highlights
- JWT-based authentication
- Real-time queue statistics
- Glassmorphism UI with dark matcha theme
- File upload with preview
- Role-based access control

---

## Architecture

```mermaid
flowchart TB
    subgraph Frontend["Frontend (React + Vite)"]
        LP[Login Page]
        RP[Register Page]
        VD[Vendor Dashboard]
        RQ[Review Queue]
        AC[Auth Context]
    end

    subgraph Backend["Backend (FastAPI)"]
        API[API Layer]
        AUTH[Auth Service]
        
        subgraph Services["Core Services"]
            SKU[SKU Generator]
            IV[Image Validator]
            RQS[Review Queue Service]
        end
        
        subgraph Storage["Storage"]
            MEM[(In-Memory Store)]
            UPL[(Uploads Folder)]
        end
    end

    LP --> AC
    RP --> AC
    AC --> API
    VD --> API
    RQ --> API
    
    API --> AUTH
    API --> SKU
    API --> IV
    API --> RQS
    
    SKU --> MEM
    RQS --> MEM
    IV --> UPL
    
    style Frontend fill:#ecfdf5,stroke:#059669
    style Backend fill:#fef3c7,stroke:#d97706
    style Services fill:#dbeafe,stroke:#3b82f6
```

### Request Flow

```mermaid
sequenceDiagram
    participant V as Vendor
    participant FE as Frontend
    participant API as Backend API
    participant IV as Image Validator
    participant RQ as Review Queue
    participant O as Official

    V->>FE: Upload Image
    FE->>API: POST /images/upload
    API->>IV: Validate Image
    IV-->>API: Score & Metrics
    
    alt Score >= 85%
        API-->>FE: Auto-Accepted
    else Score 70-85%
        API->>RQ: Create Review Task
        RQ-->>API: Task Created
        API-->>FE: Pending Review
        O->>FE: View Pending Tasks
        FE->>API: GET /review/pending
        O->>FE: Submit Decision
        FE->>API: POST /review/submit-decision
        API-->>FE: Feedback to Vendor
    else Score < 70%
        API-->>FE: Auto-Rejected
    end
```

---

## Project Structure

```
sku-image-pipeline/
├── backend/
│   ├── __init__.py
│   ├── config.py              # Configuration settings
│   ├── main.py                # Original FastAPI app
│   ├── migrations/            # Database migrations
│   └── services/
│       ├── sku_generator.py   # SKU generation logic
│       ├── image_validator.py # Image quality validation
│       └── review_queue.py    # Review workflow service
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx            # Root component with routing
│   │   ├── main.tsx           # React entry point
│   │   ├── index.css          # Global styles (matcha theme)
│   │   ├── context/
│   │   │   └── AuthContext.tsx    # Authentication state
│   │   └── pages/
│   │       ├── Login.tsx          # Login page
│   │       ├── Register.tsx       # Registration with role select
│   │       └── VendorDashboard.tsx # Vendor upload & history
│   ├── pages/
│   │   └── ReviewQueue.tsx    # Official review interface
│   ├── index.html             # HTML entry
│   ├── vite.config.ts         # Vite configuration
│   ├── package.json           # NPM dependencies
│   └── tsconfig.json          # TypeScript config
│
├── tests/
│   ├── test_sku_generator.py  # SKU generator tests
│   ├── test_image_validator.py
│   └── test_review_queue.py
│
├── uploads/                   # Uploaded images (gitignored)
├── run_server.py              # Main server entry point
├── requirements.txt           # Python dependencies
├── .env.example               # Environment template
├── .gitignore
└── README.md
```

---

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 18+
- npm or yarn

### Installation

**1. Clone the repository**
```bash
git clone <repository-url>
cd sku-image-pipeline
```

**2. Backend Setup**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v
```

**3. Frontend Setup**
```bash
cd frontend
npm install
```

**4. Start the Application**

Terminal 1 - Backend:
```bash
python run_server.py
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

**5. Access the Application**
- Frontend: http://localhost:5173
- API Docs: http://localhost:8000/docs
- API Health: http://localhost:8000/health

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login user |
| GET | `/api/v1/auth/me` | Get current user |
| POST | `/api/v1/auth/logout` | Logout |

### Images (Vendor)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/images/upload` | Upload product image |
| GET | `/api/v1/images/my-submissions` | Get vendor's submissions |

### Review (Official)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/review/pending` | Get pending tasks |
| GET | `/api/v1/review/stats` | Get queue statistics |
| POST | `/api/v1/review/submit-decision` | Submit review decision |

---

## Configuration

Copy `.env.example` to `.env` and configure:

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/sku_pipeline

# API
API_HOST=0.0.0.0
API_PORT=8000

# Image Validation Thresholds
IMAGE_ACCEPT_THRESHOLD=0.85
IMAGE_REVIEW_THRESHOLD=0.70
```

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | React 18, TypeScript, Vite |
| **Backend** | Python 3.9+, FastAPI, Pydantic |
| **Image Processing** | Pillow, OpenCV, ImageHash |
| **Authentication** | JWT (in-memory for demo) |
| **Styling** | CSS with glassmorphism effects |

---

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html
```

---

## License

MIT License - See [LICENSE](LICENSE) for details.

---

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request
