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


def title(text):
    print()
    line()
    center(text)
    line()
    print()


def progress(label, steps=28, delay=0.035):
    print(f"  {label:<32}", end="")

    for i in range(steps + 1):
        filled = "█" * i
        empty = "░" * (steps - i)
        print(f"\r  {label:<32} [{filled}{empty}]", end="", flush=True)

        if not FAST:
            time.sleep(delay)

    print("  ✓")


def system_check(name, status="ONLINE"):
    print(f"  {name:<42} [{status}]")


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

    center("A STUDENT'S BIGGEST ENEMY")
    wait(1.5)

    print()
    center("ISN'T THE EXAM.")
    wait(1.5)

    print()
    center("IT'S FORGETTING.")
    wait(2)

    clear()

    print()
    print()
    center("WHAT IF YOU COULD")
    wait(0.8)
    center("TURN EVERY MISTAKE")
    wait(0.8)
    center("INTO PROGRESS?")
    wait(2)

    clear()


# ───────────────────────────────────────────────────────────────────────────
# Boot sequence
# ───────────────────────────────────────────────────────────────────────────

def boot():
    title("Q U I Z I C I A N")

    typewrite("  INITIALIZING INTELLIGENT QUIZ SYSTEM...", 0.03)
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
    center("ALL SYSTEMS OPERATIONAL")
    line("─")

    wait(2)


# ───────────────────────────────────────────────────────────────────────────
# The question engine
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
    typewrite("  QUIZ GENERATED", 0.04)

    print()
    line("─")

    print("  QUESTION 07 / 10")
    print()
    print("  Which structure is primarily responsible")
    print("  for regulating the heart's rhythm?")
    print()
    print("      A. SA node")
    print("      B. AV node")
    print("      C. Bundle of His")
    print("      D. Purkinje fibers")

    line("─")

    wait(2)

    print()
    typewrite("  USER ANSWER: B", 0.04)
    wait(1)

    print()
    center("✗  INCORRECT")
    wait(1.5)


# ───────────────────────────────────────────────────────────────────────────
# Mistakes become data
# ───────────────────────────────────────────────────────────────────────────

def mistakes():
    clear()

    title("BUT QUIZICIAN DOESN'T JUST SAY 'WRONG'.")

    typewrite("  It remembers.", 0.05)
    wait(1)

    print()
    progress("Recording mistake")
    progress("Updating mistake frequency")
    progress("Updating topic weakness")
    progress("Updating personal history")

    print()
    line("─")
    center("MISTAKE RECORDED")
    line("─")

    print()
    print("  Topic       : Cardiac Physiology")
    print("  Question    : #07")
    print("  Attempts    : 1")
    print("  Status      : NEEDS REVIEW")

    wait(2)

    clear()

    title("AND THEN...")

    typewrite("  Days later.", 0.06)
    wait(1)

    typewrite("  The same concept returns.", 0.05)
    wait(1)

    print()
    center("YOUR MISTAKE")
    center("HAS BECOME")
    center("YOUR NEXT CHALLENGE.")

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

    print("  PERSONALIZED SESSION")
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

    center("LEVEL UP!")

    line("─")

    print()
    center("LEVEL 27  →  LEVEL 28")

    wait(2)


# ───────────────────────────────────────────────────────────────────────────
# Achievements
# ───────────────────────────────────────────────────────────────────────────

def achievements():
    clear()

    title("THEN THE GRIND GETS A LITTLE ADDICTIVE.")

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
        center("🏆  ACHIEVEMENT UNLOCKED")
        print()
        center(name)
        center(description)
        wait(1.3)

        clear()

    title("AND THEN...")

    wait(1)

    center("QUIZICIAN")

    print()
    center("\"At this point, the questions fear YOU.\"")

    wait(2)


# ───────────────────────────────────────────────────────────────────────────
# Daily Quiz
# ───────────────────────────────────────────────────────────────────────────

def daily_quiz():
    clear()

    title("EVERY DAY.")

    center("14:00")
    wait(1)

    print()
    center("THE DAILY QUIZ ARRIVES.")

    wait(1.5)

    print()
    progress("Preparing today's questions")
    progress("Checking recent mistakes")
    progress("Building daily session")

    print()
    center("10 QUESTIONS")
    center("1 DAILY CHALLENGE")

    wait(2)

    clear()

    title("DAY 42")

    center("🔥 42 DAY STREAK")

    print()
    center("BREAK IT...")

    wait(1)

    center("OR DON'T.")

    wait(2)


# ───────────────────────────────────────────────────────────────────────────
# Final statistics
# ───────────────────────────────────────────────────────────────────────────

def final_stats():
    clear()

    title("THIS ISN'T JUST A QUIZ BOT.")

    typewrite("  It's a record of your progress.", 0.04)
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
# Finale
# ───────────────────────────────────────────────────────────────────────────

def finale():
    clear()

    print()
    print()
    center("YOU MADE MISTAKES.")
    wait(1)

    center("YOU LEARNED.")
    wait(1)

    center("YOU CAME BACK.")
    wait(1.5)

    clear()

    print()
    print()
    print()
    center("AND NOW...")

    wait(2)

    print()
    print()
    center("YOU ARE")
    wait(1)

    print()
    line("═")
    center("Q U I Z I C I A N")
    line("═")

    print()
    center("\"The questions fear YOU.\"")

    print()
    print()
    center("QUIZICIAN // 2026")

    wait(4)


# ───────────────────────────────────────────────────────────────────────────
# Main trailer
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
        print("\n  Quizician trailer terminated.")
        print("  The quiz will remember. 😈\n")
