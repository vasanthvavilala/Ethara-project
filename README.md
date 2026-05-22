# TeamFlow - Team Task Manager

TeamFlow is a full-stack task management web application where Admins can create projects, add team members, assign tasks, and track progress. Members can view assigned tasks and update their task status.

## Features

- User signup and login
- Role-based access control: Admin and Member
- Project creation and team member management
- Task creation, assignment, due date and status tracking
- Dashboard with total, pending, in-progress, completed and overdue tasks
- REST API endpoints for projects and tasks
- SQLite database for local development
- Railway-ready deployment files

## Tech Stack

- Frontend: HTML, CSS, JavaScript
- Backend: Python Flask
- Database: SQLite
- Deployment: Railway

## Roles

### Admin
- Create projects
- Add members to projects
- Create and assign tasks
- Update/delete tasks
- View dashboard

### Member
- View assigned tasks
- Update task status
- View dashboard

## Local Setup

1. Clone the repository

```bash
git clone your-repo-link
cd teamflow-task-manager
```

2. Create virtual environment

```bash
python -m venv venv
```

3. Activate virtual environment

For Windows:

```bash
venv\Scripts\activate
```

For Mac/Linux:

```bash
source venv/bin/activate
```

4. Install requirements

```bash
pip install -r requirements.txt
```

5. Run the application

```bash
python app.py
```

6. Open in browser

```text
http://127.0.0.1:5000
```

## Demo Credentials

Create these users manually from the Signup page:

Admin:
- Role: Admin
- Example email: admin@gmail.com
- Password: 123456

Member:
- Role: Member
- Example email: member@gmail.com
- Password: 123456

## REST APIs

### Get Tasks

```http
GET /api/tasks
```

### Get Projects

```http
GET /api/projects
```

## Railway Deployment

1. Push this project to GitHub.
2. Open Railway.
3. Create a new project.
4. Select "Deploy from GitHub repo".
5. Choose this repository.
6. Railway will detect the Python app and use the Procfile.
7. After deployment, generate/open the live domain.

## Demo Video Flow

1. Show signup and login.
2. Login as Admin.
3. Create a project.
4. Add a member to the project.
5. Create and assign a task.
6. Login as Member.
7. Update task status.
8. Show dashboard changes.
9. Show live Railway URL and GitHub repository.
