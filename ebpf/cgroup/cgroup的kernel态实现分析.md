# cgroup的kernel态实现分析

cgroup数据结构设计（从进程角度分析）：https://abcdxyzk.github.io/blog/2015/08/07/cgroup-2/

https://abcdxyzk.github.io/blog/2015/07/31/cgroup-base/

cgroup文件系统：https://abcdxyzk.github.io/blog/2015/08/07/cgroup-3/

CPU子系统：https://abcdxyzk.github.io/blog/2015/08/07/cgroup-4/

cgroup框架的实现：https://winddoing.github.io/post/3438.html



subsystem。一个子系统就是一个资源控制器，MT2中明确说明设置TGroup为一个新的subsystem，故而应是与cpu，memory等控制器同级别，实现原理相同的组件。

`/linux/include/linux/sched.h`中task_struct的定义，与cgroups相关的如下：

```c
#ifdef CONFIG_CGROUPS
	/* Control Group info protected by css_set_lock: */
	struct css_set __rcu		*cgroups;
	/* cg_list protected by css_set_lock and tsk->alloc_lock: */
	struct list_head		cg_list;
#endif
```

> [!NOTE]
>
> `__rcu`是Linux内核中用于标记那些受RCU（Read-Copy-Update）机制保护的指针的后缀。RCU是一种用于管理共享数据同步的机制，它允许多个读者并发访问数据而不需要加锁，同时允许单个写者在复制的数据上进行更新操作，更新完成后再安全地将指针指向新数据。这种机制特别适用于读多写少的场景，可以显著提高性能。
>
> 在Linux内核中，`__rcu`修饰的指针通常与RCU提供的API如`rcu_dereference()`、`rcu_assign_pointer()`和`synchronize_rcu()`等一起使用，以确保数据访问的安全性和更新操作的正确性。`rcu_dereference()`用于读取受RCU保护的指针，而`rcu_assign_pointer()`则用于安全地更新这些指针。`synchronize_rcu()`是一个写者调用的函数，用于等待一个宽限期（grace period）结束，确保所有读者完成对旧数据的访问后，再安全地释放旧数据 。
>
> 使用`__rcu`标记的指针时，编译器和运行时会确保对这些指针的访问遵循RCU的规则，比如在读取时使用`rcu_dereference()`宏，而在更新时使用`rcu_assign_pointer()`宏，并在适当的时候调用`synchronize_rcu()`来等待宽限期结束 。这样，RCU机制可以保证在更新数据结构时，不会影响正在并发访问这些数据结构的读者，从而实现高效的并发访问 。



那为什么要这样一个结构呢？

从前面的分析，我们可以看出从task到cgroup是很容易定位的，但是从cgroup获取此cgroup的所有的task就必须通过这个结构了。每个进程都会指向一个css_set，而与这个css_set关联的所有进程都会链入到css_set->tasks链表.而cgroup又通过一个中间结构cg_cgroup_link来寻找所有与之关联的所有css_set，从而可以得到与cgroup关联的所有进程。

```c
struct cgroup_subsys {
	struct cgroup_subsys_state *(*css_alloc)(struct cgroup_subsys_state *parent_css);
	int (*css_online)(struct cgroup_subsys_state *css);
	void (*css_offline)(struct cgroup_subsys_state *css);
	void (*css_released)(struct cgroup_subsys_state *css);
	void (*css_free)(struct cgroup_subsys_state *css);
	void (*css_reset)(struct cgroup_subsys_state *css);
	void (*css_rstat_flush)(struct cgroup_subsys_state *css, int cpu);
	int (*css_extra_stat_show)(struct seq_file *seq,
				   struct cgroup_subsys_state *css);

	int (*can_attach)(struct cgroup_taskset *tset);
	void (*cancel_attach)(struct cgroup_taskset *tset);
	void (*attach)(struct cgroup_taskset *tset);
	void (*post_attach)(void);
	int (*can_fork)(struct task_struct *task,
			struct css_set *cset);
	void (*cancel_fork)(struct task_struct *task, struct css_set *cset);
	void (*fork)(struct task_struct *task);
	void (*exit)(struct task_struct *task);
	void (*release)(struct task_struct *task);
	void (*bind)(struct cgroup_subsys_state *root_css);

	bool early_init:1;

	/*
	 * If %true, the controller, on the default hierarchy, doesn't show
	 * up in "cgroup.controllers" or "cgroup.subtree_control", is
	 * implicitly enabled on all cgroups on the default hierarchy, and
	 * bypasses the "no internal process" constraint.  This is for
	 * utility type controllers which is transparent to userland.
	 *
	 * An implicit controller can be stolen from the default hierarchy
	 * anytime and thus must be okay with offline csses from previous
	 * hierarchies coexisting with csses for the current one.
	 */
	bool implicit_on_dfl:1;

	/*
	 * If %true, the controller, supports threaded mode on the default
	 * hierarchy.  In a threaded subtree, both process granularity and
	 * no-internal-process constraint are ignored and a threaded
	 * controllers should be able to handle that.
	 *
	 * Note that as an implicit controller is automatically enabled on
	 * all cgroups on the default hierarchy, it should also be
	 * threaded.  implicit && !threaded is not supported.
	 */
	bool threaded:1;

	/* the following two fields are initialized automatically during boot */
	int id;
	const char *name;

	/* optional, initialized automatically during boot if not set */
	const char *legacy_name;

	/* link to parent, protected by cgroup_lock() */
	struct cgroup_root *root;

	/* idr for css->id */
	struct idr css_idr;

	/*
	 * List of cftypes.  Each entry is the first entry of an array
	 * terminated by zero length name.
	 */
	struct list_head cfts;

	/*
	 * Base cftypes which are automatically registered.  The two can
	 * point to the same array.
	 */
	struct cftype *dfl_cftypes;	/* for the default hierarchy */
	struct cftype *legacy_cftypes;	/* for the legacy hierarchies */

	/*
	 * A subsystem may depend on other subsystems.  When such subsystem
	 * is enabled on a cgroup, the depended-upon subsystems are enabled
	 * together if available.  Subsystems enabled due to dependency are
	 * not visible to userland until explicitly enabled.  The following
	 * specifies the mask of subsystems that this one depends on.
	 */
	unsigned int depends_on;
};
```

cgroup_subsys定义了一组操作，让各个子系统根据各自的需要去实现。这个相当于C++中抽象基类，然后各个特定的子系统对应cgroup_subsys则是实现了相应操作的子类。类似的思想还被用在了cgroup_subsys_state中，cgroup_subsys_state并未定义控制信息，而只是定义了各个子系统都需要的共同信息，比如该cgroup_subsys_state从属的cgroup。然后各个子系统再根据各自的需要去定义自己的进程控制信息结构体，最后在各自的结构体中将cgroup_subsys_state包含进去，这样通过Linux内核的container_of等宏就可以通过cgroup_subsys_state来获取相应的结构体。

cgroup_subsys_state是定义子系统行为的抽象，而cgroup_subsys_state是跟踪和存储特定cgroup在某个子系统中状态的数据结构，而且是所有cgroup_subsys都有的共同状态数据，如果自己有特殊需要，可以自己定义。



---

cgroup的用户空间管理是通过cgroup文件系统实现的。每创建一个层级的时候，系统的所有进程都会自动被加到该层级的**根cgroup**里面。cgroups通过实现cgroup文件系统来为用户提供管理cgroup的工具，而cgroup文件系统是基于Linux VFS实现的，也就需要实现Linux VFS要求实现的结构和算法。相应地，cgroups为控制文件定义了相应的数据结构cftype，对其操作由cgroup文件系统定义的通过操作捕获，再调用cftype定义的具体实现。



用户层mkdir新的cgroup的时候，做了两次转换，一次是从系统通用命令到cgroup文件系统，另一次是从cgroup文件系统再到特定的子系统实现。

1. 先定义一个cgroup_subsys的结构体(换成自己的定义）：

   ```c
   struct cgroup_subsys cpu_cgroup_subsys={
     .name = "cpu",
     .create = cpu_cgroup_create,
     .destroy = cpu_cgroup_destroy,
     .can_attach = cpu_cgroup_can_attach,
     .populate = cpu_cgroup_populate,
     .subsys_id = cpu_cgroup_subsys_id,
     .early_init = 1,
   };
   ```

2. 除了cgroup中通用的控制文件外，每个子系统还有自己的控制文件，子系统也是通过cftype来管理这些控制文件。当对cgroup目录下的文件进行操作时，该结构体中定义的函数指针指向的函数就会被调用。

   ```c
   #ifdef CONFIG_FAIR_GROUP_SCHED
   {
   	.name = "shares",
   	.read_u64 = cpu_shares_read_u64,
   	.write_u64 = cpu_shares_write_u64,
   },
   #endif
   ```

![image-20240824184136125](/Users/hong/Library/Application%20Support/typora-user-images/image-20240824184136125.png)







cftype结构体的组成。

```c
struct cftype {
	/*
	 * By convention, the name should begin with the name of the
	 * subsystem, followed by a period.  Zero length string indicates
	 * end of cftype array.
	 */
	char name[MAX_CFTYPE_NAME];
	unsigned long private;

	/*
	 * The maximum length of string, excluding trailing nul, that can
	 * be passed to write.  If < PAGE_SIZE-1, PAGE_SIZE-1 is assumed.
	 */
	size_t max_write_len;

	/* CFTYPE_* flags */
	unsigned int flags;

	/*
	 * If non-zero, should contain the offset from the start of css to
	 * a struct cgroup_file field.  cgroup will record the handle of
	 * the created file into it.  The recorded handle can be used as
	 * long as the containing css remains accessible.
	 */
	unsigned int file_offset;

	/*
	 * Fields used for internal bookkeeping.  Initialized automatically
	 * during registration.
	 */
	struct cgroup_subsys *ss;	/* NULL for cgroup core files */
	struct list_head node;		/* anchored at ss->cfts */
	struct kernfs_ops *kf_ops;

	int (*open)(struct kernfs_open_file *of);
	void (*release)(struct kernfs_open_file *of);

	/*
	 * read_u64() is a shortcut for the common case of returning a
	 * single integer. Use it in place of read()
	 */
	u64 (*read_u64)(struct cgroup_subsys_state *css, struct cftype *cft);
	/*
	 * read_s64() is a signed version of read_u64()
	 */
	s64 (*read_s64)(struct cgroup_subsys_state *css, struct cftype *cft);

	/* generic seq_file read interface */
	int (*seq_show)(struct seq_file *sf, void *v);

	/* optional ops, implement all or none */
	void *(*seq_start)(struct seq_file *sf, loff_t *ppos);
	void *(*seq_next)(struct seq_file *sf, void *v, loff_t *ppos);
	void (*seq_stop)(struct seq_file *sf, void *v);

	/*
	 * write_u64() is a shortcut for the common case of accepting
	 * a single integer (as parsed by simple_strtoull) from
	 * userspace. Use in place of write(); return 0 or error.
	 */
	int (*write_u64)(struct cgroup_subsys_state *css, struct cftype *cft,
			 u64 val);
	/*
	 * write_s64() is a signed version of write_u64()
	 */
	int (*write_s64)(struct cgroup_subsys_state *css, struct cftype *cft,
			 s64 val);

	/*
	 * write() is the generic write callback which maps directly to
	 * kernfs write operation and overrides all other operations.
	 * Maximum write size is determined by ->max_write_len.  Use
	 * of_css/cft() to access the associated css and cft.
	 */
	ssize_t (*write)(struct kernfs_open_file *of,
			 char *buf, size_t nbytes, loff_t off);

	__poll_t (*poll)(struct kernfs_open_file *of,
			 struct poll_table_struct *pt);

#ifdef CONFIG_DEBUG_LOCK_ALLOC
	struct lock_class_key	lockdep_key;
#endif
};


```

