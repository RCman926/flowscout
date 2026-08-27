"""Shared session / structure hard flags — Boss + structure manager must agree."""

HARD_SESSION = {
    "NO_CLEAR_DATA",
    "OUTSIDE_RTH_OR_NO_OPEN",
    "OPENING_BAR_FORMING",
    "AWAITING_BREAK_HOLD",
    "AWAITING_FIRST_BREAK",
    "TOO_LATE_0DTE",
    "STREAK_BLOCK_CALLS",
    "STREAK_BLOCK_PUTS",
}

STRUCTURE_HARD = HARD_SESSION | {
    "SPREAD_TOO_WIDE",
    "NO_CHAIN",
    "NO_QUALITY_CONTRACT",
    "TOO_FAR_OTM",
    "NO_MARK",
}
