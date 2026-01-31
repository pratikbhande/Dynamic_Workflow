from typing import List, Dict, Any, Set
from collections import defaultdict, deque


class DependencyResolver:
    """Resolves dependencies between agents and determines execution order"""
    
    def topological_sort(
        self,
        agents: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> List[List[str]]:
        """
        Perform topological sort to determine execution levels
        
        Returns: List of lists, where each inner list contains agent IDs
                that can be executed in parallel
        """
        
        # Build adjacency list and in-degree count
        graph = defaultdict(list)
        in_degree = defaultdict(int)
        
        # Initialize all agents with in-degree 0
        for agent in agents:
            in_degree[agent["id"]] = 0
        
        # Build graph from edges
        for edge in edges:
            # Handle both field name formats
            from_agent = edge.get("from_agent") or edge.get("from")
            to_agent = edge.get("to_agent") or edge.get("to")
            
            graph[from_agent].append(to_agent)
            in_degree[to_agent] += 1
        
        # Find all nodes with in-degree 0
        queue = deque([agent_id for agent_id, degree in in_degree.items() if degree == 0])
        
        levels = []
        
        while queue:
            # All agents in current level can execute in parallel
            current_level = list(queue)
            levels.append(current_level)
            
            # Process current level
            next_queue = deque()
            for agent_id in current_level:
                # Remove this agent and update in-degrees
                for neighbor in graph[agent_id]:
                    in_degree[neighbor] -= 1
                    if in_degree[neighbor] == 0:
                        next_queue.append(neighbor)
            
            queue = next_queue
        
        # Check for cycles
        if sum(len(level) for level in levels) != len(agents):
            raise ValueError("Circular dependency detected in workflow")
        
        return levels
    
    def validate_workflow(
        self,
        agents: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Validate workflow structure"""
        
        errors = []
        warnings = []
        
        agent_ids = {agent["id"] for agent in agents}
        
        # Check edge references
        for edge in edges:
            from_agent = edge.get("from_agent") or edge.get("from")
            to_agent = edge.get("to_agent") or edge.get("to")
            
            if from_agent not in agent_ids:
                errors.append(f"Edge references unknown agent: {from_agent}")
            if to_agent not in agent_ids:
                errors.append(f"Edge references unknown agent: {to_agent}")
        
        # Check for isolated agents
        connected_agents = set()
        for edge in edges:
            from_agent = edge.get("from_agent") or edge.get("from")
            to_agent = edge.get("to_agent") or edge.get("to")
            connected_agents.add(from_agent)
            connected_agents.add(to_agent)
        
        isolated = agent_ids - connected_agents
        if isolated and len(agents) > 1:
            warnings.append(f"Isolated agents (no connections): {isolated}")
        
        # Check for cycles
        try:
            self.topological_sort(agents, edges)
        except ValueError as e:
            errors.append(str(e))
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }