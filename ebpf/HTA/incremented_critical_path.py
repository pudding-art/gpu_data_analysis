class IncrementalCriticalPathAnalyzer:
    def __init__(self, cp_graph: CPGraph):
        self.graph = cp_graph
        self.original_nodes = list(self.graph.nodes)
        self.original_edges = list(self.graph.edges)
        self.node_weights = {node: 0 for node in self.graph.nodes}
        self.edge_weights = {(u, v): self.graph.edges[u, v]["weight"] for u, v in self.graph.edges}
        self.topological_order = list(nx.topological_sort(self.graph))
        self.longest_path_lengths = {node: 0 for node in self.graph.nodes}

    def initialize_longest_paths(self):
        """初始化最长路径长度"""
        for node in reversed(self.topological_order):
            max_length = 0
            for predecessor in self.graph.predecessors(node):
                edge_weight = self.graph.edges[predecessor, node]["weight"]
                current_length = self.longest_path_lengths[predecessor] + edge_weight
                if current_length > max_length:
                    max_length = current_length
            self.longest_path_lengths[node] = max_length

    def update_edge_weight(self, u: int, v: int, new_weight: int):
        """更新边权重并增量更新关键路径"""
        if self.graph.has_edge(u, v):
            old_weight = self.graph.edges[u, v]["weight"]
            self.graph.edges[u, v]["weight"] = new_weight
            self.edge_weights[(u, v)] = new_weight

            # 只需重新计算受此边影响的后续节点的最长路径
            affected_nodes = self._get_affected_nodes(u, v)
            self._update_longest_paths(affected_nodes)

    def _get_affected_nodes(self, u: int, v: int) -> List[int]:
        """获取受边(u, v)权重变化影响的节点"""
        affected = []
        queue = deque([v])
        visited = set()

        while queue:
            node = queue.popleft()
            if node not in visited:
                visited.add(node)
                affected.append(node)
                for successor in self.graph.successors(node):
                    if successor not in visited:
                        queue.append(successor)

        return affected

    def _update_longest_paths(self, nodes: List[int]):
        """增量更新节点的最长路径长度"""
        for node in reversed(self.topological_order):
            if node not in nodes:
                continue

            max_length = 0
            for predecessor in self.graph.predecessors(node):
                edge_weight = self.graph.edges[predecessor, node]["weight"]
                current_length = self.longest_path_lengths[predecessor] + edge_weight
                if current_length > max_length:
                    max_length = current_length

            self.longest_path_lengths[node] = max_length

    def get_critical_path(self) -> List[int]:
        """获取当前图的关键路径"""
        max_length = max(self.longest_path_lengths.values())
        critical_nodes = [node for node, length in self.longest_path_lengths.items() if length == max_length]

        # 通过回溯找到完整的临界路径
        path = []
        current_node = critical_nodes[0]
        while current_node is not None:
            path.append(current_node)
            next_node = None
            max_edge_weight = -1

            for successor in self.graph.successors(current_node):
                edge_weight = self.graph.edges[current_node, successor]["weight"]
                if edge_weight > max_edge_weight and self.longest_path_lengths[successor] == self.longest_path_lengths[current_node] + edge_weight:
                    max_edge_weight = edge_weight
                    next_node = successor

            current_node = next_node

        return path[::-1]  # 反转得到正确的路径顺序

    def get_critical_path_duration(self) -> int:
        """获取关键路径的总持续时间"""
        return max(self.longest_path_lengths.values()) if self.longest_path_lengths else 0
    def add_node(self, node: int):
        """添加新节点到图中"""
        if node not in self.graph.nodes:
            self.graph.add_node(node)
            self.node_weights[node] = 0
            self.longest_path_lengths[node] = 0
            # 重新计算拓扑排序和最长路径
            self._reinitialize()

    def add_edge(self, u: int, v: int, weight: int):
        """添加新边到图中"""
        if not self.graph.has_edge(u, v):
            self.graph.add_edge(u, v, weight=weight)
            self.edge_weights[(u, v)] = weight
            # 重新计算拓扑排序和最长路径
            self._reinitialize()

    def remove_node(self, node: int):
        """从图中删除节点"""
        if node in self.graph.nodes:
            self.graph.remove_node(node)
            del self.node_weights[node]
            del self.longest_path_lengths[node]
            # 重新计算拓扑排序和最长路径
            self._reinitialize()

    def remove_edge(self, u: int, v: int):
        """从图中删除边"""
        if self.graph.has_edge(u, v):
            self.graph.remove_edge(u, v)
            del self.edge_weights[(u, v)]
            # 重新计算拓扑排序和最长路径
            self._reinitialize()

    def _reinitialize(self):
        """重新初始化分析器状态"""
        self.topological_order = list(nx.topological_sort(self.graph))
        self.longest_path_lengths = {node: 0 for node in self.graph.nodes}
        self.initialize_longest_paths()


# 使用示例
cp_graph, success = CriticalPathAnalysis.critical_path_analysis(t, rank=0, annotation="ProfilerStep", instance_id=0)
if success:
    analyzer = IncrementalCriticalPathAnalyzer(cp_graph)
    analyzer.initialize_longest_paths()

    # 模拟边权重变化
    u, v = list(cp_graph.edges)[0]  # 假设修改第一条边
    new_weight = cp_graph.edges[u, v]["weight"] * 0.8  # 减少20%
    analyzer.update_edge_weight(u, v, int(new_weight))

    new_critical_path = analyzer.get_critical_path()
    new_duration = analyzer.get_critical_path_duration()

    print(f"Original critical path duration: {max(analyzer.longest_path_lengths.values())} ns")
    print(f"New critical path duration: {new_duration} ns")
    print("New critical path nodes:", new_critical_path)