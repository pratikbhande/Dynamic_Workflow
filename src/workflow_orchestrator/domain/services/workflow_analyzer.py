"""Workflow Analyzer - Intelligent task classification"""
from typing import Dict, Any, List


class WorkflowAnalyzer:
    """Analyzes user tasks to determine output architecture"""
    
    def __init__(self):
        # Chat-related keywords
        self.chat_keywords = [
            'chatbot', 'chat', 'ask questions', 'talk to', 'interact',
            'conversation', 'query', 'qa system', 'question answering',
            'ask', 'rag', 'retrieval'
        ]
        
        # UI framework keywords
        self.ui_keywords = {
            'streamlit': ['streamlit', 'st.'],
            'gradio': ['gradio', 'gr.']
        }
        
        # Non-chat task keywords
        self.non_chat_keywords = [
            'analyze', 'report', 'generate report', 'create report',
            'process data', 'transform', 'convert', 'export',
            'visualize', 'chart', 'graph', 'dashboard'
        ]
    
    def analyze_task(self, task_description: str) -> Dict[str, Any]:
        """
        Analyze task to determine architecture
        
        Returns:
            {
                "needs_chat_endpoint": bool,  # Build /chat endpoint?
                "needs_ui": bool,             # Build Streamlit/Gradio?
                "ui_framework": str|None,     # Which UI framework?
                "is_one_time_task": bool,     # One-time vs interactive?
                "architecture": str           # "chat_api", "chat_ui", "one_time"
            }
        """
        task_lower = task_description.lower()
        
        # Detect chat requirement
        needs_chat = any(keyword in task_lower for keyword in self.chat_keywords)
        
        # Detect UI framework request
        ui_framework = None
        for framework, keywords in self.ui_keywords.items():
            if any(keyword in task_lower for keyword in keywords):
                ui_framework = framework
                break
        
        # Determine if one-time task
        is_one_time = any(keyword in task_lower for keyword in self.non_chat_keywords) and not needs_chat
        
        # Determine architecture
        if needs_chat and ui_framework:
            architecture = "chat_ui"  # Backend + /chat + UI
            needs_chat_endpoint = True
            needs_ui = True
        elif needs_chat and not ui_framework:
            architecture = "chat_api"  # Backend + /chat only
            needs_chat_endpoint = True
            needs_ui = False
        else:
            architecture = "one_time"  # Just execute and return result
            needs_chat_endpoint = False
            needs_ui = False
        
        return {
            "needs_chat_endpoint": needs_chat_endpoint,
            "needs_ui": needs_ui,
            "ui_framework": ui_framework,
            "is_one_time_task": is_one_time,
            "architecture": architecture,
            "reasoning": self._explain_architecture(architecture, ui_framework)
        }
    
    def _explain_architecture(self, architecture: str, ui_framework: str) -> str:
        """Explain the chosen architecture"""
        
        if architecture == "chat_api":
            return "Building chat backend with /chat API endpoint. No UI requested - users can interact via API."
        elif architecture == "chat_ui":
            return f"Building chat backend with /chat API endpoint + {ui_framework} UI. Users can use UI or API directly."
        elif architecture == "one_time":
            return "One-time task. No chat interaction needed. Will execute and return results."
        
        return "Standard workflow"