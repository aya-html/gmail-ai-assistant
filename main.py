#!/usr/bin/env python
# coding: utf-8

# 🚀 Flask Main App - Gmail Assistant (Lightweight API-Only Version)
# Perfect for pure API deployment without web dashboard

from flask import Flask, request, jsonify
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

# === API Routes Only ===

@app.route('/')
def root():
    """Simple API info endpoint"""
    return jsonify({
        'service': 'Gmail Assistant API',
        'version': '1.0.0',
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'endpoints': {
            '/': 'API Info',
            '/health': 'Health Check',
            '/process-emails': 'Process Gmail (POST)',
            '/api/status': 'Detailed Status'
        },
        'usage': {
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
        'deployment_type': 'api_only',
        'timestamp': datetime.now().isoformat(),
        'environment': {
            'port': os.environ.get('PORT', '5000'),
            'flask_env': os.environ.get('FLASK_ENV', 'production'),
            'python_version': os.sys.version.split()[0]
        },
        'endpoints': {
            '/': 'API Info',
            '/health': 'Health Check',
            '/process-emails': 'Process Gmail (POST only)',
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
        'available_endpoints': ['/', '/health', '/process-emails (POST)', '/api/status'],
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
    print("🚀 Starting Gmail Assistant API...")
    print("📊 API Info: http://localhost:5000")
    print("🔍 Health Check: http://localhost:5000/health")
    print("📧 Process Emails: POST http://localhost:5000/process-emails")
    
    # Check environment on startup
    required_vars = ['OPENAI_API_KEY', 'NOTION_TOKEN', 'NOTION_DB_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"⚠️ WARNING: Missing environment variables: {', '.join(missing_vars)}")
        print("💡 Make sure to set them before processing emails!")
    else:
        print("✅ All environment variables configured!")
    
    # Run Flask app
    app.run(
        host='0.0.0.0',  # Accept connections from any IP
        port=int(os.environ.get('PORT', 5000)),  # Use PORT env var for cloud deployment
        debug=os.environ.get('FLASK_ENV') == 'development'  # Debug mode only in development
    )
    