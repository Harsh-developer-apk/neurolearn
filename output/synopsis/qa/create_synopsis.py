from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

OUT = Path(__file__).resolve().parents[1]
doc = Document()
s = doc.sections[0]
s.page_width, s.page_height = Inches(8.27), Inches(11.69)
s.top_margin = s.bottom_margin = Inches(0.75)
s.left_margin = s.right_margin = Inches(0.85)
normal = doc.styles['Normal']
normal.font.name = 'Times New Roman'
normal.font.size = Pt(12)
normal.paragraph_format.line_spacing = 1.12
normal.paragraph_format.space_after = Pt(7)
for name in ['Title', 'Heading 1']:
    st = doc.styles[name]
    st.font.name = 'Times New Roman'
    st.font.color.rgb = RGBColor(0, 0, 0)
    st.font.size = Pt(16 if name == 'Title' else 13)
    st.font.bold = True
    st.paragraph_format.space_before = Pt(9)
    st.paragraph_format.space_after = Pt(7)

for st in doc.styles:
    for border in list(st.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
for name in ['Normal', 'Title', 'Heading 1']:
    fonts = doc.styles[name].element.get_or_add_rPr().get_or_add_rFonts()
    for attr in list(fonts.attrib):
        if 'Theme' in attr:
            del fonts.attrib[attr]
    fonts.set(qn('w:ascii'), 'Times New Roman')
    fonts.set(qn('w:hAnsi'), 'Times New Roman')

title = doc.add_paragraph('Subject Agnostic AI Learning Companion', 'Title')
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub = doc.add_paragraph('Project Synopsis')
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub.paragraph_format.space_after = Pt(9)

def heading(t): doc.add_paragraph(t, 'Heading 1')
def para(t): doc.add_paragraph(t)
def item(label, text):
    p = doc.add_paragraph()
    p.add_run(label + ' ').bold = True
    p.add_run(text)

heading('Problem Statement')
para('Students studying the same subject often struggle for different reasons. A student may find graph traversal difficult because queues or recursion are unclear, while another may understand these prerequisites but make mistakes in applying the algorithm. A total quiz score does not show this difference. Following the same chapter sequence or repeating the entire topic can therefore leave the actual learning gap unresolved.')
para('Online notes, videos and AI chatbots make explanations readily available, but students still have to decide what to study, which earlier concepts to revise and whether they are ready to move ahead. A correct answer may also come from guessing rather than understanding. Our project addresses the need for a system that maintains a topic-wise picture of the learner and uses it to guide diagnosis, teaching and revision.')

heading('Proposed Solution')
para('We propose a web-based learning companion that combines a learner model with a knowledge graph and a pretrained language model. The knowledge graph represents topics and their prerequisite relationships. The learner model estimates what the student understands and decides the next learning step. The language model will provide explanations, examples and practice questions according to that decision.')
para('The intended workflow begins with a student profile and syllabus or study material. The language model will suggest topics and prerequisite links for review before they are used. A diagnostic assessment then gathers evidence about the student. The current DSA prototype uses a 15-question adaptive diagnostic drawn from 100 questions across ten topics. It records correctness, response time and reported confidence. Question selection considers difficulty and the evidence already collected, while confidence affects how strongly answers update ability and mastery estimates.')
para('After assessment, the system checks weak topics alongside their prerequisites and prepares an ordered roadmap. Each topic is assigned an action such as learning, brief revision or a further knowledge check. Untested topics remain marked as unassessed. For example, difficulty with graph algorithms can lead the system to check queues and recursion before recommending more graph practice. The proposed teaching stage will explain the selected concept, conduct a topic mastery test and use the new evidence to revise the path.')
para('DSA is the first implementation domain. Syllabus-based graph creation and AI teaching are planned extensions to the existing diagnostic and roadmap, with small Operating Systems or DBMS examples proposed to check whether the design can support other subjects.')

doc.add_page_break()
heading('Objectives')
for label, text in [
    ('1.', 'Build a topic-wise learner profile that uses answer correctness, question difficulty and confidence, while retaining response time for further analysis.'),
    ('2.', 'Identify weak concepts and examine their prerequisite chain so that the recommended starting point addresses the likely source of difficulty.'),
    ('3.', 'Create an adaptive learning path that separates topics needing a lesson, revision or more assessment, and avoids repeating topics supported by sufficient mastery evidence.'),
    ('4.', 'Connect the learner model to a pretrained language model for focused explanations and practice based on the selected topic and missing prerequisites.'),
    ('5.', 'Update the learner state after topic tests and display the reasoning behind recommendations through the knowledge graph and roadmap.'),
    ('6.', 'Evaluate the DSA prototype through assessment consistency, prerequisite ordering and changes in topic-test performance, then check portability with a small second-subject example.'),
]: item(label, text)

heading('Tech Stack')
item('Frontend', 'React 18 with Vite provides the assessment interface, learner profile, results and roadmap screens. Tailwind CSS handles styling, React Router manages navigation and React Flow displays topics and prerequisite connections.')
item('Backend', 'Python with FastAPI exposes the assessment, learner-state and roadmap APIs. Pydantic validates request and response data, and Uvicorn runs the API server.')
item('Data storage', 'SQLite stores profiles, questions, assessment responses, mastery states and prerequisite relationships. SQLAlchemy maps these records to Python models. The topic graph is currently stored through relational tables.')
item('Learner modeling', 'A one-parameter Item Response Theory model estimates ability against question difficulty. Bayesian Knowledge Tracing updates mastery estimates for individual skills. Confidence weighting reduces the effect of guesses, and prerequisite traversal with dependency-based ordering produces the roadmap. These prototype parameters will need evaluation with learner data.')
item('Proposed AI integration', 'A pretrained language model accessed through an API, such as Gemini or an OpenAI model, will assist with syllabus interpretation and generate learning content from learner-model instructions. The current code does not yet include this integration.')
item('Verification', 'Pytest and HTTPX support backend checks for assessment behavior, confidence weighting, evidence handling and prerequisite-aware roadmap generation.')

doc.core_properties.title = 'Subject Agnostic AI Learning Companion Project Synopsis'
doc.core_properties.subject = 'Project synopsis'
doc.core_properties.author = ''
doc.core_properties.keywords = 'learner modeling, knowledge graphs, adaptive assessment, DSA'
path = OUT / 'Adaptive_AI_Learning_Companion_Synopsis.docx'
doc.save(path)
print(path)
print('Words:', sum(len(p.text.split()) for p in doc.paragraphs))
