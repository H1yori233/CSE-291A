DOMAIN_HINTS = {
    "vlc": (
        "VLC Tips: Preferences via Tools->Preferences (or Ctrl+P). "
        "IMPORTANT: To access advanced settings like 'cone icon', you need to switch from Simple to All mode. "
        "Look for 'All (radio-button)' element at the bottom of the Preferences dialog and click it - "
        "DO NOT click 'Show settings (panel)', click the actual 'All' radio button! "
        "After switching to All mode, navigate to: Interface -> Main interfaces -> Qt. "
        "Find 'Display background cone or art' checkbox and uncheck it. Click 'Save' and restart VLC."
    ),
    
    "chrome": (
        "Chrome Tips: Settings via address bar: type 'chrome://settings' + Enter. "
        "Search engine settings in left sidebar. Click 'Set as default' after selecting."
    ),
    "firefox": (
        "Firefox Tips: Settings via menu button (≡) or about:preferences. "
        "Search settings under 'Search' section."
    ),
    
    "files": (
        "Files Tips: DOUBLE_CLICK folders/icons to open (not single click). "
        "Ctrl+L for location bar. Right-click for context menu."
    ),
    "nautilus": (
        "Nautilus Tips: DOUBLE_CLICK to open folders. "
        "Sidebar has quick locations. Ctrl+L to type path."
    ),
    
    "terminal": (
        "Terminal Tips: Open with Ctrl+Alt+T. Type commands and press Enter. "
        "Use 'cd' to navigate, 'ls' to list files."
    ),
    
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
    
    "gimp": (
        "GIMP Tips: Tools in left panel. Layers panel on right. "
        "File->Export As to save in different formats."
    ),
    
    "gnome_settings": (
        "Settings Tips: Categories in left sidebar. "
        "Search bar at top to find settings quickly."
    ),
    
    "desktop": (
        "Desktop Tips: DOUBLE_CLICK icons to open (not single click). "
        "Right-click for context menu. Files app in dock for file management."
    ),
    
    "default": (
        "Tips: DOUBLE_CLICK icons to open. Ctrl+Alt+T for terminal. "
        "If stuck, try different approach."
    ),
}

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
    for elem in a11y_elements:
        name = (elem.name or "").lower()
        
        for domain, keywords in DOMAIN_KEYWORDS.items():
            for keyword in keywords:
                if keyword in name:
                    return domain
    
    instruction_lower = instruction.lower()
    for domain, keywords in DOMAIN_KEYWORDS.items():
        for keyword in keywords:
            if keyword in instruction_lower:
                return domain

    return "default"


def get_domain_hint(domain: str, instruction: str = "") -> str:
    if instruction:
        try:
            from framework.core.knowledge_retriever import create_knowledge_retriever
            retriever = create_knowledge_retriever()
            task_hints = retriever.get_hints_for_task(instruction, domain=domain, max_length=1000)
            
            if task_hints and len(task_hints) > 50:
                return task_hints
        except ImportError:
            pass
        except Exception:
            pass
    
    return DOMAIN_HINTS.get(domain, DOMAIN_HINTS["default"])
