export const toolNames = ['search_memory','save_memory','delete_memory'];
export function evaluate(action) {
  if(!action || typeof action!=='object' || !toolNames.includes(action.tool)) return {decision:'block',rule:'TOOL-001',reason:'This tool is outside the permitted workspace.'};
  const a=action.args;
  if(!a || typeof a!=='object'||Array.isArray(a))return {decision:'block',rule:'INPUT-001',reason:'Invalid action parameters.'};
  const allowed=action.tool==='search_memory'?['query']:action.tool==='save_memory'?['title','content']:['id'];
  if(Object.keys(a).some(k=>!allowed.includes(k)))return {decision:'block',rule:'INPUT-004',reason:'Unexpected action parameters are not permitted.'};
  if(action.tool==='search_memory'){
    if(typeof a.query!=='string'||a.query.length>300)return {decision:'block',rule:'INPUT-002',reason:'Search query must be at most 300 characters.'};
    return {decision:'allow',rule:'MEM-READ',reason:'Read-only search within your NOVA memory.'};
  }
  if(action.tool==='delete_memory')return {decision:'block',rule:'MEM-DELETE',reason:'Deletion is disabled in this release. No memory was removed.'};
  if(typeof a.title!=='string'||!a.title.trim()||a.title.length>100||typeof a.content!=='string'||!a.content.trim()||a.content.length>4000)return {decision:'block',rule:'INPUT-003',reason:'A memory needs a title (1–100 characters) and content (1–4,000 characters).'};
  return {decision:'approval',rule:'MEM-WRITE',reason:'Saving creates a persistent memory. Review the exact text before approving.'};
}
export class TurnFence {
  constructor(){this.current=0;this.controller=new AbortController()}
  next(){this.controller.abort();this.controller=new AbortController();return {id:++this.current,signal:this.controller.signal}}
  active(id){return id===this.current&&!this.controller.signal.aborted}
  cancel(){return this.next()}
}
export class ApprovalStore {
  constructor(){this.pending=new Map()}
  create(action,turn){const id=crypto.randomUUID();this.pending.set(id,{action:structuredClone(action),turn,expires:Date.now()+120000});return id}
  take(id,turn){const p=this.pending.get(id);this.pending.delete(id);if(!p||p.turn!==turn||p.expires<Date.now())throw new Error('Approval expired or belongs to an obsolete turn.');return p.action}
  clear(){this.pending.clear()}
}
export const seedMemory=[
 {id:'m1',title:'NOVA × AEGIS',content:'NOVA understands and plans. AEGIS independently checks each proposed action before execution.',kind:'project',links:['m2','m3','m4'],source:'Starter workspace'},
 {id:'m2',title:'Voice continuity',content:'Keep accepting speech during synthesis and tool work. Interrupt audio, cancel requests, and fence obsolete results by turn ID.',kind:'idea',links:['m3','m5'],source:'Starter workspace'},
 {id:'m3',title:'Rime challenge',content:'Prove one hard voice problem. Record normal and stress cases, disclose active providers, and measure what the user hears.',kind:'source',links:['m5'],source:'Rime PS brief · sample summary'},
 {id:'m4',title:'Local intelligence',content:'Ollama serves the selected Qwen model on your device. Only approved memory operations reach the executor.',kind:'idea',links:['m6'],source:'Starter workspace'},
 {id:'m5',title:'Interruption test',content:'Delay memory search by five seconds. Interrupt and change the question. The obsolete search must never be spoken as current.',kind:'task',links:['m2'],source:'Acceptance fixture'},
 {id:'m6',title:'AEGIS policy',content:'Read memory is allowed. Save memory requires explicit approval. Delete and unknown tools are blocked.',kind:'source',links:['m1'],source:'Policy v1'}
];
