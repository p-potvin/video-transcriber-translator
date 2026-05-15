from PySide6.QtWidgets import QWidget
from typing import List, Tuple

def audit_widget_tree(root_widget: QWidget) -> List[str]:
    """
    Recursively walks a PySide6 widget tree and returns a list of layout errors.
    Checks for:
    - Text clipping (widget height < fontMetrics bounding rect height)
    - Orphan bounds / Overflows (child extends outside parent)
    """
    errors = []
    
    def walk(widget: QWidget, level: int = 0):
        if not widget.isVisible():
            return
        
        # Check text clipping
        if hasattr(widget, "text") and callable(widget.text):
            text = widget.text()
            if text:
                fm = widget.fontMetrics()
                # Use boundingRect to get the actual text height, accounting for word wrap if enabled
                rect = fm.boundingRect(0, 0, widget.width(), 2000, 0, text)
                if rect.height() > widget.height():
                    errors.append(f"Text Clipped: '{text[:20]}...' in {widget.__class__.__name__}. "
                                  f"Text height: {rect.height()}, Widget height: {widget.height()}")

        # Check for children overflowing parent boundaries
        for child in widget.children():
            if isinstance(child, QWidget) and child.isVisible():
                if child.isWindow():
                    continue  # Tooltips, dialogs, etc.
                
                child_geom = child.geometry()
                parent_geom = widget.rect()  # Parent's internal geometry
                
                if not parent_geom.contains(child_geom):
                    # Minor overflows (1-2px) might be anti-aliasing or borders, but significant ones are bugs
                    # Allow slight bleed, depending on layout margins
                    # Ignore scroll area viewports where children intentionally overflow
                    from PySide6.QtWidgets import QAbstractScrollArea
                    if isinstance(widget, QAbstractScrollArea) or (widget.parent() and isinstance(widget.parent(), QAbstractScrollArea)):
                        pass
                    elif child_geom.right() > parent_geom.right() + 5 or child_geom.bottom() > parent_geom.bottom() + 5:
                        errors.append(f"Overflow: {child.__class__.__name__} bounds ({child_geom}) "
                                      f"exceed parent {widget.__class__.__name__} ({parent_geom})")
                walk(child, level + 1)
                
    walk(root_widget)
    return set(errors)  # remove duplicates

def find_intersections(widgets: List[QWidget]) -> List[Tuple[QWidget, QWidget]]:
    # In a real layout, siblings shouldn't intersect unless deliberately stacked (e.g. QStackedWidget)
    # This might be tricky to do generically without false positives. We'll stick to tree bounds.
    pass
