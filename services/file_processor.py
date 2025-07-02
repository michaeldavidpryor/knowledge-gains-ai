"""
File Processor Service for analyzing uploaded fitness documents
Using OpenAI Responses API with file search and code interpreter
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base_service import BaseService


class FileProcessorService(BaseService):
    """Service for processing fitness-related documents using Responses API"""

    def __init__(self, upload_directory: str = "uploads"):
        super().__init__(name="FileProcessorService", model="gpt-4.1-2025-04-14", temperature=0.2)
        self.upload_directory = upload_directory
        self.supported_formats = {".pdf", ".txt", ".md", ".doc", ".docx", ".csv", ".xlsx", ".json"}
        self.processed_files_cache = {}

        # Create upload directory if it doesn't exist
        Path(upload_directory).mkdir(parents=True, exist_ok=True)

    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process uploaded fitness files and extract relevant information"""
        
        # Handle different input types
        if isinstance(input_data, dict):
            if "file_paths" in input_data:
                return await self._process_files(input_data["file_paths"])
            elif "file_path" in input_data:
                return await self._process_files([input_data["file_path"]])
            elif "analyze_request" in input_data:
                return await self._analyze_with_context(input_data)
        
        return {
            "type": "error",
            "message": "Invalid input format",
            "expected": "Dictionary with 'file_paths' or 'file_path' key"
        }

    async def _process_files(self, file_paths: List[str]) -> Dict[str, Any]:
        """Process multiple files using file search"""
        
        valid_files = []
        skipped_files = []
        
        # Validate files
        for file_path in file_paths:
            path = Path(file_path)
            if path.exists() and path.suffix in self.supported_formats:
                valid_files.append(str(path))
            else:
                skipped_files.append({
                    "path": file_path,
                    "reason": "File not found" if not path.exists() else f"Unsupported format: {path.suffix}"
                })
        
        if not valid_files:
            return {
                "type": "error",
                "message": "No valid files to process",
                "skipped_files": skipped_files
            }
        
        try:
            # Upload files to OpenAI and collect file IDs for file_search tool
            file_ids: List[str] = []
            for path in valid_files:
                try:
                    with open(path, "rb") as f:
                        up_file = await self.client.files.create(file=f, purpose="file_search")
                        file_ids.append(up_file.id)
                except Exception as e:
                    skipped_files.append({"path": path, "reason": str(e)})

            # Analyze the files with file_search tool
            analysis_prompt = f"""Analyze the uploaded fitness documents and extract:
            
            1. **Workout Programs**: All exercises, sets, reps, rest periods, and progression schemes
            2. **Training Methodology**: Periodization, volume, intensity, frequency principles
            3. **Exercise Techniques**: Form cues, common mistakes, safety considerations
            4. **Nutrition Information**: Meal plans, macros, timing, supplements
            5. **Recovery Protocols**: Rest days, deload weeks, mobility work
            
            Provide a comprehensive analysis with structured JSON output for workout programs.
            
            Files analyzed: {len(valid_files)}"""
            
            # Build input items referencing files (attachments)
            input_items = [
                {
                    "role": "user",
                    "type": "message",
                    "content": [
                        {"type": "input_text", "text": analysis_prompt}
                    ],
                    "attachments": [{"file_id": fid} for fid in file_ids] if file_ids else None,
                }
            ]

            response = await self.send_message(input_items, extra_tools=[{"type": "file_search"}])
            
            # Try to extract structured data
            structured_data = self._extract_structured_data(response)
            
            return {
                "type": "file_analysis_complete",
                "files_processed": len(valid_files),
                "analysis": response,
                "structured_data": structured_data,
                "file_ids": file_ids,
                "skipped_files": skipped_files
            }
            
        except Exception as e:
            return {
                "type": "error",
                "message": f"Error processing files: {str(e)}",
                "files_attempted": valid_files
            }

    async def _analyze_with_context(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze specific aspects of previously uploaded files"""
        
        request = input_data.get("analyze_request", "")
        context = input_data.get("context", {})
        
        # Build analysis prompt
        prompt = f"""Based on the uploaded fitness documents, {request}
        
        Context: {json.dumps(context, indent=2) if context else 'General analysis'}
        
        Provide detailed analysis with practical recommendations."""
        
        response = await self.send_message(prompt)
        
        return {
            "type": "contextual_analysis",
            "request": request,
            "analysis": response,
            "context": context
        }

    async def extract_workout_program(self, file_path: str) -> Dict[str, Any]:
        """Extract a structured workout program from a file"""
        
        # Upload file for code interpreter
        with open(file_path, "rb") as f:
            up_file = await self.client.files.create(file=f, purpose="code_interpreter")
            file_id = up_file.id

        extraction_prompt = """Extract the workout program from this file and structure it as JSON:
        {
            "program_name": "string",
            "duration_weeks": number,
            "days_per_week": number,
            "workouts": [
                {
                    "day": "string",
                    "name": "string",
                    "exercises": [
                        {
                            "name": "string",
                            "sets": number,
                            "reps": "string",
                            "rest": "string",
                            "notes": "string"
                        }
                    ]
                }
            ],
            "progression_scheme": "string",
            "notes": "string"
        }
        
        Use the code interpreter to process and structure the data."""
        
        # Build input item with attachment
        input_items = [
            {
                "role": "user",
                "type": "message",
                "content": [
                    {"type": "input_text", "text": extraction_prompt}
                ],
                "attachments": [{"file_id": file_id}]
            }
        ]

        response = await self.send_message(input_items, extra_tools=[{"type": "code_interpreter"}])
        
        # Extract JSON from response
        structured_program = self._extract_json_from_response(response)
        
        return {
            "type": "workout_extraction",
            "file": file_path,
            "program": structured_program,
            "raw_response": response
        }

    async def analyze_exercise_form(self, exercise_name: str, file_ids: Optional[List[str]] = None) -> Dict[str, Any]:
        """Analyze exercise form and technique from documents"""
        
        prompt = f"""Analyze the exercise form and technique for: {exercise_name}
        
        Extract and provide:
        1. Setup and starting position
        2. Movement execution (step by step)
        3. Common form errors to avoid
        4. Safety considerations
        5. Muscle groups targeted
        6. Variations and progressions
        7. Programming recommendations
        
        Use file search to find relevant information in the uploaded documents."""
        
        if file_ids:
            input_items = [
                {
                    "role": "user",
                    "type": "message",
                    "content": [
                        {"type": "input_text", "text": prompt}
                    ],
                    "attachments": [{"file_id": fid} for fid in file_ids]
                }
            ]
            response = await self.send_message(input_items, extra_tools=[{"type": "file_search"}])
        else:
            response = await self.send_message(prompt)
        
        return {
            "type": "form_analysis",
            "exercise": exercise_name,
            "analysis": response,
            "timestamp": os.path.getmtime(file_ids[0]) if file_ids else None
        }

    def _extract_structured_data(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract structured JSON data from text response"""
        try:
            # Look for JSON blocks in the text
            import re
            json_pattern = r'```json\s*([\s\S]*?)\s*```'
            matches = re.findall(json_pattern, text)
            
            if matches:
                return json.loads(matches[0])
            
            # Try to find JSON without code blocks
            json_start = text.find('{')
            json_end = text.rfind('}')
            
            if json_start != -1 and json_end != -1:
                potential_json = text[json_start:json_end + 1]
                return json.loads(potential_json)
                
        except json.JSONDecodeError:
            pass
        
        return None

    def _extract_json_from_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Extract JSON from response"""
        return self._extract_structured_data(response)

    async def get_capabilities(self) -> List[str]:
        """Return list of service capabilities"""
        base_capabilities = await super().get_capabilities()
        return base_capabilities + [
            "document_analysis",
            "workout_extraction", 
            "form_analysis",
            "nutrition_extraction",
            "multi_file_processing"
        ]