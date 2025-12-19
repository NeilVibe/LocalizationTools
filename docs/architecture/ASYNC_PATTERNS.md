# Async Architecture Patterns

**Async/Await** | **WebSocket** | **Real-Time Updates** | **Concurrency**

---

## 🚀 WHY ASYNC?

**All new endpoints are async for 10-100x better concurrency.**

### Benefits:
- ✅ Handle 100+ concurrent requests without blocking
- ✅ Non-blocking I/O operations (database, files, network)
- ✅ Real-time WebSocket updates
- ✅ Scalable to thousands of users
- ✅ Efficient resource utilization

---

## 📝 ASYNC ENDPOINT PATTERN

### Basic Async Endpoint

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from server.utils.dependencies import get_async_db

router = APIRouter(prefix="/api/v2/resource", tags=["Resource"])

@router.post("/create")
async def create_resource(
    data: ResourceData,
    db: AsyncSession = Depends(get_async_db),  # Async database session
    current_user: dict = Depends(get_current_active_user_async)  # Async auth
):
    # All operations are non-blocking
    async with db.begin():  # Async transaction
        # Async database query
        result = await db.execute(select(Resource).where(Resource.id == data.id))
        resource = result.scalar_one_or_none()

        if not resource:
            # Create new resource
            resource = Resource(**data.dict())
            db.add(resource)

    # Async WebSocket emit
    await emit_resource_created({
        'resource_id': resource.id,
        'user_id': current_user['id']
    })

    return {"status": "success", "resource": resource}
```

---

## 🗄️ ASYNC DATABASE OPERATIONS

### Async Session Management

```python
# server/utils/dependencies.py
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

async_engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,      # Connection pool
    max_overflow=10,   # Extra connections if needed
    pool_pre_ping=True # Verify connections before use
)

async def get_async_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session
```

### Query Patterns

```python
# ✅ CORRECT: Async query
async def get_user(user_id: int, db: AsyncSession):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    return user

# ✅ CORRECT: Async insert
async def create_user(user_data: dict, db: AsyncSession):
    async with db.begin():
        user = User(**user_data)
        db.add(user)
        # Auto-commits when exiting context manager
    return user

# ✅ CORRECT: Async update
async def update_user(user_id: int, updates: dict, db: AsyncSession):
    async with db.begin():
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        for key, value in updates.items():
            setattr(user, key, value)
    return user

# ✅ CORRECT: Async delete
async def delete_user(user_id: int, db: AsyncSession):
    async with db.begin():
        await db.execute(delete(User).where(User.id == user_id))
```

---

## 🌐 WEBSOCKET REAL-TIME UPDATES

### Emit Events from API Endpoints

```python
from server.utils.websocket import emit_log_entry, emit_progress_update

@router.post("/process")
async def process_data(data: ProcessData):
    # Start processing
    await emit_progress_update({
        'operation_id': operation_id,
        'progress': 0,
        'status': 'started'
    })

    # Process data...
    result = await process(data)

    # Complete
    await emit_progress_update({
        'operation_id': operation_id,
        'progress': 100,
        'status': 'completed'
    })

    await emit_log_entry({
        'user_id': user_id,
        'tool_name': 'DataProcessor',
        'status': 'success',
        'result': result
    })

    return {"status": "success", "result": result}
```

### Client-Side WebSocket Handling

```javascript
// locaNext/src/lib/api/websocket.js
import { io } from 'socket.io-client';

const socket = io('http://localhost:8888');

// Listen for progress updates
socket.on('progress_update', (data) => {
    console.log(`Progress: ${data.progress}%`);
    // Update UI
});

// Listen for log entries
socket.on('log_entry', (data) => {
    console.log(`Log: ${data.tool_name} - ${data.status}`);
    // Update activity feed
});

// Listen for operation completion
socket.on('operation_complete', (data) => {
    console.log(`Operation ${data.operation_id} completed`);
    // Show notification
});
```

---

## ⚡ CONCURRENT OPERATIONS

### Running Multiple Async Operations

```python
import asyncio

async def process_multiple_files(files: list[str]):
    # Process all files concurrently
    tasks = [process_file(file) for file in files]
    results = await asyncio.gather(*tasks)
    return results

async def process_file(file_path: str):
    # Async file processing
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()

    # Process content...
    result = await analyze(content)
    return result
```

### Rate Limiting with Semaphore

```python
async def process_with_limit(files: list[str], max_concurrent: int = 5):
    semaphore = asyncio.Semaphore(max_concurrent)

    async def process_with_semaphore(file_path: str):
        async with semaphore:
            return await process_file(file_path)

    tasks = [process_with_semaphore(file) for file in files]
    results = await asyncio.gather(*tasks)
    return results
```

---

## 🔄 ASYNC BACKGROUND TASKS

### FastAPI Background Tasks

```python
from fastapi import BackgroundTasks

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    background_tasks: BackgroundTasks
):
    # Save file immediately
    file_path = await save_file(file)

    # Process in background
    background_tasks.add_task(process_uploaded_file, file_path)

    return {"status": "uploaded", "file_path": file_path}

async def process_uploaded_file(file_path: str):
    # Long-running processing
    result = await analyze_file(file_path)
    await emit_processing_complete(result)
```

---

## 🚨 COMMON ASYNC PITFALLS

### ❌ PITFALL 1: Mixing Sync and Async

```python
# ❌ WRONG: Sync database in async endpoint
@router.post("/endpoint")
async def my_endpoint(db: Session = Depends(get_db)):  # Sync session!
    user = db.query(User).first()  # Blocks entire event loop!

# ✅ CORRECT: Async database
@router.post("/endpoint")
async def my_endpoint(db: AsyncSession = Depends(get_async_db)):
    result = await db.execute(select(User))
    user = result.scalar_one_or_none()
```

---

### ❌ PITFALL 2: Forgetting await

```python
# ❌ WRONG: Missing await
async def get_user(user_id: int):
    user = db.execute(select(User)...)  # Returns coroutine, not user!

# ✅ CORRECT: Use await
async def get_user(user_id: int):
    result = await db.execute(select(User)...)
    user = result.scalar_one_or_none()
```

---

### ❌ PITFALL 3: Blocking Operations in Async

```python
# ❌ WRONG: Blocking I/O in async function
async def process_file(file_path: str):
    with open(file_path, 'r') as f:  # Blocking!
        content = f.read()

# ✅ CORRECT: Use async I/O
import aiofiles

async def process_file(file_path: str):
    async with aiofiles.open(file_path, 'r') as f:
        content = await f.read()
```

---

### ❌ PITFALL 4: Not Using Context Managers

```python
# ❌ WRONG: Manual commit/rollback
async def create_user(user_data: dict, db: AsyncSession):
    user = User(**user_data)
    db.add(user)
    await db.commit()  # Easy to forget!

# ✅ CORRECT: Use context manager
async def create_user(user_data: dict, db: AsyncSession):
    async with db.begin():
        user = User(**user_data)
        db.add(user)
        # Auto-commits on exit, auto-rolls back on error
```

---

## 📊 PERFORMANCE BENEFITS

### Benchmark Results

**Sync Endpoints:**
- 10 concurrent requests: ~5 seconds
- 100 concurrent requests: ~50 seconds (linear scaling)

**Async Endpoints:**
- 10 concurrent requests: ~0.5 seconds
- 100 concurrent requests: ~0.6 seconds (constant time!)

**10-100x improvement with async!**

---

## 🧪 TESTING ASYNC CODE

### Async Test Pattern

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_async_endpoint():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v2/resource/create", json={...})
        assert response.status_code == 200
        assert response.json()["status"] == "success"
```

---

## 📚 RELATED DOCUMENTATION

- **BACKEND_PRINCIPLES.md** - Backend design principles
- **CODING_STANDARDS.md** - Coding rules and patterns
- **testing/PYTEST_GUIDE.md** - Testing async code
- **PERFORMANCE.md** - Performance optimization
