import sys
import subprocess
import os

def run_script(script_path):
    print(f"=== Running {os.path.basename(script_path)} ===")
    res = subprocess.run([sys.executable, script_path])
    if res.returncode != 0:
        print(f"FAILED: {script_path} exited with code {res.returncode}")
        return False
    print("=== Done ===\n")
    return True

def main():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    tests_dir = os.path.join(root_dir, "tests")

    args = sys.argv[1:]
    if not args:
        print("Inky Calendar Test Runner")
        print("Usage: python run_tests.py [parse | render | fetch | all]")
        print("  parse  - Reads local test ICS file and generates representation JSON spec")
        print("  render - Reads representation JSON spec and renders list and grid images")
        print("  fetch  - Fetches target calendar URL from config to verify connection")
        print("  all    - Runs parse, then render, then fetch")
        sys.exit(0)

    cmd = args[0]
    success = True

    if cmd == "parse":
        success = run_script(os.path.join(tests_dir, "test_parser.py"))
    elif cmd == "render":
        success = run_script(os.path.join(tests_dir, "test_renderer.py"))
    elif cmd == "fetch":
        success = run_script(os.path.join(tests_dir, "test_fetcher.py"))
    elif cmd == "all":
        success = run_script(os.path.join(tests_dir, "test_parser.py"))
        if success:
            success = run_script(os.path.join(tests_dir, "test_renderer.py"))
        if success:
            # fetch requires network and valid url config, so run it but don't fail overall tests if offline
            run_script(os.path.join(tests_dir, "test_fetcher.py"))
    else:
        print(f"Unknown test command: {cmd}")
        sys.exit(1)

    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main()
