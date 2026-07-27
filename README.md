# Aaroh AI

**Every Great Project Starts with the Right Guidance.**

Aaroh AI is a personalized GenAI and Agentic AI-powered project mentor that helps engineering students, developers, researchers, startup teams, and professionals transform project ideas into industry-ready software solutions.

Unlike conventional AI chatbots, Aaroh AI understands a user's background, project goals, skills, timeline, and existing codebase to provide structured, context-aware guidance throughout the entire software development lifecycle.

---

## ✨ What Makes Aaroh AI Different

Most AI tools answer the question you type. Aaroh AI reads the whole situation first — your background, your timeline, and, if you give it one, your actual codebase — before it offers a single recommendation. Every suggestion is grounded in a Retrieval-Augmented Generation (RAG) pipeline backed by an engineering knowledge base, so guidance is source-grounded and explainable rather than generic.

You can start however the idea currently lives in your head:
- 📝 A simple typed description
- 🎙️ A voice memo
- 🔗 A GitHub repository link
- 📦 A ZIP upload of an existing project

From there, Aaroh AI analyzes your repository, identifies technologies and architecture, evaluates code quality, recommends improvements, suggests innovative features, generates a personalized roadmap, and prepares a comprehensive **AI Project Health Report**.

---

## 🎯 Target Users

- Engineering students
- Software developers
- Hackathon participants
- Startup teams
- Researchers
- Freelancers
- Early-career professionals

---

## 🚀 Core Features

- **Personalized project guidance** based on user profile and goals
- **Multi-format intake** — text, voice, GitHub repository, or ZIP upload
- **Repository analysis** using the GitHub API, PyGithub, and Python AST
- **Automatic detection** of architecture, frameworks, APIs, and dependencies
- **RAG-powered engineering knowledge assistant** using ChromaDB
- **Multi-agent workflow** using LangGraph for intelligent task orchestration
- **Architecture, tech stack, and database recommendations**
- **Innovation suggestions** and feature enhancement recommendations
- **AI-generated development roadmap** with milestones
- **GitHub quality review** and deployment-readiness assessment
- **AI Project Health Dashboard** — architecture, scalability, and documentation scores
- **Interactive AI mentor** for continuous, ongoing guidance
- **Secure authentication and project storage** using Firebase
- **Analytics dashboard** with React Flow and Recharts
- 🔜 **Planned**: Whisper voice input, Tree-sitter parsing, Docker deployment

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Frontend** | React, Tailwind CSS, React Flow, Recharts |
| **Backend** | FastAPI, Python, Uvicorn |
| **AI / Orchestration** | Gemini API, LangChain, LangGraph |
| **Database** | PostgreSQL, ChromaDB, Firebase |
| **Repository Analysis** | GitHub API, PyGithub, Python AST, zipfile, pathlib, markdown, PyYAML |
| **Planned / Future** | Whisper API, Tree-sitter, Docker, Redis, Celery |

---

## 🧭 How It Works

```
   Idea  →  Analysis  →  Roadmap  →  Deployment
```

1. **Idea** — Describe your project by text, voice, or point to an existing GitHub repo / ZIP.
2. **Analysis** — Architecture, tech stack, and code quality are evaluated against a grounded engineering knowledge base via RAG.
3. **Roadmap** — A milestone-based development plan is generated around your timeline, skill level, and goals.
4. **Deployment** — An AI Project Health Report and readiness assessment carry the project to a shippable state.

---

## 📐 Project Vision

To become an intelligent AI mentor that guides users from project ideation to deployment by providing **personalized, explainable, and industry-oriented recommendations** — rather than generic AI responses.

---

## 📂 Repository Structure

> Update this section to match your actual repo layout as the project grows.

```
aaroh-ai/
├── frontend/         # React + Tailwind CSS client
├── backend/          # FastAPI application
├── ai/               # LangChain / LangGraph agents & RAG pipeline
├── analysis/         # Repository analysis (GitHub API, PyGithub, AST parsing)
├── docs/             # Additional documentation
└── README.md
```

---

## ⚙️ Getting Started

> Fill in exact setup commands once the codebase is finalized. Example scaffold below:

### Prerequisites
- Node.js (for the frontend)
- Python 3.10+ (for the backend)
- PostgreSQL instance
- Firebase project (for auth & storage)
- Gemini API key

### Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables
Create a `.env` file in the backend directory:
```
DATABASE_URL=
FIREBASE_API_KEY=
FIREBASE_PROJECT_ID=
GEMINI_API_KEY=
CHROMA_DB_PATH=
```

---

## 🗺️ Roadmap

- [ ] Whisper API integration for voice input
- [ ] Tree-sitter based deep code parsing
- [ ] Docker-based deployment previews
- [ ] Redis + Celery for async task processing
- [ ] Expanded engineering knowledge base coverage

---

## 🤝 Contributing

Contributions are welcome! Please open an issue to discuss significant changes before submitting a pull request.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/your-feature`)
3. Commit your changes (`git commit -m "Add your feature"`)
4. Push to the branch (`git push origin feature/your-feature`)
5. Open a Pull Request

---

## 📄 License

>

---

## 📬 Contact

For questions, feedback, or collaboration inquiries, please open an issue or reach out via the contact details in the repository.