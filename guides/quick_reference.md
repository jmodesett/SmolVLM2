# Quick Reference - Async API Implementation

## 🚀 Quick Start Commands

### Backup Current State
```bash
cd /Users/jackmodesett/SmolVLM2
cp app.py app.py.backup
git add -A
git commit -m "Backup before async API implementation"
```

### Start Backend
```bash
source .venv/bin/activate
python app.py
```

### Test New API
```bash
python test_async_api.py
```

---

## 📡 New API Endpoints

### 1. Upload Video
```bash
POST /api/v1/video/upload
Content-Type: multipart/form-data

file: <video_file>
analysis_type: "highlights" | "workout"
params: '{"min_significance": 4}'

Response: {
  "sessionId": "uuid",
  "status": "pending"
}
```

### 2. Check Status
```bash
GET /api/v1/video/status/:sessionId

Response: {
  "sessionId": "uuid",
  "status": "processing",
  "progress": 0.45,
  "currentStep": "Analyzing segments"
}
```

### 3. Get Results
```bash
GET /api/v1/video/results/:sessionId

Response: {
  "sessionId": "uuid",
  "status": "completed",
  "results": { ... }
}
```

### 4. Cancel Processing
```bash
POST /api/v1/video/cancel/:sessionId

Response: {
  "sessionId": "uuid",
  "status": "cancelled"
}
```

### 5. Cleanup
```bash
DELETE /api/v1/video/cleanup/:sessionId

Response: {
  "message": "Session cleaned up"
}
```

---

## 🔧 Implementation Checklist

### Phase 1: Session Manager
- [ ] Copy SessionManager class into app.py
- [ ] Add import statements
- [ ] Initialize global session_manager
- [ ] Test session creation

### Phase 2: Background Worker
- [ ] Add ThreadPoolExecutor
- [ ] Add process_video_async function
- [ ] Test background execution

### Phase 3: Endpoints
- [ ] Add /api/v1/video/upload
- [ ] Add /api/v1/video/status/:sessionId
- [ ] Add /api/v1/video/results/:sessionId
- [ ] Add /api/v1/video/cancel/:sessionId
- [ ] Add /api/v1/video/cleanup/:sessionId

### Phase 4: Testing
- [ ] Create test_async_api.py
- [ ] Test upload workflow
- [ ] Test status polling
- [ ] Verify backward compatibility

---

## 🎯 Key Code Snippets

### Session Creation
```python
session_id = session_manager.create_session('highlights')
executor.submit(process_video_async, session_id, video_path, 'highlights', params)
```

### Status Check
```python
session = session_manager.get_session(session_id)
if session:
    return jsonify({
        'status': session.status.value,
        'progress': session.progress
    })
```

### Update Progress
```python
session_manager.update_session(
    session_id,
    progress=0.5,
    current_step="Processing segments"
)
```

---

## ⚠️ Critical Rules

### DO NOT MODIFY:
- ❌ SmolVLMHighlightGenerator class
- ❌ video_highlight_generator.py
- ❌ Existing /analyze/* endpoints
- ❌ Core MLX inference code

### SAFE TO ADD:
- ✅ New routes/endpoints
- ✅ Session management classes
- ✅ Background task handling
- ✅ Import statements

---

## 🧪 Testing Flow

### 1. Test Upload
```python
files = {'file': open('test_video.mp4', 'rb')}
data = {'analysis_type': 'highlights'}
response = requests.post(f"{BASE_URL}/api/v1/video/upload", files=files, data=data)
session_id = response.json()['sessionId']
```

### 2. Poll Status
```python
while True:
    response = requests.get(f"{BASE_URL}/api/v1/video/status/{session_id}")
    status = response.json()['status']
    if status in ['completed', 'failed']:
        break
    time.sleep(2)
```

### 3. Get Results
```python
response = requests.get(f"{BASE_URL}/api/v1/video/results/{session_id}")
results = response.json()['results']
```

---

## 📊 Expected Response Times

- Upload: < 1 second (just file save + session create)
- Status check: < 100ms (in-memory lookup)
- Processing: 30s - 10min (depends on video length)
- Results: < 100ms (already computed)
- Cleanup: < 1 second

---

## 🐛 Troubleshooting

### Issue: Import errors
```bash
# Ensure virtual environment is activated
source .venv/bin/activate
```

### Issue: Session not found
```bash
# Check session exists
curl http://localhost:5001/api/v1/video/status/:sessionId
```

### Issue: Background task not starting
```python
# Check ThreadPoolExecutor is initialized
print(executor._max_workers)  # Should be 4
```

### Issue: Backward compatibility broken
```bash
# Test existing endpoints
curl -X POST http://localhost:5001/analyze/highlights \
  -F "file=@test_video.mp4"
```

---

## 📚 Related Files

- `/guides/backend_api_fix_plan.md` - Detailed implementation plan
- `/guides/implementation_tracker.md` - Progress tracking
- `app.py` - Backend application
- `test_async_api.py` - Test script

---

**Quick Links**:
- [Implementation Plan](./backend_api_fix_plan.md)
- [Progress Tracker](./implementation_tracker.md)
