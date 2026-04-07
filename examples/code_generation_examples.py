#!/usr/bin/env python3
"""
Example usage of multi-language code generation via API.

This demonstrates how to use the generate_code action through the nlp2dsl API.
"""

import json

import requests

# Base URLs
NLP_SERVICE_URL = "http://localhost:8002"
BACKEND_URL = "http://localhost:8010"
CODE_PREVIEW_LEN: int = int("300")
SECTION_SEPARATOR = "=" * int("50")


def test_direct_code_generation() -> None:
    """Test direct code generation via nlp-service API."""
    print("=== Direct Code Generation API ===\n")

    # Test generating Python code
    payload = {
        "description": "Funkcja obliczająca NWD dwóch liczb (algorytm Euklidesa)",
        "language": "python",
        "context": "Dodaj sprawdzanie typów i dokumentację",
        "include_tests": True
    }

    try:
        response = requests.post(f"{NLP_SERVICE_URL}/code/generate", json=payload)
        if response.ok:
            result = response.json()
            print("✅ Python code generated successfully")
            print(f"Language: {result['language']}")
            print(f"Code length: {len(result['code'])} characters")
            if result.get('tests'):
                print(f"Tests included: {len(result['tests'])} characters")
            print("\nGenerated code preview:")
            preview = result['code'][:CODE_PREVIEW_LEN]
            print(f"{preview}..." if len(result['code']) > CODE_PREVIEW_LEN else preview)
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to nlp-service. Make sure it's running on port 8002")

    print(f"\n{SECTION_SEPARATOR}\n")

    # Test getting supported languages
    try:
        response = requests.get(f"{NLP_SERVICE_URL}/code/languages")
        if response.ok:
            result = response.json()
            print("Supported languages:")
            for lang, info in result['info'].items():
                print(f"  - {lang}: {info['extensions'][0]} ({info['style']})")
        else:
            print(f"❌ Error getting languages: {response.status_code}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to nlp-service")

def test_via_workflow() -> None:
    """Test code generation through the workflow API."""
    print("\n=== Code Generation via Workflow ===\n")

    # One-shot pipeline
    payload = {
        "text": "Napisz funkcję w JavaScript do sortowania bąbelkowego",
        "execute": False  # Just generate DSL, don't execute
    }

    try:
        response = requests.post(f"{BACKEND_URL}/workflow/from-text", json=payload)
        if response.ok:
            result = response.json()
            print("✅ DSL generated successfully")
            print(f"Intent: {result.get('intent', {}).get('intent')}")
            print(f"Confidence: {result.get('intent', {}).get('confidence')}")

            if 'dsl' in result:
                print("\nGenerated DSL:")
                print(json.dumps(result['dsl'], indent=2, ensure_ascii=False))
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure it's running on port 8010")

def test_conversation_flow() -> None:
    """Test code generation through conversation flow."""
    print("\n=== Code Generation via Conversation ===\n")

    # Start conversation
    try:
        response = requests.post(
            f"{NLP_SERVICE_URL}/chat/start",
            data={"text": "Chcę napisać program w Javie"}
        )

        if response.ok:
            result = response.json()
            conv_id = result.get('conversation_id')
            print(f"✅ Conversation started: {conv_id}")
            print(f"Message: {result.get('message')}")

            if result.get('missing'):
                print(f"Missing fields: {result['missing']}")

                # Continue conversation with missing details
                response = requests.post(
                    f"{NLP_SERVICE_URL}/chat/message",
                    data={
                        "conversation_id": conv_id,
                        "text": "Klasa do obsługi kalkulatora z podstawowymi operacjami"
                    }
                )

                if response.ok:
                    result = response.json()
                    print(f"\nResponse: {result.get('message')}")

                    if result.get('form'):
                        print("Form data:")
                        print(json.dumps(result['form'], indent=2, ensure_ascii=False))
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to nlp-service")

def test_worker_execution() -> None:
    """Test actual code generation through worker."""
    print("\n=== Code Generation via Worker ===\n")

    # Direct worker call
    payload = {
        "step_id": "test-001",
        "action": "generate_code",
        "config": {
            "description": "Funkcja sprawdzająca czy liczba jest pierwsza",
            "language": "cpp",
            "include_tests": False
        }
    }

    try:
        response = requests.post("http://localhost:8004/execute", json=payload)
        if response.ok:
            result = response.json()
            print("✅ Code generated via worker")
            print(f"Status: {result['status']}")

            if 'result' in result:
                gen_result = result['result']
                if 'error' in gen_result:
                    print(f"❌ Generation error: {gen_result['error']}")
                else:
                    print(f"Language: {gen_result.get('language')}")
                    print(f"Code length: {len(gen_result.get('code', ''))} characters")
        else:
            print(f"❌ Error: {response.status_code} - {response.text}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to worker. Make sure it's running on port 8004")
