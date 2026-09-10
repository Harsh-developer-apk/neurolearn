import json

from sqlalchemy.orm import Session

from app.models import (
    Activity,
    ActivityCompetency,
    AssessmentQuestion,
    Competency,
    Department,
    Organization,
    Position,
    Profile,
    ProfileActivity,
    ProfileDesiredCompetency,
    ProfileTraining,
    Role,
    RoleActivity,
    SkillNode,
    SkillPrerequisite,
    TrainingCatalog,
)
from app.seed.question_bank import CS_QUESTION_BANK, PHASE3_QUESTION_BANK


def upsert(db: Session, model, key_name: str, values: dict):
    existing = db.get(model, values[key_name])
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        return existing

    item = model(**values)
    db.add(item)
    return item


def ensure_link(db: Session, model, filters: dict, values: dict | None = None):
    query = db.query(model)
    for key, value in filters.items():
        query = query.filter(getattr(model, key) == value)

    existing = query.first()
    if existing:
        return existing

    item = model(**filters, **(values or {}))
    db.add(item)
    return item


def upsert_by_field(db: Session, model, field_name: str, values: dict):
    existing = db.query(model).filter(getattr(model, field_name) == values[field_name]).first()
    if existing:
        for key, value in values.items():
            setattr(existing, key, value)
        return existing

    item = model(**values)
    db.add(item)
    return item


def seed_database(db: Session):
    upsert(db, Organization, "organization_id", {
        "organization_id": "ORG001",
        "name": "Ministry of Statistics and Programme Implementation",
    })

    upsert(db, Department, "department_id", {
        "department_id": "DEP001",
        "organization_id": "ORG001",
        "name": "National Statistical Office",
    })

    upsert(db, Position, "position_id", {
        "position_id": "POS001",
        "department_id": "DEP001",
        "designation": "Deputy Director",
    })

    upsert(db, Role, "role_id", {
        "role_id": "ROLE001",
        "name": "Statistical Survey Management",
        "description": "Manages statistical survey design, sampling, validation and reporting activities.",
    })

    activities = [
        ("ACT001", "Survey Design", "Plans survey objectives, questionnaires and data collection structure."),
        ("ACT002", "Sampling", "Selects sampling methods and frames for statistical surveys."),
        ("ACT003", "Data Validation", "Checks submitted data for completeness, consistency and quality."),
        ("ACT004", "Statistical Reporting", "Prepares statistical tables, reports, indicators and metadata."),
        ("ACT005", "Team Supervision", "Coordinates field teams, analysts and reporting timelines."),
    ]
    for activity_id, name, description in activities:
        upsert(db, Activity, "activity_id", {
            "activity_id": activity_id,
            "name": name,
            "description": description,
        })
        ensure_link(db, RoleActivity, {"role_id": "ROLE001", "activity_id": activity_id})

    competencies = [
        ("COMP001", "Survey Design", "Ability to design survey objectives, instruments and collection plans.", "Statistical"),
        ("COMP002", "Sampling", "Ability to select samples, frames and sampling methods.", "Statistical"),
        ("COMP003", "Data Quality", "Ability to validate data and apply quality checks.", "Statistical"),
        ("COMP004", "Statistical Analysis", "Ability to summarize, interpret and report statistical evidence.", "Statistical"),
        ("COMP005", "Metadata Standards", "Ability to document variables, classifications and statistical metadata.", "Governance"),
        ("COMP006", "Python Programming", "Ability to use Python for data handling and analysis.", "Technical"),
        ("COMP007", "Machine Learning", "Ability to understand and apply basic machine learning methods.", "Technical"),
        ("COMP008", "Advanced Survey Design", "Ability to handle complex survey design decisions and tradeoffs.", "Statistical"),
        ("COMP009", "Team Supervision", "Ability to coordinate teams, review work and manage execution.", "Managerial"),
    ]
    for competency_id, name, description, category in competencies:
        upsert(db, Competency, "competency_id", {
            "competency_id": competency_id,
            "name": name,
            "description": description,
            "category": category,
        })

    cs_competencies = [
        ("COMP-CS-001", "Coding Skills", "Ability to understand, write, debug and reason about software programs.", "Computer Science"),
        ("COMP-CS-002", "Logical Reasoning", "Ability to reason about conditions, sequences, relationships and computational logic.", "Computer Science"),
        ("COMP-CS-003", "Problem Solving", "Ability to decompose programming problems and develop correct algorithmic solutions.", "Computer Science"),
        ("COMP-CS-004", "Analytical Thinking", "Ability to analyze computational problems, tradeoffs, complexity and system behavior.", "Computer Science"),
        ("COMP-CS-005", "AI/ML", "Ability to understand basic machine learning concepts and model behavior.", "Computer Science"),
        ("COMP-CS-006", "Android Development", "Ability to build Android applications using modern Android development practices.", "Computer Science"),
        ("COMP-CS-007", "Web Development", "Ability to build web applications and backend APIs.", "Computer Science"),
    ]
    for competency_id, name, description, category in cs_competencies:
        upsert(db, Competency, "competency_id", {
            "competency_id": competency_id,
            "name": name,
            "description": description,
            "category": category,
        })

    activity_competencies = [
        ("ACT001", "COMP001", 3),
        ("ACT001", "COMP004", 2),
        ("ACT002", "COMP002", 3),
        ("ACT002", "COMP004", 2),
        ("ACT003", "COMP003", 3),
        ("ACT004", "COMP004", 3),
        ("ACT004", "COMP005", 2),
        ("ACT005", "COMP009", 2),
    ]
    for activity_id, competency_id, target_level in activity_competencies:
        ensure_link(
            db,
            ActivityCompetency,
            {"activity_id": activity_id, "competency_id": competency_id},
            {"target_level": target_level},
        )

    skill_nodes = [
        ("SKILL001", "COMP001", "Survey Objectives", "Defines measurable survey goals, target population and expected outputs.", 1),
        ("SKILL002", "COMP001", "Questionnaire Design", "Creates clear questions, response options and survey instruments.", 2),
        ("SKILL003", "COMP001", "Sampling Design", "Connects survey objectives with sampling approach and field design.", 2),
        ("SKILL004", "COMP001", "Survey Bias", "Identifies coverage, response, measurement and selection bias.", 2),
        ("SKILL005", "COMP002", "Population and Sample", "Distinguishes population, sample, unit and respondent in a survey context.", 1),
        ("SKILL006", "COMP002", "Sampling Frame", "Understands frame coverage, frame errors and preparation of sampling frames.", 1),
        ("SKILL007", "COMP002", "Simple Random Sampling", "Applies simple random sampling concepts and selection logic.", 2),
        ("SKILL008", "COMP002", "Stratified Sampling", "Uses strata and allocation to improve sampling design.", 2),
        ("SKILL009", "COMP003", "Missing Data", "Recognizes missing values and understands their impact on data quality.", 1),
        ("SKILL010", "COMP003", "Data Validation Rules", "Defines validation checks for completeness, range and consistency.", 2),
        ("SKILL011", "COMP003", "Error Detection", "Finds inconsistent, duplicate, outlier and entry-error patterns.", 2),
        ("SKILL012", "COMP003", "Data Quality Indicators", "Uses quality indicators to summarize fitness and reliability of data.", 2),
        ("SKILL013", "COMP004", "Descriptive Statistics", "Computes and interprets measures such as mean, median, spread and frequency.", 1),
        ("SKILL014", "COMP004", "Inferential Statistics", "Understands estimation, uncertainty and drawing conclusions from samples.", 2),
        ("SKILL015", "COMP004", "Hypothesis Testing", "Applies basic test logic, significance and result interpretation.", 2),
        ("SKILL016", "COMP004", "Regression Basics", "Understands simple regression use cases and interpretation.", 3),
        ("SKILL017", "COMP005", "Metadata Concepts", "Understands how metadata supports discovery, reuse and governance.", 1),
        ("SKILL018", "COMP005", "Variable Metadata", "Documents labels, units, formats, codes and value meanings.", 1),
        ("SKILL019", "COMP005", "Statistical Classification", "Uses classifications and code lists in official statistics.", 2),
        ("SKILL020", "COMP005", "Metadata Documentation", "Prepares structured metadata documentation for datasets and outputs.", 2),
        ("SKILL021", "COMP006", "Python Basics", "Understands syntax, variables, control flow and basic program structure.", 1),
        ("SKILL022", "COMP006", "Python Data Structures", "Uses lists, dictionaries, tuples and sets for data handling tasks.", 1),
        ("SKILL023", "COMP006", "Functions and Modules", "Writes reusable functions and organizes code with modules.", 2),
        ("SKILL024", "COMP006", "Data Handling with Python", "Reads, cleans and transforms tabular data using Python libraries.", 2),
        ("SKILL025", "COMP007", "Machine Learning Concepts", "Understands features, labels, training, prediction and model use cases.", 1),
        ("SKILL026", "COMP007", "Data Preparation", "Prepares datasets through cleaning, encoding, splitting and scaling.", 2),
        ("SKILL027", "COMP007", "Supervised Learning", "Understands classification and regression with labeled data.", 2),
        ("SKILL028", "COMP007", "Model Evaluation", "Evaluates models using suitable metrics and validation methods.", 2),
        ("SKILL029", "COMP008", "Complex Survey Designs", "Understands complex designs involving clusters, strata and multiple stages.", 3),
        ("SKILL030", "COMP008", "Multi-stage Sampling", "Designs staged sampling plans across multiple selection levels.", 3),
        ("SKILL031", "COMP008", "Survey Weighting", "Understands weights, adjustment and representation in survey estimates.", 3),
        ("SKILL032", "COMP008", "Design Effect", "Interprets design effect and its impact on precision.", 3),
        ("SKILL033", "COMP009", "Team Coordination", "Coordinates people, timelines and communication across a survey team.", 1),
        ("SKILL034", "COMP009", "Work Allocation", "Assigns work based on task needs, capacity and timelines.", 2),
        ("SKILL035", "COMP009", "Performance Review", "Reviews work quality, progress and accountability.", 2),
        ("SKILL036", "COMP009", "Execution Monitoring", "Tracks execution status, risks and corrective actions.", 2),
    ]
    for skill_node_id, competency_id, name, description, difficulty_level in skill_nodes:
        upsert(db, SkillNode, "skill_node_id", {
            "skill_node_id": skill_node_id,
            "competency_id": competency_id,
            "name": name,
            "description": description,
            "difficulty_level": difficulty_level,
        })

    cs_skill_nodes = [
        ("CS-SKILL-OOPS", "COMP-CS-001", "OOPS", "Object-oriented programming concepts including encapsulation, inheritance, polymorphism and design relationships.", 2),
        ("CS-SKILL-DSA", "COMP-CS-002", "DSA", "Data structures, algorithms, complexity reasoning and algorithmic patterns.", 2),
        ("CS-SKILL-PROBLEM", "COMP-CS-003", "Algorithmic Problem Solving", "Decomposes programming problems, selects approaches and reasons about constraints.", 2),
        ("CS-SKILL-DBMS", "COMP-CS-004", "DBMS", "Relational data modeling, SQL reasoning, normalization, transactions and indexes.", 2),
        ("CS-SKILL-OS", "COMP-CS-004", "Operating Systems", "Processes, threads, scheduling, synchronization, memory management and deadlocks.", 2),
        ("CS-SKILL-ML", "COMP-CS-005", "Machine Learning Fundamentals", "Features, labels, model training and evaluation basics.", 2),
        ("CS-SKILL-MODEL-EVAL", "COMP-CS-005", "Model Evaluation", "Evaluates model behavior with suitable metrics and validation methods.", 2),
        ("CS-SKILL-ANDROID", "COMP-CS-006", "Android Fundamentals", "Android lifecycle, UI, state and application structure.", 1),
        ("CS-SKILL-COMPOSE", "COMP-CS-006", "Jetpack Compose", "Declarative Android UI development with Compose.", 2),
        ("CS-SKILL-WEB", "COMP-CS-007", "Web Fundamentals", "HTML, CSS, JavaScript and client-server web basics.", 1),
        ("CS-SKILL-API", "COMP-CS-007", "Backend/API Development", "REST APIs, backend request handling and persistence fundamentals.", 2),
    ]
    for skill_node_id, competency_id, name, description, difficulty_level in cs_skill_nodes:
        upsert(db, SkillNode, "skill_node_id", {
            "skill_node_id": skill_node_id,
            "competency_id": competency_id,
            "name": name,
            "description": description,
            "difficulty_level": difficulty_level,
        })

    db.query(SkillPrerequisite).delete()
    prerequisites = [
        ("SKILL002", "SKILL001"),
        ("SKILL003", "SKILL001"),
        ("SKILL004", "SKILL003"),
        ("SKILL006", "SKILL005"),
        ("SKILL007", "SKILL006"),
        ("SKILL008", "SKILL007"),
        ("SKILL010", "SKILL009"),
        ("SKILL011", "SKILL010"),
        ("SKILL012", "SKILL011"),
        ("SKILL014", "SKILL013"),
        ("SKILL015", "SKILL014"),
        ("SKILL016", "SKILL015"),
        ("SKILL018", "SKILL017"),
        ("SKILL019", "SKILL018"),
        ("SKILL020", "SKILL019"),
        ("SKILL022", "SKILL021"),
        ("SKILL023", "SKILL022"),
        ("SKILL024", "SKILL023"),
        ("SKILL026", "SKILL025"),
        ("SKILL027", "SKILL026"),
        ("SKILL028", "SKILL027"),
        ("SKILL029", "SKILL005"),
        ("SKILL029", "SKILL006"),
        ("SKILL030", "SKILL029"),
        ("SKILL031", "SKILL030"),
        ("SKILL032", "SKILL031"),
        ("SKILL034", "SKILL033"),
        ("SKILL035", "SKILL034"),
        ("SKILL036", "SKILL035"),
        ("CS-SKILL-PROBLEM", "CS-SKILL-DSA"),
        ("CS-SKILL-OS", "CS-SKILL-DSA"),
        ("CS-SKILL-MODEL-EVAL", "CS-SKILL-ML"),
        ("CS-SKILL-COMPOSE", "CS-SKILL-ANDROID"),
        ("CS-SKILL-API", "CS-SKILL-WEB"),
    ]
    for skill_node_id, prerequisite_skill_node_id in prerequisites:
        ensure_link(db, SkillPrerequisite, {
            "skill_node_id": skill_node_id,
            "prerequisite_skill_node_id": prerequisite_skill_node_id,
        })

    difficulty_to_b = {"Easy": -1.0, "Medium": 0.0, "Hard": 1.0}
    questions = [
        ("Q001", "SKILL001", "COMP001", "What is the first step in designing a statistical survey?", "Preparing charts", "Defining clear survey objectives", "Writing the final report", "Choosing a font", "B", "Easy", "Survey objectives define what information the survey must collect and why."),
        ("Q002", "SKILL002", "COMP001", "Which feature makes a questionnaire question better?", "It asks two things at once", "It uses unclear technical words", "It is clear and asks one idea", "It hides the response options", "C", "Easy", "A good question is clear, focused and easy for the respondent to answer."),
        ("Q003", "SKILL003", "COMP001", "Sampling design mainly decides what?", "How units are selected for observation", "Which colors are used in a report", "How passwords are stored", "Which programming language is used", "A", "Medium", "Sampling design connects survey objectives with how respondents or units are selected."),
        ("Q004", "SKILL004", "COMP001", "Which situation can create survey bias?", "Every selected unit has equal chance to respond", "Some groups are systematically missed", "The report has a title", "The sample is documented", "B", "Medium", "Bias can occur when important groups are missed or measured unfairly."),
        ("Q005", "SKILL005", "COMP002", "Which statement best describes a sample in a statistical survey?", "The complete population of interest", "A subset selected from the population", "Only the survey questionnaire", "The final statistical report", "B", "Easy", "A sample is a subset of the population selected for observation and analysis."),
        ("Q006", "SKILL006", "COMP002", "What is a sampling frame?", "A list or source from which sample units are selected", "A chart type", "A software installation file", "A final report summary", "A", "Easy", "The sampling frame provides the practical list or source used for selecting sample units."),
        ("Q007", "SKILL007", "COMP002", "In simple random sampling, each unit should have what?", "A known and equal chance of selection", "A different questionnaire", "A guaranteed response", "No identification", "A", "Medium", "Simple random sampling gives each unit a known and equal selection chance."),
        ("Q008", "SKILL008", "COMP002", "Why is stratified sampling used?", "To remove all data cleaning", "To split the population into meaningful groups before sampling", "To avoid defining the population", "To make every report shorter", "B", "Medium", "Stratification helps represent important groups more reliably."),
        ("Q009", "SKILL008", "COMP002", "A hard part of stratified sampling is deciding what?", "The database password", "The strata and allocation across strata", "The logo size", "The file extension", "B", "Hard", "Stratified sampling requires well-defined strata and allocation decisions."),
        ("Q010", "SKILL009", "COMP003", "What does missing data mean?", "A value is unavailable where it should have been recorded", "A chart is colorful", "A report has too many pages", "A sample is large", "A", "Easy", "Missing data is expected information that was not captured."),
        ("Q011", "SKILL010", "COMP003", "Which is an example of a validation rule?", "Age cannot be negative", "The title must be long", "The logo must be blue", "All users must skip questions", "A", "Easy", "Validation rules check whether values are complete, valid and consistent."),
        ("Q012", "SKILL011", "COMP003", "Which record is most likely an error?", "Age 35", "Age 42", "Age -5", "Age 60", "C", "Easy", "Negative age is outside a valid range and should be flagged."),
        ("Q013", "SKILL012", "COMP003", "What does a data quality indicator summarize?", "Fitness and reliability of data", "Only team attendance", "Only website traffic", "Only font style", "A", "Medium", "Quality indicators summarize issues such as completeness, validity and consistency."),
        ("Q014", "SKILL013", "COMP004", "Which measure is a descriptive statistic?", "Mean", "API token", "Digital signature", "Sampling frame only", "A", "Easy", "The mean summarizes a dataset and is a descriptive statistic."),
        ("Q015", "SKILL014", "COMP004", "Inferential statistics is mainly used to do what?", "Draw conclusions about a population from sample data", "Design a website", "Encrypt documents", "Create a department name", "A", "Medium", "Inference uses sample evidence to estimate or test claims about a population."),
        ("Q016", "SKILL015", "COMP004", "A hypothesis test usually evaluates what?", "Whether data supports a claim about a population", "Whether a button is visible", "Whether a report has images", "Whether a file is compressed", "A", "Medium", "Hypothesis testing evaluates evidence for or against a statistical claim."),
        ("Q017", "SKILL016", "COMP004", "Regression is commonly used to study what?", "Relationship between variables", "Only missing file names", "Only survey titles", "Only user passwords", "A", "Hard", "Regression models relationships between an outcome and one or more predictors."),
        ("Q018", "SKILL017", "COMP005", "Why is metadata important?", "It explains data meaning, structure and context", "It replaces all data", "It removes the need for validation", "It guarantees every answer is correct", "A", "Easy", "Metadata helps people understand, reuse and govern data."),
        ("Q019", "SKILL018", "COMP005", "Variable metadata should usually include what?", "Variable label, unit and code meanings", "Only presentation color", "Only login time", "Only file size", "A", "Easy", "Variable metadata documents how each variable should be interpreted."),
        ("Q020", "SKILL019", "COMP005", "Statistical classifications help with what?", "Consistent grouping and reporting", "Random guessing", "Replacing surveys", "Deleting metadata", "A", "Medium", "Classifications support consistent categories across statistical outputs."),
        ("Q021", "SKILL021", "COMP006", "Which is a valid Python variable assignment?", "x = 10", "10 = x", "x == 10 always assigns", "print = x = ?", "A", "Easy", "Python uses name = value for assignment."),
        ("Q022", "SKILL022", "COMP006", "Which Python data structure stores key-value pairs?", "List", "Dictionary", "Tuple only", "String only", "B", "Easy", "A dictionary stores data as keys mapped to values."),
        ("Q023", "SKILL023", "COMP006", "Why are functions useful in Python?", "They make reusable blocks of logic", "They delete variables automatically", "They prevent all errors", "They only display images", "A", "Medium", "Functions package reusable logic and reduce repeated code."),
        ("Q024", "SKILL024", "COMP006", "Which task belongs to data handling with Python?", "Reading and cleaning tabular data", "Choosing office furniture", "Printing only one number", "Changing monitor brightness", "A", "Medium", "Data handling includes reading, cleaning and transforming data."),
        ("Q025", "SKILL025", "COMP007", "In machine learning, a feature is usually what?", "An input variable used by a model", "A final certificate", "A password rule", "A slide background", "A", "Easy", "Features are input variables used to train or run a model."),
        ("Q026", "SKILL026", "COMP007", "Why is data preparation important before model training?", "Raw data may contain missing, inconsistent or unusable values", "It removes the need for evaluation", "It guarantees perfect accuracy", "It replaces the model", "A", "Medium", "Prepared data improves model reliability and prevents avoidable errors."),
        ("Q027", "SKILL027", "COMP007", "Supervised learning requires what kind of data?", "Labeled examples", "No examples", "Only presentation slides", "Only encrypted files", "A", "Medium", "Supervised learning uses labeled examples to learn input-output patterns."),
        ("Q028", "SKILL028", "COMP007", "Why do we evaluate a machine learning model?", "To check how well it performs on relevant data", "To remove all features", "To rename the dataset", "To avoid training", "A", "Medium", "Evaluation measures whether a model performs well enough for its intended use."),
        ("Q029", "SKILL029", "COMP008", "A complex survey design may include what?", "Clusters, strata or multiple stages", "Only one respondent", "No sampling frame", "Only report headings", "A", "Hard", "Complex survey designs often combine clusters, strata and staged selection."),
        ("Q030", "SKILL030", "COMP008", "Multi-stage sampling means what?", "Selecting samples in more than one stage", "Asking only one question", "Sorting a spreadsheet", "Skipping all validation", "A", "Hard", "Multi-stage sampling selects units step by step across levels."),
        ("Q031", "SKILL031", "COMP008", "Survey weights are mainly used to help with what?", "Representing the population correctly in estimates", "Choosing a font", "Hiding missing data", "Deleting records", "A", "Hard", "Weights adjust survey estimates to better represent the target population."),
        ("Q032", "SKILL032", "COMP008", "Design effect is related to what?", "How the survey design affects estimate precision", "How a button looks", "How files are compressed", "How names are sorted", "A", "Hard", "Design effect reflects how a complex design changes statistical precision."),
        ("Q033", "SKILL033", "COMP009", "Team coordination mainly involves what?", "Aligning people, timelines and communication", "Writing random code", "Ignoring progress", "Deleting task lists", "A", "Easy", "Coordination keeps team members aligned on work, timing and communication."),
        ("Q034", "SKILL034", "COMP009", "Good work allocation should consider what?", "Task needs, staff capacity and deadlines", "Only alphabetical order", "Only personal preference", "Only report color", "A", "Medium", "Work allocation should match tasks with capacity and timelines."),
        ("Q035", "SKILL035", "COMP009", "Performance review helps a supervisor do what?", "Assess work quality and progress", "Avoid feedback", "Skip monitoring", "Remove accountability", "A", "Medium", "Performance review checks quality, progress and accountability."),
        ("Q036", "SKILL036", "COMP009", "Execution monitoring focuses on what?", "Tracking progress, risks and corrective actions", "Changing logos", "Avoiding schedules", "Only storing certificates", "A", "Medium", "Monitoring tracks whether work is moving as planned and where correction is needed."),
    ]
    questions = [(question, "PROFILE001") for question in PHASE3_QUESTION_BANK] + [(question, "PROFILE002") for question in CS_QUESTION_BANK]
    for question, question_profile_id in questions:
        options = {item["id"]: item["text"] for item in question["options"]}
        correct_options = question["correct_options"]
        irt_b = question["difficulty"]
        difficulty_label = "Basic" if irt_b < -0.25 else "Intermediate" if irt_b <= 0.75 else "Advanced"
        upsert_by_field(db, AssessmentQuestion, "question_id", {
            "question_id": question["question_id"],
            "profile_id": question_profile_id,
            "skill_node_id": question["skill_node_id"],
            "competency_id": question["competency_id"],
            "question_text": question["question_text"],
            "option_a": options["A"],
            "option_b": options["B"],
            "option_c": options["C"],
            "option_d": options["D"],
            "correct_option": correct_options[0],
            "difficulty": difficulty_label,
            "irt_b": irt_b,
            "question_type": question["question_type"],
            "cognitive_level": question["cognitive_level"],
            "correct_options": json.dumps(correct_options),
            "misconception_tags": json.dumps(question["misconception_tags"]),
            "explanation": question["explanation"],
        })

    trainings = [
        ("TRAIN001", "Fundamentals of Statistical Surveys", "iGOT Karmayogi", "Introduces survey planning and statistical survey workflows."),
        ("TRAIN002", "Introduction to Sampling Methods", "iGOT Karmayogi", "Covers sampling frame, random sampling and stratification basics."),
        ("TRAIN003", "Data Quality Management", "NSSTA", "Covers validation rules, missing data and data quality indicators."),
        ("TRAIN004", "Statistical Reporting Standards", "NSSTA", "Covers reporting practices and metadata requirements."),
    ]
    for training_id, title, provider, description in trainings:
        upsert(db, TrainingCatalog, "training_id", {
            "training_id": training_id,
            "title": title,
            "provider": provider,
            "description": description,
        })

    upsert(db, Profile, "id", {
        "id": "PROFILE001",
        "full_name": "Arjun Mehta",
        "preferred_language": "English",
        "organization_id": "ORG001",
        "department_id": "DEP001",
        "position_id": "POS001",
        "role_id": "ROLE001",
        "years_experience": 8,
        "highest_qualification": "M.Sc Statistics",
        "specialization": "Statistics",
    })

    upsert(db, Organization, "organization_id", {
        "organization_id": "ORG-CS-001",
        "name": "J.C. Bose University / Computer Science",
    })
    upsert(db, Department, "department_id", {
        "department_id": "DEP-CS-001",
        "organization_id": "ORG-CS-001",
        "name": "Computer Science",
    })
    upsert(db, Position, "position_id", {
        "position_id": "POS-CS-001",
        "department_id": "DEP-CS-001",
        "designation": "Computer Science Student",
    })
    upsert(db, Role, "role_id", {
        "role_id": "ROLE-CS-001",
        "name": "Software / Computer Science Learner",
        "description": "Builds foundations in programming, algorithms, systems, databases and software design.",
    })
    cs_activities = [
        ("ACT-CS-001", "Coding Practice", "Writes, debugs and reasons about software programs."),
        ("ACT-CS-002", "Algorithmic Reasoning", "Solves computational problems using data structures and algorithms."),
        ("ACT-CS-003", "Systems and Data Reasoning", "Analyzes databases, operating systems and computational tradeoffs."),
        ("ACT-CS-004", "Software Problem Solving", "Decomposes programming tasks and chooses suitable implementation approaches."),
    ]
    for activity_id, name, description in cs_activities:
        upsert(db, Activity, "activity_id", {
            "activity_id": activity_id,
            "name": name,
            "description": description,
        })
        ensure_link(db, RoleActivity, {"role_id": "ROLE-CS-001", "activity_id": activity_id})

    cs_activity_competencies = [
        ("ACT-CS-001", "COMP-CS-001", 3),
        ("ACT-CS-002", "COMP-CS-002", 3),
        ("ACT-CS-003", "COMP-CS-004", 3),
        ("ACT-CS-004", "COMP-CS-003", 3),
    ]
    for activity_id, competency_id, target_level in cs_activity_competencies:
        ensure_link(
            db,
            ActivityCompetency,
            {"activity_id": activity_id, "competency_id": competency_id},
            {"target_level": target_level},
        )

    upsert(db, Profile, "id", {
        "id": "PROFILE002",
        "full_name": "Arjun Mehta",
        "preferred_language": "English",
        "organization_id": "ORG-CS-001",
        "department_id": "DEP-CS-001",
        "position_id": "POS-CS-001",
        "role_id": "ROLE-CS-001",
        "years_experience": 2,
        "highest_qualification": "MCA",
        "specialization": "Computer Applications / Software Development",
    })

    for activity_id, _, _ in activities:
        ensure_link(db, ProfileActivity, {"profile_id": "PROFILE001", "activity_id": activity_id})

    for activity_id, _, _ in cs_activities:
        ensure_link(db, ProfileActivity, {"profile_id": "PROFILE002", "activity_id": activity_id})

    for training_id in ["TRAIN001", "TRAIN003"]:
        ensure_link(
            db,
            ProfileTraining,
            {"profile_id": "PROFILE001", "training_id": training_id},
            {"completion_status": "completed"},
        )

    desired_competencies = [
        ("COMP006", 3),
        ("COMP007", 2),
        ("COMP008", 3),
    ]
    for competency_id, target_level in desired_competencies:
        ensure_link(
            db,
            ProfileDesiredCompetency,
            {"profile_id": "PROFILE001", "competency_id": competency_id},
            {"target_level": target_level},
        )

    cs_desired_competencies = [
        ("COMP-CS-005", 2),
        ("COMP-CS-006", 2),
        ("COMP-CS-007", 2),
    ]
    for competency_id, target_level in cs_desired_competencies:
        ensure_link(
            db,
            ProfileDesiredCompetency,
            {"profile_id": "PROFILE002", "competency_id": competency_id},
            {"target_level": target_level},
        )

    db.commit()
