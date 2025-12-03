# ══════════════════════════════════════════════════════════════════════════════
#  _________._____________.___ ____ ___  _________      .__         .__            
# /   _____/|   \______   \   |    |   \/   _____/____  |  | ______ |  |__ _____   
# \_____  \ |   ||       _/   |    |   /\_____  \__  \ |  | \____ \|  |  \__  \  
# /        \|   ||    |   \   |    |  / /        \/ __ \|  |_|  |_> >   Y  \/ __ \_
# /_______  /|___||____|_  /___|______/ /_______  (____  /____/   __/|___|  (____  /
#         \/             \/                     \/     \/     |__|        \/     \/ 
#
# Gold Standard - Precious Metals Intelligence System
# Copyright (c) 2025 SIRIUS Alpha
# All rights reserved.
# ══════════════════════════════════════════════════════════════════════════════
"""
Gold Standard CLI - Command-line interface for the autonomous analysis system.
"""

import os
import sys
import argparse
import signal
import time
from datetime import date, datetime
from pathlib import Path

# Add package root to path for imports
PACKAGE_ROOT = Path(__file__).parent
PROJECT_ROOT = PACKAGE_ROOT.parent.parent.parent  # src/gost -> gold_standard

# Banner
BANNER = r"""
   _________ _________ _________ _________ ____ ____ ____ ____ 
  ||       |||       |||       |||       |||G |||O |||L |||D ||
  ||_______|||_______|||_______|||_______|||__|||__|||__|||__||
  |/_______\|/_______\|/_______\|/_______\|/__\|/__\|/__\|/__\|
   _________ ____ ____ ____ ____ ____ ____ ____ ____           
  ||       |||S |||T |||A |||N |||D |||A |||R |||D ||          
  ||_______|||__|||__|||__|||__|||__|||__|||__|||__||          
  |/_______\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|/__\|          
 
            PRECIOUS METALS INTELLIGENCE COMPLEX
"""

# Global flag for graceful shutdown
_shutdown_requested = False


def _signal_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    global _shutdown_requested
    print("\n\n  [SHUTDOWN] Signal received, stopping gracefully...")
    _shutdown_requested = True


def print_banner():
    """Print the Gold Standard banner."""
    print(BANNER)


def get_project_root():
    """Get the project root directory, handling both dev and installed modes."""
    # Check if running from installed package
    if 'site-packages' in str(PACKAGE_ROOT):
        # Installed via pip - use current working directory
        return Path.cwd()
    else:
        # Development mode - use project root
        return PROJECT_ROOT


def ensure_project_setup():
    """Ensure project directories and files exist."""
    root = get_project_root()
    
    # Required directories
    (root / "output").mkdir(exist_ok=True)
    (root / "output" / "reports").mkdir(exist_ok=True)
    (root / "output" / "charts").mkdir(exist_ok=True)
    (root / "data").mkdir(exist_ok=True)
    
    # Check for .env file
    env_file = root / ".env"
    if not env_file.exists():
        env_template = root / ".env.template"
        if env_template.exists():
            print("[SETUP] No .env file found. Please copy .env.template to .env and add your API keys.")
        else:
            print("[SETUP] No .env file found. Please create one with GEMINI_API_KEY=your_key")
    
    return root


def run_analysis(mode: str = "all", no_ai: bool = False, force: bool = False):
    """
    Run Gold Standard analysis.
    
    Args:
        mode: Analysis mode ('all', 'daily', 'premarket', 'weekly', 'monthly', 'yearly')
        no_ai: Disable AI-generated content
        force: Force regenerate even if reports exist
    """
    from gost.core import GoldStandard
    
    gs = GoldStandard(no_ai=no_ai)
    
    if mode == "all":
        return gs.run_all(force=force)
    elif mode == "daily":
        return gs.run_daily()
    elif mode == "premarket":
        return gs.run_premarket()
    elif mode == "weekly":
        return gs.run_weekly()
    elif mode == "monthly":
        return gs.run_monthly()
    elif mode == "yearly":
        return gs.run_yearly()
    else:
        print(f"Unknown mode: {mode}")
        return False


def run_daemon(no_ai: bool = False, interval_minutes: int = 1):
    """
    Run Gold Standard as an autonomous daemon.
    
    Args:
        no_ai: Disable AI-generated content
        interval_minutes: Minutes between analysis runs
    """
    global _shutdown_requested
    
    import schedule
    from gost.core import GoldStandard
    
    # Register signal handlers
    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)
    
    print("\n" + "=" * 60)
    print("       GOLD STANDARD - AUTONOMOUS MODE")
    print("=" * 60)
    print(f"  Interval: Every {interval_minutes} minute(s)")
    print(f"  AI Mode:  {'Disabled' if no_ai else 'Enabled'}")
    print("  Press Ctrl+C to shutdown gracefully")
    print("=" * 60 + "\n")
    
    gs = GoldStandard(no_ai=no_ai)
    
    # Run immediately on startup
    print("[DAEMON] Running initial analysis cycle...\n")
    gs.run_all()
    
    # Schedule recurring runs
    def daemon_cycle():
        print(f"\n[DAEMON] Starting cycle at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        gs.run_all()
    
    schedule.every(interval_minutes).minutes.do(daemon_cycle)
    
    print(f"\n[DAEMON] Next run scheduled in {interval_minutes} minute(s)")
    print("[DAEMON] System is now running autonomously...\n")
    
    # Main loop
    while not _shutdown_requested:
        try:
            schedule.run_pending()
            time.sleep(1)
        except Exception as e:
            print(f"[DAEMON] Error in main loop: {e}")
            time.sleep(5)
    
    print("\n[DAEMON] Shutdown complete. Goodbye!\n")


def show_status():
    """Show current system status."""
    from gost.core import GoldStandard
    
    gs = GoldStandard()
    gs.print_status()


def interactive_mode(no_ai: bool = False):
    """Run interactive menu mode."""
    from gost.core import GoldStandard
    
    MENU = """
┌─────────────────────────────────────────────────────────────┐
│                    GOLD STANDARD                            │
│              Precious Metals Intelligence                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   [1]  RUN ALL ANALYSIS                                     │
│   [2]  Quick Daily Update                                   │
│   [3]  Pre-Market Plan                                      │
│   [4]  Force Regenerate All                                 │
│   [5]  View Status                                          │
│   [0]  Exit                                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
"""
    
    gs = GoldStandard(no_ai=no_ai)
    
    while True:
        os.system('cls' if os.name == 'nt' else 'clear')
        print_banner()
        gs.print_status()
        print(MENU)
        
        if no_ai:
            print("  [AI Disabled - running in --no-ai mode]\n")
        
        choice = input("  Enter choice [0-5]: ").strip()
        
        if choice == "1":
            gs.run_all()
            input("\n  Press Enter to continue...")
        elif choice == "2":
            gs.run_daily()
            input("\n  Press Enter to continue...")
        elif choice == "3":
            gs.run_premarket()
            input("\n  Press Enter to continue...")
        elif choice == "4":
            confirm = input("\n  Regenerate ALL reports? [y/N]: ").strip().lower()
            if confirm == 'y':
                gs.run_all(force=True)
            input("\n  Press Enter to continue...")
        elif choice == "5":
            gs.print_status()
            input("\n  Press Enter to continue...")
        elif choice == "0":
            print("\n  Goodbye!\n")
            break


def main():
    """Main entry point for the gost CLI."""
    parser = argparse.ArgumentParser(
        prog="gost",
        description="Gold Standard - Autonomous precious metals intelligence system",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  gost                     # Autonomous daemon mode (1-minute cycles)
  gost --once              # Single run and exit
  gost --run               # Run all analysis once
  gost --interval-min 5    # Daemon with 5-minute interval
  gost --interactive       # Interactive menu
  gost --status            # Show current status
  gost --no-ai             # Daemon without AI
  gost --init              # Initialize project in current directory
        """
    )
    
    parser.add_argument('--version', '-V', action='version', version='%(prog)s 3.1.0')
    parser.add_argument('--run', '-r', action='store_true',
                       help='Run complete analysis once')
    parser.add_argument('--daily', '-d', action='store_true',
                       help='Quick daily journal update only')
    parser.add_argument('--premarket', '-p', action='store_true',
                       help='Generate pre-market plan')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Force regenerate reports even if they exist')
    parser.add_argument('--status', '-s', action='store_true',
                       help='Show current system status')
    parser.add_argument('--no-ai', action='store_true',
                       help='Disable AI-generated content (Gemini)')
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive menu mode')
    parser.add_argument('--once', action='store_true',
                       help='Run once and exit (no daemon)')
    parser.add_argument('--interval-min', type=int, default=1,
                       help='Minutes between daemon runs (default: 1)')
    parser.add_argument('--init', action='store_true',
                       help='Initialize Gold Standard in current directory')
    
    args = parser.parse_args()
    
    # Initialize project structure
    if args.init:
        from gost.init import initialize_project
        initialize_project()
        return
    
    # Ensure project is set up
    project_root = ensure_project_setup()
    os.chdir(project_root)
    
    # Load environment
    from dotenv import load_dotenv
    load_dotenv()
    
    # Handle commands
    if args.status:
        print_banner()
        show_status()
        return
    
    if args.run or args.once:
        print_banner()
        run_analysis("all", no_ai=args.no_ai, force=args.force)
        return
    
    if args.daily:
        print_banner()
        run_analysis("daily", no_ai=args.no_ai)
        return
    
    if args.premarket:
        print_banner()
        run_analysis("premarket", no_ai=args.no_ai)
        return
    
    if args.interactive:
        interactive_mode(no_ai=args.no_ai)
        return
    
    # Default: Autonomous daemon mode
    print_banner()
    run_daemon(no_ai=args.no_ai, interval_minutes=args.interval_min)


if __name__ == '__main__':
    main()
