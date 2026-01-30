"""Slack MCP - Complete Implementation"""
from typing import Dict, Any, List
import httpx
from ...config import settings

class SlackMCP:
    """Slack MCP for notifications"""
    
    def __init__(self):
        self.bot_token = settings.SLACK_BOT_TOKEN
        self.connected = bool(self.bot_token)
    
    async def send_message(self, channel: str, text: str) -> str:
        """Send message to Slack channel"""
        if not self.connected:
            return "Slack not configured (no bot token)"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={"Authorization": f"Bearer {self.bot_token}"},
                    json={"channel": channel, "text": text}
                )
                
                result = response.json()
                if result.get("ok"):
                    return f"Message sent successfully to {channel}"
                else:
                    return f"Error: {result.get('error', 'Unknown error')}"
        
        except Exception as e:
            return f"Error sending message: {str(e)}"
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get available tools"""
        return [
            {
                "name": "send_slack_message",
                "description": "Send a message to a Slack channel",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "channel": {"type": "string", "description": "Channel ID or name"},
                        "text": {"type": "string", "description": "Message text"}
                    },
                    "required": ["channel", "text"]
                }
            }
        ]