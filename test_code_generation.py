#!/usr/bin/env python3
"""
Test script for multi-language code generation in nlp2dsl.

This script tests the generate_code action with different programming languages.
"""

import sys
from pathlib import Path

# Add nlp-service to path
sys.path.insert(0, str(Path(__file__).parent / "nlp-service" / "app"))

from code_generator import code_generator


async def test_code_generation():
    """Test code generation for all supported languages."""
    
    test_cases = [
        {
            "description": "Funkcja obliczająca silnię liczby",
            "language": "python",
            "context": "Użyj rekurencji i dodaj sprawdzanie argumentów"
        },
        {
            "description": "Funkcja sortująca tablicę liczb",
            "language": "javascript",
            "context": "Użyj algorytmu quicksort"
        },
        {
            "description": "Klasa reprezentująca punkt w 2D",
            "language": "java",
            "context": "Z metodami do obliczania odległości"
        },
        {
            "description": "Funkcja odwracająca string",
            "language": "cpp",
            "context": "Użyj STL i iteratory"
        },
        {
            "description": "Prosty serwer HTTP",
            "language": "go",
            "context": "Użyj standardowego pakietu net/http"
        },
        {
            "description": "Struktura drzewa binarnego",
            "language": "rust",
            "context": "Z operacjami wstawiania i przeszukiwania"
        },
        {
            "description": "Klasa do połączenia z bazą danych",
            "language": "php",
            "context": "Użyj PDO i obsługi błędów"
        },
        {
            "description": "Generator liczb Fibonacciego",
            "language": "ruby",
            "context": "Użyj yield i enumerator"
        }
    ]
    
    print("=== Testing Multi-Language Code Generation ===\n")
    
    supported = code_generator.get_supported_languages()
    print(f"Supported languages: {', '.join(supported)}\n")
    
    results = {}
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['language']} - {test['description'][:50]}...")
        
        result = await code_generator.generate_code(
            description=test["description"],
            language=test["language"],
            context=test.get("context"),
            include_tests=True
        )
        
        if "error" in result:
            print(f"  ❌ Error: {result['error']}")
            results[test["language"]] = {"status": "error", "message": result["error"]}
        else:
            print(f"  ✅ Generated {len(result['code'])} characters")
            if result.get("tests"):
                print(f"  ✅ Tests included ({len(result['tests'])} characters)")
            results[test["language"]] = {
                "status": "success",
                "code_length": len(result["code"]),
                "has_tests": bool(result.get("tests"))
            }
            
            # Save generated code to files
            lang_info = code_generator.get_language_info(test["language"])
            ext = lang_info["extensions"][0]
            filename = f"generated_{test['language']}_test{ext}"
            
            with open(filename, "w", encoding="utf-8") as f:
                f.write(result["code"])
            
            if result.get("tests"):
                test_filename = f"generated_{test['language']}_test_tests{ext}"
                with open(test_filename, "w", encoding="utf-8") as f:
                    f.write(result["tests"])
        
        print()
    
    # Summary
    print("=== Summary ===")
    success_count = sum(1 for r in results.values() if r["status"] == "success")
    print(f"Successful: {success_count}/{len(test_cases)}")
    
    for lang, result in results.items():
        status = "✅" if result["status"] == "success" else "❌"
        print(f"  {status} {lang}: {result['status']}")
    
    # Test invalid language
    print("\n=== Testing Invalid Language ===")
    invalid_result = await code_generator.generate_code(
        description="Test code",
        language="brainfuck"
    )
    if "error" in invalid_result:
        print("✅ Invalid language properly rejected")
    
    # Test without API key (simulate)
    print("\n=== Testing Without LLM Configuration ===")
    original_api_key = code_generator.api_key
    code_generator.api_key = None
    no_key_result = await code_generator.generate_code(
        description="Test code",
        language="python"
    )
    if "error" in no_key_result:
        print("✅ Missing API key properly detected")
    code_generator.api_key = original_api_key
    
    print("\n=== Test Complete ===")
    return results
