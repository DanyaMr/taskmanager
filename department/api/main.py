from contextlib import asynccontextmanager
import uvicorn
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from starlette.requests import Request
from fastapi.staticfiles import StaticFiles
from department.api.endpoints import router, router_legacy
from department.database.service import DatabaseService
from department.database.db_models import TaskDB, EmployeeDB
from fastapi.templating import Jinja2Templates


sys.path.append(str(Path(__file__).parent.parent.parent))


db_service = DatabaseService()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    db_service.init_database()
    print("🚀 Digital Twin Enterprise started successfully")
    print("📊 Fractal architecture: department level active")
    yield
    print("Shutdown complete")

app = FastAPI(
    title="Enterprise Digital Twin",
    description="Цифровой двойник предприятия с фрактальной архитектурой",
    version="2.0.0",
    lifespan=lifespan
)

# Пути к шаблонам и статике
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

app.include_router(router)
app.include_router(router_legacy, prefix="/api")

@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    # Получите данные из БД (пример)
    db = DatabaseService()
    session = db.Session()
    try:
        total_tasks = session.query(TaskDB).count()
        total_employees = session.query(EmployeeDB).count()

        metrics = [
            {"title": "Total Tasks", "value": total_tasks, "icon": "tasks"},
            {"title": "Employees", "value": total_employees, "icon": "users"},
        ]

        return templates.TemplateResponse(
            request=request,
            name="dashboard.html",
            context={"metrics": metrics}
        )
    finally:
        session.close()

@app.get("/employees", response_class=HTMLResponse)
async def employees_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="employees.html",
        context={}
    )

@app.get("/tasks", response_class=HTMLResponse)
async def tasks_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="tasks.html",
        context={}
    )

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8339, reload=True)