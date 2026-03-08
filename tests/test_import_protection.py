#!/usr/bin/env python3
"""Test the import protection logic"""
import re

def protect_imports(content: str) -> str:
    """Apply the same logic as our fix"""
    lines = content.split('\n')
    processed_lines = []
    for line in lines:
        # Keep import/export statements untouched
        if line.strip().startswith(('import ', 'export ', 'import{', 'export{')):
            processed_lines.append(line)
        else:
            # Apply semicolon removal to prose only
            processed_lines.append(re.sub(r';\s+', '. ', line))
    return '\n'.join(processed_lines)

# Test case 1: Imports should be preserved
test1 = """import { Image } from 'astro:assets';
import { Icon } from 'astro-icon/components';

This is prose; it should change.
Another sentence; also changes."""

result1 = protect_imports(test1)
print("Test 1: Import protection")
print("=" * 50)
print(result1)
print()

# Check assertions
assert "import { Image } from 'astro:assets';" in result1, "❌ Import 1 lost semicolon"
assert "import { Icon } from 'astro-icon/components';" in result1, "❌ Import 2 lost semicolon"
assert ". import " not in result1, "❌ Imports got concatenated"
assert "prose. it should change" in result1, "❌ Prose semicolon not converted"
assert "sentence. also changes" in result1, "❌ Prose semicolon not converted"

print("✅ Test 1 PASSED: Imports preserved, prose cleaned\n")

# Test case 2: Malformed imports (should NOT happen after our fix)
test2 = """import { Image } from 'astro:assets'. import { Icon } from 'components';"""

result2 = protect_imports(test2)
print("Test 2: Malformed input (shouldn't happen but testing)")
print("=" * 50)
print(result2)
print()

# This won't fix already-malformed imports (that's what validation does)
# But it should at least not make it worse
print("✅ Test 2 PASSED: Logic doesn't crash on malformed input\n")

# Test case 3: Mixed content
test3 = """import { useState } from 'react';

## Heading

Some text; with semicolons; should be dots.
But the import above; stays intact."""

result3 = protect_imports(test3)
print("Test 3: Mixed content")
print("=" * 50)
print(result3)
print()

assert "import { useState } from 'react';" in result3, "❌ Import lost"
assert "with semicolons. should be dots" in result3, "❌ Prose not cleaned"
assert "import above. stays intact" in result3, "❌ Prose not cleaned"

print("✅ Test 3 PASSED: Mixed content handled correctly\n")

print("=" * 50)
print("🎉 ALL TESTS PASSED!")
print("=" * 50)
