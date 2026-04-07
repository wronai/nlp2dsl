"""
Code Generator — generuje kod w różnych językach programowania.

Używa LLM do generowania kodu na podstawie opisu w języku naturalnym.
Obsługuje: Python, JavaScript, Java, C++, Go, Rust, PHP, Ruby.
"""

from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional, Any
import json

try:
    import litellm
except ImportError:
    litellm = None

log = logging.getLogger("code_generator")

# Supported programming languages with their configurations
SUPPORTED_LANGUAGES = {
    "python": {
        "extensions": [".py"],
        "template": """# Generated Python code
{code}

if __name__ == "__main__":
    # Example usage
    pass
""",
        "style": "PEP 8 compliant, with type hints where appropriate"
    },
    "javascript": {
        "extensions": [".js", ".mjs"],
        "template": """// Generated JavaScript code
{code}

// Example usage
// main();
""",
        "style": "ES6+ with proper error handling"
    },
    "java": {
        "extensions": [".java"],
        "template": """// Generated Java code
public class {ClassName} {{
    {code}
    
    public static void main(String[] args) {{
        // Example usage
    }}
}}
""",
        "style": "Standard Java conventions with proper package structure"
    },
    "cpp": {
        "extensions": [".cpp", ".cc"],
        "template": """// Generated C++ code
#include <iostream>
#include <string>

{code}

int main() {{
    // Example usage
    return 0;
}}
""",
        "style": "Modern C++ (C++17/20) with RAII and smart pointers"
    },
    "go": {
        "extensions": [".go"],
        "template": """// Generated Go code
package main

import "fmt"

{code}

func main() {{
    // Example usage
}}
""",
        "style": "Idiomatic Go with proper error handling"
    },
    "rust": {
        "extensions": [".rs"],
        "template": """// Generated Rust code
{code}

fn main() {{
    // Example usage
}}
""",
        "style": "Idiomatic Rust with proper error handling and borrowing"
    },
    "php": {
        "extensions": [".php"],
        "template": """<?php
// Generated PHP code
{code}

// Example usage
?>
""",
        "style": "Modern PHP (8.x) with proper typing"
    },
    "ruby": {
        "extensions": [".rb"],
        "template": """# Generated Ruby code
{code}

# Example usage
# main
""",
        "style": "Idiomatic Ruby with proper conventions"
    }
}


class CodeGenerator:
    """Generates code in multiple programming languages using LLM."""
    
    def __init__(self):
        self.model = os.getenv("LLM_MODEL", "openrouter/openai/gpt-5-mini")
        self.api_key = self._get_api_key()
        self.max_tokens = 4000
        
    def _get_api_key(self) -> Optional[str]:
        """Get API key based on model provider."""
        if "openrouter" in self.model:
            return os.getenv("OPENROUTER_API_KEY")
        elif "openai" in self.model:
            return os.getenv("OPENAI_API_KEY")
        elif "anthropic" in self.model:
            return os.getenv("ANTHROPIC_API_KEY")
        elif "groq" in self.model:
            return os.getenv("GROQ_API_KEY")
        return None
    
    def _build_prompt(self, description: str, language: str, context: Optional[str] = None) -> str:
        """Build the LLM prompt for code generation."""
        lang_config = SUPPORTED_LANGUAGES.get(language, SUPPORTED_LANGUAGES["python"])
        
        prompt = f"""Generate {language} code for the following task:

Task: {description}

Requirements:
- Write clean, production-ready code
- Follow {lang_config['style']}
- Include appropriate error handling
- Add comments for complex logic
- NO explanatory text, ONLY code
"""
        
        if context:
            prompt += f"\nAdditional context: {context}\n"
        
        prompt += f"\nGenerate only the code block without markdown formatting."
        
        return prompt
    
    async def generate_code(
        self, 
        description: str, 
        language: str = "python",
        context: Optional[str] = None,
        include_tests: bool = False
    ) -> Dict[str, Any]:
        """
        Generate code in the specified language.
        
        Args:
            description: Natural language description of what to generate
            language: Target programming language
            context: Additional context for code generation
            include_tests: Whether to include unit tests
            
        Returns:
            Dictionary with generated code and metadata
        """
        if language not in SUPPORTED_LANGUAGES:
            return {
                "error": f"Unsupported language: {language}",
                "supported": list(SUPPORTED_LANGUAGES.keys())
            }
        
        if not litellm or not self.api_key:
            return {
                "error": "LLM not configured. Set appropriate API key.",
                "model": self.model
            }
        
        try:
            # Build prompt
            prompt = self._build_prompt(description, language, context)
            
            # Add test generation if requested
            if include_tests:
                prompt += "\n\nAlso generate unit tests for the code."
            
            # Call LLM
            response = await litellm.acompletion(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self.max_tokens,
                temperature=0.1
            )
            
            generated_code = response.choices[0].message.content.strip()
            
            # Apply template if needed
            lang_config = SUPPORTED_LANGUAGES[language]
            if language == "java" and "class" not in generated_code:
                class_name = self._extract_class_name(description) or "GeneratedCode"
                generated_code = lang_config["template"].format(
                    code=generated_code,
                    ClassName=class_name
                )
            elif language in ["cpp", "go", "rust", "php", "ruby", "javascript", "python"]:
                if not any(generated_code.startswith(prefix) for prefix in ["//", "#", "/*", "<?php"]):
                    generated_code = lang_config["template"].format(code=generated_code)
            
            # Prepare response
            result = {
                "language": language,
                "code": generated_code,
                "description": description,
                "extensions": lang_config["extensions"],
                "model": self.model,
                "tokens_used": response.usage.total_tokens if response.usage else None
            }
            
            if include_tests:
                # Split code and tests if both were generated
                result = self._split_code_and_tests(generated_code, result)
            
            return result
            
        except Exception as e:
            log.exception("Code generation failed")
            return {
                "error": f"Code generation failed: {str(e)}",
                "language": language,
                "description": description
            }
    
    def _extract_class_name(self, description: str) -> Optional[str]:
        """Extract a suitable class name from description."""
        import re
        words = re.findall(r'\b\w+\b', description.title())
        if words:
            return words[0] + "Class"
        return None
    
    def _split_code_and_tests(self, combined: str, result: Dict) -> Dict:
        """Split generated code into main code and tests."""
        # Simple heuristic - look for test markers
        test_markers = ["// Tests", "# Tests", "/* Tests", "def test", "function test", "test("]
        
        for marker in test_markers:
            if marker in combined:
                parts = combined.split(marker, 1)
                result["code"] = parts[0].strip()
                result["tests"] = marker + parts[1].strip()
                return result
        
        result["tests"] = None
        return result
    
    def get_supported_languages(self) -> List[str]:
        """Get list of supported programming languages."""
        return list(SUPPORTED_LANGUAGES.keys())
    
    def get_language_info(self, language: str) -> Optional[Dict]:
        """Get information about a specific language."""
        return SUPPORTED_LANGUAGES.get(language)


# Singleton instance
code_generator = CodeGenerator()
