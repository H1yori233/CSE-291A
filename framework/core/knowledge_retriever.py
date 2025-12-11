import json
import os
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass


@dataclass
class RetrievedKnowledge:
    domain: str
    general_tips: List[str]
    specific_steps: List[str]
    rag_solutions: List[Dict[str, Any]]
    confidence: float


class KnowledgeRetriever:
    def __init__(
        self,
        domain_config_path: Optional[str] = None,
        rag_knowledge_path: Optional[str] = None
    ):
        self.domain_config: Dict[str, Any] = {}
        self.rag_system = None
        
        if domain_config_path and os.path.exists(domain_config_path):
            self._load_domain_config(domain_config_path)
        
        if rag_knowledge_path and os.path.exists(rag_knowledge_path):
            self._init_rag(rag_knowledge_path)
    
    def _load_domain_config(self, path: str):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                self.domain_config = json.load(f)
        except Exception:
            pass
    
    def _init_rag(self, rag_path: str):
        try:
            from .domain_rag import DomainRAG
            self.rag_system = DomainRAG()
            self.rag_system.load_knowledge_base(rag_path)
        except ImportError:
            pass
        except Exception:
            pass
    
    def detect_domain(self, task: str, a11y_elements: Optional[List[str]] = None) -> str:
        text = task.lower()
        if a11y_elements:
            text += " " + " ".join(a11y_elements).lower()

        domain_patterns = {
            "vlc": ["vlc", "media player", "video player", "cone", "playback", "subtitle", "loop", "rotate video", "extract audio"],
            "libreoffice_writer": ["writer", "document", "docx", "odt", "paragraph", "libreoffice writer", "bullet list", "page break", "header", "footer"],
            "libreoffice_calc": ["calc", "spreadsheet", "excel", "xlsx", "cell", "libreoffice calc", "pivot", "sum column", "freeze row", "chart", "data"],
            "libreoffice_impress": ["impress", "presentation", "slide", "pptx", "libreoffice impress", "slideshow"],
            "chrome": ["chrome", "chromium", "browser", "website", "search engine", "web page", "incognito", "browsing", "bookmark", "homepage"],
            "gimp": ["gimp", "image manipulation", "photo edit", "brightness", "saturation", "crop image", "resize image", "gaussian blur", "gif", "animated", "remove background"],
            "vscode": ["vscode", "vs code", "visual studio code", "code editor", "__pycache__", "pycache", "extension", "theme", "keybinding", "autosave", "merge conflict", "git conflict"],
            "thunderbird": ["thunderbird", "email client", "mail account", "email filter", "signature", "compose email", "email folder"],
            "files": ["nautilus", "file manager", "trash"],
            "system": ["terminal", "command line", "cli", "bash", "top", "cpu", "symlink", "symbolic link", "sha256", "checksum", "find files", "largest files"],
            "audacity": ["audacity", "audio edit", "trim audio", "record audio", "mp3", "wav", "sound"],
            "typora": ["typora", "markdown", "md file", "export md"],
            "pdfarranger": ["pdfarranger", "pdf arranger", "merge pdf", "combine pdf"],
            "gimagereader": ["gimagereader", "ocr", "extract text", "recognize text", "tesseract"],
            "gnome_calendar": ["gnome calendar", "calendar", "schedule", "reminder", "event", "meeting"],
        }
        
        scores = {}
        for domain, patterns in domain_patterns.items():
            score = sum(pattern in text for pattern in patterns)
            if score > 0:
                scores[domain] = score
        
        if scores:
            return max(scores, key=scores.get)
        return "general"
    
    def _match_specific_knowledge(
        self,
        task: str,
        domain_knowledge: Dict[str, Any]
    ) -> Tuple[Optional[Dict], float]:
        task_lower = task.lower()
        task_words = set(task_lower.split())
        specific = domain_knowledge.get("specific_knowledge", {})
        
        best_match = None
        best_score = 0.0
        
        for topic, knowledge in specific.items():
            keywords = knowledge.get("keywords", [])
            
            matched_keywords = sum(1 for kw in keywords if kw.lower() in task_lower)
            keyword_score = matched_keywords / len(keywords) if keywords else 0
            
            topic_words = set(topic.lower().split())
            topic_match = len(task_words & topic_words) / len(topic_words) if topic_words else 0
            
            score = 0.6 * keyword_score + 0.4 * topic_match
            
            if topic.lower() in task_lower or any(w in topic.lower() for w in task_words if len(w) > 3):
                score += 0.2
            
            if score > best_score:
                best_score = min(score, 1.0)
                best_match = knowledge
        
        return best_match, best_score
    
    def retrieve(
        self,
        task: str,
        domain: Optional[str] = None,
        max_rag_results: int = 2,
        include_general_tips: bool = True
    ) -> RetrievedKnowledge:
        if domain is None:
            domain = self.detect_domain(task)
        
        general_tips = []
        specific_steps = []
        rag_solutions = []
        confidence = 0.0
        
        if domain in self.domain_config:
            domain_knowledge = self.domain_config[domain]
            
            if include_general_tips:
                general_tips = domain_knowledge.get("general_tips", [])
            
            matched, match_confidence = self._match_specific_knowledge(task, domain_knowledge)
            if matched:
                specific_steps = matched.get("steps", [])
                confidence = max(confidence, match_confidence)
        
        if self.rag_system:
            try:
                rag_results = self.rag_system.query(
                    task=task,
                    domain=domain,
                    top_k=max_rag_results,
                    similarity_threshold=0.2
                )
                rag_solutions = rag_results
                
                if rag_results:
                    rag_confidence = max(r.get("similarity", 0) for r in rag_results)
                    confidence = max(confidence, rag_confidence)
            except Exception:
                pass
        
        return RetrievedKnowledge(
            domain=domain,
            general_tips=general_tips,
            specific_steps=specific_steps,
            rag_solutions=rag_solutions,
            confidence=confidence
        )
    
    def format_hints(
        self,
        knowledge: RetrievedKnowledge,
        max_length: int = 2000,
        include_rag_solutions: bool = True
    ) -> str:
        lines = []
        current_length = 0
        
        domain_name = self.domain_config.get(knowledge.domain, {}).get("name", knowledge.domain.upper())
        lines.append(f"\n## {domain_name} Tips:")
        current_length += len(lines[-1])
        
        if knowledge.general_tips:
            lines.append("\n### General Tips:")
            for tip in knowledge.general_tips[:3]:
                if current_length + len(tip) < max_length:
                    lines.append(f"- {tip}")
                    current_length += len(tip)
        
        if knowledge.specific_steps:
            lines.append("\n### Specific Steps for This Task:")
            for step in knowledge.specific_steps:
                if current_length + len(step) < max_length:
                    lines.append(step)
                    current_length += len(step)
        
        if include_rag_solutions and knowledge.rag_solutions:
            lines.append("\n### Similar Task Reference:")
            for i, solution in enumerate(knowledge.rag_solutions[:2], 1):
                task_preview = solution.get("task", "")[:100]
                sol_preview = solution.get("solution", "")[:500]
                
                if current_length + len(task_preview) + len(sol_preview) < max_length:
                    lines.append(f"\n**Example {i}**: \"{task_preview}...\"")
                    lines.append(f"{sol_preview}...")
                    current_length += len(task_preview) + len(sol_preview)
        
        return "\n".join(lines)
    
    def get_hints_for_task(
        self,
        task: str,
        domain: Optional[str] = None,
        max_length: int = 1500
    ) -> str:
        knowledge = self.retrieve(task, domain=domain)
        
        if knowledge.confidence < 0.1 and not knowledge.general_tips:
            return ""
        
        return self.format_hints(knowledge, max_length=max_length)


def create_knowledge_retriever(
    framework_root: Optional[str] = None
) -> KnowledgeRetriever:
    if framework_root is None:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        framework_root = os.path.dirname(current_dir)
    
    domain_config_path = os.path.join(framework_root, "config", "domain_knowledge.json")
    
    return KnowledgeRetriever(
        domain_config_path=domain_config_path,
        rag_knowledge_path=None
    )


if __name__ == "__main__":
    retriever = create_knowledge_retriever()
    
    test_tasks = [
        "disable the cone icon in VLC splash screen",
        "export document as PDF in LibreOffice Writer",
        "set Bing as default search engine",
        "reduce brightness of my photo"
    ]
    
    for task in test_tasks:
        print(f"\n{'='*60}")
        print(f"Task: {task}")
        
        hints = retriever.get_hints_for_task(task)
        print(f"\nHints:\n{hints[:800]}...")
