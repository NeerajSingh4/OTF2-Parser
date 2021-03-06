import otf2
import numpy as np
import pandas as pd
import gc
from otf2.events import *


def get_metric_events(trace_name):
    with otf2.reader.open(trace_name, 5000) as trace:
        metric_events = []
        for metric_members in trace.definitions.metric_members:
            metric_events.append(metric_members.name)
    # gc.collect()
    return metric_events

def get_mpi_init_end_time(trace_name):
    with otf2.reader.open(trace_name, 5000) as trace:
        time_list = []
        for location, event in trace.events:
            if isinstance(event, Leave):
                if(event.region.name == "MPI_Init"):
                    time_list.append(event.time)
    time_mpi_init = max(time_list)
    # gc.collect()
    return time_mpi_init

def get_count_events(papi_events, trace_name):
    count_papi_events = np.zeros(len(papi_events))
    with otf2.reader.open(trace_name, 5000) as trace:
        global_offset = trace.definitions.clock_properties.global_offset
        resolution = trace.timer_resolution
        for location, event in trace.events:
            for i in range(0, len(papi_events)):
                if isinstance(event, Metric):
                    if(event.metric.metric_class.members[0].name == papi_events[i]):
                        count_papi_events[i] += 1
    return count_papi_events, global_offset, resolution

def get_papi_values(papi_events,count_papi_events, trace_name, num_threads):
    value_list = np.zeros((len(papi_events), int(num_threads)))
    count_list = np.zeros(len(papi_events), dtype = np.int64)
    papi_values = np.zeros(len(papi_events), dtype = np.float32)
    counter = np.zeros(len(papi_events), dtype = np.int64)
    time_list = []
    with otf2.reader.open(trace_name, 5000) as trace:
        for location, event in trace.events:
            for i in range(0, len(papi_events)):
                if isinstance(event, Metric):
                    if(event.metric.metric_class.members[0].name == papi_events[i]):
                        counter[i] += 1
                        time_list.append(event.time)
                        # print('Counter Value: {0}'.format(counter[i]), end="")
                        if(counter[i] > int(count_papi_events[i]) - int(num_threads)):
                            value_list[i][count_list[i]] = event.values[0]
                            count_list[i] += 1
                            # print(value_list)
                            # print(count_list)
            # gc.collect()
    print(value_list)
    print(count_list)
    # print(count)
    papi_values = np.mean(value_list, axis = 1)
    # papi_values[0] /= 770
    # print(papi_values)
    return papi_values,time_list

def read_trace(trace_name, num_threads, name):
    metric_events = get_metric_events(trace_name)
    print(metric_events)
    papi_events = [i for i in metric_events if "APAPI" in i]
    # print(papi_events)
    other_events = [i for i in metric_events if i not in papi_events]
    # other_events = [i for i in metric_events if "hdeem" in i]
    print(other_events)
    count_papi_events, global_offset, resolution = get_count_events(papi_events, trace_name)
    # count_papi_events = [ 41205,41205,41205,41205,41205]
    # print(count_papi_events)
    # print(get_papi_events)
    # print(other_events)
    # value_list = []
    papi_values, time_list = get_papi_values(papi_events, count_papi_events, trace_name, num_threads)
    # print(papi_values)
    # time_mpi_init = get_mpi_init_end_time(trace_name)
    # time_list = []
    metric_values = np.zeros(len(other_events))
    metric_events_counts = np.zeros(len(other_events))
    with otf2.reader.open(trace_name, 5000) as trace:
        global_offset = trace.definitions.clock_properties.global_offset
        resolution = trace.timer_resolution
        for location, event in trace.events:
            if isinstance(event, Metric):
                for i in range(0, len(other_events)):
                    if(event.metric.metric_class.members[0].name == other_events[i]):
                            # print(event.metric.scope.group.name)
                            # value_list.append(event.values[0])
                            # print(event)
                            # print(location)
                            # time_list.append(event.time)
                            metric_values[i] += event.values[0]
                            metric_events_counts[i] += 1
            # gc.collect()
    for i in range(0, len(other_events)):
        metric_values[i] /= metric_events_counts[i]
    # with otf2.reader.open(trace_name) as trace:
    #     for location, event in trace.events:
    #         for i in range(0, len(other_events) + len(papi_events)):
    #             if isinstance(event, Metric):

    # # print(value_list)
    # # metric_values[0] /= metric_events_counts[0]
    # print(metric_values)
    # print(papi_values)
    print(metric_values)
    time_list.sort(key=int)
    time_end = time_list[len(time_list) -1]
    time_start = time_list[0]
    time_end = (time_end - global_offset)/resolution
    time_start = (time_start - global_offset)/resolution
    # print(time_end)
    # print(time_start)
    time = time_end - time_start
    convert_2_csv(papi_events,other_events, papi_values, metric_values,name, time)
    # convert_2_csv(other_events, metric_values, name, time)

def convert_2_csv(papi_events, other_events, papi_values, metric_values, name, time):
    data = list(papi_values) + list(metric_values)
    print(data)
    columns = []
    for i in range(0, len(papi_events)):
        columns.append(papi_events[i])
    for i in range(0, len(other_events)):
        columns.append((other_events[i]))
    # print(columns)
    # print(columns.shape)
    data_dict = {columns[i]:data[i] for i in range(0, len(data))}
    data_dict.update({'time':time})
    print(data_dict)

    df = pd.DataFrame(data = data_dict, index = [0])
    df.to_csv(name + ".csv", sep='\t', header=True)
    # df = pd.DataFrame(data, columns=columns)
    # print(df)

# def convert_2_csv(other_events, metric_values, name, time):
#     # data = list(papi_values) + list(metric_values)
#     data = list(metric_values)
#     print(data)
#     columns = []
#     # for i in range(0, len(papi_events)):
#         # columns.append(papi_events[i])
#     for i in range(0, len(other_events)):
#         columns.append((other_events[i]))
#     # print(columns)
#     # print(columns.shape)
#     data_dict = {columns[i]:data[i] for i in range(0, len(data))}
#     data_dict.update({'time':time})
#     print(data_dict)

#     df = pd.DataFrame(data = data_dict, index = [0])
#     df.to_csv(name + ".csv", sep='\t', header=True)



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description = 'This script parsers the metrics from an OTF2 trace file and converts it to a csv')
    parser.add_argument("-i","--input", help="Trace file with path", required=True)
    parser.add_argument("-t", "--num_threads", help="Number of threads for MPI program", required=True)
    parser.add_argument("-n", "--name", help="Name of the output csv file", required=True)
    args = parser.parse_args()
    read_trace(args.input, args.num_threads, args.name)









