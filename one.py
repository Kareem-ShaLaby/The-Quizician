import os
import sys
import time


# ─────────────────────────────────────────────────────────────────────────────
# Trailer settings
# ─────────────────────────────────────────────────────────────────────────────

FAST = False

GREEN = "\033[92m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def wait(seconds=0.4):
    if not FAST:
        time.sleep(seconds)


def text(msg="", delay=0.018):
    if FAST:
        print(msg)
        return

    for char in msg:
        print(char, end="", flush=True)
        time.sleep(delay)
    print()


def green(msg):
    return f"{GREEN}{msg}{RESET}"


def bold(msg):
    return f"{BOLD}{msg}{RESET}"


def banner(msg):
    print()
    print(green("═" * 62))
    print(bold(msg.center(62)))
    print(green("═" * 62))
    print()


def progress(name):
    print(f"  {name:<34}", end="")

    for i in range(21):
        bar = "█" * i + "░" * (20 - i)
        print(f"\r  {name:<34} [{green(bar)}]", end="", flush=True)
        if not FAST:
            time.sleep(0.015)

    print(f"  {green('✓')}")


# ─────────────────────────────────────────────────────────────────────────────
# Opening
# ─────────────────────────────────────────────────────────────────────────────

def opening():
    clear()

    print()
    print()
    print(green(r"""
             ╔══════════════════════════════════╗
             ║                                  ║
             ║          YOUR NEXT QUIZ          ║
             ║                                  ║
             ╚══════════════════════════════════╝
    """))

    wait(0.7)

    text("  Every answer leaves a trace.")
    wait(0.5)

    text("  Especially the wrong ones.")

    wait(1)


# ─────────────────────────────────────────────────────────────────────────────
# Core systems
# ─────────────────────────────────────────────────────────────────────────────

def systems():
    clear()

    banner("INITIALIZING")

    progress("Question system")
    progress("Lecture system")
    progress("Mistakes bank")
    progress("Student analytics")
    progress("XP & levels")
    progress("Achievements")
    progress("Daily Quiz")

    wait(0.7)

    print()
    print(f"  {green('ALL SYSTEMS READY')}")
    wait(1)


# ─────────────────────────────────────────────────────────────────────────────
# Mistakes
# ─────────────────────────────────────────────────────────────────────────────

def mistakes():
    clear()

    banner("A WRONG ANSWER ISN'T WASTED")

    print("  Answer: B")
    print(f"  Result: {green('✗ INCORRECT')}")
    wait(0.5)

    print()
    print("  → Mistake recorded")
    print("  → Topic performance updated")
    print("  → Question added to review")

    wait(1)

    print()
    print(green("  Later..."))
    wait(0.5)

    print()
    print("  The question comes back.")
    print(f"  This time: {green('✓ CORRECT')}")

    wait(1)


# ─────────────────────────────────────────────────────────────────────────────
# Personalization
# ─────────────────────────────────────────────────────────────────────────────

def personalization():
    clear()

    banner("YOUR QUIZ ISN'T RANDOM")

    print("  Building session...")
    wait(0.3)

    print()
    print(f"    {green('40%')}  Weak topics")
    print(f"    {green('30%')}  Previous mistakes")
    print(f"    {green('20%')}  Unseen questions")
    print(f"    {green('10%')}  Random review")

    wait(1)


# ─────────────────────────────────────────────────────────────────────────────
# Progression
# ─────────────────────────────────────────────────────────────────────────────

def progression():
    clear()

    banner("KEEP GOING")

    print("  XP                         18,420")
    print("  Level                          27")
    print("  Questions answered          1,842")
    print("  Mistakes conquered            147")
    print("  Lecture completions             31")
    print("  Daily streak                    42")

    wait(1)

    print()
    print(green("  ★ ACHIEVEMENT UNLOCKED"))
    print()
    print(bold("       MISTAKE HUNTER"))
    print("       10 mistakes conquered.")

    wait(1)


# ─────────────────────────────────────────────────────────────────────────────
# Daily Quiz
# ─────────────────────────────────────────────────────────────────────────────

def daily_quiz():
    clear()

    banner("EVERY DAY")

    print()
    print("             14:00")
    print()
    print("       Daily Quiz")
    print()
    print("       Questions prepared.")
    print("       Your progress remembered.")
    print("       Your mistakes considered.")

    wait(1.2)


# ─────────────────────────────────────────────────────────────────────────────
# Finale
# ─────────────────────────────────────────────────────────────────────────────

def finale():
    clear()

    print()
    print()
    print(green(r"""
                 ██████╗ ██╗   ██╗██╗███████╗
                ██╔═══██╗██║   ██║██║██╔════╝
                ██║   ██║██║   ██║██║███████╗
                ██║▄▄ ██║██║   ██║██║╚════██║
                ╚██████╔╝╚██████╔╝██║███████║
                 ╚══▀▀═╝  ╚═════╝ ╚═╝╚══════╝
    """))

    wait(0.5)

    print()
    print(green("                  Q U I Z I C I A N"))
    print()

    text("                  Built to make mistakes")
    text("                  part of the learning.")

    wait(1.5)

    print()
    print(green("                       2026"))
    print()


# ─────────────────────────────────────────────────────────────────────────────
# Run
# ─────────────────────────────────────────────────────────────────────────────

def main():
    opening()
    systems()
    mistakes()
    personalization()
    progression()
    daily_quiz()
    finale()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        clear()
        print("\n  Trailer stopped.\n")
