import pathlib
import subprocess
import sys


def main():
    tests = sys.argv[1:]
    passed = 0
    for test in tests:
        result = run_test(test)
        if result:
            print(f"Test {test} passed!")
            passed += 1
        else:
            print(f"Test {test} failed!")
        print("-----------------------")
    print(f"{passed}/{len(tests)} tests passed")


def run_test(name):
    root_path = pathlib.Path(__file__).parent.parent.resolve()
    filename = f"{root_path}/tests/{name}.flo"
    expected_output_file = f"{root_path}/tests/{name}.txt"
    result = subprocess.run(
        f"{root_path}/.venv/Scripts/activate && py {root_path}/src/flo.py -e {filename}", shell=True, capture_output=True, text=True)
    with open(expected_output_file, "r") as f:
        expected_output = f.read()
        return result.stdout == expected_output


if __name__ == "__main__":
    main()
