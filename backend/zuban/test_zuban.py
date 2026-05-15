import sys
import os

# Force UTF-8 output so Urdu/Arabic characters display correctly on Windows
sys.stdout.reconfigure(encoding='utf-8')

# Add the project root to sys.path so we can import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from backend.zuban.zuban_agent import ZubanAgent

def run_tests():
    agent = ZubanAgent()

    test_cases = [
        ("Roman Urdu",  "Mujhe kal subah G-13 mein AC technician chahiye"),
        ("Urdu",        "مجھے کل صبح جی تیرہ میں اے سی ٹیکنیشن چاہیے"),
        ("English",     "I need a plumber in DHA tomorrow afternoon"),
        ("Mixed",       "bhai koi acha electrician hai Gulshan mein? urgent hai"),
        ("Edge case",   "help"), # Very short input — tests low-confidence path
    ]

    passed = 0
    for i, (label, text) in enumerate(test_cases):
        print(f"\n--- Test Case {i+1}: {label} ---")
        print(f"Input : {text}")
        try:
            response = agent.parse_input(text)
            print(f"Output: {response.model_dump_json(indent=2)}")
            passed += 1
        except ValueError as e:
            # Expected for edge cases (e.g., ambiguous / unrecognisable input)
            print(f"[HANDLED] {e}")
        except Exception as e:
            print(f"[ERROR]   {e}")

    print(f"\n{'='*40}")
    print(f"Tests passed: {passed}/{len(test_cases)}")

if __name__ == "__main__":
    run_tests()
