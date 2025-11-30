#!/usr/bin/env python3
"""
Gold Standard CLI
Unified entry point for running daily journals, weekly rundowns, monthly and yearly reports.
"""
import os
import sys
import argparse

# Banner
BANNER = r"""
                                          ___           ___                                                              
                                         /\__\         /\  \                       _____                                 
                                        /:/ _/_       /::\  \                     /::\  \                                
                                       /:/ /\  \     /:/\:\  \                   /:/\:\  \                               
                                      /:/ /::\  \   /:/  \:\  \   ___     ___   /:/  \:\__\                              
                                     /:/__\/\:\__\ /:/__/ \:\__\ /\  \   /\__\ /:/__/ \:|__|                             
                                     \:\  \ /:/  / \:\  \ /:/  / \:\  \ /:/  / \:\  \ /:/  /                             
                                      \:\  /:/  /   \:\  /:/  /   \:\  /:/  /   \:\  /:/  /                              
                                       \:\/:/  /     \:\/:/  /     \:\/:/  /     \:\/:/  /                               
                                        \::/  /       \::/  /       \::/  /       \::/  /                                
                                         \/__/         \/__/         \/__/         \/__/                                 
               ___                         ___           ___                         ___           ___                   
              /\__\                       /\  \         /\  \         _____         /\  \         /\  \         _____    
             /:/ _/_         ___         /::\  \        \:\  \       /::\  \       /::\  \       /::\  \       /::\  \   
            /:/ /\  \       /\__\       /:/\:\  \        \:\  \     /:/\:\  \     /:/\:\  \     /:/\:\__\     /:/\:\  \  
           /:/ /::\  \     /:/  /      /:/ /::\  \   _____\:\  \   /:/  \:\__\   /:/ /::\  \   /:/ /:/  /    /:/  \:\__\ 
          /:/_/:/\:\__\   /:/__/      /:/_/:/\:\__\ /::::::::\__\ /:/__/ \:|__| /:/_/:/\:\__\ /:/_/:/__/___ /:/__/ \:|__|
          \:\/:/ /:/  /  /::\  \      \:\/:/  \/__/ \:\~~\~~\/__/ \:\  \ /:/  / \:\/:/  \/__/ \:\/:::::/  / \:\  \ /:/  /
           \::/ /:/  /  /:/\:\  \      \::/__/       \:\  \        \:\  /:/  /   \::/__/       \::/~~/~~~~   \:\  /:/  / 
            \/_/:/  /   \/__\:\  \      \:\  \        \:\  \        \:\/:/  /     \:\  \        \:\~~\        \:\/:/  /  
              /:/  /         \:\__\      \:\__\        \:\__\        \::/  /       \:\__\        \:\__\        \::/  /   
              \/__/           \/__/       \/__/         \/__/         \/__/         \/__/         \/__/         \/__/    

                                                  
                                                  PRECIOUS METALS INTELLIGENCE COMPLEX
"""

MENU = """
Select a mode:

  [1] Daily Journal   -  Full daily analysis with AI-generated thesis
  [2] Weekly Rundown  -  Short-horizon tactical overview for the weekend
  [3] Monthly Report  -  Monthly aggregated performance tables + AI outlook
  [4] Yearly Report   -  Year-over-year analysis + AI forecast

  [0] Exit

"""

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def print_banner():
    print(BANNER)


def run_daily(no_ai: bool = False):
    """Run the daily journal via main.py."""
    print("\n>> Running Daily Journal...\n")
    cmd_parts = [sys.executable, "main.py", "--once"]
    if no_ai:
        cmd_parts.append("--no-ai")
    os.system(" ".join(cmd_parts))


def run_weekly(no_ai: bool = False):
    """Run the weekly rundown via split_reports.py."""
    print("\n>> Running Weekly Rundown...\n")
    cmd_parts = [sys.executable, "scripts/split_reports.py", "--mode", "weekly", "--once"]
    if no_ai:
        cmd_parts.append("--no-ai")
    os.system(" ".join(cmd_parts))


def run_monthly(no_ai: bool = False):
    """Run the monthly report via split_reports.py."""
    print("\n>> Running Monthly Report...\n")
    cmd_parts = [sys.executable, "scripts/split_reports.py", "--mode", "monthly", "--once"]
    if no_ai:
        cmd_parts.append("--no-ai")
    os.system(" ".join(cmd_parts))


def run_yearly(no_ai: bool = False):
    """Run the yearly report via split_reports.py."""
    print("\n>> Running Yearly Report...\n")
    cmd_parts = [sys.executable, "scripts/split_reports.py", "--mode", "yearly", "--once"]
    if no_ai:
        cmd_parts.append("--no-ai")
    os.system(" ".join(cmd_parts))


def interactive_mode(no_ai: bool = False):
    """Interactive menu loop."""
    while True:
        clear_screen()
        print_banner()
        print(MENU)
        if no_ai:
            print("  [AI Disabled - running in --no-ai mode]\n")
        choice = input("  Enter choice [0-4]: ").strip()

        if choice == "1":
            run_daily(no_ai=no_ai)
            input("\n  Press Enter to continue...")
        elif choice == "2":
            run_weekly(no_ai=no_ai)
            input("\n  Press Enter to continue...")
        elif choice == "3":
            run_monthly(no_ai=no_ai)
            input("\n  Press Enter to continue...")
        elif choice == "4":
            run_yearly(no_ai=no_ai)
            input("\n  Press Enter to continue...")
        elif choice == "0":
            print("\n  Goodbye!\n")
            break
        else:
            print("\n  Invalid choice. Please enter a number between 0 and 4.")
            input("  Press Enter to continue...")


def main():
    parser = argparse.ArgumentParser(
        description="Gold Standard CLI - Unified entry point for daily, weekly, monthly, and yearly reports.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py                       # Interactive menu
  python run.py --mode daily          # Run daily journal
  python run.py --mode weekly         # Run weekly rundown
  python run.py --mode monthly        # Run monthly report
  python run.py --mode yearly         # Run yearly report
  python run.py --mode daily --no-ai  # Run daily without AI
        """
    )
    parser.add_argument(
        '--mode', '-m',
        choices=['daily', 'weekly', 'monthly', 'yearly'],
        help='Run mode: daily, weekly, monthly, or yearly. If omitted, interactive menu is shown.'
    )
    parser.add_argument(
        '--no-ai',
        action='store_true',
        help='Disable AI-generated content (Gemini).'
    )
    parser.add_argument(
        '--interactive', '-i',
        action='store_true',
        help='Force interactive mode even if --mode is provided.'
    )

    args = parser.parse_args()

    # Change to project root (where run.py is located)
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    # Non-interactive direct execution
    if args.mode and not args.interactive:
        print_banner()
        if args.mode == 'daily':
            run_daily(no_ai=args.no_ai)
        elif args.mode == 'weekly':
            run_weekly(no_ai=args.no_ai)
        elif args.mode == 'monthly':
            run_monthly(no_ai=args.no_ai)
        elif args.mode == 'yearly':
            run_yearly(no_ai=args.no_ai)
        return

    # Interactive mode
    interactive_mode(no_ai=args.no_ai)


if __name__ == '__main__':
    main()
