"""
Simple test script for the FastAPI backend
"""
import requests
import json
from dotenv import load_dotenv
import os

load_dotenv()


BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint"""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

def test_models():
    """Test models endpoint"""
    print("Testing models endpoint...")
    response = requests.get(f"{BASE_URL}/models")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}\n")

def test_chat():
    """Test chat endpoint"""
    print("Testing chat endpoint...")
    
    payload = {
        "question": "What is an agent?",
        "groq_api_key": os.getenv("GROQ_API_KEY")
    }
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json=payload
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Question: {result['question']}")
        print(f"Answer: {result['answer']}")
        print(f"Documents Used: {result['documents_used']}")
        print(f"\nProcessing Steps:")
        for step in result['steps']:
            print(f"  - {step}")
    else:
        print(f"Error: {response.json()}")

if __name__ == "__main__":
    print("=" * 50)
    print("FastAPI Backend Test")
    print("=" * 50 + "\n")
    
    test_health()
    test_models()
    test_chat()
