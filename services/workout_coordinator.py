"""
Workout Coordinator Service - Specialized service for generating science-based workout programs
"""

import asyncio
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from .base_service import BaseService


class WorkoutCoordinatorService(BaseService):
    """Specialized coordinator service for workout program generation"""

    def __init__(self):
        super().__init__(
            name="WorkoutCoordinatorService", model="gpt-4.1-2025-04-14", temperature=0.2
        )
        self.required_info = {
            "equipment": None,
            "duration_weeks": None,
            "days_per_week": None,
            "user_files": [],
            "program_request": None,
        }

    async def process(self, input_data: Any) -> Dict[str, Any]:
        """Process workout program request"""

        if isinstance(input_data, str):
            user_request = input_data
            additional_info = {}
        elif isinstance(input_data, dict):
            user_request = input_data.get("request", "")
            additional_info = input_data
        else:
            return {"error": "Invalid input format for workout coordinator"}

        # Extract any provided information
        self._extract_provided_info(user_request, additional_info)

        # Check if we have all required information
        missing_info = self._check_missing_information()

        if missing_info:
            return await self._request_missing_information(missing_info, user_request)

        # Generate the program
        return await self._generate_program(user_request)

    def _extract_provided_info(self, user_request: str, additional_info: Dict):
        """Extract information from user request and additional data"""

        # Extract from additional_info (form data, etc.)
        if "equipment" in additional_info:
            self.required_info["equipment"] = additional_info["equipment"]

        if "duration_weeks" in additional_info:
            self.required_info["duration_weeks"] = additional_info["duration_weeks"]

        if "days_per_week" in additional_info:
            self.required_info["days_per_week"] = additional_info["days_per_week"]

        if "user_files" in additional_info:
            self.required_info["user_files"] = additional_info["user_files"]

        self.required_info["program_request"] = user_request

        # Try to extract from natural language request
        self._extract_from_natural_language(user_request)

    def _extract_from_natural_language(self, user_request: str):
        """Extract information from natural language using AI"""

        # Equipment keywords
        equipment_keywords = {
            "full gym": ["full gym", "commercial gym", "complete gym", "gym access"],
            "home gym": ["home gym", "garage gym", "basement gym"],
            "minimal": [
                "dumbbells only",
                "barbell only",
                "basic equipment",
                "limited equipment",
            ],
            "bodyweight": ["bodyweight", "no equipment", "calisthenics"],
        }

        request_lower = user_request.lower()

        # Check for equipment mentions
        for equipment_type, keywords in equipment_keywords.items():
            if any(keyword in request_lower for keyword in keywords):
                if not self.required_info["equipment"]:
                    self.required_info["equipment"] = equipment_type
                break

        # Check for duration mentions
        import re

        # Look for week patterns
        week_pattern = r"(\d+)\s*week"
        week_match = re.search(week_pattern, request_lower)
        if week_match and not self.required_info["duration_weeks"]:
            self.required_info["duration_weeks"] = int(week_match.group(1))

        # Look for days per week patterns
        days_patterns = [
            r"(\d+)\s*days?\s*per\s*week",
            r"(\d+)\s*days?\s*a\s*week",
            r"(\d+)x\s*per\s*week",
            r"train\s*(\d+)\s*times?",
        ]

        for pattern in days_patterns:
            days_match = re.search(pattern, request_lower)
            if days_match and not self.required_info["days_per_week"]:
                self.required_info["days_per_week"] = int(days_match.group(1))
                break

    def _check_missing_information(self) -> List[str]:
        """Check what information is still missing"""
        missing = []

        if not self.required_info["equipment"]:
            missing.append("equipment")

        if not self.required_info["duration_weeks"]:
            missing.append("duration_weeks")

        if not self.required_info["days_per_week"]:
            missing.append("days_per_week")

        return missing

    async def _request_missing_information(
        self, missing_info: List[str], user_request: str
    ) -> Dict[str, Any]:
        """Generate questions to gather missing information"""

        system_prompt = """You are a fitness expert helping users create workout programs. 
        The user has made a request but is missing some key information. 
        Generate friendly, specific questions to gather the missing information.
        Be conversational and explain why you need this information."""

        missing_descriptions = {
            "equipment": "available gym equipment",
            "duration_weeks": "program duration in weeks",
            "days_per_week": "training frequency (days per week)",
        }

        missing_list = [missing_descriptions[item] for item in missing_info]

        question_prompt = f"""
        User request: "{user_request}"
        
        I need to gather the following missing information to create the best program:
        {', '.join(missing_list)}
        
        Generate friendly questions to gather this information. For each missing piece:
        
        Equipment: Ask what equipment they have access to (full gym, home gym setup, specific equipment list, etc.)
        Duration: Ask how many weeks they want the program to run
        Days per week: Ask how many days per week they can train
        
        Make it conversational and explain why each piece of information helps create a better program.
        """

        full_prompt = f"{system_prompt}\n\n{question_prompt}"
        questions = await self.send_message(full_prompt)

        return {
            "type": "information_request",
            "missing_info": missing_info,
            "questions": questions,
            "current_info": self.required_info,
        }

    async def _generate_program(self, user_request: str) -> Dict[str, Any]:
        """Generate the complete workout program"""

        system_prompt = """You are a world-class strength and conditioning coach with expertise in:
        - Exercise science and muscle hypertrophy
        - Program periodization and progressive overload
        - Equipment-specific exercise selection
        - Evidence-based training methodologies
        
        Create detailed, scientifically-backed workout programs based on user requirements."""

        # Prepare file context if available
        file_context = ""
        if self.required_info["user_files"]:
            file_context = f"\nUser has provided these relevant files: {self.required_info['user_files']}"

        program_prompt = f"""
        Create a comprehensive workout program with these specifications:
        
        User Request: {user_request}
        Equipment Available: {self.required_info['equipment']}
        Program Duration: {self.required_info['duration_weeks']} weeks
        Training Frequency: {self.required_info['days_per_week']} days per week
        {file_context}
        
        Generate a program in this JSON format:
        {{
            "program_name": "Program Name",
            "program_description": "Brief description and goals",
            "total_weeks": {self.required_info['duration_weeks']},
            "days_per_week": {self.required_info['days_per_week']},
            "equipment_required": "{self.required_info['equipment']}",
            "weeks": [
                {{
                    "week_number": 1,
                    "focus": "Week focus (e.g., 'Adaptation', 'Volume', 'Intensity')",
                    "workouts": [
                        {{
                            "day": 1,
                            "workout_name": "Workout A - Upper Body",
                            "exercises": [
                                {{
                                    "name": "Barbell Bench Press",
                                    "sets": 4,
                                    "reps": "8-10",
                                    "rest_seconds": 180,
                                    "notes": "Focus on controlled tempo",
                                    "progression": "Add 2.5-5lbs when you can complete all sets at top of rep range"
                                }}
                            ]
                        }}
                    ]
                }}
            ],
            "progression_notes": "How to progress week to week",
            "deload_info": "When and how to deload"
        }}
        
        Include:
        - Progressive overload schemes
        - Proper exercise selection for available equipment
        - Scientifically-backed rep ranges and set schemes
        - Rest periods optimized for goals
        - Clear progression guidelines
        - Exercise substitutions if needed
        """

        full_program_prompt = f"{system_prompt}\n\n{program_prompt}"
        program_response = await self.send_message(full_program_prompt)

        try:
            program_data = json.loads(program_response)

            # Add metadata
            program_data["generated_at"] = datetime.now().isoformat()
            program_data["user_request"] = user_request
            program_data["agent_info"] = {
                "coordinator": "WorkoutCoordinatorService",
                "model": self.model,
                "version": "1.0",
            }

            return {
                "type": "program_generated",
                "program": program_data,
                "success": True,
            }

        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return {
                "type": "program_text",
                "program_text": program_response,
                "success": True,
                "note": "Program generated in text format, may need manual formatting",
            }

    async def modify_workout(
        self, workout_data: Dict, modification_request: str
    ) -> Dict[str, Any]:
        """Modify a specific workout based on user feedback"""

        system_prompt = """You are a fitness expert helping modify workouts based on user feedback.
        Make intelligent substitutions while maintaining the program's integrity and goals."""

        modification_prompt = f"""
        Original workout: {json.dumps(workout_data, indent=2)}
        
        User modification request: {modification_request}
        Available equipment: {self.required_info['equipment']}
        
        Modify the workout to address the user's request while:
        1. Maintaining similar muscle groups and movement patterns
        2. Keeping appropriate volume and intensity
        3. Using only available equipment
        4. Preserving the workout's role in the overall program
        
        Return the modified workout in the same JSON format.
        """

        full_mod_prompt = f"{system_prompt}\n\n{modification_prompt}"
        modified_response = await self.send_message(full_mod_prompt)

        try:
            modified_workout = json.loads(modified_response)
            return {
                "success": True,
                "modified_workout": modified_workout,
                "modification_applied": modification_request,
            }
        except json.JSONDecodeError:
            return {
                "success": False,
                "error": "Could not parse modified workout",
                "text_response": modified_response,
            }

    async def calculate_progression(
        self, base_weight: float, week: int, exercise_name: str, progression_scheme: str
    ) -> float:
        """Calculate recommended weight for a given week based on progression scheme"""

        # Common progression schemes
        if "linear" in progression_scheme.lower():
            # Simple linear progression - add weight each week
            increment = 2.5 if "upper" in progression_scheme.lower() else 5.0
            return base_weight + (increment * (week - 1))

        elif "percentage" in progression_scheme.lower():
            # Percentage-based progression
            week_multipliers = {
                1: 1.0,  # 100% - baseline
                2: 1.025,  # 102.5%
                3: 1.05,  # 105%
                4: 1.075,  # 107.5%
                5: 1.1,  # 110%
                6: 1.0,  # Deload week
            }
            multiplier = week_multipliers.get(week % 6 if week % 6 != 0 else 6, 1.0)
            return base_weight * multiplier

        else:
            # Default: minimal progression
            return base_weight + (2.5 * (week - 1))

    async def get_capabilities(self) -> List[str]:
        """Return workout coordinator capabilities"""
        return [
            "program_generation",
            "exercise_selection",
            "progression_planning",
            "equipment_adaptation",
            "workout_modification",
            "science_based_programming",
        ]