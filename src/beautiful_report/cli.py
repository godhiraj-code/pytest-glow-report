import argparse
import sys
import subprocess
from typing import List, Optional

def main() -> None:
    parser = argparse.ArgumentParser(description="Beautiful Report CLI")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Run command (wrapper for unittest)
    run_parser = subparsers.add_parser("run", help="Run tests with beautiful reporting")
    run_parser.add_argument("args", nargs=argparse.REMAINDER, help="Arguments to pass to the test runner")

    # Serve command (placeholder)
    serve_parser = subparsers.add_parser("serve", help="Serve reports locally with live reload")
    serve_parser.add_argument("--port", type=int, default=8000, help="Port to serve on")
    serve_parser.add_argument("dir", nargs="?", default="reports", help="Directory to serve")
    
    # Convert command (placeholder)
    convert_parser = subparsers.add_parser("convert", help="Convert JUnit XML to HTML report")
    convert_parser.add_argument("input_file", help="Input JUnit XML file")
    convert_parser.add_argument("output_file", help="Output HTML file")

    args = parser.parse_args()

    if args.command == "run":
        # Separate the runner (unittest) from its args if needed, or just pass through
        # For now, we assume the user provides the full command after 'run --'
        # Example: beautiful-report run -- unittest discover tests
        cmd = args.args
        if not cmd:
            print("Error: No test command provided. Usage: beautiful-report run -- unittest ...")
            sys.exit(1)
        
        # In a real implementation, we would inject our BeautifulTestRunner here
        # For now, just running the command as a subprocess to verify scaffolding
        print(f"Running tests: {' '.join(cmd)}")
        try:
             # Basic passthrough for now - will hook in proper runner later
            subprocess.run(cmd, check=True)
        except subprocess.CalledProcessError as e:
            sys.exit(e.returncode)

    elif args.command == "serve":
        print(f"Serving {args.dir} on port {args.port}...")
        # Placeholder for http.server based implementation
    
    elif args.command == "convert":
        print(f"Converting {args.input_file} to {args.output_file}...")
        # Placeholder for conversion logic

    else:
        parser.print_help()

if __name__ == "__main__":
    main()
