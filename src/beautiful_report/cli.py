"""
CLI for pytest-glow-report.

Provides commands for running unittest with report generation,
serving reports locally, and converting JUnit XML.
"""
import argparse
import subprocess
import sys
from typing import List


def main() -> None:
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        prog="glow-report",
        description="Beautiful, glowing HTML test reports"
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Run command (wrapper for unittest)
    run_parser = subparsers.add_parser("run", help="Run unittest tests with report generation")
    run_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments to pass to unittest")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Serve reports locally")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to serve on")
    serve_parser.add_argument("dir", nargs="?", default="reports", help="Directory to serve")
    
    # Convert command
    convert_parser = subparsers.add_parser("convert", help="Convert JUnit XML to HTML report")
    convert_parser.add_argument("input_file", help="Input JUnit XML file")
    convert_parser.add_argument("output_file", help="Output HTML file")

    args = parser.parse_args()

    if args.command == "run":
        _run_unittest(args.args)
    elif args.command == "serve":
        _serve_reports(args.dir, args.port)
    elif args.command == "convert":
        _convert_junit(args.input_file, args.output_file)
    else:
        parser.print_help()


def _run_unittest(cmd_args: List[str]) -> None:
    """Run unittest with BeautifulTestRunner."""
    cmd = list(cmd_args)
    
    if cmd and cmd[0] == '--':
        cmd.pop(0)
        
    if not cmd:
        print("Error: No test command provided.")
        print("Usage: glow-report run -- unittest discover tests")
        sys.exit(1)
    
    if cmd and cmd[0] == "unittest":
        sys.argv = [sys.argv[0]] + cmd[1:]
        from .unittest_runner import BeautifulTestRunner
        import unittest
        
        print(f"Running unittest with GlowReport: {sys.argv}")
        try:
            unittest.main(module=None, testRunner=BeautifulTestRunner, argv=sys.argv)
        except SystemExit as e:
            sys.exit(e.code if e.code else 0)
    else:
        subprocess.run(cmd, check=True)


def _serve_reports(directory: str, port: int) -> None:
    """Serve reports directory via HTTP."""
    import http.server
    import os
    
    os.chdir(directory)
    handler = http.server.SimpleHTTPRequestHandler
    
    with http.server.HTTPServer(("", port), handler) as httpd:
        print(f"Serving {directory} at http://localhost:{port}")
        print("Press Ctrl+C to stop")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")


def _convert_junit(input_file: str, output_file: str) -> None:
    """Convert JUnit XML to HTML report."""
    print(f"Converting {input_file} to {output_file}...")
    print("Note: JUnit conversion is not yet implemented.")


if __name__ == "__main__":
    main()
