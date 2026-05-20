import time

DOTS12_FRAMES = [
    '⢀⠀', '⡀⠀', '⠄⠀', '⢂⠀', '⡂⠀', '⠅⠀', '⢃⠀', '⡃⠀', '⠍⠀', '⢋⠀', '⡋⠀', '⠍⠁', 
    '⢋⠁', '⡋⠁', '⠍⠉', '⠋⠉', '⠋⠉', '⠉⠙', '⠉⠙', '⠉⠩', '⠈⢙', '⠈⡙', '⢈⠩', '⡀⢙', 
    '⠄⡙', '⢂⠩', '⡂⢘', '⠅⡘', '⢃⠨', '⡃⢐', '⠍⡐', '⢋⠠', '⡋⢀', '⠍⡁', '⢋⠁', '⡋⠁', 
    '⠍⠉', '⠋⠉', '⠋⠉', '⠉⠙', '⠉⠙', '⠉⠩', '⠈⢙', '⠈⡙', '⠈⠩', '⠀⢙', '⠀⡙', '⠀⠩', 
    '⠀⢘', '⠀⡘', '⠀⠨', '⠀⢐', '⠀⡐', '⠀⠠', '⠀⢀', '⠀⡀'
]

class BaseProgress:
    """Base class for VWIPL progress formatters."""
    def __init__(self, prefix=""):
        self.prefix = prefix
        self.start_time = time.time()
        self.ticks = 0

    def tick(self) -> tuple[str, bool]:
        """Returns the formatted string and a boolean flag (replace_last)."""
        self.ticks += 1
        elapsed = int(time.time() - self.start_time)
        return self.format(elapsed), True
        
    def format(self, elapsed: int) -> str:
        raise NotImplementedError

class IndeterminateBar(BaseProgress):
    """Bouncing block progress bar [======    ]"""
    def __init__(self, prefix="", width=20, block_width=6, char="=", empty=" "):
        super().__init__(prefix)
        self.width = width
        self.block_width = block_width
        self.char = char
        self.empty = empty
        self.position = 0
        self.direction = 1

    def format(self, elapsed: int) -> str:
        # Update position
        self.position += self.direction
        if self.position >= self.width - self.block_width:
            self.direction = -1
            self.position = self.width - self.block_width
        elif self.position <= 0:
            self.direction = 1
            self.position = 0

        bar = self.empty * self.width
        bar = bar[:self.position] + (self.char * self.block_width) + bar[self.position + self.block_width:]
        
        return f"{self.prefix} [{bar}] {elapsed}s elapsed"

class Spinner(BaseProgress):
    """Spinner using the dots12 animation."""
    def __init__(self, prefix="", frames=None):
        super().__init__(prefix)
        self.frames = frames or DOTS12_FRAMES
        
    def format(self, elapsed: int) -> str:
        frame = self.frames[self.ticks % len(self.frames)]
        return f"{self.prefix} {frame} {elapsed}s elapsed"

class DeterminateBar(BaseProgress):
    """Standard progress bar [██████░░░░] 60%"""
    def __init__(self, total, prefix="", width=20, fill="█", empty="░"):
        super().__init__(prefix)
        self.total = total
        self.width = width
        self.fill = fill
        self.empty = empty
        self.current = 0

    def update(self, current: int) -> tuple[str, bool]:
        self.current = current
        self.ticks += 1
        elapsed = int(time.time() - self.start_time)
        return self.format(elapsed), True

    def format(self, elapsed: int) -> str:
        pct = self.current / self.total if self.total > 0 else 0
        filled = int(self.width * pct)
        bar = (self.fill * filled) + (self.empty * (self.width - filled))
        pct_str = f"{int(pct * 100)}%"
        return f"{self.prefix} [{bar}] {pct_str} ({elapsed}s elapsed)"
