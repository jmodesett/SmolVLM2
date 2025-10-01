# Backend API Implementation Checklist

**Quick Reference Guide for Implementation**

---

## 🎯 Overview

This checklist breaks down the implementation into bite-sized, trackable tasks. Check off each item as you complete it.

**Estimated Total Time:** 2 hours  
**Priority:** HIGH - Frontend blocked until complete

---

## Phase 1: Core Infrastructure (30 min)

### Task 1.1: Create Session Manager ⏱️ 15 min
**File:** `session_manager.py`

```python
# Create new file with SessionManager class
```

**Checklist:**
- [ ] Create `session_manager.py`
- [ ] Implement `SessionManager.__init__()`
- [ ] Implement `create_session(video_path, analysis_type, params)`
- [ ] Implement `get_session(session_id)`
- [ ] Implement `update_session(session_id, **updates)`
- [ ] Implement `delete_session(session_id)`
- [ ] Add thread-safe locks for all operations
- [ ] Test: Create → Get → Update → Delete

**Validation:**
```python
# Test script
manager = SessionManager()
session_id = manager.create_session("/path/video.mp4", "highlights", {})
assert manager.get_session(session_id) is not None
assert manager.update_session(session_id, status="processing")
assert manager.delete_session(session_id)
```

### Task 1.2: Create Task Manager ⏱️ 15 min
**File:** `task_manager.py`

**Checklist:**
- [ ] Create `task_manager.py`
- [ ] Implement `BackgroundTaskManager.__init__(max_workers=2)`
- [ ] Implement `submit_task(session_id, analysis_fn, *args)`
- [ ] Implement `cancel_task(session_id)`
- [ ] Implement `get_task_status(session_id)`
- [ ] Add task tracking dictionary
- [ ] Test: Submit → Check Status → Cancel

**Validation:**
```python
# Test script
import time
task_manager = BackgroundTaskManager(max_workers=2)

def dummy_task():
    time.sleep(2)
    return {"result": "success"}

session_id = "test-123"
task_manager.submit_task(session_id, dummy_task)
assert task_manager.get_task_status(session_id)["status"] == "running"
time.sleep(3)
assert task_manager.get_task_status(session_id)["status"] == "completed"
```

---

## Phase 2: API Endpoints (45 min)

### Task 2.1: Upload Endpoint ⏱️ 10 min
**File:** `async_api.py` (create new)

**Checklist:**
- [ ] Create `async_api.py`
- [ ] Import FastAPI, SessionManager, TaskManager
- [ ] Implement `POST /api/v1/video/upload`
- [ ] Validate video file (size, format)
- [ ] Save video to temporary storage
- [ ] Create session with parameters
- [ ] Submit background task
- [ ] Return session ID

**Test:**
```bash
curl -X POST http://localhost:8000/api/v1/video/upload \
  -F "video=@test_video.mp4" \
  -F "analysis_type=highlights" \
  -F "params={}"
```

**Expected Response:**
```json
{
  "sessionId": "uuid-here",
  "status": "queued",
  "message": "Video uploaded successfully"
}
```

### Task 2.2: Status Endpoint ⏱️ 5 min
**File:** `async_api.py`

**Checklist:**
- [ ] Implement `GET /api/v1/video/status/{session_id}`
- [ ] Lookup session in manager
- [ ] Return status and progress
- [ ] Handle 404 if not found

**Test:**
```bash
curl http://localhost:8000/api/v1/video/status/SESSION_ID
```

**Expected Response:**
```json
{
  "sessionId": "uuid-here",
  "status": "processing",
  "progress": 65,
  "message": "Analyzing segment 13/20"
}
```

### Task 2.3: Results Endpoint ⏱️ 5 min
**File:** `async_api.py`

**Checklist:**
- [ ] Implement `GET /api/v1/video/results/{session_id}`
- [ ] Verify session exists and completed
- [ ] Return full analysis results
- [ ] Handle incomplete states (400 error)

**Test:**
```bash
curl http://localhost:8000/api/v1/video/results/SESSION_ID
```

**Expected Response:**
```json
{
  "sessionId": "uuid-here",
  "status": "completed",
  "data": {
    "highlights": [...],
    "processing_time": 45.2
  }
}
```

### Task 2.4: Cancel Endpoint ⏱️ 5 min
**File:** `async_api.py`

**Checklist:**
- [ ] Implement `POST /api/v1/video/cancel/{session_id}`
- [ ] Cancel background task via TaskManager
- [ ] Update session status to "cancelled"
- [ ] Cleanup partial results

**Test:**
```bash
curl -X POST http://localhost:8000/api/v1/video/cancel/SESSION_ID
```

**Expected Response:**
```json
{
  "sessionId": "uuid-here",
  "status": "cancelled",
  "message": "Processing cancelled successfully"
}
```

### Task 2.5: Cleanup Endpoint ⏱️ 5 min
**File:** `async_api.py`

**Checklist:**
- [ ] Implement `DELETE /api/v1/video/cleanup/{session_id}`
- [ ] Cancel any running tasks
- [ ] Delete video file from storage
- [ ] Remove session from manager
- [ ] Clear cached results

**Test:**
```bash
curl -X DELETE http://localhost:8000/api/v1/video/cleanup/SESSION_ID
```

**Expected Response:**
```json
{
  "message": "Session cleaned up successfully"
}
```

### Task 2.6: Integrate with Main App ⏱️ 15 min
**File:** `app.py`

**Checklist:**
- [ ] Import `async_api` module
- [ ] Initialize SessionManager on startup
- [ ] Initialize TaskManager on startup
- [ ] Mount async_api routes with `app.include_router()`
- [ ] Add periodic cleanup task
- [ ] Keep existing endpoints unchanged

**Update app.py:**
```python
from async_api import router as async_router

# In startup event
session_manager = SessionManager()
task_manager = BackgroundTaskManager(max_workers=2)

# Mount routes
app.include_router(async_router, prefix="/api/v1")
```

---

## Phase 3: Progress Integration (15 min)

### Task 3.1: Modify Video Generator ⏱️ 10 min
**File:** `railway_video_generator.py`

**Checklist:**
- [ ] Add `progress_callback` parameter to `generate_highlights()`
- [ ] Add `progress_callback` parameter to `analyze_workout_with_timestamps()`
- [ ] Call `progress_callback(progress, message)` during segment analysis
- [ ] Test callback with dummy function

**Code Changes:**
```python
def generate_highlights(
    self,
    video_path: str,
    progress_callback: callable = None,  # ADD THIS
    **kwargs
):
    # In segment analysis loop:
    for i, segment in enumerate(segments):
        if progress_callback:
            progress = int((i / len(segments)) * 100)
            progress_callback(progress, f"Analyzing segment {i+1}/{len(segments)}")
        # ... rest of analysis
```

### Task 3.2: Wire Progress to Sessions ⏱️ 5 min
**File:** `async_api.py`

**Checklist:**
- [ ] Create progress callback function
- [ ] Update session progress in callback
- [ ] Pass callback to video generator
- [ ] Test progress updates via status endpoint

**Implementation:**
```python
def create_progress_callback(session_id):
    def callback(progress, message):
        session_manager.update_session(
            session_id,
            progress=progress,
            message=message
        )
    return callback

# When submitting task:
callback = create_progress_callback(session_id)
task_manager.submit_task(
    session_id,
    generator.generate_highlights,
    video_path=path,
    progress_callback=callback,  # PASS HERE
    **params
)
```

---

## Phase 4: Testing (30 min)

### Task 4.1: Unit Tests ⏱️ 10 min
**File:** `tests/test_async_api.py`

**Checklist:**
- [ ] Create test directory and file
- [ ] Test SessionManager operations
- [ ] Test TaskManager operations
- [ ] Test progress callback

### Task 4.2: Integration Tests ⏱️ 10 min
**File:** `tests/test_integration.py`

**Checklist:**
- [ ] Test upload → status → results flow
- [ ] Test cancellation mid-processing
- [ ] Test cleanup after completion
- [ ] Test concurrent uploads (2-3 videos)
- [ ] Test error scenarios (invalid session, etc.)

### Task 4.3: Manual Testing ⏱️ 10 min

**Test Cases:**
1. **Happy Path:**
   ```bash
   # Upload
   SESSION_ID=$(curl -X POST http://localhost:8000/api/v1/video/upload \
     -F "video=@test.mp4" -F "analysis_type=highlights" | jq -r .sessionId)
   
   # Poll status
   while true; do
     curl http://localhost:8000/api/v1/video/status/$SESSION_ID
     sleep 2
   done
   
   # Get results
   curl http://localhost:8000/api/v1/video/results/$SESSION_ID
   
   # Cleanup
   curl -X DELETE http://localhost:8000/api/v1/video/cleanup/$SESSION_ID
   ```

2. **Cancellation:**
   ```bash
   # Upload long video
   SESSION_ID=$(curl -X POST ... | jq -r .sessionId)
   
   # Cancel after 5 seconds
   sleep 5
   curl -X POST http://localhost:8000/api/v1/video/cancel/$SESSION_ID
   ```

3. **Error Cases:**
   ```bash
   # Invalid session
   curl http://localhost:8000/api/v1/video/status/invalid-id
   
   # Results before completion
   curl http://localhost:8000/api/v1/video/results/$SESSION_ID_PROCESSING
   ```

---

## 🎯 Definition of Done

### Functional Requirements
- [ ] All 5 new endpoints responding correctly
- [ ] Progress tracking updates during processing
- [ ] Cancellation stops processing and cleans up
- [ ] Cleanup removes all resources
- [ ] Concurrent processing works (2+ videos)
- [ ] Existing `/analyze/*` endpoints still work

### Performance Requirements
- [ ] Upload response < 500ms
- [ ] Status check < 100ms
- [ ] Results retrieval < 200ms
- [ ] No memory leaks after 10+ uploads

### Reliability Requirements
- [ ] Proper error messages for all failure cases
- [ ] Resource cleanup on errors
- [ ] Session expiration (24 hours)
- [ ] Graceful shutdown cleans up pending tasks

### Documentation
- [ ] API endpoints documented
- [ ] Code comments for complex logic
- [ ] Test cases documented
- [ ] This checklist updated with any changes

---

## 🚀 Deployment Checklist

### Pre-Deployment
- [ ] All tests passing
- [ ] Code reviewed
- [ ] Environment variables configured
- [ ] Railway deployment config updated

### Deployment Steps
1. [ ] Commit changes to git
2. [ ] Push to Railway
3. [ ] Verify deployment successful
4. [ ] Test all endpoints on production
5. [ ] Monitor logs for errors

### Post-Deployment
- [ ] Notify frontend team
- [ ] Update API documentation
- [ ] Monitor first few requests
- [ ] Check resource usage

---

## 📞 Questions / Blockers

**If you encounter issues:**

1. **Session management issues:**
   - Check thread locks
   - Verify UUID generation
   - Test CRUD operations individually

2. **Background task problems:**
   - Check thread pool configuration
   - Verify task submission
   - Test cancellation logic

3. **Progress not updating:**
   - Verify callback is called
   - Check session update logic
   - Test with print statements

4. **Memory issues:**
   - Check video file cleanup
   - Verify session deletion
   - Monitor with `htop` or similar

---

## 🎓 Implementation Tips

1. **Start Simple:** Get one endpoint working end-to-end before adding complexity
2. **Test Often:** Test each component as you build it
3. **Log Everything:** Add logging for debugging
4. **Use Type Hints:** Makes code easier to understand
5. **Handle Errors:** Every operation should have try/except

**Remember:** The goal is working software, not perfect software. Get it working first, then refine!