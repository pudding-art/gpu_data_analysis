class AdvancedCriticalPathAnalyzer(CriticalPathAnalyzer):
    r"""
    未考虑操作类型：不同类型的节点（如计算密集型、通信密集型、I/O 操作）对性能优化的潜力不同。例如，通信瓶颈可能需要从算法层面优化，而计算瓶颈可能需要硬件加速。
    未考虑依赖关系：关键路径上的节点存在依赖关系，某些节点的优化可能会影响后续节点的执行时间。
    未考虑敏感性：未反映节点执行时间变化对整体关键路径的敏感性。某些节点的小幅优化可能显著缩短关键路径。


    (1) 时间贡献（Time Contribution）
    这是基础指标，表示节点执行时间占关键路径总时长的比例：
    Time Contribution=  Critical Path Total Duration / Node Duration
    ​
    
    (2) 性能敏感性（Performance Sensitivity）
    衡量节点执行时间变化对关键路径总时长的影响。可以通过模拟小幅改变节点权重来计算敏感性：
    Sensitivity= ΔNode Duration / ΔCritical Path Duration
    ​
    (3) 操作类型（Operation Type）
    结合节点的操作类型（如 CPU-bound、GPU-bound、通信等），不同类型的优化策略不同。

    (4) 优化潜力（Optimization Potential）
    基于操作类型和硬件限制，评估每个节点的最大优化潜力。例如：
    GPU计算节点：受计算能力和内存带宽限制
    通信节点：受网络带宽和延迟限制
    """
    def __init__(self, cp_graph: CPGraph):
        super().__init__(cp_graph)
        self.performance_sensitivity = {}

    def compute_sensitivity(self, perturbation=0.01):
        """计算每个节点的性能敏感性"""
        original_duration = self.get_critical_path_duration()
        self.performance_sensitivity = {}

        for edge in self.cp_graph.critical_path_edges_set:
            u, v = edge.begin, edge.end
            original_weight = self.cp_graph.edges[u, v]["weight"]
            
            # 小幅改变权重
            new_weight = int(original_weight * (1 + perturbation))
            self.cp_graph.edges[u, v]["weight"] = new_weight
            
            # 重新计算关键路径
            new_duration = self.cp_graph.critical_path()
            
            # 恢复原权重
            self.cp_graph.edges[u, v]["weight"] = original_weight
            
            # 计算敏感性
            self.performance_sensitivity[edge] = (new_duration - original_duration) / (new_weight - original_weight)
        
        return self.performance_sensitivity

    def analyze_node_impact(self) -> pd.DataFrame:
        """扩展分析方法，包含敏感性和操作类型"""
        df = super().analyze_node_impact()
        
        # 添加敏感性
        df["sensitivity"] = df["event_idx"].map(
            lambda idx: self.performance_sensitivity.get(idx, 0)
        )
        
        # 添加操作类型和优化潜力
        df["operation_type"] = df["event_name"].map(self._infer_operation_type)
        df["optimization_potential"] = df.apply(self._estimate_optimization_potential, axis=1)
        
        return df

    def _infer_operation_type(self, event_name: str) -> str:
        """根据事件名称推断操作类型"""
        if "memcpy" in event_name.lower() or "data transfer" in event_name.lower():
            return "Data Transfer"
        elif "kernel" in event_name.lower() or "compute" in event_name.lower():
            return "Compute"
        elif "cpu" in event_name.lower():
            return "CPU Operation"
        else:
            return "Other"

    def _estimate_optimization_potential(self, row: pd.Series) -> float:
        """估计节点的优化潜力"""
        if row["operation_type"] == "Compute":
            # GPU计算节点优化潜力较高
            return 0.4  # 假设可优化40%
        elif row["operation_type"] == "Data Transfer":
            # 通信节点优化潜力中等
            return 0.25  # 假设可优化25%
        else:
            # 其他类型节点优化潜力较低
            return 0.1  # 假设可优化10%

# 使用示例
cp_graph, success = CriticalPathAnalysis.critical_path_analysis(t, rank=0, annotation="ProfilerStep", instance_id=0)
if success:
    analyzer = AdvancedCriticalPathAnalyzer(cp_graph)
    analyzer.compute_sensitivity()
    advanced_impact_df = analyzer.analyze_node_impact()
    
    print("Advanced Node Impact Analysis:")
    print(advanced_impact_df[["event_name", "duration", "contribution", "sensitivity", "operation_type", "optimization_potential"]])



"""
性能敏感性（Performance Sensitivity）
衡量节点执行时间变化对关键路径总时长的影响：
Sensitivity= 
ΔNode Duration
ΔCritical Path Duration
​
 
敏感性高的节点优化效果更显著。
资源瓶颈（Resource Bottlenecks）
识别关键路径上的主要资源瓶颈类型（如计算、内存、同步等）。
帮助确定优化方向，例如：
计算瓶颈：可能需要优化算法或使用更高效的计算资源。
内存瓶颈：可能需要优化数据传输或使用更快的存储设备。
同步瓶颈：可能需要减少不必要的同步操作。
优化优先级（Optimization Priority）
综合考虑时间贡献和敏感性，计算每个节点的优化优先级：
Optimization Priority=Time Contribution×Sensitivity
优先级高的节点应优先优化。
累积贡献（Cumulative Contribution）
显示关键路径上节点的累积时间贡献，帮助理解整体性能构成。

"""
import pandas as pd
import networkx as nx
import time
from typing import Dict, List, Tuple, Optional

class AdvancedCriticalPathAnalyzer(CriticalPathAnalyzer):
    def __init__(self, cp_graph: CPGraph):
        super().__init__(cp_graph)
        self.performance_sensitivity: Dict[Tuple[int, int], float] = {}
        self.resource_bottlenecks: Dict[str, List[Tuple[int, int]]] = defaultdict(list)

    def compute_sensitivity(self, perturbation: float = 0.01) -> Dict[Tuple[int, int], float]:
        """计算每个边的性能敏感性"""
        original_duration = self.get_critical_path_duration()
        self.performance_sensitivity = {}

        for u, v in self.cp_graph.critical_path_edges_set:
            original_weight = self.cp_graph.edges[u, v]["weight"]
            
            # 小幅改变权重
            new_weight = int(original_weight * (1 + perturbation))
            self.cp_graph.edges[u, v]["weight"] = new_weight
            
            # 重新计算关键路径
            new_duration = self.cp_graph.critical_path()
            
            # 恢复原权重
            self.cp_graph.edges[u, v]["weight"] = original_weight
            
            # 计算敏感性
            self.performance_sensitivity[(u, v)] = (new_duration - original_duration) / (new_weight - original_weight)
        
        return self.performance_sensitivity

    def identify_resource_bottlenecks(self) -> Dict[str, List[Tuple[int, int]]]:
        """识别资源瓶颈"""
        self.resource_bottlenecks = defaultdict(list)

        for edge in self.cp_graph.critical_path_edges_set:
            event_idx = self.cp_graph.get_event_attribution_for_edge(edge)
            event_name = self.cp_graph._get_node_name(event_idx) if event_idx != -1 else "Unknown"
            
            if "compute" in event_name.lower():
                self.resource_bottlenecks["Compute"].append((edge.begin, edge.end))
            elif "memcpy" in event_name.lower() or "data transfer" in event_name.lower():
                self.resource_bottlenecks["Memory"].append((edge.begin, edge.end))
            elif "sync" in event_name.lower():
                self.resource_bottlenecks["Synchronization"].append((edge.begin, edge.end))
            else:
                self.resource_bottlenecks["Other"].append((edge.begin, edge.end))
        
        return self.resource_bottlenecks

    def analyze_node_impact(self) -> pd.DataFrame:
        """全面分析节点影响"""
        if not hasattr(self.cp_graph, 'critical_path_edges_set') or not self.cp_graph.critical_path_edges_set:
            raise ValueError("Critical path has not been computed yet.")

        total_duration = sum(edge.weight for edge in self.cp_graph.critical_path_edges_set)
        if total_duration == 0:
            raise ValueError("Total critical path duration is zero.")

        # 获取关键路径的边及其属性
        critical_edges = []
        for edge in self.cp_graph.critical_path_edges_set:
            start_node = self.cp_graph.node_list[edge.begin]
            end_node = self.cp_graph.node_list[edge.end]
            event_idx = self.cp_graph.get_event_attribution_for_edge(edge)
            event_name = self.cp_graph._get_node_name(event_idx) if event_idx != -1 else "Unknown"

            sensitivity = self.performance_sensitivity.get((edge.begin, edge.end), 0)
            bottleneck_type = None
            for bt, edges in self.resource_bottlenecks.items():
                if (edge.begin, edge.end) in edges:
                    bottleneck_type = bt
                    break

            critical_edges.append({
                "event_idx": event_idx,
                "event_name": event_name,
                "start_ts": start_node.ts,
                "end_ts": end_node.ts,
                "duration": edge.weight,
                "type": edge.type.value,
                "contribution": edge.weight / total_duration * 100,
                "sensitivity": sensitivity,
                "bottleneck_type": bottleneck_type,
                "bound_by": bound_by({"type": edge.type.value, "s_name": event_name, "stream": start_node.ev_idx})
            })

        # 创建DataFrame
        df = pd.DataFrame(critical_edges)
        df = df.sort_values(by="start_ts").reset_index(drop=True)

        # 添加累积贡献和优化优先级
        df["cumulative_contribution"] = df["contribution"].cumsum()
        df["optimization_priority"] = df["contribution"] * df["sensitivity"]

        return df

    def summarize_impact_by_category(self, df: pd.DataFrame) -> pd.DataFrame:
        """按类别汇总关键路径贡献"""
        summary = df.groupby("bottleneck_type").agg(
            total_duration=("duration", "sum"),
            max_duration=("duration", "max"),
            avg_duration=("duration", "mean"),
            count=("duration", "count"),
            max_contribution=("contribution", "max"),
            avg_contribution=("contribution", "mean"),
            total_contribution=("contribution", "sum"),
            avg_sensitivity=("sensitivity", "mean"),
            total_optimization_priority=("optimization_priority", "sum")
        ).reset_index()

        summary["total_contribution"] = summary["total_contribution"].round(2)
        summary["total_optimization_priority"] = summary["total_optimization_priority"].round(2)
        return summary.sort_values(by="total_optimization_priority", ascending=False)

# 使用示例
cp_graph, success = CriticalPathAnalysis.critical_path_analysis(t, rank=0, annotation="ProfilerStep", instance_id=0)
if success:
    analyzer = AdvancedCriticalPathAnalyzer(cp_graph)
    
    # 计算敏感性和资源瓶颈
    analyzer.compute_sensitivity()
    analyzer.identify_resource_bottlenecks()
    
    # 获取详细分析结果
    detailed_df = analyzer.analyze_node_impact()
    print("Detailed Node Impact Analysis:")
    print(detailed_df[["event_name", "duration", "contribution", "sensitivity", "bottleneck_type", "optimization_priority"]])

    # 获取按类别汇总的结果
    summary_df = analyzer.summarize_impact_by_category(detailed_df)
    print("\nSummary by Bottleneck Category:")
    print(summary_df)