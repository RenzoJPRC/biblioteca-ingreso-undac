import threading
import uuid
import time

# Estructura global para rastrear las tareas
# {"task_id": {"status": "processing", "progress": 0, "total": 0, "message": ""}}
# status puede ser: 'processing', 'completed', 'error'
UPLOAD_TASKS = {}
_tasks_lock = threading.Lock()

def create_task():
    task_id = str(uuid.uuid4())
    with _tasks_lock:
        UPLOAD_TASKS[task_id] = {
            "status": "processing",
            "progress": 0,
            "total": 0,
            "message": "Iniciando carga..."
        }
    return task_id

def update_task_progress(task_id, progress, total=None, msg=""):
    with _tasks_lock:
        if task_id in UPLOAD_TASKS:
            UPLOAD_TASKS[task_id]["progress"] = progress
            if total is not None:
                UPLOAD_TASKS[task_id]["total"] = total
            if msg:
                UPLOAD_TASKS[task_id]["message"] = msg

def finish_task(task_id, success=True, msg=""):
    with _tasks_lock:
        if task_id in UPLOAD_TASKS:
            UPLOAD_TASKS[task_id]["status"] = "completed" if success else "error"
            if msg:
                UPLOAD_TASKS[task_id]["message"] = msg

def get_task_status(task_id):
    with _tasks_lock:
        return dict(UPLOAD_TASKS.get(task_id, {"status": "error", "message": "Tarea no encontrada"}))
