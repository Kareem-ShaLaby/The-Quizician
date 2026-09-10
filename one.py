import os
import sys
import time
import random


# ╔══════════════════════════════════════════════════════════════════════════╗
# ║                         Q U I Z I C I A N                              ║
# ║                    THE QUIZ BOT TRAILER                                ║
# ╚══════════════════════════════════════════════════════════════════════════╝


# ───────────────────────────────────────────────────────────────────────────
# Configuration
# ───────────────────────────────────────────────────────────────────────────

FAST = False          # Set True to skip dramatic pauses
WIDTH = 72


# ───────────────────────────────────────────────────────────────────────────
# ANSI Colors
# ───────────────────────────────────────────────────────────────────────────

RESET = "\033[0m"
BOLD = "\033[1m"

GREEN = "\033[92m"
PURPLE = "\033[95m"
CYAN = "\033[96m"
WHITE = "\033[97m"
DIM = "\033[2m"
RED = "\033[91m"
YELLOW = "\033[93m"


# ───────────────────────────────────────────────────────────────────────────
# Basic Helpers
# ───────────────────────────────────────────────────────────────────────────

def clear():
    os.system("cls" if os.name == "nt" else "clear")


def wait(seconds=1):
    if not FAST:
        time.sleep(seconds)


def typewrite(text, speed=0.025):
    if FAST:
        print(text)
        return

    for char in text:
        print(char, end="", flush=True)
        time.sleep(speed)

    print()


def line(char="═"):
    print(char * WIDTH)


def center(text):
    print(text.center(WIDTH))


def center_color(text, color="", bold=False):
    style = BOLD if bold else ""
    print(f"{color}{style}{text.center(WIDTH)}{RESET}")


def title(text):
    print()
    line()
    center_color(text, GREEN, True)
    line()
    print()


def progress(label, steps=28, delay=0.035):
    print(f"  {label:<32}", end="")

    for i in range(steps + 1):
        filled = "█" * i
        empty = "░" * (steps - i)

        print(
            f"\r  {label:<32} [{filled}{empty}]",
            end="",
            flush=True
        )

        if not FAST:
            time.sleep(delay)

    print("  ✓")


def system_check(name, status="ONLINE"):
    print(
        f"  {GREEN}{name:<42}{RESET} "
        f"[{GREEN}{status}{RESET}]"
    )


def glitch_pause():
    wait(0.5)
    print()
    wait(0.5)


# ───────────────────────────────────────────────────────────────────────────
# Opening
# ───────────────────────────────────────────────────────────────────────────

def opening():
    clear()

    print()
    wait(1)

    center_color("A STUDENT'S BIGGEST ENEMY", GREEN, True)
    wait(1.5)

    print()
    center_color("ISN'T THE EXAM.", GREEN, True)
    wait(1.5)

    print()
    center_color("IT'S FORGETTING.", GREEN, True)
    wait(2)

    clear()

    print()
    print()

    center_color("WHAT IF YOU COULD", GREEN, True)
    wait(0.8)

    center_color("TURN EVERY MISTAKE", GREEN, True)
    wait(0.8)

    center_color("INTO PROGRESS?", GREEN, True)

    wait(2)

    clear()


# ───────────────────────────────────────────────────────────────────────────
# Boot Sequence
# ───────────────────────────────────────────────────────────────────────────

def boot():
    title("Q U I Z I C I A N")

    typewrite(
        "  INITIALIZING INTELLIGENT QUIZ SYSTEM...",
        0.03
    )

    wait(0.8)

    progress("Loading question engine")
    progress("Loading mistake bank")
    progress("Loading lecture index")
    progress("Loading analytics")
    progress("Loading achievement engine")
    progress("Loading XP & progression")
    progress("Loading personalization")
    progress("Loading Daily Quiz")
    progress("Loading student profiles")

    print()

    system_check("Question Engine")
    system_check("Mistakes Bank")
    system_check("Lecture System")
    system_check("Analytics Engine")
    system_check("Achievement System")
    system_check("XP / Level System")
    system_check("Daily Quiz")
    system_check("Personalization Engine")

    wait(1)

    print()
    line("─")

    center_color(
        "ALL SYSTEMS OPERATIONAL",
        GREEN,
        True
    )

    line("─")

    wait(2)


# ───────────────────────────────────────────────────────────────────────────
# The Question Engine
# ───────────────────────────────────────────────────────────────────────────

def question_engine():
    clear()

    title("THE QUESTION ENGINE")

    typewrite("  Millions of possible paths.")
    wait(0.7)

    typewrite("  One question at a time.")
    wait(0.7)

    print()

    progress("Selecting lecture", 20)
    progress("Selecting difficulty", 20)
    progress("Checking history", 20)
    progress("Building session", 20)

    print()

    typewrite(
        "  QUIZ GENERATED",
        0.04
    )

    print()

    line("─")

    print("  QUESTION 07 / 10")
    print()

    print(
        "  Which structure is primarily responsible"
    )

    print(
        "  for regulating the heart's rhythm?"
    )

    print()

    print("      A. SA node")
    print("      B. AV node")
    print("      C. Bundle of His")
    print("      D. Purkinje fibers")

    line("─")

    wait(2)

    print()

    typewrite(
        "  USER ANSWER: B",
        0.04
    )

    wait(1)

    print()

    center_color(
        "✗  INCORRECT",
        RED,
        True
    )

    wait(1.5)


# ───────────────────────────────────────────────────────────────────────────
# Mistakes Become Data
# ───────────────────────────────────────────────────────────────────────────

def mistakes():
    clear()

    title(
        "BUT QUIZICIAN DOESN'T JUST SAY 'WRONG'."
    )

    typewrite(
        "  It remembers.",
        0.05
    )

    wait(1)

    print()

    progress("Recording mistake")
    progress("Updating mistake frequency")
    progress("Updating topic weakness")
    progress("Updating personal history")

    print()

    line("─")

    center_color(
        "MISTAKE RECORDED",
        GREEN,
        True
    )

    line("─")

    print()

    print("  Topic       : Cardiac Physiology")
    print("  Question    : #07")
    print("  Attempts    : 1")
    print("  Status      : NEEDS REVIEW")

    wait(2)

    clear()

    title("AND THEN...")

    typewrite(
        "  Days later.",
        0.06
    )

    wait(1)

    typewrite(
        "  The same concept returns.",
        0.05
    )

    wait(1)

    print()

    center_color("YOUR MISTAKE", GREEN, True)
    center_color("HAS BECOME", GREEN, True)
    center_color("YOUR NEXT CHALLENGE.", GREEN, True)

    wait(2)


# ───────────────────────────────────────────────────────────────────────────
# Personalization
# ───────────────────────────────────────────────────────────────────────────

def personalization():
    clear()

    title("THE QUIZ ADAPTS.")

    typewrite("  Your history matters.")
    wait(0.7)

    typewrite("  Your mistakes matter.")
    wait(0.7)

    typewrite("  Your weak topics matter.")
    wait(1)

    print()

    progress("Analyzing performance")
    progress("Finding weak topics")
    progress("Finding unresolved mistakes")
    progress("Finding unseen questions")
    progress("Balancing session")

    print()

    line("─")

    center_color(
        "PERSONALIZED SESSION",
        GREEN,
        True
    )

    print()

    print("      40%  Weak Topics")
    print("      30%  Previous Mistakes")
    print("      20%  Unseen Questions")
    print("      10%  Random Review")

    line("─")

    wait(2)


# ───────────────────────────────────────────────────────────────────────────
# Progression
# ───────────────────────────────────────────────────────────────────────────

def progression():
    clear()

    title("EVERY ANSWER COUNTS.")

    print()

    print("  XP                         18,420")
    print("  LEVEL                          27")
    print("  QUESTIONS ANSWERED          1,842")
    print("  MISTAKES CONQUERED            147")
    print("  LECTURES COMPLETED             31")
    print("  DAILY STREAK                    42")

    wait(1.5)

    print()

    line("─")

    center_color(
        "LEVEL UP!",
        GREEN,
        True
    )

    line("─")

    print()

    center_color(
        "LEVEL 27  →  LEVEL 28",
        GREEN,
        True
    )

    wait(2)


# ───────────────────────────────────────────────────────────────────────────
# Achievements
# ───────────────────────────────────────────────────────────────────────────

def achievements():
    clear()

    title(
        "THEN THE GRIND GETS A LITTLE ADDICTIVE."
    )

    wait(1)

    achievements = [
        ("FIRST REDEMPTION", "Fix your first mistake."),
        ("HOT START", "Get 5 correct in a row."),
        ("MISTAKE HUNTER", "Conquer 10 mistakes."),
        ("WEEK WARRIOR", "Maintain a 7-day streak."),
        ("ERROR ERADICATOR", "Conquer 100 mistakes."),
        ("WALKING TEXTBOOK", "Complete 50 lectures."),
    ]

    for name, description in achievements:

        print()

        center_color(
            "🏆  ACHIEVEMENT UNLOCKED",
            GREEN,
            True
        )

        print()

        center_color(
            name,
            GREEN,
            True
        )

        center(description)

        wait(1.3)

        clear()

    title("AND THEN...")

    wait(1)

    center_color(
        "QUIZICIAN",
        PURPLE,
        True
    )

    print()

    center_color(
        '"At this point, the questions fear YOU."',
        GREEN,
        True
    )

    wait(2)


# ───────────────────────────────────────────────────────────────────────────
# Daily Quiz
# ───────────────────────────────────────────────────────────────────────────

def daily_quiz():
    clear()

    title("EVERY DAY.")

    center_color(
        "14:00",
        GREEN,
        True
    )

    wait(1)

    print()

    center_color(
        "THE DAILY QUIZ ARRIVES.",
        GREEN,
        True
    )

    wait(1.5)

    print()

    progress("Preparing today's questions")
    progress("Checking recent mistakes")
    progress("Building daily session")

    print()

    center_color(
        "10 QUESTIONS",
        GREEN,
        True
    )

    center_color(
        "1 DAILY CHALLENGE",
        GREEN,
        True
    )

    wait(2)

    clear()

    title("DAY 42")

    center_color(
        "🔥 42 DAY STREAK",
        GREEN,
        True
    )

    print()

    center_color(
        "BREAK IT...",
        GREEN,
        True
    )

    wait(1)

    center_color(
        "OR DON'T.",
        GREEN,
        True
    )

    wait(2)


# ───────────────────────────────────────────────────────────────────────────
# Final Statistics
# ───────────────────────────────────────────────────────────────────────────

def final_stats():
    clear()

    title("THIS ISN'T JUST A QUIZ BOT.")

    typewrite(
        "  It's a record of your progress.",
        0.04
    )

    wait(1)

    print()

    print("  ┌────────────────────────────────────────────┐")
    print("  │                                            │")
    print("  │       QUESTIONS ANSWERED     10,482       │")
    print("  │       MISTAKES CONQUERED        847       │")
    print("  │       LECTURES COMPLETED         93       │")
    print("  │       DAILY STREAK              127       │")
    print("  │       ACHIEVEMENTS               64       │")
    print("  │       XP                    284,921       │")
    print("  │                                            │")
    print("  └────────────────────────────────────────────┘")

    wait(2)


# ───────────────────────────────────────────────────────────────────────────
# FINAL SYSTEM / LOGO REVEAL
# ───────────────────────────────────────────────────────────────────────────

def finale():
    clear()

    wait(1)

    # Final story beat
    center_color(
        "YOU MADE MISTAKES.",
        GREEN,
        True
    )

    wait(1)

    center_color(
        "YOU LEARNED.",
        GREEN,
        True
    )

    wait(1)

    center_color(
        "YOU CAME BACK.",
        GREEN,
        True
    )

    wait(1.5)

    clear()

    print()
    print()

    center_color(
        "AND NOW...",
        GREEN,
        True
    )

    wait(2)

    clear()

    # System status
    typewrite(
        "  $ system_status",
        0.04
    )

    wait(0.5)

    print()

    system_check("Question Engine")
    system_check("Mistakes Bank")
    system_check("Lecture System")
    system_check("Analytics Engine")
    system_check("Achievement System")
    system_check("XP / Level System")
    system_check("Daily Quiz")
    system_check("Personalization Engine")

    wait(1)

    print()

    line("─")

    center_color(
        "ALL SYSTEMS OPERATIONAL",
        GREEN,
        True
    )

    line("─")

    wait(2)

    clear()

    # ─────────────────────────────────────────────────────────────
    # SYSTEM ONLINE
    # ─────────────────────────────────────────────────────────────

    print()
    print()

    center_color(
        "SYSTEM ONLINE",
        GREEN,
        True
    )

    wait(1)

    print()
    print()

    # ─────────────────────────────────────────────────────────────
    # QUIZICIAN ASCII LOGO
    # ─────────────────────────────────────────────────────────────

    ascii_logo = [
        " ██████╗ ██╗   ██╗██╗███████╗██╗ ██████╗██╗ █████╗ ███╗   ██╗",
        "██╔═══██╗██║   ██║██║╚══███╔╝██║██╔════╝██║██╔══██╗████╗  ██║",
        "██║   ██║██║   ██║██║  ███╔╝ ██║██║     ██║███████║██╔██╗ ██║",
        "██║▄▄ ██║██║   ██║██║ ███╔╝  ██║██║     ██║██╔══██║██║╚██╗██║",
        "╚██████╔╝╚██████╔╝██║███████╗██║╚██████╗██║██║  ██║██║ ╚████║",
        " ╚══▀▀═╝  ╚═════╝ ╚═╝╚══════╝╚═╝ ╚═════╝╚═╝╚═╝  ╚═╝╚═╝  ╚═══╝",
    ]

    for row in ascii_logo:
        center_color(
            row,
            PURPLE,
            True
        )

        wait(0.08)

    # ─────────────────────────────────────────────────────────────
    # FINAL TITLE
    # ─────────────────────────────────────────────────────────────
    print()
    print()

    # Final screen
    line("═")

    print()

    center_color(
        "LAUNCHING SOON",
        GREEN,
        True
    )

    print()

    line("═")

    print()
    print()

    center_color(
        ".",
        DIM
    )

    wait(5)


# ───────────────────────────────────────────────────────────────────────────
# Main Trailer
# ───────────────────────────────────────────────────────────────────────────

def main():
    opening()
    boot()
    question_engine()
    mistakes()
    personalization()
    progression()
    achievements()
    daily_quiz()
    final_stats()
    finale()


if __name__ == "__main__":

    try:
        main()

    except KeyboardInterrupt:

        clear()

        print(
            "\n  Quizician trailer terminated."
        )

        print(
            "  The Quizician is waiting. 😈\n"
    )
