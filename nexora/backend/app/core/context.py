"""
Nexora Context Optimizer
Indexes, ranks, budgets, compresses, and caches repository context
"""
import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from nexora.backend.app.models import ModelRegistry
from nexora.backend.app.schemas import ContextPackageBase as ContextPackageSchema


@dataclass
class FileInfo:
    """Indexed file information"""
    path: str
    language: str
    size: int
    hash: str
    symbols: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    is_test: bool = False
    is_generated: bool = False
    last_modified: float = 0


@dataclass
class RankedFile:
    """File with relevance score"""
    file_info: FileInfo
    score: float
    reasons: List[str] = field(default_factory=list)


@dataclass
class ContextPackage:
    """Prepared context for model"""
    included_files: List[Dict[str, Any]]
    omitted_categories: List[Dict[str, Any]]
    ranking_reasons: Dict[str, str]
    cache_hits: int
    estimated_tokens: int
    compression_ratio: Optional[float]


class ContextOptimizer:
    """
    Context Optimizer - builds model context from repository.
    
    Pipeline: query extraction -> candidate retrieval -> ranking -> 
    budget allocation -> compression -> cache -> model context package.
    """
    
    def __init__(self, workspace_path: str):
        self.workspace_path = Path(workspace_path)
        self.optimizer_version = "1.0.0"
        self._cache: Dict[str, Any] = {}
        self._index: Dict[str, FileInfo] = {}
        self._indexed = False
    
    def build_context(
        self,
        task_query: str,
        model: ModelRegistry,
        current_diff: Optional[str] = None,
        recent_tool_output: Optional[str] = None,
        step_number: int = 1,
    ) -> ContextPackage:
        """
        Build optimized context package for model inference.
        
        Args:
            task_query: The task/question for the model
            model: Model registry entry with capacity info
            current_diff: Current patch/diff if any
            recent_tool_output: Recent tool execution output
            step_number: Current step number
            
        Returns:
            ContextPackage ready for model
        """
        # Ensure index is built
        if not self._indexed:
            self._build_index()
        
        # Extract query terms
        query_terms = self._extract_query_terms(task_query)
        
        # Retrieve candidate files
        candidates = self._retrieve_candidates(query_terms, current_diff)
        
        # Rank candidates
        ranked = self._rank_candidates(candidates, query_terms, current_diff, recent_tool_output)
        
        # Allocate budget
        budget = self._calculate_budget(model)
        selected, omitted = self._allocate_budget(ranked, budget, current_diff, recent_tool_output)
        
        # Compress context
        compressed = self._compress_context(selected, budget)
        
        # Check cache
        cache_hits = self._check_cache(selected)
        
        # Estimate tokens
        estimated_tokens = self._estimate_tokens(compressed, task_query, current_diff, recent_tool_output)
        
        # Build ranking reasons
        ranking_reasons = {r.file_info.path: "; ".join(r.reasons) for r in selected}
        
        # Build omitted categories
        omitted_categories = self._categorize_omitted(omitted)
        
        return ContextPackage(
            included_files=compressed,
            omitted_categories=omitted_categories,
            ranking_reasons=ranking_reasons,
            cache_hits=cache_hits,
            estimated_tokens=estimated_tokens,
            compression_ratio=None,  # Would need actual vs original
        )
    
    def _build_index(self) -> None:
        """Build repository index using Python AST"""
        self._index = {}
        
        for py_file in self.workspace_path.rglob("*.py"):
            # Skip excluded directories
            if any(part in py_file.parts for part in {".git", "__pycache__", ".venv", "venv", "env", "build", "dist"}):
                continue
            
            try:
                rel_path = py_file.relative_to(self.workspace_path)
                content = py_file.read_text(encoding="utf-8")
                
                file_info = FileInfo(
                    path=str(rel_path),
                    language="python",
                    size=len(content),
                    hash=hashlib.sha256(content.encode()).hexdigest()[:16],
                    is_test="test" in str(rel_path).lower() or "test_" in py_file.name,
                    is_generated=self._is_generated(py_file),
                    last_modified=py_file.stat().st_mtime,
                )
                
                # Extract symbols and imports using AST
                file_info.symbols, file_info.imports = self._extract_symbols(content)
                
                self._index[str(rel_path)] = file_info
                
            except Exception:
                # Skip files that can't be parsed
                continue
        
        self._indexed = True
    
    def _is_generated(self, path: Path) -> bool:
        """Check if file is likely generated"""
        generated_patterns = [
            "generated",
            "auto",
            "migrations",
            "proto",
            "pb2.py",
            "_grpc.py",
        ]
        path_str = str(path).lower()
        return any(p in path_str for p in generated_patterns)
    
    def _extract_symbols(self, content: str) -> Tuple[List[str], List[str]]:
        """Extract symbols and imports using AST"""
        import ast
        
        symbols = []
        imports = []
        
        try:
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    symbols.append(f"func:{node.name}")
                elif isinstance(node, ast.ClassDef):
                    symbols.append(f"class:{node.name}")
                    for method in node.body:
                        if isinstance(method, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            symbols.append(f"method:{node.name}.{method.name}")
                elif isinstance(node, (ast.Import, ast.ImportFrom)):
                    for alias in node.names:
                        imports.append(alias.name)
                        
        except SyntaxError:
            pass
        
        return symbols, imports
    
    def _extract_query_terms(self, query: str) -> Set[str]:
        """Extract meaningful terms from query"""
        # Simple tokenization - in production use proper NLP
        stopwords = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with", "by", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "do", "does", "did", "will", "would", "could", "should", "may", "might", "must", "can", "this", "that", "these", "those", "i", "you", "he", "she", "it", "we", "they", "me", "him", "her", "us", "them"}
        
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', query.lower())
        return {w for w in words if w not in stopwords and len(w) > 2}
    
    def _retrieve_candidates(
        self,
        query_terms: Set[str],
        current_diff: Optional[str],
    ) -> List[FileInfo]:
        """Retrieve candidate files based on query"""
        candidates = []
        
        for file_info in self._index.values():
            # Skip generated files unless explicitly needed
            if file_info.is_generated:
                continue
            
            # Always include test files if they might be relevant
            score = 0
            reasons = []
            
            # Keyword overlap
            path_lower = file_info.path.lower()
            symbols_lower = [s.lower() for s in file_info.symbols]
            
            for term in query_terms:
                if term in path_lower:
                    score += 3
                    reasons.append(f"path_match:{term}")
                for sym in symbols_lower:
                    if term in sym:
                        score += 2
                        reasons.append(f"symbol_match:{term}")
            
            # Test file relevance
            if file_info.is_test:
                score += 1
                reasons.append("test_file")
            
            # Diff relevance
            if current_diff and file_info.path in current_diff:
                score += 5
                reasons.append("in_current_diff")
            
            if score > 0:
                candidates.append(file_info)
        
        return candidates
    
    def _rank_candidates(
        self,
        candidates: List[FileInfo],
        query_terms: Set[str],
        current_diff: Optional[str],
        recent_tool_output: Optional[str],
    ) -> List[RankedFile]:
        """Rank candidates by relevance"""
        ranked = []
        
        for file_info in candidates:
            score = 0
            reasons = []
            
            path_lower = file_info.path.lower()
            symbols_lower = [s.lower() for s in file_info.symbols]
            
            # Keyword overlap (already computed, but recompute for clarity)
            for term in query_terms:
                if term in path_lower:
                    score += 3
                    reasons.append(f"path:{term}")
                for sym in symbols_lower:
                    if term in sym:
                        score += 2
                        reasons.append(f"symbol:{term}")
            
            # Import/dependency relationship
            # TODO: Build import graph
            
            # Failing test location
            if file_info.is_test and recent_tool_output:
                if "FAILED" in recent_tool_output and file_info.path in recent_tool_output:
                    score += 10
                    reasons.append("failing_test_location")
            
            # Git history signal (simplified)
            # TODO: Integrate git log
            
            # Generated file penalty
            if file_info.is_generated:
                score -= 5
                reasons.append("generated_file_penalty")
            
            # File type bonus
            if file_info.path.endswith(".py"):
                score += 1
                reasons.append("python_file")
            
            if score > 0:
                ranked.append(RankedFile(file_info=file_info, score=score, reasons=reasons))
        
        # Sort by score descending
        ranked.sort(key=lambda r: r.score, reverse=True)
        return ranked
    
    def _calculate_budget(self, model: ModelRegistry) -> int:
        """Calculate token budget for context"""
        # Reserve space for output and safety margin
        output_reservation = model.max_output_tokens
        safety_margin = 1000
        instruction_budget = 2000  # System prompt, task, etc.
        
        usable = model.context_capacity - output_reservation - safety_margin - instruction_budget
        return max(usable, 1000)
    
    def _allocate_budget(
        self,
        ranked: List[RankedFile],
        budget: int,
        current_diff: Optional[str],
        recent_tool_output: Optional[str],
    ) -> Tuple[List[RankedFile], List[RankedFile]]:
        """Allocate token budget across ranked files"""
        selected = []
        omitted = []
        used_tokens = 0
        
        # Always include current diff if present
        diff_tokens = 0
        if current_diff:
            diff_tokens = self._estimate_tokens_for_text(current_diff)
            if diff_tokens <= budget * 0.3:  # Max 30% for diff
                # Create a pseudo-ranked file for diff
                pass
        
        for ranked_file in ranked:
            file_tokens = self._estimate_file_tokens(ranked_file.file_info)
            
            if used_tokens + file_tokens <= budget:
                selected.append(ranked_file)
                used_tokens += file_tokens
            else:
                omitted.append(ranked_file)
        
        return selected, omitted
    
    def _compress_context(
        self,
        selected: List[RankedFile],
        budget: int,
    ) -> List[Dict[str, Any]]:
        """Compress selected files to fit budget"""
        compressed = []
        
        for ranked_file in selected:
            file_info = ranked_file.file_info
            path = file_info.path
            
            # Read file content
            full_path = self.workspace_path / path
            try:
                content = full_path.read_text(encoding="utf-8")
            except Exception:
                content = f"# Could not read {path}"
            
            # For now, include full file (compression is future work)
            compressed.append({
                "path": path,
                "content": content,
                "language": file_info.language,
                "symbols": file_info.symbols,
                "relevance_score": ranked_file.score,
                "reasons": ranked_file.reasons,
            })
        
        return compressed
    
    def _check_cache(self, selected: List[RankedFile]) -> int:
        """Check cache for file summaries"""
        hits = 0
        for ranked_file in selected:
            cache_key = f"{ranked_file.file_info.path}:{ranked_file.file_info.hash}"
            if cache_key in self._cache:
                hits += 1
        return hits
    
    def _estimate_tokens(self, compressed: List[Dict], task_query: str, current_diff: Optional[str], recent_tool_output: Optional[str]) -> int:
        """Estimate total tokens (rough approximation: 1 token ≈ 4 chars)"""
        total_chars = len(task_query)
        
        if current_diff:
            total_chars += len(current_diff)
        if recent_tool_output:
            total_chars += len(recent_tool_output)
        
        for file_data in compressed:
            total_chars += len(file_data.get("content", ""))
        
        return total_chars // 4
    
    def _estimate_file_tokens(self, file_info: FileInfo) -> int:
        """Estimate tokens for a file"""
        return file_info.size // 4
    
    def _estimate_tokens_for_text(self, text: str) -> int:
        return len(text) // 4
    
    def _categorize_omitted(self, omitted: List[RankedFile]) -> List[Dict[str, Any]]:
        """Categorize omitted files by reason"""
        categories: Dict[str, List[str]] = {}
        
        for ranked_file in omitted:
            reason = "low_relevance"
            if ranked_file.file_info.is_generated:
                reason = "generated_file"
            elif ranked_file.file_info.is_test:
                reason = "test_file_low_relevance"
            
            if reason not in categories:
                categories[reason] = []
            categories[reason].append(ranked_file.file_info.path)
        
        return [
            {"category": cat, "count": len(files), "files": files[:10]}
            for cat, files in categories.items()
        ]
    
    def to_schema(self, package: ContextPackage, run_id: str, step_number: int, model_id: Optional[str] = None) -> ContextPackageSchema:
        """Convert to API schema"""
        return ContextPackageSchema(
            id=run_id,
            run_id=run_id,
            step_number=step_number,
            model_id=model_id,
            included_files=package.included_files,
            omitted_categories=package.omitted_categories,
            ranking_reasons=package.ranking_reasons,
            cache_hits=package.cache_hits,
            estimated_input_tokens=package.estimated_tokens,
            actual_input_tokens=None,
            compression_ratio=package.compression_ratio,
            context_optimizer_version=self.optimizer_version,
            created_at=datetime.now(),
        )


# Need to import datetime
from datetime import datetime
import re
