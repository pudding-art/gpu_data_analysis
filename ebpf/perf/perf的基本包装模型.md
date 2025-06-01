perf的基本包装模型

每个event分配一个对应的perf_event结构，所有对event的操作都是围绕 perf_event来展开的。

- 通过perf_event_open系统调用分配到perf_event之后，会返回一个文件句柄(用户态使用)fd，这样这个perf_event结构可以通过read/write/ioctl/mmap通用文件接口来操作；
-  perf_event提供两种类型的trace数据：count和sample. count只是记录了event发生的次数， sample记录了大量的信息（如IP, ADDR, TID, TIME, CPU ,BT)。如果要使用sample功能，需要给perf_event分配ringbuffer空间，并且将这部分空间通过mmap映射到用户空间。这和定位问题时从粗到细的思路是相符的，首先从counter的比例上找出问题热点出现在哪个模块，再使用详细记录抓取更多信息来进一步定位。
- perf的开销比ftrace大，因为它给每个event都独立一套数据结构perf_event， 对应独立的attr和pmu。在数据记录时的开销肯定大于ftrace，但是每个event的ringbuffer是独立的所以也不需要ftrace复杂的ringbuffer操作。perf也有比ftrace开销小的地方，它的sample数据存储的ringbuffer空间会通过mmap映射到到用户态，这样在读取数据的时候就会少一次拷贝。不过perf的设计初衷也不是让成百上千的event同时使用，只会挑出一些event重点debug
  





https://blog.csdn.net/pwl999/article/details/81200439

get_unused_fd_flags:https://blog.csdn.net/lickylin/article/details/100864176

https://blog.csdn.net/qq_38089448/article/details/140603355?spm=1001.2101.3001.6650.2&utm_medium=distribute.pc_relevant.none-task-blog-2%7Edefault%7EYuanLiJiHua%7EPosition-2-140603355-blog-100864176.235%5Ev43%5Epc_blog_bottom_relevance_base5&depth_1-utm_source=distribute.pc_relevant.none-task-blog-2%7Edefault%7EYuanLiJiHua%7EPosition-2-140603355-blog-100864176.235%5Ev43%5Epc_blog_bottom_relevance_base5&utm_relevant_index=5

htmm.h

```c
#define BUFFER_SIZE	512 /* 1MB */
#define CPUS_PER_SOCKET 48


/* pebs events */
//#define DRAM_LLC_LOAD_MISS  0x1d3
//#define NVM_LLC_LOAD_MISS   0x80d1
//#define ALL_STORES	    0x82d0
//#define ALL_LOADS	    0x81d0
//#define STLB_MISS_STORES    0x12d0
//#define STLB_MISS_LOADS	    0x11d0

// read & write bandwidth estimation
#define UNC_CXLCM_TxC_PACK_BUF_INSERTS_MEM_DATA 0x1002 //cxlcm 0-3 Number of Allocation to Mem Data Packing buffer
#define UNC_CXLCM_TxC_PACK_BUF_INSERTS_MEM_REQ 0x0802 //cxlcm 0-3 Number of Allocation to Mem Rxx Packing buffer
#define UNC_CXLCM_RxC_PACK_BUF_INSERTS_MEM_DATA 0x1041 //cxlcm 4-7 Number of Allocation to Mem Data Packing buffer
#define UNC_CXLCM_RxC_PACK_BUF_INSERTS_MEM_REQ 0x0841 //cxlcm 4-7 Number of Allocation to Mem Rxx Packing buffer

// latency estimation
#define UNC_CXLCM_RxC_PACK_BUF_FULL_MEM_DATA 0x1052 //cxlcm 4-7 Number of cycles the Packing Buffer is Full
#define UNC_CXLCM_RxC_PACK_BUF_FULL_MEM_REQ 0x0852 //cxlcm 4-7 Number of cycles the Packing Buffer is Full


// AFG related
#define UNC_CXLDP_TxC_AGF_INSERTS_M2S_DATA 0x2002 //cxldp
#define UNC_CXLDP_TxC_AGF_INSERTS_M2S_REQ 0x1002 //cxldp
#define UNC_CXLCM_RxC_AGF_INSERTS_MEM_DATA 0x2043 //cxlcm
#define UNC_CXLCM_RxC_AGF_INSERTS_MEM_REQ 0x1043 //cxlcm

// flits related
#define UNC_CXLCM_TxC_FLITS_NO_HDR 0x0805
#define UNC_CXLCM_TxC_FLITS_CTRL 0x0405
#define UNC_CXLCM_TxC_FLITS_PROT 0x0205
#define UNC_CXLCM_TxC_FLITS_VALID 0x0105

// PACK_BUF_NE
#define UNC_CXLCM_RxC_PACK_BUF_NE_MEM_DATA 0x1042
#define UNC_CXLCM_RxC_PACK_BUF_NE_MEM_REQ 0xs0842


struct  htmm_event {
    struct perf_event_header header;
    __u64 ip;
    __u32 pid, tid;
    __u64 addr;
  	// new added
    struct read_format v;
    __u32 size;
    char data[size]; //char * data;
};


enum events {
    TX_MEM_DATA = 0,
    TX_MEM_REQ = 1,
    RX_MEM_DATA = 2,
    RX_MEM_REQ = 3,
    RX_BUF_FULL_MEM_DATA = 4,
  	RX_BUF_FULL_MEM_REQ = 5,
    N_HTMMEVENTS
};




extern int ksamplingd_init(pid_t pid, int node);
extern void ksamplingd_exit(void);

```



```c
#ifndef CONFIG_HTMM
SYSCALL_DEFINE2(htmm_start,
		pid_t, pid, int, node)
{
    return 0;
}

SYSCALL_DEFINE1(htmm_end,
		pid_t, pid)
{
    return 0;
}

#else
SYSCALL_DEFINE2(htmm_start,
		pid_t, pid, int, node)
{
    ksamplingd_init(pid, node);
    return 0;
}

SYSCALL_DEFINE1(htmm_end,
		pid_t, pid)
{
    ksamplingd_exit();
    return 0;
}

/* allocates perf_buffer instead of calling perf_mmap() */
//这个函数的目的是为性能事件设置一个内存缓冲区，用于收集性能数据。通过使用环形缓冲区，事件可以持续收集数据而不会因为缓冲区满而停止。
int htmm__perf_event_init(struct perf_event *event, unsigned long nr_pages)
{
    struct perf_buffer *rb = NULL;
    int ret = 0, flags = 0;

    if (event->cpu == -1 && event->attr.inherit)
			return -EINVAL;

    ret = security_perf_event_read(event);
    if (ret)
			return ret;

    if (nr_pages != 0 && !is_power_of_2(nr_pages))
			return -EINVAL;

    WARN_ON_ONCE(event->ctx->parent_ctx);
    mutex_lock(&event->mmap_mutex);

    WARN_ON(event->rb);

    rb = rb_alloc(nr_pages,
	    event->attr.watermark ? event->attr.wakeup_watermark : 0,
	    event->cpu, flags);
    if (!rb) {
      ret = -ENOMEM;
      goto unlock;
    }

    ring_buffer_attach(event, rb);
    perf_event_init_userpage(event);
    perf_event_update_userpage(event);

unlock:
    if (!ret) {
			atomic_inc(&event->mmap_count);
    }
    mutex_unlock(&event->mmap_mutex);
    return ret;
  
  
/* sys_perf_event_open for htmm use */
int htmm__perf_event_open(struct perf_event_attr *attr_ptr, pid_t pid,
	int cpu, int group_fd, unsigned long flags)
{
 	struct perf_event *group_leader = NULL, *output_event = NULL;
	struct perf_event *event, *sibling;
	struct perf_event_attr attr;
	struct perf_event_context *ctx, *gctx;
	struct file *event_file = NULL;
	struct fd group = {NULL, 0};
	struct task_struct *task = NULL;
	struct pmu *pmu;
	int event_fd;
	int move_group = 0;
	int err;
	int f_flags = O_RDWR;
	int cgroup_fd = -1;

	/* for future expandability... */
	if (flags & ~PERF_FLAG_ALL)
		return -EINVAL;

	/* Do we allow access to perf_event_open(2) ? */
	err = security_perf_event_open(&attr, PERF_SECURITY_OPEN);
	if (err)
		return err;

	/*err = perf_copy_attr(attr_ptr, &attr);
	if (err)
		return err;*/
	attr = *attr_ptr;

	if (!attr.exclude_kernel) {
		err = perf_allow_kernel(&attr);
		if (err)
			return err;
	}

	if (attr.namespaces) {
		if (!perfmon_capable())
			return -EACCES;
	}

	if (attr.freq) {
		if (attr.sample_freq > sysctl_perf_event_sample_rate)
			return -EINVAL;
	} else {
		if (attr.sample_period & (1ULL << 63))
			return -EINVAL;
	}

	/* Only privileged users can get physical addresses */
	if ((attr.sample_type & PERF_SAMPLE_PHYS_ADDR)) {
		err = perf_allow_kernel(&attr);
		if (err)
			return err;
	}

	/* REGS_INTR can leak data, lockdown must prevent this */
	if (attr.sample_type & PERF_SAMPLE_REGS_INTR) {
		err = security_locked_down(LOCKDOWN_PERF);
		if (err)
			return err;
	}

	/*
	 * In cgroup mode, the pid argument is used to pass the fd
	 * opened to the cgroup directory in cgroupfs. The cpu argument
	 * designates the cpu on which to monitor threads from that
	 * cgroup.
	 */
	if ((flags & PERF_FLAG_PID_CGROUP) && (pid == -1 || cpu == -1))
		return -EINVAL;

	if (flags & PERF_FLAG_FD_CLOEXEC)
		f_flags |= O_CLOEXEC;

  /* 当前进程获取一个新的fd编号 */
	event_fd = get_unused_fd_flags(f_flags);
	if (event_fd < 0)
		return event_fd;

	if (group_fd != -1) {
		err = perf_fget_light(group_fd, &group);
		if (err)
			goto err_fd;
		group_leader = group.file->private_data;
		if (flags & PERF_FLAG_FD_OUTPUT)
			output_event = group_leader;
		if (flags & PERF_FLAG_FD_NO_GROUP)
			group_leader = NULL;
	}

	if (pid != -1 && !(flags & PERF_FLAG_PID_CGROUP)) {
		task = find_lively_task_by_vpid(pid);
		if (IS_ERR(task)) {
			err = PTR_ERR(task);
			goto err_group_fd;
		}
	}

	if (task && group_leader &&
	    group_leader->attr.inherit != attr.inherit) {
		err = -EINVAL;
		goto err_task;
	}

	if (flags & PERF_FLAG_PID_CGROUP)
		cgroup_fd = pid;

  /* 根据传入的参数，分配perf_event结构并初始化 */
	event = perf_event_alloc(&attr, cpu, task, group_leader, NULL,
				 NULL, NULL, cgroup_fd);
	if (IS_ERR(event)) {
		err = PTR_ERR(event);
		goto err_task;
	}

	if (is_sampling_event(event)) {
		if (event->pmu->capabilities & PERF_PMU_CAP_NO_INTERRUPT) {
			err = -EOPNOTSUPP;
			goto err_alloc;
		}
	}

	/*
	 * Special case software events and allow them to be part of
	 * any hardware group.
	 */
	pmu = event->pmu;

	if (attr.use_clockid) {
		err = perf_event_set_clock(event, attr.clockid);
		if (err)
			goto err_alloc;
	}

	if (pmu->task_ctx_nr == perf_sw_context)
		event->event_caps |= PERF_EV_CAP_SOFTWARE;

  /*如果是sw event加入到hw event group中，完全可以；
  但如果是hw event加入到sw event group中，需要将所有的sw event group全都更换到新的hw event group的上下文环境中*/
	if (group_leader) {
		if (is_software_event(event) &&
		    !in_software_context(group_leader)) {
			/*
			 * If the event is a sw event, but the group_leader
			 * is on hw context.
			 *
			 * Allow the addition of software events to hw
			 * groups, this is safe because software events
			 * never fail to schedule.
			 */
			pmu = group_leader->ctx->pmu;
		} else if (!is_software_event(event) &&
			   is_software_event(group_leader) &&
			   (group_leader->group_caps & PERF_EV_CAP_SOFTWARE)) {
			/*
			 * In case the group is a pure software group, and we
			 * try to add a hardware event, move the whole group to
			 * the hardware context.
			 */
			move_group = 1;
		}
	}

	/*
	 * Get the target context (task or percpu):
	 get到perf_event_context，根据perf_event类型得到cpu维度/task维度的context：
        如果pid=-1即task=NULL，获得cpu维度的context，即pmu注册时根据pmu->task_ctx_nr分配的pmu->pmu_cpu_context->ctx
        如果pid>=0即task!=NULL，获得task维度的context，即task->perf_event_ctxp[ctxn]，如果为空则重新创建
	 */
	ctx = find_get_context(pmu, task, event);
	if (IS_ERR(ctx)) {
		err = PTR_ERR(ctx);
		goto err_alloc;
	}

	/*
	 * Look up the group leader (we will attach this event to it):
	 event 需要加入到group leader中进行的一些合法性判断
	 */
	if (group_leader) {
		err = -EINVAL;

		/*
		 * Do not allow a recursive hierarchy (this new sibling
		 * becoming part of another group-sibling): 不允许递归的->group_leader
		 */
		if (group_leader->group_leader != group_leader)
			goto err_context;

		/* All events in a group should have the same clock 需要时钟源一致*/
		if (group_leader->clock != event->clock)
			goto err_context;

		/*
		 * Make sure we're both events for the same CPU;
		 * grouping events for different CPUs is broken; since
		 * you can never concurrently schedule them anyhow.
		 */
		if (group_leader->cpu != event->cpu)
			goto err_context;

		/*
		 * Make sure we're both on the same task, or both
		 * per-CPU events.
		 */
		if (group_leader->ctx->task != ctx->task)
			goto err_context;

		/*
		 * Do not allow to attach to a group in a different task
		 * or CPU context. If we're moving SW events, we'll fix
		 * this up later, so allow that.
		 */
		if (!move_group && group_leader->ctx != ctx)
			goto err_context;

		/*
		 * Only a group leader can be exclusive or pinned
		 */
		if (attr.exclusive || attr.pinned)
			goto err_context;
	}

	if (output_event) {
		err = perf_event_set_output(event, output_event);
		if (err)
			goto err_context;
	}

   /* 分配perf_event对应的file结构 
    * file->private_data = event; //file和event结构链接在一起
    * file->f_op = perf_fops; // file的文件操作函数集
    * 后续会将fd和file链接到一起:fd_install(event_fd, event_file)
   */
	event_file = anon_inode_getfile("[perf_event]", &perf_fops, event,
					f_flags);
	if (IS_ERR(event_file)) {
		err = PTR_ERR(event_file);
		event_file = NULL;
		goto err_context;
	}

	if (task) {
		err = down_read_interruptible(&task->signal->exec_update_lock);//	Reader获取rwsem锁的接口，如果不成功，进入S状态
		if (err)
			goto err_file;

		/*
		 * We must hold exec_update_lock across this and any potential
		 * perf_install_in_context() call for this new event to
		 * serialize against exec() altering our credentials (and the
		 * perf_event_exit_task() that could imply).
		 */
		err = -EACCES;
		if (!perf_check_permission(&attr, task))
			goto err_cred;
	}

	if (move_group) {
		gctx = __perf_event_ctx_lock_double(group_leader, ctx);

		if (gctx->task == TASK_TOMBSTONE) {
			err = -ESRCH;
			goto err_locked;
		}

		/*
		 * Check if we raced against another sys_perf_event_open() call
		 * moving the software group underneath us.
		 */
		if (!(group_leader->group_caps & PERF_EV_CAP_SOFTWARE)) {
			/*
			 * If someone moved the group out from under us, check
			 * if this new event wound up on the same ctx, if so
			 * its the regular !move_group case, otherwise fail.
			 */
			if (gctx != ctx) { /*如果 group_leader 与当前上下文 ctx 不匹配，说明事件组被移动到了不同的上下文中，这时返回 -EINVAL 错误*/
				err = -EINVAL;
				goto err_locked;
			} else {
				perf_event_ctx_unlock(group_leader, gctx);
				move_group = 0; /*如果上下文匹配，则释放锁，并设置 move_group 为 0，表示不需要移动组*/
			}
		}

		/*
		 * Failure to create exclusive events returns -EBUSY.
		 */
		err = -EBUSY;
    /*如果是排他性event：(pmu->capabilities & PERF_PMU_CAP_EXCLUSIVE) 
        检查context链表中现有的event是否允许新的event插入*/
		if (!exclusive_event_installable(group_leader, ctx)) //是否为独占事件？独占事件（Exclusive Events）是指那些在一个给定的上下文（context）中只能同时激活一个实例的性能事件。这种类型的事件通常用于测量特定类型的性能计数，而这个计数可能受到其他事件的影响，或者需要确保在测量期间没有其他事件干扰。
			goto err_locked;

		for_each_sibling_event(sibling, group_leader) {
			if (!exclusive_event_installable(sibling, ctx))
				goto err_locked;
		}
	} else {
		mutex_lock(&ctx->mutex);
	}

	if (ctx->task == TASK_TOMBSTONE) {
		err = -ESRCH;
		goto err_locked;
	}
  
  /* 根据attr计算：event->read_size, event->header_size, event->id_header_size并判断是否有超长*/
	if (!perf_event_validate_size(event)) {
		err = -E2BIG;
		goto err_locked;
	}

	if (!task) {
		/*
		 * Check if the @cpu we're creating an event for is online.
		 *
		 * We use the perf_cpu_context::ctx::mutex to serialize against
		 * the hotplug notifiers. See perf_event_{init,exit}_cpu().
		 */
		struct perf_cpu_context *cpuctx =
			container_of(ctx, struct perf_cpu_context, ctx);

		if (!cpuctx->online) {
			err = -ENODEV;
			goto err_locked;
		}
	}

	if (perf_need_aux_event(event) && !perf_get_aux_event(event, group_leader)) {
		err = -EINVAL;
		goto err_locked;
	}

	/*
	 * Must be under the same ctx::mutex as perf_install_in_context(),
	 * because we need to serialize with concurrent event creation.
	 */
	if (!exclusive_event_installable(event, ctx)) {
		err = -EBUSY;
		goto err_locked;
	}

	WARN_ON_ONCE(ctx->parent_ctx);

	/*
	 * This is the point on no return; we cannot fail hereafter. This is
	 * where we start modifying current state.
	 */
 //如果group和当前event的pmu type不一致，尝试更改context到当前的event
	if (move_group) {
		/*
		 * See perf_event_ctx_lock() for comments on the details
		 * of swizzling perf_event::ctx.
		 */
		perf_remove_from_context(group_leader, 0);//将group_leader从原有的context中remove
		put_ctx(gctx);

		for_each_sibling_event(sibling, group_leader) {//将所有group_leader的子event从原有context中remove
			perf_remove_from_context(sibling, 0);
			put_ctx(gctx);
		}

		/*
		 * Wait for everybody to stop referencing the events through
		 * the old lists, before installing it on new lists.
		 */
		synchronize_rcu();

		/*
		 * Install the group siblings before the group leader.
		 *
		 * Because a group leader will try and install the entire group
		 * (through the sibling list, which is still in-tact), we can
		 * end up with siblings installed in the wrong context.
		 *
		 * By installing siblings first we NO-OP because they're not
		 * reachable through the group lists.
		 */
    //将所有group_leader的子event安装到新的context中
		for_each_sibling_event(sibling, group_leader) {
			perf_event__state_init(sibling);
			perf_install_in_context(ctx, sibling, sibling->cpu);
			get_ctx(ctx);
		}

		/*
		 * Removing from the context ends up with disabled
		 * event. What we want here is event in the initial
		 * startup state, ready to be add into new context.
		 */
    //将group_leader安装到新的context中
		perf_event__state_init(group_leader);
		perf_install_in_context(ctx, group_leader, group_leader->cpu);
		get_ctx(ctx);
	}

	/*
	 * Precalculate sample_data sizes; do while holding ctx::mutex such
	 * that we're serialized against further additions and before
	 * perf_install_in_context() which is the point the event is active and
	 * can use these values.
	 */
  // 重新计算:event->read_size, event->header_size, event->id_header_size
	perf_event__header_size(event);
	perf_event__id_header_size(event);

	event->owner = current; //current是一个struct task_struct类型的指针，用来指向当前正在执行这段kernel代码的进程

	perf_install_in_context(ctx, event, event->cpu);//将event安装到context中
	perf_unpin_context(ctx);

	if (move_group)
		perf_event_ctx_unlock(group_leader, gctx);
	mutex_unlock(&ctx->mutex);

	if (task) {
		up_read(&task->signal->exec_update_lock);
		put_task_struct(task);
	}

  // 将当前进程创建的所有event, 加入到current->perf_event_list链表中
	mutex_lock(&current->perf_event_mutex);
	list_add_tail(&event->owner_entry, &current->perf_event_list);
	mutex_unlock(&current->perf_event_mutex);

	/*
	 * Drop the reference on the group_event after placing the
	 * new event on the sibling_list. This ensures destruction
	 * of the group leader will find the pointer to itself in
	 * perf_group_detach().
	 */
	fdput(group);
	fd_install(event_fd, event_file); //将fd和file进行链接
	return event_fd;

err_locked:
	if (move_group)
		perf_event_ctx_unlock(group_leader, gctx);
	mutex_unlock(&ctx->mutex);
err_cred:
	if (task)
		up_read(&task->signal->exec_update_lock);
err_file:
	fput(event_file);
err_context:
	perf_unpin_context(ctx);
	put_ctx(ctx);
err_alloc:
	/*
	 * If event_file is set, the fput() above will have called ->release()
	 * and that will take care of freeing the event.
	 */
	if (!event_file)
		free_event(event);
err_task:
	if (task)
		put_task_struct(task);
err_group_fd:
	fdput(group);
err_fd:
	put_unused_fd(event_fd);
	return err;
}
#endif

```

```c
static int
perf_event_set_output(struct perf_event *event, struct perf_event *output_event)
{
	struct perf_buffer *buffer = NULL, *old_buffer = NULL;
	int ret = -EINVAL;

  /* 如果没有指定输出事件，output_event为空，set操作*/
	if (!output_event)
		goto set;

	/* don't allow circular references */
  /* 防止出现循环引用*/
	if (event == output_event)
		goto out;

	/*
	 * Don't allow cross-cpu buffers 确保两个事件在同一个CPU上，不允许跨CPU的缓冲区重定向
	 */
	if (output_event->cpu != event->cpu)
		goto out;

	/*
	 * If its not a per-cpu buffer, it must be the same task.如果 output_event 不是每个CPU的缓冲区，则要求两个事件属于同一个任务上下文
	 */
	if (output_event->cpu == -1 && output_event->ctx != event->ctx)
		goto out;

set:
	mutex_lock(&event->mmap_mutex);
	/* Can't redirect output if we've got an active mmap() */
	if (atomic_read(&event->mmap_count))
		goto unlock;

	if (output_event) {
		/* get the buffer we want to redirect to */
		buffer = perf_buffer_get(output_event); //获得新的缓冲区
		if (!buffer)//如果为空解锁并推出
			goto unlock;
	}

	old_buffer = event->buffer;//保存旧的缓冲区
	rcu_assign_pointer(event->buffer, buffer); //更新缓冲区
	ret = 0;
unlock:
	mutex_unlock(&event->mmap_mutex);

	if (old_buffer) //如果存在旧的缓冲区，释放
		perf_buffer_put(old_buffer);
out:
	return ret;
}
```



```c
#include <linux/kthread.h>
#include <linux/memcontrol.h>
#include <linux/perf_event.h>

#include "../kernel/events/internal.h"

#include <linux/htmm.h>

struct task_struct *access_sampling = NULL;
struct perf_event ***mem_event;

static bool valid_va(unsigned long addr)
{
    if (!(addr >> (PGDIR_SHIFT + 9)) && addr != 0)
	return true;
    else
	return false;
}


// 获得当前监控的pebs事件类型
static __u64 get_pebs_event(enum events e)
{
    switch (e) {
	case DRAMREAD:
	    return DRAM_LLC_LOAD_MISS; //#define DRAM_LLC_LOAD_MISS  0x1d3
	case NVMREAD:
	    return NVM_LLC_LOAD_MISS; //#define NVM_LLC_LOAD_MISS   0x80d1
	case MEMWRITE:
	    return ALL_STORES;//#define ALL_STORES	    0x82d0
	default:
	    return N_HTMMEVENTS;
    }
}

static int __perf_event_open(__u64 config, __u64 config1, __u64 cpu,
	__u64 type, __u32 pid)
{
    struct perf_event_attr attr;
    struct file *file;
    int event_fd;
		// 配置perf_event_attr参数的内容
    memset(&attr, 0, sizeof(struct perf_event_attr));

    attr.type = PERF_TYPE_RAW;
    attr.size = sizeof(struct perf_event_attr);
    attr.config = config;
    attr.config1 = config1;
    attr.sample_period = 10007;
    attr.sample_type = PERF_SAMPLE_IP | PERF_SAMPLE_TID | PERF_SAMPLE_ADDR | PERF_SAMPLE_READ | PERF_SAMPLE_RAW ;//增加了最后两个字段
    attr.disabled = 0;
    attr.exclude_kernel = 0;
    attr.precise_ip = 1;

	//根据配置的perf_event_attr内容生成perf_event, file以及对应的fd
    event_fd = htmm__perf_event_open(&attr, pid, cpu, -1, 0);
    //event_fd = htmm__perf_event_open(&attr, -1, cpu, -1, 0);
    if (event_fd <= 0) {
	printk("[error htmm__perf_event_open failure] event_fd: %d\n", event_fd);
	return -1;
    }

    file = fget(event_fd);//根据文件描述符找到对应的struct file文件结构
    if (!file) {
	printk("invalid file\n");
	return -1;
    }
    mem_event[cpu][type] = fget(event_fd)->private_data; 
    return 0;
}

static int pebs_init(pid_t pid, int node)
{
    int cpu, event;

  //为mem_event分配实际内存空间
    mem_event = kzalloc(sizeof(struct perf_event **) * CPUS_PER_SOCKET, GFP_KERNEL);
    for (cpu = 0; cpu < CPUS_PER_SOCKET; cpu++) {
	mem_event[cpu] = kzalloc(sizeof(struct perf_event *) * N_HTMMEVENTS, GFP_KERNEL);
    }

    printk("pebs_init\n");  
  
    for (cpu = 0; cpu < CPUS_PER_SOCKET; cpu++) {
				for (event = 0; event < N_HTMMEVENTS; event++) {//N_HTMMEVNETS保存最后一个监控event的枚举变量值，正好可以作为边界
	    			if (get_pebs_event(event) == N_HTMMEVENTS) {//如果事件恰好是N_HTMMEVENTS，为空事件 
							mem_event[cpu][event] = NULL;
							continue;
	    			}
            if (__perf_event_open(DRAM_LLC_LOAD_MISS, 0, cpu, event, pid))
                return -1;
            if (htmm__perf_event_init(mem_event[cpu][event], BUFFER_SIZE)) //为每个事件分配ringbuffer
                return -1;
				}
    }

    return 0;
}

static void pebs_disable(void)
{
    int cpu, event;

    printk("pebs disable\n");
    for (cpu = 0; cpu < CPUS_PER_SOCKET; cpu++) {
      for (event = 0; event < N_HTMMEVENTS; event++) {
          if (mem_event[cpu][event])
        perf_event_disable(mem_event[cpu][event]); //禁用所有的性能监控事件
      }
    }
}

static int ksamplingd(void *data)
{
    unsigned long long nr_sampled = 0;
    unsigned long long nr_throttled = 0;
    unsigned long long nr_unknown = 0;

    while (!kthread_should_stop()) {
        int cpu, event;

        for (cpu = 0; cpu < CPUS_PER_SOCKET; cpu++) {
            for (event = 0; event < N_HTMMEVENTS; event++) {
                struct perf_buffer *rb;
                struct perf_event_mmap_page *up;
                struct perf_event_header *ph;
                struct htmm_event *he;
                unsigned long pg_index, offset;
                int page_shift;

                if (!mem_event[cpu][event])
                    continue;

                __sync_synchronize();//提供内存屏障，确保之前的读写操作在访问共享数据 rb 之前完成

                rb = mem_event[cpu][event]->rb;//获取当前event收集的数据
                if (!rb) {
                    printk("event->rb is NULL\n");
                    return -1;
                }
                /* perf_buffer is ring buffer */
                up = READ_ONCE(rb->user_page);
                if (READ_ONCE(up->data_head) == up->data_tail) {//读取并检查环形缓冲区的头部和尾部索引，如果相等，表示缓冲区为空，继续下一次循环
                    continue;
                }
                /* read barrier */
                smp_rmb();//确保环形缓冲区的尾部索引读取完成后，再进行其他依赖读取操作

                page_shift = PAGE_SHIFT + page_order(rb);//定位到实际数据
                /* get address of a tail sample */
                offset = READ_ONCE(up->data_tail);
                pg_index = (offset >> page_shift) & (rb->nr_pages - 1);
                offset &= (1 << page_shift) - 1;

                ph = (void*)(rb->data_pages[pg_index] + offset); //指向采样事件的头部 header
                switch (ph->type) {
                    case PERF_RECORD_SAMPLE:
                      he = (struct htmm_event *)ph;
                      if (!valid_va(he->addr)) {
                          printk("invalid va: %llx\n", he->addr);
                          break;
                  		}
                      /* TODO: update page info */
                      nr_sampled++;
                 			// 获取对应的采样数据
                    	// method1
                    	struct read_format *rf = he->v;
                    	unsigned long long sample_value = rf->value;
                    	printk("sample_value:%llu", sample_value );
                    	// method2
                    	u32 size = he->size;
                      char* data =he->data;
                      printk("data size:%llu, data:%c", size, data)l
                      
                    
                    	break;
                    case PERF_RECORD_THROTTLE:
              				break;
                    case PERF_RECORD_UNTHROTTLE:
                      nr_throttled++;
                  		break;
                    default:
                      nr_unknown++;
                      break;
              }

              /* read, write barrier */
              smp_mb();//确保在更新环形缓冲区尾部索引之前，所有写入操作已完成
              WRITE_ONCE(up->data_tail, up->data_tail + ph->size);
            }
          }
       }

    printk("nr_sampled: %llu, nr_throttled: %llu, nr_unknown: %llu\n", nr_sampled, nr_throttled, nr_unknown);

    return 0;
}

static int ksamplingd_run(void)
{
    int err = 0;

    if (!access_sampling) {
			access_sampling = kthread_run(ksamplingd, NULL, "ksamplingd");//创建内核线程ksamplingd
    if (IS_ERR(access_sampling)) {
        err = PTR_ERR(access_sampling);
        access_sampling = NULL;
    }
    }
    return err;
}

int ksamplingd_init(pid_t pid, int node)
{
    int ret;

    if (access_sampling)
			return 0;

    ret = pebs_init(pid, node);
    if (ret) {
      printk("htmm__perf_event_init failure... ERROR:%d\n", ret);
      return 0;
    }

    return ksamplingd_run();//创建内核线程ksamplingd
}

void ksamplingd_exit(void)
{
    if (access_sampling) {
      kthread_stop(access_sampling);
      access_sampling = NULL;
    }
    pebs_disable();
}
```



关于file->private_data的解读：https://blog.csdn.net/qq_42049394/article/details/131586941

Linux读写锁解析：http://www.wowotech.net/kernel_synchronization/rwsem.html

Linux中的current变量解析：https://nanxiao.me/linux-kernel-note-18-current/

kmalloc函数的使用：http://www.deansys.com/doc/ldd3/ch08.html

`PERF_RECORD_THROTTLE` 和 `PERF_RECORD_UNTHROTTLE` 是 Linux 内核中的 perf 事件子系统中的两种特殊记录类型，它们用于指示性能监控事件的门事件（fencing events）。门事件主要用于控制事件的采样率，防止因采样过于频繁而导致的性能退化。

以下是对这两种记录类型的解释：

1. **`PERF_RECORD_THROTTLE`**：
   - 这种类型的记录表示性能监控事件的采样被暂停或限制。这通常发生在当系统管理员或性能监控工具认为采样可能对系统性能产生负面影响时。
   - 当一个性能事件被节流时，它不会生成新的采样数据，直到收到对应的 `PERF_RECORD_UNTHROTTLE` 事件。

2. **`PERF_RECORD_UNTHROTTLE`**：
   - 这种类型的记录表示之前被节流的性能监控事件现在被恢复，可以继续生成采样数据。
   - 这通常发生在系统条件改变，且认为可以安全地恢复采样时。

对于这两种类型的记录，它们的数据结构大致如下：

```c
struct {
    struct perf_event_header header; // 通用的事件头部
    u64 time;                       // 事件发生时的时间戳
    u64 id;                         // 事件的唯一标识符
    u64 stream_id;                  // 事件流的标识符
};
```

- `struct perf_event_header header`：每个 perf 事件记录都包含一个通用的头部，其中包含了事件的类型和其他元数据。
- `u64 time`：事件发生时的时间戳，通常表示自系统启动以来的纳秒数。
- `u64 id`：这个字段表示事件的唯一标识符，可以用来识别特定的性能事件。
- `u64 stream_id`：这个字段表示事件流的标识符。在 perf 系统中，事件可以组织成流，以便于管理和分析。

在 `ksamplingd` 函数中，如果处理到这两种类型的事件，通常会更新一个计数器来跟踪节流和取消节流的事件数量。例如：

```c
switch (ph->type) {
    case PERF_RECORD_THROTTLE:
        nr_throttled++;
        break;
    case PERF_RECORD_UNTHROTTLE:
        // 可以在这里添加处理逻辑，比如重置某些计数器
        break;
    // 其他事件处理...
}
```

在实际的性能监控场景中，节流和取消节流的事件可以用于动态调整性能数据的收集频率，以适应不同的监控需求和系统负载情况。





https://zhou-yuxin.github.io/articles/2017/Linux%20perf%E5%AD%90%E7%B3%BB%E7%BB%9F%E7%9A%84%E4%BD%BF%E7%94%A8%EF%BC%88%E4%B8%80%EF%BC%89%E2%80%94%E2%80%94%E8%AE%A1%E6%95%B0/index.html



perf和intel pcm的区别：https://stackoverflow.com/questions/21250695/difference-in-perf-and-intel-pcm

![image-20240829194019153](/Users/hong/Library/Application%20Support/typora-user-images/image-20240829194019153.png)

Performance monitoring events can be found here: https://perfmon-events.intel.com/.



CPUID leaf https://www.cnblogs.com/qianxinn/p/15061748.html

4th Generation Intel Xeon Processor Scalable Family based on Sapphire Rapids microarchitecture https://perfmon-events.intel.com/#





使用 GDB（GNU Debugger）进行调试通常包括以下步骤：

1. **编译程序**：首先，确保你的程序是用调试选项编译的。对于 C 或 C++ 程序，你可以使用 `-g` 编译器选项来生成调试信息。

    ```sh
    g++ -g -o my_program my_program.cpp
    ```

2. **启动 GDB**：使用以下命令启动 GDB 并加载你的程序。

    ```sh
    gdb ./my_program
    ```

3. **设置断点**：在代码的特定位置设置断点，使用 `break` 或 `b` 命令。你可以按行号或函数名来设置断点。

    ```sh
    break main
    ```

    或者：

    ```sh
    break my_program.cpp:42
    ```

4. **运行程序**：使用 `run` 命令开始执行程序。程序将运行到下一个断点。

    ```sh
    run
    ```

5. **查看程序状态**：当程序在断点处停止时，你可以使用以下命令来检查程序状态：

    - `backtrace` 或 `bt`：显示当前的调用栈。
    - `list` 或 `l`：显示当前断点处的源代码。
    - `info locals`：显示局部变量的信息。
    - `info args`：显示函数参数的信息。
    - `print` 或 `p`：打印变量的值。

6. **单步执行**：使用 `step` 或 `s` 命令单步进入函数内部，或者使用 `next` 或 `n` 命令单步执行但不进入函数内部。

7. **继续执行**：使用 `continue` 或 `c` 命令继续程序执行直到下一个断点或程序结束。

8. **退出 GDB**：使用 `quit` 或 `q` 命令退出 GDB。

9. **信号处理**：如果程序因信号（如 segmentation fault）而崩溃，GDB 会停下来。你可以使用 `info signals` 查看信号信息，然后继续执行或退出。

10. **附加到正在运行的进程**：如果你需要调试一个已经运行的程序，可以使用 `attach` 命令。

    ```sh
    gdb -p <process-id>
    ```

11. **使用 GDB 脚本**：你可以将 GDB 命令放入一个脚本文件中，然后使用 `source` 命令执行它们。

    ```sh
    source my_gdb_script.gdb
    ```

12. **设置 GDB 配置**：你可以使用 `set` 命令来设置 GDB 的配置选项，例如设置打印变量时的格式。

这些是 GDB 调试的基本步骤。GDB 是一个功能强大的工具，支持许多高级特性，如条件断点、观察点（watchpoints）、反向跟踪（backtrace）等。你可以使用 `help` 命令在 GDB 中获取更多帮助信息。



![image-20240830015923251](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830015923251.png)

![image-20240830020001081](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830020001081.png)

最后一步是这个

![image-20240830022243527](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830022243527.png)

![image-20240830023429209](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830023429209.png)

![image-20240830023504860](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830023504860.png)

在 GDB 中，不能直接为 lambda 函数设置断点，因为 lambda 函数是匿名的，它们没有名字来标识。但是，你可以通过以下几种方法间接调试 lambda 函数：

1. **捕获 lambda 函数的地址**：
   如果你有一个 lambda 函数的引用或者指针，你可以在 GDB 中使用这个地址来设置断点。例如：

   ```cpp
   auto lambda = [](int x) { return x * x; };
   ```

   在 GDB 中，你可以使用 `lambda` 的地址来设置断点：

   ```gdb
   (gdb) break *(lambda address)
   ```

2. **使用调用 lambda 的函数或代码上下文**：
   如果你知道调用 lambda 函数的函数或代码位置，你可以在调用 lambda 的位置设置断点。

3. **使用源代码位置**：
   如果你在编译时带有调试信息（通常是使用 `-g` 编译器选项），你可以尝试在调用 lambda 的源代码行设置断点：

   ```gdb
   (gdb) break my_file.cpp:42
   ```

   其中 `my_file.cpp:42` 是调用 lambda 的代码行。

4. **单步执行到 lambda 调用**：
   如果你在调用 lambda 函数的循环或某个代码块中，你可以设置断点然后单步执行到 lambda 调用的位置。

5. **使用 watchpoint**：
   如果你想要监视 lambda 函数内部变量的变化，你可以设置一个 watchpoint：

   ```gdb
   (gdb) watch variable_name
   ```

6. **使用 `catch` 命令**：
   如果你想要捕获 lambda 函数抛出的异常，可以使用 `catch throw` 命令：

   ```gdb
   (gdb) catch throw
   ```

7. **编译带有调试信息**：
   确保你的程序是使用调试信息编译的，这样 GDB 才能正确地解析 lambda 函数和相关的变量。

8. **使用 `info args` 和 `info locals`**：
   当程序在 lambda 函数内部暂停时，你可以使用 `info args` 查看 lambda 函数的参数，使用 `info locals` 查看局部变量。

请注意，调试 lambda 函数可能会比较复杂，特别是当它们在多个地方被调用或捕获了外部上下文的变量时。在某些情况下，可能需要结合使用多种 GDB 功能来有效地调试 lambda 函数。



```c++
auto programPMUs = [&m, &pid](const PCM::RawPMUConfigs & config)
    {
        if (verbose)
        {
            for (const auto & pmuConfig: config)
            {
                for (const auto & e : pmuConfig.second.fixed)
                {
                    cerr << "Programming " << pmuConfig.first << " fixed event: " << e.second << "\n";
                }
                for (const auto & e : pmuConfig.second.programmable)
                {
                    cerr << "Programming " << pmuConfig.first << " programmable event: " << e.second << "\n";
                }
            }
        }
        PCM::ErrorCode status = m->program(config, !verbose, pid);//add breakpoint
        m->checkError(status);
    };

    SystemCounterState SysBeforeState, SysAfterState;
    vector<CoreCounterState> BeforeState, AfterState;
    vector<SocketCounterState> BeforeSocketState, AfterSocketState;
    vector<ServerUncoreCounterState> BeforeUncoreState, AfterUncoreState;
    BeforeUncoreState.resize(m->getNumSockets());
    AfterUncoreState.resize(m->getNumSockets());

    if ((sysCmd != NULL) && (delay <= 0.0)) {
        // in case external command is provided in command line, and
        // delay either not provided (-1) or is zero
        m->setBlocked(true);
    }
    else {
        m->setBlocked(false);
    }

    if (delay <= 0.0) delay = defaultDelay;

    cerr << "Update every " << delay << " seconds\n";

    std::cout.precision(2);
    std::cout << std::fixed;

    if (sysCmd != NULL) {
        MySystem(sysCmd, sysArgv);
    }

    auto programAndReadGroup = [&](const PCM::RawPMUConfigs & group)
    {
        if (forceRTMAbortMode)
        {
            m->enableForceRTMAbortMode(true);
        }
        programPMUs(group);//add breakpoint
        m->globalFreezeUncoreCounters();
        m->getAllCounterStates(SysBeforeState, BeforeSocketState, BeforeState);
        for (uint32 s = 0; s < m->getNumSockets(); ++s)
        {
            BeforeUncoreState[s] = m->getServerUncoreCounterState(s);
        }
        m->globalUnfreezeUncoreCounters();
    };

    if (nGroups == 1)
    {
        programAndReadGroup(PMUConfigs[0]);
    }

    mainLoop([&]()
    {
         size_t groupNr = 0;
         for (const auto & group : PMUConfigs)
         {
                ++groupNr;

                if (nGroups > 1)
                {
                    programAndReadGroup(group);
                }

                calibratedSleep(delay, sysCmd, mainLoop, m);

                m->globalFreezeUncoreCounters();
                m->getAllCounterStates(SysAfterState, AfterSocketState, AfterState);
                for (uint32 s = 0; s < m->getNumSockets(); ++s)
                {
                    AfterUncoreState[s] = m->getServerUncoreCounterState(s);
                }
                m->globalUnfreezeUncoreCounters();

                //cout << "Time elapsed: " << dec << fixed << AfterTime - BeforeTime << " ms\n";
                //cout << "Called sleep function for " << dec << fixed << delay_ms << " ms\n";

                printAll(group, m, SysBeforeState, SysAfterState, BeforeState, AfterState, BeforeUncoreState, AfterUncoreState, BeforeSocketState, AfterSocketState, PMUConfigs, groupNr == nGroups);
                if (nGroups == 1)
                {
                    std::swap(BeforeState, AfterState);
                    std::swap(BeforeSocketState, AfterSocketState);
                    std::swap(BeforeUncoreState, AfterUncoreState);
                    std::swap(SysBeforeState, SysAfterState);
                }
         }
         if (m->isBlocked()) {
             // in case PCM was blocked after spawning child application: break monitoring loop here
             return false;
         }
         return true;
    });
    exit(EXIT_SUCCESS);
}

```



1. **programPMUs 函数**： 这是一个 lambda 函数，用于配置 PMU。它接受一个 `PCM::RawPMUConfigs` 类型的参数，这是一个包含所有监控事件配置的容器。函数内部首先检查是否设置了 `verbose` 模式，如果是，它会打印出所有固定和可编程事件的配置信息。然后调用 `m->program` 方法来实际配置 PMU，并检查配置过程中是否有错误。
2. **programAndReadGroup 函数**： 这是另一个 lambda 函数，用于配置 PMU 并读取初始的性能计数器状态。它调用 `programPMUs` 函数来配置 PMU，然后冻结非核心计数器，获取所有计数器的状态，并存储在之前定义的变量中。
3. **mainLoop 函数**： 这是程序的主要循环，用于重复收集性能数据。它接受一个 lambda 函数作为参数，这个 lambda 函数在每次循环迭代中被调用。在循环中，程序可以选择性地配置 PMU、等待指定的延迟时间、冻结和获取性能计数器状态，然后调用 `printAll` 函数来打印性能数据。



![image-20240830025742161](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830025742161.png)

![image-20240830030020583](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830030020583.png)





![image-20240830133502110](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830133502110.png)





```c
//不同种类的read操作有什么区别？

int32 MsrHandle::read(uint64 msr_number, uint64 * value)
{
    cpuctl_msr_args_t args;
    int32 ret;

    args.msr = msr_number;
    ret = ::ioctl(fd, CPUCTL_RDMSR, &args); //fd == handle
    if (ret) return ret;
    *value = args.data;
    return sizeof(*value);
}


// OSX 相关
int32 MsrHandle::read(uint64 *msr_number*, uint64 ***** *value*)
{
 		//MSRAccessor * MsrHandle::driver = NULL; 
    return driver->read(cpu_id, msr_number, value);

}


// windows系统中的函数
int32 MsrHandle::read(uint64 msr_number, uint64 * value)
{
    if (hDriver != INVALID_HANDLE_VALUE)
    {
        MSR_Request req;
        // ULONG64 result;
        DWORD reslength = 0;
        req.core_id = cpu_id;
        req.msr_address = msr_number;
        BOOL status = DeviceIoControl(hDriver, IO_CTL_MSR_READ, &req, sizeof(MSR_Request), value, sizeof(uint64), &reslength, NULL);
        assert(status && "Error in DeviceIoControl");
        return (int32)reslength;
    }

    cvt_ds cvt;
  /*
  
  */
    cvt.ui64 = 0;

    ThreadGroupTempAffinity affinity(cpu_id);
    DWORD status = Rdmsr((DWORD)msr_number, &(cvt.ui32.low), &(cvt.ui32.high)); //主要是这个函数
  //需要在C++中引入对应的module, library

    if (status) *value = cvt.ui64;

    return status ? sizeof(uint64) : 0;
}

```

<img src="/Users/hong/Library/Application%20Support/typora-user-images/image-20240830191816888.png" alt="image-20240830191816888" style="zoom:50%;" />





![image-20240830192041453](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830192041453.png)

OlsApiInit.h

![image-20240830192128099](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830192128099.png)

看起来是Windows的API而不是Linux的API。

![image-20240830192210569](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830192210569.png)

绕过Linux Kernel读写MSRs的工具——msr-tools

https://www.intel.com/content/www/us/en/developer/articles/technical/software-security-guidance/best-practices/reading-writing-msrs-in-linux.html

要看引用的动态链接库. libcpuid.h, libcpuid_utils.h, libcpuid_internal.h









![image-20240830201237766](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830201237766.png)

https://github.com/anrieff/libcpuid/blob/master/libcpuid/rdmsr.c

rdmsr的函数

CPUCTL_RDMSR

![image-20240830202431450](/Users/hong/Library/Application%20Support/typora-user-images/image-20240830202431450.png)

https://man.freebsd.org/cgi/man.cgi?query=cpuctl&sektion=4&format=html

<img src="/Users/hong/Library/Application%20Support/typora-user-images/image-20240830204854800.png" alt="image-20240830204854800" style="zoom:50%;" />

这里的内核代码rdmsrl/wrmsrl和ioctl(driver->fd, CPUCTL_RDMSR, &args)有区别吗？





FreeBSD、DragonFly BSD 和 Linux 都是开源的类 Unix 操作系统，它们在很多方面有相似之处，比如都支持多用户、多任务、网络功能等，但它们之间也存在一些关键的区别：

1. **内核架构**：
   - **FreeBSD**：使用 BSD 许可证，它的内核是完全自由的，没有 Linux 内核中的某些限制。FreeBSD 以其稳定性和性能著称，特别是在网络和文件系统方面。
   - **DragonFly BSD**：也是基于 BSD 许可证，但它的内核设计有一些独特之处，比如使用更先进的内存管理和调度算法，以提高多核心处理器的性能。
   - **Linux**：使用 GNU 通用公共许可证（GPL），它的内核是开源社区中最著名的，支持广泛的硬件和设备。

2. **许可证**：
   - FreeBSD 和 DragonFly BSD 通常使用 BSD 许可证，这使得它们在商业使用上更加灵活。
   - Linux 使用 GPL 许可证，这要求任何修改后的代码也必须开源。

3. **软件包管理**：
   - **FreeBSD** 使用 Ports 系统和 pkg 管理器。
   - **DragonFly BSD** 也使用类似的 Ports 系统。
   - **Linux** 发行版通常使用如 apt、yum、dnf 等不同的包管理器。

4. **用户社区和支持**：
   - Linux 拥有最大的用户社区和开发者基础，因此它通常拥有最多的软件包和支持。
   - FreeBSD 和 DragonFly BSD 的社区相对较小，但它们都非常活跃和支持性强。

5. **目标用户**：
   - Linux 适合广泛的用户，从桌面用户到服务器管理员。
   - FreeBSD 通常被认为是服务器和嵌入式系统的好选择。
   - DragonFly BSD 可能更适合那些需要高性能文件系统和调度算法的用户。

6. **性能和特性**：
   - 每个系统都有其特定的性能优化和特性，这取决于它们的设计目标和用户需求。

选择哪个系统通常取决于个人或组织的特定需求、偏好以及对特定特性的需求。







intel pcm的msr.cpp中有不同操作系统平台下的对msr读写操作的函数。主要包括Windows, FreeBSD, Dragonfly, Linux,OSX等。由于服务器平台使用Linux系统，所以这里我们主要分析Linux平台下针对msr寄存器的读写操作。

```c++
int32 MsrHandle::write(uint64 msr_number, uint64 value)
{
#if 0
    static std::mutex m;
    std::lock_guard<std::mutex> g(m);
    std::cout << "DEBUG: writing MSR 0x" << std::hex << msr_number << " value 0x" << value << " on cpu " << std::dec << cpu_id << std::endl;
#endif
    if (fd < 0) return 0;
    return ::pwrite(fd, (const void *)&value, sizeof(uint64), msr_number);
}

int32 MsrHandle::read(uint64 msr_number, uint64 * value)
{
    if (fd < 0) return 0;
    return ::pread(fd, (void *)value, sizeof(uint64), msr_number);
}

```

主要有两个函数pwrite和pread，通过以上两个函数对msr进行读写。

Linux系统调用pread, pwrite实现多线程中文件复制：https://blog.csdn.net/yexiangCSDN/article/details/103387201

https://www.cnblogs.com/-colin/p/7992214.html

```c
#include<unistd.h>
// pread() 原子操作
ssize_t  pread (int filedes,   void *buf,  size_t  nbytes,  off_t  offset );

/*  成功：返回读到的字节数；出错：返回-1；到文件结尾：返回0
原因：由于lseek和read 调用之间，内核可能会临时挂起进程，所以对同步问题造成了问题，调用pread相当于顺序调用了lseek 和　read，这两个操作相当于一个捆绑的原子操作。
实现：文件（由filedes所指）－读nbytes字节－＞内存buf中。
补充：调用pread时，无法中断其定位和读操作，另外不更新文件指针。
*/
//pwrite()
ssize_t  pwrite (int filedes,   const void *buf,  size_t  nbytes,  off_t  offset );

/*  成功：返回已写的字节数；出错：返回-1；
原因：由于lseek和write 调用之间，内核可能会临时挂起进程，所以对同步问题造成了问题，调用pwrite相当于顺序调用了lseek 和　write，这两个操作相当于一个捆绑的原子操作。
实现：文件（由filedes所指）＜－写nbytes字节－内存buf中。
补充：调用pwrite时，无法中断其定位和读操作，另外不更新文件指针。
*/
```

pread和pwrite，这两个函数允许指定文件偏移量进行I/O操作，不改变文件当前偏移量，适合多线程环境。通过它们，可以实现原子性的文件读写，避免了线程间的竞争问题。文章探讨了如何利用这两个函数在**多线程中实现文件复制**，简化了如迅雷下载等复杂场景的实现。

<img src="/Users/hong/Library/Application%20Support/typora-user-images/image-20240831155155201.png" alt="image-20240831155155201" style="zoom:50%;" />





`/sys/module/msr/parameters` 是 Linux 内核中的一个特殊文件目录，它与内核模块 `msr` 相关。`msr` 模块提供了一个接口来读取和写入 x86 CPU 的模型特定寄存器（MSRs）。这些寄存器是用于控制和监视 CPU 的各种功能和特性的一组特殊寄存器。

在 `/sys/module/msr/parameters` 目录下，你可以找到与 `msr` 模块相关的参数。这些参数是通过 `module_param` 宏在内核模块代码中定义的，并且它们允许在加载模块时通过命令行指定参数值。这些参数的值可以在模块加载后通过 `sysfs` 文件系统进行读取和修改（如果权限允许的话）。

例如，如果你有一个名为 `debug` 的参数，你可以在 `/sys/module/msr/parameters/debug` 文件中读取或写入它的值。这可以用来开启或关闭模块的调试模式，或者调整模块的行为。

需要注意的是，修改这些参数可能会影响系统的行为，甚至可能导致系统不稳定，因此通常需要具有 root 权限才能进行修改。此外，不是所有的内核模块都会导出参数到 `sysfs`，只有那些在模块代码中明确使用 `module_param` 宏导出的参数才会出现在这里。

在某些情况下，`/sys/module/msr/parameters` 目录可能不存在，这可能是因为 `msr` 模块没有被加载，或者模块没有定义任何导出参数。你可以通过 `lsmod` 命令检查 `msr` 模块是否已加载，或者使用 `modprobe msr` 命令尝试加载它。

总的来说，`/sys/module/msr/parameters` 是一个用于内核模块参数的接口，它允许用户空间程序与内核模块交互，调整模块的行为。



可以理解为内核关于msr有一部分用户可配的参数，可以通过修改/sys/module/msr/parameters下的参数进行修改。

