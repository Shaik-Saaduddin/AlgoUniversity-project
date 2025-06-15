# OnlineJudge

OnlineJudge is a web-based platform for competitive programming and coding practice. It allows users to register, browse coding problems, submit solutions in multiple programming languages, and receive instant feedback on their code correctness and performance. The platform also features AI-powered code review and hints to assist users in improving their solutions.

## Features

- **User Accounts and Authentication**  
  Secure user registration, login, and profile management.

- **Problem Management**  
  Browse a curated list of coding problems with detailed descriptions and test cases. Admin users can add, edit, and delete problems.

- **Code Submission and Compilation**  
  Submit code solutions in Python, C, C++, and Java. The platform compiles and runs code against predefined test cases and provides detailed results including output, errors, execution time, and verdict.

- **AI Assistance for Code Review and Hints**  
  Integrated AI-powered assistance provides personalized code reviews, feedback, and hints to help users improve their solutions and learn best practices.

- **Leaderboard and Problem of the Day**  
  Track top users based on solved problems and feature a daily problem to encourage regular practice.

## Technology Stack

- Python 3.11  
- Django 4.2  
- SQLite (default database)  
- Docker (for containerized deployment)  
- AI integration using Gemini API (optional)

## Installation and Setup

### Prerequisites

- Python 3.11 or higher  
- Git  
- Docker (optional, for containerized setup)

### Clone the Repository

```bash
git clone <repository-url>
cd OnlineJudge
```

### Create Virtual Environment and Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

### Database Migrations

```bash
python manage.py migrate
```

### Running the Development Server

```bash
python manage.py runserver
```

Access the application at `http://127.0.0.1:8000/`.

### Running with Docker

Build and run the Docker container:

```bash
docker build -t onlinejudge .
docker run -p 8000:8000 onlinejudge
```

The application will be accessible at `http://localhost:8000/`.

## Usage

- Register a new user account or log in with existing credentials.  
- Browse the list of available coding problems and view detailed problem descriptions.  
- Submit your code solution using the integrated code editor and select your programming language.  
- View detailed results of your submission including output, errors, execution time, and pass/fail status for each test case.  
- Track your submission history and filter by problem, language, and status.  
- Admin users can manage problems through the admin interface (add, edit, delete).  
- Use the AI assistance feature to get personalized code reviews and hints to improve your solutions.

## Project Structure Overview

```
OnlineJudge/
├── accounts/            # User authentication and profile management
├── compiler/            # Code submission, compilation, and execution
├── problems/            # Problem management and AI assistance
├── OnlineJudge/         # Project settings and configuration
├── static/              # Static files (CSS, JS)
├── db.sqlite3           # SQLite database file
├── Dockerfile           # Docker container setup
├── manage.py            # Django project entry point
├── requirements.txt     # Python dependencies
```

## Contributing

Contributions are welcome! Please fork the repository and submit pull requests for bug fixes, improvements, or new features. Ensure code quality and include tests where applicable.

---

Thank you for using OnlineJudge! Happy coding!
