import pytest
import sys

def run_stop_limit_tests():
    test_args = [
        "test/test_stop_limit_orders.py",
        "-v",
        "--tb=short"
    ]
    
    print("=" * 60)
    print("STOP-LIMIT ORDER TESTING SUITE")
    print("=" * 60)
    print()
    

    exit_code = pytest.main(test_args)
    
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    if exit_code == 0:
        print("✅ All tests passed!")
    else:
        print("❌ Some tests failed!")
    
    return exit_code

if __name__ == "__main__":
    exit_code = run_stop_limit_tests()
    sys.exit(exit_code)