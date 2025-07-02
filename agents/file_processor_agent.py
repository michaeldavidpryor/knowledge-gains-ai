"""
File Processor Agent for Knowledge Gains - Handles fitness-related document processing
"""

import asyncio
import os
import json
from typing import Any, Dict, List, Optional
from pathlib import Path
import hashlib

from .base_agent import BaseAgent


class FileProcessorAgent(BaseAgent):
    """Agent specialized in processing fitness-related documents and extracting workout information"""
    
    def __init__(self, upload_directory: str = "uploads"):
        super().__init__(name="FileProcessorAgent", model="gpt-4", temperature=0.2)
        self.upload_directory = upload_directory
        self.supported_formats = {'.pdf', '.txt', '.md', '.doc', '.docx'}
        self.processed_files_cache = {}
        
        # Create upload directory if it doesn't exist
        Path(upload_directory).mkdir(parents=True, exist_ok=True)
        
    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process uploaded fitness files and extract relevant information"""
        
        if isinstance(input_data, dict):
            file_info = input_data
        else:
            return {"error": "Invalid input format for file processor"}
            
        file_paths = file_info.get("file_paths", [])
        context_request = file_info.get("context", "extract workout and fitness information")
        
        if not file_paths:
            return {"error": "No files provided for processing"}
            
        results = []
        
        for file_path in file_paths:
            try:
                file_result = await self._process_single_file(file_path, context_request)
                results.append(file_result)
            except Exception as e:
                results.append({
                    "file_path": file_path,
                    "error": str(e),
                    "processed": False
                })
        
        # Synthesize information across all files
        synthesis = await self._synthesize_file_information(results, context_request)
        
        return {
            "type": "file_processing_complete",
            "individual_files": results,
            "synthesis": synthesis,
            "files_processed": len([r for r in results if r.get("processed", False)]),
            "total_files": len(results)
        }
    
    async def _process_single_file(self, file_path: str, context_request: str) -> Dict[str, Any]:
        """Process a single file and extract fitness-relevant information"""
        
        # Check cache first
        file_hash = self._get_file_hash(file_path)
        if file_hash in self.processed_files_cache:
            cached_result = self.processed_files_cache[file_hash]
            cached_result["from_cache"] = True
            return cached_result
        
        # Read file content
        content = await self._read_file_content(file_path)
        if not content:
            return {
                "file_path": file_path,
                "error": "Could not read file content",
                "processed": False
            }
        
        # Extract fitness information using AI
        system_prompt = """You are a fitness and exercise science expert. Analyze documents for:
        1. Workout programs and routines
        2. Exercise specifications (sets, reps, weights, progression)
        3. Training principles and methodologies
        4. Equipment requirements
        5. Scientific findings related to strength training
        6. Progression schemes and periodization
        
        Extract specific, actionable information that can be used to create workout programs."""
        
        analysis_prompt = f"""
        Analyze this fitness/exercise document and extract key information:
        
        File: {os.path.basename(file_path)}
        Context request: {context_request}
        
        Content: {content[:8000]}  # Limit content to avoid token limits
        
        Extract and return the following in JSON format:
        {{
            "document_type": "research_paper|workout_program|exercise_guide|nutrition_guide|other",
            "key_findings": ["list", "of", "key", "points"],
            "workout_programs": [
                {{
                    "name": "Program name",
                    "description": "Brief description",
                    "duration": "Duration in weeks",
                    "frequency": "Days per week",
                    "exercises": ["exercise", "names"],
                    "equipment": ["required", "equipment"],
                    "progression": "How to progress"
                }}
            ],
            "exercises": [
                {{
                    "name": "Exercise name",
                    "muscle_groups": ["targeted", "muscles"],
                    "equipment": "required equipment",
                    "sets_reps": "typical sets x reps",
                    "notes": "form cues or variations"
                }}
            ],
            "training_principles": ["principle1", "principle2"],
            "equipment_mentioned": ["equipment", "list"],
            "scientific_evidence": "Summary of any research findings",
            "practical_applications": "How this information can be applied to programming"
        }}
        """
        
        analysis_response = await self.send_message(analysis_prompt, system_prompt)
        
        try:
            analysis_data = json.loads(analysis_response)
            
            result = {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_hash": file_hash,
                "content_length": len(content),
                "analysis": analysis_data,
                "processed": True,
                "from_cache": False
            }
            
            # Cache the result
            self.processed_files_cache[file_hash] = result
            
            return result
            
        except json.JSONDecodeError:
            # Fallback to text analysis if JSON parsing fails
            return {
                "file_path": file_path,
                "file_name": os.path.basename(file_path),
                "file_hash": file_hash,
                "content_length": len(content),
                "analysis_text": analysis_response,
                "processed": True,
                "from_cache": False,
                "note": "Analysis in text format due to parsing error"
            }
    
    async def _read_file_content(self, file_path: str) -> Optional[str]:
        """Read content from various file formats"""
        
        file_ext = Path(file_path).suffix.lower()
        
        try:
            if file_ext == '.pdf':
                return await self._read_pdf(file_path)
            elif file_ext in {'.txt', '.md'}:
                return await self._read_text_file(file_path)
            elif file_ext in {'.doc', '.docx'}:
                return await self._read_word_doc(file_path)
            else:
                # Try to read as text
                return await self._read_text_file(file_path)
                
        except Exception as e:
            print(f"Error reading file {file_path}: {e}")
            return None
    
    async def _read_pdf(self, file_path: str) -> Optional[str]:
        """Read PDF content using PyPDF2 or similar"""
        try:
            import PyPDF2
            
            with open(file_path, 'rb') as file:
                reader = PyPDF2.PdfReader(file)
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
                
        except ImportError:
            return "PyPDF2 not installed - cannot process PDF files"
        except Exception as e:
            return f"Error reading PDF: {str(e)}"
    
    async def _read_text_file(self, file_path: str) -> Optional[str]:
        """Read plain text files"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                return file.read()
        except Exception as e:
            return f"Error reading text file: {str(e)}"
    
    async def _read_word_doc(self, file_path: str) -> Optional[str]:
        """Read Word documents using python-docx"""
        try:
            import docx
            
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
            
        except ImportError:
            return "python-docx not installed - cannot process Word documents"
        except Exception as e:
            return f"Error reading Word document: {str(e)}"
    
    def _get_file_hash(self, file_path: str) -> str:
        """Generate hash of file for caching"""
        try:
            with open(file_path, 'rb') as file:
                file_hash = hashlib.md5(file.read()).hexdigest()
            return file_hash
        except Exception:
            return hashlib.md5(file_path.encode()).hexdigest()
    
    async def _synthesize_file_information(self, file_results: List[Dict], context_request: str) -> Dict[str, Any]:
        """Synthesize information from multiple processed files"""
        
        if not file_results:
            return {"error": "No files to synthesize"}
        
        # Gather all successful analyses
        successful_analyses = [
            result["analysis"] for result in file_results 
            if result.get("processed") and "analysis" in result
        ]
        
        if not successful_analyses:
            return {"error": "No successful file analyses to synthesize"}
        
        system_prompt = """You are a fitness programming expert. Synthesize information from multiple fitness documents to create comprehensive insights for workout program creation."""
        
        synthesis_prompt = f"""
        Synthesize the following fitness document analyses into actionable insights:
        
        Context: {context_request}
        
        Document Analyses:
        {json.dumps(successful_analyses, indent=2)}
        
        Create a comprehensive synthesis in JSON format:
        {{
            "overall_themes": ["key", "themes", "across", "documents"],
            "recommended_programs": [
                {{
                    "name": "Synthesized program name",
                    "description": "Combined approach description",
                    "best_for": "Who this program is best for",
                    "duration": "Recommended duration",
                    "frequency": "Training frequency",
                    "key_exercises": ["essential", "exercises"],
                    "equipment_needed": ["equipment", "list"],
                    "progression_strategy": "How to progress"
                }}
            ],
            "key_principles": ["training", "principles", "to", "follow"],
            "equipment_recommendations": ["equipment", "priorities"],
            "scientific_backing": "Summary of scientific evidence",
            "implementation_tips": ["practical", "tips", "for", "implementation"],
            "program_variations": ["beginner", "intermediate", "advanced"]
        }}
        """
        
        synthesis_response = await self.send_message(synthesis_prompt, system_prompt)
        
        try:
            synthesis_data = json.loads(synthesis_response)
            return {
                "synthesis": synthesis_data,
                "source_files": len(successful_analyses),
                "synthesis_type": "json"
            }
        except json.JSONDecodeError:
            return {
                "synthesis_text": synthesis_response,
                "source_files": len(successful_analyses),
                "synthesis_type": "text"
            }
    
    async def extract_specific_program(self, file_path: str, program_name: str) -> Dict[str, Any]:
        """Extract a specific workout program from a document"""
        
        content = await self._read_file_content(file_path)
        if not content:
            return {"error": f"Could not read file: {file_path}"}
        
        system_prompt = f"""You are a fitness expert extracting specific workout programs from documents. 
        Focus on finding the program named "{program_name}" or the most similar program."""
        
        extraction_prompt = f"""
        Find and extract the workout program "{program_name}" from this document:
        
        {content[:8000]}
        
        Return detailed program information in JSON format:
        {{
            "program_found": true/false,
            "program_name": "Actual program name found",
            "similarity_score": "How closely it matches the request (1-10)",
            "program_details": {{
                "description": "Program description",
                "duration": "Duration in weeks",
                "frequency": "Days per week",
                "weekly_structure": [
                    {{
                        "day": 1,
                        "name": "Workout name",
                        "exercises": [
                            {{
                                "name": "Exercise name",
                                "sets": 4,
                                "reps": "8-12",
                                "weight": "percentage of 1RM or description",
                                "rest": "rest time",
                                "notes": "any special notes"
                            }}
                        ]
                    }}
                ],
                "equipment_required": ["equipment", "list"],
                "progression": "How to progress week to week"
            }}
        }}
        """
        
        extraction_response = await self.send_message(extraction_prompt, system_prompt)
        
        try:
            return json.loads(extraction_response)
        except json.JSONDecodeError:
            return {
                "program_found": False,
                "error": "Could not parse program extraction",
                "raw_response": extraction_response
            }
    
    async def get_capabilities(self) -> List[str]:
        """Return file processing capabilities"""
        return [
            "pdf_processing",
            "document_analysis",
            "workout_extraction",
            "program_synthesis",
            "exercise_database_creation",
            "scientific_literature_analysis"
        ]