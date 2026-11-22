DSA_PROFILE_ID = "PROFILE-DSA"
DSA_SUBJECT = "Data Structures and Algorithms"

DSA_COMPETENCIES = [
    ("COMP-DSA-FOUNDATIONS", "Algorithm Analysis", "Reason about running time, space and input constraints."),
    ("COMP-DSA-LINEAR", "Linear Data Structures", "Choose and use arrays, strings, linked lists, stacks, queues and hash tables."),
    ("COMP-DSA-SEARCH", "Searching and Sorting", "Apply search and sorting algorithms with their preconditions and tradeoffs."),
    ("COMP-DSA-NONLINEAR", "Trees and Graphs", "Represent and traverse hierarchical and connected data."),
    ("COMP-DSA-DESIGN", "Algorithm Design", "Use recursion, backtracking, greedy strategies and dynamic programming."),
]

DSA_SKILLS = [
    ("DSA-COMPLEXITY", "COMP-DSA-FOUNDATIONS", "Time and Space Complexity", "Analyze loops, recurrences, amortized cost and auxiliary space.", 1),
    ("DSA-ARRAYS", "COMP-DSA-LINEAR", "Arrays and Strings", "Use indexing, prefix sums, two pointers and sliding windows.", 1),
    ("DSA-LINKED", "COMP-DSA-LINEAR", "Linked Lists", "Manipulate pointers, reverse lists and detect cycles.", 2),
    ("DSA-STACKS", "COMP-DSA-LINEAR", "Stacks and Queues", "Apply LIFO, FIFO, deques and monotonic stacks.", 2),
    ("DSA-HASHING", "COMP-DSA-LINEAR", "Hashing", "Use maps and sets while reasoning about collisions and load factors.", 2),
    ("DSA-SEARCH-SORT", "COMP-DSA-SEARCH", "Searching and Sorting", "Apply binary search, sorting, partitioning and selection.", 2),
    ("DSA-TREES", "COMP-DSA-NONLINEAR", "Trees and Heaps", "Traverse trees, use BST invariants and maintain priority queues.", 2),
    ("DSA-GRAPHS", "COMP-DSA-NONLINEAR", "Graph Algorithms", "Use BFS, DFS, shortest paths, topological sorting and spanning trees.", 3),
    ("DSA-RECURSION", "COMP-DSA-DESIGN", "Recursion and Backtracking", "Define base cases, explore choices and restore state correctly.", 2),
    ("DSA-GREEDY-DP", "COMP-DSA-DESIGN", "Greedy and Dynamic Programming", "Identify reusable subproblems and justify local or global decisions.", 3),
]

DSA_PREREQUISITES = [
    ("DSA-LINKED", "DSA-ARRAYS"),
    ("DSA-STACKS", "DSA-ARRAYS"),
    ("DSA-HASHING", "DSA-ARRAYS"),
    ("DSA-SEARCH-SORT", "DSA-ARRAYS"),
    ("DSA-TREES", "DSA-RECURSION"),
    ("DSA-GRAPHS", "DSA-STACKS"),
    ("DSA-GRAPHS", "DSA-RECURSION"),
    ("DSA-GREEDY-DP", "DSA-RECURSION"),
    ("DSA-GREEDY-DP", "DSA-SEARCH-SORT"),
]

DSA_STUDY_ORDER = [
    ("DSA-ARRAYS", "DSA-COMPLEXITY"),
    ("DSA-SEARCH-SORT", "DSA-COMPLEXITY"),
    ("DSA-LINKED", "DSA-SEARCH-SORT"),
    ("DSA-STACKS", "DSA-LINKED"),
    ("DSA-HASHING", "DSA-SEARCH-SORT"),
    ("DSA-RECURSION", "DSA-LINKED"),
    ("DSA-TREES", "DSA-LINKED"),
    ("DSA-TREES", "DSA-SEARCH-SORT"),
    ("DSA-TREES", "DSA-STACKS"),
    ("DSA-TREES", "DSA-HASHING"),
    ("DSA-GRAPHS", "DSA-TREES"),
    ("DSA-GREEDY-DP", "DSA-GRAPHS"),
]
