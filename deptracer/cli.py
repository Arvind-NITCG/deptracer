# deptracer/cli.py
import argparse
import sys
from .core import run_akdeptracer
from .explain import explain_problem

def main():
    cli_parser = argparse.ArgumentParser(prog="deptracer", description="Universal Dependency Auto-Patcher")
    subparsers = cli_parser.add_subparsers(dest="command", help="Available engine commands")
    
    build_parser = subparsers.add_parser("build", help="Initiate the self-healing loop")
    build_parser.add_argument("project_dir", help="Path to the folder containing the .spec file")
    build_parser.add_argument("binary_name", help="Name of the executable")
    build_parser.add_argument("spec_name", help="Name of the .spec file")
    

    subparsers.add_parser("explain", help="Diagnose the last failed compilation trace")

    args = cli_parser.parse_args()

    if args.command == "explain":
        explain_problem()
    elif args.command == "build":
        run_akdeptracer(args.project_dir, args.binary_name, args.spec_name, verbose=args.verbose)
    else:
        cli_parser.print_help()

if __name__ == "__main__":
    main()