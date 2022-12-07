#!/usr/bin/env python3
import os
from subprocess import run, STDOUT, PIPE

def main():
    TEST_PATH_DIR = "./tests"
    FLO_COMPILER_PROG_PATH = "./flo"
    print("-------------------Running tests-------------------")
    failed_test_suits = 0
    passed_test_suits = 0
    failed_tests = 0
    passed_tests = 0
    for dir in os.scandir(TEST_PATH_DIR):
        test_name = dir.name.capitalize()
        failed_suites = False
        print(f"\033[1mRunning {test_name} Test suite:\033[0m")
        for file in os.scandir(os.path.join(TEST_PATH_DIR, dir.name)):
            abs_file_path = os.path.join(TEST_PATH_DIR, dir.name, file.name)
            if os.path.isdir(abs_file_path):
                continue
            p = run([FLO_COMPILER_PROG_PATH, abs_file_path], stdout=PIPE, stderr=STDOUT)
            expected_return_code = parse_return_code(abs_file_path)
            if p.returncode != expected_return_code:
                failed_tests+=1
                print(f"\033[41mFailed\033[0m Test {file.name}: return code {p.returncode}")
                stdout = str(p.stdout, 'utf-8')[0:-1] if p.returncode != -11 else "Segmentation fault"
                print(f"\033[31m>>> {stdout}\033[0m")
                failed_suites = True
            else:
                print(f"\033[42mPassed\033[0m Test {file.name} passed!")
                passed_tests+=1
        if failed_suites:
            failed_test_suits+=1
        else:
            passed_test_suits+=1
        print("---------------------------------------------")
    print(f"Test Suites: \033[31;1m{failed_test_suits} failed\033[0m, \033[32;1m{passed_test_suits} passed\033[0m, {passed_test_suits+failed_test_suits} total")
    print(f"Tests:       \033[31;1m{failed_tests} failed\033[0m, \033[32;1m{passed_tests} passed\033[0m, {passed_tests+failed_tests} total")

def parse_return_code(filename):
     with open(filename) as f:
        first_line = f.readline()
        if first_line.startswith("//@expect:"):
            idx = first_line.find("return_code=")
            idx+=len("return_code=")
            return int(first_line[idx:])
        else:
            return 0


if __name__ == "__main__":
    main()