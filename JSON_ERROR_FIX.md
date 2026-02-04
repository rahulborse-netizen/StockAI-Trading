# JSON Error Fix - "Unexpected token '<'"

## Problem
Error: `Unexpected token '<' "<!doctype"...is not Valid JSON`

This error occurs when the JavaScript code expects JSON but receives HTML instead (usually an error page).

## Root Cause
1. Flask server returns HTML error page (404/500) instead of JSON
2. JavaScript tries to parse HTML as JSON → fails
3. No error handling for non-JSON responses

## Fixes Applied

### 1. Frontend: Check Response Before Parsing JSON
```javascript
// Check if response is OK and is JSON
if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Server error (${response.status}): ${errorText}`);
}

// Check content type before parsing JSON
const contentType = response.headers.get('content-type');
if (!contentType || !contentType.includes('application/json')) {
    const errorText = await response.text();
    throw new Error(`Server returned HTML instead of JSON. Check Flask server logs.`);
}

const result = await response.json(); // Safe to parse now
```

### 2. Backend: Always Return JSON for API Routes
```python
# Error handlers to ensure API routes always return JSON
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'status': 'error', 'message': 'API endpoint not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    if request.path.startswith('/api/'):
        return jsonify({
            'status': 'error', 
            'message': 'Internal server error. Check Flask server logs.',
        }), 500
```

### 3. Backend: Better JSON Parsing Error Handling
```python
try:
    data = request.json
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid request: No JSON data'}), 400
except Exception as e:
    return jsonify({'status': 'error', 'message': f'Invalid request format: {str(e)}'}), 400
```

## Testing
1. **Restart Flask server** to load error handlers
2. **Refresh browser** (Ctrl+F5) to load new JavaScript
3. **Try connecting again**

## If Error Persists

### Check Flask Server Logs
Look at the terminal where Flask is running. You should see:
- `[Phase 1.2] Connect request - API Key: ...`
- Any error messages or tracebacks

### Common Causes
1. **Import Error**: Missing module or incorrect import
   - Check: `ModuleNotFoundError` in Flask logs
   - Fix: Install missing packages: `pip install -r requirements.txt`

2. **Syntax Error**: Python code has syntax error
   - Check: Flask won't start or shows syntax error
   - Fix: Check the file mentioned in error

3. **Route Not Found**: `/api/upstox/connect` doesn't exist
   - Check: 404 error in Flask logs
   - Fix: Verify route is defined in `app.py`

4. **Server Not Running**: Flask server crashed or not started
   - Check: No Flask output in terminal
   - Fix: Restart with `python start_simple.py`

## Next Steps
1. Check Flask server terminal for detailed error
2. Share the error message from Flask logs
3. Verify all imports are working: `python check_errors.py`
