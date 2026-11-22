from pathlib import Path
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT

OUT = Path(__file__).resolve().parents[1]
doc = Document()
s = doc.sections[0]
s.page_width, s.page_height = Inches(8.27), Inches(11.69)
s.top_margin = s.bottom_margin = Inches(.65)
s.left_margin = s.right_margin = Inches(.78)

for style in doc.styles:
    for border in list(style.element.iter(qn('w:pBdr'))):
        border.getparent().remove(border)
for name, size in [('Normal', 11), ('Title', 23), ('Subtitle', 10), ('Heading 1', 15)]:
    st = doc.styles[name]
    st.font.name = 'Calibri'
    st.font.size = Pt(size)
    st.font.color.rgb = RGBColor(0, 0, 0)
    fonts = st.element.get_or_add_rPr().get_or_add_rFonts()
    for attr in list(fonts.attrib):
        if 'Theme' in attr:
            del fonts.attrib[attr]
    fonts.set(qn('w:ascii'), 'Calibri')
    fonts.set(qn('w:hAnsi'), 'Calibri')
    st.paragraph_format.space_after = Pt(7)
doc.styles['Normal'].paragraph_format.line_spacing = 1.1
doc.styles['Heading 1'].font.bold = True
doc.styles['Heading 1'].paragraph_format.space_before = Pt(13)
doc.styles['Heading 1'].paragraph_format.space_after = Pt(8)
doc.styles['Title'].font.bold = True
doc.styles['Title'].paragraph_format.line_spacing = 1.0
doc.styles['Title'].paragraph_format.space_after = Pt(5)

doc.add_paragraph('Subject Agnostic\nAI Learning Companion', 'Title')
p = doc.add_paragraph('PROJECT SYNOPSIS', 'Subtitle')
p.paragraph_format.space_after = Pt(7)

def heading(t): doc.add_paragraph(t, 'Heading 1')
def para(t): return doc.add_paragraph(t)
def block(label, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(9)
    p.add_run(label + '\n').bold = True
    p.add_run(text)
    p.paragraph_format.keep_together = True

heading('01  Problem Statement')
para('A student struggling with graph traversal may actually need help with queues or recursion. A quiz score can show poor performance, but it rarely explains where the difficulty began. Repeating the same chapter may leave that gap untouched.')
para('Students already have access to notes, videos and AI explanations. The harder task is deciding what to study next and when to move ahead. We propose a learning companion that tracks understanding topic by topic and uses prerequisite relationships to guide those decisions.')

heading('02  Proposed Solution')
para('The system combines a knowledge graph, a learner model and a pretrained language model. The graph connects concepts, the learner model selects the next step, and the language model will prepare the teaching content.')
block('1  Map the subject', 'Use the syllabus or study material to suggest topics and prerequisite links for review. DSA is the first domain; its current topic graph is predefined.')
block('2  Check what the student understands', 'Start with an adaptive diagnostic. The prototype selects 15 questions from a bank of 100 DSA questions, records response time and uses correctness, difficulty and confidence to update learner estimates.')
block('3  Trace the learning gap', 'Check a weak topic alongside its prerequisites. For graph algorithms, this may mean checking queues and recursion first. A guessed answer receives little weight, and an untested topic stays unassessed.')
block('4  Choose a useful next step', 'Build an ordered roadmap that recommends learning, brief revision or another knowledge check. Topics with sufficient mastery evidence are marked as covered.')
block('5  Teach and reassess', 'Add AI explanations and practice guided by the learner model, then use topic tests to update the path. Syllabus extraction and AI teaching are planned extensions to the working diagnostic and roadmap.')

doc.add_page_break()
heading('03  Objectives')
for lead, text in [
    ('Understand the learner', 'Maintain topic-wise ability and mastery estimates rather than relying on one overall score.'),
    ('Find missing foundations', 'Use prerequisite links to identify earlier concepts that may be blocking progress.'),
    ('Make the next step clear', 'Recommend a lesson, revision or verification, with a visible reason for the choice.'),
    ('Adapt after practice', 'Use fresh assessment evidence to revise the learning path and guide AI teaching.'),
    ('Test beyond one subject', 'Evaluate the DSA prototype and use a small OS or DBMS example to check whether the design can support other subjects.'),
]:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(9)
    p.add_run(lead + '. ').bold = True
    p.add_run(text)

heading('04  Tech Stack')
table = doc.add_table(rows=1, cols=3)
table.alignment = WD_TABLE_ALIGNMENT.CENTER
table.autofit = False
widths = [1.05, 2.06, 3.60]
for c, w in zip(table.columns, widths): c.width = Inches(w)
for c, w, text in zip(table.rows[0].cells, widths, ['Layer', 'Technology', 'Role in the project']):
    c.width = Inches(w)
    c.text = text
rows = [
    ('Interface', 'React 18, Vite, Tailwind CSS, React Router', 'Assessment, profile, results and roadmap screens.'),
    ('Graph view', 'React Flow', 'Displays topics, prerequisites and learner progress.'),
    ('API', 'Python, FastAPI, Pydantic, Uvicorn', 'Runs assessment and roadmap services; validates data exchanged with the interface.'),
    ('Storage', 'SQLite, SQLAlchemy', 'Stores questions, responses, mastery states and topic relationships in relational tables.'),
    ('Learner model', 'Item Response Theory and Bayesian Knowledge Tracing', 'Estimates ability and topic mastery. Confidence weighting reduces the influence of guesses.'),
    ('Path planning', 'Prerequisite traversal and dependency ordering', 'Places foundations before dependent topics and prioritizes learning gaps.'),
    ('AI teaching\nPlanned', 'Pretrained LLM through an API', 'Interprets a syllabus and prepares explanations and practice from learner-model instructions.'),
    ('Verification', 'Pytest, HTTPX', 'Checks assessment behavior, confidence handling and roadmap ordering.'),
]
for row in rows:
    cells = table.add_row().cells
    for c, w, text in zip(cells, widths, row):
        c.width = Inches(w)
        c.text = text

for ri, row in enumerate(table.rows):
    trpr = row._tr.get_or_add_trPr()
    trpr.append(OxmlElement('w:cantSplit'))
    if ri == 0: trpr.append(OxmlElement('w:tblHeader'))
    for ci, cell in enumerate(row.cells):
        cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
        pr = cell._tc.get_or_add_tcPr()
        shade = OxmlElement('w:shd')
        shade.set(qn('w:fill'), '23374D' if ri == 0 else ('F1F4F7' if ri % 2 else 'FFFFFF'))
        pr.append(shade)
        margins = OxmlElement('w:tcMar')
        for side in ['top', 'left', 'bottom', 'right']:
            el = OxmlElement('w:' + side)
            el.set(qn('w:w'), '100')
            el.set(qn('w:type'), 'dxa')
            margins.append(el)
        pr.append(margins)
        borders = OxmlElement('w:tcBorders')
        for side in ['top', 'left', 'bottom', 'right']:
            el = OxmlElement('w:' + side)
            el.set(qn('w:val'), 'single')
            el.set(qn('w:sz'), '4')
            el.set(qn('w:color'), 'D9D9D9')
            borders.append(el)
        pr.append(borders)
        for p in cell.paragraphs:
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.02
            for r in p.runs:
                r.font.size = Pt(10)
                r.font.bold = ri == 0 or ci == 0
                r.font.color.rgb = RGBColor.from_string('FFFFFF' if ri == 0 else '000000')

doc.core_properties.title = 'Subject Agnostic AI Learning Companion Project Synopsis'
doc.core_properties.author = ''
target = OUT / 'Adaptive_AI_Learning_Companion_Synopsis_Revised.docx'
doc.save(target)
print(target)
