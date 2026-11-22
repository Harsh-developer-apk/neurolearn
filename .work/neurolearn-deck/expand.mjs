import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {FileBlob, PresentationFile} from '@oai/artifact-tool';
process.on('uncaughtException',error=>{console.error(error.stack);process.exit(1);});
const ROOT='C:/Users/asus1/shukraniti';
const BUILD=ROOT+'/.work/neurolearn-deck/expanded';
const SKILL='C:/Users/asus1/.codex/plugins/cache/openai-primary-runtime/presentations/26.1013.11914/skills/presentations';
const RUNTIME='C:/Users/asus1/.cache/codex-runtimes/codex-primary-runtime/dependencies';
process.env.RUNTIME_NODE_MODULES=RUNTIME+'/node/node_modules';
const {finalizePresentation}=await import(pathToFileURL(SKILL+'/container_tools/artifact_tool_utils.mjs').href);
const C={navy:'#102A3A',ivory:'#F4F1E9',teal:'#0F766E',amber:'#E8A247',ink:'#172E3A',muted:'#536771',pale:'#C5D6D9',white:'#FFFFFF'};
const FONT='Calibri';
await fs.mkdir(BUILD+'/previews',{recursive:true});
const p=await PresentationFile.importPptx(await FileBlob.load(ROOT+'/output/presentation/NeuroLearn_Project_Presentation.pptx'));
const original=[...p.slides.items];
const inspection=await p.inspect({kind:'slide,textbox,shape',maxChars:120000});
await fs.writeFile(BUILD+'/source-inspection.ndjson',inspection.ndjson);
const records=inspection.ndjson.split('\n').filter(Boolean).map(x=>JSON.parse(x));
function edit(index,old,value){
 const r=records.find(r=>r.slideIndex===index&&r.text===old);
 if(!r)throw new Error('Missing source text: '+old);
 p.resolve(r.id).text=value;
}
function text(s,content,x,y,w,h,size=27,color=C.ink,bold=false){
 const t=s.shapes.add({geometry:'textbox',name:content.replace(/\n/g,' ').slice(0,70),position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
 t.text=content;t.text.style={fontSize:size,typeface:FONT,color,bold,alignment:'left',verticalAlignment:'top',autoFit:'none',wrap:'square',insets:0};return t;
}
function slide(title,n,dark=false){
 const s=p.slides.add();s.background.fill=dark?C.navy:C.ivory;
 text(s,title,70,56,1138,77,46,dark?C.ivory:C.navy,true);
 text(s,'NEUROLEARN',70,666,450,24,16,dark?C.pale:C.muted,true);
 text(s,String(n).padStart(2,'0'),1160,663,48,29,19,dark?C.pale:C.muted);return s;
}
const USER='User clarification: planned B2C personalized training, subject diagnostic, learner graph and roadmap, software-controlled LLM teaching with RAG, and a topic test before progression.';
function note(s,body,extra=''){s.speakerNotes.text=body+'\n\nSources: '+USER+(extra?'\n'+extra:'');}
edit(0,'A learner model that identifies knowledge gaps\nand guides the next learning step.','Personalized training through diagnosis,\nguided AI teaching and topic mastery checks.');
edit(4,'05','09');
edit(4,'Planned AI layer','Planned RAG layer');
edit(4,'A pretrained LLM API will provide explanations and practice.','Content index and retrieval feed an LLM API,\nunder the software’s lesson instructions.');
original[4].speakerNotes.text+='\nPlanned RAG architecture: reviewed subject material is split into passages and indexed for retrieval. Retrieval returns topic-relevant passages. The lesson controller sends the selected evidence and learner-specific teaching instructions to the LLM. A separate topic assessment updates the learner model. A vector index is proposed, with no vendor selected. '+USER;
edit(5,'06','10');
edit(5,'AI teaching guided by the model','RAG teaching with topic mastery checks');
edit(5,'Extract topics and suggested links\nfrom a syllabus for review.','The software sets lesson scope, depth\nand practice from learner evidence.');
edit(5,'Evaluate the DSA prototype and\ntrial a small OS or DBMS domain.','Add topic tests, evaluate learning gains\nand extend to other subjects.');
edit(5,'Expected outcome','Training goal');
edit(5,'A clearer next learning step, with visible reasons\nbased on the learner’s evidence and prerequisites.','Personalized training that adapts what each\nstudent learns and verifies topic understanding.');
original[5].speakerNotes.text+='\nThe B2C vision serves individual students directly. RAG teaching, a lesson controller and topic-level progression checks are planned extensions. Evaluation should assess learning gains without claiming they have already been demonstrated. '+USER;
p.slides.keep([0,1,3,4,5]);

const journey=slide('Personalized training for each learner',3);
text(journey,'B2C model: an individual student chooses a subject and follows an adaptive path.',70,151,1138,64,28,C.teal,true);
[
 ['01  Choose a subject','The student selects what they want to learn.'],
 ['02  Take the diagnostic','Answers reveal strengths, gaps and uncertainty.'],
 ['03  See a personal roadmap','The learner graph guides the topic sequence.'],
 ['04  Learn with guided AI','The software directs a RAG-based LLM lesson.'],
 ['05  Test the current topic','A focused test checks understanding after teaching.'],
 ['06  Advance or revisit','Fresh evidence updates the path before progression.']
].forEach((r,i)=>{const x=i%2?690:70,y=245+Math.floor(i/2)*132;text(journey,r[0],x,y,520,43,30,C.navy,true);text(journey,r[1],x,y+51,520,72,27,C.muted);});
note(journey,'This is the planned end-to-end B2C learner journey. The learner chooses a subject, completes its diagnostic and receives a learner-specific view of the topic graph and a personalized roadmap. Topic relationships come from the curriculum. Assessment personalizes learner state rather than creating prerequisite relationships from scratch. The software selects the next suitable topic, directs teaching and evaluates readiness after a focused topic test. The loop repeats until the training goals are met. Current diagnostic scope is DSA.');

const control=slide('The software controls what the LLM teaches',5,true);
[
 ['Learner evidence','Topic mastery, confidence and prerequisite gaps\ndetermine what the student needs next.'],
 ['Lesson controller','The software sets the topic, learning objective,\nexplanation depth and practice difficulty.'],
 ['LLM teacher','The model follows that brief and uses retrieved\nmaterial to explain the topic with examples.']
].forEach((r,i)=>{const y=170+i*125;text(control,r[0],70,y,400,45,32,C.amber,true);text(control,r[1],510,y,690,90,28,C.pale);});
text(control,'Example teaching brief',70,566,385,45,28,C.ivory,true);
text(control,'Review queue operations before teaching BFS.\nUse a simple worked example, then guided practice.',510,566,690,80,27,C.pale);
note(control,'Planned controller design: use the learner state and curriculum prerequisites to select an objective and prepare a structured teaching brief. It specifies topic scope, prerequisites to review, depth, difficulty and relevant misconceptions. The LLM generates the explanation using this brief and retrieved study material. The application checks scope and grounding and controls progression through topic assessments. These are proposed application controls, not a claim that instructions guarantee perfect model compliance. Example brief is illustrative.');

const rag=slide('RAG-based teaching with subject material',6);
text(rag,'Retrieval-Augmented Generation pairs relevant study passages with the LLM.',70,150,1138,62,28,C.teal,true);
[
 ['01','Prepare the material','Split reviewed subject content into passages\nand index them for retrieval.'],
 ['02','Retrieve for this lesson','Find passages for the selected topic,\nlearning objective and prerequisite gap.'],
 ['03','Generate the explanation','Send the passages and the software’s\nteaching brief to the LLM.'],
 ['04','Support the student','Explain with examples and practice,\nand link the lesson to its source material.']
].forEach((r,i)=>{const y=235+i*92;text(rag,r[0],70,y,75,55,38,C.teal,true);text(rag,r[1],170,y+2,410,40,30,C.navy,true);text(rag,r[2],600,y+2,605,79,26,C.muted);});
text(rag,'Planned teaching layer',70,620,1000,31,21,C.teal,true);
note(rag,'RAG combines retrieval from an external knowledge source with language generation. The proposed NeuroLearn teaching design indexes reviewed subject passages and retrieves material relevant to the lesson objective. The prompt combines those passages with the learner-specific teaching brief. The generated lesson can cite or link the retrieved source passages. The retrieval index supplies teaching content, while the curriculum knowledge graph organizes prerequisites and the learner model tracks understanding. These are distinct roles. RAG does not itself establish learner mastery or guarantee factual accuracy. Implementation choices, including an embedding model and index vendor, remain open.','RAG foundation: Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks, https://arxiv.org/abs/2005.11401');

const mastery=slide('Topic tests guide progression',7);
[
 ['Teach and practise','The student completes the current topic’s\nexplanation, worked examples and practice.'],
 ['Test the topic','A focused assessment checks understanding\nwith fresh questions after the lesson.'],
 ['Update learner state','Responses revise topic mastery and reveal\nremaining gaps in the learner graph.']
].forEach((r,i)=>{const y=170+i*107;text(mastery,r[0],70,y,430,44,32,C.navy,true);text(mastery,r[1],600,y,605,84,28,C.muted);});
text(mastery,'Mastery supported',70,521,520,45,31,C.teal,true);
text(mastery,'Move to the next eligible topic\nwhen prerequisite checks also pass.',70,578,520,75,27,C.muted);
text(mastery,'Understanding still uncertain',690,521,520,45,31,C.teal,true);
text(mastery,'Reteach the gap, adjust practice\nand reassess before moving ahead.',690,578,520,75,27,C.muted);
note(mastery,'Planned topic-level teaching loop: a student studies the assigned topic, completes practice and then takes a focused test. The assessment should use fresh items rather than simply repeat solved practice. The application updates the learner state using performance evidence and confidence, then decides whether mastery is sufficiently supported. If so, it proceeds to the next eligible topic. Otherwise it revisits the weak concept or prerequisite, adjusts the lesson and tests again. Exact progression thresholds and test length require evaluation. Completing a lesson alone does not establish mastery.');

const example=slide('A personalized DSA learning path',8);
text(example,'Illustrative learner goal: understand breadth-first search (BFS)',70,150,1138,50,28,C.teal,true);
[
 ['Diagnostic finding','The learner struggles with queue operations.\nThe graph identifies queues as a BFS prerequisite.'],
 ['Assigned teaching','The software asks the LLM to teach FIFO and queue\noperations using retrieved material and a worked example.'],
 ['Topic test and next step','Test queue understanding. If evidence supports mastery,\nteach BFS next. Otherwise revisit the missed concept.']
].forEach((r,i)=>{const y=242+i*125;text(example,r[0],70,y,445,78,32,C.navy,true);text(example,r[1],570,y,638,98,28,C.muted);});
text(example,'The next lesson changes when the evidence changes.',70,624,1138,35,27,C.teal,true);
note(example,'This scenario illustrates the proposed product experience, not a measured result or an actual student record. A diagnostic reveals a queue-related gap. The controller chooses queue operations as the immediate objective and retrieves suitable explanations. The LLM teaches FIFO and queue operations. A topic test checks the learner’s understanding. Passing with sufficient evidence allows a BFS lesson when other requirements are also satisfied. Otherwise the application revisits the missed concept and reassesses. The example makes the software’s control of content and progression concrete.');

const slideIds=(await p.inspect({kind:'slide',maxChars:30000})).ndjson.split('\n').filter(Boolean).map(x=>JSON.parse(x)).filter(x=>x.kind==='slide').map(x=>x.id);
p.slides.reorder([0,1,5,2,6,7,8,9,3,4].map(i=>slideIds[i]));
await (await PresentationFile.exportPptx(p)).save(BUILD+'/draft.pptx');
for(let i=0;i<p.slides.items.length;i++){
 const png=await p.export({slide:p.slides.items[i],format:'png',scale:1.2});
 await fs.writeFile(BUILD+`/previews/slide-${i+1}.png`,new Uint8Array(await png.arrayBuffer()));
}
await fs.writeFile(BUILD+'/inspection.ndjson',(await p.inspect({kind:'slide,textbox,table,image',maxChars:150000})).ndjson);
const result=await finalizePresentation({workspaceDir:ROOT,candidatePath:BUILD+'/draft.pptx',finalPath:ROOT+'/output/presentation/NeuroLearn_Personalized_Training_Expanded.pptx',pythonExecutable:RUNTIME+'/python/python.exe',integrityValidatorPath:SKILL+'/container_tools/inspect_presentation_package_integrity.py',layoutValidatorPath:SKILL+'/container_tools/inspect_presentation_layout_geometry.py',layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-bullet-geometry','--validate-heading-fit','--require-native-table-slide','9'],explicitTotalSlideCount:10,requiredNativeTableOwnerSlides:[9],fontPolicy:{basis:'design',families:[FONT]},verifyArtifactToolImport:true,receiptPath:BUILD+'/validation.json'});
console.log(JSON.stringify(result));
