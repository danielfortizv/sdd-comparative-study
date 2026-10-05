# Background Tasks

FastAPI provides built-in support for background tasks that execute after sending the HTTP response to the client. This allows you to perform time-consuming operations like sending emails, processing files, or updating databases without making the client wait for the response.

## Capabilities

### Background Tasks Class

Class for managing and executing background tasks after HTTP response completion.

```python { .api }
class BackgroundTasks:
    def __init__(self, tasks: List[Task] = None) -> None:
        """
        Background tasks container.
        
        Parameters:
        - tasks: Optional list of initial tasks to execute
        """
        self.tasks = tasks or []

    def add_task(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any
    ) -> None:
        """
        Add background task to execute after response.
        
        Parameters:
        - func: Function to execute in background
        - args: Positional arguments for the function
        - kwargs: Keyword arguments for the function
        """
```

### Task Execution Interface

Functions can be added as background tasks with any signature and parameters.

```python { .api }
def background_task_function(*args: Any, **kwargs: Any) -> None:
    """
    Background task function signature.
    
    Parameters:
    - args: Positional arguments passed from add_task
    - kwargs: Keyword arguments passed from add_task
    
    Note: Background tasks are executed synchronously after response
    """

async def async_background_task_function(*args: Any, **kwargs: Any) -> None:
    """
    Async background task function signature.
    
    Parameters:
    - args: Positional arguments passed from add_task
    - kwargs: Keyword arguments passed from add_task
    
    Note: Async background tasks are awaited after response
    """
```

### Background Tasks Dependency

Background tasks can be injected as dependencies into route handlers.

```python { .api }
def route_handler(
    background_tasks: BackgroundTasks,
    # other parameters...
) -> Any:
    """
    Route handler with background tasks dependency.
    
    Parameters:
    - background_tasks: BackgroundTasks instance for adding tasks
    
    The BackgroundTasks instance is automatically provided by FastAPI
    """
```

## Usage Examples

### Basic Background Task

```python
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

def write_notification(email: str, message: str = ""):
    with open("log.txt", mode="w") as email_file:
        content = f"notification for {email}: {message}\n"
        email_file.write(content)

@app.post("/send-notification/{email}")
async def send_notification(email: str, background_tasks: BackgroundTasks):
    background_tasks.add_task(write_notification, email, message="some notification")
    return {"message": "Notification sent in the background"}
```

### Multiple Background Tasks

```python
from fastapi import FastAPI, BackgroundTasks
import time

app = FastAPI()

def slow_task_1(name: str):
    time.sleep(2)
    print(f"Task 1 completed for {name}")

def slow_task_2(name: str):
    time.sleep(3)
    print(f"Task 2 completed for {name}")

def cleanup_task():
    print("Cleanup completed")

@app.post("/process/{name}")
async def process_data(name: str, background_tasks: BackgroundTasks):
    # Add multiple background tasks
    background_tasks.add_task(slow_task_1, name)
    background_tasks.add_task(slow_task_2, name)
    background_tasks.add_task(cleanup_task)
    
    return {"message": f"Processing started for {name}"}
```

### Background Task with Email Sending

```python
from fastapi import FastAPI, BackgroundTasks
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

app = FastAPI()

def send_email(to_email: str, subject: str, body: str):
    # Email configuration (use environment variables in production)
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "your-email@gmail.com"
    sender_password = "your-password"
    
    try:
        # Create message
        message = MIMEMultipart()
        message["From"] = sender_email
        message["To"] = to_email
        message["Subject"] = subject
        
        message.attach(MIMEText(body, "plain"))
        
        # Send email
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(message)
        
        print(f"Email sent successfully to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {str(e)}")

@app.post("/send-email/")
async def send_email_endpoint(
    to_email: str,
    subject: str,
    body: str,
    background_tasks: BackgroundTasks
):
    background_tasks.add_task(send_email, to_email, subject, body)
    return {"message": "Email will be sent in the background"}
```

### Background Task with File Processing

```python
import os
import csv
from typing import List
from fastapi import FastAPI, BackgroundTasks, UploadFile, File

app = FastAPI()

def process_csv_file(filename: str, user_id: int):
    try:
        with open(filename, 'r') as file:
            csv_reader = csv.DictReader(file)
            processed_rows = 0
            
            for row in csv_reader:
                # Process each row (simulate some work)
                process_csv_row(row, user_id)
                processed_rows += 1
        
        # Clean up temporary file
        os.remove(filename)
        
        # Log completion
        print(f"Processed {processed_rows} rows for user {user_id}")
        
        # Notify user (in a real app, you might update a database or send a webhook)
        notify_user_completion(user_id, processed_rows)
        
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        notify_user_error(user_id, str(e))

def process_csv_row(row: dict, user_id: int):
    # Simulate row processing
    print(f"Processing row for user {user_id}: {row}")

def notify_user_completion(user_id: int, row_count: int):
    # In a real application, this might send a push notification or update a database
    print(f"Notifying user {user_id}: processed {row_count} rows")

def notify_user_error(user_id: int, error_message: str):
    print(f"Notifying user {user_id} of error: {error_message}")

@app.post("/upload-csv/{user_id}")
async def upload_csv(
    user_id: int,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    # Save uploaded file temporarily
    temp_filename = f"temp_{user_id}_{file.filename}"
    
    with open(temp_filename, "wb") as temp_file:
        content = await file.read()
        temp_file.write(content)
    
    # Process file in background
    background_tasks.add_task(process_csv_file, temp_filename, user_id)
    
    return {"message": f"File {file.filename} uploaded and will be processed in background"}
```

### Background Task with Database Operations

```python
from fastapi import FastAPI, BackgroundTasks
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

app = FastAPI()

# Database setup (simplified)
Base = declarative_base()
engine = create_engine("sqlite:///./test.db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    action = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)

def log_user_activity(user_id: int, action: str):
    db = SessionLocal()
    try:
        activity = ActivityLog(user_id=user_id, action=action)
        db.add(activity)
        db.commit()
        print(f"Logged activity: User {user_id} performed {action}")
    except Exception as e:
        print(f"Failed to log activity: {str(e)}")
        db.rollback()
    finally:
        db.close()

def update_user_statistics(user_id: int):
    db = SessionLocal()
    try:
        # Update user statistics based on recent activity
        # This is a placeholder for complex statistical calculations
        print(f"Updated statistics for user {user_id}")
    except Exception as e:
        print(f"Failed to update statistics: {str(e)}")
    finally:
        db.close()

@app.post("/user/{user_id}/action")
async def perform_user_action(
    user_id: int,
    action: str,
    background_tasks: BackgroundTasks
):
    # Log the activity in background
    background_tasks.add_task(log_user_activity, user_id, action)
    
    # Update user statistics in background
    background_tasks.add_task(update_user_statistics, user_id)
    
    return {"message": f"Action '{action}' recorded for user {user_id}"}
```

### Async Background Tasks

```python
import asyncio
import aiohttp
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

async def fetch_external_data(url: str, user_id: int):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                data = await response.json()
                
                # Process the fetched data
                await process_external_data(data, user_id)
                
                print(f"Successfully processed external data for user {user_id}")
    except Exception as e:
        print(f"Failed to fetch external data: {str(e)}")

async def process_external_data(data: dict, user_id: int):
    # Simulate async processing
    await asyncio.sleep(1)
    print(f"Processed data for user {user_id}: {len(data)} items")

async def send_webhook(webhook_url: str, payload: dict):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as response:
                if response.status == 200:
                    print("Webhook sent successfully")
                else:
                    print(f"Webhook failed with status {response.status}")
    except Exception as e:
        print(f"Webhook error: {str(e)}")

@app.post("/trigger-external-fetch/{user_id}")
async def trigger_external_fetch(
    user_id: int,
    data_url: str,
    webhook_url: str,
    background_tasks: BackgroundTasks
):
    # Fetch external data in background
    background_tasks.add_task(fetch_external_data, data_url, user_id)
    
    # Send webhook notification in background
    payload = {"user_id": user_id, "action": "external_fetch_triggered"}
    background_tasks.add_task(send_webhook, webhook_url, payload)
    
    return {"message": f"External data fetch triggered for user {user_id}"}
```

### Background Tasks with Error Handling

```python
import logging
from fastapi import FastAPI, BackgroundTasks

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

def safe_background_task(task_name: str, *args, **kwargs):
    """Wrapper for background tasks with error handling"""
    try:
        logger.info(f"Starting background task: {task_name}")
        
        # Determine which task to run based on task_name
        if task_name == "send_notification":
            send_notification_task(*args, **kwargs)
        elif task_name == "process_data":
            process_data_task(*args, **kwargs)
        elif task_name == "cleanup":
            cleanup_task(*args, **kwargs)
        else:
            raise ValueError(f"Unknown task: {task_name}")
        
        logger.info(f"Completed background task: {task_name}")
        
    except Exception as e:
        logger.error(f"Background task {task_name} failed: {str(e)}")
        # In a real app, you might want to retry, alert admins, etc.

def send_notification_task(user_id: int, message: str):
    if not user_id:
        raise ValueError("User ID is required")
    print(f"Notification sent to user {user_id}: {message}")

def process_data_task(data_id: int):
    if data_id <= 0:
        raise ValueError("Invalid data ID")
    print(f"Processed data {data_id}")

def cleanup_task():
    print("Cleanup completed")

@app.post("/safe-task/{user_id}")
async def create_safe_task(user_id: int, message: str, background_tasks: BackgroundTasks):
    # Use the safe wrapper for error handling
    background_tasks.add_task(safe_background_task, "send_notification", user_id, message)
    background_tasks.add_task(safe_background_task, "cleanup")
    
    return {"message": "Tasks scheduled with error handling"}
```

### Background Tasks with Progress Tracking

```python
import time
from typing import Dict
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

# In-memory progress tracking (use Redis or database in production)
task_progress: Dict[str, dict] = {}

def long_running_task(task_id: str, items_count: int):
    task_progress[task_id] = {
        "status": "running",
        "progress": 0,
        "total": items_count,
        "message": "Starting task..."
    }
    
    try:
        for i in range(items_count):
            # Simulate work
            time.sleep(0.5)
            
            # Update progress
            task_progress[task_id].update({
                "progress": i + 1,
                "message": f"Processing item {i + 1} of {items_count}"
            })
        
        # Task completed
        task_progress[task_id].update({
            "status": "completed",
            "message": "Task completed successfully"
        })
        
    except Exception as e:
        task_progress[task_id].update({
            "status": "failed",
            "message": f"Task failed: {str(e)}"
        })

@app.post("/start-task/{task_id}")
async def start_task(task_id: str, items_count: int, background_tasks: BackgroundTasks):
    if task_id in task_progress:
        return {"error": "Task with this ID already exists"}
    
    background_tasks.add_task(long_running_task, task_id, items_count)
    
    return {
        "message": f"Task {task_id} started",
        "task_id": task_id,
        "check_progress_url": f"/task-progress/{task_id}"
    }

@app.get("/task-progress/{task_id}")
async def get_task_progress(task_id: str):
    if task_id not in task_progress:
        return {"error": "Task not found"}
    
    return task_progress[task_id]
```

### Background Tasks with Dependency Injection

```python
from fastapi import FastAPI, BackgroundTasks, Depends

app = FastAPI()

class EmailService:
    def send_email(self, to: str, subject: str, body: str):
        print(f"Sending email to {to}: {subject}")

class DatabaseService:
    def log_activity(self, user_id: int, action: str):
        print(f"Logging: User {user_id} performed {action}")

# Dependency providers
def get_email_service() -> EmailService:
    return EmailService()

def get_database_service() -> DatabaseService:
    return DatabaseService()

def notification_task(
    user_id: int,
    action: str,
    email_service: EmailService,
    db_service: DatabaseService
):
    # Use injected services in background task
    db_service.log_activity(user_id, action)
    email_service.send_email(
        f"user{user_id}@example.com",
        "Action Performed",
        f"You performed: {action}"
    )

@app.post("/action/{user_id}")
async def perform_action(
    user_id: int,
    action: str,
    background_tasks: BackgroundTasks,
    email_service: EmailService = Depends(get_email_service),
    db_service: DatabaseService = Depends(get_database_service)
):
    # Pass dependencies to background task
    background_tasks.add_task(
        notification_task,
        user_id,
        action,
        email_service,
        db_service
    )
    
    return {"message": f"Action {action} performed for user {user_id}"}
```