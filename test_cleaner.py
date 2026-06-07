"""
test_cleaner.py - Terminal Test for llm_cleaner

Usage:
    python test_cleaner.py
"""

from LLM_Cleaner import llm_clean_text

print("\n" + "="*60)
print("  LLM Text Cleaner - Terminal Test")
print("="*60)
print("  Type your text and press Enter to clean it.")
print("  Type 'quit' to exit.\n")

QUICK_TESTS = [
    "This AI system uses API calls and the GFPGAN model for our FYP at UCP university. Well done team!",
    "Visit https://my-fyp.com/results & email ali@test.com for 95% accuracy info.",
    "state-of-the-art real-time processing costs $500 approx.",
]

print("Run quick built-in tests? (y/n): ", end="", flush=True)
choice = input().strip().lower()

if choice == "y":
    print("\n" + "-"*60)
    for i, test in enumerate(QUICK_TESTS, 1):
        print(f"\n[Test {i}]")
        print(f"  INPUT  : {test}")
        result = llm_clean_text(test)
        print(f"  OUTPUT : {result}")
        print(f"  CHANGE : {'YES - ' + str(len(test)-len(result)) + ' chars removed' if result != test else 'NO CHANGE'}")
    print("\n" + "-"*60)

print("\n--- Manual Test Mode ---")
print("Enter your text below:\n")

while True:
    try:
        user_input = input("INPUT  > ").strip()

        if user_input.lower() in ("quit", "exit", "q"):
            print("\nBye!")
            break

        if not user_input:
            print("  (empty — try again)\n")
            continue

        print("  Cleaning via Azure OpenAI...")
        result = llm_clean_text(user_input)

        print(f"OUTPUT > {result}")
        print(f"CHARS  : {len(user_input)} -> {len(result)} ({'no change' if result == user_input else str(len(user_input) - len(result)) + ' chars removed'})\n")

    except KeyboardInterrupt:
        print("\n\nBye!")
        break
