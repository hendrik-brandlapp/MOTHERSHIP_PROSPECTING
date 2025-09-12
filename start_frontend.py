#!/usr/bin/env python3
"""
Start the DOUANO Frontend Server
Simple script to launch the beautiful web interface
"""

import subprocess
import sys
import webbrowser
import time
import os

def main():
    print("🚀 Starting DOUANO Frontend...")
    print("=" * 50)
    
    # Change to script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)
    
    # Check if virtual environment exists
    if not os.path.exists('venv'):
        print("❌ Virtual environment not found!")
        print("Please run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt")
        return
    
    print("✅ Virtual environment found")
    
    # Start the Flask server
    print("🌐 Starting Flask server on http://localhost:5001...")
    
    try:
        # Start server
        process = subprocess.Popen([
            'venv/bin/python', 'app.py'
        ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        
        # Wait a moment for server to start
        time.sleep(3)
        
        # Check if server is running
        if process.poll() is None:
            print("✅ Server started successfully!")
            print("🌐 Opening browser at http://localhost:5001...")
            
            # Open browser
            webbrowser.open('http://localhost:5001')
            
            print("\n🎉 DOUANO Frontend is running!")
            print("=" * 40)
            print("📊 Dashboard: http://localhost:5001")
            print("🏢 Companies: http://localhost:5001/companies") 
            print("👥 CRM: http://localhost:5001/crm")
            print("=" * 40)
            print("Press Ctrl+C to stop the server")
            
            # Wait for server
            try:
                process.wait()
            except KeyboardInterrupt:
                print("\n🛑 Shutting down server...")
                process.terminate()
                print("✅ Server stopped")
        else:
            print("❌ Failed to start server")
            stdout, stderr = process.communicate()
            if stderr:
                print(f"Error: {stderr.decode()}")
                
    except Exception as e:
        print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    main()
