import inspect
from hta.trace_analysis import TraceAnalysis
from hta.analyzers.critical_path_analysis import restore_cpgraph


test = 1

hta_dir = "/home/hwt/HolisticTraceAnalysis"
trace_dir = hta_dir + "/tests/data/critical_path/simple_add/"

analyzer = TraceAnalysis(trace_dir = trace_dir)
annotation = "[param|pytorch.model.alex_net|0|0|0|measure|forward]"
instance_id = 1  # note this is zero based

cp_graph, success = analyzer.critical_path_analysis(
        rank = 0, annotation=annotation, instance_id=instance_id)

if test == 1:
    print(success)
    print(cp_graph.summary())
    print("xxxxxxxxxxxxxxxx")
    # print(cp_graph.get_critical_path_breakdown())


    zip_file = cp_graph.save(out_dir="/tmp/my_saved_cp_graph")

    rest_graph = restore_cpgraph(zip_filename=zip_file, t_full=analyzer.t, rank=0)

    print(len(rest_graph.critical_path_edges_set) == len(cp_graph.critical_path_edges_set))
    print(len(rest_graph.nodes) == len(cp_graph.nodes))
    # analyzer.overlay_critical_path_analysis(
    #     0, cp_graph, output_dir='~/HolisticTraceAnalysis/tests/data/critical_path/simple_add/overlaid')

    print(rest_graph.summary())
    # recompute critical path
    rest_graph.critical_path()
    print(rest_graph.summary())


