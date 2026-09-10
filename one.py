import os
import time


# Set True if you want to preview the trailer without waiting.
FAST = False

GREEN = "\033[92m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


def clear():
    os.system("cls" if os.name == "nt" else "clear")


def wait(seconds=0.8):
    if not FAST:
        time.sleep(seconds)


def text(msg="", delay=0.025):
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


def dim(msg):
    return f"{DIM}{msg}{RESET}"


def banner(msg):
    print()
    print(green("═" * 68))
    print(bold(msg.center(68)))
    print(green("═" * 68))
    print()


def progress(name, duration=0.7):
    print(f"  {name:<38}", end="")

    steps = 24

    for i in range(steps + 1):
        bar = "█" * i + "░" * (steps - i)

        print(
            f"\r  {name:<38} [{green(bar)}]",
            end="",
            flush=True,
        )

        if not FAST:
            time.sleep(duration / steps)

    print(f" {green('✓')}")


# ─────────────────────────────────────────────
# OPENING
# ─────────────────────────────────────────────

def opening():
    clear()

    print("\n\n\n")

    print(green("""
                    ╔══════════════════════════════╗
                     ║                                 ║
                     ║         YOUR NEXT QUIZ          ║
                     ║                                 ║
                    ╚══════════════════════════════╝
    """))

    wait(1.5)

    text("        Every answer leaves a trace.")

    wait(1.2)

    text("        Especially the wrong ones.")

    wait(2)


# ─────────────────────────────────────────────
# SYSTEMS
# ─────────────────────────────────────────────

def systems():
    clear()

    banner("INITIALIZING")

    wait(0.8)

    progress("Question system")
    wait(0.3)

    progress("Lecture system")
    wait(0.3)

    progress("Mistakes bank")
    wait(0.3)

    progress("Student analytics")
    wait(0.3)

    progress("XP & levels")
    wait(0.3)

    progress("Achievements")
    wait(0.3)

    progress("Daily Quiz")

    wait(1.2)

    print()
    print()
    print(green("                 ALL SYSTEMS READY"))

    wait(2)


# ─────────────────────────────────────────────
# MISTAKES
# ─────────────────────────────────────────────

def mistakes():
    clear()

    banner("A WRONG ANSWER ISN'T WASTED")

    wait(1)

    print("  Question 042")
    print()
    print("  Your answer: B")
    print()

    wait(0.8)

    print(f"  Result: {green('✗ INCORRECT')}")

    wait(1)

    print()
    print("  → Mistake recorded")

    wait(0.5)

    print("  → Topic performance updated")

    wait(0.5)

    print("  → Question added to review")

    wait(1.8)

    print()
    print(dim("  Later..."))

    wait(1.5)

    print()
    print("  The question comes back.")

    wait(1.2)

    print()

    print(f"  This time: {green('✓ CORRECT')}")

    wait(2)


# ─────────────────────────────────────────────
# PERSONALIZATION
# ─────────────────────────────────────────────

def personalization():
    clear()

    banner("YOUR QUIZ ISN'T RANDOM")

    wait(1)

    text("  Building session...")

    wait(1)

    print()

    print(f"    {green('40%')}   Weak topics")
    wait(0.7)

    print(f"    {green('30%')}   Previous mistakes")
    wait(0.7)

    print(f"    {green('20%')}   Unseen questions")
    wait(0.7)

    print(f"    {green('10%')}   Random review")

    wait(2)


# ─────────────────────────────────────────────
# PROGRESSION
# ─────────────────────────────────────────────

def progression():
    clear()

    banner("KEEP GOING")

    wait(1)

    stats = [
        ("XP", "18,420"),
        ("Level", "27"),
        ("Questions answered", "1,842"),
        ("Mistakes conquered", "147"),
        ("Lecture completions", "31"),
        ("Daily streak", "42"),
    ]

    for name, value in stats:
        print(f"  {name:<30} {bold(value)}")
        wait(0.45)

    wait(1.5)

    print()
    print(green("             ★ ACHIEVEMENT UNLOCKED ★"))

    wait(1)

    print()
    print(bold("                  MISTAKE HUNTER"))

    wait(0.6)

    print("                  10 mistakes conquered.")

    wait(2)


# ─────────────────────────────────────────────
# DAILY QUIZ
# ─────────────────────────────────────────────

def daily_quiz():
    clear()

    banner("EVERY DAY")

    wait(1.2)

    print()
    print(bold("                       14:00"))

    wait(1.2)

    print()
    print("                    Daily Quiz")

    wait(1)

    print()
    print("              Questions prepared.")

    wait(0.7)

    print("              Your progress remembered.")

    wait(0.7)

    print("              Your mistakes considered.")

    wait(2)


# ─────────────────────────────────────────────
# FINAL REVEAL
# ─────────────────────────────────────────────

def finale():
    clear()

    wait(1)

    print()
    print()
    print(green(r"""
 ██████╗ ██╗   ██╗██╗███████╗██╗ ██████╗██╗ █████╗ ███╗   ██╗
██╔═══██╗██║   ██║██║╚══███╔╝██║██╔════╝██║██╔══██╗████╗  ██║
██║   ██║██║   ██║██║  ███╔╝ ██║██║     ██║███████║██╔██╗ ██║
██║▄▄ ██║██║   ██║██║ ███╔╝  ██║██║     ██║██╔══██║██║╚██╗██║
╚██████╔╝╚██████╔╝██║███████╗██║╚██████╗██║██║  ██║██║ ╚████║
 ╚══▀▀═╝  ╚═════╝ ╚═╝╚══════╝╚═╝ ╚═════╝╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝
    """))

    wait(1.5)

    print(green(r"""
             ██████╗██╗ █████╗ ███╗   ██╗██╗ ██████╗
            ██╔════╝██║██╔══██╗████╗  ██║██║██╔════╝
            ██║     ██║███████║██╔██╗ ██║██║██║     
            ██║     ██║██╔══██║██║╚██╗██║██║██║     
            ╚██████╗██║██║  ██║██║ ╚████║██║╚██████╗
             ╚═════╝╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝╚═╝ ╚═════╝
    """))

    wait(1.5)

    print()
    print(green("                     Q U I Z I C I A N"))

    wait(1.5)

    print()
    text("              Built to make mistakes")
    text("              part of the learning.")

    wait(2)

    print()
    print(green("                         2026"))

    wait(3)


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

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
