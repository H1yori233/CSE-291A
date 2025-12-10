import json
import os
import re
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeItem:
    task_description: str
    solution: str
    domain: str
    keywords: List[str] = None
    
    def __post_init__(self):
        if self.keywords is None:
            self.keywords = self._extract_keywords(self.task_description)
    
    @staticmethod
    def _extract_keywords(text: str) -> List[str]:
        # Remove common stop words and extract unique words
        stop_words = {'the', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of', 'and', 'or', 
                      'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has',
                      'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may',
                      'can', 'i', 'you', 'we', 'they', 'it', 'this', 'that', 'my', 'your'}
        
        # Extract words, lowercase
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        # Filter stop words and short words
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return list(set(keywords))


class DomainRAG:
    DOMAIN_KEYWORDS = {
        "vlc": ["vlc", "video", "media player", "playback", "cone", "audio", "subtitle"],
        "libreoffice_writer": ["writer", "document", "docx", "odt", "paragraph", "font", "text"],
        "libreoffice_calc": ["calc", "spreadsheet", "excel", "xlsx", "cell", "formula", "column", "row"],
        "libreoffice_impress": ["impress", "presentation", "slide", "pptx", "powerpoint"],
        "chrome": ["chrome", "browser", "chromium", "website", "web", "search engine", "extension"],
        "gimp": ["gimp", "image", "photo", "png", "jpg", "brightness", "color", "layer"],
        "vscode": ["vscode", "vs code", "visual studio code", "code", "editor", "python", "file"],
        "thunderbird": ["thunderbird", "email", "mail", "outlook", "account"],
        "files": ["files", "folder", "directory", "trash", "desktop", "nautilus"],
        "system": ["ubuntu", "terminal", "command", "ssh", "sudo", "password", "conda"],
    }
    
    def __init__(self):
        self.knowledge_base: Dict[str, List[KnowledgeItem]] = {} = {}
        self.all_items: List[KnowledgeItem] = []
        logger.info("DomainRAG initialized (keyword matching mode)")
    
    def detect_domain(self, text: str) -> str:
        text_lower = text.lower()
        
        domain_scores = {}
        for domain, keywords in self.DOMAIN_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in text_lower)
            if score > 0:
                domain_scores[domain] = score
        
        if domain_scores:
            return max(domain_scores, key=domain_scores.get)
        return "general"
    
    def load_knowledge_base(self, knowledge_file: str, organize_by_domain: bool = True):
        if not os.path.exists(knowledge_file):
            logger.error(f"Knowledge file not found: {knowledge_file}")
            return
        
        with open(knowledge_file, 'r', encoding='utf-8') as f:
            raw_knowledge = json.load(f)
        
        self.knowledge_base = {}
        self.all_items = []
        
        for task_desc, solution in raw_knowledge.items():
            # Detect domain from task description
            domain = self.detect_domain(task_desc) if organize_by_domain else "general"
            
            item = KnowledgeItem(
                task_description=task_desc,
                solution=solution,
                domain=domain
            )
            
            self.all_items.append(item)
            
            if domain not in self.knowledge_base:
                self.knowledge_base[domain] = []
            self.knowledge_base[domain].append(item)
        
        logger.info(f"Loaded {len(self.all_items)} knowledge items across {len(self.knowledge_base)} domains")
        for domain, items in self.knowledge_base.items():
            logger.debug(f"  {domain}: {len(items)} items")
    
    def _keyword_similarity(self, query: str, item: KnowledgeItem) -> float:
        """
        Compute keyword-based similarity score using Jaccard similarity.
        """
        query_keywords = set(KnowledgeItem._extract_keywords(query))
        item_keywords = set(item.keywords)
        
        if not query_keywords or not item_keywords:
            return 0.0
        
        intersection = query_keywords & item_keywords
        union = query_keywords | item_keywords
        
        # Jaccard similarity with bonus for exact matches
        base_score = len(intersection) / len(union)
        
        # Bonus for matching important words
        important_match_bonus = 0
        for word in intersection:
            if len(word) > 4:  # Longer words are more meaningful
                important_match_bonus += 0.1
        
        return min(base_score + important_match_bonus, 1.0)
    
    def query(
        self,
        task: str,
        domain: Optional[str] = None,
        top_k: int = 3,
        similarity_threshold: float = 0.15,
        include_cross_domain: bool = False
    ) -> List[Dict[str, Any]]:
        if not self.all_items:
            logger.warning("Knowledge base is empty")
            return []
        
        # Auto-detect domain if not provided
        if domain is None:
            domain = self.detect_domain(task)
        
        logger.debug(f"Querying RAG for domain: {domain}")
        
        # Get items to search
        if include_cross_domain:
            search_items = self.all_items
        else:
            search_items = self.knowledge_base.get(domain, [])
            if not search_items:
                logger.debug(f"No items in domain '{domain}', searching all domains")
                search_items = self.all_items
        
        # Calculate keyword similarities
        results = []
        for item in search_items:
            similarity = self._keyword_similarity(task, item)
            
            if similarity >= similarity_threshold:
                results.append({
                    "task": item.task_description,
                    "solution": item.solution,
                    "domain": item.domain,
                    "similarity": similarity
                })
        
        # Sort by similarity and return top_k
        results.sort(key=lambda x: x["similarity"], reverse=True)
        return results[:top_k]
    
    def get_domain_hints(
        self,
        task: str,
        domain: Optional[str] = None,
        max_hints: int = 2,
        max_length: int = 1000
    ) -> str:
        results = self.query(task, domain=domain, top_k=max_hints)
        
        if not results:
            return ""
        
        domain_name = results[0]["domain"] if results else "General"
        
        hints_lines = [f"\n## {domain_name.upper()} Tips:"]
        
        for i, result in enumerate(results, 1):
            solution = result["solution"]
            
            # Truncate if too long
            if len(solution) > max_length:
                solution = solution[:max_length] + "..."
            
            task_preview = result['task'][:80]
            hints_lines.append(f"\n### Reference: \"{task_preview}...\"")
            hints_lines.append(solution)
        
        return "\n".join(hints_lines)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about the knowledge base."""
        return {
            "total_items": len(self.all_items),
            "domains": list(self.knowledge_base.keys()),
            "items_per_domain": {d: len(items) for d, items in self.knowledge_base.items()},
            "mode": "keyword_matching"
        }


# Convenience function for quick usage
def create_domain_rag(knowledge_file: str) -> DomainRAG:
    rag = DomainRAG()
    rag.load_knowledge_base(knowledge_file)
    return rag


# test
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    knowledge_path = "mm_agents/mobileagent_v3/Perplexica_rag_knowledge_verified.json"
    
    if os.path.exists(knowledge_path):
        rag = create_domain_rag(knowledge_path)
        
        # Test query
        test_tasks = [
            "disable the cone icon in VLC splash screen",
            "export document as PDF in LibreOffice",
            "set Bing as default search engine in Chrome"
        ]
        
        for task in test_tasks:
            print(f"\n{'='*60}")
            print(f"Task: {task}")
            print(f"Detected domain: {rag.detect_domain(task)}")
            
            hints = rag.get_domain_hints(task, max_hints=1, max_length=500)
            print(f"\nHints:\n{hints[:500]}...")
    else:
        print(f"Knowledge file not found: {knowledge_path}")
