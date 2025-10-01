# Backend API Fix Plan - Session-Based Async Processing

**Date:** September 30, 2025  
**Issue:** API Contract Mismatch between Backend and Frontend  
**Status:** Implementation Ready

---

## 🎯 Problem Summary

### Current State (Backend)
- **Pattern:** Synchronous processing
- **Endpoints:** 
  - `POST /analyze/highlights` - Upload → Process → Return results
  - `POST /analyze/workout` - Upload → Process → Return results
- **Processing:** Blocking requests during video analysis
- **Response:** Immediate with complete results

### Expected State (Frontend)
- **Pattern:** Asynchronous with session management
- **Endpoints:**
  - `POST /api/v1/video/upload` - Upload → Return session ID
  - `GET /api/v1/video/status/:sessionId` - Check processing status
  - `GET /api/v1/video/results/:sessionId` - Get completed results
  - `POST /api/v1/video/cancel/:sessionId` - Cancel processing
  - `DELETE /api/v1/video/cleanup/:sessionId` - Cleanup resources
- **Processing:** Background tasks with status tracking
- **Response:** Session-based with polling

### Impact
❌ **Frontend cannot integrate** - API endpoints don't exist  
❌ **Long processing blocks requests** - Poor UX for long videos  
❌ **No progress tracking** - Users can't see analysis progress  
❌ **No cancellation** - Can't stop long-running analysis

---

## 🏗️ Solution Architecture

### Core Components

#### 1. Session Manager
**Purpose:** Track video processing sessions  
**Storage:** In-memory dictionary (upgradeable to Redis)  
**Data Structure:**
```python
{
    "session_id": {
        "status": "queued|processing|completed|failed|cancelled",
        "progress": 0-100,
        "video_path": "/path/to/video.mp4",
        "analysis_type": "highlights|workout",
        "params": {...},
        "result": {...},
        "error": "...",
        "created_at": datetime,
        "updated_at": datetime,
        "metadata": {...}
    }
}
```

#### 2. Background Task System
**Purpose:** Process videos asynchronously  
**Technology:** Python's `asyncio` + `concurrent.futures`  
**Features:**
- Thread pool for video analysis
- Task cancellation support
- Progress callbacks
- Error handling

#### 3. API Adapter Layer
**Purpose:** Bridge existing sync logic with async API  
**Location:** New file `async_api.py`  
**Components:**
- Session-based endpoints
- Status tracking
- Result caching
- Resource cleanup

---

## 📋 Implementation Plan

### Phase 1: Core Infrastructure (30 min)

#### Step 1.1: Session Manager (`session_manager.py`)
```python
class SessionManager:
    """Manage video processing sessions"""
    
    def create_session(self, video_path, analysis_type, params) -> str
    def get_session(self, session_id) -> dict
    def update_session(self, session_id, **updates) -> bool
    def delete_session(self, session_id) -> bool
    def list_sessions(self) -> list
    def cleanup_expired_sessions(self, max_age_hours=24) -> int
```

**Features:**
- UUID-based session IDs
- Thread-safe operations (with locks)
- Automatic cleanup of expired sessions
- Progress tracking (0-100%)
- Error state management

#### Step 1.2: Background Task Manager (`task_manager.py`)
```python
class BackgroundTaskManager:
    """Execute video analysis in background"""
    
    def submit_task(self, session_id, analysis_fn, *args, **kwargs) -> Future
    def cancel_task(self, session_id) -> bool
    def get_task_status(self, session_id) -> dict
    async def process_video_async(self, session_id, video_path, analysis_type, params)
```

**Features:**
- Thread pool executor (configurable workers)
- Task cancellation support
- Progress callbacks
- Exception handling and logging

### Phase 2: New API Endpoints (45 min)

#### Endpoint 1: Upload Video
```python
@app.post("/api/v1/video/upload")
async def upload_video(
    video: UploadFile,
    analysis_type: str = Form(...),  # "highlights" or "workout"
    params: str = Form(default="{}")  # JSON string of parameters
) -> dict:
    """
    Upload video and start async processing
    
    Returns:
        {
            "sessionId": "uuid-string",
            "status": "queued",
            "message": "Video uploaded successfully"
        }
    """
```

**Implementation:**
1. Validate video file (size, format)
2. Save to temporary storage
3. Create session with parameters
4. Submit background task
5. Return session ID immediately

#### Endpoint 2: Check Status
```python
@app.get("/api/v1/video/status/{session_id}")
async def get_status(session_id: str) -> dict:
    """
    Get processing status
    
    Returns:
        {
            "sessionId": "uuid-string",
            "status": "processing|completed|failed",
            "progress": 65,
            "message": "Analyzing segment 13/20"
        }
    """
```

**Implementation:**
1. Lookup session in manager
2. Return current status and progress
3. Handle not found (404)

#### Endpoint 3: Get Results
```python
@app.get("/api/v1/video/results/{session_id}")
async def get_results(session_id: str) -> dict:
    """
    Get analysis results (only if completed)
    
    Returns:
        {
            "sessionId": "uuid-string",
            "status": "completed",
            "data": {...}  # Full analysis results
        }
    """
```

**Implementation:**
1. Verify session exists
2. Check status is "completed"
3. Return stored results
4. Handle incomplete/failed states

#### Endpoint 4: Cancel Processing
```python
@app.post("/api/v1/video/cancel/{session_id}")
async def cancel_processing(session_id: str) -> dict:
    """
    Cancel ongoing processing
    
    Returns:
        {
            "sessionId": "uuid-string",
            "status": "cancelled",
            "message": "Processing cancelled successfully"
        }
    """
```

**Implementation:**
1. Verify session exists
2. Cancel background task
3. Update session status
4. Cleanup partial results

#### Endpoint 5: Cleanup
```python
@app.delete("/api/v1/video/cleanup/{session_id}")
async def cleanup_session(session_id: str) -> dict:
    """
    Delete session and cleanup resources
    
    Returns:
        {
            "message": "Session cleaned up successfully"
        }
    """
```

**Implementation:**
1. Cancel any running tasks
2. Delete video file
3. Remove session data
4. Clear cached results

### Phase 3: Integration & Testing (30 min)

#### Integration Points

1. **Modify `RailwayVideoGenerator`** to support progress callbacks:
```python
class RailwayVideoGenerator:
    def generate_highlights(
        self,
        video_path: str,
        progress_callback: callable = None,  # NEW
        **kwargs
    ):
        # Call progress_callback(progress, message) during processing
        ...
```

2. **Add Progress Tracking** to segment analysis:
```python
for i, segment in enumerate(segments):
    if progress_callback:
        progress = int((i / len(segments)) * 100)
        progress_callback(progress, f"Analyzing segment {i+1}/{len(segments)}")
    ...
```

3. **Update `app.py`** startup to initialize managers:
```python
@app.on_event("startup")
async def startup_event():
    global generator, session_manager, task_manager
    
    generator = RailwayVideoGenerator(...)
    session_manager = SessionManager()
    task_manager = BackgroundTaskManager(max_workers=2)
    
    # Start cleanup task
    asyncio.create_task(periodic_cleanup())
```

#### Testing Checklist

- [ ] Upload small video (< 10s) → Get session ID
- [ ] Poll status → See progress updates
- [ ] Get results → Receive complete analysis
- [ ] Upload long video (> 1 min) → Cancel mid-processing
- [ ] Cleanup → Verify resources deleted
- [ ] Multiple uploads → Verify concurrent processing
- [ ] Invalid session ID → 404 response
- [ ] Get results before completion → 400 error
- [ ] Expired session → Auto cleanup

---

## 📁 File Structure

```
/Users/jackmodesett/SmolVLM2/
├── app.py                          # Main FastAPI app (EXISTING - keep current endpoints)
├── async_api.py                    # NEW - Async API adapter layer
├── session_manager.py              # NEW - Session management
├── task_manager.py                 # NEW - Background task execution
├── railway_video_generator.py      # MODIFY - Add progress callbacks
├── guides/
│   └── backend_api_fix_plan.md    # THIS FILE
└── tests/
    └── test_async_api.py           # NEW - Integration tests
```

---

## 🚀 Implementation Order

### Step-by-Step Execution

#### 1. Create Session Manager (session_manager.py)
```bash
# 15 minutes
- Implement SessionManager class
- Add thread-safe operations
- Test CRUD operations
```

#### 2. Create Task Manager (task_manager.py)
```bash
# 15 minutes
- Implement BackgroundTaskManager
- Add thread pool executor
- Test task submission/cancellation
```

#### 3. Create Async API Layer (async_api.py)
```bash
# 30 minutes
- Implement 5 new endpoints
- Integrate with session/task managers
- Add error handling
```

#### 4. Modify Video Generator
```bash
# 15 minutes
- Add progress_callback parameter
- Update segment analysis loop
- Test callback functionality
```

#### 5. Update Main App (app.py)
```bash
# 10 minutes
- Initialize managers on startup
- Add periodic cleanup task
- Keep existing endpoints for backward compatibility
```

#### 6. Integration Testing
```bash
# 20 minutes
- Test all 5 new endpoints
- Verify progress tracking
- Test cancellation
- Test concurrent processing
```

**Total Estimated Time:** ~2 hours

---

## 🔄 Backward Compatibility

### Existing Endpoints (KEEP UNCHANGED)
- `POST /analyze/highlights` → Continue to work synchronously
- `POST /analyze/workout` → Continue to work synchronously
- `GET /health` → Continue to work
- `GET /` → Continue to work

### New Endpoints (FRONTEND USES THESE)
- `POST /api/v1/video/upload` → Async entry point
- `GET /api/v1/video/status/:sessionId` → Status polling
- `GET /api/v1/video/results/:sessionId` → Result retrieval
- `POST /api/v1/video/cancel/:sessionId` → Cancellation
- `DELETE /api/v1/video/cleanup/:sessionId` → Resource cleanup

**Migration Path:**
- Frontend uses new async endpoints
- Legacy integrations (if any) continue using sync endpoints
- Both can coexist without conflicts

---

## ⚡ Performance Considerations

### Resource Management
- **Max Concurrent Jobs:** 2 (configurable via env var)
- **Session TTL:** 24 hours (auto-cleanup)
- **Video Storage:** Temporary files cleaned after processing
- **Memory Usage:** Results cached in-memory (consider Redis for scale)

### Scalability Options
1. **Current:** In-memory session storage (single instance)
2. **Phase 2:** Redis for session storage (multi-instance support)
3. **Phase 3:** Celery for distributed task queue
4. **Phase 4:** Object storage (S3/GCS) for video files

---

## 🛡️ Error Handling

### Error States
- **queued** → Initial state after upload
- **processing** → Analysis in progress
- **completed** → Successfully finished
- **failed** → Analysis error (with error message)
- **cancelled** → User cancelled
- **expired** → Session TTL exceeded

### Error Responses
```python
# Session not found
{
    "error": "Session not found",
    "sessionId": "...",
    "code": 404
}

# Results not ready
{
    "error": "Results not ready",
    "status": "processing",
    "progress": 45,
    "code": 400
}

# Processing failed
{
    "error": "Analysis failed",
    "message": "Video format not supported",
    "sessionId": "...",
    "code": 500
}
```

---

## 🧪 Testing Strategy

### Unit Tests
- SessionManager CRUD operations
- TaskManager submit/cancel
- Progress callback functionality

### Integration Tests
- Full upload → status → results flow
- Cancellation during processing
- Cleanup after completion
- Concurrent uploads
- Error scenarios

### Performance Tests
- Multiple concurrent uploads (10+)
- Large video files (> 100MB)
- Long processing times (> 5 min)
- Session cleanup efficiency

---

## 📊 Monitoring & Logging

### Metrics to Track
- Active sessions count
- Average processing time
- Success/failure rate
- Queue depth
- Resource usage (CPU/Memory)

### Logging Points
- Video upload start/complete
- Processing start/progress/complete
- Cancellation events
- Cleanup operations
- Error conditions

---

## 🎯 Success Criteria

✅ **Functionality**
- [ ] All 5 new endpoints working
- [ ] Progress tracking operational
- [ ] Cancellation works reliably
- [ ] Cleanup removes all resources
- [ ] Concurrent processing supported

✅ **Performance**
- [ ] Upload response < 500ms
- [ ] Status check response < 100ms
- [ ] Results retrieval < 200ms
- [ ] Processing time matches sync version

✅ **Reliability**
- [ ] No memory leaks
- [ ] Proper error handling
- [ ] Resource cleanup on failure
- [ ] Session expiration works

✅ **Integration**
- [ ] Frontend can upload videos
- [ ] Frontend can poll status
- [ ] Frontend receives results
- [ ] Frontend can cancel/cleanup

---

## 🚦 Ready to Implement

This plan provides: