"""
File Search Agent for searching through local files and documents
"""

import os
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
import mimetypes
from .base_agent import BaseAgent


class FileSearchAgent(BaseAgent):
    """Agent specialized in searching through local files and extracting information"""
    
    def __init__(self, search_directories: Optional[List[str]] = None):
        super().__init__(name="FileSearchAgent", model="gpt-4", temperature=0.2)
        self.search_directories = search_directories or ["."]
        self.supported_extensions = {
            '.txt', '.md', '.py', '.js', '.ts', '.json', '.yaml', '.yml', 
            '.xml', '.html', '.htm', '.css', '.sql', '.sh', '.bash', '.log',
            '.csv', '.ini', '.cfg', '.conf'
        }
        
    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process file search request"""
        if isinstance(input_data, str):
            query = input_data
            search_type = "content"
        elif isinstance(input_data, dict):
            query = input_data.get("query", "")
            search_type = input_data.get("type", "content")  # content, filename, both
        else:
            return {"error": "Invalid input format for file search"}
            
        if not query:
            return {"error": "No search query provided"}
            
        search_results = await self.search_files(query, search_type)
        
        # Use OpenAI to analyze and summarize findings
        system_prompt = """You are a file search specialist. Analyze the file search results and provide a comprehensive summary. 
        Focus on the most relevant information found, organize it clearly, and highlight key findings. Include file paths and relevant code snippets when appropriate."""
        
        analysis_prompt = f"""
        File Search Query: {query}
        Search Type: {search_type}
        
        Search Results:
        {self._format_file_results(search_results)}
        
        Please analyze these file search results and provide:
        1. A summary of what was found
        2. Key insights or patterns
        3. Most relevant files and their contents
        4. Any recommendations based on the findings
        """
        
        analysis = await self.send_message(analysis_prompt, system_prompt)
        
        return {
            "query": query,
            "search_type": search_type,
            "analysis": analysis,
            "files_found": len(search_results),
            "results": search_results
        }
    
    async def search_files(self, query: str, search_type: str = "content") -> List[Dict[str, Any]]:
        """Search through files based on query and type"""
        results = []
        
        for directory in self.search_directories:
            if not os.path.exists(directory):
                continue
                
            for root, dirs, files in os.walk(directory):
                # Skip common non-relevant directories
                dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', '__pycache__', 'venv', 'env']]
                
                for file in files:
                    file_path = os.path.join(root, file)
                    file_ext = Path(file).suffix.lower()
                    
                    # Skip binary files and unsupported extensions
                    if file_ext not in self.supported_extensions:
                        continue
                        
                    try:
                        result = await self._search_in_file(file_path, query, search_type)
                        if result:
                            results.append(result)
                    except Exception as e:
                        # Skip files that can't be read
                        continue
                        
        return results
    
    async def _search_in_file(self, file_path: str, query: str, search_type: str) -> Optional[Dict[str, Any]]:
        """Search within a specific file"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            filename = os.path.basename(file_path)
            query_lower = query.lower()
            
            # Check filename match
            filename_match = query_lower in filename.lower()
            
            # Check content match
            content_match = query_lower in content.lower()
            
            # Determine if this file should be included
            include_file = False
            if search_type == "filename" and filename_match:
                include_file = True
            elif search_type == "content" and content_match:
                include_file = True
            elif search_type == "both" and (filename_match or content_match):
                include_file = True
                
            if not include_file:
                return None
                
            # Extract relevant snippets if content matches
            snippets = []
            if content_match:
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        snippet = {
                            "line_number": i + 1,
                            "context": '\n'.join(lines[start:end]),
                            "matched_line": line.strip()
                        }
                        snippets.append(snippet)
                        
                        # Limit to first 5 matches per file
                        if len(snippets) >= 5:
                            break
            
            return {
                "file_path": file_path,
                "filename": filename,
                "file_size": len(content),
                "filename_match": filename_match,
                "content_match": content_match,
                "snippets": snippets,
                "total_matches": len(snippets)
            }
            
        except Exception as e:
            return None
    
    def _format_file_results(self, results: List[Dict[str, Any]]) -> str:
        """Format file search results for OpenAI processing"""
        if not results:
            return "No files found matching the search criteria."
            
        formatted = f"Found {len(results)} files:\n\n"
        
        for result in results:
            formatted += f"File: {result['file_path']}\n"
            formatted += f"Size: {result['file_size']} characters\n"
            
            if result['filename_match']:
                formatted += "✓ Filename matches query\n"
            if result['content_match']:
                formatted += f"✓ Content matches ({result['total_matches']} occurrences)\n"
                
            if result['snippets']:
                formatted += "Relevant snippets:\n"
                for snippet in result['snippets'][:3]:  # Show first 3 snippets
                    formatted += f"  Line {snippet['line_number']}: {snippet['matched_line']}\n"
                    
            formatted += "---\n\n"
            
        return formatted
    
    def add_search_directory(self, directory: str):
        """Add a directory to search in"""
        if os.path.exists(directory) and directory not in self.search_directories:
            self.search_directories.append(directory)
    
    def remove_search_directory(self, directory: str):
        """Remove a directory from search"""
        if directory in self.search_directories:
            self.search_directories.remove(directory)
    
    async def get_capabilities(self) -> List[str]:
        """Return file search capabilities"""
        return [
            "file_content_search",
            "filename_search",
            "code_analysis",
            "text_extraction",
            "pattern_matching"
        ]