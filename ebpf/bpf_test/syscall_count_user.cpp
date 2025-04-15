// syscall_count_user.cpp
#include <bpf/libbpf.h>
#include <iostream>
#include <string>
#include <unistd.h>

const std::string file_name = "syscall_count_kern.o";

int main() {
    // 打开文件为 obj
    bpf_object *obj = bpf_object__open_file(file_name.c_str(), nullptr);
    if (libbpf_get_error(obj)) {
        std::cout << "open file error:" << strerror(errno) << std::endl;
        return 0;
    }
    // 解析elf查找其中的 program
    bpf_program *prog = bpf_object__find_program_by_name(obj, "trace_enter_open");
    if (!prog) {
        std::cout << "not find the program" << std::endl;
        return 0;
    }
    // 加载
    if (bpf_object__load(obj)) {
        std::cout << "load object error: " << strerror(errno) << std::endl;
        return 0;
    }
    // 建立 map
    bpf_map *map = bpf_object__find_map_by_name(obj, "data");
    if (map < 0) {
        std::cout << "finding map error: " << strerror(errno) << std::endl;
        return 0;
    }
    // attach
    bpf_link *link = bpf_program__attach(prog);
    if (libbpf_get_error(link)) {
        std::cout << "attach failed: " << strerror(errno) << std::endl;
        return 0;
    }
    while (true) {
        __u32 key = 0;
        __u32 val = 0;
        // 等待统计数据
        sleep(5);
        // 读取
        if (bpf_map__lookup_elem(map, &key, sizeof(key), &val, sizeof(val), 0) != 0) {
            std::cout << "loopup error: " << strerror(errno) << std::endl;
        }
        std::cout << "syscall count: " << val << std::endl;
        // 写入
        val = 0;
        if (bpf_map__update_elem(map, &key, sizeof(key), &val, sizeof(val), BPF_ANY) !=
            0) {
            std::cout << "update error: " << strerror(errno) << std::endl;
        }
    }
    return 0;
}