"""Error Memory - Learn from mistakes"""
from typing import Dict, Any, List, Optional
import re
from ...infrastructure.database.mongodb import get_mongodb


class ErrorMemory:
    """Intelligent error pattern recognition and solution storage"""
    
    def __init__(self):
        self.error_patterns = {
            # Common Python errors
            "KeyError": {
                "pattern": r"KeyError: '(.+?)'",
                "common_solutions": [
                    "Check if key exists: if 'key' in dict:",
                    "Use .get() method: dict.get('key', default_value)",
                    "Check column names: df.columns.tolist()"
                ]
            },
            "AttributeError_applymap": {
                "pattern": r"AttributeError.*applymap",
                "common_solutions": [
                    "Replace df.applymap() with df.map() (pandas >= 2.1.0)",
                    "Use df.apply(lambda col: col.map(func))"
                ]
            },
            "ModuleNotFoundError": {
                "pattern": r"ModuleNotFoundError: No module named '(.+?)'",
                "common_solutions": [
                    "Install missing package: pip install {module}",
                    "Check package name spelling",
                    "Add to requirements.txt"
                ]
            },
            "FileNotFoundError": {
                "pattern": r"FileNotFoundError.*'(.+?)'",
                "common_solutions": [
                    "Check file path is correct",
                    "Use absolute path: os.path.join(settings.UPLOAD_DIR, filename)",
                    "Verify file was uploaded"
                ]
            },
            "ValueError_trailing_spaces": {
                "pattern": r"ValueError.*trailing",
                "common_solutions": [
                    "Strip column names: df.columns = df.columns.str.strip()",
                    "Clean whitespace: df = df.apply(lambda x: x.str.strip() if x.dtype == 'object' else x)"
                ]
            }
        }
    
    def extract_error_signature(self, error_message: str) -> str:
        """Extract error signature for pattern matching"""
        # Try to match known patterns
        for error_type, config in self.error_patterns.items():
            if re.search(config["pattern"], error_message, re.IGNORECASE):
                return error_type
        
        # Fallback: Use first line of error
        lines = error_message.strip().split('\n')
        return lines[-1][:100] if lines else error_message[:100]
    
    async def find_solution(self, error_message: str) -> Optional[Dict[str, Any]]:
        """Find solution from memory or patterns"""
        
        # Extract signature
        signature = self.extract_error_signature(error_message)
        
        # Check known patterns first
        for error_type, config in self.error_patterns.items():
            if re.search(config["pattern"], error_message, re.IGNORECASE):
                return {
                    "error_type": error_type,
                    "solutions": config["common_solutions"],
                    "source": "pattern_matching"
                }
        
        # Check database for learned solutions
        db = await get_mongodb()
        learned_solution = await db.get_collection("error_solutions").find_one({
            "signature": signature
        })
        
        if learned_solution:
            return {
                "error_type": signature,
                "solutions": [learned_solution["solution"]],
                "success_count": learned_solution.get("success_count", 0),
                "source": "learned"
            }
        
        return None
    
    async def store_solution(
        self,
        error_message: str,
        solution: str,
        success: bool = True
    ):
        """Store a successful solution"""
        signature = self.extract_error_signature(error_message)
        
        db = await get_mongodb()
        
        # Update or insert solution
        await db.get_collection("error_solutions").update_one(
            {"signature": signature},
            {
                "$set": {
                    "signature": signature,
                    "error_example": error_message[:500],
                    "solution": solution,
                    "last_used": __import__('datetime').datetime.utcnow()
                },
                "$inc": {"success_count": 1 if success else 0}
            },
            upsert=True
        )
        
        print(f"💾 Stored solution for: {signature}")
    
    async def get_error_stats(self) -> List[Dict[str, Any]]:
        """Get statistics on common errors"""
        db = await get_mongodb()
        
        cursor = db.get_collection("error_solutions").find().sort("success_count", -1).limit(10)
        solutions = await cursor.to_list(length=10)
        
        return [
            {
                "error_type": sol["signature"],
                "success_count": sol.get("success_count", 0),
                "solution": sol["solution"][:100] + "..."
            }
            for sol in solutions
        ]
    
    def generate_error_context(self, error_message: str, solution: Optional[Dict[str, Any]]) -> str:
        """Generate context to add to agent prompt"""
        if not solution:
            return ""
        
        context = [
            "\n⚠️ ERROR PREVENTION GUIDANCE:",
            f"Similar error detected: {solution['error_type']}",
            "\nKNOWN SOLUTIONS:"
        ]
        
        for idx, sol in enumerate(solution['solutions'], 1):
            context.append(f"{idx}. {sol}")
        
        if solution.get('success_count'):
            context.append(f"\n✅ This solution worked {solution['success_count']} times before")
        
        return "\n".join(context)