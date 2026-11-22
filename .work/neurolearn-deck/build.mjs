import fs from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {Presentation, PresentationFile} from '@oai/artifact-tool';

const ROOT='C:/Users/asus1/shukraniti';
const BUILD=ROOT+'/.work/neurolearn-deck';
const SKILL='C:/Users/asus1/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const RUNTIME='C:/Users/asus1/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES=RUNTIME+'/node/node_modules';
const {finalizePresentation}=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs').href);
const C={navy:'#102A3A',ivory:'#F4F1E9',teal:'#0F766E',amber:'#E8A247',ink:'#172E3A',muted:'#536771',pale:'#C5D6D9',white:'#FFFFFF'};
const FONT='Calibri';
const p=Presentation.create({slideSize:{width:1280,height:720}});
const fontPolicy={basis:'design',families:[FONT]};
function text(s,content,x,y,w,h,size=27,color=C.ink,bold=false){
 const t=s.shapes.add({geometry:'textbox',name:content.replace(/\n/g,' ').slice(0,70),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 t.text=content;
 t.text.style={fontSize:size,typeface:FONT,color,bold,alignment:'left',verticalAlignment:'top',autoFit:'none',wrap:'square',insets:0};
 return t;
}
function slide(title,n,dark=false){
 const s=p.slides.add(); s.background.fill=dark?C.navy:C.ivory;
 text(s,title,70,56,1138,77,46,dark?C.ivory:C.navy,true);
 text(s,'NEUROLEARN',70,666,450,24,16,dark?C.pale:C.muted,true);
 text(s,String(n).padStart(2,'0'),1160,663,48,29,19,dark?C.pale:C.muted);
 return s;
}
function note(s,body,source){s.speakerNotes.text=body+'\n\nSources: '+source;}
const synopsis='C:/Users/asus1/Downloads/project_synopsis.pdf';

// 1. Cover
{
 const s=p.slides.add();s.background.fill=C.navy;
 const art=await fs.readFile(BUILD+'/cover-art.png');
 s.images.add({blob:art.buffer.slice(art.byteOffset,art.byteOffset+art.byteLength),contentType:'image/png',alt:'An open book supporting a branching network of knowledge, conceptual illustration',fit:'contain',position:{left:736,top:30,width:520,height:650}});
 text(s,'MCA MINOR PROJECT',72,66,630,28,19,C.amber,true);
 text(s,'NeuroLearn',67,142,710,100,86,C.ivory,true);
 text(s,'Adaptive Learning Platform',72,248,675,58,38,C.ivory);
 text(s,'A learner model that identifies knowledge gaps\nand guides the next learning step.',72,333,660,92,28,C.pale);
 text(s,'Dhairya Verma  (25001602018)\nHarsh Sharma  (25001602025)\nAbhishek Sharma  (25001602003)',72,478,635,101,22,C.ivory);
 text(s,'Supervisor: Ms. Anshu Gulati',72,588,640,31,22,C.amber);
 text(s,'Department of Computer Applications\nJ.C. Bose University of Science and Technology, YMCA',72,641,670,54,18,C.pale);
 note(s,'NeuroLearn is a web-based adaptive learning companion. The current prototype focuses on Data Structures and Algorithms. The broader proposal combines the learner model, prerequisite knowledge graph and a pretrained language model for teaching.',synopsis+', page 1. Illustration generated for this presentation using the built-in image generation tool. Prompt: editorial 3D paper sculpture of a branching knowledge network growing from an open book, teal and ivory nodes with an amber path on a navy background, no text.');
}
// 2. Problem
{
 const s=slide('The problem with one overall score',2);
 text(s,'The same weak result can hide\ndifferent learning gaps.',70,170,1070,115,43,C.navy,true);
 text(s,'LEARNER A',70,332,490,30,21,C.teal,true);
 text(s,'Missing foundations',70,380,505,47,32,C.navy,true);
 text(s,'Graph traversal feels difficult because\nqueues or recursion are unclear.',70,443,505,94,28,C.muted);
 text(s,'LEARNER B',684,332,505,30,21,C.teal,true);
 text(s,'Difficulty applying the algorithm',684,380,520,47,32,C.navy,true);
 text(s,'The prerequisites are clear, but the\nstudent makes application mistakes.',684,443,520,94,28,C.muted);
 text(s,'Students need topic-level diagnosis and a reason for what to study next.',70,582,1130,56,28,C.teal,true);
 note(s,'A total quiz score does not explain whether a student needs prerequisite revision or practice applying a known algorithm. Repeating an entire chapter may leave the real gap unresolved. Correct answers can also come from guessing. These examples explain the motivation and do not report measured study outcomes.',synopsis+', page 2, Problem Statement.');
}
// 3. Solution
{
 const s=slide('How NeuroLearn guides learning',3);
 const rows=[
  ['01','Map the subject','A topic graph records the concepts and their prerequisite links.'],
  ['02','Diagnose understanding','An adaptive quiz gathers answers and confidence, and records time.'],
  ['03','Identify the gap','The learner model checks weak topics and earlier foundations.'],
  ['04','Recommend the next step','The roadmap selects learning, revision or a knowledge check.']
 ];
 rows.forEach((r,i)=>{const y=165+i*100;text(s,r[0],70,y,78,61,42,C.teal,true);text(s,r[1],170,y+1,410,42,30,C.navy,true);text(s,r[2],600,y+2,605,80,27,C.muted);});
 text(s,'15 questions per diagnostic',70,595,410,42,27,C.teal,true);
 text(s,'100 questions in the DSA bank',520,595,685,42,27,C.teal,true);
 note(s,'The first domain is DSA, with a predefined graph covering ten topics. The prototype selects a 15-question diagnostic from 100 authored questions. It stores response time, but the stated learner updates use correctness, difficulty and confidence. A dependency-respecting roadmap prioritizes gaps and marks topics as covered when evidence is sufficient. New diagnostic evidence recalculates the path. AI teaching and syllabus extraction remain planned extensions.',synopsis+', page 2. Repository: backend/README.md; backend/app/services/assessment_service.py; backend/app/services/roadmap_service.py.');
}
// 4. Intelligence
{
 const s=slide('The adaptive learner model',4,true);
 text(s,'IRT',70,169,500,82,65,C.amber,true);
 text(s,'Item Response Theory',70,258,515,43,31,C.ivory,true);
 text(s,'Estimates ability from correctness\nand question difficulty to support\nadaptive question selection.',70,327,520,133,28,C.pale);
 text(s,'BKT',690,169,500,82,65,C.amber,true);
 text(s,'Bayesian Knowledge Tracing',690,258,520,43,31,C.ivory,true);
 text(s,'Updates the probability of mastery\nfor each topic as the student\nanswers questions.',690,327,520,133,28,C.pale);
 text(s,'Evidence matters',70,513,400,43,31,C.ivory,true);
 text(s,'Guesses receive little weight. Untested topics remain unassessed.\nPrerequisite checks keep foundations ahead of dependent topics.',70,570,1120,80,27,C.pale);
 note(s,'IRT is Item Response Theory. The implementation uses a logistic probability based on ability theta and item difficulty. BKT is Bayesian Knowledge Tracing and maintains topic mastery probabilities. Ability theta is not a percentage. Correct answers marked Just guessing do not increase theta. Guessing receives 5% of the usual BKT update and cannot establish sufficient evidence or prerequisite readiness. These are prototype policies and require calibration with learner data. The roadmap considers all required prerequisite ancestors.',synopsis+', page 3. Repository: backend/app/services/irt_service.py; backend/app/services/bkt_service.py; backend/app/services/confidence_service.py; backend/README.md.');
}
// 5. Technology
{
 const s=slide('System architecture and technology',5);
 const values=[
 ['Layer','Technology','Responsibility'],
 ['Web interface','React 18, Vite, Tailwind CSS','Profile, assessment, results and roadmap'],
 ['Graph view','React Flow','Topics, prerequisite links and progress'],
 ['Backend API','Python, FastAPI, Pydantic','Assessment and roadmap services'],
 ['Data storage','SQLite, SQLAlchemy','Questions, responses and learner states'],
 ['Adaptive engine','IRT, BKT, prerequisite traversal','Ability, mastery and learning sequence']
 ];
 const t=s.tables.add({rows:6,columns:3,left:70,top:167,width:1138,height:390,columnWidths:[220,370,548],values});
 t.borders.assign({fill:'#D6DFDB',width:0.7,style:'solid'});
 for(let r=0;r<6;r++)for(let c=0;c<3;c++){
  const cell=t.getCell(r,c);cell.fill=r===0?C.teal:(r%2===1?'#ECEFE9':C.ivory);
  cell.text.style={typeface:FONT,fontSize:r===0?24:23,bold:r===0||c===0,color:r===0?C.white:C.ink,verticalAlignment:'middle',insets:{left:15,right:12,top:10,bottom:10}};
 }
 text(s,'Planned AI layer',70,590,295,40,28,C.teal,true);
 text(s,'A pretrained LLM API will provide explanations and practice.',370,592,830,68,26,C.muted);
 note(s,'The interface exchanges validated data with FastAPI services, which access a SQLite database through SQLAlchemy. The knowledge graph is represented by topic and relationship records in relational tables. React Flow visualizes it. Learner model and path-planning services run in the Python backend. Pytest and HTTPX support verification of assessment behavior, confidence handling and roadmap ordering. The language model integration is planned rather than present in the current stack.',synopsis+', page 3, Tech Stack. Repository: frontend/package.json; backend/requirements.txt; backend/app/models/; backend/app/services/.');
}
// 6. Scope and future
{
 const s=slide('Prototype and next steps',6);
 text(s,'WORKING DSA PROTOTYPE',70,166,530,31,21,C.teal,true);
 text(s,'10 topics with prerequisite links',70,223,520,76,32,C.navy,true);
 text(s,'Adaptive diagnostics update ability\nand topic mastery estimates.',70,321,520,83,28,C.muted);
 text(s,'The knowledge graph and roadmap\nshow gaps and recommended actions.',70,426,530,83,28,C.muted);
 text(s,'PLANNED EXTENSIONS',690,166,510,31,21,C.teal,true);
 text(s,'AI teaching guided by the model',690,223,520,76,32,C.navy,true);
 text(s,'Extract topics and suggested links\nfrom a syllabus for review.',690,321,520,83,28,C.muted);
 text(s,'Evaluate the DSA prototype and\ntrial a small OS or DBMS domain.',690,426,520,83,28,C.muted);
 text(s,'Expected outcome',70,566,280,42,28,C.teal,true);
 text(s,'A clearer next learning step, with visible reasons\nbased on the learner’s evidence and prerequisites.',370,568,835,80,28,C.navy);
 note(s,'Current scope includes the DSA graph, question bank, confidence-aware diagnostic, learner state visualization and personalized roadmap. The next phase adds model-guided explanations and practice, topic-level reassessment and syllabus extraction. Evaluation should examine the DSA prototype and a small OS or DBMS example to assess whether the design transfers to another subject. Expected benefits are design goals. The supplied materials do not establish measured learning gains.',synopsis+', pages 2-3, Proposed Solution and Objectives. Repository: backend/README.md; frontend/src/App.jsx.');
}

await fs.mkdir(BUILD+'/previews',{recursive:true});
await (await PresentationFile.exportPptx(p)).save(BUILD+'/draft.pptx');
for(let i=0;i<p.slides.items.length;i++){
 const blob=await p.export({slide:p.slides.items[i],format:'png',scale:1.2});
 await fs.writeFile(BUILD+`/previews/slide-${i+1}.png`,new Uint8Array(await blob.arrayBuffer()));
}
await fs.writeFile(BUILD+'/inspection.ndjson',(await p.inspect({kind:'slide,textbox,table,image',maxChars:50000})).ndjson);
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:BUILD+'/draft.pptx',finalPath:ROOT+'/output/presentation/NeuroLearn_Project_Presentation.pptx',pythonExecutable:RUNTIME+'/python/python.exe',integrityValidatorPath:SKILL+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:SKILL+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','5'],explicitTotalSlideCount:6,requiredNativeTableOwnerSlides:[5],fontPolicy,verifyArtifactToolImport:true,receiptPath:BUILD+'/validation.json'});
console.log(JSON.stringify(result));
