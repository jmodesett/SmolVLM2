# Architecture Overview - Async API Backend

## 🏗️ System Architecture

### Current State (Before Changes)
```
┌─────────────────────────────────────┐
│       Frontend (React/Next.js)       │
│                                      │
│  Expected:                           │
│  - POST /api/v1/video/upload        │  ❌ 404 Not Found
│  - GET  /api/v1/video/status/:id    │  ❌ 404 Not Found
│  - GET  /api/v1/video/results/:id   │  ❌ 404 Not Found
│                                      │
└──────────────────┬───────────────────┘
                   │
                   │ HTTP Requests
                   │
                   ▼
┌─────────────────────────────────────┐
│       Flask Backend (app.py)         │
│                                      │
│  Actual Endpoints:                   │
│  - POST /analyze/highlights  ✅      │  Sync, No sessions
│  - POST /analyze/workout     ✅      │  Sync, No sessions
│  - GET  /health              ✅      │
│                                      │
└──────────────────┬───────────────────┘
                   │
                   ▼
┌─────────────────────────────────────┐
│  SmolVLM2 Video Processing           │
│  (video_highlight_generator.py)      │
└──────────────────────────────────────┘
```

### Target State (After Implementation)
```
┌─────────────────────────────────────────────────────────┐
│              Frontend (React/Next.js)                    │
│                                                          │
│  API Calls:                                              │
│  1. POST /api/v1/video/upload          → SessionID      │
│  2. GET  /api/v1/video/status/:id      → Status Polling │
│  3. GET  /api/v1/video/results/:id     → Final Results  │
│  4. POST /api/v1/video/cancel/:id      → Cancel         │
│  5. DELETE /api/v1/video/cleanup/:id   → Cleanup        │
│                                                          │
└──────────────────────┬──────────────────────────────────┘
                       │
                       │ HTTP Requests
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│                Flask Backend (app.py)                     │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  NEW ASYNC API LAYER: ✅                                 │
│  ┌────────────────────────────────────────────────┐     │
│  │  POST   /api/v1/video/upload                   │     │
│  │  GET    /api/v1/video/status/:sessionId        │     │
│  │  GET    /api/v1/video/results/:sessionId       │     │
│  │  POST   /api/v1/video/cancel/:sessionId        │     │
│  │  DELETE /api/v1/video/cleanup/:sessionId       │     │
│  └────────────────────────────────────────────────┘     │
│                         ↓                                │
│  ┌────────────────────────────────────────────────┐     │
│  │         Session Manager                         │     │
│  │  - Create/Get/Update/Delete sessions           │     │
│  │  - Track: status, progress, results            │     │
│  │  - Thread-safe with locks                      │     │
│  └────────────────────────────────────────────────┘     │
│                         ↓                                │
│  ┌────────────────────────────────────────────────┐     │
│  │      Background Worker (ThreadPool)            │     │
│  │  - Async video processing                      │     │
│  │  - Progress updates                            │     │
│  │  - Error handling                              │     │
│  └────────────────────────────────────────────────┘     │
│                                                           │
│  BACKWARD COMPATIBLE (Unchanged): ✅                     │
│  ┌────────────────────────────────────────────────┐     │
│  │  POST /analyze/highlights                      │     │
│  │  POST /analyze/workout                         │     │
│  │  GET  /health                                  │     │
│  └────────────────────────────────────────────────┘     │
│                                                           │
└──────────────────────┬────────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│           SmolVLM2 Video Processing                       │
│           (video_highlight_generator.py)                  │
│                                                           │
│  - generate_highlights()                                 │
│  - analyze_workout_with_timestamps()                     │
│  - SmolVLMHighlightGenerator class                       │
│                                                           │
│  ⚠️ NO CHANGES TO THIS COMPONENT                         │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

---

## 📊 Request Flow Diagrams

### Async Upload & Processing Flow
```
┌─────────┐
│ Client  │
└────┬────┘
     │
     │ 1. POST /api/v1/video/upload
     │    (multipart: file + analysis_type + params)
     ▼
┌─────────────────┐
│ Upload Endpoint │
└────┬────────────┘
     │
     │ 2. Save file to /tmp/smolvlm_uploads/
     │ 3. Create session → sessionId
     │ 4. Submit to ThreadPool
     ▼
┌──────────────────┐         ┌─────────────────────┐
│ Session Manager  │◄────────┤ Background Worker   │
│                  │         │                     │
│ Status: PENDING  │         │ process_video_async │
│ Progress: 0.0    │         │                     │
└──────────────────┘         └─────────────────────┘
     │                                 │
     │ 5. Return 202 Accepted         │
     │    + sessionId                  │
     ▼                                 │
┌─────────┐                           │
│ Client  │                           │
└────┬────┘                           │
     │                                 │
     │ 6. Poll every 2s:              │
     │    GET /api/v1/video/status    │
     │                                 │
     ▼                                 ▼
┌──────────────────┐         ┌─────────────────────┐
│ Status Endpoint  │◄────────┤ Background Worker   │
│                  │         │                     │
│ Returns:         │         │ Updates progress:   │
│ - status         │         │ 0.2 → 0.5 → 1.0     │
│ - progress       │         │                     │
│ - currentStep    │         │ Updates status:     │
└──────────────────┘         │ PROCESSING →        │
     │                       │ COMPLETED           │
     │                       └─────────────────────┘
     │ 7. status = "completed"
     │
     │ 8. GET /api/v1/video/results/:sessionId
     ▼
┌──────────────────┐
│ Results Endpoint │
│                  │
│ Returns:         │
│ - results object │
│ - analysis data  │
└──────────────────┘
     │
     │ 9. DELETE /api/v1/video/cleanup/:sessionId
     ▼
┌──────────────────┐
│ Cleanup Endpoint │
│                  │
│ - Remove file    │
│ - Delete session │
└──────────────────┘
```

### Session State Transitions
```
┌─────────┐
│ PENDING │  (Upload complete, processing not started)
└────┬────┘
     │
     │ Background worker picks up task
     ▼
┌─────────────┐
│ PROCESSING  │  (Analysis in progress)
└────┬────────┘
     │
     ├─► Success
     │   ▼
     │   ┌───────────┐
     │   │ COMPLETED │  (Results available)
     │   └───────────┘
     │
     ├─► Error
     │   ▼
     │   ┌─────────┐
     │   │ FAILED  │  (Error occurred)
     │   └─────────┘
     │
     └─► Cancel
         ▼
         ┌───────────┐
         │ CANCELLED │  (User cancelled)
         └───────────┘
```

---

## 🔧 Component Interactions

### Session Manager
```
SessionManager
├─ sessions: Dict[str, SessionState]
│  └─ Thread-safe with locks
│
├─ create_session(analysis_type)
│  └─ Generate UUID → Create SessionState → Return ID
│
├─ get_session(session_id)
│  └─ Lookup in dict → Return SessionState or None
│
├─ update_session(session_id, **updates)
│  └─ Lock → Update fields → Update timestamp → Unlock
│
└─ delete_session(session_id)
   └─ Lock → Remove from dict → Unlock
```

### Background Worker
```
ThreadPoolExecutor (max_workers=4)
│
└─ process_video_async(session_id, video_path, analysis_type, params)
   │
   ├─ Update: status=PROCESSING, progress=0.2
   │
   ├─ Create SmolVLMHighlightGenerator()
   │
   ├─ if analysis_type == 'highlights':
   │  └─ generate_highlights(...)
   │     └─ Update: progress=0.4, 0.6, 0.8
   │
   ├─ elif analysis_type == 'workout':
   │  └─ analyze_workout_with_timestamps(...)
   │     └─ Update: progress=0.4, 0.6, 0.8
   │
   ├─ Update: status=COMPLETED, progress=1.0, results={...}
   │
   └─ Cleanup generator
```

### API Endpoints Flow
```
/api/v1/video/upload
  │
  ├─ Validate file
  ├─ Parse parameters
  ├─ Save to /tmp/smolvlm_uploads/
  ├─ session_id = session_manager.create_session()
  ├─ executor.submit(process_video_async, ...)
  └─ return {sessionId, status: "pending"}

/api/v1/video/status/:sessionId
  │
  ├─ session = session_manager.get_session()
  └─ return {status, progress, currentStep}

/api/v1/video/results/:sessionId
  │
  ├─ session = session_manager.get_session()
  ├─ if status != COMPLETED: return error
  └─ return {sessionId, results}

/api/v1/video/cancel/:sessionId
  │
  ├─ session = session_manager.get_session()
  ├─ session_manager.update_session(status=CANCELLED)
  └─ return {message: "cancelled"}

/api/v1/video/cleanup/:sessionId
  │
  ├─ session = session_manager.get_session()
  ├─ os.remove(session.video_path)
  ├─ session_manager.delete_session()
  └─ return {message: "cleaned up"}
```

---

## 🎯 Data Models

### SessionState
```python
@dataclass
class SessionState:
    session_id: str           # UUID
    status: ProcessingStatus  # Enum: PENDING|PROCESSING|COMPLETED|FAILED|CANCELLED
    created_at: datetime      # Timestamp
    updated_at: datetime      # Timestamp
    analysis_type: str        # 'highlights' or 'workout'
    video_path: str          # /tmp/smolvlm_uploads/uuid_filename.mp4
    progress: float          # 0.0 to 1.0
    current_step: str        # "Extracting segments"
    results: dict            # Analysis results (when completed)
    error: str               # Error message (if failed)
```

### API Response Formats

**Upload Response (202 Accepted)**:
```json
{
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "pending",
  "message": "Video uploaded successfully, processing started"
}
```

**Status Response (200 OK)**:
```json
{
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 0.65,
  "currentStep": "Analyzing workout segments",
  "createdAt": "2025-09-30T10:30:00Z",
  "updatedAt": "2025-09-30T10:32:15Z",
  "error": null
}
```

**Results Response (200 OK)**:
```json
{
  "sessionId": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "results": {
    "video_path": "/tmp/...",
    "processing_time_seconds": 45.2,
    "highlights_found": 5,
    "highlights": [...]
  }
}
```

---

## 📈 Performance Considerations

### Threading Model
```
Main Thread (Flask)
  ├─ Handle HTTP requests
  ├─ Manage sessions (thread-safe)
  └─ Return responses immediately

Background Threads (4 workers)
  ├─ Worker 1: Process video task
  ├─ Worker 2: Process video task
  ├─ Worker 3: Process video task
  └─ Worker 4: Process video task
```

### Memory Usage
- Session Manager: ~1KB per session (minimal)
- Background Tasks: ~2GB per active video processing
- Max Concurrent: 4 video processing tasks
- **Total Peak**: ~8GB with all 4 workers active

### Concurrency Limits
- Max simultaneous uploads: Unlimited (fast operation)
- Max simultaneous processing: 4 (ThreadPoolExecutor limit)
- Session storage: In-memory (consider Redis for production)

---

## 🔒 Thread Safety

### SessionManager Locking
```python
self.lock = threading.Lock()

with self.lock:
    # All dict operations protected
    self.sessions[session_id] = SessionState(...)
```

### Background Task Isolation
- Each task runs in separate thread
- No shared state between tasks (except session updates)
- Session updates are atomic via lock

---

**Architecture Status**: 🟢 DESIGNED  
**Implementation Status**: 🟡 AWAITING APPROVAL  
**Next Step**: Begin Phase 1 implementation
