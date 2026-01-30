from typing import List, Dict, Any, Set
from collections import defaultdict, deque

class DependencyResolver:
    """Resolves agent dependencies and determines execution order"""
    
    def topological_sort(self, agents: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> List[List[str]]:
        """
        Perform topological sort to determine execution order
        
        Returns:
            List of execution levels, where each level contains agent IDs that can run in parallel
        """
        
        # Build adjacency list and in-degree map
        adj_list = defaultdict(list)
        in_degree = {agent["id"]: 0 for agent in agents}
        
        for edge in edges:
            from_agent = edge["from"]
            to_agent = edge["to"]
            adj_list[from_agent].append(to_agent)
            in_degree[to_agent] += 1
        
        # Find all agents with no dependencies (in-degree = 0)
        queue = deque([agent_id for agent_id, degree in in_degree.items() if degree == 0])
        
        execution_levels = []
        
        while queue:
            # All agents in current queue can execute in parallel
            current_level = list(queue)
            execution_levels.append(current_level)
            
            # Process current level
            next_queue = deque()
            for agent_id in current_level:
                # Reduce in-degree for all dependent agents
                for neighbor in adj_list[agent_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)
            
            queue = next_queue
        
        # Check for cycles
        total_sorted = sum(len(level) for level in execution_levels)
        if total_sorted < len(agents):
            raise ValueError("Circular dependency detected in workflow!")
        
        return execution_levels
    
    def validate_workflow(self, agents: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate workflow for correctness"""
        
        agent_ids = {agent["id"] for agent in agents}
        errors = []
        warnings = []
        
        # Check edge references
        for edge in edges:
            if edge["from"] not in agent_ids:
                errors.append(f"Edge references unknown agent: {edge['from']}")
            if edge["to"] not in agent_ids:
                errors.append(f"Edge references unknown agent: {edge['to']}")
        
        # Check for isolated agents
        connected_agents = set()
        for edge in edges:
            connected_agents.add(edge["from"])
            connected_agents.add(edge["to"])
        
        isolated = agent_ids - connected_agents
        if len(isolated) > 1:  # More than just the starting agent
            warnings.append(f"Isolated agents (not connected): {isolated}")
        
        # Try topological sort to check for cycles
        try:
            self.topological_sort(agents, edges)
        except ValueError as e:
            errors.append(str(e))
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }