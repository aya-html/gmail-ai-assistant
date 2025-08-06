#!/usr/bin/env python
# coding: utf-8

# 🚀 Flask Main App - Gmail Assistant (Web Dashboard + API)
# Professional SaaS-style interface with mobile support

from flask import Flask, request, jsonify, render_template_string
import os
import logging
from datetime import datetime
import traceback

# Import our assistant logic
from assistant import run_assistant

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# === HTML DASHBOARD TEMPLATE ===
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gmail Assistant Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 1rem;
            line-height: 1.6;
        }
        
        .container {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            overflow: hidden;
            animation: slideUp 0.6s ease-out;
        }
        
        @keyframes slideUp {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .header {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: white;
            padding: 2rem;
            text-align: center;
            position: relative;
            overflow: hidden;
        }
        
        .header::before {
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
            background-size: 30px 30px;
            animation: float 20s infinite linear;
        }
        
        @keyframes float {
            0% { transform: translate(0, 0); }
            100% { transform: translate(30px, 30px); }
        }
        
        .header h1 {
            font-size: clamp(1.8rem, 4vw, 2.5rem);
            font-weight: 700;
            margin-bottom: 0.5rem;
            position: relative;
            z-index: 1;
        }
        
        .header p {
            font-size: clamp(1rem, 2.5vw, 1.2rem);
            opacity: 0.9;
            position: relative;
            z-index: 1;
        }
        
        .content {
            padding: 2rem;
        }
        
        .status-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .status-card {
            background: #f8fafc;
            border: 2px solid #e2e8f0;
            border-radius: 12px;
            padding: 1.5rem;
            text-align: center;
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }
        
        .status-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0,0,0,0.1);
            border-color: #4f46e5;
        }
        
        .status-card.ready {
            border-color: #10b981;
            background: linear-gradient(135deg, #ecfdf5 0%, #f0fdf4 100%);
        }
        
        .status-card.error {
            border-color: #ef4444;
            background: linear-gradient(135deg, #fef2f2 0%, #fef2f2 100%);
        }
        
        .status-icon {
            font-size: 2rem;
            margin-bottom: 0.5rem;
            display: block;
        }
        
        .status-title {
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 0.5rem;
            font-size: 1.1rem;
        }
        
        .status-value {
            color: #64748b;
            font-size: 0.9rem;
        }
        
        .action-section {
            text-align: center;
            margin: 2rem 0;
        }
        
        .process-btn {
            background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
            color: white;
            border: none;
            padding: 1rem 2rem;
            border-radius: 50px;
            font-size: 1.1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 4px 15px rgba(79, 70, 229, 0.3);
            position: relative;
            overflow: hidden;
            width: 100%;
            max-width: 300px;
        }
        
        .process-btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(79, 70, 229, 0.4);
        }
        
        .process-btn:active {
            transform: translateY(0);
        }
        
        .process-btn:disabled {
            background: #9ca3af;
            cursor: not-allowed;
            transform: none;
            box-shadow: none;
        }
        
        .process-btn::before {
            content: '';
            position: absolute;
            top: 0;
            left: -100%;
            width: 100%;
            height: 100%;
            background: linear-gradient(90deg, transparent, rgba(255,255,255,0.2), transparent);
            transition: left 0.5s ease;
        }
        
        .process-btn:hover::before {
            left: 100%;
        }
        
        .results {
            margin-top: 2rem;
            padding: 1.5rem;
            background: #f8fafc;
            border-radius: 12px;
            border-left: 4px solid #4f46e5;
            display: none;
        }
        
        .results.show {
            display: block;
            animation: fadeIn 0.5s ease-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .results h3 {
            color: #1e293b;
            margin-bottom: 1rem;
            font-size: 1.2rem;
        }
        
        .results pre {
            background: #1e293b;
            color: #e2e8f0;
            padding: 1rem;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9rem;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        .loading {
            display: none;
            text-align: center;
            color: #64748b;
            margin: 1rem 0;
        }
        
        .loading.show {
            display: block;
        }
        
        .spinner {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 2px solid #e2e8f0;
            border-radius: 50%;
            border-top-color: #4f46e5;
            animation: spin 1s ease-in-out infinite;
            margin-right: 0.5rem;
        }
        
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
        
        .footer {
            background: #f8fafc;
            padding: 1.5rem;
            text-align: center;
            color: #64748b;
            font-size: 0.9rem;
        }
        
        .api-links {
            margin-top: 1rem;
            display: flex;
            gap: 1rem;
            justify-content: center;
            flex-wrap: wrap;
        }
        
        .api-link {
            color: #4f46e5;
            text-decoration: none;
            font-weight: 500;
            padding: 0.5rem 1rem;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            transition: all 0.3s ease;
            font-size: 0.9rem;
        }
        
        .api-link:hover {
            background: #4f46e5;
            color: white;
            transform: translateY(-1px);
        }
        
        /* Mobile Optimizations */
        @media (max-width: 640px) {
            body {
                padding: 0.5rem;
            }
            
            .header {
                padding: 1.5rem;
            }
            
            .content {
                padding: 1.5rem;
            }
            
            .status-grid {
                grid-template-columns: 1fr;
                gap: 1rem;
            }
            
            .status-card {
                padding: 1rem;
            }
            
            .process-btn {
                padding: 0.875rem 1.5rem;
                font-size: 1rem;
            }
            
            .api-links {
                flex-direction: column;
                align-items: center;
            }
            
            .api-link {
                width: 100%;
                max-width: 200px;
                text-align: center;
            }
        }
        
        /* Dark mode support */
        @media (prefers-color-scheme: dark) {
            body {
                background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
            }
            
            .container {
                background: #1e293b;
                color: #e2e8f0;
            }
            
            .status-card {
                background: #334155;
                border-color: #475569;
                color: #e2e8f0;
            }
            
            .status-title {
                color: #e2e8f0;
            }
            
            .results {
                background: #334155;
                color: #e2e8f0;
            }
            
            .footer {
                background: #334155;
                color: #94a3b8;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📧 Gmail Assistant</h1>
            <p>AI-powered email processing with Notion integration</p>
        </div>
        
        <div class="content">
            <div class="status-grid">
                <div class="status-card {{ 'ready' if openai_key else 'error' }}">
                    <span class="status-icon">{{ '🤖' if openai_key else '❌' }}</span>
                    <div class="status-title">OpenAI API</div>
                    <div class="status-value">{{ 'Connected' if openai_key else 'Missing Key' }}</div>
                </div>
                
                <div class="status-card {{ 'ready' if notion_token else 'error' }}">
                    <span class="status-icon">{{ '📝' if notion_token else '❌' }}</span>
                    <div class="status-title">Notion Token</div>
                    <div class="status-value">{{ 'Connected' if notion_token else 'Missing Token' }}</div>
                </div>
                
                <div class="status-card {{ 'ready' if notion_db else 'error' }}">
                    <span class="status-icon">{{ '🗄️' if notion_db else '❌' }}</span>
                    <div class="status-title">Notion Database</div>
                    <div class="status-value">{{ 'Connected' if notion_db else 'Missing DB ID' }}</div>
                </div>
            </div>
            
            <div class="action-section">
                <button 
                    id="processBtn" 
                    class="process-btn"
                    {{ 'disabled' if not (openai_key and notion_token and notion_db) else '' }}
                >
                    🚀 Process Gmail Inbox
                </button>
                
                <div id="loading" class="loading">
                    <span class="spinner"></span>
                    Processing your emails...
                </div>
                
                <div id="results" class="results">
                    <h3>📊 Processing Results</h3>
                    <pre id="resultsContent"></pre>
                </div>
            </div>
        </div>
        
        <div class="footer">
            <p>Gmail Assistant API v1.0.0 • Powered by OpenAI & Notion</p>
            <div class="api-links">
                <a href="/api/info" class="api-link">📋 API Info</a>
                <a href="/health" class="api-link">💓 Health Check</a>
                <a href="/api/status" class="api-link">📊 Status</a>
            </div>
        </div>
    </div>

    <script>
        document.getElementById('processBtn').addEventListener('click', async function() {
            const btn = this;
            const loading = document.getElementById('loading');
            const results = document.getElementById('results');
            const resultsContent = document.getElementById('resultsContent');
            
            // Show loading state
            btn.disabled = true;
            btn.textContent = '⏳ Processing...';
            loading.classList.add('show');
            results.classList.remove('show');
            
            try {
                const response = await fetch('/process-emails', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                
                const data = await response.json();
                
                // Show results
                resultsContent.textContent = JSON.stringify(data, null, 2);
                results.classList.add('show');
                
                // Scroll to results
                results.scrollIntoView({ behavior: 'smooth' });
                
            } catch (error) {
                resultsContent.textContent = `Error: ${error.message}`;
                results.classList.add('show');
            } finally {
                // Reset button state
                btn.disabled = false;
                btn.textContent = '🚀 Process Gmail Inbox';
                loading.classList.remove('show');
            }
        });
        
        // Auto-refresh status every 30 seconds
        setInterval(() => {
            location.reload();
        }, 30000);
    </script>
</body>
</html>
'''

# === WEB DASHBOARD ROUTE ===

@app.route('/')
def dashboard():
    """Main dashboard - serves the HTML interface"""
    return render_template_string(HTML_TEMPLATE, 
        openai_key=bool(os.getenv('OPENAI_API_KEY')),
        notion_token=bool(os.getenv('NOTION_TOKEN')), 
        notion_db=bool(os.getenv('NOTION_DB_ID'))
    )

# === API ROUTES ===

@app.route('/api/info')
def api_info():
    """API information endpoint (moved from root)"""
    return jsonify({
        'service': 'Gmail Assistant API',
        'version': '1.0.0',
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            '/': 'Dashboard UI (HTML)',
            '/health': 'Health Check',
            '/process-emails': 'Process Gmail (POST)',
            '/api/status': 'Detailed Status',
            '/api/info': 'This endpoint'
        },
        'usage': {
            'dashboard': 'GET /',
            'process_emails': 'POST /process-emails',
            'health_check': 'GET /health'
        }
    })

@app.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Check required environment variables
        required_vars = ['OPENAI_API_KEY', 'NOTION_TOKEN', 'NOTION_DB_ID']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            return jsonify({
                'status': 'error',
                'message': f'Missing environment variables: {", ".join(missing_vars)}',
                'timestamp': datetime.now().isoformat(),
                'ready': False
            }), 500
        
        # Try to import Google Auth (basic DWDA check)
        try:
            import google.auth
            creds, project = google.auth.default()
            dwda_status = 'configured'
            project_id = project if project else 'detected'
        except Exception as e:
            dwda_status = f'error: {str(e)}'
            project_id = 'unknown'
        
        return jsonify({
            'status': 'healthy',
            'message': 'Gmail Assistant is ready',
            'dwda_auth': dwda_status,
            'project_id': project_id,
            'environment_vars': {
                'openai_api_key': bool(os.getenv('OPENAI_API_KEY')),
                'notion_token': bool(os.getenv('NOTION_TOKEN')),
                'notion_db_id': bool(os.getenv('NOTION_DB_ID'))
            },
            'timestamp': datetime.now().isoformat(),
            'ready': True
        })
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': str(e),
            'timestamp': datetime.now().isoformat(),
            'ready': False
        }), 500

@app.route('/process-emails', methods=['POST'])
def process_emails():
    """Main endpoint to process Gmail emails"""
    try:
        logger.info("Starting email processing...")
        start_time = datetime.now()
        
        # Run the assistant
        result = run_assistant()
        
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()
        
        logger.info(f"Email processing completed successfully in {processing_time:.2f} seconds")
        
        return jsonify({
            'status': 'success',
            'message': 'Email processing completed',
            'result': result,
            'processing_time_seconds': processing_time,
            'timestamp': end_time.isoformat()
        }), 200
        
    except ValueError as e:
        # Configuration errors
        error_msg = f"Configuration Error: {str(e)}"
        logger.error(error_msg)
        return jsonify({
            'status': 'error',
            'error_type': 'configuration',
            'message': error_msg,
            'timestamp': datetime.now().isoformat()
        }), 400
        
    except Exception as e:
        # Unexpected errors
        error_msg = f"Processing Error: {str(e)}"
        logger.error(f"{error_msg}\n\nTraceback:\n{traceback.format_exc()}")
        return jsonify({
            'status': 'error',
            'error_type': 'processing',
            'message': error_msg,
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/api/status')
def api_status():
    """Detailed API status endpoint"""
    return jsonify({
        'service': 'Gmail Assistant API',
        'version': '1.0.0',
        'status': 'running',
        'deployment_type': 'web_dashboard_plus_api',
        'timestamp': datetime.now().isoformat(),
        'environment': {
            'port': os.environ.get('PORT', '5000'),
            'flask_env': os.environ.get('FLASK_ENV', 'production'),
            'python_version': os.sys.version.split()[0]
        },
        'endpoints': {
            '/': 'Web Dashboard (HTML)',
            '/health': 'Health Check',
            '/process-emails': 'Process Gmail (POST only)',
            '/api/info': 'API Information',
            '/api/status': 'This endpoint'
        }
    })

# === Error Handlers ===

@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({
        'error': 'Method not allowed',
        'message': 'Check the HTTP method. /process-emails requires POST.',
        'timestamp': datetime.now().isoformat()
    }), 405

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'error': 'Endpoint not found',
        'message': 'Please check the URL and try again',
        'available_endpoints': ['/', '/health', '/process-emails (POST)', '/api/info', '/api/status'],
        'timestamp': datetime.now().isoformat()
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        'error': 'Internal server error',
        'message': 'Something went wrong on our end',
        'timestamp': datetime.now().isoformat()
    }), 500

# === Main Application Entry Point ===

if __name__ == '__main__':
    # For local development
    print("🚀 Starting Gmail Assistant Dashboard...")
    print("🌐 Dashboard: http://localhost:5000")
    print("🔍 Health Check: http://localhost:5000/health")
    print("📋 API Info: http://localhost:5000/api/info")
    print("📧 Process Emails: POST http://localhost:5000/process-emails")
    
    # Check environment on startup
    required_vars = ['OPENAI_API_KEY', 'NOTION_TOKEN', 'NOTION_DB_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️ WARNING: Missing environment variables: {', '.join(missing_vars)}")
        print("💡 Dashboard will show configuration issues!")
    else:
        print("✅ All environment variables configured!")
    
    # Run Flask app
    app.run(
        host='0.0.0.0',  # Accept connections from any IP
        port=int(os.environ.get('PORT', 5000)),  # Use PORT env var for cloud deployment
        debug=os.environ.get('FLASK_ENV') == 'development'  # Debug mode only in development
    )
    
