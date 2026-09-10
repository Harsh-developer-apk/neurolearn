from datetime import datetime

from sqlalchemy.orm import Session

from app.models import Course, CourseCompetency, CourseLearningOutcome, CourseModule, CourseTopic


SOURCE_PLATFORM = "iGOT Karmayogi - Prototype Catalog"
CATALOG_TYPE = "prototype_igot_compatible"


def _course(course_id, title, area, mappings, topics, duration=180, difficulty="Intermediate", provider="Prototype iGOT Catalog", learning_format="Video + Assessment"):
    return {
        "course_id": course_id,
        "title": title,
        "short_description": f"Prototype learning resource for {area}.",
        "description": f"This prototype course develops practical capability in {area} through structured concepts, worked examples, knowledge checks and applied scenarios aligned to competency gaps.",
        "provider": provider,
        "source_platform": SOURCE_PLATFORM,
        "catalog_type": CATALOG_TYPE,
        "duration_minutes": duration,
        "difficulty_level": difficulty,
        "language": "English",
        "course_type": "Course",
        "learning_format": learning_format,
        "status": "active",
        "external_url": None,
        "thumbnail_url": None,
        "topics": topics,
        "outcomes": [
            f"Explain core concepts in {area}.",
            f"Apply {area} concepts to realistic work or learning scenarios.",
            "Identify common mistakes and select appropriate corrective actions.",
            "Use assessment feedback to plan the next learning step.",
        ],
        "modules": [
            (f"{area} foundations", 35, "Video"),
            ("Worked examples and guided practice", 45, "Video + PDF"),
            ("Applied scenario walkthrough", 50, "Interactive"),
            ("Knowledge check and reflection", 30, "Assessment"),
        ],
        "mappings": mappings,
    }


STAT_COURSES = [
    _course("STAT-COURSE-001", "Survey Design Fundamentals", "survey objectives and survey planning", [("COMP001", 0.9), ("SKILL001", 1.0), ("SKILL003", 0.7)], ["Survey objectives", "Target population", "Indicators", "Reference period", "Design constraints"], 210, "Beginner", "Capacity Building Centre"),
    _course("STAT-COURSE-002", "Questionnaire Design and Measurement", "questionnaire design and measurement quality", [("COMP001", 0.85), ("SKILL002", 1.0), ("SKILL004", 0.65)], ["Question wording", "Response options", "Measurement error", "Piloting", "Bias reduction"], 180),
    _course("STAT-COURSE-003", "Sampling Methods and Sampling Frames", "sampling frames and probability sampling", [("COMP002", 0.9), ("SKILL005", 0.75), ("SKILL006", 1.0), ("SKILL007", 0.85)], ["Population", "Sample", "Sampling frames", "Simple random sampling", "Frame errors"], 240, "Intermediate", "National Skills Learning Centre"),
    _course("STAT-COURSE-004", "Statistical Sampling: Bias and Representativeness", "sampling bias and representativeness", [("COMP002", 0.75), ("SKILL008", 0.85), ("SKILL004", 1.0)], ["Stratification", "Coverage bias", "Non-response", "Representativeness", "Subgroup precision"], 220),
    _course("STAT-COURSE-005", "Data Quality Management", "data quality management for survey evidence", [("COMP003", 0.9), ("SKILL009", 0.8), ("SKILL012", 1.0)], ["Completeness", "Validity", "Consistency", "Quality indicators", "Review workflows"], 190, "Beginner", "Digital Learning Academy"),
    _course("STAT-COURSE-006", "Data Validation and Quality Assurance", "validation rules and quality assurance", [("COMP003", 0.85), ("SKILL010", 1.0), ("SKILL011", 0.9)], ["Range checks", "Skip checks", "Duplicate detection", "Outlier review", "Audit trails"], 210),
    _course("STAT-COURSE-007", "Fundamentals of Statistical Analysis", "statistical analysis and interpretation", [("COMP004", 0.9), ("SKILL013", 0.8), ("SKILL014", 0.85)], ["Descriptive analysis", "Sampling uncertainty", "Confidence intervals", "Inference", "Interpretation"], 240, "Intermediate", "Capacity Building Centre"),
    _course("STAT-COURSE-008", "Descriptive Statistics and Data Interpretation", "descriptive statistics and data interpretation", [("COMP004", 0.75), ("SKILL013", 1.0)], ["Mean", "Median", "Spread", "Skew", "Tables"], 160, "Beginner"),
    _course("STAT-COURSE-009", "Statistical Metadata and Data Documentation", "metadata standards and data documentation", [("COMP005", 1.0), ("SKILL017", 0.9), ("SKILL018", 0.9), ("SKILL020", 0.8)], ["Variable labels", "Units", "Code lists", "Classifications", "Reuse"], 170, "Beginner", "National Skills Learning Centre"),
    _course("STAT-COURSE-010", "Statistical Reporting and Evidence-Based Interpretation", "statistical reporting and evidence-based interpretation", [("COMP004", 0.8), ("SKILL014", 0.75), ("SKILL015", 0.85), ("SKILL016", 0.7)], ["Report structure", "Uncertainty", "Hypothesis testing", "Regression interpretation", "Evidence statements"], 230, "Advanced"),
]


CS_COURSES = [
    _course("CS-COURSE-001", "Programming Fundamentals with Java", "programming fundamentals with Java", [("COMP-CS-001", 0.9), ("CS-SKILL-OOPS", 0.55)], ["Variables", "Control flow", "Methods", "Debugging", "Basic programs"], 240, "Beginner"),
    _course("CS-COURSE-002", "Object-Oriented Programming with Java", "object-oriented programming in Java", [("COMP-CS-001", 0.9), ("CS-SKILL-OOPS", 1.0)], ["Classes", "Objects", "Inheritance", "Polymorphism", "Interfaces"], 270, "Intermediate", "Digital Learning Academy"),
    _course("CS-COURSE-003", "Advanced Object-Oriented Design", "object-oriented design quality", [("COMP-CS-001", 0.8), ("CS-SKILL-OOPS", 0.9), ("COMP-CS-003", 0.55)], ["SOLID basics", "Composition", "Coupling", "Cohesion", "Refactoring"], 210, "Advanced"),
    _course("CS-COURSE-004", "Data Structures and Algorithms Fundamentals", "data structures and algorithms", [("COMP-CS-002", 0.9), ("CS-SKILL-DSA", 1.0), ("COMP-CS-003", 0.7)], ["Arrays", "Linked lists", "Stacks", "Queues", "Trees", "Complexity analysis"], 270, "Intermediate", "Prototype iGOT Catalog"),
    _course("CS-COURSE-005", "Arrays, Strings and Searching", "arrays, strings and search techniques", [("CS-SKILL-DSA", 0.92), ("COMP-CS-003", 0.65)], ["Arrays", "Strings", "Hashing", "Binary search", "Two pointers"], 180, "Intermediate"),
    _course("CS-COURSE-006", "Linked Lists, Stacks and Queues", "linear data structures", [("CS-SKILL-DSA", 0.9), ("COMP-CS-002", 0.65)], ["Linked lists", "Stacks", "Queues", "Deque", "Cycle detection"], 190, "Intermediate"),
    _course("CS-COURSE-007", "Trees, Graphs and Traversal", "tree and graph traversal", [("CS-SKILL-DSA", 0.88), ("COMP-CS-003", 0.7)], ["Binary trees", "DFS", "BFS", "Graphs", "Traversal"], 220, "Advanced"),
    _course("CS-COURSE-008", "Algorithmic Complexity and Problem Solving", "complexity analysis and problem solving", [("CS-SKILL-DSA", 0.82), ("CS-SKILL-PROBLEM", 1.0), ("COMP-CS-003", 0.9)], ["Big O", "Constraints", "Tradeoffs", "Recurrences", "Optimization"], 210, "Intermediate"),
    _course("CS-COURSE-009", "Competitive Problem Solving Fundamentals", "competitive programming foundations", [("CS-SKILL-PROBLEM", 0.95), ("CS-SKILL-DSA", 0.85)], ["Pattern recognition", "Greedy basics", "Dynamic programming", "Testing", "Edge cases"], 240, "Advanced"),
    _course("CS-COURSE-010", "Database Management Fundamentals", "database management fundamentals", [("COMP-CS-004", 0.85), ("CS-SKILL-DBMS", 1.0)], ["Relational model", "Keys", "SQL", "Joins", "Transactions"], 230, "Intermediate", "National Skills Learning Centre"),
    _course("CS-COURSE-011", "SQL and Relational Database Design", "SQL and relational database design", [("CS-SKILL-DBMS", 0.95), ("COMP-CS-004", 0.75)], ["SELECT queries", "Joins", "Aggregation", "Indexes", "Schema design"], 210, "Intermediate"),
    _course("CS-COURSE-012", "Database Normalization and Transactions", "normalization and transactions", [("CS-SKILL-DBMS", 0.9), ("COMP-CS-004", 0.8)], ["Functional dependencies", "Normal forms", "ACID", "Isolation", "Concurrency"], 200, "Advanced"),
    _course("CS-COURSE-013", "Operating Systems Fundamentals", "operating systems fundamentals", [("COMP-CS-004", 0.85), ("CS-SKILL-OS", 1.0)], ["Processes", "Threads", "Scheduling", "Memory", "File systems"], 240, "Intermediate", "Capacity Building Centre"),
    _course("CS-COURSE-014", "Processes, Threads and CPU Scheduling", "processes, threads and scheduling", [("CS-SKILL-OS", 0.92), ("COMP-CS-004", 0.7)], ["Process states", "Threads", "Synchronization", "CPU scheduling", "Deadlocks"], 180, "Intermediate"),
    _course("CS-COURSE-015", "Memory Management and File Systems", "memory management and file systems", [("CS-SKILL-OS", 0.88), ("COMP-CS-004", 0.7)], ["Paging", "Virtual memory", "Thrashing", "File allocation", "Caching"], 190, "Advanced"),
    _course("CS-COURSE-016", "Computer Networks Fundamentals", "computer networking fundamentals", [("COMP-CS-004", 0.65), ("COMP-CS-007", 0.55)], ["Network layers", "TCP/IP", "HTTP", "DNS", "Routing"], 210, "Intermediate"),
    _course("CS-COURSE-017", "Software Engineering Fundamentals", "software engineering fundamentals", [("COMP-CS-001", 0.65), ("COMP-CS-003", 0.7)], ["Requirements", "Testing", "Version control", "Design review", "Maintainability"], 180, "Beginner"),
    _course("CS-COURSE-018", "Web Development Fundamentals", "web development fundamentals", [("COMP-CS-007", 1.0), ("CS-SKILL-WEB", 1.0), ("COMP-CS-001", 0.55)], ["HTML", "CSS", "JavaScript", "Browser", "Client-server"], 240, "Beginner", "Digital Learning Academy"),
    _course("CS-COURSE-019", "Modern Frontend Web Development", "modern frontend development", [("COMP-CS-007", 0.9), ("CS-SKILL-WEB", 0.85)], ["React basics", "State", "Routing", "API calls", "Responsive UI"], 260, "Intermediate"),
    _course("CS-COURSE-020", "Backend Development Fundamentals", "backend API development", [("COMP-CS-007", 0.9), ("CS-SKILL-API", 1.0), ("CS-SKILL-DBMS", 0.55)], ["REST APIs", "Validation", "Persistence", "Auth concepts", "Testing"], 250, "Intermediate"),
    _course("CS-COURSE-021", "Android Development with Kotlin", "Android application development with Kotlin", [("COMP-CS-006", 1.0), ("CS-SKILL-ANDROID", 1.0), ("COMP-CS-001", 0.55)], ["Kotlin basics", "Activity lifecycle", "Layouts", "State", "Navigation"], 270, "Intermediate"),
    _course("CS-COURSE-022", "Android UI and Jetpack Compose", "Android UI with Jetpack Compose", [("COMP-CS-006", 0.9), ("CS-SKILL-COMPOSE", 1.0), ("CS-SKILL-ANDROID", 0.75)], ["Composable functions", "State", "Lists", "Themes", "Navigation"], 230, "Advanced"),
    _course("CS-COURSE-023", "Artificial Intelligence Fundamentals", "artificial intelligence fundamentals", [("COMP-CS-005", 0.9), ("CS-SKILL-ML", 0.75)], ["AI concepts", "Search", "Knowledge representation", "Agents", "Ethics"], 200, "Beginner"),
    _course("CS-COURSE-024", "Machine Learning Fundamentals", "machine learning fundamentals", [("COMP-CS-005", 1.0), ("CS-SKILL-ML", 1.0), ("CS-SKILL-MODEL-EVAL", 0.8)], ["Features", "Labels", "Training", "Evaluation", "Overfitting"], 260, "Intermediate", "National Skills Learning Centre"),
    _course("CS-COURSE-025", "Data Analysis with Python", "data analysis with Python", [("COMP-CS-005", 0.7), ("COMP-CS-001", 0.55)], ["Python data structures", "Pandas", "Cleaning", "Visualization", "Summaries"], 240, "Beginner"),
]


COURSE_CATALOG = STAT_COURSES + CS_COURSES


def seed_course_catalog(db: Session):
    now = datetime.utcnow()
    for item in COURSE_CATALOG:
        course_values = {key: value for key, value in item.items() if key not in {"topics", "outcomes", "modules", "mappings"}}
        existing = db.get(Course, item["course_id"])
        if existing:
            for key, value in course_values.items():
                setattr(existing, key, value)
            existing.updated_at = now
        else:
            db.add(Course(**course_values, created_at=now, updated_at=now))

        for model in [CourseCompetency, CourseTopic, CourseLearningOutcome, CourseModule]:
            db.query(model).filter(model.course_id == item["course_id"]).delete()

        for competency_id, relevance_score in item["mappings"]:
            db.add(CourseCompetency(course_id=item["course_id"], competency_id=competency_id, relevance_score=relevance_score))
        for topic in item["topics"]:
            db.add(CourseTopic(course_id=item["course_id"], topic_name=topic))
        for index, outcome in enumerate(item["outcomes"], start=1):
            db.add(CourseLearningOutcome(course_id=item["course_id"], outcome_text=outcome, sequence_order=index))
        for index, (title, duration, content_type) in enumerate(item["modules"], start=1):
            db.add(CourseModule(course_id=item["course_id"], module_title=title, sequence_order=index, duration_minutes=duration, content_type=content_type))
