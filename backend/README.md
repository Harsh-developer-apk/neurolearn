# DSA diagnostic

The active diagnostic covers Data Structures and Algorithms using profile `PROFILE-DSA`. Each live or demo assessment still has a 15-question budget. Previous Computer Science assessments remain stored separately and do not initialize DSA mastery or ability.

## Question bank

`app/seed/dsa_question_bank.py` contains 100 distinct questions using the existing `q()` schema: IDs, competency and skill mappings, question type, cognitive level, difficulty, four options, correct options, explanation and misconception tags.

There are 10 questions per topic:

- Time and space complexity
- Arrays and strings
- Linked lists
- Stacks and queues
- Hashing
- Searching and sorting
- Trees and heaps
- Graph algorithms
- Recursion and backtracking
- Greedy and dynamic programming

Each topic includes basic, intermediate and advanced items. The difficulty values are authored initial IRT estimates and can later be calibrated using response data.

`app/seed/dsa_curriculum.py` defines the five competency groups, ten topic skills, required prerequisites and suggested study order. The graph labels these two relationship types separately. Suggested order guides the learning sequence without becoming a mandatory readiness requirement. Unassessed topics remain visible in the learner graph with no mastery estimate.

## Learning path

The roadmap uses a dependency-respecting ordering. Prerequisites and suggested preceding topics come before dependent topics; priority chooses between eligible topics. Larger downstream gaps increase the priority of foundations that prepare the learner for those topics.

Each step recommends learning, brief revision or verification. Topics at their target with sufficient evidence appear under Already Covered and are excluded from repeat lessons. Mastery of at least 55% suggests revision when the evidence is sufficient; lower mastery suggests learning. Missing, uncertain or guessing-only evidence recommends a knowledge check before choosing a lesson.

Readiness checks all required prerequisite ancestors, not just immediate parents. A prerequisite is ready when mastery is at least 65%, its evidence status is sufficient and it has at least two effective attempts. This readiness threshold is separate from the 75% learning target. Suggested study order does not affect the readiness threshold. The next step is selected from currently available topics, and the path is recalculated whenever new diagnostic evidence is available.

## Confidence weighting

Correct answers at confidence 1 (Just guessing) do not increase theta. Incorrect guesses receive 5% of the usual theta adjustment. Both correct and incorrect guesses receive 5% of the usual BKT mastery adjustment, still count toward the 15-question budget and retain their actual correctness in the score.

Guessing responses do not count toward effective evidence or demonstrate higher-level understanding. They cannot establish sufficient mastery or prerequisite readiness and are not interpreted as misconception signals. Confidence 2 receives half the normal update and counts as half an effective attempt. Confidence 3 through 5 receive the same standard weight, so reporting higher confidence does not earn extra ability credit.

These rules apply to new response updates. Previously saved theta and BKT values are retained; graph evidence classification uses the saved confidence values. Weighting and readiness thresholds are explicit prototype policies that can be evaluated and calibrated with response data.

## Run and verify

From the backend directory, install `requirements.txt`, then run `python -m uvicorn app.main:app --reload`. Startup seeds the DSA curriculum and question bank into `learning.db` by default; `DATABASE_URL` overrides its location.

Run `python -m pytest -q` to check question coverage, dependency ordering, readiness, learning actions, confidence weighting, 15-question diagnostics, live/demo results and separation from historical Computer Science evidence.
