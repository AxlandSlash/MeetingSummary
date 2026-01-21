"""应用入口点"""

import sys


def main():
    """主入口函数"""
    from meet_conclusion.app import run_app
    sys.exit(run_app())


if __name__ == "__main__":
    main()
