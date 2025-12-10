DOMAIN_HINTS = {
    # Media players
    "vlc": (
        "VLC Tips: Preferences via Tools->Preferences (or Ctrl+P). "
        "Interface tab has 'Show background cone or icon' checkbox. Save with 'Save'."
    ),
    
    # Browsers
    "chrome": (
        "Chrome Tips: Settings via address bar: type 'chrome://settings' + Enter. "
        "Search engine settings in left sidebar. Click 'Set as default' after selecting."
    ),
    "firefox": (
        "Firefox Tips: Settings via menu button (≡) or about:preferences. "
        "Search settings under 'Search' section."
    ),
    
    # File management
    "files": (
        "Files Tips: DOUBLE_CLICK folders/icons to open (not single click). "
        "Ctrl+L for location bar. Right-click for context menu."
    ),
    "nautilus": (
        "Nautilus Tips: DOUBLE_CLICK to open folders. "
        "Sidebar has quick locations. Ctrl+L to type path."
    ),
    
    # Terminal
    "terminal": (
        "Terminal Tips: Open with Ctrl+Alt+T. Type commands and press Enter. "
        "Use 'cd' to navigate, 'ls' to list files."
    ),
    
    # Office applications
    "libreoffice_writer": (
        "Writer Tips: Select text first, then format. "
        "Format->Paragraph->Indents & Spacing for line spacing. "
        "Double/1.5 spacing in 'Line Spacing' dropdown."
    ),
    "libreoffice_calc": (
        "Calc Tips: Click cell to select. Format->Cells for formatting. "
        "Use formula bar for formulas starting with '='."
    ),
    "libreoffice_impress": (
        "Impress Tips: Slide->Slide Properties for slide settings. "
        "Insert->Image for adding pictures."
    ),
    
    # Graphics
    "gimp": (
        "GIMP Tips: Tools in left panel. Layers panel on right. "
        "File->Export As to save in different formats."
    ),
    
    # System settings
    "gnome_settings": (
        "Settings Tips: Categories in left sidebar. "
        "Search bar at top to find settings quickly."
    ),
    
    # Desktop general
    "desktop": (
        "Desktop Tips: DOUBLE_CLICK icons to open (not single click). "
        "Right-click for context menu. Files app in dock for file management."
    ),
    
    # Default (minimal hint)
    "default": (
        "Tips: DOUBLE_CLICK icons to open. Ctrl+Alt+T for terminal. "
        "If stuck, try different approach."
    ),
}

# Keywords to match for domain detection
DOMAIN_KEYWORDS = {
    "vlc": ["vlc", "media player", "vlc media"],
    "chrome": ["chrome", "chromium", "google chrome"],
    "firefox": ["firefox", "mozilla"],
    "files": ["files", "nautilus", "file manager"],
    "nautilus": ["nautilus"],
    "terminal": ["terminal", "gnome-terminal", "console", "bash", "shell"],
    "libreoffice_writer": ["writer", "libreoffice writer", "word processor"],
    "libreoffice_calc": ["calc", "libreoffice calc", "spreadsheet"],
    "libreoffice_impress": ["impress", "libreoffice impress", "presentation"],
    "gimp": ["gimp", "gnu image", "image manipulation"],
    "gnome_settings": ["settings", "gnome-control-center"],
    "desktop": ["desktop"],
}


def detect_domain(a11y_elements: list, instruction: str) -> str:
    # Check a11y element names for app signatures
    for elem in a11y_elements:
        name = (elem.name or "").lower()
        
        # Check each domain's keywords
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name:
                    return domain
    
    # Check instruction keywords
    instruction_lower = instruction.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in instruction_lower:
                return domain

    return "default"


def get_domain_hint(domain: str) -> str:
    return DOMAIN_HINTS.get(domain, DOMAIN_HINTS["default"])
