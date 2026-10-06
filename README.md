# FlowBoard

A responsive Kanban task-management MVP built with FastAPI, PostgreSQL (Neon), and a dependency-free HTML/CSS/JavaScript single-page interface.

## Run it

1. Create and activate a virtual environment.
2. Install dependencies: `pip install -r requirements.txt`
3. Create `.env` and add the Neon connection string.
4. Run: `uvicorn main:app --reload`
5. Visit `http://127.0.0.1:8000`.

If `DATABASE_URL` is not configured, the app uses a local SQLite database only as a development convenience. The intended deployment database is Neon PostgreSQL.

## What is included

- Three-column Kanban board: To-do, In progress, Done.
- Drag and drop to change a task's status; server-side state persists the change.
- Create, edit, and delete tasks with description, priority, due date, and assignee.
- Priority filtering and live task totals per displayed column.
- Add people to a project with `owner` or `member` membership roles.
- A team sidebar. Each person’s in-progress workload is counted; an avatar pulses red when it exceeds five tasks.
- Initial sample project, users, and tasks are created only when the database has no projects.

## Data model and API

`Project` has many `Task` records. `User` records join projects through `Membership`, which stores the role. A task may be assigned only to a member of its project.

| Endpoint                          | Purpose                                |
| --------------------------------- | -------------------------------------- |
| `GET /api/projects`               | List available projects                |
| `GET /api/projects/{id}/board`    | Board data, members, workloads         |
| `POST /api/projects/{id}/tasks`   | Create a task                          |
| `PATCH /api/tasks/{id}`           | Update task fields/status              |
| `DELETE /api/tasks/{id}`          | Delete a task                          |
| `POST /api/projects/{id}/members` | Create/reuse a user and add membership |

Interactive API documentation is at `/docs`.

## Assumptions and tradeoffs

- Authentication is intentionally omitted. Membership roles are stored as requested but are not access-control enforcement; every API consumer has the same access in this MVP.
- The UI uses the first project returned by the API. Project creation/switching is out of scope because the requested MVP only specifies a board and project membership controls.
- Status changes are the only drag-and-drop operation; there is no within-column manual ordering. Tasks are ordered by creation time.
- No migration framework is included. Tables are created on startup, appropriate for an MVP; use Alembic before schema changes in production.
- The workload warning is computed from tasks assigned to each member whose status is exactly `in_progress`; it activates at 6 or more tasks.
